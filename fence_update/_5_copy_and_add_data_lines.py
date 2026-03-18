import arcpy
from datetime import datetime

arcpy.env.overwriteOutput = True


def add_message(msg):
    arcpy.AddMessage(msg)
    print(msg)


def add_warning(msg):
    arcpy.AddWarning(msg)
    print(msg)


def get_existing_field(possible_fields, available_fields):
    for field in possible_fields:
        if field in available_fields:
            return field
    return None


def copy_lines(lines_to_copy, target_lines):
    inserted_count = 0

    add_message(f"Copying lines from: {lines_to_copy}")
    add_message(f"Into target: {target_lines}")

    with arcpy.da.SearchCursor(lines_to_copy, ["SHAPE@"]) as search_cur:
        with arcpy.da.InsertCursor(target_lines, ["SHAPE@"]) as insert_cur:
            for row in search_cur:
                insert_cur.insertRow(row)
                inserted_count += 1

    add_message(f"Inserted {inserted_count} line(s) into target.")
    return inserted_count


def get_feature_code(improvement_group):
    if not improvement_group:
        return None

    value = str(improvement_group).upper()

    if value == "FENCE":
        return "FI91600370"
    elif value == "STOCK TRAIL":
        return "DC31700700"
    elif value == "WATER DEVELOPMENT":
        return "FI19600010"
    else:
        add_warning(f"Uncommon Improvement Group value: {value}")
        return None


def build_source_dictionary(fc_to_copy):
    possible_field_names_1 = ["Funding"]
    possible_field_names_2 = ["IMPRV_TYPE", "Impr_type", "Imprv_Type", "Imprv_type", "IMPR_TYPE"]
    possible_field_names_3 = ["IMPRV_GRP", "Impr_Grp", "Imprv_Grp", "Imprv_grp"]
    possible_field_names_4 = ["FieldCond", "Field_Cond"]
    possible_field_names_5 = ["Ownership"]
    possible_field_names_6 = ["Date_Creat", "TimeStamp"]

    source_field_names = [f.name for f in arcpy.ListFields(fc_to_copy)]
    add_message(f"Available fields in source: {source_field_names}")

    selected_field_funding = get_existing_field(possible_field_names_1, source_field_names)
    selected_field_imprv_type = get_existing_field(possible_field_names_2, source_field_names)
    selected_field_imprv_grp = get_existing_field(possible_field_names_3, source_field_names)
    selected_field_fieldcond = get_existing_field(possible_field_names_4, source_field_names)
    selected_field_ownership = get_existing_field(possible_field_names_5, source_field_names)
    selected_field_date = get_existing_field(possible_field_names_6, source_field_names)

    add_message(f"Selected Funding field: {selected_field_funding}")
    add_message(f"Selected Improvement_Type field: {selected_field_imprv_type}")
    add_message(f"Selected Improvement_Group field: {selected_field_imprv_grp}")
    add_message(f"Selected Field_Condition field: {selected_field_fieldcond}")
    add_message(f"Selected Ownership field: {selected_field_ownership}")
    add_message(f"Selected Field_Condition_Date field: {selected_field_date}")

    mapping_list = []

    if selected_field_funding:
        mapping_list.append(("Funding_Source", selected_field_funding))
    else:
        add_warning("No source field found for Funding_Source.")

    if selected_field_imprv_type:
        mapping_list.append(("Improvement_Type", selected_field_imprv_type))
    else:
        add_warning("No source field found for Improvement_Type.")

    if selected_field_imprv_grp:
        mapping_list.append(("Improvement_Group", selected_field_imprv_grp))
    else:
        add_warning("No source field found for Improvement_Group.")

    if selected_field_fieldcond:
        mapping_list.append(("Field_Condition", selected_field_fieldcond))
    else:
        add_warning("No source field found for Field_Condition.")

    if selected_field_ownership:
        mapping_list.append(("Ownership", selected_field_ownership))
    else:
        add_warning("No source field found for Ownership.")

    if selected_field_date:
        mapping_list.append(("Field_Condition_Date", selected_field_date))
    else:
        add_warning("No source field found for Field_Condition_Date.")

    source_fields = ["SHAPE@"] + [src for (_, src) in mapping_list]
    add_message(f"Using source cursor fields: {source_fields}")

    source_dict = {}

    with arcpy.da.SearchCursor(fc_to_copy, source_fields) as s_cur:
        for row in s_cur:
            geom = row[0]
            if geom is None:
                add_warning("Skipping source feature with null geometry.")
                continue

            key = geom.WKT
            attr_dict = {}

            for i, (target_field, source_field) in enumerate(mapping_list):
                value = row[i + 1]

                if target_field == "Improvement_Group" and value not in [None, ""]:
                    value = str(value).upper()

                if target_field == "Field_Condition_Date" and value not in [None, ""]:
                    try:
                        if isinstance(value, datetime):
                            value = value.date()
                    except Exception:
                        pass

                attr_dict[target_field] = value

            if key in source_dict:
                add_warning("Duplicate geometry found in source FC. Later record will overwrite earlier one.")

            source_dict[key] = attr_dict

    add_message(f"Created source dictionary with {len(source_dict)} entries.")
    return source_dict


def update_target_attributes(fc_to_update, source_dict):
    update_fields = [
        "SHAPE@",
        "Funding_Source",
        "Improvement_Type",
        "Improvement_Group",
        "Field_Condition",
        "Ownership",
        "Field_Condition_Date",
        "District_Responsible_Code",
        "Feature_Code"
    ]

    target_field_names = [f.name for f in arcpy.ListFields(fc_to_update)]
    missing_fields = [fld for fld in update_fields[1:] if fld not in target_field_names]

    if missing_fields:
        raise Exception(f"Target FC is missing required fields: {', '.join(missing_fields)}")

    updated_count = 0

    with arcpy.da.UpdateCursor(fc_to_update, update_fields) as u_cur:
        for row in u_cur:
            geom = row[0]
            if geom is None:
                continue

            key = geom.WKT

            if key in source_dict:
                attr_values = source_dict[key]

                for idx, field_name in enumerate(update_fields[1:], start=1):
                    if field_name in attr_values:
                        row[idx] = attr_values[field_name]

                # Constant value
                row[7] = "DMH"

                # Feature code based on Improvement_Group
                improvement_group = row[3]
                feature_code = get_feature_code(improvement_group)
                row[8] = feature_code

                u_cur.updateRow(row)
                updated_count += 1

    add_message(f"Updated {updated_count} target feature(s).")
    return updated_count


def main():
    # Parameter 0 = Source lines
    # Parameter 1 = Target lines
    lines_to_copy = arcpy.GetParameterAsText(0)
    target_lines = arcpy.GetParameterAsText(1)

    if not lines_to_copy:
        raise Exception("Parameter 0 (Source Lines) is required.")
    if not target_lines:
        raise Exception("Parameter 1 (Target Lines) is required.")

    if not arcpy.Exists(lines_to_copy):
        raise Exception(f"Source feature class does not exist: {lines_to_copy}")
    if not arcpy.Exists(target_lines):
        raise Exception(f"Target feature class does not exist: {target_lines}")

    source_desc = arcpy.Describe(lines_to_copy)
    target_desc = arcpy.Describe(target_lines)

    if source_desc.shapeType != "Polyline":
        raise Exception("Source feature class must be a line feature class.")
    if target_desc.shapeType != "Polyline":
        raise Exception("Target feature class must be a line feature class.")

    add_message("*** Starting combined line copy/update tool ***")

    inserted_count = copy_lines(lines_to_copy, target_lines)
    source_dict = build_source_dictionary(lines_to_copy)
    updated_count = update_target_attributes(target_lines, source_dict)

    add_message("****************************************")
    add_message(f"Lines inserted: {inserted_count}")
    add_message(f"Target features updated: {updated_count}")
    add_message("*** Tool completed successfully ***")


if __name__ == "__main__":
    main()
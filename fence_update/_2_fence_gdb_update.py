
import arcpy
import os
import re
from datetime import datetime

arcpy.env.overwriteOutput = True

# ---------------------------------------------------------
# CONSTANTS (as requested)
# ---------------------------------------------------------
OUTPUT_WORKSPACE = r"W:\srm\wml\Workarea\ofedyshy\GIS_requests\a_Requests_Project1\a_Requests_Project1.gdb"
OUT_SR = arcpy.SpatialReference(3005)  # NAD 1983 BC Environment Albers

TARGET_POINTS = (r"W:\FOR\RSI\DCC\CAR\Local_Data\DMH\LOCAL DATA\Range Features\DISTRICT_Data_Range_Business_View\2024 CLEAN VERSION(MOST CURRENT)\DMH_Data_Range_Business_View_Copy.gdb\Range_Improvement_Point")

TARGET_LINES = (r"W:\FOR\RSI\DCC\CAR\Local_Data\DMH\LOCAL DATA\Range Features\DISTRICT_Data_Range_Business_View\2024 CLEAN VERSION(MOST CURRENT)\DMH_Data_Range_Business_View_Copy.gdb\Range_Improvement_Line")


# ---------------------------------------------------------
# Messaging helpers
# ---------------------------------------------------------
def msg(text):
    arcpy.AddMessage(text)
    print(text)

def warn(text):
    arcpy.AddWarning(text)
    print(text)

def err(text):
    arcpy.AddError(text)
    print(text)


# ---------------------------------------------------------
# General helpers
# ---------------------------------------------------------
def clean_name(name: str) -> str:
    """Clean output feature class name for geodatabase use."""
    name = name.replace(" ", "_")
    name = re.sub(r"[^a-zA-Z0-9_]", "", name)
    return name[:63]

def derive_pcs_name(layer_name: str) -> str:
    """
    Ensures output name ends with exactly ONE '_PCS'.
    Prevents '_PCS_PCS' duplication.
    """
    n = clean_name(layer_name)
    return n if n.upper().endswith("_PCS") else f"{n}_PCS"

def get_all_layers_from_group(group_layer):
    """Recursively return all layers inside a group layer."""
    layers = []
    for lyr in group_layer.listLayers():
        if lyr.isGroupLayer:
            layers.extend(get_all_layers_from_group(lyr))
        else:
            layers.append(lyr)
    return layers

def find_group_layer_by_name(map_obj, group_name: str):
    """Find a top-level group layer in the map by name."""
    for lyr in map_obj.listLayers():
        if lyr.isGroupLayer and lyr.name == group_name:
            return lyr
    return None

def get_transformation(in_sr, out_sr):
    """Return a valid transformation if needed, otherwise return empty string."""
    try:
        if not in_sr or in_sr.name == "Unknown":
            return ""
        if hasattr(in_sr, "GCS") and hasattr(out_sr, "GCS"):
            if in_sr.GCS and out_sr.GCS and in_sr.GCS.name == out_sr.GCS.name:
                return ""
        transforms = arcpy.ListTransformations(in_sr, out_sr)
        return transforms[0] if transforms else ""
    except Exception:
        return ""

def layer_already_in_map(map_obj, dataset_path: str) -> bool:
    """Best-effort check whether a dataset path is already present as a layer."""
    ds_norm = os.path.normpath(dataset_path).lower()
    for lyr in map_obj.listLayers():
        try:
            if hasattr(lyr, "dataSource"):
                if os.path.normpath(lyr.dataSource).lower() == ds_norm:
                    return True
        except Exception:
            continue
    return False


# ---------------------------------------------------------
# Geometry keys
# ---------------------------------------------------------
def point_key(geom, precision=6):
    try:
        pt = geom.firstPoint
        return (round(pt.X, precision), round(pt.Y, precision))
    except Exception:
        return None

def wkt_key(geom):
    try:
        return geom.WKT if geom else None
    except Exception:
        return None


# ---------------------------------------------------------
# Field mapping utilities
# ---------------------------------------------------------
def get_existing_field(possible_fields, available_fields):
    for f in possible_fields:
        if f in available_fields:
            return f
    return None

def normalize_value(target_field, value):
    """
    Normalization rules:
      - Field_Condition + Ownership -> strip + lower
      - Improvement_Group -> strip + upper
      - Field_Condition_Date -> datetime -> date
    """
    if value in (None, ""):
        return value

    if target_field in ("Field_Condition", "Ownership"):
        try:
            return str(value).strip().lower()
        except Exception:
            return value

    if target_field == "Improvement_Group":
        return str(value).strip().upper()

    if target_field == "Field_Condition_Date":
        try:
            if isinstance(value, datetime):
                return value.date()
        except Exception:
            pass

    return value

def build_source_dictionary(source_fc, mapping_spec, key_func):
    """
    Build dict: key -> {TargetFieldName: value, ...}
    mapping_spec: dict TargetFieldName -> list of candidate source fields.
    """
    source_fields = [f.name for f in arcpy.ListFields(source_fc)]
    msg(f"Available fields in source ({os.path.basename(source_fc)}): {source_fields}")

    mapping_list = []
    for target_field, candidates in mapping_spec.items():
        src = get_existing_field(candidates, source_fields)
        if src:
            mapping_list.append((target_field, src))
            msg(f"Selected source field for {target_field}: {src}")
        else:
            warn(f"No source field found for {target_field} (candidates: {candidates}).")

    cursor_fields = ["SHAPE@"] + [src for (_, src) in mapping_list]
    msg(f"Using source cursor fields: {cursor_fields}")

    out = {}
    with arcpy.da.SearchCursor(source_fc, cursor_fields) as s_cur:
        for row in s_cur:
            geom = row[0]
            key = key_func(geom)
            if key is None:
                warn("Skipping source feature with invalid/null geometry.")
                continue

            attrs = {}
            for i, (tgt, _) in enumerate(mapping_list):
                attrs[tgt] = normalize_value(tgt, row[i + 1])

            if key in out:
                warn(f"Duplicate geometry key found in source: {key}. Later row overwrote earlier row.")
            out[key] = attrs

    msg(f"Created source dictionary with {len(out)} entries.")
    return out


# ---------------------------------------------------------
# Copy + Update core
# ---------------------------------------------------------
def copy_features(source_fc, target_fc):
    inserted = 0
    msg(f"Copying features from: {source_fc}")
    msg(f"Into target: {target_fc}")

    with arcpy.da.SearchCursor(source_fc, ["SHAPE@"]) as s_cur:
        with arcpy.da.InsertCursor(target_fc, ["SHAPE@"]) as i_cur:
            for row in s_cur:
                i_cur.insertRow(row)
                inserted += 1

    msg(f"Inserted {inserted} feature(s) into target.")
    return inserted

def update_target_attributes(target_fc, source_dict, key_func, update_fields,
                            feature_code_func=None, constants=None):
    """
    update_fields: list of fields excluding SHAPE@
    constants: dict of constant field values applied to every matched row
    """
    constants = constants or {}

    target_field_names = [f.name for f in arcpy.ListFields(target_fc)]
    missing = [f for f in update_fields if f not in target_field_names]
    if missing:
        raise Exception(f"Target FC is missing required fields: {', '.join(missing)}")

    cursor_fields = ["SHAPE@"] + update_fields
    updated = 0

    idx_impr_grp = None
    idx_feature_code = None
    if "Improvement_Group" in update_fields:
        idx_impr_grp = 1 + update_fields.index("Improvement_Group")
    if "Feature_Code" in update_fields:
        idx_feature_code = 1 + update_fields.index("Feature_Code")

    constant_indices = {}
    for fld, val in constants.items():
        if fld in update_fields:
            constant_indices[fld] = (1 + update_fields.index(fld), val)

    with arcpy.da.UpdateCursor(target_fc, cursor_fields) as u_cur:
        for row in u_cur:
            geom = row[0]
            key = key_func(geom)
            if key is None:
                continue

            if key in source_dict:
                attrs = source_dict[key]

                # Apply mapped attributes
                for i, fld in enumerate(update_fields, start=1):
                    if fld in attrs:
                        row[i] = attrs[fld]

                # Apply constants (District_Responsible_Code, etc.)
                for fld, (i, val) in constant_indices.items():
                    row[i] = val

                # Compute Feature_Code safely:
                # NEVER write None into a non-nullable field.
                if feature_code_func and idx_impr_grp and idx_feature_code:
                    computed = feature_code_func(row[idx_impr_grp])
                    if computed is not None:
                        row[idx_feature_code] = computed
                    # else: leave existing value as-is (avoids NOT NULL crash)

                u_cur.updateRow(row)
                updated += 1

    msg(f"Updated {updated} target feature(s).")
    return updated


# ---------------------------------------------------------
# Feature code rules (strip-safe)
# ---------------------------------------------------------
def feature_code_points(improvement_group):
    if not improvement_group:
        return None
    v = str(improvement_group).strip().upper()
    if v == "GATE":
        return "FI91600120"
    if v == "CATTLEGUARD":
        return "FI91600070"
    if v == "WATER DEVELOPMENT":
        return "FI19600010"
    if v == "CORRAL":
        return "FI91600080"
    if v == "CROSSING":
        return "FA00000003"
    if v == "EXCLOSURE":
        return "EXCLOSURE"
    warn(f"Uncommon Improvement Group value (points): {v}")
    return None

def feature_code_lines(improvement_group):
    if not improvement_group:
        return None
    v = str(improvement_group).strip().upper()
    if v == "FENCE":
        return "FI91600370"
    if v == "STOCK TRAIL":
        return "DC31700700"
    if v == "WATER DEVELOPMENT":
        return "FI19600010"
    warn(f"Uncommon Improvement Group value (lines): {v}")
    return None


# ---------------------------------------------------------
# Projection stage (with skip-if-exists)
# ---------------------------------------------------------
def project_groups_to_gdb(aprx_map, group_names):
    """
    For each feature layer in given groups:
      - determine intended output '<name>_PCS' (without double suffix)
      - if output exists: WARN and use it (no reprojection)
      - else: project to OUTPUT_WORKSPACE
      - add the chosen output to map
    Returns: (projected_points, projected_lines)
    """
    if not arcpy.Exists(OUTPUT_WORKSPACE):
        raise arcpy.ExecuteError(f"Output geodatabase does not exist: {OUTPUT_WORKSPACE}")

    projected_points = []
    projected_lines = []
    projected_other = 0
    skipped = 0
    projected_total = 0
    reused_existing = 0

    msg(f"Using output GDB: {OUTPUT_WORKSPACE}")
    msg(f"Output coordinate system: {OUT_SR.name}")

    for group_name in group_names:
        msg(f"--- Processing group: {group_name} ---")
        group_layer = find_group_layer_by_name(aprx_map, group_name)

        if not group_layer:
            warn(f"Group not found: {group_name}")
            skipped += 1
            continue

        for lyr in get_all_layers_from_group(group_layer):
            try:
                if not lyr.isFeatureLayer:
                    continue

                desc = arcpy.Describe(lyr)
                in_fc = desc.catalogPath

                if not arcpy.Exists(in_fc):
                    warn(f"Missing dataset: {lyr.name}")
                    skipped += 1
                    continue

                in_sr = desc.spatialReference
                if not in_sr or in_sr.name == "Unknown":
                    warn(f"Skipping {lyr.name}: unknown spatial reference.")
                    skipped += 1
                    continue

                out_name = derive_pcs_name(lyr.name)
                out_fc = os.path.join(OUTPUT_WORKSPACE, out_name)

                # NEW: if output already exists, reuse and skip projection
                if arcpy.Exists(out_fc):
                    warn(f"Output exists, skipping projection and reusing: {out_name}")
                    reused_existing += 1
                else:
                    transform_method = get_transformation(in_sr, OUT_SR)
                    msg(f"Projecting {lyr.name} -> {out_name}")
                    msg(f"Input SR: {in_sr.name}")
                    msg(f"Transformation: {transform_method if transform_method else 'none'}")

                    arcpy.management.Project(
                        in_dataset=in_fc,
                        out_dataset=out_fc,
                        out_coor_system=OUT_SR,
                        transform_method=transform_method if transform_method else None,
                        in_coor_system=in_sr
                    )
                    projected_total += 1

                # Add chosen output to map
                if not layer_already_in_map(aprx_map, out_fc):
                    aprx_map.addDataFromPath(out_fc)
                    msg(f"Added to map: {out_name}")
                else:
                    msg(f"Already in map: {out_name}")

                # Classify by geometry
                out_desc = arcpy.Describe(out_fc)
                if out_desc.shapeType == "Point":
                    projected_points.append(out_fc)
                elif out_desc.shapeType == "Polyline":
                    projected_lines.append(out_fc)
                else:
                    projected_other += 1

            except arcpy.ExecuteError:
                warn(f"Failed: {lyr.name}")
                warn(arcpy.GetMessages(2))
                skipped += 1
            except Exception as ex:
                warn(f"Failed: {lyr.name} | {str(ex)}")
                skipped += 1

    msg("--------------------------------------------------")
    msg(f"New projections created: {projected_total}")
    msg(f"Reused existing *_PCS: {reused_existing}")
    msg(f"Projected points used: {len(projected_points)}")
    msg(f"Projected lines used: {len(projected_lines)}")
    msg(f"Other geometry: {projected_other}")
    msg(f"Skipped: {skipped}")

    return projected_points, projected_lines


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------
def main():
    # Parameter 0 = group names (multi-value string)
    group_names_raw = arcpy.GetParameterAsText(0)
    group_names = [g.strip() for g in group_names_raw.split(";") if g.strip()]
    if not group_names:
        raise arcpy.ExecuteError("No group layer names were provided.")

    # Parameter 1 = district code (optional, default DMH)
    district_code = arcpy.GetParameterAsText(1)
    if not district_code:
        district_code = "DMH"
    district_code = district_code.strip().upper()
    if len(district_code) > 3:
        warn(f"District code '{district_code}' is longer than 3 characters; trimming to 3.")
        district_code = district_code[:3]

    # Ensure targets exist
    for p in (TARGET_POINTS, TARGET_LINES):
        if not arcpy.Exists(p):
            raise arcpy.ExecuteError(f"Target feature class does not exist: {p}")

    # Current project / map
    aprx = arcpy.mp.ArcGISProject("CURRENT")
    active_map = aprx.activeMap
    if active_map is None:
        raise arcpy.ExecuteError("No active map found.")

    msg("*** Starting unified Project + Copy/Update tool ***")
    msg(f"Using District_Responsible_Code = {district_code}")

    # 1) Project (or reuse) and add to map
    projected_points, projected_lines = project_groups_to_gdb(active_map, group_names)

    # 2) Points workflow
    point_mapping_spec = {
        "Funding_Source": ["Fund_Src", "Funding"],
        "Improvement_Type": ["IMPRV_TYPE", "Impr_type", "Imprv_Type"],
        "Improvement_Group": ["IMPRV_GRP", "Impr_Grp", "Imprv_Grp", "Imprv_grp"],
        "Field_Condition": ["FieldCond", "Field_Cond"],
        "Ownership": ["Ownership"],
        "Field_Condition_Date": ["Date_Creat", "TimeStamp"],
    }

    point_update_fields = [
        "Funding_Source",
        "Improvement_Type",
        "Improvement_Group",
        "Field_Condition",
        "Ownership",
        "Field_Condition_Date",
        "District_Responsible_Code",
        "Feature_Code",
    ]

    total_inserted_points = 0
    total_updated_points = 0

    for src in projected_points:
        msg(f"--- POINT workflow for projected FC: {src} ---")
        total_inserted_points += copy_features(src, TARGET_POINTS)
        src_dict = build_source_dictionary(src, point_mapping_spec, key_func=point_key)
        total_updated_points += update_target_attributes(
            TARGET_POINTS,
            src_dict,
            key_func=point_key,
            update_fields=point_update_fields,
            feature_code_func=feature_code_points,
            constants={"District_Responsible_Code": district_code}
        )

    # 3) Lines workflow
    line_mapping_spec = {
        "Funding_Source": ["Funding", "Fund_Src"],
        "Improvement_Type": ["IMPRV_TYPE", "Impr_type", "Imprv_Type", "Imprv_type", "IMPR_TYPE"],
        "Improvement_Group": ["IMPRV_GRP", "Impr_Grp", "Imprv_Grp", "Imprv_grp"],
        "Field_Condition": ["FieldCond", "Field_Cond"],
        "Ownership": ["Ownership"],
        "Field_Condition_Date": ["Date_Creat", "TimeStamp"],
    }

    line_update_fields = [
        "Funding_Source",
        "Improvement_Type",
        "Improvement_Group",
        "Field_Condition",
        "Ownership",
        "Field_Condition_Date",
        "District_Responsible_Code",
        "Feature_Code",
    ]

    total_inserted_lines = 0
    total_updated_lines = 0

    for src in projected_lines:
        msg(f"--- LINE workflow for projected FC: {src} ---")
        total_inserted_lines += copy_features(src, TARGET_LINES)
        src_dict = build_source_dictionary(src, line_mapping_spec, key_func=wkt_key)
        total_updated_lines += update_target_attributes(
            TARGET_LINES,
            src_dict,
            key_func=wkt_key,
            update_fields=line_update_fields,
            feature_code_func=feature_code_lines,
            constants={"District_Responsible_Code": district_code}
        )

    # Optional: add targets to map
    for target in (TARGET_POINTS, TARGET_LINES):
        try:
            if not layer_already_in_map(active_map, target):
                active_map.addDataFromPath(target)
                msg(f"Added target to map: {target}")
        except Exception:
            pass

    msg("****************************************")
    msg(f"Projected point FCs used: {len(projected_points)}")
    msg(f"Projected line FCs used: {len(projected_lines)}")
    msg(f"Points inserted: {total_inserted_points}")
    msg(f"Points updated: {total_updated_points}")
    msg(f"Lines inserted: {total_inserted_lines}")
    msg(f"Lines updated: {total_updated_lines}")
    msg("*** Tool completed successfully ***")


if __name__ == "__main__":
    main()
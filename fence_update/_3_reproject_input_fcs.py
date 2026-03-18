import arcpy
import os
import re

# ---------------------------------------------------------
# DEFAULT OUTPUT GDB
# ---------------------------------------------------------
output_workspace = r"W:\srm\wml\Workarea\ofedyshy\GIS_requests\a_Requests_Project1\a_Requests_Project1.gdb"

# Output coordinate system: NAD 1983 BC Environment Albers
output_coordinate_system = arcpy.SpatialReference(3005)


# ---------------------------------------------------------
# Helper functions
# ---------------------------------------------------------
def clean_name(name):
    """Clean output feature class name for geodatabase use."""
    name = name.replace(" ", "_")
    name = re.sub(r"[^a-zA-Z0-9_]", "", name)
    return name[:63]


def get_all_layers_from_group(group_layer):
    """Recursively return all layers inside a group layer."""
    layers = []
    for lyr in group_layer.listLayers():
        if lyr.isGroupLayer:
            layers.extend(get_all_layers_from_group(lyr))
        else:
            layers.append(lyr)
    return layers


def find_group_layer_by_name(map_obj, group_name):
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
            if in_sr.GCS.name == out_sr.GCS.name:
                return ""

        transformations = arcpy.ListTransformations(in_sr, out_sr)
        if transformations:
            return transformations[0]

        return ""
    except Exception:
        return ""


# ---------------------------------------------------------
# Script tool parameter
# ---------------------------------------------------------
# Parameter 0 = group names (multi-value string)
group_names_raw = arcpy.GetParameterAsText(0)
group_names = [g.strip() for g in group_names_raw.split(";") if g.strip()]

if not group_names:
    raise arcpy.ExecuteError("No group layer names were provided.")

if not arcpy.Exists(output_workspace):
    raise arcpy.ExecuteError(f"Output geodatabase does not exist: {output_workspace}")


# ---------------------------------------------------------
# Current project / map
# ---------------------------------------------------------
aprx = arcpy.mp.ArcGISProject("CURRENT")
active_map = aprx.activeMap

if active_map is None:
    raise arcpy.ExecuteError("No active map found.")

arcpy.AddMessage(f"Using output GDB: {output_workspace}")

projected_count = 0
added_count = 0
skipped_count = 0


# ---------------------------------------------------------
# Main processing
# ---------------------------------------------------------
for group_name in group_names:
    arcpy.AddMessage(f"--- Processing group: {group_name} ---")

    group_layer = find_group_layer_by_name(active_map, group_name)

    if not group_layer:
        arcpy.AddWarning(f"Group not found: {group_name}")
        skipped_count += 1
        continue

    child_layers = get_all_layers_from_group(group_layer)

    for lyr in child_layers:
        try:
            if not lyr.isFeatureLayer:
                continue

            desc = arcpy.Describe(lyr)
            in_dataset = desc.catalogPath

            if not arcpy.Exists(in_dataset):
                arcpy.AddWarning(f"Missing dataset: {lyr.name}")
                skipped_count += 1
                continue

            in_sr = desc.spatialReference
            if not in_sr or in_sr.name == "Unknown":
                arcpy.AddWarning(f"Skipping {lyr.name}: unknown spatial reference.")
                skipped_count += 1
                continue

            clean_fc_name = clean_name(lyr.name)
            out_fc_name = f"{clean_fc_name}_PCS"
            out_dataset = os.path.join(output_workspace, out_fc_name)

            transform_method = get_transformation(in_sr, output_coordinate_system)

            arcpy.AddMessage(f"Projecting {lyr.name} -> {out_fc_name}")
            arcpy.AddMessage(f"Input SR: {in_sr.name}")
            arcpy.AddMessage(f"Transformation: {transform_method if transform_method else 'none'}")

            # Delete existing output if it already exists
            if arcpy.Exists(out_dataset):
                arcpy.management.Delete(out_dataset)

            arcpy.management.Project(
                in_dataset=in_dataset,
                out_dataset=out_dataset,
                out_coor_system=output_coordinate_system,
                transform_method=transform_method if transform_method else None,
                in_coor_system=in_sr
            )

            projected_count += 1

            # Add output directly to the map
            active_map.addDataFromPath(out_dataset)
            arcpy.AddMessage(f"Added to map: {out_fc_name}")
            added_count += 1

        except arcpy.ExecuteError:
            arcpy.AddWarning(f"Failed: {lyr.name}")
            arcpy.AddWarning(arcpy.GetMessages(2))
            skipped_count += 1
        except Exception as e:
            arcpy.AddWarning(f"Failed: {lyr.name} | {str(e)}")
            skipped_count += 1

arcpy.AddMessage("--------------------------------------------------")
arcpy.AddMessage(f"Projected: {projected_count}")
arcpy.AddMessage(f"Added to map: {added_count}")
arcpy.AddMessage(f"Skipped: {skipped_count}")
arcpy.AddMessage("Done.")
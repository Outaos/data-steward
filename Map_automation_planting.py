# -*- coding: utf-8 -*-

import time
import arcpy
import os
import math
from datetime import datetime


# ------------------------------------------------------------
# MAIN FUNCTION
# ------------------------------------------------------------
def produce_maps(opening_ids, output_folder, layout_template,
                 zoom_buffer_ratio, number_of_maps):

    start_time = time.time()

    arcpy.env.workspace = arcpy.Describe(opening_ids).path
    os.makedirs(output_folder, exist_ok=True)

    project = arcpy.mp.ArcGISProject("CURRENT")
    layout = project.listLayouts(layout_template)[0]

    # Required map frames (same as original script)
    map_frame = layout.listElements("MAPFRAME_ELEMENT", "Planting_and_Silviculture")[0]
    ref_map_frame = layout.listElements("MAPFRAME_ELEMENT", "Reference")[0]

    map_view = map_frame.map

    # Set reference frame scale (same as original)
    ref_map_frame.camera.scale = 8000000

    count = 0

    with arcpy.da.SearchCursor(opening_ids,
                               ["OPENING_ID", "SILV_POLYG", "SHAPE@"]) as cursor:

        for opening_id, silv_poly_num, geometry in cursor:

            if number_of_maps and count >= number_of_maps:
                arcpy.AddMessage(f"[INFO] Reached max exports ({count}); stopping.")
                break

            count += 1
            arcpy.AddMessage(f"[{count}] OPENING_ID={opening_id}")

            if geometry is None or geometry.extent is None:
                arcpy.AddWarning("Geometry or extent is None; skipping.")
                continue

            orig_ext = geometry.extent
            width = orig_ext.XMax - orig_ext.XMin
            height = orig_ext.YMax - orig_ext.YMin

            # ------------------------------------------------------------
            # BUFFER EXTENT (same logic as original)
            # ------------------------------------------------------------
            x_buffer = width * zoom_buffer_ratio
            y_buffer = height * zoom_buffer_ratio

            new_extent = arcpy.Extent(
                orig_ext.XMin - x_buffer,
                orig_ext.YMin - y_buffer,
                orig_ext.XMax + x_buffer,
                orig_ext.YMax + y_buffer
            )

            map_frame.camera.setExtent(new_extent)

            # Raw scale
            raw_scale = map_frame.camera.scale

            # Round UP to nearest 5000 (same as original)
            step = 5000.0
            rounded_scale = math.ceil(raw_scale / step) * step
            map_frame.camera.scale = rounded_scale

            # ------------------------------------------------------------
            # DYNAMIC TEXT (same as original)
            # ------------------------------------------------------------

            # Opening name
            silv_poly_str = "" if silv_poly_num is None else str(silv_poly_num)
            opening_ids_text = f"Opening {opening_id} {silv_poly_str}".strip()

            layout.listElements("TEXT_ELEMENT", "Opening_Name")[0].text = opening_ids_text

            # Date
            current_time = datetime.now().strftime("%Y-%m-%d %I:%M %p")
            layout.listElements("TEXT_ELEMENT", "Date")[0].text = f"Date exported: {current_time}"

            # Spatial Reference
            spatial_ref_name = map_view.spatialReference.name
            layout.listElements("TEXT_ELEMENT", "Spatial_Reference")[0].text = \
                f"Spatial Reference: {spatial_ref_name}"

            # Scale
            layout.listElements("TEXT_ELEMENT", "Scale")[0].text = \
                f"Scale: 1:{int(map_frame.camera.scale)}"

            # ------------------------------------------------------------
            # EXPORT (exactly as in your original)
            # ------------------------------------------------------------
            output_pdf = os.path.join(
                output_folder,
                f"Planting_{opening_id}_{silv_poly_str}.pdf"
            )

            layout.exportToPDF(output_pdf)
            arcpy.AddMessage(f"Exported: {output_pdf}")

    arcpy.AddMessage("Map creation complete!")

    elapsed_time = time.time() - start_time
    arcpy.AddMessage(f"Script execution time: {elapsed_time:.2f} seconds")


# ------------------------------------------------------------
# TOOLBOX PARAMETERS
# ------------------------------------------------------------
if __name__ == "__main__":

    opening_ids = arcpy.GetParameterAsText(0)       # Feature Layer
    output_folder = arcpy.GetParameterAsText(1)     # Folder
    layout_template = arcpy.GetParameterAsText(2)   # String
    zoom_buffer_ratio = float(arcpy.GetParameterAsText(3))
    number_of_maps = int(arcpy.GetParameterAsText(4))

    produce_maps(opening_ids,
                 output_folder,
                 layout_template,
                 zoom_buffer_ratio,
                 number_of_maps)
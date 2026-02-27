# -*- coding: utf-8 -*-
"""
ArcGIS Pro Script Tool: Export Feature Layer to SHP and/or KMZ

Parameters (recommended):
  0) Input Feature Layer   (Feature Layer)
  1) Export Shapefile?     (Boolean)
  2) Export KMZ?           (Boolean)
  3) Output Folder         (Folder) OPTIONAL

Outputs:
  - <sanitized_name>.shp  (if checked)
  - <sanitized_name>.kmz  (if checked)
"""

import os
import re
import shutil
import tempfile
import arcpy


def get_bool_param(i: int, default: bool = False) -> bool:
    v = arcpy.GetParameter(i)
    if v is None:
        return default
    if isinstance(v, bool):
        return v
    s = str(v).strip().lower()
    if s == "":
        return default
    return s in ("true", "t", "1", "yes", "y")


def sanitize_filename(name: str) -> str:
    """
    Safe filename base:
    - replace non [A-Za-z0-9_] with underscore
    - collapse multiple underscores
    - trim underscores
    """
    if not name:
        return "export"
    name = name.strip()
    name = re.sub(r"[^\w]+", "_", name)     # \w = letters/digits/underscore
    name = re.sub(r"_+", "_", name)
    name = name.strip("_")
    return name or "export"


def infer_output_folder(desc) -> str:
    """
    If input is a shapefile, use its folder; else use scratchFolder.
    """
    cat = getattr(desc, "catalogPath", "") or ""
    if cat.lower().endswith(".shp"):
        folder = os.path.dirname(cat)
        if os.path.isdir(folder):
            return folder

    scratch = arcpy.env.scratchFolder or arcpy.env.scratchWorkspace
    if scratch and os.path.isdir(scratch):
        return scratch

    return tempfile.gettempdir()


def delete_shapefile_set(shp_path: str) -> None:
    """
    Deletes .shp and common sidecars if they exist.
    """
    base = os.path.splitext(shp_path)[0]
    for ext in (".shp", ".dbf", ".shx", ".prj", ".cpg", ".sbn", ".sbx", ".xml"):
        p = base + ext
        if os.path.exists(p):
            try:
                os.remove(p)
            except Exception:
                pass


def export_shp(input_layer: str, out_folder: str, base: str) -> str:
    """
    Export to shapefile with sanitized name.
    Uses CopyFeatures (more predictable naming) into a temp folder, then renames set.
    """
    arcpy.AddMessage("Exporting to SHP...")

    out_shp = os.path.join(out_folder, f"{base}.shp")
    if os.path.exists(out_shp) and arcpy.env.overwriteOutput:
        delete_shapefile_set(out_shp)

    # CopyFeatures can write directly to .shp path
    arcpy.management.CopyFeatures(input_layer, out_shp)

    if not os.path.exists(out_shp):
        raise RuntimeError(f"SHP export completed but output not found: {out_shp}")

    return out_shp


def export_kmz(input_layer: str, out_folder: str, base: str) -> str:
    """
    Export to KMZ using LayerToKML via a temporary .lyrx.
    """
    arcpy.AddMessage("Exporting to KMZ...")

    out_kmz = os.path.join(out_folder, f"{base}.kmz")

    # temp workspace for .lyrx
    tmp_root = arcpy.env.scratchFolder or tempfile.gettempdir()
    work_dir = tempfile.mkdtemp(prefix="lyrx_", dir=tmp_root)

    tmp_layer = "tmp_export_layer"
    tmp_lyrx = os.path.join(work_dir, f"{base}.lyrx")

    try:
        if arcpy.Exists(tmp_layer):
            arcpy.management.Delete(tmp_layer)

        arcpy.management.MakeFeatureLayer(input_layer, tmp_layer)
        arcpy.management.SaveToLayerFile(tmp_layer, tmp_lyrx, "RELATIVE")
        arcpy.management.Delete(tmp_layer)

        # Try writing directly to destination
        try:
            if os.path.exists(out_kmz) and arcpy.env.overwriteOutput:
                os.remove(out_kmz)

            # IMPORTANT: positional args only
            # LayerToKML(in_layer, out_kmz_file, layer_output_scale, is_composite, boundary_box_extent)
            arcpy.conversion.LayerToKML(tmp_lyrx, out_kmz, 0, "NO_COMPOSITE", "")

        except Exception as e:
            arcpy.AddWarning(f"Direct KMZ write failed; trying local temp then copy. Reason: {e}")

            local_kmz = os.path.join(tempfile.gettempdir(), f"{base}.kmz")
            if os.path.exists(local_kmz) and arcpy.env.overwriteOutput:
                os.remove(local_kmz)

            arcpy.conversion.LayerToKML(tmp_lyrx, local_kmz, 0, "NO_COMPOSITE", "")

            # Copy back to destination folder
            shutil.copy2(local_kmz, out_kmz)

        if not os.path.exists(out_kmz):
            raise RuntimeError(f"KMZ export completed but output not found: {out_kmz}")

        return out_kmz

    finally:
        try:
            shutil.rmtree(work_dir, ignore_errors=True)
        except Exception:
            pass


def main() -> None:
    arcpy.env.overwriteOutput = True

    input_layer = arcpy.GetParameterAsText(0)
    do_shp = get_bool_param(1, False)
    do_kmz = get_bool_param(2, False)
    out_folder = arcpy.GetParameterAsText(3)

    if not input_layer:
        raise ValueError("Input Feature Layer is required.")
    if not do_shp and not do_kmz:
        raise ValueError("Select at least one output option: SHP and/or KMZ.")

    desc = arcpy.Describe(input_layer)

    # Prefer display name; fall back to dataset name
    raw_name = getattr(desc, "name", None) or os.path.basename(getattr(desc, "catalogPath", "") or "") or "export"
    base = sanitize_filename(raw_name)

    if out_folder and out_folder.strip():
        out_folder = out_folder.strip()
    else:
        out_folder = infer_output_folder(desc)

    if not os.path.isdir(out_folder):
        raise ValueError(f"Output folder does not exist or is not accessible: {out_folder}")

    arcpy.AddMessage(f"Input: {raw_name}")
    arcpy.AddMessage(f"Sanitized base name: {base}")
    arcpy.AddMessage(f"Output folder: {out_folder}")

    if do_shp:
        shp_path = export_shp(input_layer, out_folder, base)
        arcpy.AddMessage(f"✅ SHP: {shp_path}")

    if do_kmz:
        kmz_path = export_kmz(input_layer, out_folder, base)
        arcpy.AddMessage(f"✅ KMZ: {kmz_path}")


if __name__ == "__main__":
    try:
        main()
    except Exception as ex:
        arcpy.AddError(str(ex))
        raise
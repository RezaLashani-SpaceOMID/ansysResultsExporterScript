# -*- coding: utf-8 -*-
"""
ansysResultsExportScript.py v1.0
=====================
Exports every result of every analysis in ANSYS Mechanical (Modal, Random
Vibration, Static Structural, ... whatever exists in the tree) to PNG files.

- One sub-folder per analysis, named as the analysis appears in the tree.
- One PNG per result, named exactly as the result appears in the tree.

Export options (same as "New Figure or Image > Image to File"):
    - Current graphics display : off
    - Resolution               : Enhanced resolution (2:1)
    - Capture                  : Image and legends
    - Background               : White
    - Size                     : 1080 x 1080 px

Version handling:
    - Newer Mechanical releases: uses Graphics.ExportImage(path, format,
      settings) so the options above are applied.
    - ANSYS 2019 R2: that call is not available, so the script falls back to
      a plain screenshot (ExportScreenToImage); the options are NOT applied.
The console tells you which method was used.
"""

import os
import re
import clr
import System
from System.Reflection import BindingFlags
clr.AddReference("System.Windows.Forms")
from System.Windows.Forms import FolderBrowserDialog, DialogResult

# ----------------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------------
IMAGE_WIDTH = 1080
IMAGE_HEIGHT = 1080
FLAGS = BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance

# Solution-tree items whose category/name contains one of these words are not
# exported (they have no contour plot). Edit this list if needed.
SKIP_KEYWORDS = ["solutioninformation", "solution information", "chart",
                 "convergence", "figure", "image"]

# ----------------------------------------------------------------------------
# Mechanical objects (Model / Tree shortcuts do not exist in 2019 R2)
# ----------------------------------------------------------------------------
try:
    model = Model
except NameError:
    model = ExtAPI.DataModel.Project.Model
try:
    tree = Tree
except NameError:
    tree = ExtAPI.DataModel.Tree
gfx = ExtAPI.Graphics

SETTINGS_ERROR = [None]   # first error raised by the settings export (diagnostics)


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------
def choose_folder():
    """Ask the user for the output folder. Returns None if cancelled."""
    dlg = FolderBrowserDialog()
    dlg.Description = "Select folder for result images"
    if dlg.ShowDialog() != DialogResult.OK:
        return None
    return dlg.SelectedPath


def clean_name(name):
    """Replace characters that are not allowed in Windows file names."""
    return re.sub(r'[\\/:*?"<>|]', '_', name).strip()


def unique_path(folder, base_name):
    """Return folder/base_name.png, adding (2), (3)... if the name is taken."""
    path = os.path.join(folder, base_name + ".png")
    n = 2
    while os.path.exists(path):
        path = os.path.join(folder, "{0} ({1}).png".format(base_name, n))
        n += 1
    return path


def pick_enum(enum_type, *keywords):
    """Return the enum member matching a keyword: exact name first, then 'contains'."""
    names = list(System.Enum.GetNames(enum_type))
    for keyword in keywords:
        for name in names:
            if name.lower() == keyword.lower():
                return System.Enum.Parse(enum_type, name)
    for keyword in keywords:
        for name in names:
            if keyword.lower() in name.lower():
                return System.Enum.Parse(enum_type, name)
    return None


def find_export_image_method():
    """
    Look for an ExportImage(path, format, settings) overload on the graphics
    object (newer releases) or on the objects stored in its fields.
    Returns (target_object, MethodInfo) or (None, None).
    """
    targets = [gfx]
    try:
        for field in gfx.GetType().GetFields(FLAGS):
            try:
                value = field.GetValue(gfx)
                if value is not None:
                    targets.append(value)
            except Exception:
                pass
        for target in targets:
            for method in target.GetType().GetMethods(FLAGS):
                if method.Name == "ExportImage" and method.GetParameters().Length == 3:
                    return target, method
    except Exception:
        pass
    return None, None


def build_settings(settings_type):
    """Create the 'Image to File' settings object and fill it by property name."""
    settings = System.Activator.CreateInstance(settings_type)
    for prop in settings_type.GetProperties():
        if not prop.CanWrite:
            continue
        name = prop.Name.lower()
        ptype = prop.PropertyType
        if "current" in name:                                   # Current graphic display
            prop.SetValue(settings, False, None)
        elif "resol" in name and ptype.IsEnum:                  # Enhanced resolution (2:1)
            prop.SetValue(settings, pick_enum(ptype, "EnhancedResolution", "Enhanced"), None)
        elif ("capture" in name or "legend" in name) and ptype.IsEnum:   # Image and legends
            prop.SetValue(settings, pick_enum(ptype, "ImageAndLegend", "Legend"), None)
        elif "background" in name and ptype.IsEnum:             # White background
            prop.SetValue(settings, pick_enum(ptype, "White"), None)
        elif name == "width":
            prop.SetValue(settings, IMAGE_WIDTH, None)
        elif name == "height":
            prop.SetValue(settings, IMAGE_HEIGHT, None)
    return settings


EXPORT_TARGET, EXPORT_METHOD = find_export_image_method()


def export_image(path):
    """
    Export the current graphics view to 'path'.
    Returns "settings" if the Image-to-File settings were applied,
    "screenshot" if only a plain screen capture was possible, None on failure.
    """
    if EXPORT_METHOD is not None:
        try:
            params = EXPORT_METHOD.GetParameters()
            fmt = pick_enum(params[1].ParameterType, "PNG")
            settings = build_settings(params[2].ParameterType)
            EXPORT_METHOD.Invoke(EXPORT_TARGET, System.Array[object]([path, fmt, settings]))
            if os.path.exists(path):
                return "settings"
        except Exception as e:
            if SETTINGS_ERROR[0] is None:
                SETTINGS_ERROR[0] = str(e)
    try:
        gfx.ExportScreenToImage(path)
        if os.path.exists(path):
            return "screenshot"
    except Exception:
        pass
    return None


def is_skipped(obj):
    """True for solution-tree items that have no result plot."""
    try:
        text = (str(obj.DataModelObjectCategory) + " " + obj.Name).lower()
    except Exception:
        text = obj.Name.lower()
    return any(k in text for k in SKIP_KEYWORDS)


def collect_results(node):
    """Recursively collect all exportable results below a solution object."""
    found = []
    try:
        children = list(node.Children)
    except Exception:
        return found
    for child in children:
        if is_skipped(child):
            continue
        try:
            sub = list(child.Children)
        except Exception:
            sub = []
        if sub:
            found.extend(collect_results(child))   # group/folder: look inside
        else:
            found.append(child)
    return found


def activate(obj):
    try:
        tree.Activate([obj])
    except Exception:
        obj.Activate()


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------
def main():
    try:
        analyses = list(model.Analyses)
    except Exception:
        analyses = []
    if not analyses:
        print("No analyses found in the project tree. Nothing to export.")
        return

    root_dir = choose_folder()
    if root_dir is None:
        print("No folder selected. Script stopped.")
        return

    if EXPORT_METHOD is not None:
        print("Export method: ExportImage with Image-to-File settings")
    else:
        print("Export method: ExportImage not available in this version -> "
              "plain screenshots will be used")

    total_ok = 0
    total_all = 0
    screenshots = 0

    for analysis in analyses:
        try:
            solution = analysis.Solution
        except Exception:
            continue

        try:
            solution.EvaluateAllResults()
        except Exception:
            pass

        results = collect_results(solution)
        if not results:
            print("--- " + analysis.Name + ": no results, skipped ---")
            continue

        out_dir = os.path.join(root_dir, clean_name(analysis.Name))
        if not os.path.isdir(out_dir):
            os.makedirs(out_dir)
        print("--- " + analysis.Name + " (" + str(len(results)) + " results) ---")

        for result in results:
            total_all += 1
            path = ""
            try:
                activate(result)
                try:
                    gfx.Camera.SetFit()
                except Exception:
                    pass
                path = unique_path(out_dir, clean_name(result.Name))
                method = export_image(path)
            except Exception:
                method = None
            if method is None:
                print("FAILED:   " + analysis.Name + " / " + result.Name)
                continue
            total_ok += 1
            if method == "screenshot":
                screenshots += 1
            print("Exported: " + path)

    if total_all == 0:
        print("No results found in the tree. Nothing exported "
              "(make sure the analyses have been solved).")
        return

    print("Done. {0} of {1} images exported to {2}".format(total_ok, total_all, root_dir))
    if screenshots:
        print("Note: {0} image(s) were plain screenshots (Image-to-File settings "
              "not applied).".format(screenshots))
        if EXPORT_METHOD is not None and SETTINGS_ERROR[0]:
            print("ExportImage with settings failed with: " + SETTINGS_ERROR[0])


main()
# ANSYS Mechanical – Export All Results to PNG

An ACT/IronPython script for **ANSYS Mechanical** that exports the contour plot of
every result in the project tree (mode shapes, random vibration results, stresses, etc.)
as PNG images, named exactly as they appear in the tree.

On releases that provide `Graphics.ExportImage(path, format, settings)`, the script applies
the same options as **New Figure or Image > Image to File**. On **ANSYS 2019 R2**, where that
call is not available, it falls back to plain screenshots.

## Features

- Loops over **all analyses** in the tree (Modal, Random Vibration, Harmonic, Static Structural, ...)
- Creates **one sub-folder per analysis**, named as in the tree
- Creates **one PNG per result**, named as in the tree (characters not allowed in Windows
  file names are replaced by `_`; duplicate names get `(2)`, `(3)`, ...)
- Evaluates all results before exporting
- Skips items that have no contour plot (Solution Information, charts, ...)
- Does not crash on an empty tree or on analyses without results; it prints a message instead
- Detects the available export method automatically and reports it in the console
- Applies these Image-to-File options where supported:
  - Current graphics display: off
  - Resolution: Enhanced resolution (2:1)
  - Capture: Image and legends
  - Background: White
  - Size: 1080 x 1080 px

## Version support

| Mechanical version | Export method used | Image-to-File options applied |
|--------------------|--------------------|-------------------------------|
| Newer releases with `ExportImage(path, format, settings)` | `ExportImage` with settings | Yes |
| ANSYS 2019 R2 | `ExportScreenToImage` (plain screenshot) | No |

The newer-release route is untested by the author, because no newer installation was
available. The 2019 R2 fallback was developed against 2019 R2 feedback. If the settings
export fails on your version, the script falls back to a screenshot and prints the error at
the end (see Troubleshooting).

## Requirements

- ANSYS Mechanical (2019 R2 or newer)
- Solved analyses (results must exist in the Solution branches)

## Usage

1. Open your project in **ANSYS Mechanical**.
2. Activate the **ACT** toggle in the ribbon.
3. Create a **new snippet**.
4. Paste the contents of `Export_All_Results.py` into the new snippet.
5. Click the snippet and press **Enter** to run it.
6. Choose the output folder when the dialog appears.

The console first prints which export method will be used, then lists each exported file,
and finishes with a summary line.

## Output structure

```
<chosen folder>/
├── Modal/
│   ├── Total Deformation.png
│   ├── Total Deformation 2.png
│   └── ...
└── Random Vibration/
    ├── Directional Deformation.png
    └── ...
```

## Configuration

Edit the constants at the top of the script:

| Name            | Purpose                                                     |
|-----------------|-------------------------------------------------------------|
| `IMAGE_WIDTH`   | Image width in pixels (default 1080)                        |
| `IMAGE_HEIGHT`  | Image height in pixels (default 1080)                       |
| `SKIP_KEYWORDS` | Tree items containing these words are not exported          |

`IMAGE_WIDTH` and `IMAGE_HEIGHT` only apply when the settings-based export is available.

## How it works

1. `Model` and `Tree` are taken from `ExtAPI` when the shortcuts are missing (2019 R2).
2. The script searches the graphics object for an `ExportImage(path, format, settings)`
   method. The settings type is taken from that method's own signature, so no namespace
   import is needed.
3. For each analysis, `EvaluateAllResults()` is called, then the solution branch is walked
   recursively to collect all results.
4. Each result is activated in the tree, the camera is fitted, and the graphics view is exported:
   - With `ExportImage` and the settings object when available.
   - Otherwise (or if that call fails) with `ExportScreenToImage`.
5. Enum values are matched by exact name first (`EnhancedResolution`, `ImageAndLegend`,
   `White`, `PNG`), then by a "contains" match.

## Troubleshooting

- **Console says "plain screenshots will be used"**: `ExportImage` with settings does not
  exist in your version (expected on 2019 R2). Images use the current graphics window size
  and background. Maximizing the graphics pane before running gives larger screenshots.
- **Final note says "ExportImage with settings failed with: ..."**: the method exists but
  raised an error, and the script fell back to screenshots. Open an issue and include that
  message; it usually points to a property or enum name that differs in your version.
- **An unwanted item was exported, or a result is missing**: adjust `SKIP_KEYWORDS`.
- **"No results found in the tree"**: make sure the analyses have been solved.
- **A result shows `FAILED`**: it could not be evaluated or exported. The script continues
  with the next one.

## Known limitations

- Property and enum names for the settings (`CurrentGraphicsDisplay`, `Resolution`,
  `Capture`, `Background`, `Width`, `Height`) are matched by keyword, based on the newer
  API documentation as remembered by the author. They have not been verified on a newer
  release.
- On 2019 R2 the Image-to-File options cannot be applied by script, so output is a screenshot.
- The first run may include or exclude an item you did not expect, because results are
  detected from tree object categories and names.

## License

MIT (or choose your own).

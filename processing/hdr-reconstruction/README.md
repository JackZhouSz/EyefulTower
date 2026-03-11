# HDR Reconstruction Scripts

These scripts are used for creating HDR images from Eyeful Tower capture data, and various other tasks needed during the processing pipeline.

---

## Table of Contents

1. [hdrmerge.py](#hdrmerge)
2. [process_metashape.py](#process_metashape)
3. [compute_whitebalance.py](#compute_whitebalance)
4. [export_jpeg.py](#export_jpeg)
5. [downscale_images.py](#downscale_images)
6. [rename_images.py](#rename_images)
7. [metashape_to_krt.py](#metashape_to_krt)

---

## hdrmerge.py {#hdrmerge}

### Purpose

The `hdrmerge.py` script performs **RAW image debayering and HDR image merging**. It takes RAW images (e.g., Sony ARW files) from exposure brackets, debayers them using LibRaw's `dcraw_emu`, and merges them into HDR OpenEXR files.

### What It Does

1. **Reads RAW images** from a dataset directory and extracts EXIF metadata (f-number, exposure time, ISO)
2. **Groups images into exposure stacks** (either auto-detected or fixed number per bracket)
3. **Debayers RAW images** using `dcraw_emu` to produce 16-bit linear TIFF files
4. **Merges exposure stacks into HDR** using one of several methods:
   - `R-PPNE` (Robust Poisson Photon Noise Estimator) - default
   - `R-PPNE2` (2nd-gen robust PPNE)
   - `PPNE` (Original PPNE)
   - `Debevec` (Debevec & Malik 1997)
   - `Max` (pixel-wise maximum)
5. **Outputs HDR EXR files** with optional auto-exposure compensation
6. **Supports GPU acceleration** for faster HDR merging

### Prerequisites: dcraw_emu

The `hdrmerge.py` script requires **dcraw_emu**, a command-line tool from the [LibRaw](https://www.libraw.org/) library that handles RAW image debayering. This tool converts proprietary camera RAW formats (like Sony ARW) into standard 16-bit linear TIFF images.

#### What is dcraw_emu?

`dcraw_emu` is a sample application included with LibRaw that emulates the functionality of the original `dcraw` utility. It supports a wide range of RAW formats and provides options for:
- Color space conversion (sRGB, DCI-P3, Rec2020, etc.)
- White balance adjustment
- Demosaicing/debayering algorithms
- Output to TIFF format

#### How to Get dcraw_emu

`dcraw_emu` is included with LibRaw. You can download pre-built binaries or build from source at:

https://www.libraw.org/download

#### Specifying the dcraw_emu Path

Pass the path to `dcraw_emu` using the `--dcraw` argument:

```powershell
python hdrmerge.py --dcraw "C:\path\to\dcraw_emu.exe" ...
```

The script will also search for `dcraw_emu` in:
1. The current directory
2. The same directory as `hdrmerge.py`

### Example Usage

Here's how `hdrmerge.py` is typically invoked for Eyeful Tower captures:

```powershell
python "$env:CODE_PATH\hdrmerge.py" `
    -c Rec2020 `
    --no-rotate `
    --images-per-bracket 14 `
    --auto-exposure `
    --merge-method R-PPNE `
    --black-level 0.0 `
    --threshold 0.98 `
    --tempdir "$env:DATA_PATH\temp\" `
    --zip-logs `
    --delete-temp `
    --gpu `
    --workers 64 `
    --dcraw "$env:DCRAW_EMU_PATH" `
    --output-dir "$env:DATA_PATH\images\$i" `
    $env:CAPTURE_PATH\$i
```

This command:
- Uses Rec2020 color space
- Processes 14 images per exposure bracket
- Enables auto-exposure compensation
- Uses the PPNE merge method with 0.98 saturation threshold
- Uses GPU acceleration with 64 worker threads
- Cleans up temporary files and zips logs when done

---

## process_metashape.py {#process_metashape}

### Purpose

The `process_metashape.py` script provides **automated Agisoft Metashape processing** for datasets captured with the Eyeful Tower. It handles the complete photogrammetry pipeline and exports COLMAP, models, camera positions, and point clouds.

### What It Does

1. **Adds photos** with optional rig calibration support
2. **Configures camera calibration** based on rig type and optional KRT files
3. **Aligns photos** (feature matching and camera alignment)
4. **Applies coordinate transforms** (e.g., Z-up orientation)
5. **Detects markers and scale bars** for accurate metric reconstruction
6. **Filters tie points** by reconstruction uncertainty, projection accuracy, and reprojection error
7. **Builds depth maps and dense point clouds**
8. **Generates textured 3D mesh**
9. **Exports cameras, point clouds, and models** in various formats (XML, PLY, OBJ, COLMAP)

### Processing Stages

The script processes data in stages that can be run individually or in groups:

| Stage Group |                                         Stages Included                                        |
|-------------|------------------------------------------------------------------------------------------------|
| `all`       | `part1`, `save`, `filter`, `save`, `part2`                                                     |
| `part1`     | `addphotos`, `calib`, `align`, `transform`, `scalebars`                                        |
| `part2`     | `depthmaps`, `densecloud`, `model`, `texture`, `export`                                        |
| `filter`    | `filter_ru`, `optimizecameras`, `filter_pa`, `optimizecameras`, `filter_re`, `optimizecameras` |


### Example Usage

From the workflow script, Metashape processing is typically done in two parts:

**Part 1 - Photo alignment and initial calibration:**

```powershell
python "$env:CODE_PATH\process_metashape.py" `
    --rig eyeful3.0 `
    --stages part1 `
    --output "$DatasetName-part1.psx"
```

The output of part1 will be a Metashape project that has a point cloud and tie points. You can manually adjust things here, or let the full pipeline cntinue through.

**Part 2 - Filtering, dense reconstruction, and export:**

```powershell
python "$env:CODE_PATH\process_metashape.py" `
    --rig eyeful3.0 `
    --stages filter,part2 `
    --input "$DatasetName-part1.psx" `
    --filter-ru 50 `
    --filter-pa 5 `
    --filter-re 1 `
    --report
```

**COLMAP export (requires Metashape 2.2+):**

```powershell
python "$env:CODE_PATH\process_metashape.py" `
    --rig eyeful3.0 `
    --stages colmap `
    --input "$DatasetName-final.psx" `
    --report
```

COLMAP will be automatically exported in part 2, if you have a supported version of Metashape.

### Outputs

After processing, the script exports:
- `cameras.xml` - Camera calibration and poses in Metashape XML format
- `points.ply` - Tie points as a PLY point cloud
- `mesh.obj` - Textured mesh (if model export is enabled)
- `colmap/` - COLMAP-compatible camera format (Metashape 2.1.4+)
- `*-final.psx` - Final Metashape project file
- `*.pdf` - Processing report (if `--report` is enabled)

---

## compute_whitebalance.py {#compute_whitebalance}

### Purpose

The `compute_whitebalance.py` script computes **white balance coefficients** from color checker detection results. These coefficients are used to correct color casts in HDR images when exporting to JPEG. Color checker detections can be found in `cc_detections` in the root of the datasets.

### What It Does

1. **Reads color checker detection JSON files** produced by a color checker detector
2. **Extracts the white patch color** (patch 18) from each detection
3. **Filters out invalid detections** (missing patches, low confidence, outliers)
4. **Computes mean white patch color** in linear color space
5. **Outputs RGB white balance coefficients** to normalize colors

### Example Usage

```powershell
# Compute white balance from multiple detection files
python compute_whitebalance.py detection1.json detection2.json detection3.json

# Output: 1.023456,1.000000,0.987654
```

From the workflow script:

```powershell
$jsonFiles = Get-ChildItem "$env:DATA_PATH\cc_detections\*.json" -File | Select-Object -ExpandProperty FullName
$WB = python "$env:CODE_PATH\compute_whitebalance.py" $jsonFiles
```

### Output

The script outputs a single line with three comma-separated RGB coefficients:
```
1.023456,1.000000,0.987654
```

These coefficients can be passed directly to `export_jpeg.py` using the `--wb` argument.

---

## export_jpeg.py {#export_jpeg}

### Purpose

The `export_jpeg.py` script converts **HDR EXR images to JPEG** with white balance correction, exposure adjustment, and color space conversion.

### What It Does

1. **Reads HDR EXR images** from a source directory
2. **Applies white balance coefficients** to correct color casts
3. **Converts between color primaries** (Rec2020, P3, Rec709, XYZ)
4. **Applies sRGB tone mapping** for display
5. **Outputs high-quality JPEG images**

### Example Usage

```powershell
# Export with white balance correction
python export_jpeg.py --wb 1.02,1.00,0.98 -w 16 -o output_dir input_dir
```

From the workflow script:

```powershell
python "$env:CODE_PATH\export_jpeg.py" --wb $WB -w 16 -o "$env:DATA_PATH\images-jpeg\$i" "$env:DATA_PATH\images\$i"
```

---

## downscale_images.py {#downscale_images}

### Purpose

The `downscale_images.py` script **downscales images** to create lower-resolution versions. This is commonly used to create 4K, 2K, and 1K versions of full-resolution HDR images for faster processing or preview purposes.

### What It Does

1. **Reads images** from a source directory (recursively)
2. **Downscales by a specified factor** using appropriate interpolation
3. **Preserves directory structure** in the output
4. **Supports multiple formats** (EXR, JPEG, etc.)

### Example Usage

```powershell
# Downscale EXR images to half size (4K from 8K)
python downscale_images.py -e exr -s 0.5 -w 16 input_dir output_dir

# Downscale to quarter size (2K from 8K)
python downscale_images.py -e exr -s 0.25 -w 16 input_dir output_dir
```

```powershell
# Create 4K versions (half resolution)
python "$env:CODE_PATH\downscale_images.py" -e exr -s 0.5 -w 16 "$env:DATA_PATH\images\$i" "$env:DATA_PATH\images-4k\$i"

# Create 2K versions (quarter resolution)
python "$env:CODE_PATH\downscale_images.py" -e exr -s 0.25 -w 16 "$env:DATA_PATH\images\$i" "$env:DATA_PATH\images-2k\$i"

# Create 1K versions (eighth resolution)
python "$env:CODE_PATH\downscale_images.py" -e exr -s 0.125 -w 16 "$env:DATA_PATH\images\$i" "$env:DATA_PATH\images-1k\$i"
```

---

## rename_images.py {#rename_images}

### Purpose

The `rename_images.py` script **renames images** in subdirectories. It will append the current directories name to the filename. This makes it easier to see which camera an image comes from in the logs. It can also make the numbering consecutively.

The camras will name images sequentially, and it is possible some images will have names like _DSC0001(1).ARW with larger captures. Renaming them with consecutive will rename them so they have unique names.

### What It Does

1. **Iterates through camera subdirectories**
2. **Adds directory name as filename prefix** (e.g., `40/DSC1234.exr` → `40/40_DSC1234.exr`)
3. **Supports optional infix** between prefix and original name
4. **Can remove prefixes** (reverse operation)
5. **Can renumber images consecutively** (for Sony SDK transfers)
6. **Supports dry-run mode** to preview changes

### Example Usage

```powershell
# Add directory name as prefix to all images
python rename_images.py --prefix images/

# Preview changes without actually renaming
python rename_images.py --prefix --dry-run images/

# Add prefix with underscore infix
python rename_images.py --prefix --infix "_" images/
```

From the workflow script:

```powershell
python "$env:CODE_PATH\rename_images.py" --prefix "$env:DATA_PATH\images"
```

### Before/After Example

```
Before:                          After:
images/                          images/
├── 40/                          ├── 40/
│   ├── _DSC1234.exr             │   ├── 40_DSC1234.exr
│   └── _DSC1235.exr             │   └── 40_DSC1235.exr
├── 41/                          ├── 41/
│   ├── _DSC1234.exr             │   ├── 41_DSC1234.exr
│   └── _DSC1235.exr             │   └── 41_DSC1235.exr
```

---

## metashape_to_krt.py {#metashape_to_krt}

### Purpose

The `metashape_to_krt.py` script converts **Metashape camera XML exports to KRT JSON format**. KRT is a standardized camera format used by various rendering and reconstruction pipelines.

A benefit of the KRT format over the Metashape camera xml is the transforms for each camera are camera to world, instead of being relative to a master camera.

### What It Does

1. **Parses Metashape XML camera file** (`cameras.xml`)
2. **Extracts sensor calibration** (intrinsics, distortion coefficients)
3. **Extracts camera poses** (world-to-camera transforms)
4. **Handles camera rigs** with master/slave relationships
5. **Applies chunk transforms** (scale, rotation, translation)
6. **Outputs KRT JSON format** with all cameras

### KRT Format

The output JSON contains a `KRT` array with camera entries including:
- `cameraId` - Camera identifier (includes path like `"40/40_DSC1234"`)
- `width`, `height` - Image dimensions
- `K` - 3x3 intrinsic matrix (transposed)
- `T` - 4x4 world-to-camera transform (transposed)
- `distortion` - Distortion coefficients
- `distortionModel` - Either `"RadialAndTangential"` or `"Fisheye"`
- `projectionModel` - Projection model type
- `frameId` - Frame number (for multi-camera setups)

### Example Usage

```powershell
python metashape_to_krt.py cameras.xml cameras.json
```

From the workflow script:

```powershell
python "$env:CODE_PATH\metashape_to_krt.py" "$env:DATA_PATH\cameras.xml" "$env:DATA_PATH\cameras.json"
```

---

## Related Scripts

The `hdr-reconstruction` repository contains additional utility scripts that are often used in conjunction with the main scripts above:

- `create_split_json.py` - Create train/test split JSON files
- `extract_psnrs.py` - Parse PSNR metrics from log files and compute statistics per image/camera. Useful for evaluating reconstruction quality across datasets.
- `image_utils.py` - Shared utilities for image I/O and color conversion, including linear-to-sRGB transforms and color space matrices (XYZ to Rec2020/Rec709/P3).
- `utils.py` - Metashape helper utilities including KRT JSON loading, progress bar wrappers, scale bar error calculation, and object inspection tools.

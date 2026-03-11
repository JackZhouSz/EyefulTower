# Eyeful Dock Scripts

This is a collection of scripts for triggering file transfers and interactions with the Eyeful Tower.

## Scripts Overview

### `camera_transfer.py`

Python script that handles data transfer from the Eyeful cameras to the local machine.

**Features:**

- Checks robot connectivity via ping before attempting transfer
- Executes the transfer executable with specified parameters
- Supports retry logic for failed transfers
- Requires `CAPTURE_DIR` environment variable to be set

**Arguments:**

- `--robot-ip`: IP address of the robot (required)
- `--transfer-exe`: Path to the transfer executable (required)
- `--transfer-dataset`: Dataset name to pass to the transfer executable (required)
- `--transfer-num-cameras`: Expected number of cameras (optional)
- `--transfer-retries`: Number of retry attempts before failing (optional)

**Usage:**

```bash
python camera_transfer.py \
    --robot-ip 192.168.1.100 \
    --transfer-exe /path/to/transfer/exe \
    --transfer-dataset my_dataset \
    --transfer-num-cameras 14 \
    --transfer-retries 5
```

### `pipeline_runner.py`

Python script that automates the full HDR reconstruction workflow from data transfer through Metashape processing. This is the main orchestration script for processing Eyeful captures.

**Workflow:**

1. Validates required environment variables
2. Transfers data from robot cameras using `camera_transfer.py`
3. Runs HDR merge on captured images (folders 40-53)
4. Computes white balance from detections
5. Renames images using standard naming convention
6. Creates downscaled versions (4K, 2K, 1K) of images
7. Exports JPEG versions at all resolutions
8. Runs Metashape processing (Part 1, Part 2, and COLMAP export)
9. Creates split JSON and converts to KRT format

**Required Environment Variables:**

- `DATASETS_PATH`: Base path for processed datasets
- `HDR_REPO_PATH`: Path to the HDR processing repository
- `CAPTURE_DIR`: Base directory for raw captured data
- `DCRAW_EMU_PATH`: Path to the dcraw emulator executable
- `EYEFUL_DOCK_PATH`: Path to the eyeful_dock scripts directory
- `EYEFUL_IP`: IP address of the robot
- `TRANSFER_EXE`: Path to the transfer executable

**Required Conda Environments:**

- `hdrmerge-env`: Main processing environment

**Usage:**

```powershell
# Run the pipeline
python pipeline_runner.py dataset_name
```

**Example:**

```powershell
# Set required environment variables (or add to system environment)
$env:DATASETS_PATH = "D:\datasets"
$env:HDR_REPO_PATH = "C:\repos\EyefulTower\processing\hdr-processing"
$env:CAPTURE_DIR = "D:\captures"
$env:DCRAW_EMU_PATH = "C:\tools\dcraw_emu.exe"
$env:Eyeful_DOCK_PATH = "C:\repos\EyefulTower\processing\Eyeful_dock"
$env:Eyeful_IP = "192.168.1.100"
$env:TRANSFER_EXE = "C:\repos\EyefulTower\camera_driver\build\Release\transfer.exe"

# Activate environment and run
conda activate hdrmerge-env
python pipeline_runner.py dataset_name
```

**Output Structure:**

The script creates the following directory structure in `$DATASETS_PATH\<dataset-name>`:

- `images/` - Full resolution HDR EXR images
- `images-4k/` - 4K downscaled EXR images
- `images-2k/` - 2K downscaled EXR images
- `images-1k/` - 1K downscaled EXR images
- `images-jpeg/` - Full resolution JPEG exports
- `images-jpeg-4k/` - 4K JPEG exports
- `images-jpeg-2k/` - 2K JPEG exports
- `images-jpeg-1k/` - 1K JPEG exports
- `cc_detections/` - Color checker detection results
- `logs/` - Processing logs
- `temp/` - Temporary processing files
- `cameras.xml` - Metashape camera data
- `cameras.json` - KRT format camera data

### Other Scripts

### `capture_transfer_pipeline.py`

Wrapper script that orchestrates the camera transfer step. Pulls images from the robot.

```powershell
python capture_transfer_pipeline.py dataset_name
```

### `merge_pipeline.py`

Handles HDR merge of raw capture data. Merges exposure brackets into HDR images and optionally deletes the raw capture data afterwards.

```powershell
python merge_pipeline.py dataset_name
python merge_pipeline.py dataset_name --delete-capture
```

### `post_process_pipeline.py`

Runs all post-processing steps after HDR merge: white balance, image renaming, downscaling, JPEG export, Metashape reconstruction, and camera format conversion.

```powershell
python post_process_pipeline.py dataset_name
```


### `pipeline_utils.py`

Shared utility functions used across all pipeline scripts. Not intended to be run directly.

**Open Sourced Data Note**

The data we provide won't work out-of-the box with some of these scripts. The full res data is very large to provide in the means we are, however you can reacch out in this repo and we can provide it.

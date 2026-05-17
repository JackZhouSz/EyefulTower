# Copyright (c) Meta Platforms, Inc. and affiliates.

"""Post-processing pipeline - white balance, downscaling, JPEG export, Metashape, and COLMAP."""

import argparse
import glob
import os
import sys
from pathlib import Path

from pipeline_utils import (
    get_code_path,
    get_data_path,
    print_args,
    run_python,
    setup_env,
    validate_env_vars,
    validate_white_balance,
)

REQUIRED_VARS = [
    "DATASETS_PATH",
    "HDR_REPO_PATH",
    "CAPTURE_DIR",
    "DCRAW_EMU_PATH",
    "TRANSFER_EXE",
]


def run_post_process(dataset_name: str) -> None:
    """Run the post-processing pipeline.

    Args:
        dataset_name: Name of the dataset.
    """
    validate_env_vars(REQUIRED_VARS)

    code_path = get_code_path()
    data_path = get_data_path(dataset_name)

    setup_env(dataset_name)

    print("Environment variables loaded:")
    print(f"  DATA_PATH: {data_path}")
    print(f"  CAPTURE_PATH: {os.environ['CAPTURE_PATH']}")
    print(f"  CODE_PATH: {code_path}")

    data_path.mkdir(parents=True, exist_ok=True)
    os.chdir(data_path)

    ## Compute white balance
    print("\nComputing white balance...")
    json_files = sorted(glob.glob(str(data_path / "cc_detections" / "*.json")))
    if json_files:
        result = run_python(
            code_path / "compute_whitebalance.py",
            json_files,
            capture_output=True,
        )
        wb = validate_white_balance(result.stdout)
    else:
        print("No detection files found.")
        wb = "1.000000,1.000000,1.000000"

    print(f"White balance: {wb}")

    ## Create output directories
    for d in [
        "images-4k",
        "images-2k",
        "images-1k",
        "images-jpeg",
        "images-jpeg-4k",
        "images-jpeg-2k",
        "images-jpeg-1k",
    ]:
        (data_path / d).mkdir(exist_ok=True)

    ## Export to JPEG - Full resolution
    print("\nExporting to JPEG (full resolution)...")
    for i in range(40, 54):
        (data_path / "images-jpeg" / str(i)).mkdir(exist_ok=True)
        print(f"Processing folder {i}...")
        run_python(
            code_path / "export_jpeg.py",
            [
                "--wb",
                wb,
                "-w",
                "16",
                "-o",
                str(data_path / "images-jpeg" / str(i)),
                str(data_path / "images" / str(i)),
            ],
        )

    ## Downscale to 4K
    print("\nDownscaling images to 4k...")
    for i in range(40, 54):
        (data_path / "images-4k" / str(i)).mkdir(exist_ok=True)
        print(f"Processing folder {i}...")
        run_python(
            code_path / "downscale_images.py",
            [
                "-e",
                "exr",
                "-s",
                "0.5",
                "-w",
                "16",
                str(data_path / "images" / str(i)),
                str(data_path / "images-4k" / str(i)),
            ],
        )

    ## Export to JPEG - 4K
    print("\nExporting to JPEG (4K)...")
    for i in range(40, 54):
        (data_path / "images-jpeg-4k" / str(i)).mkdir(exist_ok=True)
        print(f"Processing folder {i}...")
        run_python(
            code_path / "export_jpeg.py",
            [
                "--wb",
                wb,
                "-w",
                "16",
                "-o",
                str(data_path / "images-jpeg-4k" / str(i)),
                str(data_path / "images-4k" / str(i)),
            ],
        )

    ## Downscale to 2K
    print("\nDownscaling images to 2K...")
    for i in range(40, 54):
        (data_path / "images-2k" / str(i)).mkdir(exist_ok=True)
        print(f"Processing folder {i}...")
        run_python(
            code_path / "downscale_images.py",
            [
                "-e",
                "exr",
                "-s",
                "0.25",
                "-w",
                "16",
                str(data_path / "images" / str(i)),
                str(data_path / "images-2k" / str(i)),
            ],
        )

    ## Export to JPEG - 2K
    print("\nExporting to JPEG (2K)...")
    for i in range(40, 54):
        (data_path / "images-jpeg-2k" / str(i)).mkdir(exist_ok=True)
        print(f"Processing folder {i}...")
        run_python(
            code_path / "export_jpeg.py",
            [
                "--wb",
                wb,
                "-w",
                "16",
                "-o",
                str(data_path / "images-jpeg-2k" / str(i)),
                str(data_path / "images-2k" / str(i)),
            ],
        )

    ## Downscale to 1K
    print("\nDownscaling images to 1K...")
    for i in range(40, 54):
        (data_path / "images-1k" / str(i)).mkdir(exist_ok=True)
        print(f"Processing folder {i}...")
        run_python(
            code_path / "downscale_images.py",
            [
                "-e",
                "exr",
                "-s",
                "0.125",
                "-w",
                "16",
                str(data_path / "images" / str(i)),
                str(data_path / "images-1k" / str(i)),
            ],
        )

    ## Export to JPEG - 1K
    print("\nExporting to JPEG (1K)...")
    for i in range(40, 54):
        (data_path / "images-jpeg-1k" / str(i)).mkdir(exist_ok=True)
        print(f"Processing folder {i}...")
        run_python(
            code_path / "export_jpeg.py",
            [
                "--wb",
                wb,
                "-w",
                "16",
                "-o",
                str(data_path / "images-jpeg-1k" / str(i)),
                str(data_path / "images-1k" / str(i)),
            ],
        )

    ## Process Metashape - Part 1
    print("\nProcessing Metashape - Part 1...")
    run_python(
        code_path / "process_metashape.py",
        [
            "--rig",
            "eyeful3.0",
            "--stages",
            "part1",
            "--output",
            f"{dataset_name}-part1.psx",
            str(data_path),
        ],
        log_file=Path("metashape-part1.log"),
    )

    ## Process Metashape - Part 2
    print("\nProcessing Metashape - Part 2...")
    run_python(
        code_path / "process_metashape.py",
        [
            "--rig",
            "eyeful3.0",
            "--stages",
            "filter,part2,colmap",
            "--input",
            f"{dataset_name}-part1.psx",
            "--filter-ru",
            "50",
            "--filter-pa",
            "5",
            "--filter-re",
            "1",
            "--report",
            str(data_path),
        ],
        log_file=Path("metashape-part2.log"),
    )

    ## Downscale Colmap
    print("\nDownscaling Colmap...")
    for scale, out_dir in [
        ("0.5", "images_2"),
        ("0.25", "images_4"),
        ("0.125", "images_8"),
    ]:
        run_python(
            code_path / "downscale_images.py",
            [
                "-e",
                "jpg",
                "-s",
                scale,
                "-w",
                "16",
                str(data_path / "colmap" / "images"),
                str(data_path / "colmap" / out_dir),
            ],
        )

    ## Create split JSON
    print("\nCreating split JSON...")
    run_python(
        code_path / "create_split_json.py",
        ["-i", "images-jpeg", "-e", "jpg", "45"],
    )

    ## Convert Metashape to KRT format
    print("\nConverting Metashape to KRT format...")
    run_python(
        code_path / "metashape_to_krt.py",
        [
            str(data_path / "cameras.xml"),
            str(data_path / "cameras.json"),
        ],
    )

    print("\n===== Workflow Completed Successfully =====")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Post-processing pipeline.")
    parser.add_argument("dataset_name", type=str, help="Name of the dataset")
    args = parser.parse_args()
    print_args(args)

    try:
        run_post_process(args.dataset_name)
    except KeyboardInterrupt:
        print("\nInterrupted by user. Exiting...")
        sys.exit(1)

# (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

"""HDR merge pipeline - merges bracketed exposures into HDR images."""

import argparse
import os
import shutil
import sys

from pipeline_utils import (
    get_capture_path,
    get_code_path,
    get_data_path,
    print_args,
    run_python,
    setup_env,
    validate_env_vars,
)

REQUIRED_VARS = [
    "DATASETS_PATH",
    "HDR_REPO_PATH",
    "CAPTURE_DIR",
    "DCRAW_EMU_PATH",
    "TRANSFER_EXE",
]


def run_merge(dataset_name: str, delete_capture: bool = False) -> None:
    """Run the HDR merge pipeline.

    Args:
        dataset_name: Name of the dataset.
        delete_capture: If True, delete capture folders after merge.
    """
    validate_env_vars(REQUIRED_VARS)

    code_path = get_code_path()
    capture_path = get_capture_path(dataset_name)
    data_path = get_data_path(dataset_name)
    dcraw_path = os.environ["DCRAW_EMU_PATH"]

    setup_env(dataset_name)

    print("Environment variables loaded:")
    print(f"  DATA_PATH: {data_path}")
    print(f"  CAPTURE_PATH: {capture_path}")
    print(f"  CODE_PATH: {code_path}")

    data_path.mkdir(parents=True, exist_ok=True)
    os.chdir(data_path)

    for d in ["logs", "temp", "images", "cc_detections"]:
        (data_path / d).mkdir(exist_ok=True)

    ## Run HDR merge
    for i in range(40, 54):
        print(f"Merging folder {i}...")
        result = run_python(
            code_path / "hdrmerge.py",
            [
                "-c",
                "Rec2020",
                "--no-rotate",
                "--images-per-bracket",
                "14",
                "--auto-exposure",
                "--merge-method",
                "R-PPNE",
                "--black-level",
                "0.0",
                "--threshold",
                "0.98",
                "--tempdir",
                str(data_path / "temp") + os.sep,
                "--zip-logs",
                "--delete-temp",
                "--gpu",
                "--workers",
                "64",
                "--dcraw",
                dcraw_path,
                "--output-dir",
                str(data_path / "images" / str(i)),
                str(capture_path / str(i)),
            ],
            check=False,
        )

        if result.returncode != 0:
            print("HDR merge failed. Not deleting folder.")
        elif delete_capture:
            print(f"Deleting capture folder {i}...")
            shutil.rmtree(capture_path / str(i), ignore_errors=True)

    ## Rename images
    print("\nRenaming images...")
    run_python(
        code_path / "rename_images.py",
        ["--prefix", str(data_path / "images")],
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="HDR merge pipeline.")
    parser.add_argument("dataset_name", type=str, help="Name of the dataset")
    parser.add_argument(
        "--delete-capture",
        action="store_true",
        help="Delete capture folders after merge",
    )
    args = parser.parse_args()
    print_args(args)

    try:
        run_merge(args.dataset_name, delete_capture=args.delete_capture)
    except KeyboardInterrupt:
        print("\nInterrupted by user. Exiting...")
        sys.exit(1)

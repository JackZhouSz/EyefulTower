# (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

"""Capture transfer pipeline - transfers images from the robot."""

import argparse
import os
import sys
from pathlib import Path

from pipeline_utils import print_args, run_python, validate_env_vars

REQUIRED_VARS = [
    "DATASETS_PATH",
    "HDR_REPO_PATH",
    "CAPTURE_DIR",
    "DCRAW_EMU_PATH",
    "TRANSFER_EXE",
    "EYEFUL_DOCK_PATH",
    "EYEFUL_IP",
]


def run_capture_transfer(dataset_name: str) -> None:
    """Run the capture transfer pipeline."""
    validate_env_vars(REQUIRED_VARS)

    eyeful_dock_path = Path(os.environ["EYEFUL_DOCK_PATH"])
    eyeful_ip = os.environ["EYEFUL_IP"]
    transfer_exe = os.environ["TRANSFER_EXE"]

    print("Running transfer pipeline...")
    run_python(
        eyeful_dock_path / "camera_transfer.py",
        [
            "--robot-ip",
            eyeful_ip,
            "--transfer-exe",
            transfer_exe,
            "--transfer-dataset",
            dataset_name,
            "--transfer-num-cameras",
            "14",
            "--transfer-retries",
            "3",
        ],
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Capture transfer pipeline - transfers images from the robot."
    )
    parser.add_argument("dataset_name", type=str, help="Name of the dataset")
    args = parser.parse_args()
    print_args(args)

    try:
        run_capture_transfer(args.dataset_name)
    except KeyboardInterrupt:
        print("\nInterrupted by user. Exiting...")
        sys.exit(1)

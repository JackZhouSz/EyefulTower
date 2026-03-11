# (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

"""Pipeline wrapper - orchestrates capture transfer, merge, and post-processing."""

import argparse
import sys

from capture_transfer_pipeline import run_capture_transfer
from merge_pipeline import run_merge
from pipeline_utils import print_args, validate_env_vars
from post_process_pipeline import run_post_process

REQUIRED_VARS = [
    "DATASETS_PATH",
    "HDR_REPO_PATH",
    "CAPTURE_DIR",
    "DCRAW_EMU_PATH",
    "TRANSFER_EXE",
]


def run_pipeline(
    dataset_name: str,
    delete_capture: bool = False,
    skip_transfer: bool = False,
) -> None:
    """Run the full pipeline: capture transfer, merge, and post-process.

    Args:
        dataset_name: Name of the dataset.
        delete_capture: If True, delete capture folders after merge.
        skip_transfer: If True, skip the capture transfer step.
    """
    validate_env_vars(REQUIRED_VARS)

    if skip_transfer:
        print("===== Skipping Camera Transfer =====")
    else:
        print("===== Starting Camera Transfer =====")
        run_capture_transfer(dataset_name)

    run_merge(dataset_name, delete_capture=delete_capture)

    run_post_process(dataset_name)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pipeline wrapper.")
    parser.add_argument("dataset_name", type=str, help="Name of the dataset")
    parser.add_argument(
        "--delete-capture",
        action="store_true",
        help="Delete capture folders after merge",
    )
    parser.add_argument(
        "--skip-transfer",
        action="store_true",
        help="Skip camera transfer step",
    )
    args = parser.parse_args()
    print_args(args)

    try:
        run_pipeline(
            args.dataset_name,
            delete_capture=args.delete_capture,
            skip_transfer=args.skip_transfer,
        )
    except KeyboardInterrupt:
        print("\nInterrupted by user. Exiting...")
        sys.exit(1)

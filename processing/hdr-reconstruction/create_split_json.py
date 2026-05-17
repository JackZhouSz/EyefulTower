# Copyright (c) Meta Platforms, Inc. and affiliates.


import argparse
import json
from pathlib import Path

parser = argparse.ArgumentParser(
    description="Script for creating a basic splits.json file."
)
parser.add_argument(
    "test_camera",
    metavar="test_camera",
    type=str,
    help="Comma-separated test camera ID(s)",
)
parser.add_argument(
    "-i",
    dest="images_path",
    type=Path,
    default="images",
    help="Image path (default: 'images')",
)
parser.add_argument(
    "-e",
    "--extension",
    type=str,
    default="exr",
    help="Extension of image files (default: 'exr')",
)
parser.add_argument(
    "-o",
    dest="output",
    type=str,
    default="splits.json",
    help="Output filename for splits file",
)
args = parser.parse_args()

path = args.images_path
assert path.exists(), f"Image path '{path}' not found."
all_exrs = sorted(path.rglob(f"*.{args.extension}"))
assert len(all_exrs) > 0, f"No images found in '{path}'"
all_names = [i.relative_to(path).with_suffix("").as_posix() for i in all_exrs]
test_cameras = tuple(args.test_camera.split(","))

splits = {
    "train": sorted([e for e in all_names if not e.startswith(test_cameras)]),
    "test": sorted([e for e in all_names if e.startswith(test_cameras)]),
}

# Remove empty splits
for name in list(splits.keys()):
    if len(splits[name]) == 0:
        print(f"Info: Split '{name}' is empty and will be removed.")
        del splits[name]

with open(args.output, "w", encoding="utf-8") as f:
    json.dump(splits, f, ensure_ascii=False, indent=4)

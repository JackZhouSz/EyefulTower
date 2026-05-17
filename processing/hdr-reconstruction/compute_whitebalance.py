# Copyright (c) Meta Platforms, Inc. and affiliates.

"""Script for computing white-balancing coefficients from detected color checkers."""

import argparse
import json
from pathlib import Path

import numpy as np
from image_utils import srgb2linear
from tqdm.contrib.concurrent import thread_map


def read_detection_json(path: Path) -> list[float]:
    """Reads a colorchecker detection JSON and returns the white patch RGB colors and confidence."""
    with open(path, "r", encoding="utf-8") as fh:
        detections = json.load(fh)

    patch = 18
    keypoints = np.array(detections.get("keypoints")[4 * patch : 4 * patch + 3])
    confidence = np.mean(keypoints[:, 2])

    colors = detections.get("colors_observed_rgb")[patch]
    return colors + [confidence]


parser = argparse.ArgumentParser(
    description="Computes white-balance parameters from colorchecker detections."
)
parser.add_argument(
    "detections",
    type=Path,
    nargs="+",
    help="Paths to one or more `detection.json` files",
)
parser.add_argument(
    "-s",
    "--sigma",
    type=float,
    default=2.0,
    help="Outlier threshold, in sigma (default: 2)",
)
parser.add_argument(
    "-t",
    "--target",
    type=float,
    help="Target intensity of the white patch (in linear color space)",
)
args = parser.parse_args()


# Read all detection.json files
dets = thread_map(
    read_detection_json, args.detections, max_workers=8, desc="Reading detections"
)
print()
print(f"- {len(dets)} detections loaded")

# Filter NaNs (missing white patches)
valid_dets = np.array([det for det in dets if not np.isnan(det).any()])
percentage = 100 * len(valid_dets) / len(dets)
print(f"- {len(valid_dets)} detections are valid ({percentage:.1f}%)")

# Filter by confidence
confident_dets = np.array([det for det in valid_dets if det[3] > 0.7])
percentage = 100 * len(confident_dets) / len(dets)
print(f"- {len(confident_dets)} detections are confident ({percentage:.1f}%)")
print(confident_dets)  # (r, g, b, confidence)

# Remove outliers (outside of 2 sigma in any channel)
while True:
    mean = np.mean(confident_dets[:, :3], axis=0)
    stdev = np.std(confident_dets[:, :3], axis=0)
    # print(f"mean = {mean}")
    # print(f"stdev = {stdev}")

    inliers = abs((confident_dets[:, :3] - mean) / stdev) < args.sigma
    inliers = np.logical_and.reduce(inliers, axis=1)
    inlier_dets = confident_dets[inliers]
    num_outliers = len(confident_dets) - len(inlier_dets)
    percentage = 100 * len(inlier_dets) / len(dets)
    print(
        f"- {len(inlier_dets)} detections are inliers ({percentage:.1f}%) after removing {num_outliers} outlier(s)"
    )
    confident_dets = inlier_dets

    if num_outliers == 0:
        break

print()
print(f"Mean patch color (sRGB)   : {mean} +/- {stdev}")

linear_colors = srgb2linear(confident_dets[:, :3])
mean = np.mean(linear_colors, axis=0)
stdev = np.std(linear_colors, axis=0)
print(f"Mean patch color (linear) : {mean} +/- {stdev}")

print()
print("White-balancing coefficients for matching intensity of the green color channel:")
print()

if args.target is not None:
    print(f"White-balancing coefficients for matching target value of {args.target}:")
    wb = args.target / mean
    print(f"{wb[0]:.6f},{wb[1]:.6f},{wb[2]:.6f}")
    print()
else:
    wb = mean[1] / mean
    print(f"{wb[0]:.6f},{wb[1]:.6f},{wb[2]:.6f}")

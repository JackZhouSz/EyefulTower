#!/usr/bin/env python3
# (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

import argparse
import re
from pathlib import Path

import numpy as np

parser = argparse.ArgumentParser()
parser.add_argument("dirs", type=Path, nargs="+")
parser.add_argument(
    "--csv", type=Path, help="save PSNRs as CSV file with this filename"
)
args = parser.parse_args()

stats = {}
for path in args.dirs:
    print(f"- Scanning '{path}'")
    if not path.is_dir():
        print("  Skipped (not a directory).\n")
        continue

    ## Find testing log file
    logs = sorted(path.rglob("*.log"))

    if len(logs) == 0:
        print("  No logs found. Check directory.\n")
        continue

    for log in logs:
        log_name = log.relative_to(path)
        print(f"  Found log '{log_name}'.", end="")

        ## Find 'PSNRs' line
        with open(log, encoding="utf-8") as fh:
            lines = fh.readlines()
            metrics_lines = [line for line in lines if line.startswith("PSNRs")]

        if len(metrics_lines) == 0:
            print("  No 'PSNRs' found in testing log.")
            print(f"  Check the log file '{log}'.\n")
            continue

        if len(metrics_lines) > 1:
            print("  Skipped as more than one 'PSNRs' line found.")
            print(f"  Check the log file '{log}'.\n")
            continue

        ## Extract metrics
        metrics = re.findall(r"^PSNRs = \[(.*?)\]$", metrics_lines[0])

        if len(metrics) == 0:
            print("  Could not parse 'PSNRs' line.")
            print(f"  Check the log file '{log}'.\n")
            continue

        stats[str(log_name)] = list(re.findall(r"(\d+\.\d+)", metrics[0]))
        mean = sum(float(e) for e in stats[str(log_name)]) / len(stats[str(log_name)])
        print(f"  PSNRs: {metrics[0]} -- mean: {mean:5.2f}")


## Compute some basic statistics
print("\nStatistics per image:")
num_images = max(len(e) for e in stats.values())
for index in range(num_images):
    values = [float(e[index]) for e in stats.values() if index < len(e)]
    print(f"  Image {index}. range = [{min(values):5.2f}, {max(values):5.2f}]", end="")
    print(f" -- mean: {np.mean(values):5.2f} +/- {np.std(values):5.2f}")

print("\nStatistics per camera:")
cameras = sorted({e.split("/")[0] for e in stats.keys() if "/" in e})
for camera in cameras:
    values = np.concatenate(
        [list(map(float, v)) for k, v in stats.items() if k.startswith(camera)], axis=0
    )
    print(
        f"  Camera {camera}. range = [{np.min(values):5.2f}, {np.max(values):5.2f}]",
        end="",
    )
    print(f" -- mean: {np.mean(values):5.2f} +/- {np.std(values):5.2f}")


## Highlight worst metrics
min_index = np.argmin([min(map(float, e)) for e in stats.values()])
min_file = list(stats.keys())[min_index]
min_psnrs = " ".join(list(stats.values())[min_index])
min_psnr = np.mean(list(map(float, list(stats.values())[min_index])))
print(f"\nWorst PSNR     :  {min_file} -- {min_psnrs} -- mean: {min_psnr:5.2f}")

mean_index = np.argmin([np.mean(list(map(float, e))) for e in stats.values()])
mean_file = list(stats.keys())[mean_index]
mean_psnrs = " ".join(list(stats.values())[mean_index])
mean_psnr = np.mean(list(map(float, list(stats.values())[mean_index])))
print(f"Worst Mean PSNR : {mean_file} -- {mean_psnrs} -- mean: {mean_psnr:5.2f}")


def natural_sort_key(s: str) -> list[int | str]:
    """
    Sorts strings naturally (aka "natsort"), e.g. ["1", "2", ..., "9", "10", "11", ...].
    """
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", s)]


## Print metrics (CSV)
if args.csv is not None:
    print(f"\nWriting CSV to '{args.csv}' ... ", end="")
    keys = sorted(stats.keys(), key=natural_sort_key)
    with open(args.csv, "w", encoding="utf-8") as fh:
        for key in keys:
            comma_sep = ",".join(str(e) for e in stats[key])
            fh.write(f"{key},{comma_sep}\n")
    print("Done.")

# ## Print metrics (human-readable)
# pad = max(20, *[len(e) for e in keys])
# print("Table:")
# for key in keys:
#     tab_sep = "\t".join(str(e) for e in stats[key])
#     print(f"{key.ljust(pad)}\t{tab_sep}")

print()

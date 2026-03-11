#!/usr/bin/env python3
# (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

"""Script for excluding selected images from a capture."""

# coding: utf-8
import argparse
import re
import shutil
from pathlib import Path

# from tqdm.contrib.concurrent import thread_map


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Script for excluding selected images."
    )
    parser.add_argument(
        "images_spec",
        metavar="images_spec",
        type=str,
        nargs="+",
        help="One or more comma-separated lists of image numbers or regular expressions.",
    )
    parser.add_argument(
        "-f",
        dest="filename_spec",
        type=str,
        default="{camera}_DSC{frame:04d}.{extension}",
        help="Template for image filenames",
    )
    parser.add_argument(
        "-o",
        "--output",
        dest="output",
        type=str,
        default="excluded-data",
        help="Directory to move excluded images to",
    )
    parser.add_argument(
        "--regex", action="store_true", help="Enables regular expression mode"
    )
    parser.add_argument(
        "-d",
        "--dry-run",
        action="store_true",
        help="Do not rename files, just print their old and new paths",
    )
    return parser.parse_args()


# def print_shell_command(src: Path, dst: Path):
#     src_path = str(src.relative_to(dataset_dir)).replace("\\", "/")
#     dst_path = str(dst.parent.relative_to(dataset_dir)).replace("\\", "/")
#     print(f"mv {src_path} {dst_path}/")


def move_file_dry_run(old: Path, new: Path):
    old_path = str(old.relative_to(dataset_dir)).replace("\\", "/")
    new_path = str(new.parent.relative_to(dataset_dir)).replace("\\", "/")
    print(f"  - {old_path} => {new_path}")


def move_file(old: Path, new: Path):
    print(f"  - Moved {old} => {new}")
    shutil.move(old, new)


if __name__ == "__main__":
    args = parse_arguments()
    print(args)

    work = []
    for images in args.images_spec:
        if args.regex:
            images_re = re.compile(images, re.IGNORECASE)
        else:
            images = [int(e) for e in images.split(",")]
            print(f"Excluding images: {images}")

        dataset_dir = Path.cwd()

        for directory, extension in [
            ("images", "exr"),
            ("images", "log"),
            ("images-merged", "exr"),
            ("images-merged", "log"),
            ("images-1k", "exr"),
            ("images-2k", "exr"),
            ("images-4k", "exr"),
            ("images-jpeg", "jpg"),
            ("images-jpeg-1k", "jpg"),
            ("images-jpeg-2k", "jpg"),
            ("images-jpeg-4k", "jpg"),
        ]:
            subdir: Path = dataset_dir / directory
            if not subdir.exists():
                print(
                    f"Warning: directory '{directory}' not found in '{dataset_dir}'. Skipping."
                )
                continue

            for src_dir in sorted(list(subdir.iterdir())):
                if not src_dir.is_dir():
                    continue

                camera = src_dir.name
                dst_dir = dataset_dir / args.output / directory / camera
                dst_dir.mkdir(parents=True, exist_ok=True)

                if args.regex:
                    for f in sorted(list(src_dir.glob(f"*.{extension}"))):
                        if images_re.match(f.stem):
                            work.append((f, dst_dir / f.name))
                else:
                    for frame in images:
                        filename = args.filename_spec.format(**locals())
                        if not (src_dir / filename).exists():
                            print(
                                f"  - Image '{src_dir / filename}' not found. Skipping."
                            )
                            continue

                        work.append((src_dir / filename, dst_dir / filename))

    move_fun = move_file_dry_run if args.dry_run else move_file
    # thread_map(lambda x: move_fun(*x), work, max_workers=1, desc="Excluding images")
    for x in work:
        move_fun(*x)

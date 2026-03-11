# (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

import argparse
import os
from collections.abc import Callable
from pathlib import Path


def add_dirname_as_prefix(
    cam_dir: Path,
    rename_fun: Callable[[Path, Path], None],
    infix: str = "",
) -> None:
    """Adds the name of `cam_dir` as a prefix to each file in `cam_dir` (with optional `infix`) by calling `rename_fun`."""
    if not cam_dir.is_dir():
        print(f"Warning: '{cam_dir}' is not a directory. Skipping.")
        return

    for old in sorted(cam_dir.iterdir()):
        if old.is_file():
            new = old.parent / (old.parent.name + infix + old.name)
            rename_fun(old, new)


def remove_dirname_as_prefix(
    cam_dir: Path,
    rename_fun: Callable[[Path, Path], None],
) -> None:
    """Removes the name of `cam_dir` as a prefix from each file in `cam_dir` by calling `rename_fun`."""
    if not cam_dir.is_dir():
        print(f"Warning: '{cam_dir}' is not a directory. Skipping.")
        return

    for old in sorted(cam_dir.iterdir()):
        if old.is_file():
            if old.name.startswith(old.parent.name):
                new = old.parent / old.name[len(old.parent.name) :]
                rename_fun(old, new)


def rename_photos_consecutively(
    cam_dir: Path,
    rename_fun: Callable[[Path, Path], None],
) -> None:
    """Renames images transferred via the Sony SDK to have consecutive filenames.
    For example, 0001..4000 stay the same, but 0001(1)..1234(1) are renamed to 4001..5234.
    """
    if not cam_dir.is_dir():
        print(f"Warning: '{cam_dir}' is not a directory. Skipping.")
        return

    for extension in ["ARW", "JPG"]:
        for frame in range(1, 4001):
            src = cam_dir / f"_DSC{frame:04d}.{extension}"
            if not src.exists():
                print(f"Warning: '{src}' not found. Will skip renaming.")
                return
            # There's no need rename the first 4000 images as they have the correct name.

        for frame in range(1, 4000):
            src = cam_dir / f"_DSC{frame:04d}(1).{extension}"
            dst = cam_dir / f"_DSC{4000 + frame:04d}.{extension}"

            if src.exists():
                if dst.exists():
                    print(f"Warning: file {dst} already exists. Skipping.")
                else:
                    rename_fun(src, dst)
            else:
                break  # End of capture


def renumber_photos(
    cam_dir: Path,
    rename_fun: Callable[[Path, Path], None],
) -> None:
    """Renumbers images sequentially, starting from 1."""
    if not cam_dir.is_dir():
        print(f"Warning: '{cam_dir}' is not a directory. Skipping.")
        return

    all_frames = sorted({f.stem for f in cam_dir.iterdir() if f.is_file()})

    for new_frame, old_frame in enumerate(all_frames, start=1):
        for extension in ["ARW", "JPG"]:
            src = cam_dir / f"{old_frame}.{extension}"
            dst = cam_dir / f"_REN{new_frame:04d}.{extension}"

            if dst.exists():
                print(f"Warning: file {dst} already exists. Skipping.")
            else:
                rename_fun(src, dst)


def rename_dry_run(old: Path, new: Path) -> None:
    """Prints a rename without performing it."""
    print(f"  - {old} => {new}")


def rename_file(old: Path, new: Path) -> None:
    """Renames a file and prints the operation."""
    print(f"  - Renamed {old} => {new}")
    os.rename(old, new)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Script for renaming images in sub-directories."
    )
    parser.add_argument(
        "directory", type=Path, help="Directory containing directories of images"
    )
    parser.add_argument(
        "-p",
        "--prefix",
        action="store_true",
        help="Use directory name as filename prefix",
    )
    parser.add_argument(
        "--remove-prefix",
        action="store_true",
        help="Remove the directory name from filenames",
    )
    parser.add_argument(
        "-c", "--consecutive", action="store_true", help="Renumber images consecutively"
    )
    parser.add_argument(
        "-n", "--renumber", action="store_true", help="Renumber images from 1 onwards"
    )
    parser.add_argument(
        "-i",
        "--infix",
        type=str,
        default="",
        help="Infix for combining prefix and existing name",
    )
    parser.add_argument(
        "-d",
        "--dry-run",
        action="store_true",
        help="Do not rename files, just print their old and new paths",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_arguments()
    rename_fun = rename_dry_run if args.dry_run else rename_file
    assert args.directory.exists(), f"Path '{args.directory}' not found."
    assert args.directory.is_dir(), f"Path '{args.directory}' is not a directory."

    for cam_dir in sorted(args.directory.iterdir()):
        if not cam_dir.is_dir():
            continue

        print()
        print(f"cam_dir = {cam_dir}")

        if args.consecutive:
            rename_photos_consecutively(cam_dir, rename_fun)

        if args.renumber:
            renumber_photos(cam_dir, rename_fun)

        if args.prefix:
            add_dirname_as_prefix(cam_dir, rename_fun, args.infix)

        if args.remove_prefix:
            remove_dirname_as_prefix(cam_dir, rename_fun)

# Copyright (c) Meta Platforms, Inc. and affiliates.

"""Script for downscaling images."""

import os
from pathlib import Path

import cv2

os.environ["OPENCV_IO_ENABLE_OPENEXR"] = "1"


def downsample_image(src: Path, dst: Path, scale: float = 1.0) -> None:
    """Downscales a single input image."""

    if dst.exists():
        print(f"Warning: File '{dst}' exists. Skipped.")
        return

    if not dst.parent.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)

    img = cv2.imread(str(src), cv2.IMREAD_UNCHANGED)

    if scale != 1.0:
        interpolation = cv2.INTER_AREA if scale < 1.0 else cv2.INTER_LINEAR
        img = cv2.resize(
            img, dsize=None, fx=scale, fy=scale, interpolation=interpolation
        )

    if dst.suffix == ".exr":  # uncompressed EXR
        cv2.imwrite(
            str(dst),
            img,
            params=[cv2.IMWRITE_EXR_COMPRESSION, cv2.IMWRITE_EXR_COMPRESSION_NO],
        )
    elif dst.suffix == ".jpg":  # high-quality JPEG
        cv2.imwrite(str(dst), img, params=[cv2.IMWRITE_JPEG_QUALITY, 100])
    else:  # Try saving using OpenCV defaults
        cv2.imwrite(str(dst), img)


if __name__ == "__main__":
    import argparse

    from tqdm.contrib.concurrent import thread_map

    ## Parse command line arguments.
    parser = argparse.ArgumentParser(description="Tool for downscaling images.")
    parser.add_argument(
        "src_path", metavar="src_path", type=Path, help="Source path (recursive)."
    )
    parser.add_argument(
        "dst_path", metavar="dst_path", type=Path, help="Output path for images."
    )
    parser.add_argument(
        "-s",
        "--scale",
        default=1.0,
        type=float,
        help="Scale factor for resizing images (default: 1)",
    )
    parser.add_argument(
        "-e",
        "--extension",
        type=str,
        default="exr",
        help="Extension of image files (default: exr)",
    )
    parser.add_argument(
        "-w",
        "--workers",
        default=16,
        type=int,
        help="Number of worker threads (default: 16)",
    )

    args = parser.parse_args()
    print("Using arguments:")
    for k, v in vars(args).items():
        print(f"  - {k} = {v}")
    print()

    if args.dst_path is None:
        print(f"Info: Using source path '{args.src_path}' as output path.")
        args.dst_path = args.src_path

    src_paths = sorted(args.src_path.glob(f"**/*.{args.extension}"))
    work = [
        {
            "src": src_path,
            "dst": args.dst_path / src_path.relative_to(args.src_path),
            "scale": args.scale,
        }
        for src_path in src_paths
    ]

    if len(work) == 0:
        print("Warning: No images found. Check the path.")
    else:
        ## Parallel processing
        thread_map(
            lambda x: downsample_image(**x),
            work,
            max_workers=args.workers,
            desc=f"Downsampling {args.extension} images",
        )

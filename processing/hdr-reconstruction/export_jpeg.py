# Copyright (c) Meta Platforms, Inc. and affiliates.

"""Script for converting EXR images to JPEG images."""

import os
from pathlib import Path

import cv2
import numpy as np
from image_utils import (
    linear2srgb,
    MAT_XYZ_TO_P3,
    MAT_XYZ_TO_REC2020,
    MAT_XYZ_TO_REC709,
)

os.environ["OPENCV_IO_ENABLE_OPENEXR"] = "1"


def convert_exr_to_jpg(
    src: Path,
    dst: Path,
    coeffs: np.ndarray,
    scale: float = 1.0,
    input_primaries: str = "Rec2020",
    output_primaries: str = "Rec2020",
) -> None:
    """Converts an EXR image to a JPEG image using sRGB tone mapping,
    with per-channel white-balance coefficient, optional image scaling,
    and configurable input/output color primaries."""

    ## Sanity checks
    if dst.exists():
        print(f"Warning: File '{dst}' exists. Skipped.")
        return
    if not dst.parent.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)

    ## Read the input EXR image, and rescale if necessary
    img = cv2.imread(str(src), cv2.IMREAD_UNCHANGED)
    if scale != 1.0:
        interpolation = cv2.INTER_AREA if scale < 1.0 else cv2.INTER_LINEAR
        img = cv2.resize(
            img, dsize=None, fx=scale, fy=scale, interpolation=interpolation
        )

    ## Convert color primaries if necessary
    if input_primaries != output_primaries:
        if input_primaries == "XYZ":
            input_to_xyz = np.eye(3, dtype=np.float32)
        elif input_primaries == "Rec2020":
            input_to_xyz = np.linalg.inv(MAT_XYZ_TO_REC2020)
        elif input_primaries == "P3":
            input_to_xyz = np.linalg.inv(MAT_XYZ_TO_P3)
        elif input_primaries == "Rec709":
            input_to_xyz = np.linalg.inv(MAT_XYZ_TO_REC709)
        else:
            raise ValueError(f"Input primaries '{input_primaries}' not supported.")

        if output_primaries == "XYZ":
            xyz_to_output = np.eye(3, dtype=np.float32)
        elif output_primaries == "Rec2020":
            xyz_to_output = MAT_XYZ_TO_REC2020
        elif output_primaries == "P3":
            xyz_to_output = MAT_XYZ_TO_P3
        elif output_primaries == "Rec709":
            xyz_to_output = MAT_XYZ_TO_REC709
        else:
            raise ValueError(f"Output primaries '{output_primaries}' not supported.")

        input_to_output = xyz_to_output @ input_to_xyz
        img = (img.reshape([-1, 3]) @ input_to_output.T).reshape(img.shape)
        img = img.clip(min=0.0)

    ## Apply white-balance coefficients (in target color space)
    img = np.einsum("ijk,k->ijk", img, coeffs)

    ## Apply sRGB transfer curve
    img = linear2srgb(img)

    ## Save output as high-quality JPEG
    img = np.clip(255 * img, 0.0, 255.0).astype(np.uint8)
    cv2.imwrite(str(dst), img, params=[cv2.IMWRITE_JPEG_QUALITY, 100])


if __name__ == "__main__":
    import argparse

    from tqdm.contrib.concurrent import thread_map

    primaries = ["XYZ", "Rec2020", "P3", "Rec709"]

    ## Parse command line arguments.
    parser = argparse.ArgumentParser(
        description="Tool for exporting EXR images as JPEG images."
    )
    parser.add_argument(
        "src_path", metavar="src_path", type=Path, help="Source path (recursive)."
    )
    parser.add_argument(
        "-e",
        "--exposure",
        default=0.0,
        type=float,
        help="Exposure compensation: 1 == twice as bright (default: 0)",
    )
    parser.add_argument(
        "-s",
        "--scale",
        default=1.0,
        type=float,
        help="Scale factor for resizing images (default: 1)",
    )
    parser.add_argument(
        "--input-primaries",
        default="Rec2020",
        choices=primaries,
        help="Color space primaries of the input EXR images (default: Rec2020)",
    )
    parser.add_argument(
        "--output-primaries",
        default="Rec2020",
        choices=primaries,
        help="Color space primaries of the output JPEG images (default: Rec2020)",
    )
    parser.add_argument(
        "--wb",
        default="1,1,1",
        type=str,
        help="RGB white-balance coefficients (default: 1,1,1)",
    )
    parser.add_argument(
        "-w",
        "--workers",
        default=8,
        type=int,
        help="Number of worker threads (default: 8)",
    )
    parser.add_argument("-o", dest="dst_path", type=Path, help="Output path for JPEGs")

    args = parser.parse_args()
    print("Using arguments:")
    for k, v in vars(args).items():
        print(f"  - {k} = {v}")
    print()

    if args.dst_path is None:
        print(f"Info: Using source path '{args.src_path}' as output path.")
        args.dst_path = args.src_path

    # Combine exposure and white balance into per-channel coefficients.
    wb = np.array([float(e) for e in args.wb.split(",")], dtype=np.float32)
    coeffs = (2**args.exposure) * wb[::-1]  # convert RGB coeffs to BGR to match OpenCV

    src_paths = sorted(args.src_path.glob("**/*.exr"))
    work = [
        {
            "src": src_path,
            "dst": args.dst_path
            / src_path.with_suffix(".jpg").relative_to(args.src_path),
            # "dst": args.dst_path / src_path.with_suffix(".exr").name,
            "coeffs": coeffs,
            "scale": args.scale,
            "input_primaries": args.input_primaries,
            "output_primaries": args.output_primaries,
        }
        for src_path in src_paths
    ]

    if len(work) == 0:
        print("Warning: No images found. Check the path.")
    else:
        ## Parallel processing
        # 8 workers: 1368 EXRs in 27:09 mins = 1.2/second -- not IO bottlenecked?
        thread_map(
            lambda x: convert_exr_to_jpg(**x),
            work,
            max_workers=args.workers,
            desc="Exporting EXR images to JPEG",
        )

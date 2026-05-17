# Copyright (c) Meta Platforms, Inc. and affiliates.

"""Utilities for image loading, writing and color conversion."""

import os
from pathlib import Path
from typing import Final

import cv2
import numpy as np

os.environ["OPENCV_IO_ENABLE_OPENEXR"] = "1"

# Source of matrix: `colour.RGB_COLOURSPACES["ITU-R BT.2020"].matrix_XYZ_to_RGB`
MAT_XYZ_TO_REC2020: Final[np.ndarray] = np.array(
    [
        [1.7166511880, -0.3556707838, -0.2533662814],
        [-0.6666843518, 1.6164812366, 0.0157685458],
        [0.0176398574, -0.0427706133, 0.9421031213],
    ],
    dtype=np.float32,
)

# Source of matrix: `colour.RGB_COLOURSPACES["sRGB"].matrix_XYZ_to_RGB`
MAT_XYZ_TO_REC709: Final[np.ndarray] = np.array(
    [
        [3.2404542, -1.5371385, -0.4985314],
        [-0.9692660, 1.8760108, 0.0415560],
        [0.0556434, -0.2040259, 1.0572252],
    ],
    dtype=np.float32,
)

# Source of matrix: `colour.RGB_COLOURSPACES["Display P3"].matrix_XYZ_to_RGB`
MAT_XYZ_TO_P3: Final[np.ndarray] = np.array(
    [
        [2.49349691, -0.93138362, -0.40271078],
        [-0.82948897, 1.76266406, 0.02362469],
        [0.03584583, -0.07617239, 0.95688452],
    ],
    dtype=np.float32,
)


def linear2srgb(img: np.ndarray) -> np.ndarray:
    """Transforms image colours from linear RGB to sRGB tone curve."""
    linear_part = 12.92 * img  # linear part of sRGB curve
    exp_part = 1.055 * (np.maximum(img, 0.0) ** (1 / 2.4)) - 0.055
    return np.where(img <= 0.0031308, linear_part, exp_part)


def srgb2linear(img: np.ndarray) -> np.ndarray:
    """Transforms image colours from sRGB tone curve to linear RGB."""
    linear_part = img / 12.92  # linear part of sRGB curve
    exp_part = ((np.maximum(img, 0.04045) + 0.055) / 1.055) ** 2.4
    return np.where(img <= 0.04045, linear_part, exp_part)


def save_linear_as_exr(img: np.ndarray, filename: Path | str) -> None:
    """Saves a linear RGB image as an uncompressed EXR image."""
    if img.dtype != np.float32:
        img = img.astype(np.float32)

    params = [cv2.IMWRITE_EXR_COMPRESSION, cv2.IMWRITE_EXR_COMPRESSION_NO]
    cv2.imwrite(str(filename), img, params=params)


def save_linear_as_jpeg(
    img: np.ndarray,
    filename: Path | str,
    quality: int = 100,
) -> None:
    """Saves a linear RGB image as a JPEG image with an sRGB transfer curve."""
    img = np.clip(255 * linear2srgb(img), 0.0, 255.0).astype(np.uint8)
    cv2.imwrite(str(filename), img, params=[cv2.IMWRITE_JPEG_QUALITY, quality])


def add_label_centered(
    img: np.ndarray,
    text: str,
    font_scale: float = 1.0,
    thickness: int = 2,
    alignment: str = "top",
    color: tuple[int, int, int] = (0, 255, 0),
) -> np.ndarray:
    """Adds label to an image

    Args:
        img: Input image.
        text: Text to be added on the image.
        font_scale: The scale of the font.
        thickness: Thickness of the lines.
        alignment: Can be `top` or `bottom`. The alignment of the text.
        color: The color of the text. Assumes the same color space as `img`.
    """
    font = cv2.FONT_HERSHEY_SIMPLEX
    textsize = cv2.getTextSize(text, font, font_scale, thickness=thickness)[0]
    img = img.astype(np.uint8).copy()

    if alignment == "top":
        cv2.putText(
            img,
            text,
            ((img.shape[1] - textsize[0]) // 2, 50),
            font,
            font_scale,
            color,
            thickness=thickness,
            lineType=cv2.LINE_AA,
        )
    elif alignment == "bottom":
        cv2.putText(
            img,
            text,
            ((img.shape[1] - textsize[0]) // 2, img.shape[0] - textsize[1]),
            font,
            font_scale,
            color,
            thickness=thickness,
            lineType=cv2.LINE_AA,
        )
    else:
        raise ValueError("Unknown text alignment")

    return img

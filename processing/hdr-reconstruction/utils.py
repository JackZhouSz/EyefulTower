# Copyright (c) Meta Platforms, Inc. and affiliates.

"""Tools for inspecting Metashape objects and visualising progress."""

import json
from collections import OrderedDict
from collections.abc import Generator
from pathlib import Path
from typing import Any

import cv2
import Metashape  # pylint: disable=E0401
import numpy as np
from tqdm import tqdm


if not Metashape.License().valid:
    raise RuntimeError("Metashape license is not valid. Please fix.")


def dump(obj: object) -> None:
    """Prints an objects's attributes."""
    for attr in dir(obj):
        if attr.startswith("__"):
            continue
        print(f"obj.{attr} = {getattr(obj, attr)}")


def dump_yield(obj: object) -> Generator[str, None, None]:
    """Generates string representations of an objects's attributes."""
    for attr in dir(obj):
        if attr.startswith("__"):
            continue
        yield f"obj.{attr} = {getattr(obj, attr)}"


def diff(object_a: object, object_b: object, verbose: bool = False) -> None:
    """Compares the attributes of two objects (rather naively, in order)."""
    for i, j in zip(dump_yield(object_a), dump_yield(object_b)):
        if i != j:
            print("< " + i)
            print("> " + j)
        elif verbose:
            print("= " + i)


class TqdmProgressBar(tqdm):
    """tqdm wrapper that exposes a call_back function for use with Metashape."""

    def __init__(self, **tqdm_kwargs: Any) -> None:
        super().__init__(
            total=100.0,
            unit="%",
            ascii=True,
            ncols=100,
            smoothing=0.1,
            **tqdm_kwargs,
        )
        self.previous = 0

    def update_to(self, value: float) -> None:
        """Callback function that expects a progress value in percent."""
        rounded = int(value + 0.5)
        if rounded > self.previous:
            delta = rounded - self.previous
            self.previous = rounded
            self.update(delta)

    def close(self, **kwargs: Any) -> None:
        self.update_to(self.total)
        super().close(**kwargs)


def load_krt_json(krt_file: str | Path) -> OrderedDict[str, dict[str, Any]]:
    """Reads a KRT camera calibration file."""
    with open(krt_file, encoding="utf-8") as fid:
        data = json.load(fid)["KRT"]
        krt = OrderedDict()
        for cam in data:
            name = cam["cameraId"]
            krt[name] = dict(cam)
            krt[name]["K"] = np.array(cam["K"]).T
            krt[name]["T"] = np.array(cam["T"]).T
            krt[name]["distortion"] = np.array(cam["distortion"])

    return krt


def calculate_total_error(scale: float, doc: "Metashape.Document") -> float:
    """Calculate total error for a given scale value."""
    total_error = 0.0
    for scalebar in doc.chunk.scalebars:
        point0 = None
        point1 = None
        if isinstance(scalebar.point0, Metashape.Marker):
            point0 = scalebar.point0.position
        if isinstance(scalebar.point0, Metashape.Camera):
            point0 = scalebar.point0.center
        if isinstance(scalebar.point1, Metashape.Marker):
            point1 = scalebar.point1.position
        if isinstance(scalebar.point1, Metashape.Camera):
            point1 = scalebar.point1.center
        estimated_distance = (point1 - point0).norm() * scale
        reference_distance = scalebar.reference.distance
        error_distance = estimated_distance - reference_distance
        total_error += error_distance
    return total_error


def binary_search_optimal_scale(
    low: float,
    high: float,
    doc: "Metashape.Document",
    tolerance: float = 1e-9,
    max_iterations: int = 100,
) -> tuple[float, float]:
    """
    Find the optimal scale using binary search to minimize |total_error|.
    Since total_error is linear in scale, we search for the scale where error crosses zero.
    """
    iteration = 0
    while iteration < max_iterations and (high - low) > tolerance:
        mid = (low + high) / 2.0
        error = calculate_total_error(mid, doc)
        if abs(error) < tolerance:
            return mid, error
        # Since error is linear in scale and increases with scale,
        # if error > 0, optimal scale is lower; if error < 0, optimal scale is higher
        if error > 0:
            high = mid
        else:
            low = mid
        iteration += 1
    # Return the midpoint of final range
    optimal_scale = (low + high) / 2.0
    return optimal_scale, calculate_total_error(optimal_scale, doc)


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

# Copyright (c) Meta Platforms, Inc. and affiliates.

import argparse
from pathlib import Path

import cv2
import numpy as np
from image_utils import add_label_centered
from tqdm import tqdm


parser = argparse.ArgumentParser(
    description="Exports a collage video from images in subdirs."
)
parser.add_argument(
    "src_dir",
    nargs="?",
    default=Path.cwd() / "images-jpeg-2k",
    type=Path,
    help="Source path.",
)
parser.add_argument("--fps", default=4, type=float, help="Framerate (default: 4)")
parser.add_argument(
    "--labels",
    default=True,
    action=argparse.BooleanOptionalAction,
    help="Show labels for image filenames",
)

args = parser.parse_args()
print("Using arguments:")
for k, v in vars(args).items():
    print(f"  - {k} = {v}")
print()


video_size = (3840, 2160)

camera_dirs = sorted([f for f in args.src_dir.glob("*") if f.is_dir()])
images = [sorted(c.glob("*.jpg")) for c in camera_dirs]  # cameras x image_paths

## Restore missing filenames, so they can be blanked in the collage
stems = sorted(
    {e.name.split("_")[-1] for i in images for e in i}
)  # list of "DSC1234.jpg" etc.
images = [
    [cam_dir / f"{cam_dir.name}_{stem}" for stem in stems] for cam_dir in camera_dirs
]

layout = None
video = None
image_size = None
framesets = list(zip(*images))  # frames x cameras x path
for frameset in tqdm(framesets, "Creating collage.mp4"):
    frames = [
        cv2.imread(str(frame_path)) if frame_path.exists() else None
        for frame_path in frameset
    ]

    if layout is None:
        # Find best grid layout
        target_aspect = video_size[0] / video_size[1]
        frame = next(f for f in frames if f is not None)  # first non-None frame
        image_width = frame.shape[1]
        image_height = frame.shape[0]
        for cols in range(2, len(frames) + 1):
            rows = int(np.ceil(len(frames) / cols))
            collage_width = cols * image_width
            collage_height = rows * image_height
            aspect = collage_width / collage_height
            if layout is None:
                layout = (rows, cols)
                best_aspect = aspect
            elif abs(aspect - target_aspect) < abs(best_aspect - target_aspect):
                layout = (rows, cols)
                best_aspect = aspect

        # Calculate size of sub-images
        rows, cols = layout
        target_image_width = video_size[0] // cols
        target_image_height = video_size[1] // rows
        scale_factor = min(
            target_image_width / image_width, target_image_height / image_height
        )
        image_size = (int(scale_factor * image_width), int(scale_factor * image_height))

    resized_frames = []
    for frame, filename in zip(frames, frameset):
        if frame is None:
            frame = np.zeros([image_size[1], image_size[0], 3], np.uint8)
            if args.labels:
                frame = add_label_centered(
                    frame, filename.name, alignment="top", color=(0, 0, 255)
                )
        else:
            frame = cv2.resize(frame, image_size, interpolation=cv2.INTER_AREA)
            if args.labels:
                frame = add_label_centered(frame, filename.name, alignment="top")
        resized_frames.append(frame)

    # Fill up last row of collage
    while len(resized_frames) < rows * cols:
        resized_frames.append(np.zeros_like(resized_frames[-1]))

    montage_rows = []
    for index in range(0, len(resized_frames), cols):
        montage_rows.append(np.hstack(resized_frames[index : index + cols]))
    montage = np.vstack(montage_rows)

    if montage.shape[1] % 2 != 0:
        # Pad video frame to have even width as h.264 doesn't support odd widths.
        montage = np.pad(montage, ((0, 0), (0, 1), (0, 0)), mode="constant")

    if video is None:
        fourcc = cv2.VideoWriter_fourcc(*"avc1")
        video = cv2.VideoWriter(
            str(args.src_dir / "collage.mp4"), fourcc, args.fps, montage.shape[1::-1]
        )
        assert video.isOpened(), "Video could not be opened for writing"

    video.write(montage)

del video

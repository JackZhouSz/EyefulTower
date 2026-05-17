# Copyright (c) Meta Platforms, Inc. and affiliates.

import argparse
from pathlib import Path

import cv2
from tqdm import tqdm


parser = argparse.ArgumentParser(description="Exports a video for each subdirectory.")
parser.add_argument(
    "src_dir",
    nargs="?",
    default=Path.cwd() / "images-jpeg-2k",
    type=Path,
    help="Source path.",
)
parser.add_argument("--fps", default=12, type=float, help="Framerate (default: 12)")
args = parser.parse_args()
print("Using arguments:")
for k, v in vars(args).items():
    print(f"  - {k} = {v}")
print()

src_paths = sorted(args.src_dir.glob("*"))
for src_path in src_paths:
    if not src_path.is_dir():
        continue

    video = None
    video_path = src_path.with_suffix(".mp4")
    frames = sorted(src_path.glob("*.jpg"))
    for frame_path in tqdm(frames, f"Creating {video_path.name}"):
        if not frame_path.is_file():
            continue
        frame = cv2.imread(str(frame_path))
        height, width = frame.shape[:2]

        video_size = (width, height)

        if video is None:
            fourcc = cv2.VideoWriter_fourcc(*"avc1")
            video = cv2.VideoWriter(str(video_path), fourcc, args.fps, video_size)

        video.write(frame)

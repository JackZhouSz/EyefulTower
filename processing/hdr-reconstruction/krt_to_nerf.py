# Copyright (c) Meta Platforms, Inc. and affiliates.

import argparse
import collections
import json
from pathlib import Path

import numpy as np

# Scene-specific fisheye mask radii for V1 captures
eyefultower_fisheye_radii: dict[str, float] = {
    "office1a": 0.43,
    "office2": 0.45,
    "seating_area": 0.375,  # could be .45 except for camera 2
    "table": 0.45,
    "workshop": 0.45,
}


def convert_cameras_to_nerfstudio_transforms(
    capture_name: str,
    cameras: dict,
    splits: dict,
    target_width: int,
    target_height: int,
    extension: str,
) -> dict:
    """Converts EyefulTower cameras.json format to Nerfstudio's transforms.json format
    The EyefulTower dataset provides a cameras.json file containing geometric calibration information for the
    original resolution ~8K images, similar to the cameras.xml file from Metashape. The main advantage is that data
    is provided for each individual image, rather than being structured hierarchically with rig constraints (as in
    the Metashape cameras.xml).
    This function takes the cameras.json file and converts it to the transforms.json Nerfstudio expects, with the
    necessary scaling of intrinsics parameters applied. This function also handles the EyefulTower splits.json file,
    describing the breakdown of training and validation images, and adds the appropriate fields to transforms.json.
    This function works for both fisheye (V1) and pinhole (V2) cameras. Scene-specific fisheye mask radii are added
    to the returned dictionary if needed.
    Args:
        capture_name: Which specific EyefulTower capture is being converted
        cameras: Data loaded from EyefulTower cameras.json
        splits: Data loaded from EyefulTower splits.json
        target_width: Width of output images
        target_height: Height of output images
        extension: Extension of output images
    Returns:
        Dict in the Nerfstudio transforms.json format, with scaled camera parameters, splits, and optional metadata.
    """
    output = {}

    distortion_models = [c["distortionModel"] for c in cameras["KRT"]]
    distortion_model = list(set(distortion_models))
    assert len(distortion_model) == 1
    distortion_model = distortion_model[0]
    if distortion_model == "RadialAndTangential":
        output["camera_model"] = "OPENCV"
    elif distortion_model == "Fisheye":
        output["camera_model"] = "OPENCV_FISHEYE"
        output["fisheye_crop_radius"] = eyefultower_fisheye_radii.get(
            capture_name, 0.45
        )
    else:
        raise NotImplementedError(f"Camera model {distortion_model} not implemented")

    split_sets = {k: set(v) for k, v in splits.items()}

    frames = []
    split_filenames = collections.defaultdict(list)
    for camera in cameras["KRT"]:
        frame = {}
        frame["file_path"] = camera["cameraId"] + f".{extension}"
        for split in split_sets:
            if camera["cameraId"] in split_sets[split]:
                split_filenames[split].append(frame["file_path"])

        original_width = camera["width"]
        original_height = camera["height"]
        if original_width > original_height:
            target_width, target_height = (
                max(target_width, target_height),
                min(target_width, target_height),
            )
        else:
            target_height, target_width = (
                max(target_width, target_height),
                min(target_width, target_height),
            )
        x_scale = target_width / original_width
        y_scale = target_height / original_height

        frame["w"] = target_width
        frame["h"] = target_height
        K = np.array(camera["K"]).T  # Data stored as column-major
        frame["fl_x"] = K[0][0] * x_scale
        frame["fl_y"] = K[1][1] * y_scale
        frame["cx"] = K[0][2] * x_scale
        frame["cy"] = K[1][2] * y_scale

        if distortion_model == "RadialAndTangential":
            # pinhole: [k1, k2, p1, p2, k3]
            frame["k1"] = camera["distortion"][0]
            frame["k2"] = camera["distortion"][1]
            frame["k3"] = camera["distortion"][4]
            frame["k4"] = 0.0
            frame["p1"] = camera["distortion"][2]
            frame["p2"] = camera["distortion"][3]
        elif distortion_model == "Fisheye":
            # fisheye: [k1, k2, k3, _, _, _, p1, p2]
            frame["k1"] = camera["distortion"][0]
            frame["k2"] = camera["distortion"][1]
            frame["k3"] = camera["distortion"][2]
            frame["p1"] = camera["distortion"][6]
            frame["p2"] = camera["distortion"][7]
        else:
            raise NotImplementedError("This shouldn't happen")

        T = np.array(camera["T"]).T  # Data stored as column-major
        T = np.linalg.inv(T)
        T = T[[2, 0, 1, 3], :]
        T[:, 1:3] *= -1
        frame["transform_matrix"] = T.tolist()

        frames.append(frame)

    frames = sorted(frames, key=lambda f: f["file_path"])

    output["frames"] = frames
    output["train_filenames"] = split_filenames["train"]
    output["val_filenames"] = split_filenames["test"]
    return output


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert EyefulTower cameras.json (KRT) to Nerfstudio transforms.json"
    )
    parser.add_argument(
        "data_path",
        type=str,
        help="Path to data directory containing cameras.json and splits.json",
    )
    parser.add_argument(
        "--capture-name",
        type=str,
        default="",
        help="Capture name for fisheye radius lookup",
    )
    parser.add_argument("--width", type=int, default=1920, help="Target image width")
    parser.add_argument("--height", type=int, default=1080, help="Target image height")
    parser.add_argument(
        "--extension", type=str, default="jpg", help="Image file extension"
    )
    args = parser.parse_args()

    data_dir = Path(args.data_path)

    with open(data_dir / "cameras.json", "r") as f:
        cameras = json.load(f)
    with open(data_dir / "splits.json", "r") as f:
        splits = json.load(f)

    transforms = convert_cameras_to_nerfstudio_transforms(
        capture_name=args.capture_name,
        cameras=cameras,
        splits=splits,
        target_width=args.width,
        target_height=args.height,
        extension=args.extension,
    )

    output_path = data_dir / "transforms.json"
    with open(output_path, "w") as f:
        json.dump(transforms, f, indent=4)
    print(f"Saved transforms to {output_path}")


if __name__ == "__main__":
    main()

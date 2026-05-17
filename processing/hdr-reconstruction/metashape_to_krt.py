# Copyright (c) Meta Platforms, Inc. and affiliates.

"""
metashape_to_krt.py
==========================
Convert the metashape xml data to KRT format
"""

import argparse
import json
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import numpy as np


def safe_load_float_xml(x: ET.Element | None) -> float:
    """Returns the float value of an XML element's text, or 0.0 if the element is None."""
    return float(x.text) if x is not None else 0.0


def extract_sensors(xml_root: ET.Element) -> dict[int, dict[str, Any]]:
    """Extracts sensor calibration data (intrinsics, distortion, rig poses) from Metashape XML."""
    sensors = xml_root.findall("chunk/sensors/sensor")

    output_sensors = {}
    for sensor in sensors:
        calibration = sensor.find("calibration[@class='adjusted']")
        if calibration is None:
            continue
        cali_type = calibration.attrib["type"]
        width = int(calibration.find("resolution").attrib["width"])
        height = int(calibration.find("resolution").attrib["height"])

        fx = float(calibration.find("f").text)
        fy = fx
        cx = float(width / 2.0) + safe_load_float_xml(calibration.find("cx"))
        cy = float(height / 2.0) + safe_load_float_xml(calibration.find("cy"))
        intrin = np.array(
            [
                [fx, 0.0, cx],
                [0.0, fy, cy],
                [0.0, 0.0, 1.0],
            ]
        )

        k1 = safe_load_float_xml(calibration.find("k1"))
        k2 = safe_load_float_xml(calibration.find("k2"))
        k3 = safe_load_float_xml(calibration.find("k3"))
        k4 = safe_load_float_xml(calibration.find("k4"))
        t1 = safe_load_float_xml(calibration.find("t1"))
        t2 = safe_load_float_xml(calibration.find("t2"))
        p1 = safe_load_float_xml(calibration.find("p1"))
        p2 = safe_load_float_xml(calibration.find("p2"))

        p1, p2 = p2, p1  # metashape and opencv are not consistent
        distortionModel = "Fisheye"
        if cali_type == "frame":
            distortionModel = "RadialAndTangential"
            dist = [k1, k2, p1, p2, k3]
        else:
            dist = [k1, k2, k3, k4, t1, t2, p1, p2]

        sensor_id = int(sensor.attrib["id"])
        output_sensors[sensor_id] = {
            "width": width,
            "height": height,
            "K": intrin.T.tolist(),
            "distortion": dist,
            "distortionModel": distortionModel,
            "projectionModel": distortionModel,  # Needed for the KRT viewer to work
        }

        # Process slave camera details
        if "master_id" in sensor.attrib:
            rotation = sensor.find("rotation").text
            location = sensor.find("location").text
            rotation = np.fromstring(rotation, dtype=np.float32, sep=" ").reshape(
                (3, 3)
            )
            location = np.fromstring(location, dtype=np.float32, sep=" ").reshape(
                (3, 1)
            )
            pose = np.vstack([np.hstack([rotation, location]), [[0, 0, 0, 1]]])

            output_sensors[sensor_id]["sensorMasterId"] = int(
                sensor.attrib["master_id"]
            )
            output_sensors[sensor_id]["pose"] = pose
        else:
            output_sensors[sensor_id]["pose"] = np.eye(4, dtype=float)

    return output_sensors


def extract_chunk_data(chunk_transform: ET.Element | None) -> np.ndarray:
    """Extracts and inverts the rigid chunk transform (rotation + translation) to world-to-chunk."""
    chunk = np.eye(4, 4, dtype=np.float32)  # rigid chunk transform
    if chunk_transform is not None:
        # Rotation matrix
        rotation = chunk_transform.find("rotation")
        if rotation is not None:
            values = np.fromstring(rotation.text, dtype=np.float32, sep=" ")
            chunk[:3, :3] = values.reshape((3, 3))

        # Translation vector
        translation = chunk_transform.find("translation")
        if translation is not None:
            values = np.fromstring(translation.text, dtype=np.float32, sep=" ")
            chunk[:3, 3] = values.reshape(3)

        # Invert the chunk transform, so it becomes world-to-chunk
        chunk[:3, 3] = -chunk[:3, :3].T @ chunk[:3, 3]
        chunk[:3, :3] = chunk[:3, :3].T
    return chunk


def extract_scale_data(chunk_transform: ET.Element | None) -> float:
    """Extracts the scale factor from a chunk transform, defaulting to 1.0."""
    if chunk_transform is not None:
        scale = chunk_transform.find("scale")
        if scale is not None:
            return float(scale.text)
    return 1.0


def camera_builder(
    sensors: dict[int, dict[str, Any]], sensor_id: int, camera: ET.Element
) -> dict[str, Any]:
    """Builds a KRT camera dict from a sensor and a Metashape XML camera element."""
    output_camera = dict(sensors[sensor_id])
    output_camera["cameraId"] = camera.attrib["label"]
    output_camera["sensorId"] = sensor_id

    if "master_id" in camera.attrib:
        # Slave cameras don't have a transform; they are always relative to the master camera
        output_camera["cameraMasterId"] = int(camera.attrib["master_id"])

    elif camera.find("transform") is not None:
        T = np.fromstring(camera.find("transform").text, dtype=np.float32, sep=" ")
        T = T.reshape((4, 4))

        # Get chunk-to-camera transform by inverting the (camera-to-chunk) camera transform
        T[:3, 3] = -T[:3, :3].T @ T[:3, 3]
        T[:3, :3] = T[:3, :3].T

        output_camera["T"] = T

    else:
        print(f"Warning: no transform found for camera {camera.attrib['id']}.")
        output_camera["T"] = None

    return output_camera


def compute_slave_camera_pose(
    output_cameras: dict[int, dict[str, Any]],
    sensors: dict[int, dict[str, Any]],
) -> None:
    """Computes absolute world-to-camera poses for slave cameras in a rig."""
    is_rig = any("sensorMasterId" in s for s in sensors.values())
    if is_rig:
        for curr_id, camera in output_cameras.items():
            if "cameraMasterId" not in camera:
                camera["cameraMasterId"] = curr_id

            slave2master = camera["pose"]
            world2master = output_cameras[camera["cameraMasterId"]]["T"]
            master2slave = np.linalg.inv(slave2master)
            world2slave = master2slave @ world2master
            camera["newT"] = world2slave

        for camera in output_cameras.values():
            camera["T"] = camera["newT"]
            del camera["newT"]


def get_frame_ids(
    sensors: dict[int, dict[str, Any]],
    output_cameras: dict[int, dict[str, Any]],
    frame_numbering: str,
) -> dict[str, int] | None:
    """Assigns frame IDs to cameras for multi-camera setups."""
    is_multicam = len(sensors) > 1
    camera_id_to_frame_id_lut = None
    if is_multicam:
        camera_id_to_frame_id_lut = {}

        if frame_numbering == "per-camera":
            print(
                "Note: using per-camera frame numbering.\n"
                "      This is incorrect if some frames are missing for some cameras."
            )
            for sensor in sensors:
                camera_ids = sorted(
                    [
                        camera["cameraId"]
                        for camera in output_cameras.values()
                        if camera["sensorId"] == sensor
                    ]
                )

                # Assign sequential frame IDs to all images of this sensor
                camera_id_to_frame_id_lut.update(
                    dict(zip(camera_ids, range(len(camera_ids))))
                )

        elif frame_numbering == "camera-suffix":
            print(
                "Note: using frame IDs based on a filename suffix like 'DSC1234' that is shared between (synchronized) cameras."
            )

            # Split camera IDs into lists of prefixes (e.g. 10, 11, ...) and suffixes (e.g. "DSC1234").
            camera_ids = {camera["cameraId"] for camera in output_cameras.values()}
            prefixes = sorted({"_".join(cid.split("_")[:-1]) for cid in camera_ids})
            suffixes = sorted({cid.split("_")[-1] for cid in camera_ids})

            # Add all combinations of prefixes and suffixes, even for frames skipped by some cameras.
            for frame_id, suffix in enumerate(suffixes):
                for prefix in prefixes:
                    camera_id_to_frame_id_lut[f"{prefix}_{suffix}"] = frame_id

        else:
            print("Note: frame numbering disabled.")
            camera_id_to_frame_id_lut = None

    return camera_id_to_frame_id_lut


def extract_cameras(
    xml_root: ET.Element,
    frame_numbering: str = "camera-suffix",
) -> list[dict[str, Any]]:
    """Extracts all cameras from Metashape XML and returns them in KRT format."""
    sensors = extract_sensors(xml_root)

    # Parse the chunk transform (if available)
    chunk_transform = xml_root.find("chunk/transform")
    T_scale = extract_scale_data(chunk_transform)
    T_chunk = extract_chunk_data(chunk_transform)  # rigid chunk transform

    cameras = xml_root.findall("chunk/cameras//camera")
    output_cameras = {}
    for camera in cameras:
        sensor_id = int(camera.attrib["sensor_id"])

        if sensor_id not in sensors:
            print(
                f"Warning: sensor '{sensor_id}' not found for camera {camera.attrib['id']}."
            )
            continue

        output_cameras[int(camera.attrib["id"])] = camera_builder(
            sensors, sensor_id, camera
        )

    # Second pass: compute absolute camera poses for slave cameras
    compute_slave_camera_pose(output_cameras, sensors)

    # Third pass: assign frame numbers for multi-camera cases (with or without rig).
    camera_id_to_frame_id_lut = get_frame_ids(sensors, output_cameras, frame_numbering)

    is_multicam = len(sensors) > 1
    # Fourth pass: prepare names and transforms for export
    for camera in output_cameras.values():
        if "pose" in camera:
            del camera["pose"]

        if is_multicam:
            # Add sequential frame IDs to all cameras
            if camera_id_to_frame_id_lut is not None:
                camera["frameId"] = camera_id_to_frame_id_lut[camera["cameraId"]]

            # Camera name needs to include camera directory
            camera["cameraId"] = get_camera_id_from_camera(camera)

        if camera["T"] is None:
            print(f'Skipping camera "{camera["cameraId"]}" due to lack of pose.')
            continue

        # Apply global scale factor by scaling the translation vectors of world-to-camera poses.
        # This is equivalent to scaling all camera centers by the same factor.
        camera["T"][:3, 3] *= T_scale

        # Apply chunk transform (rotation and translation).
        camera["T"] = camera["T"] @ T_chunk

        # KRT format: A 4x4 world-to-camera transformation matrix, but transposed
        camera["T"] = camera["T"].T.tolist()

    cameras_list = [c for c in output_cameras.values() if c["T"]]
    return cameras_list


def get_camera_id_from_camera(camera: dict[str, Any]) -> str:
    """
    Reconstructs the camera image's relative path from its filename.
    """
    tokens = camera["cameraId"].split("_")
    if len(tokens) == 1 or len(tokens[0]) == 0:
        # No underscore or leading underscore? Assume everything's in the same directory.
        return camera["cameraId"]
    else:
        # Use string before underscore as directory name
        return tokens[0] + "/" + camera["cameraId"]


def convert_cameras(
    inpath: str | Path,
    outpath: str | Path,
    frame_numbering: str,
) -> None:
    """Converts a Metashape cameras XML file to KRT JSON format."""
    tree = ET.parse(inpath)
    xml_root = tree.getroot()

    output_cameras = extract_cameras(xml_root, frame_numbering=frame_numbering)

    with open(outpath, "w", encoding="utf-8") as outfile:
        json.dump({"KRT": output_cameras}, outfile, indent=2)


def compare_krt_cameras(
    name: str,
    source: dict[str, Any],
    target: dict[str, Any],
) -> None:
    """Compares two KRT camera dictionaries. Throws `AssertionError` for any discrepancy."""
    for key in target.keys():  # `source` can have new keys that are not checked
        # Check arrays and matrices using NumPy's to be lenient to floating point errors
        if key in ["K", "T", "distortion"]:
            source_value = np.array(source[key])
            target_value = np.array(target[key])
            assert np.allclose(source_value, target_value, rtol=1e-4, atol=1e-6), (
                f"Expected similar value for '{key}' in camera '{name}':\n"
                f"  - source = {source_value}\n"
                f"  - target = {target_value}"
            )
        else:
            assert source[key] == target[key], (
                f"Expected matching value for '{key}' in camera '{name}':\n"
                f"  - source = {source[key]}\n"
                f"  - target = {target[key]}"
            )


def compare_krt_dicts(
    source: list[dict[str, Any]],
    target: list[dict[str, Any]],
) -> None:
    """Compares two KRT camera dictionaries with any number of cameras.
    Throws `AssertionError` for any discrepancy."""

    # Create dictionaries to index cameras by `cameraId`
    source_cameras = {e["cameraId"]: e for e in source}
    target_cameras = {e["cameraId"]: e for e in target}

    # Check for same camera IDs
    source_camera_ids = set(source_cameras.keys())
    target_camera_ids = set(target_cameras.keys())
    assert source_camera_ids == target_camera_ids, (
        "Expected same camera labels:\n"
        f"  - only in source: {source_camera_ids - target_camera_ids}\n"
        f"  - only in target: {target_camera_ids - source_camera_ids}"
    )

    # Compare corresponding cameras
    for camera_id in source_camera_ids:
        compare_krt_cameras(
            camera_id, source_cameras[camera_id], target_cameras[camera_id]
        )


def test_convert_cameras(filename: str) -> None:
    """Tests camera conversion by comparing output against a reference KRT JSON."""
    test_data_dir = Path(__file__).parent / "test_data"
    cameras_xml = test_data_dir / f"{filename}.xml"
    cameras_json = test_data_dir / f"{filename}.json"

    # Convert "cameras.xml" to KRT format
    tree = ET.parse(str(cameras_xml))
    xml_root = tree.getroot()
    converted_cameras = extract_cameras(xml_root, frame_numbering="per-camera")

    # Load reference KRT
    with open(cameras_json, "r", encoding="utf-8") as fh:
        reference_cameras = json.load(fh)["KRT"]

    compare_krt_dicts(converted_cameras, reference_cameras)


class TestConverter(unittest.TestCase):
    def test_single_camera(self):
        """Tests a single-camera capture via the outdoor loader dataset."""
        test_convert_cameras("cameras-metashape_outside_0")

    def test_rig9_master0_scale_only(self):
        """Tests a 9-camera rig with master camera 0 and chunk scaling."""
        test_convert_cameras("cameras-eyeful_heinz57")

    def test_rig9_master6_scale_only(self):
        """Tests a 9-camera rig with master camera 6 (non-zero) and chunk scaling."""
        test_convert_cameras("cameras-eyeful_roomsy")

    def test_rig22_master13_scale_only(self):
        """Tests a 22-camera rig with master camera 13 (non-zero) and chunk scaling."""
        test_convert_cameras("cameras-eyeful15_heinz57")

    def test_rig22_master13_full_transform(self):
        """Tests a 22-camera rig with master camera 13 (non-zero) and chunk scaling,
        rotation and translation."""
        test_convert_cameras("cameras-eyeful15_heinz57_rotated")

    def test_22cam_full_transform(self):
        """Tests a 22-camera capture without rig calibration, but chunk scaling,
        rotation and translation."""
        test_convert_cameras("cameras-eyeful15_apartment1_v3")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("infile")
    parser.add_argument("outfile")
    parser.add_argument(
        "--frame-numbering",
        type=str,
        default="camera-suffix",
        choices=["per-camera", "camera-suffix", "none"],
        help="Method for numbering frame IDs. 'none' disables frame numbering.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    print("loading...")
    convert_cameras(args.infile, args.outfile, frame_numbering=args.frame_numbering)


if __name__ == "__main__":
    main()

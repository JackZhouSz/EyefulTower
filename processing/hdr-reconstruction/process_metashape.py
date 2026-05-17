# Copyright (c) Meta Platforms, Inc. and affiliates.

import argparse
import sys
from itertools import chain
from pathlib import Path

import numpy as np
from utils import (
    binary_search_optimal_scale,
    calculate_total_error,
    load_krt_json,
    TqdmProgressBar,
)

## Parse command line arguments
parser = argparse.ArgumentParser(
    description="Tool for scripted Metashape dataset processing."
)
parser.add_argument(
    "project_dir",
    default=Path.cwd(),
    nargs="?",
    type=Path,
    help="Path to the project/dataset (default: cwd)",
)
parser.add_argument(
    "-i",
    "--image-dir",
    default="images-jpeg",
    type=str,
    help="Name of image directory (default: images-jpeg)",
)
parser.add_argument(
    "-r",
    "--rig",
    type=str,
    default="none",
    choices=[
        "eyeful1.0",
        "eyeful1.5",
        "eyeful3.0",
        "double-fisheye",
        "none",
    ],
    help="Camera rig to use, if any (default: none)",
)
parser.add_argument(
    "--rig-calibration",
    default=True,
    action=argparse.BooleanOptionalAction,
    help="Use rig calibration. When disabled, treats all cameras as independent",
)
parser.add_argument(
    "--master-camera",
    default=-1,
    type=int,
    help="Camera index of the master camera (-1: rig-dependent, 0: first camera, 1: 2nd camera)",
)
parser.add_argument(
    "--fixed-calibration",
    default=False,
    action=argparse.BooleanOptionalAction,
    help="Fix the initial calibration",
)
parser.add_argument(
    "--krt-extrinsics",
    default=True,
    action=argparse.BooleanOptionalAction,
    help="Use the extrinsics when loading a KRT.",
)
parser.add_argument(
    "--undistorted",
    default=False,
    action=argparse.BooleanOptionalAction,
    help="Ignores the lens distortion parameters when loading a KRT.",
)
parser.add_argument(
    "--load-krt",
    type=Path,
    help="Loads a KRT calibration file",
)
parser.add_argument(
    "--focal-length",
    type=float,
    default=2000.0,
    help="Focal length, in pixels (default: 2000)",
)
parser.add_argument(
    "--fisheye",
    default=False,
    action=argparse.BooleanOptionalAction,
    help="Uses the fisheye projection model.",
)
parser.add_argument(
    "-s",
    "--stages",
    type=str,
    default="all",
    help="Stages to process (default: 'all')",
)
parser.add_argument(
    "--skip-model-export",
    default=False,
    action=argparse.BooleanOptionalAction,
    help="Skipping model export. On lower end machines, the model process gets stuck. This lets you skip exporting.",
)
parser.add_argument(
    "--skip-vertex-colors",
    default=False,
    action=argparse.BooleanOptionalAction,
    help="On Mac. Metashape gets stuck on this step exporting models.",
)
parser.add_argument(
    "--save-often",
    default=False,
    action=argparse.BooleanOptionalAction,
    help="Saves a new project after each stage",
)
parser.add_argument(
    "--report",
    default=False,
    action=argparse.BooleanOptionalAction,
    help="Saves a final report",
)
parser.add_argument(
    "--input",
    type=Path,
    help="Path to the input Metashape project to load",
)
parser.add_argument(
    "--output",
    type=str,
    default="",
    help="Path to the Metashape project to save",
)
parser.add_argument(
    "--filter-ru",
    type=float,
    default=50.0,
    help="Threshold for filtering the reconstruction uncertainty (default: 50)",
)
parser.add_argument(
    "--filter-pa",
    type=float,
    default=5.0,
    help="Threshold for filtering the projection accuracy (default: 5)",
)
parser.add_argument(
    "--filter-re",
    type=float,
    default=1.0,
    help="Threshold for filtering the reprojection error (default: 1)",
)

args = parser.parse_args()
print("Using arguments:")
for k, v in vars(args).items():
    print(f"  - {k} = {v}")
print()

# %%
import Metashape  # pylint: disable=E0401

if not Metashape.License().valid:
    raise RuntimeError("Metashape license is not valid. Please fix.")

print(f"Found Metashape version {Metashape.app.version}\n")
metashape_major_version = ".".join(Metashape.app.version.split(".")[:2])


print("Detected GPUs:")
for i, gpu in enumerate(Metashape.app.enumGPUDevices()):
    gpu_gb = gpu["mem_size"] / 2**30
    print(f"  {i}. {gpu['name']} ({gpu_gb:.1f} GB, {gpu['clock'] / 1000:.1f} GHz)")


## Step 1. Start a new project + chunk / load an existing project
doc = Metashape.Document()
doc.addChunk()

# Compatibility
if metashape_major_version == "1.8":
    TiePoints = Metashape.PointCloud
else:  # renamed in Metashape 2.0 onwards
    TiePoints = Metashape.TiePoints

if args.input:
    doc.open(str(args.project_dir / args.input))

## Replace named groups of stages with a list of stages
stage_groups = {
    "all": ["part1", "save", "filter", "save", "part2"],
    "part1": ["addphotos", "calib", "align", "scalebars"],
    "part2": ["depthmaps", "densecloud", "model", "texture", "export"],
    "filter": [
        "filter_ru",
        "optimizecameras",
        "filter_pa",
        "optimizecameras",
        "filter_re",
        "optimizecameras",
    ],
    "filter_noopt": ["filter_ru", "filter_pa", "filter_re"],
}

stages = args.stages.split(",")
while True:
    for group in stage_groups.keys():
        if group in stages:
            pos = stages.index(group)
            stages = stages[:pos] + stage_groups[group] + stages[pos + 1 :]
            break  # replaced one group, start over with replacing groups
    else:  # break the while loop when no groups were found
        break

for stage_index, stage in enumerate(stages, start=1):
    print(f"\n{stage_index}. Running stage '{stage}' ...", file=sys.stderr)

    ## Step 2. Add images
    if stage == "addphotos":
        images_dir = args.project_dir / args.image_dir
        images = []
        for camera_dir in sorted(images_dir.iterdir()):
            if camera_dir.is_dir():
                # Images in sub-directories, one per camera
                camera_images = [
                    str(f) for f in sorted(camera_dir.iterdir()) if f.is_file()
                ]
                print(f"camera added: {camera_dir}", file=sys.stderr)

                images.append(camera_images)
            else:
                # Images in the input directory
                if len(images) == 0:
                    images = [[]]
                images[0].append(str(camera_dir))

        if args.rig_calibration and args.rig != "none":
            with TqdmProgressBar(desc="Adding photos (rig)") as t:
                filenames = list(chain(*zip(*images)))
                filegroups = [len(images)] * (len(filenames) // len(images))

                for filename in filenames:
                    print(f"filename = {filename}", file=sys.stderr)

                doc.chunk.addPhotos(
                    filenames=filenames,  # (list of string) – List of files to add.
                    filegroups=filegroups,  # (list of int) – List of file groups.
                    layout=Metashape.MultiplaneLayout,  # (ImageLayout) – Image layout. [default: UndefinedLayout]
                    # [group,]  # (int) – Camera group key.
                    # strip_extensions=True,  # (bool) – Strip file extensions from camera labels.
                    # load_reference=True,  # (bool) – Load reference coordinates.
                    # load_xmp_calibration=True,  # (bool) – Load calibration from XMP meta data.
                    # load_xmp_orientation=True,  # (bool) – Load orientation from XMP meta data.
                    # load_xmp_accuracy=False,  # (bool) – Load accuracy from XMP meta data.
                    # load_xmp_antenna=True,  # (bool) – Load GPS/INS offset from XMP meta data.
                    # load_rpc_txt=False,  # (bool) – Load satellite RPC data from auxiliary TXT files.
                    progress=t.update_to,  # (Callable[[float], None]) – Progress callback.
                )

            ## Name each sensor (camera) according to the subdirectory containing its images
            for sensor, sensor_images in zip(doc.chunk.sensors, images):
                sensor.label = Path(sensor_images[0]).parent.name

        else:  # no rig or no rig calibration
            for _index, filenames in enumerate(images):
                camera_name = Path(
                    filenames[0]
                ).parent.name  # Use directory name as sensor name
                with TqdmProgressBar(
                    desc=f"Adding photos (no rig, camera '{camera_name}')"
                ) as t:
                    doc.chunk.addPhotos(
                        filenames=filenames,  # (list of string) – List of files to add.
                        # filegroups=filegroups,  # (list of int) – List of file groups.
                        # layout=Metashape.MultiplaneLayout,  # (ImageLayout) – Image layout. [default: UndefinedLayout]
                        # layout=Metashape.FlatLayout,
                        # [group,]  # (int) – Camera group key.
                        # group=index,
                        # strip_extensions=True,  # (bool) – Strip file extensions from camera labels.
                        # load_reference=True,  # (bool) – Load reference coordinates.
                        # load_xmp_calibration=True,  # (bool) – Load calibration from XMP meta data.
                        # load_xmp_orientation=True,  # (bool) – Load orientation from XMP meta data.
                        # load_xmp_accuracy=False,  # (bool) – Load accuracy from XMP meta data.
                        # load_xmp_antenna=True,  # (bool) – Load GPS/INS offset from XMP meta data.
                        # load_rpc_txt=False,  # (bool) – Load satellite RPC data from auxiliary TXT files.
                        progress=t.update_to,  # (Callable[[float], None]) – Progress callback.
                    )

                ## The following worked in Metashape 1.8, maybe in 2.0, but no longer in 2.1.
                ## It now creates one extra 'unknown' sensor for each camera.
                # if index == 0:
                #     # Metashape created a sensor for us, so use that
                #     sensor = doc.chunk.sensors[0]
                # else:
                #     # Create a copy of the first sensor (including image width + height)
                #     sensor = doc.chunk.addSensor(doc.chunk.sensors[0])

                sensor = doc.chunk.sensors[-1]
                sensor.label = camera_name

                # Assign newly added photos to a camera group and separate sensor (for calibration)
                camera_group = doc.chunk.addCameraGroup()
                camera_group.label = f"Group {sensor.label}"
                for camera in doc.chunk.cameras:
                    if not camera.group:
                        camera.group = camera_group
                        camera.sensor = sensor

    # Step 3. Add calibration information (only in first pass)
    elif stage == "calib":
        if args.rig_calibration:
            master_camera = args.master_camera
            if args.rig == "eyeful1.0":
                if master_camera == -1:
                    master_camera = 6
            elif args.rig == "eyeful1.5":
                if master_camera == -1:
                    # 23 is master but camera 10 is index 0
                    master_camera = 23 - 10
            elif args.rig in ["eyeful3.0", "double-fisheye", "none"]:
                if args.master_camera == -1:
                    master_camera = 0
            else:
                raise ValueError(f"Rig '{args.rig}' not supported")

            if master_camera >= 0:
                print(
                    f"Setting sensor {master_camera} as master camera.", file=sys.stderr
                )
                doc.chunk.sensors[master_camera].makeMaster()

        # Load existing calibration from KRT
        if args.load_krt is not None:
            krt = load_krt_json(args.load_krt)
        else:
            krt = None

        for sensor_id, sensor in enumerate(doc.chunk.sensors):
            if not sensor.label:
                sensor.label = f"Camera {sensor_id}"
            sensor.black_level = Metashape.Vector([0, 0, 0])
            sensor.sensitivity = Metashape.Vector([1, 1, 1])
            sensor.fixed = args.fixed_calibration

            if args.rig == "eyeful1.0":
                ## Sony A1
                sensor.pixel_width = (
                    0.00416667 / max(sensor.width, sensor.height) * 8660
                )
                sensor.pixel_height = sensor.pixel_width

                ## Canon 8-15 mm fisheye
                sensor.type = Metashape.Sensor.Type.Fisheye
                sensor.focal_length = 14.0 if sensor.key == 0 else 12.0

            elif args.rig == "eyeful1.5":
                ## Sony A1
                sensor.pixel_width = (
                    0.00416667 / max(sensor.width, sensor.height) * 8660
                )
                sensor.pixel_height = sensor.pixel_width

                ## Sony 12-24 mm pinhole
                sensor.type = Metashape.Sensor.Type.Frame
                sensor.focal_length = 12.0

            if args.rig == "eyeful3.0":
                ## Sony A1
                sensor.pixel_width = (
                    0.00416667 / max(sensor.width, sensor.height) * 8660
                )
                sensor.pixel_height = sensor.pixel_width

                ## Entaniya 6 mm fisheye
                sensor.type = Metashape.Sensor.Type.Fisheye
                sensor.focal_length = 6.0

            elif args.rig == "double-fisheye":
                sensor.type = Metashape.Sensor.Type.Fisheye
                # estimated for Insta360 One RS 1-Inch
                sensor.focal_length = 3
                sensor.pixel_height = sensor.pixel_width = 0.003

            elif args.rig == "none":
                sensor.type = Metashape.Sensor.Type.Frame
                sensor.focal_length = args.focal_length / 1000.0
                # hypothetical sensor with 1 micrometer pixels
                sensor.pixel_height = sensor.pixel_width = 0.001

            if args.fisheye:
                sensor.type = Metashape.Sensor.Type.Fisheye

            ## Set pre-calibrated intrinsics from KRT
            if krt:
                # Find the KRT entry for this camera (name ending in two-digit camera number)
                keys = [key for key in krt.keys() if key in sensor.label]
                assert len(keys) == 1, (
                    f"Need unique mapping from `sensor_id` ({sensor.label}) to KRT `cameraId`."
                )
                # print(f"sensor_id {sensor_id} => KRT cameraId '{keys[0]}'")
                krt_calib = krt[keys[0]]

                # Set the correct projection model
                if krt_calib["projectionModel"] == "Pinhole":
                    sensor.type = Metashape.Sensor.Type.Frame
                elif krt_calib["projectionModel"] == "Fisheye":
                    sensor.type = Metashape.Sensor.Type.Fisheye
                else:
                    raise ValueError(
                        f"Unknown projection model '{krt_calib['projectionModel']}'"
                    )

                # Set the correct camera intrinsics
                calib = sensor.calibration.copy()
                calib.f = (krt_calib["K"][0, 0] + krt_calib["K"][1, 1]) / 2
                calib.cx = krt_calib["K"][0, 2] - sensor.width / 2
                calib.cy = krt_calib["K"][1, 2] - sensor.height / 2

                if not args.undistorted:
                    calib.k1 = krt_calib["distortion"][0, 0]
                    calib.k2 = krt_calib["distortion"][0, 1]

                    # Set the correct distortion model
                    if krt_calib["distortionModel"] == "RadialAndTangential":
                        # Metashape p1/p2 is OpenCV p2/p1
                        calib.p2 = krt_calib["distortion"][0, 2]
                        calib.p1 = krt_calib["distortion"][0, 3]
                    elif krt_calib["distortionModel"] == "Fisheye":
                        calib.k3 = krt_calib["distortion"][0, 2]
                        calib.k4 = krt_calib["distortion"][0, 3]
                    else:
                        raise ValueError(
                            f"Unknown distortion model '{krt_calib['distortionModel']}'"
                        )

                sensor.user_calib = calib
                sensor.fixed_location = True  # fix location

            ## rig-based calibration relative to master camera
            if sensor != sensor.master:
                sensor.fixed_location = False

        ## Set pre-calibrated extrinsics (no support for rigs yet)
        if krt:
            if args.krt_extrinsics:
                for _camera_id, camera in enumerate(doc.chunk.cameras):
                    # Find the KRT entry for this camera
                    keys = [key for key in krt.keys() if key in camera.sensor.label]
                    assert len(keys) == 1, (
                        "Need unique mapping from `sensor_id` to KRT `cameraId`."
                    )
                    # print(f"camera_id {camera_id} => KRT cameraId '{keys[0]}'")
                    krt_calib = krt[keys[0]]

                    transform = np.linalg.inv(krt_calib["T"])
                    camera.transform = Metashape.Matrix(transform.tolist())
            else:
                print(
                    "Skipping KRT extrinsics as requested by --no-krt-extrinsics",
                    file=sys.stderr,
                )

    ## Step 4. Align photos = matchPhotos + alignCameras (https://www.agisoft.com/forum/index.php?topic=12185.0)
    elif stage == "align":
        with TqdmProgressBar(desc="Matching photos") as t:
            doc.chunk.matchPhotos(
                # 0 = Highest (double resolution),
                # 1 = High (original resolution),
                # 2 = Medium (half resolution),
                # 4 = Low (quarter resolution),
                # 8 = Lowest (one eight resolution)
                # -- https://www.agisoft.com/forum/index.php?topic=11697.0
                downscale=0,  # Image alignment accuracy (int)
                # generic_preselection=True,  # Enable generic preselection [default: True]
                # reference_preselection=True,  # Enable reference preselection [default: True]
                reference_preselection_mode=Metashape.ReferencePreselectionMode.ReferencePreselectionEstimated,  # [default: ReferencePreselectionSource]
                # filter_mask=False,  # Filter points by mask [default: False]
                mask_tiepoints=False,  # Apply mask filter to tie points [default: True]
                # filter_stationary_points=True,  # Exclude tie points which are stationary across images [default: True]
                keypoint_limit=60_000,  # Key point limit (int)
                tiepoint_limit=0,  # Tie point limit (int)
                # keypoint_limit_per_mpx=1000,  # Key point limit per megapixel [default: 1000]
                keep_keypoints=True,  # Store keypoints in the project
                # [pairs,]  # (list of (int, int) tuples) – User defined list of camera pairs to match.
                # [cameras,]  # (list of int) – List of cameras to match
                # guided_matching=False,  # Enable guided image matching [default: False]
                # reset_matches=False,  # Reset current matches [default: False]
                # subdivide_task=True,  # Enable fine-level task subdivision [default: True]
                workitem_size_cameras=64,  # Number of cameras in a workitem [default: 20]
                workitem_size_pairs=1024,  # Number of image pairs in a workitem [default: 80]
                max_workgroup_size=1024,  # Maximum workgroup size [default: 100]
                progress=t.update_to,  # (Callable[[float], None]) – Progress callback.
            )

        with TqdmProgressBar(desc="Aligning cameras") as t:
            doc.chunk.alignCameras(
                # [cameras],  # (list of int) – List of cameras to align
                # min_image=2,  # Minimum number of point projections [default: 2]
                # adaptive_fitting=False,  # Enable adaptive fitting of distortion coefficients [default: False]
                # reset_alignment=False,  # Reset current alignment [default: False]
                # subdivide_task=True,  # Enable fine-level task subdivision [default: True]
                progress=t.update_to  # (Callable[[float], None]) – Progress callback.
            )

    ## Step X. Transform chunk to Z-up
    elif stage == "transform":
        rot90 = Metashape.Matrix([[1, 0, 0], [0, 0, -1], [0, 1, 0]])
        rotation = Metashape.Matrix.Rotation(rot90)
        translation = Metashape.Matrix.Translation(Metashape.Vector([0, 0, 0]))

        doc.chunk.transform.matrix = rotation * translation

    ## Step X. Trim points and resize bounding box
    elif stage == "trim":
        region = doc.chunk.region
        regionSize = region.size

        # I am assuming region size is whole width, not from center.
        for point in doc.chunk.tie_points.points:
            if point.valid:
                pointCoord = Metashape.Vector(
                    [point.coord.x, point.coord.y, point.coord.z]
                )
                distFromCenter = region.rot.t() * (pointCoord - region.center)

                if (
                    abs(distFromCenter.x) > abs(regionSize.x / 2)
                    or abs(distFromCenter.y) > abs(regionSize.y / 2)
                    or abs(distFromCenter.z) > abs(regionSize.z / 2)
                ):
                    point.valid = False

        doc.chunk.resetRegion()
        doc.chunk.region.rot = doc.chunk.transform.matrix.rotation()

    ## Step 5. Detect and add scale bars
    elif stage == "scalebars":
        with TqdmProgressBar(desc="Detecting markers") as t:
            doc.chunk.detectMarkers(
                # target_type=CircularTarget12bit,  # (TargetType) – Type of targets.
                # tolerance=50,  # (int) – Detector tolerance (0 - 100). [default: 50]
                # filter_mask=False,  # (bool) – Ignore masked image regions.
                # inverted=False,  # (bool) – Detect markers on black background.
                # noparity=False,  # (bool) – Disable parity checking.
                # maximum_residual=5,  # (float) – Maximum residual for non-coded targets in pixels.
                # minimum_size=0,  # (int) Minimum target radius in pixels to be detected (CrossTarget type only).
                # minimum_dist=5,  # (int) Minimum distance between targets in pixels (CrossTarget type only).
                # [cameras, ]  # (list of int) – List of cameras to process.
                # [frames, ]  # (list of int) – List of frames to process.
                progress=t.update_to,  # (Callable[[float], None]) – Progress callback.
            )

        scalebars = [
            # 25 cm scale bars
            ["003", 7, 8, 0.25006],
            ["006", 15, 16, 0.25003],
            ["009", 23, 24, 0.25012],
            # 50 cm scale bars
            ["002a", 4, 5, 0.25000],
            ["002b", 5, 6, 0.24990],
            ["005a", 12, 13, 0.24998],
            ["005b", 13, 14, 0.24989],
            ["008a", 20, 21, 0.25003],
            ["008b", 21, 22, 0.24988],
        ]

        markers = {m.label: m for m in doc.chunk.markers}
        doc.chunk.scalebar_accuracy = 0.0001  # [m] == 0.1 mm

        print("Markers found:", file=sys.stderr)
        for marker in doc.chunk.markers:
            print(
                f"- '{marker.label}': {len(marker.projections)} projections",
                file=sys.stderr,
            )
        print()

        print("Markers disabled due to insufficient projections:", file=sys.stderr)
        for marker in doc.chunk.markers:
            if len(marker.projections) < 10:
                print(
                    f"- '{marker.label}': {len(marker.projections)} projections",
                    file=sys.stderr,
                )
                marker.enabled = False
        print()

        for scalebar_name, start, end, distance in scalebars:
            point1 = markers.get(f"target {start}")
            point2 = markers.get(f"target {end}")

            if point1 is None:
                print(
                    f"Skipping scale bar '{scalebar_name}' as 'target {start}' not found."
                )
            elif point2 is None:
                print(
                    f"Skipping scale bar '{scalebar_name}' as 'target {end}' not found."
                )
            else:
                print(
                    f"Adding scale bar '{scalebar_name}' ({start}-{end}): {distance:.5f} m."
                )
                scalebar = doc.chunk.addScalebar(point1, point2)
                scalebar.label = f"{scalebar_name}. {start}-{end}"
                scalebar.reference.enabled = True
                scalebar.reference.distance = distance

        with TqdmProgressBar(desc="Optimizing cameras") as t:
            doc.chunk.optimizeCameras(
                # fit_f=True,  # (bool) – Enable optimization of focal length coefficient.
                # fit_cx=True,  # (bool) – Enable optimization of X principal point coordinates.
                # fit_cy=True,  # (bool) – Enable optimization of Y principal point coordinates.
                # fit_b1=False,  # (bool) – Enable optimization of aspect ratio.
                # fit_b2=False,  # (bool) – Enable optimization of skew coefficient.
                # fit_k1=True,  # (bool) – Enable optimization of k1 radial distortion coefficient.
                # fit_k2=True,  # (bool) – Enable optimization of k2 radial distortion coefficient.
                # fit_k3=True,  # (bool) – Enable optimization of k3 radial distortion coefficient.
                # fit_k4=False,  # (bool) – Enable optimization of k3 radial distortion coefficient.
                # fit_p1=True,  # (bool) – Enable optimization of p1 tangential distortion coefficient.
                # fit_p2=True,  # (bool) – Enable optimization of p2 tangential distortion coefficient.
                # fit_corrections=False,  # (bool) – Enable optimization of additional corrections.
                # adaptive_fitting=False,  # (bool) – Enable adaptive fitting of distortion coefficients.
                tiepoint_covariance=True,  # (bool) – Estimate tie point covariance matrices. [Default: False]
                progress=t.update_to,  # (Callable[[float], None]) – Progress callback.
            )

            # Below is a fix for later versions of Metashape (2.2.1 and 2.2.2) that have a bug in the scalebar optimization.
            # Get initial scale
            initial_scale = doc.chunk.transform.scale or 1.0
            print(f"Initial scale: {initial_scale}")
            print(
                f"Initial total error: {calculate_total_error(initial_scale, doc):.6f} m\n"
            )
            # Set search bounds (adjust these based on your expected scale range)
            # Using a wide range around the initial scale
            scale_low = 1e-6
            scale_high = 1e6
            # Perform binary search
            optimal_scale, optimal_error = binary_search_optimal_scale(
                scale_low, scale_high, doc
            )
            print("\n=== Binary Search Results ===")
            print(f"Optimal scale: {optimal_scale:.6f}")
            print(f"Optimal total error: {optimal_error:.6f} m\n")
            print("Individual scalebar errors with optimal scale:")
            for i, scalebar in enumerate(doc.chunk.scalebars):
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
                estimated_distance = (point1 - point0).norm() * optimal_scale
                reference_distance = scalebar.reference.distance
                error_distance = estimated_distance - reference_distance
                print(f"{i}. ({scalebar.label}) error: {1000 * error_distance:,.2f} mm")
            ## Apply the optimal scale
            print(f"doc.chunk.transform.scale = {optimal_scale}")
            doc.chunk.transform.scale = optimal_scale

        print(
            f"Estimated scale factor: {doc.chunk.transform.scale:f}",
            file=sys.stderr,
        )

    ## Step X. Triangulate points
    elif stage == "triangulate":
        if metashape_major_version == "1.8":
            triangulatePoints = doc.chunk.triangulatePoints
        else:  # renamed in Metashape 2.0 onwards
            triangulatePoints = doc.chunk.triangulateTiePoints

        with TqdmProgressBar(desc="Triangulating points") as t:
            triangulatePoints(
                max_error=10,  # (float) – Reprojection error threshold.
                min_image=2,  # (int) – Minimum number of point projections.
                progress=t.update_to,
            )

    elif stage == "optimizecameras":
        with TqdmProgressBar(desc="Optimizing cameras") as t:
            doc.chunk.optimizeCameras(progress=t.update_to)

    ## Step X. Filter tie points by reconstruction uncertainty
    elif stage == "filter_ru":
        with TqdmProgressBar(
            desc=f"Filtering by reconstruction uncertainty ({args.filter_ru})"
        ) as t:
            filter = TiePoints.Filter()
            filter.init(
                doc.chunk,
                TiePoints.Filter.ReconstructionUncertainty,
                progress=t.update_to,
            )
            filter.removePoints(args.filter_ru)

    ## Step X. Filter tie points by projection accuracy
    elif stage == "filter_pa":
        with TqdmProgressBar(
            desc=f"Filtering by projection accuracy ({args.filter_pa})"
        ) as t:
            filter = TiePoints.Filter()
            filter.init(
                doc.chunk, TiePoints.Filter.ProjectionAccuracy, progress=t.update_to
            )
            filter.removePoints(args.filter_pa)

    ## Step X. Filter tie points by reprojection error
    elif stage == "filter_re":
        with TqdmProgressBar(
            desc=f"Filtering by reprojection error ({args.filter_re})"
        ) as t:
            filter = TiePoints.Filter()
            filter.init(
                doc.chunk, TiePoints.Filter.ReprojectionError, progress=t.update_to
            )
            filter.removePoints(args.filter_re)

    ## Step 7. Build dense point cloud
    ## "In the version 1.4.2 the complete dense cloud generation procedure is split to the two parts:
    ##  depth maps generation and dense cloud reconstruction itself."
    ## Source: https://www.agisoft.com/forum/index.php?topic=9017.0
    elif stage == "depthmaps":
        with TqdmProgressBar(desc="Building depth maps") as t:
            doc.chunk.buildDepthMaps(
                ## 0 = Highest (double resolution),
                ## 1 = Ultra (original resolution),
                ## 2 = High (half resolution),
                ## 4 = Medium (quarter resolution),
                ## 8 = Low (one eight resolution)
                ## 16 = Low (one sixteenth resolution)
                ## -- https://www.agisoft.com/forum/index.php?topic=11697.0
                downscale=4,  # (int) – Depth map quality.
                # filter_mode=Metashape.FilterMode.MildFiltering,  # (FilterMode) – Depth map filtering mode.
                # [cameras,]  # (list of int) – List of cameras to process.
                # reuse_depth=False,  # (bool) – Enable reuse depth maps option.
                # max_neighbors=16,  # (int) – Maximum number of neighbor images to use for depth map generation.
                # subdivide_task=True,  # (bool) – Enable fine-level task subdivision.
                workitem_size_cameras=64,  # (int) – Number of cameras in a workitem. [default: 20]
                max_workgroup_size=1024,  # (int) – Maximum workgroup size. [default: 100]
                progress=t.update_to,  # (Callable[[float], None]) – Progress callback.
            )

    elif stage == "densecloud":
        if metashape_major_version == "1.8":
            buildDenseCloud = doc.chunk.buildDenseCloud
        else:  # renamed in Metashape 2.0 onwards
            buildDenseCloud = doc.chunk.buildPointCloud

        with TqdmProgressBar(desc="Building dense cloud") as t:
            buildDenseCloud(
                # point_colors=True,  # (bool) – Enable point colors calculation.
                # point_confidence=False,  # (bool) – Enable point confidence calculation. [default: False]
                # keep_depth=True,  # (bool) – Enable store depth maps option.
                # max_neighbors=100,  # (int) – Maximum number of neighbor images to use for depth map filtering.
                # subdivide_task=True,  # (bool) – Enable fine-level task subdivision.
                workitem_size_cameras=64,  # (int) – Number of cameras in a workitem. [default: 20]
                max_workgroup_size=1024,  # (int) – Maximum workgroup size. [default: 100]
                progress=t.update_to,  # (Callable[[float], None]) – Progress callback.
            )

    ## Step 8. Build model
    elif stage == "model":
        with TqdmProgressBar(desc="Building model") as t:
            doc.chunk.buildModel(
                # surface_type=Arbitrary,  # (SurfaceType) – Type of object to be reconstructed.
                # interpolation=EnabledInterpolation,  # (Interpolation) – Interpolation mode.
                ## "The number of target polygons in the High/Medium/Low presets depend on the number of
                ## points in the source point cloud, the ratio is 1/5, 1/15, and 1/45 respectively."
                ## Source: https://www.agisoft.com/forum/index.php?topic=9370.0
                # face_count=Metashape.FaceCount.HighFaceCount,  # (FaceCount) – Target face count.
                face_count=Metashape.FaceCount.CustomFaceCount,
                face_count_custom=2000000,  # (int) – Custom face count.
                # source_data=DenseCloudData,  # (DataSource) – Selects between dense point cloud, tie points and depth maps.
                vertex_colors=not args.skip_vertex_colors,  # (bool) – Enable vertex colors calculation.
                # vertex_confidence=True,  # (bool) – Enable vertex confidence calculation.
                # volumetric_masks=False,  # (bool) – Enable strict volumetric masking.
                # keep_depth=True,  # (bool) – Enable store depth maps option.
                # trimming_radius=10,  # (int) – Trimming radius (no trimming if zero).
                # [cameras,]  # (list of int) – List of cameras to process.
                # [classes,]  # s (list of int) – List of dense point classes to be used for surface extraction.
                # subdivide_task=True,  # (bool) – Enable fine-level task subdivision.
                workitem_size_cameras=64,  # (int) – Number of cameras in a workitem. [default: 20]
                max_workgroup_size=1024,  # (int) – Maximum workgroup size. [default: 100]
                progress=t.update_to,  # (Callable[[float], None]) – Progress callback.
            )

    ## Step 9. Build texture
    elif stage == "texture":
        if args.rig in ["eyeful1.0", "eyeful1.5", "eyeful3.0"]:
            texture_size = 16384
        else:
            texture_size = 8192

        with TqdmProgressBar(desc="Building UV map") as t:
            doc.chunk.buildUV(
                # mapping_mode=GenericMapping,  # (MappingMode) – Texture mapping mode.
                # page_count=1,  # (int) – Number of texture pages to generate.
                texture_size=texture_size,  # (int) – Expected size of texture page at texture generation step. [default: 8192]
                # [camera,]  # Camera to be used for texturing in MappingCamera mode.
                progress=t.update_to,  # (Callable[[float], None]) – Progress callback.
            )

        with TqdmProgressBar(desc="Building texture") as t:
            doc.chunk.buildTexture(
                # blending_mode=MosaicBlending,  # (BlendingMode) – Texture blending mode.
                texture_size=texture_size,  # (int) – Texture page size. [default: 8192]
                # fill_holes=True,  # (bool) – Enable hole filling.
                # ghosting_filter=True,  # (bool) – Enable ghosting filter.
                # [cameras,]  # (list of int) – A list of cameras to be used for texturing.
                # texture_type=DiffuseMap,  # (Model.TextureType) – Texture type.
                # [source_model,]  # (int) – Source model.
                # transfer_texture=True,  # (bool) – Transfer texture.
                progress=t.update_to,  # (Callable[[float], None]) – Progress callback.
            )

    ## Step 10. Export mesh + cameras
    elif stage == "export":
        with TqdmProgressBar(desc="Exporting cameras") as t:
            doc.chunk.exportCameras(
                path=str(
                    args.project_dir / "cameras.xml"
                ),  # (string) – Path to output file.
                # format=CamerasFormatXML,  # (CamerasFormat) – Export format.
                # [crs,]  # (CoordinateSystem) – Output coordinate system.
                # save_points=True,  # (bool) – Enables/disables export of automatic tie points. Seems to do nothing with non-COLMAP cameras.
                # save_markers=False,  # (bool) – Enables/disables export of manual matching points.
                # save_invalid_matches=False,  # (bool) – Enables/disables export of invalid image matches.
                # use_labels=False,  # (bool) – Enables/disables label based item identifiers.
                # use_initial_calibration=False,  # (bool) – Transform image coordinates to initial calibration.
                # image_orientation=0,  # (int) – Image coordinate system (0 - X right, 1 - X up, 2 - X left, 3 - X down).
                # chan_rotation_order=RotationOrderXYZ,  # (RotationOrder) – Rotation order (CHAN format only).
                # binary=False,  # (bool) – Enables/disables binary encoding for selected format (if applicable).
                # bundler_save_list=True,  # (bool) – Enables/disables export of Bundler image list file.
                # bundler_path_list='list.txt',  # (string) – Path to Bundler image list file.
                # bingo_save_image=True,  # (bool) – Enables/disables export of BINGO IMAGE COORDINATE file.
                # bingo_save_itera=True,  # (bool) – Enables/disables export of BINGO ITERA file.
                # bingo_save_geoin=True,  # (bool) – Enables/disables export of BINGO GEO INPUT file.
                # bingo_save_gps=False,  # (bool) – Enables/disables export of BINGO GPS/IMU data.
                # bingo_path_itera='itera.dat',  # (string) – Path to BINGO ITERA file.
                # bingo_path_image='image.dat',  # (string) – Path to BINGO IMAGE COORDINATE file.
                # bingo_path_geoin='geoin.dat',  # (string) – Path to BINGO GEO INPUT file.
                # bingo_path_gps='gps-imu.dat',  # (string) – Path to BINGO GPS/IMU file
                progress=t.update_to,  # (Callable[[float], None]) – Progress callback.
            )

            with TqdmProgressBar(desc="Exporting cameras") as t:
                doc.chunk.exportPointCloud(
                    path=str(
                        args.project_dir / "points.ply"
                    ),  # (string) – Path to output file.
                    source_data=Metashape.TiePointsData,  # We don't need all points for reconstructions.
                    # point_cloud=0,  # int - Point cloud key (optional)
                    binary=True,  # bool - Binary encoding (default: True)
                    save_point_color=True,  # bool - Export point color (default: True)
                    # save_point_normal=True,  # bool - Export point normal (default: True)
                    # save_point_intensity=True,  # bool - Export point intensity (default: True)
                    # save_point_classification=True,  # bool - Export point classification (default: True)
                    # save_point_confidence=True,  # bool - Export point confidence (default: True)
                    # save_point_return_number=True,  # bool - Export point return number (default: True)
                    # save_point_scan_angle=True,  # bool - Export point scan angle (default: True)
                    # save_point_source_id=True,  # bool - Export point source ID (default: True)
                    # save_point_timestamp=True,  # bool - Export point timestamp (default: True)
                    # save_point_index=True,  # bool - Export point indices (default: True)
                    # raster_transform=Metashape.RasterTransformNone,  # Metashape.RasterTransformType
                    colors_rgb_8bit=True,  # bool - Convert to 8-bit RGB (default: True)
                    # comment='',  # str - Optional comment (default: '')
                    # save_comment=True,  # bool - Enable comment export (default: True)
                    format=Metashape.PointCloudFormatPLY,  # Metashape.PointCloudFormat
                    # image_format=Metashape.ImageFormatJPEG,  # Metashape.ImageFormat
                    # crs=Metashape.CoordinateSystem(),  # Metashape.CoordinateSystem (optional)
                    # shift=Metashape.Vector([0, 0, 0]),  # Metashape.Vector (optional)
                    # region=Metashape.BBox(),  # Metashape.BBox (optional)
                    # clip_to_boundary=True,  # bool - Clip to boundary shapes (default: True)
                    # clip_to_region=True,  # bool - Clip to chunk region (default: True)
                    # block_width=1000.0,  # float - Block width in meters (default: 1000)
                    # block_height=1000.0,  # float - Block height in meters (default: 1000)
                    # split_in_blocks=False,  # bool - Enable tiled export (default: False)
                    # classes=[0, 1, 2],  # list[int] - Point classes to export (optional)
                    save_images=False,  # bool - Enable image export (default: False)
                    # compression=True,  # bool - Enable compression for Cesium (default: True)
                    # tileset_version='1.0',  # str - Cesium version: '1.0' or '1.1' (default: '1.0')
                    # screen_space_error=16.0,  # float - Screen space error for Cesium (default: 16)
                    # folder_depth=5,  # int - Tileset subdivision depth (default: 5)
                    # viewpoint=Metashape.Viewpoint(),  # Metashape.Viewpoint (optional)
                    # subdivide_task=True,  # bool - Fine-level task subdivision (default: True)
                    progress=t.update_to,  # (Callable[[float], None]) – Progress callback.
                )

        if not args.skip_model_export:
            with TqdmProgressBar(desc="Exporting model") as t:
                doc.chunk.exportModel(
                    path=str(
                        args.project_dir / "mesh.obj"
                    ),  # (string) – Path to output model.
                    # binary=True,  # (bool) – Enables/disables binary encoding (if supported by format).
                    # precision=6,  # (int) – Number of digits after the decimal point (for text formats).
                    # texture_format=ImageFormatJPEG,  # (ImageFormat) – Texture format.
                    # save_texture=True,  # (bool) – Enables/disables texture export.
                    # save_uv=True,  # (bool) – Enables/disables uv coordinates export.
                    # save_normals=True,  # (bool) – Enables/disables export of vertex normals.
                    # save_colors=True,  # (bool) – Enables/disables export of vertex colors.
                    # save_confidence=False,  # (bool) – Enables/disables export of vertex confidence.
                    # save_cameras=True,  # (bool) – Enables/disables camera export.
                    # save_markers=True,  # (bool) – Enables/disables marker export.
                    # save_udim=False,  # (bool) – Enables/disables UDIM texture layout.
                    # save_alpha=False,  # (bool) – Enables/disables alpha channel export.
                    # embed_texture=False,  # (bool) – Embeds texture inside the model file (if supported by format).
                    # strip_extensions=False,  # (bool) – Strips camera label extensions during export.
                    # raster_transform=RasterTransformNone,  # (RasterTransformType) – Raster band transformation.
                    # colors_rgb_8bit=True,  # (bool) – Convert colors to 8 bit RGB.
                    # comment='',  # (string) – Optional comment (if supported by selected format).
                    # save_comment=True,  # (bool) – Enables/disables comment export.
                    format=Metashape.ModelFormatOBJ,  # (ModelFormat) – Export format. [default: ModelFormatNone]
                    # [crs,]  # (CoordinateSystem) – Output coordinate system.
                    # [shift,]  # (Vector) – Optional shift to be applied to vertex coordinates.
                    # clip_to_boundary=True,  # (bool) – Clip model to boundary shapes.
                    # [viewpoint,]  # (Viewpoint) – Default view
                    progress=t.update_to,  # (Callable[[float], None]) – Progress callback.
                )

    # For now, this is just using the default args when you export to COLMAP in metashape
    elif stage == "colmap":
        # Colmap export is only supported in Metashape 2.1.4 and above, but we are likely only using 2.2.0+ or 2.0.2
        if metashape_major_version == "2.2":
            with TqdmProgressBar(desc="Exporting colmaps") as t:
                doc.chunk.exportCameras(
                    path=str(
                        args.project_dir / "colmap/colmap.txt"
                    ),  # (string) – Path to output file.
                    format=Metashape.CamerasFormatColmap,  # (CamerasFormat) – Export format.
                    save_images=True,  # (bool) – Enables/disables export of image list for colmaps
                    # [crs,]  # (CoordinateSystem) – Output coordinate system.
                    save_points=True,  # (bool) – Enables/disables export of automatic tie points.
                    convert_to_pinhole=True,  # (bool) – Transform images to pinhole model without distortions.
                    # image_path="images",  # (string) – Path to output images folder.
                    # save_markers=False,  # (bool) – Enables/disables export of manual matching points.
                    # save_invalid_matches=False,  # (bool) – Enables/disables export of invalid image matches.
                    # use_labels=False,  # (bool) – Enables/disables label based item identifiers.
                    # use_initial_calibration=False,  # (bool) – Transform image coordinates to initial calibration.
                    # image_orientation=0,  # (int) – Image coordinate system (0 - X right, 1 - X up, 2 - X left, 3 - X down).
                    # chan_rotation_order=RotationOrderXYZ,  # (RotationOrder) – Rotation order (CHAN format only).
                    binary=True,  # (bool) – Enables/disables binary encoding for selected format (if applicable).
                    # bundler_save_list=True,  # (bool) – Enables/disables export of Bundler image list file.
                    # bundler_path_list='list.txt',  # (string) – Path to Bundler image list file.
                    # bingo_save_image=True,  # (bool) – Enables/disables export of BINGO IMAGE COORDINATE file.
                    # bingo_save_itera=True,  # (bool) – Enables/disables export of BINGO ITERA file.
                    # bingo_save_geoin=True,  # (bool) – Enables/disables export of BINGO GEO INPUT file.
                    # bingo_save_gps=False,  # (bool) – Enables/disables export of BINGO GPS/IMU data.
                    # bingo_path_itera='itera.dat',  # (string) – Path to BINGO ITERA file.
                    # bingo_path_image='image.dat',  # (string) – Path to BINGO IMAGE COORDINATE file.
                    # bingo_path_geoin='geoin.dat',  # (string) – Path to BINGO GEO INPUT file.
                    # bingo_path_gps='gps-imu.dat',  # (string) – Path to BINGO GPS/IMU file
                    progress=t.update_to,  # (Callable[[float], None]) – Progress callback.
                )

    ## Step 11. Export report
    elif stage == "report":
        with TqdmProgressBar(desc="Exporting report") as t:
            doc.chunk.exportReport(
                path=str(
                    Path(doc.path).with_suffix(".pdf")
                ),  # (string) – Path to output report.
                # title='',  # (string) – Report title.
                # description='',  # (string) – Report description.
                # font_size=12,  # (int) – Font size (pt).
                # page_numbers=True,  # (bool) – Enable page numbers.
                # include_system_info=True,  # (bool) – Include system information.
                # [user_settings,]  # (list of (string, string) tuples) – A list of user defined settings to include on the Processing Parameters page.
                progress=t.update_to,  # (Callable[[float], None]) – Progress callback.
            )

    ## Step 12. Save the project
    elif stage == "save":
        doc.save(
            str(args.project_dir / (args.project_dir.name + f"-{stage_index}-wip.psx"))
        )

    else:
        raise NotImplementedError(f"Stage '{stage}' not implemented.")

    ## Save the project after running each stage
    if args.save_often:
        save_path = args.project_dir / (
            args.project_dir.name + f"-{stage_index}-{stage}.psx"
        )
        print(f"Saving project to '{save_path}'", file=sys.stderr)
        doc.save(str(save_path))


## Save project after all stages are run
print("\nFinal steps ...", file=sys.stderr)
output_filename = str(args.project_dir / (args.project_dir.name + "-final.psx"))
if args.output:
    output_filename = str(args.project_dir / args.output)
print(f"Saving project to {output_filename} ...", file=sys.stderr)
doc.save(output_filename)


## Export final report (optional)
if args.report:
    with TqdmProgressBar(desc="Exporting report") as t:
        doc.chunk.exportReport(
            path=str(
                Path(doc.path).with_suffix(".pdf")
            ),  # (string) – Path to output report.
            # title='',  # (string) – Report title.
            # description='',  # (string) – Report description.
            # font_size=12,  # (int) – Font size (pt).
            # page_numbers=True,  # (bool) – Enable page numbers.
            # include_system_info=True,  # (bool) – Include system information.
            # [user_settings,]  # (list of (string, string) tuples) – A list of user defined settings to include on the Processing Parameters page.
            progress=t.update_to,  # (Callable[[float], None]) – Progress callback.
        )

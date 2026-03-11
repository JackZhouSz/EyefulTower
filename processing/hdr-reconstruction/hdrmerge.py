# (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

"""
This script performs RAW image debayering and HDR image merging.
"""

import argparse
import csv
import json
import os
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

## Enable OpenEXR support in OpenCV (https://github.com/opencv/opencv/issues/21326)
os.environ["OPENCV_IO_ENABLE_OPENEXR"] = "1"
import cv2
import exifread  # install: pip install --user exifread /OR/ conda install -c conda-forge exifread
import numpy as np
import torch
from tqdm.contrib.concurrent import thread_map


def circle_mask(
    image_shape: tuple[int, ...],
    center: np.ndarray | None = None,
    radius: int | None = None,
) -> np.ndarray:
    """Returns a boolean mask for a circular region within the given image shape."""
    h, w = image_shape[:2]

    if center is None:
        center = np.array([w / 2, h / 2])
    center = np.array(center).reshape((1, 1, 2))

    if radius is None:
        # Entaniya HAL 200: 200° FOV, equidistant projection
        fov_rad = np.radians(180)
        diagonal_pixels = np.sqrt(w**2 + h**2)
        radius = int((diagonal_pixels / 2) * (fov_rad / np.pi))

        # Safety bounds
        max_radius = min(w, h) // 2
        radius = min(radius, max_radius)

        print(f"Auto-calculated Entaniya HAL 180 radius: {radius} pixels")

    mgrid = np.stack(np.meshgrid(np.arange(w), np.arange(h)), axis=2)  # [h w 2]
    rads = np.linalg.norm(mgrid - center, axis=2)

    if len(image_shape) > 2:
        rads = np.repeat(rads[:, :, None], image_shape[2], axis=2)

    return rads < radius


def tent(x: np.ndarray) -> np.ndarray:
    """Tent weighting function peaking at 0.5."""
    return 1 - 2 * np.abs(x - 0.5)


def raised_tent(x: np.ndarray, amount: float = 1e-6) -> np.ndarray:
    """Tent weighting function with a minimum value of `amount` at the endpoints."""
    return 1 - 2 * (1 - amount) * np.abs(x - 0.5)


def get_exif_metadata(raw_file: Path) -> dict:
    """Extracts EXIF metadata from a RAW image and computes its exposure value (EV)."""
    with open(raw_file, "rb") as fh:
        # Don’t process makernote tags, don’t extract the thumbnail image (if any).
        tags = exifread.process_file(fh)

        f_number = tags["EXIF FNumber"].values[0].decimal()
        exp_time = tags["EXIF ExposureTime"].values[0].decimal()
        iso_speed = tags["EXIF ISOSpeedRatings"].values[0]

        # Correct the nominal values reported by the camera to actual power-of-two values.
        # For example, 1/60 seconds shutter time is actually 1/64 seconds long.
        # Source: https://www.scantips.com/lights/fstop2.html
        if f_number != 0.0:
            f_number_stop = np.round(3 * 2 * np.log2(f_number), 0) / 3
            f_number = np.sqrt(2**f_number_stop)

        exp_time_stop = np.round(3 * np.log2(exp_time), 0) / 3
        exp_time = 2**exp_time_stop

        iso_speed_stop = np.round(3 * np.log2(iso_speed / 100), 0) / 3
        iso_speed = 2 ** (np.log2(100) + iso_speed_stop)

        if f_number == 0.0:
            ## The Entaniya lenses on Eyeful Tower report an f-number of zero, which we will ignore.
            ev: float = -np.log2(exp_time * iso_speed / 100)
        else:
            # ev = np.log2((f_number ** 2) / exp_time) - np.log2(iso_speed / 100)  # Eq. 15 in ADOP but with fixed sign
            ev: float = 2 * np.log2(f_number) - np.log2(exp_time * iso_speed / 100)
        # print(f"{raw_file}: f/{f_number:.2f}, {exp_time:.4f} s, ISO {iso_speed:.0f} => EV={ev:6.3f}")

        # # [Debug] Print all EXIF tags
        # for tag, value in tags.items():
        #     if tag not in ('JPEGThumbnail', 'TIFFThumbnail', 'Filename', 'EXIF MakerNote'):
        #         print(f"{tag}: {value}")
        # print()

        return {
            "file": raw_file,
            "f_number": f_number,
            "exp_time": exp_time,
            "iso_speed": iso_speed,
            "ev": ev,
        }


def list_raw_images(
    path: Path,
    extension: str,
    desc: str = "Reading EXIF metadata",
    max_workers: int = 16,
) -> list[dict]:
    """Lists all files matching the `path` expression using `glob`, and returns a list of
    dictionaries that are sorted by `filename`."""

    ## List matching filenames
    raw_files = path.rglob(f"*.{extension}")
    raw_files = [Path(p).resolve() for p in raw_files]
    raw_files.sort()

    if not raw_files:
        raise FileNotFoundError(
            f"No '{extension}' images found at '{path}'. Please check path."
        )

    ## Get EXIF metadata for each RAW image
    image_list = thread_map(
        get_exif_metadata, raw_files, max_workers=max_workers, desc=desc
    )

    ## Path relative to input directory
    for image in image_list:
        image["relpath"] = str(image["file"].relative_to(path))

    return image_list


def group_image_stacks(image_list: list[dict]) -> list[list[dict]]:
    """Groups a sequence of images into stacks based on their EVs, assuming stacks were captured
    with increasing exposures, i.e. decreasing EVs."""

    stack = None
    stacks: list[list[dict]] = []
    last_ev: float = -1000
    for image in image_list:
        if image["ev"] >= last_ev:  # start of new stack
            if stack:  # push previous stack
                stacks.append(stack)
            stack = [image]  # start new stack
        else:
            stack.append(image)  # add image to current stack
        last_ev = image["ev"]  # keep track of most recent EV

    if stack:  # push final stack
        stacks.append(stack)

    return stacks


def group_image_brackets(
    image_list: list[dict],
    images_per_bracket: int,
) -> list[list[dict]]:
    """Groups a sequence of images into fixed-sized stacks, e.g. every set of 9 images."""

    stacks = []
    for i in range(0, len(image_list), images_per_bracket):
        ## Sanity check that all images are actually in the same directory, not different ones
        if len({e["file"].parent for e in image_list[i : i + images_per_bracket]}) > 1:
            print(image_list[i : i + images_per_bracket])
            raise ValueError("Image stack mixes images in more than one directory!")
        stacks.append(image_list[i : i + images_per_bracket])

    return stacks


def single_image_stacks(image_list: list[dict]) -> list[list[dict]]:
    """Converts a list of images into a list of single-image stacks."""
    return [[image] for image in image_list]


def subtract_mean_ev(stacks: list[list[dict]]) -> list[list[dict]]:
    """Subtracts the mean EV across all stacks from all EV, such that average exposure means EV=0."""
    mean_ev: float = np.concatenate(
        [[i["ev"] for i in stack] for stack in stacks]
    ).mean()
    updated = [
        [{**i, "delta_ev": i["ev"] - mean_ev} for i in stack] for stack in stacks
    ]
    return updated


def compute_PSNR_exposures(
    hdr_tensor: torch.Tensor,
    raws_tensor: torch.Tensor,
    delta_evs: list[float],
    verbose: bool = True,
) -> torch.Tensor:
    """Computes PSNR between tone-mapped HDR and RAW images across all exposures."""
    input_tm_tensor = torch.clip(
        torch.pow(raws_tensor.detach() / (2**16 - 1), 1 / 2.2), 0, 1
    )
    hdr_tm_tensor = torch.clamp(
        torch.pow(torch.clamp(hdr_tensor.detach(), min=0) / (2**16 - 1), 1 / 2.2),
        0,
        1,
    )

    mse = torch.mean((input_tm_tensor - hdr_tm_tensor) ** 2, dim=[1, 2, 3])
    psnr = 20 * torch.log10(1 / torch.sqrt(mse))

    if verbose:
        for i in range(len(raws_tensor)):
            print(f"  {i}. {delta_evs[i]:+.1f} EV: {psnr[i]:.2f} dB")
        print(f"     Average: {torch.mean(psnr).item():.2f} dB")

    return psnr


def compute_PSNR(
    hdr_image: torch.Tensor | np.ndarray,
    raws_tensor: torch.Tensor,
    delta_evs: list[float],
    verbose: bool = True,
    debug: bool = False,
) -> torch.Tensor:
    """Computes per-exposure PSNR between a reconstructed HDR image and the RAW inputs."""
    if torch.is_tensor(hdr_image):
        hdr_image_tensor = hdr_image.detach()
    else:
        hdr_image_tensor = torch.tensor(hdr_image, device=raws_tensor.device)

    if torch.is_tensor(delta_evs):
        delta_evs_tensor = delta_evs.detach()
    else:
        delta_evs_tensor = torch.tensor(
            delta_evs, dtype=float, device=raws_tensor.device
        )
    delta_evs_tensor = delta_evs_tensor.reshape([-1])

    if debug:
        debug_dir: Path = Path("debug")
        debug_dir.mkdir(parents=True, exist_ok=True)

    psnr = []
    for i in range(len(raws_tensor)):
        input_tm_tensor = torch.clamp(
            torch.pow(raws_tensor[i].detach() / (2**16 - 1), 1 / 2.2), 0, 1
        )
        hdr_tm_tensor = torch.clamp(
            torch.pow(
                torch.clamp(hdr_image_tensor / (2 ** delta_evs_tensor[i]), min=0)
                / (2**16 - 1),
                1 / 2.2,
            ),
            0,
            1,
        )
        mse = torch.mean((input_tm_tensor - hdr_tm_tensor) ** 2)
        psnr.append(20 * torch.log10(1 / torch.sqrt(mse)).item())

        if verbose:
            print(f"  {i}. {delta_evs[i]:+.1f} EV: {psnr[i]:5.2f} dB")

        if debug:
            cv2.imwrite(  # Tone-mapped input image
                str(debug_dir / f"{i:02d}-input_tm.jpg"),
                255 * input_tm_tensor.cpu().numpy()[:, :, ::-1],
            )
            cv2.imwrite(  # Tone-mapped HDR image
                str(debug_dir / f"{i:02d}-hdr_tm-PSNR{psnr[-1]:.2f}.jpg"),
                255 * hdr_tm_tensor.cpu().numpy()[:, :, ::-1],
            )

            diff_export = np.linalg.norm(
                input_tm_tensor.cpu().numpy().astype(np.float32)
                - hdr_tm_tensor.cpu().numpy().astype(np.float32),
                axis=2,
            )
            diff_export = np.clip(10 * 255 * diff_export, 0, 255).astype(np.uint8)
            diff_export = cv2.applyColorMap(diff_export, cv2.COLORMAP_MAGMA)
            cv2.imwrite(  # Error map visualisation
                str(debug_dir / f"{i:02d}-diff-PSNR{psnr[-1]:.2f}.jpg"),
                diff_export,
            )

    psnr = torch.tensor(psnr)
    if verbose:
        print(f"     Average: {torch.mean(psnr).item():.2f} dB")

    return psnr


def saturate_fix(
    irradiance: torch.Tensor,
    raws_tensor: torch.Tensor,
    delta_evs: list[float],
    threshold: float,
) -> None:
    """Fixes pixels in `irradiance` that are saturated in all images of the exposure stack."""

    ## Set pixels with any channel saturated in all images to the least-saturated color.
    max_ev = np.argmax(delta_evs)  # lowest exposure
    any_saturated = (raws_tensor >= threshold * 2**16).any(dim=3).all(dim=0)
    irradiance[any_saturated] = raws_tensor[max_ev, ...][any_saturated] * (
        2 ** delta_evs[max_ev]
    )


def merge_DM1997_numpy(
    raws: list[np.ndarray],
    delta_evs: list[float],
) -> np.ndarray:
    """HDR reconstruction per Eq. 6 in Debevec and Malik 1997 using NumPy."""

    acc = 0
    for i, raw in enumerate(raws):
        img = raw.astype(np.float32)

        weight = tent(img / (2**16 - 1))

        log_img = np.log2(img + 1e-10)
        acc += np.concatenate([weight * (log_img + delta_evs[i]), weight], axis=2)

    log_irradiance = acc[:, :, :3] / (acc[:, :, 3:] + 1e-10)
    return 2**log_irradiance


def merge_DM1997_torch(
    raws_tensor: torch.Tensor,
    delta_evs: list[float],
    saturate: bool = True,
) -> torch.Tensor:
    """HDR reconstruction per Eq. 6 in Debevec and Malik 1997 using PyTorch with tweak that ensures all-saturated pixels are preserved."""

    log_irradiance = (
        (
            torch.log2(raws_tensor + 1e-10)
            + torch.tensor(
                delta_evs, dtype=torch.float32, device=raws_tensor.device
            ).reshape([-1, 1, 1, 1])
        )
        * (1 - 2 * torch.abs(raws_tensor / (2**16 - 1) - 0.5))
    ).sum(dim=0) / (
        (1 - 2 * torch.abs(raws_tensor / (2**16 - 1) - 0.5)).sum(dim=0) + 1e-10
    )

    ## Tweak: Set all-saturated pixels to lowest value that saturates in all images.
    if saturate:
        log_irradiance[(raws_tensor >= 0.98 * 2**16).all(dim=0)] = 16 + np.max(
            delta_evs
        )

    return 2**log_irradiance


def merge_PPNE(
    raws_tensor: torch.Tensor,
    delta_evs: list[float],
    saturate: bool = True,
    threshold: float = 0.98,
    black_level: float = 0.01,
) -> torch.Tensor:
    """HDR reconstruction via Poisson Photon Noise Estimator (PPNE; Hanji et al. 2020)."""

    acc = torch.zeros(
        raws_tensor[0].shape, dtype=torch.float32, device=raws_tensor.device
    )
    weight = torch.zeros(
        raws_tensor[0].shape, dtype=torch.float32, device=raws_tensor.device
    )

    for i, raw_tensor in enumerate(raws_tensor):
        unsaturated = torch.logical_and(
            black_level * 2**16 < raw_tensor, raw_tensor < threshold * 2**16
        )
        acc[unsaturated] += raw_tensor[unsaturated]
        weight[unsaturated] += 2 ** -delta_evs[i]  # exposure time ~= 2^(-EV)

    irradiance = acc / (weight + 1e-10)

    if saturate:
        saturate_fix(irradiance, raws_tensor, delta_evs, threshold)

    return irradiance


def merge_robust_PPNE(
    raws_tensor: torch.Tensor,
    delta_evs: list[float],
    saturate: bool = True,
    threshold: float = 0.9,
    black_level: float = 0.01,
) -> torch.Tensor:
    """HDR reconstruction via a robustified Poisson Photon Noise Estimator (PPNE; Hanji et al. 2020)."""

    ## We observed on the Sony A1 RAW images that for some unknown reason, values do not saturate
    ## as quickly as expected. This produces outliers that can drag down the estimated irradiance
    ## sufficiently to cause visible colour changes. The tensor `unsaturated_minval` keeps track
    ## of the minimum irradiance estimate per pixel, such that it can be ignored (assuming there
    ## are enough unsaturated observations, hence keeping `unsaturated_count` as well).
    unsaturated_minval = 2**16 * torch.ones(
        raws_tensor[0].shape, dtype=torch.float32, device=raws_tensor.device
    )
    unsaturated_count = torch.zeros(
        raws_tensor[0].shape, dtype=torch.uint8, device=raws_tensor.device
    )

    for i, raw_tensor in enumerate(raws_tensor):
        unsaturated = torch.logical_and(
            black_level * 2**16 < raw_tensor, raw_tensor < threshold * 2**16
        )
        unsaturated_minval[unsaturated] = torch.min(
            raw_tensor[unsaturated] / (2 ** -delta_evs[i]),
            unsaturated_minval[unsaturated],
        )
        unsaturated_count[unsaturated] += 1

    accumulator = torch.zeros(
        raws_tensor[0].shape, dtype=torch.float32, device=raws_tensor.device
    )
    weight = torch.zeros(
        raws_tensor[0].shape, dtype=torch.float32, device=raws_tensor.device
    )

    for i, raw_tensor in enumerate(raws_tensor):
        unsaturated = torch.logical_and(
            black_level * 2**16 < raw_tensor, raw_tensor < threshold * 2**16
        )
        use_value = torch.logical_or(
            unsaturated_count[unsaturated] < 3,
            raw_tensor[unsaturated] / (2 ** -delta_evs[i])
            != unsaturated_minval[unsaturated],
        ).float()
        accumulator[unsaturated] += use_value * raw_tensor[unsaturated]
        weight[unsaturated] += (
            use_value * 2 ** -delta_evs[i]
        )  # exposure time ~= 2^(-EV)

    irradiance = accumulator / (weight + 1e-10)

    if saturate:
        saturate_fix(irradiance, raws_tensor, delta_evs, threshold)

    return irradiance


def merge_robust_PPNE2(
    raws_tensor: torch.Tensor,
    delta_evs: list[float],
    saturate: bool = True,
    threshold: float = 0.9,
    black_level: float = 0.01,
) -> torch.Tensor:
    """HDR reconstruction via 2nd-gen robustified Poisson Photon Noise Estimator (Hanji et al. 2020). Only merges pixels where all channels are unsaturated."""

    accumulator = torch.zeros(
        raws_tensor[0].shape, dtype=torch.float32, device=raws_tensor.device
    )
    weight = torch.full_like(accumulator, 1e-10)

    for i, raw_tensor in enumerate(raws_tensor):
        unsaturated = torch.logical_and(
            black_level * 2**16 < raw_tensor,
            (raw_tensor < threshold * 2**16).all(dim=2, keepdim=True),
        )

        accumulator[unsaturated] += raw_tensor[unsaturated]
        weight[unsaturated] += 2 ** -delta_evs[i]  # exposure time ~= 2^(-EV)

    irradiance = accumulator / weight

    if saturate:
        saturate_fix(irradiance, raws_tensor, delta_evs, threshold)

    return irradiance


def merge_max(
    raws_tensor: torch.Tensor,
    delta_evs: list[float],
) -> torch.Tensor:
    """HDR reconstruction via pixel-wise maximum, e.g. from a burst of exposures."""

    torch_delta_evs = torch.tensor(
        delta_evs, dtype=torch.float32, device=raws_tensor.device
    )
    torch_delta_evs = torch_delta_evs.reshape([-1, 1, 1, 1])
    irradiance, _ = torch.max(raws_tensor * (2**torch_delta_evs), dim=0)

    return irradiance


def run_cmd_with_log(cmd: list[str], logfile: Path) -> None:
    """Runs a shell command and writes its output to a log file."""
    with open(logfile, "w", encoding="utf-8", newline="\n") as log:
        log.write("Running command:\r\n")
        log.write(100 * "-" + "\r\n")
        log.write((" ".join(cmd)) + "\r\n")
        log.write(100 * "-" + "\r\n")

        output = subprocess.run(cmd, capture_output=True)
        log.write(output.stdout.decode("utf-8"))
        log.write((100 * "-") + "\r\n")
        log.write(f"Return code: {output.returncode}\r\n")

        if output.returncode != 0:
            print()
            print(
                f'Error: return code {output.returncode} when running "{" ".join(cmd)}"'
            )
            print(f'  For details, see "{logfile}"')


def merge_stack_to_hdr(
    dataset_dir: Path,
    device_handle: dict[str, Any],
    stack: list[dict[str, Any]],
    merge_method_name: str,
    merge_method: Callable[..., torch.Tensor],
    args: argparse.Namespace,
) -> None:
    """Merges an exposure stack into an HDR EXR image and writes a per-stack log."""
    exr_path = (dataset_dir / stack[0]["relpath"]).with_suffix(".exr")
    log_path = exr_path.with_suffix(".log")
    exr_path.parent.mkdir(parents=True, exist_ok=True)

    with open(log_path, "w", encoding="utf-8", newline="\n") as log:
        log.write("Merging image stack:\r\n")
        for image in stack:
            log.write(
                "  - {file}: f/{f_number:.2f}, {exp_time:.4f} s, ISO {iso_speed:.0f} => {ev:6.3f} EV ~ {delta_ev:+.3f} EV\r\n".format(
                    **image
                )
            )
        log.write("\r\n")

        ## Load linear 16-bit RAW RGB images
        raws = [
            cv2.imread(str(image["file"]), cv2.IMREAD_UNCHANGED)[:, :, ::-1]
            for image in stack
        ]
        log.write(
            f"Loaded {len(raws)} {raws[0].dtype} image(s) with resolution {raws[0].shape[1]}×{raws[0].shape[0]}\r\n"
        )

        ## Arguments to pass the selected HDR merging function
        if merge_method_name in ["PPNE", "R-PPNE", "R-PPNE2"]:
            method_args = {
                "black_level": args.black_level,
                "threshold": args.threshold,
                "saturate": True,
            }
        elif merge_method_name == "Debevec":
            method_args = {"saturate": True}
        else:
            method_args = {}

        with device_handle["lock"]:
            ## Upload images to GPU
            device = device_handle["device"]
            raws_tensor = torch.tensor(np.stack(raws).astype(np.float32), device=device)
            log.write(
                f"Uploaded {len(raws)} {raws[0].dtype} image(s) with resolution {raws[0].shape[1]}×{raws[0].shape[0]} to {device}\r\n"
            )

            ## HDR reconstruction via the specified method
            delta_evs = [image["delta_ev"] for image in stack]
            irradiance = merge_method(raws_tensor, delta_evs, **method_args)
            log.write(f"Merged to HDR using {merge_method_name}:\r\n")
            for arg, value in method_args.items():
                log.write(f"  - {arg} = {value}\r\n")

            log.write("\r\n")
            psnr = compute_PSNR(
                irradiance, raws_tensor, delta_evs, verbose=False, debug=args.debug
            )
            log.write(
                f"PSNRs = {np.array2string(psnr.cpu().numpy(), precision=2, floatmode='fixed')}\r\n"
            )
            log.write(f"Mean PSNR = {psnr.mean().item():.2f} dB\r\n")

            hdr_image = irradiance / (2**16 - 1)
            hdr_image = hdr_image.detach().cpu().numpy()[:, :, ::-1]

            ## Auto-exposure calculation
            if args.auto_exposure:
                exposure_compensation = calculate_auto_exposure(
                    hdr_image,
                    target_mean=args.target_mean,
                    method=args.auto_exposure_method,
                    stat=args.auto_exposure_stat,
                )
                log.write(
                    f"Auto-exposure compensation: {exposure_compensation:+.3f}\r\n"
                )
            else:
                exposure_compensation = args.exposure
                log.write(f"Manual exposure compensation: {exposure_compensation}\r\n")

            ## Cleanup
            del raws_tensor, irradiance

        # Save with calculated exposure compensation
        cv2.imwrite(
            str(exr_path),
            hdr_image * (2**exposure_compensation),
            params=[cv2.IMWRITE_EXR_COMPRESSION, cv2.IMWRITE_EXR_COMPRESSION_NO],
        )
        log.write(f"Saved output HDR image as {exr_path}\r\n")

        if args.delete_temp:
            log.write("\r\nDeleting temporary files:\r\n")
            for image in stack:
                log.write(f"  - {image['file']}\r\n")
                os.unlink(image["file"])


def calculate_auto_exposure(
    hdr_image: np.ndarray | torch.Tensor,
    target_mean: float = 0.2,
    method: str = "global",
    stat: str = "mean",
) -> float:
    """
    Calculate automatic exposure compensation to achieve target mean brightness.

    Args:
        hdr_image: HDR image array (numpy or torch tensor)
        target_mean: Target mean brightness value (default: 0.2)
        method: "global" for entire image, "center" for center crop, "samples" for random sampling

    Returns:
        exposure_compensation: Value to use for --exposure argument
    """
    stat_method = np.mean if stat == "mean" else np.median

    if torch.is_tensor(hdr_image):
        hdr_array = hdr_image.detach().cpu().numpy()
    else:
        hdr_array = hdr_image

    mask = circle_mask(hdr_array.shape)
    valid = hdr_array[mask[:, :, 0]]
    current_stat = stat_method(valid)

    # Calculate required exposure compensation
    if current_stat <= 0:
        print(
            f"Warning: Current mean is {current_stat}, using default exposure compensation"
        )
        return 0.0

    scale_factor = target_mean / current_stat
    exposure_compensation = np.log2(scale_factor)

    print(
        f"Auto-exposure: current_stat={current_stat:.6f}, target={target_mean}, scale={scale_factor:.3f}x, exposure={exposure_compensation:+.2f}"
    )

    return exposure_compensation


def save_stacks_csv(
    stacks: list[list[dict[str, Any]]],
    filename: str | Path,
) -> None:
    """Writes exposure stack metadata to a CSV file."""
    with open(filename, "w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, delimiter=",", quotechar='"', quoting=csv.QUOTE_MINIMAL)
        writer.writerow(
            ["Filename", "F Number", "Exposure Time", "ISO Speed", "EV", "Delta EV"]
        )
        for stack in stacks:
            writer.writerow([])
            for image in stack:
                writer.writerow(
                    [
                        image["file"],
                        image["f_number"],
                        image["exp_time"],
                        image["iso_speed"],
                        image["ev"],
                        image["delta_ev"],
                    ]
                )


def save_stacks_json(
    stacks: list[list[dict[str, Any]]],
    filename: str | Path,
) -> None:
    """Writes exposure stack metadata to a JSON file."""
    with open(filename, "w", encoding="utf-8") as fh:
        json.dump(
            [
                [{**image, "file": image["file"].as_posix()} for image in stack]
                for stack in stacks
            ],
            fh,
            ensure_ascii=False,
            indent=4,
        )


if __name__ == "__main__":
    import shutil
    import tempfile
    import threading
    import time
    import zipfile
    from functools import partial

    from tqdm import tqdm

    ## Colour spaces supported by dcraw_emu.
    dcraw_colour_spaces = {
        "raw": 0,
        "sRGB": 1,
        "Adobe": 2,
        "Wide": 3,
        "ProPhoto": 4,
        "XYZ": 5,
        "ACES": 6,
        "DCI-P3": 7,
        "Rec2020": 8,
    }

    # HDR merging methods provided in this file.
    merge_methods = {
        "Debevec": merge_DM1997_torch,
        "Max": merge_max,
        "PPNE": merge_PPNE,
        "R-PPNE": merge_robust_PPNE,
        "R-PPNE2": merge_robust_PPNE2,
    }

    start_time = time.time()

    ## Parse command line arguments.
    parser = argparse.ArgumentParser(
        description="Tool for merging RAW images into HDR EXR images."
    )
    parser.add_argument(
        "dataset_dir",
        metavar="dataset_dir",
        type=Path,
        help="Path to the dataset to process.",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        help="Output path, if different to `dataset_dir`.",
    )
    parser.add_argument(
        "--tempdir",
        type=Path,
        default=Path(tempfile.gettempdir()),
        help="Path to temporary directory (default: system temp).",
    )
    parser.add_argument(
        "--name",
        type=str,
        help="Dataset name (default: name of `dataset_dir`).",
    )
    parser.add_argument(
        "--dcraw",
        type=str,
        default="./dcraw_emu",
        help="Path to LibRaw's `dcraw_emu` sample binary (default: './dcraw_emu').",
    )
    parser.add_argument(
        "-c",
        "--colour-space",
        dest="colour_space",
        default="DCI-P3",
        choices=dcraw_colour_spaces.keys(),
        help="Output colour space (default: DCI-P3)",
    )
    parser.add_argument(
        "--rotate",
        default=True,
        action=argparse.BooleanOptionalAction,
        help="Rotate RAW images based on embedded orientation tag (default: True)",
    )
    parser.add_argument(
        "-i",
        "--image-format",
        default="ARW",
        type=str,
        help="Extension of RAW images (default: ARW)",
    )
    parser.add_argument(
        "-e",
        "--exposure",
        default=0.0,
        type=float,
        help="Exposure compensation: 1 == twice as bright (default: 0)",
    )
    parser.add_argument(
        "-m",
        "--merge-method",
        default="R-PPNE",
        choices=merge_methods.keys(),
        help="HDR merging method (default: R-PPNE)",
    )
    parser.add_argument(
        "--black-level",
        default=0.0,
        type=float,
        help="Black-level noise to discard as a fraction of the range of values (default: 0)",
    )
    parser.add_argument(
        "--threshold",
        default=0.9,
        type=float,
        help="Level at which saturated values are ignored (default: 0.9)",
    )
    parser.add_argument(
        "-w",
        "--workers",
        default=64,
        type=int,
        help="Number of worker threads (default: 64)",
    )
    parser.add_argument(
        "--gpu",
        default=True,
        action=argparse.BooleanOptionalAction,
        help="Enable GPU-based merging of HDR images",
    )
    parser.add_argument(
        "--debayering",
        default=True,
        action=argparse.BooleanOptionalAction,
        help="Debayer RAW images into 16-bit linear TIFF images",
    )
    parser.add_argument(
        "--no-brackets",
        default=False,
        action=argparse.BooleanOptionalAction,
        help="Detect exposure brackets to merge into a single image",
    )
    parser.add_argument(
        "--no-merge",
        default=False,
        action=argparse.BooleanOptionalAction,
        help="Merge RAW images into HDR images",
    )
    parser.add_argument(
        "--images-per-bracket",
        type=int,
        default=0,
        help="Number of images per exposure bracket (default: 0 = auto-detect; -1 = all images)",
    )
    parser.add_argument(
        "--delete-temp",
        default=False,
        action=argparse.BooleanOptionalAction,
        help="Delete intermediate TIFF files after merging them",
    )
    parser.add_argument(
        "--zip-logs",
        action="store_true",
        help="Zips up the debayering log files to a file 'hdrmerge-logs.zip'",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Saves additional debug images in 'debug/'",
    )
    parser.add_argument(
        "--auto-exposure",
        action="store_true",
        help="Enable automatic exposure compensation (overrides --exposure)",
    )
    parser.add_argument(
        "--target-mean",
        default=0.2,
        type=float,
        help="Target mean brightness for auto-exposure (default: 0.2)",
    )
    parser.add_argument(
        "--auto-exposure-method",
        default="global",
        choices=["global", "center", "samples"],
        help="Method for calculating auto-exposure: global (entire image), center (center crop), samples (random sampling)",
    )
    parser.add_argument(
        "--auto-exposure-stat",
        default="mean",
        choices=["mean", "median"],
        help="Whether to use mean or median for auto-exposure calculation. Median can be much slower.",
    )

    args = parser.parse_args()
    print("Using arguments:")
    for k, v in vars(args).items():
        print(f"  - {k} = {v}")
    print()

    ## Path to libraw's 'dcraw_emu' binary.
    dcraw = args.dcraw  # try in current directory
    if not os.path.exists(dcraw):
        # try in the same directory as this script
        dcraw = os.path.join(os.path.dirname(__file__), dcraw)
    if not os.path.exists(dcraw):
        # try .exe in the same directory as this script
        dcraw = dcraw + ".exe"
    assert os.path.exists(dcraw), f"dcraw_emu not found at {dcraw}"
    dcraw = os.path.realpath(dcraw)
    print(f"Found dcraw_emu at '{dcraw}'.")

    if args.gpu:
        ## Use all available GPUs for HDR merging.
        available_devices = list(range(torch.cuda.device_count()))
        print(f"Using {len(available_devices)} GPU(s): {available_devices}")
        available_devices = [
            {"device": torch.device(f"cuda:{gpu}"), "lock": threading.Lock()}
            for gpu in available_devices
        ]
    else:
        ## Use one 'cpu' device per worker thread.
        available_devices = [
            {"device": torch.device("cpu"), "lock": threading.Lock()}
            for _ in range(args.workers)
        ]
        print(f"Using {len(available_devices)} CPU core(s).")

    dataset_dir = args.dataset_dir.resolve()
    assert dataset_dir.exists(), f"Dataset directory '{dataset_dir}' not found."
    dataset_name = args.name if args.name is not None else dataset_dir.name
    print(f"Using dataset_name = {dataset_name}")

    ## Create temp dir for TIFFs
    tmp_dir = args.tempdir / "hdrmerge" / dataset_name
    tmp_dir.mkdir(parents=True, exist_ok=True)
    tmp_dir = tmp_dir.resolve()
    print(f"Using tmp_dir = {tmp_dir}")

    ## Output directory
    output_dir = (
        args.output_dir if args.output_dir is not None else dataset_dir / "images"
    )
    print(f"Using output_dir = {output_dir}\n")

    ## List all input files
    if args.debayering:
        files = list_raw_images(
            dataset_dir,
            args.image_format,
            f"Reading {args.image_format} EXIF metadata",
            max_workers=args.workers,
        )
    elif args.merge:
        files = list_raw_images(
            tmp_dir,
            "tiff",
            "Reading TIFF EXIF metadata",
            max_workers=args.workers,
        )
    else:
        print("Info: No work to do as debayering and HDR merging are disabled.")
        exit()

    ## Group files into stacks of images
    if args.brackets:
        if args.images_per_bracket > 0:
            # Use a fixed number of images per bracket
            stacks = group_image_brackets(
                files, images_per_bracket=args.images_per_bracket
            )
        elif args.images_per_bracket == 0:
            # Auto-detect exposure brackets (assuming increasing exposures)
            stacks = group_image_stacks(files)
        else:
            # Merge all images (e.g. for bursts)
            stacks = [files]
    else:
        stacks = single_image_stacks(files)
    stacks = subtract_mean_ev(stacks)

    if args.debayering:
        save_stacks_csv(stacks, tmp_dir / "raw-stacks.csv")
        save_stacks_json(stacks, tmp_dir / "raw-stacks.json")
    elif args.merge:
        save_stacks_csv(stacks, tmp_dir / "tiff-stacks.csv")
        save_stacks_json(stacks, tmp_dir / "tiff-stacks.json")

    ## Group stacks by directory, so we can process them sequentially.
    stacks_per_dir: dict[Path, list[list[dict]]] = {}
    for stack in stacks:
        cam_dir: Path = stack[0]["file"].parent
        if cam_dir in stacks_per_dir:
            stacks_per_dir[cam_dir].append(stack)
        else:
            stacks_per_dir[cam_dir] = [stack]

    if not args.debayering:
        print("Skipping RAW image debayering, as requested by '--no-debayering'.")

    for cam_dir, cam_stacks in stacks_per_dir.items():
        ## Debayer RAW images -----------------------------------------------------------------
        merge_queue: list[list[dict]] = []
        if args.debayering:
            tiff_dir: Path = tmp_dir / cam_stacks[0][0]["file"].parent.name
            tiff_dir.mkdir(exist_ok=True)
            if args.merge:
                print()  # group per-camera progress bars by leaving space between them

            debayer_queue = []
            for stack in cam_stacks:
                tiff_stack: list[dict] = []
                for image in stack:
                    tiff_path = (tiff_dir / image["file"].name).with_suffix(".tiff")
                    log_path = tiff_path.with_suffix(".log")
                    tiff_stack.append({**image, "file": tiff_path})

                    cmd = [
                        dcraw,
                        "-T",  # Write TIFF instead of PPM
                        "-4",  # Linear 16-bit, same as "-6 -W -g 1 1”
                        "-v",
                        "-v",  # Verbose: print progress messages (repeated -v will add verbosity)
                        "-o",
                        str(
                            dcraw_colour_spaces[args.colour_space]
                        ),  # Output colour space
                    ]

                    if not args.rotate:
                        # Don't rotate images based on orientation tag
                        cmd.extend(["-t", "0"])

                    cmd.extend(
                        [
                            "-Z",
                            str(tiff_path),  # Output filename generation rules
                            str(image["file"]),
                        ]
                    )

                    debayer_queue.append([cmd, log_path])
                merge_queue.append(tiff_stack)

            ## Use a thread pool to max out a 64-core Threadripper CPU or more likely the disk.
            thread_map(
                lambda x: run_cmd_with_log(*x),
                debayer_queue,
                max_workers=args.workers,
                desc=f"Debayering RAW images ({cam_dir.name})",
            )

        ## Merge HDR images -----------------------------------------------------------------------
        if args.merge:
            if not args.debayering:
                merge_queue = cam_stacks

            thread_map(
                partial(
                    lambda d, args, x: merge_stack_to_hdr(
                        d,
                        *x,
                        args.merge_method,
                        merge_methods[args.merge_method],
                        args,
                    ),
                    output_dir,
                    args,
                ),
                [
                    (available_devices[i % len(available_devices)], stack)
                    for i, stack in enumerate(merge_queue)
                ],
                max_workers=min(4 * len(available_devices), args.workers),
                desc=(
                    f"Merging HDR images ({cam_dir.name}) using {args.merge_method}"
                    if args.brackets
                    else f"Converting HDR images ({cam_dir.name})"
                ),
            )

    if not args.merge:
        print("Skipping HDR merging, as requested by '--no-merge'.")

    if args.zip_logs:
        with zipfile.ZipFile(
            output_dir / "hdrmerge-logs.zip", "w", zipfile.ZIP_DEFLATED
        ) as zf:
            for item in tqdm(sorted(tmp_dir.glob("**/*")), desc="Zipping log files"):
                if item.is_file() and item.suffix in [".json", ".log"]:
                    zf.write(item, arcname=item.relative_to(tmp_dir))

    if args.delete_temp:
        print(f"Deleting '{tmp_dir}'")
        shutil.rmtree(tmp_dir)

    print(f"--- {(time.time() - start_time):.3f} seconds ---")

# (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

"""Common utilities for pipeline scripts."""

import os
import platform
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Union


def validate_env_vars(required_vars: List[str]) -> None:
    """Validate that all required environment variables are set."""
    missing = [v for v in required_vars if not os.environ.get(v)]
    if missing:
        print("Error: Required environment variables are not set:")
        for var in missing:
            print(f"  - {var}")
        print()
        print(
            "Please set these environment variables in your system or user environment."
        )
        sys.exit(1)


def print_args(args) -> None:
    """Print parsed arguments in the standard repo format."""
    print("Using arguments:")
    for k, v in vars(args).items():
        print(f"  - {k} = {v}")
    print()


def get_code_path() -> Path:
    """Return the HDR_REPO_PATH as a Path object."""
    return Path(os.environ["HDR_REPO_PATH"])


def get_data_path(dataset_name: str) -> Path:
    """Return the dataset data path."""
    return Path(os.environ["DATASETS_PATH"]) / dataset_name


def get_capture_path(dataset_name: str) -> Path:
    """Return the dataset capture path."""
    return Path(os.environ["CAPTURE_DIR"]) / dataset_name


def setup_env(dataset_name: str) -> None:
    """Set common environment variables for pipeline scripts."""
    os.environ["DATA_SET"] = dataset_name
    os.environ["CODE_PATH"] = os.environ["HDR_REPO_PATH"]
    os.environ["CAPTURE_PATH"] = str(get_capture_path(dataset_name))
    os.environ["DATA_PATH"] = str(get_data_path(dataset_name))


def run(
    cmd: List[str],
    check: bool = True,
    capture_output: bool = False,
    cwd: Optional[str] = None,
    log_file: Optional[Path] = None,
) -> subprocess.CompletedProcess:
    """Run a subprocess command with optional logging to file.

    Handles Ctrl+C by terminating the child process before exiting.
    """
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=cwd,
            text=True,
        )
        try:
            stdout, _ = proc.communicate()
        except KeyboardInterrupt:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
            print("\nInterrupted by user. Exiting...")
            sys.exit(1)
        with open(log_path, "w") as f:
            f.write(stdout or "")
        sys.stdout.write(stdout or "")
        if check and proc.returncode != 0:
            print(f"Command failed with exit code {proc.returncode}")
            sys.exit(1)
        return subprocess.CompletedProcess(cmd, proc.returncode, stdout=stdout)
    else:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE if capture_output else None,
            stderr=subprocess.PIPE if capture_output else None,
            cwd=cwd,
            text=capture_output or None,
        )
        try:
            stdout, stderr = proc.communicate()
        except KeyboardInterrupt:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
            print("\nInterrupted by user. Exiting...")
            sys.exit(1)
        if check and proc.returncode != 0:
            raise subprocess.CalledProcessError(
                proc.returncode, cmd, output=stdout, stderr=stderr
            )
        return subprocess.CompletedProcess(
            cmd, proc.returncode, stdout=stdout, stderr=stderr
        )


def run_python(
    script: Union[str, Path],
    args: Optional[List[str]] = None,
    check: bool = True,
    capture_output: bool = False,
    cwd: Optional[str] = None,
    log_file: Optional[Path] = None,
) -> subprocess.CompletedProcess:
    """Run a python script as a subprocess."""
    cmd = [sys.executable, str(script)] + [str(a) for a in (args or [])]
    return run(
        cmd, check=check, capture_output=capture_output, cwd=cwd, log_file=log_file
    )


def validate_white_balance(wb: Optional[str]) -> str:
    """Validate white balance format and return a valid value or default."""
    default = "1.000000,1.000000,1.000000"
    if not wb:
        return default
    wb = wb.strip()
    if "nan" in wb.lower():
        print(f"Invalid white balance detected: {wb}")
        print(f"Using default: {default}")
        return default
    if not re.match(r"^\d+\.\d+,\d+\.\d+,\d+\.\d+$", wb):
        print(f"Invalid white balance detected: {wb}")
        print(f"Using default: {default}")
        return default
    return wb


def is_windows() -> bool:
    """Check if running on Windows."""
    return platform.system().lower() == "windows"

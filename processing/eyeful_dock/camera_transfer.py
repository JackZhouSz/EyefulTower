# (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

import argparse
import os
import platform
import subprocess
import sys
import time


def check_robot_connectivity(robot_ip):
    """Check if the robot IP is reachable by pinging it."""
    print(f"Checking connectivity to robot at {robot_ip}...")

    # Determine ping command based on OS
    if platform.system().lower() == "windows":
        ping_cmd = ["ping", "-n", "1", robot_ip]
    else:
        ping_cmd = ["ping", "-c", "1", robot_ip]

    try:
        result = subprocess.run(
            ping_cmd,
            capture_output=True,
            text=True,
            timeout=10,  # 10 second timeout
        )

        if result.returncode == 0:
            print(f"Robot at {robot_ip} is reachable")
            return True
        else:
            print(f"Robot at {robot_ip} is not reachable")
            return False

    except subprocess.TimeoutExpired:
        print(f"Connection timeout to robot at {robot_ip}")
        return False
    except Exception as e:
        print(f"Error checking connectivity to {robot_ip}: {e}")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Tool for triggering transfers from the Eyeful Tower V3"
    )

    parser.add_argument(
        "--robot-ip",
        type=str,
        required=True,
        help="IP of the robot.",
    )
    parser.add_argument(
        "--transfer-exe",
        type=str,
        required=True,
        help="Path to the transfer executable.",
    )
    parser.add_argument(
        "--transfer-dataset",
        type=str,
        required=True,
        help="Dataset name. Passing to transfer executable.",
    )
    parser.add_argument(
        "--transfer-num-cameras",
        type=str,
        help="Expected number of cameras. Passing to transfer executable.",
    )
    parser.add_argument(
        "--transfer-retries",
        type=int,
        help="Number of retries before failing the transfer.",
    )

    args = parser.parse_args()
    print("Using arguments:")
    for k, v in vars(args).items():
        print(f"  - {k} = {v}")
    print()

    if "CAPTURE_DIR" not in os.environ:
        print("Set CAPTURE_DIR before running this script. Exiting.")
        sys.exit(1)

    if not check_robot_connectivity(args.robot_ip):
        print("Cannot reach the robot. Exiting.")
        sys.exit(1)

    for i in range(0, args.transfer_retries):
        print(f"Running transfer attempt {i + 1}")

        # Build the command to run
        cmd = [
            args.transfer_exe,
            "-d",
            args.transfer_dataset,
            "-n",
            args.transfer_num_cameras,
            "-t",
            args.transfer_num_cameras,
        ]

        try:
            # Run the transfer executable
            result = subprocess.check_call(
                cmd,
                text=True,
                stdout=sys.stdout,
                stderr=subprocess.STDOUT,
            )

            print(f"Transfer successful on attempt {i + 1}")
            break  # Exit loop on success

        except subprocess.CalledProcessError as e:
            print(f"Transfer failed on attempt {i + 1} with return code {e.returncode}")
            print("STDOUT:", e.stdout)
            print("STDERR:", e.stderr)

            if i == args.transfer_retries - 1:  # Last attempt
                print("All transfer attempts failed!")
                sys.exit(1)
            else:
                print("Retrying...")
                print()
                time.sleep(5)

        except FileNotFoundError:
            print(f"Error: Transfer executable not found at {args.transfer_exe}")
            sys.exit(1)
        except Exception as e:
            print(f"Transfer failed on attempt {i + 1} with return code {e.returncode}")
            print("STDOUT:", e.stdout)
            print("STDERR:", e.stderr)

            if i == args.transfer_retries - 1:  # Last attempt
                print("All transfer attempts failed!")
                sys.exit(1)
            else:
                print("Retrying...")
                print()
                time.sleep(5)

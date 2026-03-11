# Dock Machine Setup

## Network Configuration

You will need to plug the tower into the dock computer, so you should have an additional ethernet port you can use for the EyefulTower network.

| Setting | Value |
| :---- | :---- |
| IP Address | 192.168.1.100 |
| Subnet Mask | 255.255.255.0 |
| Gateway | 192.168.1.1 |

## Installing Scripts and Dependencies

There will be a series of python and shell scripts that will be in the processing directory of this repo. 

The transfer app will need to be built for the system. That can be run using CMake:

```shell
cd camera_driver
mkdir build
cd build
cmake ..
cd ..
cmake --build build --config Release
```

You will also need to get the LibRaw library: [https://www.libraw.org/download](https://www.libraw.org/download)  
You will need the “dcraw\_emu” binary. The version this pipeline has been tested with is 0.22.0.

## Environment Variables

Once pulled you will need to set up some environment variables. If you are on Windows, set these in the User Environment Variables not the system.

| Variable | Description |
| :---- | :---- |
| `CAPTURE_DIR` | Path to where the local versions of the images will be saved during/before transfer. |
| `DATASETS_PATH` | The location of the completed datasets. |
| `DCRAW_EMU_PATH` | The location of the dcraw\_emu.exe |
| `EYEFUL_DOCK_PATH` | Path to the dock repo. |
| `EYEFUL_IP` | Eyeful Tower IP, should be 192.168.1.200. |
| `TRANSFER_EXE` | The full path to the compiled transfer application executable. |
| `HDR_REPO_PATH` | Location of the [hdrmerge.py](http://hdrmerge.py) script.  |

## Conda Environment

The pipeline will start a conda environment, you will need to build it locally with the provided environment file:

```shell
cd processing/hdr-reconstruction
conda env create -f env_hdrmerge.yml
```

Once that environment is setup, you will need to manually install the Metashape library in to the conda environment. The library: [https://www.agisoft.com/downloads/installer/](https://www.agisoft.com/downloads/installer/) 

This has been tested with 2.0.2 to 2.2.2. Prior to 2.1.4 there isn’t COLMAP export support in Metashape, so COLMAP will not be exported during the processing. You will also want to activate your Metashape license.

Once you have the library for your platform, install it:

```shell
conda activate hdrmerge-env
pip install Metashape-2.2.2-cp37.cp38.cp39.cp310.cp311-none-win_amd64.whl # or whatever file for your system
```

Once the Metashape library is installed, you are ready to process the full pipeline\!

## Scripts

```shell
# Running the full pipeline
# This will pull from the robot 
conda activate hdrmerge-env
python pipeline_runner.py dataset_name # dataset name can be whatever, it will create that as a directory

python pipeline_runner.py --delete-capture # this will delete the raw capture after processing to save space

python pipeline_runner.py --delete-capture --skip-transfer # --skip-transfer will skip the transfeer step and go right to reconstruction
```


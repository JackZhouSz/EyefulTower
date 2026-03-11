# Eyeful

A camera control system for the Eyeful Tower platforms.

## Structure

### `app/`

Platform-specific executables:

- `mac/` - macOS applications
- `pi/` - Raspberry Pi applications
- `sd_format/` - SD card formatting utility for cameras
- `transfer/` - File transfer tool for retrieving files from cameras

### `eyeful/`

Core library for camera interaction using Sony SDK. Handles camera control, bracketing, and multi-camera operations.

### `logging/`

Logging framework.

### `third-party/`

External dependencies:

- **cli11** - Command line argument parsing
- **fmt** - Fast, safe text formatting library
- **magic_enum** - Compile-time enum reflection and string conversion

## Setup

### Sony Camera Remote SDK

#### Installation Paths

The Sony SDK can be optained here: <https://support.d-imaging.sony.co.jp/app/sdk/en/index.html>

We are using version 2.00.00

The build system expects Sony SDK files in these default locations:

- **Libraries**: `/usr/local/lib`
- **Headers**: `/usr/local/include`

Alternatively, you can define custom paths using CMake variables:

```bash
cmake -DSONY_CAMERA_SDK_LIB_DIR=/custom/lib/path -DSONY_CAMERA_SDK_INCLUDE_DIR=/custom/include/path
```

#### Required Library Files

Copy the Sony SDK library to the library directory:

- **Linux**: `libCr_Core.so`
- **macOS**: `libCr_Core.dylib`
- **Windows**: `Cr_Core.dll`

#### Runtime Dependencies

When using this library in your application, the following files must be located next to your executable in a `CrAdapter` directory:

**Linux**:

```text
your_executable
CrAdapter/
├── libCr_PTP_IP.so
├── libCr_PTP_USB.so
└── libusb-1.0.so
```

**macOS**:

```text
your_executable
Contents/Frameworks/CrAdapter/
├── libCr_PTP_IP.dylib
├── libCr_PTP_USB.dylib
└── libusb-1.0.dylib
```

**Windows**:

```text
your_executable.exe
Cr_Core.dll
CrAdapter/
├── Cr_PTP_IP.dll
└── Cr_PTP_USB.dll
```

The build system automatically copies these files from `$HOME/CRSDK/CrAdapter` if found.

## Build

### Linux / macOS

Standard CMake build process:

```bash
mkdir build
cd build
cmake ..
make
```

For custom Sony SDK paths:

```bash
cmake -DSONY_CAMERA_SDK_LIB_DIR=/custom/lib/path -DSONY_CAMERA_SDK_INCLUDE_DIR=/custom/include/path ..
make
```

### Windows

Build using CMake:

```powershell
mkdir build
cd build
cmake ..
cmake --build . --config Release
```

#### Windows Linking Notes

- The Sony SDK provides `Cr_Core.lib` as an import library that links to `Cr_Core.dll`
- Ensure `Cr_Core.dll` and the `CrAdapter/` directory are copied to your output directory
- The CMake build will attempt to copy runtime dependencies automatically if `CRSDK` is found in your home directory

## Build Requirements

- CMake
- Sony Camera Remote SDK
- C++17 compatible compiler

## Platform Support

- Linux
- macOS
- Windows

# Commandly

Commandly is a Godot-based control application that provides remote control capabilities for the Eyeful Tower robot.

## Key Features

- **Dual Communication**: Uses ROS# for ROS2 topic communication and SSH.NET for direct PAL system control
- **Joystick Control**: Full gamepad support for robot teleoperation
- **Real-time Monitoring**: Live camera feed, IMU data, robot pose, and system status
- **Mapping & Localization**: Control and monitor SLAM and localization modules
- **Capture System**: Integrated camera capture with configurable settings
- **Status Dashboard**: Visual indicators for robot state, connectivity, and autonomous modes

## Project Layout

### `Scripts`

Core application logic and robot communication scripts.

**Core Management:**

- **`ROSManager.cs`** - Central ROS2 connection manager
- **`PALControl.cs`** - SSH-based PAL system control for managing PAL modules

**ROS2 Subscribers:**

- **`CameraSubscriber.cs`** - Handles camera feed from the robot
- **`RobotStateSubscriber.cs`** - Monitors robot state and status
- **`ImuSubscriber.cs`** - IMU sensor data processing
- **`JoyPrioritySubscriber.cs`** - Joystick priority and control status
- **`LocalCostmapSubscriber.cs`** - Local navigation costmap data
- **`RobotPoseSubscriber.cs`** - Robot position and orientation tracking

**ROS2 Publishers:**

- **`JoystickPublisher.cs`** - Publishes joystick commands to robot control topics

**ROS2 Services:**

- **`CaptureService.cs`** - Camera capture functionality
- **`CaptureTypeService.cs`** - Configurable capture modes and settings
- **`SdFormatterService.cs`** - SD card formatting utilities

### `UI`

User interface components and interaction handlers.

- **`AutonomousIcon.cs` & `AutonomousStatus.cs`** - Autonomous mode status indicators
- **`Camera.cs`** - Camera display and controls
- **`CaptureButton.cs`, `CaptureDropdown.cs`, `CaptureIcon.cs`, `CaptureToggle.cs`** - Capture system UI components
- **`FormatButton.cs`** - SD card formatting interface
- **`Map.cs`** - Map displays the local costmap of the robot
- **`MappingStateButton.cs`** - SLAM/localization mode controls

### `Types`

Custom UI component definitions.

- **`RobotButton.cs`** - Custom button implementation
- **`RobotOptionButton.cs`** - Custom dropdown implementation

### `Images`

Status icons and visual indicators for connection states and robot status.

### `Styles`

UI styling and theme resources for consistent visual appearance.

## Robot Controls

### Controller Button Mapping

| Controller Input | Function |
|------------------|----------|
| **Left Stick** | Robot base movement (forward/backward) |
| **Right Stick** | Robot rotation and turning |
| **Y Button** | Camera capture |
| **Start Button** | Toggle between autonomous and joystick control |
| **Deadman Switch** | Safety enable (must be held for robot movement) |

### Connection Requirements

- Must be connected to the robot's WiFi network

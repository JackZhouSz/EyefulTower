# Eyeful ROS2

This is the primary ROS2 package for the Eyeful Tower. It runs on a PAL TIAGo base and provides the `eyeful_controller` node for camera capture coordination and robot movement.

## Node: `eyeful_controller`

The main node that interfaces with the PAL TIAGo robot base and controls the camera tower. It handles capture routines, robot movement, and state management.

### Published Topics

| Topic | Type | Description |
|-------|------|-------------|
| `/eyeful/capture_state` | `std_msgs/Int8` | Current capture state (0=READY, 1=CAPTURING, 2=FORMATTING, 3=NOT_READY, -1=ERROR) |
| `/eyeful/camera_state` | `std_msgs/Int8` | Current camera connection state |
| `/eyeful/capture_positions` | `eyeful_ros_msgs/CapturePoseList` | List of positions where captures have been taken |
| `/eyeful/pose` | `geometry_msgs/Pose` | Current robot pose in the map frame |

### Subscribed Topics

| Topic | Type | Description |
|-------|------|-------------|
| `joy_priority` | `std_msgs/Bool` | PAL's joystick topic for whether the joystick shuld be listened to |
| `base_imu` | `sensor_msgs/Imu` | IMU data from the robot base |
| `/eyeful/imu_ready` | `std_msgs/Bool` | IMU stability status - capture waits for IMU to settle |

### Services

| Service | Type | Description |
|---------|------|-------------|
| `/eyeful/capture` | `eyeful_ros_msgs/TriggerCapture` | Trigger a capture sequence. Request includes `move_forward` (bool) to optionally drive forward before spinning. |
| `/eyeful/format_cameras` | `std_srvs/Trigger` | Format all camera SD cards. Clears capture position history. |
| `/eyeful/set_capture_type` | `std_srvs/SetBool` | Set capture type: `true` for double exposure, `false` for single |
| `/eyeful/set_shutter` | `eyeful_ros_msgs/SetShutter` | Set shutter speed (e.g., "1/100", "1/250"). Specify `batch_id` for dual-capture mode. |
| `/eyeful/set_iso` | `eyeful_ros_msgs/SetIso` | Set ISO value. Specify `batch_id` for dual-capture mode. |
| `/eyeful/set_drive_mode` | `eyeful_ros_msgs/SetDriveMode` | Set camera drive mode. Specify `batch_id` for dual-capture mode. |
| `/eyeful/send_capture_pose` | `eyeful_ros_msgs/SendCapturePose` | Navigate to a pose and trigger capture automatically |

### Actions

#### Provided Actions

| Action | Type | Description |
|--------|------|-------------|
| `/eyeful/send_capture_pose_action` | `eyeful_ros_msgs/AdvNavPose` | Navigate to a goal pose and capture. Returns `finished` (bool) on completion. |

#### Used Actions (Nav2)

| Action | Type | Description |
|--------|------|-------------|
| `spin` | `nav2_msgs/Spin` | Rotate the robot in place |
| `drive_on_heading` | `nav2_msgs/DriveOnHeading` | Drive forward a set distance |
| `navigate_to_pose` | `nav2_msgs/NavigateToPose` | Navigate to a target pose |

### TF Frames

The node listens to transforms between:
- `map` → `base_footprint` - Used for tracking robot position and recording capture locations

## Custom Messages

### `eyeful_ros_msgs/CapturePoseList`

```
geometry_msgs/Vector3[] capture_poses
```

List of positions where captures have been taken during a session.

### `eyeful_ros_msgs/TriggerCapture`

```
# Request
bool move_forward       # Drive forward before capture sequence
---
# Response
int32 success
string message
```

### `eyeful_ros_msgs/SetShutter`

```
# Request
string shutter          # Shutter speed string (e.g., "1/100")
int32 batch_id          # 0 for first exposure, 1 for second
---
# Response
int32 success
string message
```

### `eyeful_ros_msgs/SetIso`

```
# Request
int32 iso               # ISO value (e.g., 100, 200, 400)
int32 batch_id          # 0 for first exposure, 1 for second
---
# Response
int32 success
string message
```

### `eyeful_ros_msgs/SetDriveMode`

```
# Request
int64 drive_mode        # Camera drive mode
int32 batch_id          # 0 for first exposure, 1 for second
---
# Response
int32 success
string message
```

### `eyeful_ros_msgs/SendCapturePose`

```
# Request
geometry_msgs/Pose pose # Target pose to navigate to
---
# Response
int32 success
string message
```

### `eyeful_ros_msgs/AdvNavPose` (Action)

```
# Goal
geometry_msgs/Pose pose # Target pose to navigate to
---
# Result
bool finished           # Whether capture completed successfully
---
# Feedback
uint16 step             # Current step in the capture sequence
```

## Capture Sequence

A typical capture sequence performs the following:

1. **Setup** - Configure cameras for batch capture
2. **Drive Forward** - Optionally move forward ~1.25 feet
3. **Wait for IMU** - Ensure robot is stable before capturing
4. **Capture First Exposure** - Trigger cameras with first settings
5. **Capture Second Exposure** - Apply second settings and capture again
6. **Spin** - Rotate 120° (configurable via `numSpinStops`)
7. **Repeat** - Steps 3-6 are repeated for each spin stop (default: 3 positions)
8. **Record Position** - Store the capture location for visualization

## Camera Configuration

The node connects to 14 Sony cameras via IP:
- IP range: `192.168.1.40` - `192.168.1.53`
- Default first shutter: `1/100`
- Default second shutter: `1/250`
- Default ISO: 500 (first), 100 (second)

## Dependencies

- ROS2 (tested on Humble)
- nav2_msgs
- tf2_ros
- Sony Camera Remote SDK (via `camera_driver`)

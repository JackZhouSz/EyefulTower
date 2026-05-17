// Copyright (c) Meta Platforms, Inc. and affiliates.

#include <atomic>
#include <chrono>
#include <condition_variable>
#include <fstream>
#include <functional>
#include <future>
#include <memory>
#include <mutex>
#include <string>
#include <thread>

#include "eyeful/EyefulTower.h"
#include "eyeful_ros_msgs/action/adv_nav_pose.hpp"
#include "eyeful_ros_msgs/msg/capture_pose_list.hpp"
#include "eyeful_ros_msgs/srv/send_capture_pose.hpp"
#include "eyeful_ros_msgs/srv/set_drive_mode.hpp"
#include "eyeful_ros_msgs/srv/set_iso.hpp"
#include "eyeful_ros_msgs/srv/set_shutter.hpp"
#include "eyeful_ros_msgs/srv/trigger_capture.hpp"
#include "geometry_msgs/msg/pose.hpp"
#include "geometry_msgs/msg/pose_with_covariance_stamped.hpp"
#include "geometry_msgs/msg/transform_stamped.hpp"
#include "geometry_msgs/msg/twist.hpp"
#include "geometry_msgs/msg/vector3.hpp"
#include "nav2_msgs/action/drive_on_heading.hpp"
#include "nav2_msgs/action/navigate_to_pose.hpp"
#include "nav2_msgs/action/spin.hpp"
#include "rclcpp/qos.hpp"
#include "rclcpp/rclcpp.hpp"
#include "rclcpp_action/rclcpp_action.hpp"
#include "sensor_msgs/msg/imu.hpp"
#include "std_msgs/msg/bool.hpp"
#include "std_msgs/msg/int8.hpp"
#include "std_srvs/srv/set_bool.hpp"
#include "std_srvs/srv/trigger.hpp"
#include "tf2/LinearMath/Matrix3x3.hpp"
#include "tf2/LinearMath/Quaternion.h"
#include "tf2_ros/buffer.h"
#include "tf2_ros/transform_listener.h"

using namespace std::chrono_literals;
using std::placeholders::_1;
using std::placeholders::_2;

/**
 * EyefulController
 *
 * This node interfaces with the PAL Tiago robot base.
 *
 * Primarily, it will handle the routines for moving the robot, and managing any state.
 *
 *
 * I am going to start with fully copying the control code from the ROS1 python version.
 * After that works, I will then iterate on it.
 *
 *
 */

class EyefulController : public rclcpp::Node {
  enum CaptureState { NOT_READY = 3, FORMATTING = 2, CAPTURING = 1, READY = 0, ERROR = -1 };

  enum CaptureType {
    DOUBLE = 1,
    SINGLE = 0,
  };

  enum AppButtons {
    CAPTURE = 3, // Y
    QUIT = 2,
  };

  struct ActionState {
    rclcpp_action::ResultCode result;
    bool started;
  };

 public:
  EyefulController() : Node("eyeful_controller") {
    capture_type = CaptureType::SINGLE;

    joy_priority_sub = this->create_subscription<std_msgs::msg::Bool>(
        "joy_priority", 10, std::bind(&EyefulController::joyPriorityCallback, this, _1));
    imu_sub = this->create_subscription<sensor_msgs::msg::Imu>(
        "base_imu", 10, std::bind(&EyefulController::imuCallback, this, _1));
    imu_ready_sub = this->create_subscription<std_msgs::msg::Bool>(
        "/eyeful/imu_ready", 10, std::bind(&EyefulController::imuReadyCallback, this, _1));
    // auto_capture_pose_sub = this->create_subscription<geometry_msgs::msg::Pose>(
    //                     "joy_priority", 10, std::bind(&EyefulController::joyPriorityCallback,
    //                     this, _1));

    // Setting up latching
    rclcpp::QoS qos_profile(10);
    qos_profile.reliable();
    qos_profile.transient_local();

    capture_state_pub =
        this->create_publisher<std_msgs::msg::Int8>("/eyeful/capture_state", qos_profile);
    camera_state_pub =
        this->create_publisher<std_msgs::msg::Int8>("/eyeful/camera_state", qos_profile);
    capture_pos_pub = this->create_publisher<eyeful_ros_msgs::msg::CapturePoseList>(
        "/eyeful/capture_positions", qos_profile);
    pose_pub = this->create_publisher<geometry_msgs::msg::Pose>("/eyeful/pose", qos_profile);
    state_timer = create_wall_timer(250ms, std::bind(&EyefulController::sendState, this));
    pose_timer = create_wall_timer(50ms, std::bind(&EyefulController::sendPose, this));

    // Action for spinning in place
    spin_action_client = rclcpp_action::create_client<nav2_msgs::action::Spin>(this, "spin");
    drive_action_client =
        rclcpp_action::create_client<nav2_msgs::action::DriveOnHeading>(this, "drive_on_heading");
    nav_pose_client =
        rclcpp_action::create_client<nav2_msgs::action::NavigateToPose>(this, "navigate_to_pose");

    format_service = this->create_service<std_srvs::srv::Trigger>(
        "/eyeful/format_cameras", std::bind(&EyefulController::formatCameras, this, _1, _2));
    capture_service = this->create_service<eyeful_ros_msgs::srv::TriggerCapture>(
        "/eyeful/capture", std::bind(&EyefulController::capture, this, _1, _2));
    capture_type_service = this->create_service<std_srvs::srv::SetBool>(
        "/eyeful/set_capture_type", std::bind(&EyefulController::setCaptureType, this, _1, _2));
    shutter_service = this->create_service<eyeful_ros_msgs::srv::SetShutter>(
        "/eyeful/set_shutter", std::bind(&EyefulController::setShutter, this, _1, _2));
    iso_service = this->create_service<eyeful_ros_msgs::srv::SetIso>(
        "/eyeful/set_iso", std::bind(&EyefulController::setIso, this, _1, _2));
    drive_mode_service = this->create_service<eyeful_ros_msgs::srv::SetDriveMode>(
        "/eyeful/set_drive_mode", std::bind(&EyefulController::setDriveMode, this, _1, _2));
    send_capture_pose_service = this->create_service<eyeful_ros_msgs::srv::SendCapturePose>(
        "/eyeful/send_capture_pose", std::bind(&EyefulController::sendCapturePose, this, _1, _2));

    capture_srv_client =
        this->create_client<eyeful_ros_msgs::srv::TriggerCapture>("/eyeful/capture");

    send_capture_pose_action = rclcpp_action::create_server<eyeful_ros_msgs::action::AdvNavPose>(
        this,
        "/eyeful/send_capture_pose_action",
        std::bind(&EyefulController::handleCaptureActionGoal, this, _1, _2),
        std::bind(&EyefulController::handleCaptureActionCancel, this, _1),
        std::bind(&EyefulController::handleCaptureActionAccepted, this, _1));

    lastImuNotReady = 0;

    tf_buffer = std::make_unique<tf2_ros::Buffer>(this->get_clock());
    tf_listener = std::make_shared<tf2_ros::TransformListener>(*tf_buffer);

    std::thread cameraInitThread(std::bind(&EyefulController::initEyefulTower, this));
    cameraInitThread.detach();

    setCameraState(eyeful_tower::CameraReady::WAITING);
  }

 private:
  // It is a list of chars because of the way that sony handels the IPs.
  std::vector<std::array<unsigned char, 4>> ips = {
      {192, 168, 1, 40},
      {192, 168, 1, 41},
      {192, 168, 1, 42},
      {192, 168, 1, 43},
      {192, 168, 1, 44},
      {192, 168, 1, 45},
      {192, 168, 1, 46},
      {192, 168, 1, 47},
      {192, 168, 1, 48},
      {192, 168, 1, 49},
      {192, 168, 1, 50},
      {192, 168, 1, 51},
      {192, 168, 1, 52},
      {192, 168, 1, 53},
  };

  std::mutex robot_mutex;
  std::shared_ptr<EyefulTower> eyeful_tower;
  std::atomic_bool robotReady = false;
  std::atomic_bool driveForward = true;

  rclcpp::Service<std_srvs::srv::Trigger>::SharedPtr format_service;
  rclcpp::Service<eyeful_ros_msgs::srv::TriggerCapture>::SharedPtr capture_service;
  rclcpp::Client<eyeful_ros_msgs::srv::TriggerCapture>::SharedPtr capture_srv_client;

  rclcpp::Service<std_srvs::srv::SetBool>::SharedPtr capture_type_service;
  rclcpp::Service<eyeful_ros_msgs::srv::SetShutter>::SharedPtr shutter_service;
  rclcpp::Service<eyeful_ros_msgs::srv::SetIso>::SharedPtr iso_service;
  rclcpp::Service<eyeful_ros_msgs::srv::SetDriveMode>::SharedPtr drive_mode_service;
  rclcpp::Service<eyeful_ros_msgs::srv::SendCapturePose>::SharedPtr send_capture_pose_service;

  rclcpp::Subscription<std_msgs::msg::Bool>::SharedPtr joy_priority_sub;
  rclcpp::Subscription<sensor_msgs::msg::Imu>::SharedPtr imu_sub;
  rclcpp::Subscription<std_msgs::msg::Bool>::SharedPtr imu_ready_sub;
  rclcpp::Subscription<geometry_msgs::msg::Pose>::SharedPtr auto_capture_pose_sub;

  rclcpp_action::Client<nav2_msgs::action::Spin>::SharedPtr spin_action_client;
  rclcpp_action::Client<nav2_msgs::action::DriveOnHeading>::SharedPtr drive_action_client;
  rclcpp_action::Client<nav2_msgs::action::NavigateToPose>::SharedPtr nav_pose_client;

  rclcpp_action::Server<eyeful_ros_msgs::action::AdvNavPose>::SharedPtr send_capture_pose_action;

  std::shared_ptr<tf2_ros::TransformListener> tf_listener;
  std::unique_ptr<tf2_ros::Buffer> tf_buffer;
  std::vector<geometry_msgs::msg::TransformStamped> capture_transforms;

  std::atomic<CaptureState> capture_state;
  rclcpp::Publisher<std_msgs::msg::Int8>::SharedPtr capture_state_pub;
  std::atomic<eyeful_tower::CameraReady> camera_state;
  rclcpp::Publisher<std_msgs::msg::Int8>::SharedPtr camera_state_pub;
  rclcpp::Publisher<eyeful_ros_msgs::msg::CapturePoseList>::SharedPtr capture_pos_pub;
  rclcpp::Publisher<geometry_msgs::msg::Pose>::SharedPtr pose_pub;

  std::mutex poseLock;
  geometry_msgs::msg::Pose curr_pose;

  rclcpp::TimerBase::SharedPtr state_timer;
  rclcpp::TimerBase::SharedPtr pose_timer;

  std::mutex imuLock;
  ActionState spin_state;
  ActionState drive_state;
  CaptureType capture_type;

  std::atomic_bool imuReady = false;
  double lastImuNotReady;

  const int numSpinStops = 3;
  std::atomic_bool canCapture = true;
  sensor_msgs::msg::Imu::SharedPtr currImu;
  std::vector<sensor_msgs::msg::Imu::SharedPtr> imuCaptureValues;
  std::condition_variable_any imuCond;
  std::mutex imuCond_m;

  /// CAPTURE ACTION STUFF

  rclcpp_action::GoalResponse handleCaptureActionGoal(
      const rclcpp_action::GoalUUID& uuid,
      const std::shared_ptr<const eyeful_ros_msgs::action::AdvNavPose::Goal> goal) {
    return rclcpp_action::GoalResponse::ACCEPT_AND_EXECUTE;
  }

  rclcpp_action::CancelResponse handleCaptureActionCancel(
      const std::shared_ptr<rclcpp_action::ServerGoalHandle<eyeful_ros_msgs::action::AdvNavPose>>
          goalHandle) {
    return rclcpp_action::CancelResponse::ACCEPT;
  }

  void handleCaptureActionAccepted(
      const std::shared_ptr<rclcpp_action::ServerGoalHandle<eyeful_ros_msgs::action::AdvNavPose>>
          goalHandle) {
    if (robotReady) {
      std::thread capture_thread(
          std::bind(&EyefulController::autoCaptureActionThread, this, _1), goalHandle);
      capture_thread.detach();
    }
  }

  /// CAPTURE ACTION STUFF

  void initEyefulTower() {
    setCaptureState(CaptureState::NOT_READY);
    robotReady = false;
    RCLCPP_INFO(this->get_logger(), "ROS Initializing Cameras");
    // We are letting the PAL network and cameras initialize.
    // The Sony SDK can be very picky about the network, waiting seems to be their suggest way of
    // settling it.
    std::this_thread::sleep_for(90000ms);
    eyeful_tower = std::make_shared<EyefulTower>(ips, "1/100", "1/250", 500, 100);
    setCaptureState(CaptureState::READY);
    setCameraState(eyeful_tower->GetReadyState());
    robotReady = true;
    RCLCPP_INFO(this->get_logger(), "ROS Cameras Ready");
  }

  // I need to keep track of the IMU so that when I capture, I can get the state at that point.
  void imuCallback(const sensor_msgs::msg::Imu::SharedPtr imu) {
    imuLock.lock();
    currImu = imu;
    imuLock.unlock();
  }

  void imuReadyCallback(const std_msgs::msg::Bool::SharedPtr msg) {
    auto now = this->get_clock()->now().seconds();

    if (msg->data) {
      double timeSinceLastFalse = now - lastImuNotReady;
      if (timeSinceLastFalse >= 1.0) {
        imuReady = true;
        imuCond.notify_all();
      }
    } else {
      lastImuNotReady = now;
      imuReady = false;
    }
  }

  void joyPriorityCallback(const std_msgs::msg::Bool::SharedPtr msg) {
    // If joystick priority is true, that means the joystick is on, and we can't capture
    if (robotReady) {
      if (msg->data) {
        setCaptureState(CaptureState::NOT_READY);
      } else {
        setCaptureState(CaptureState::READY);
      }
    }
  }

  void capture(
      const std::shared_ptr<eyeful_ros_msgs::srv::TriggerCapture::Request> request,
      std::shared_ptr<eyeful_ros_msgs::srv::TriggerCapture::Response> response) {
    if (robotReady) {
      driveForward = request->move_forward;
      std::thread capture_thread(
          std::bind(&EyefulController::doBatchCaptureServiceAsync, this, _1), response);
      capture_thread.detach();
    }
  }

  void pubPositions() {
    geometry_msgs::msg::TransformStamped map_base;
    try {
      map_base = tf_buffer->lookupTransform("map", "base_footprint", tf2::TimePointZero);
    } catch (const tf2::TransformException& ex) {
      RCLCPP_INFO(this->get_logger(), "No transforms.");
      return;
    }

    capture_transforms.push_back(map_base);
    RCLCPP_INFO(this->get_logger(), "Publishing captures: %zu", capture_transforms.size());

    eyeful_ros_msgs::msg::CapturePoseList msg;

    for (size_t i = 0; i < capture_transforms.size(); i++) {
      geometry_msgs::msg::Vector3 pos;
      pos.x = capture_transforms[i].transform.translation.x;
      pos.y = capture_transforms[i].transform.translation.y;
      pos.z = capture_transforms[i].transform.translation.z;
      msg.capture_poses.push_back(pos);
    }

    capture_pos_pub->publish(msg);
  }

  bool doBatchCapture() {
    robot_mutex.lock();
    canCapture = false;
    setCaptureState(CaptureState::CAPTURING);
    // bool successfulCapture = SetCapture();
    RCLCPP_INFO(this->get_logger(), "Setting capture");
    std::future<bool> _successfulCapture = std::async(
        std::launch::async, std::bind(&EyefulController::setCaptureAndFirstSettings, this));
    if (driveForward) {
      RCLCPP_INFO(this->get_logger(), "Sending drive forward");
      sendDriveBlocking();
    } else {
      RCLCPP_INFO(this->get_logger(), "Not driving forward");
    }
    bool successfulCapture = _successfulCapture.get();

    if (successfulCapture) {
      for (int i = 0; i < numSpinStops; i++) {
        // Settings for first capture are set before the loop
        successfulCapture = waitAndCaptureRaw();
        if (!successfulCapture) {
          break;
        }

        // Doing second capture
        successfulCapture = eyeful_tower->ApplySettingsSecond();
        if (!successfulCapture) {
          break;
        }
        successfulCapture = waitAndCaptureRaw();

        // Setting first capture settings async, and starting spin
        _successfulCapture = std::async(
            std::launch::async, std::bind(&EyefulTower::ApplySettingsFirst, eyeful_tower));
        RCLCPP_INFO(this->get_logger(), "Sending spin");
        sendSpinBlocking();
        RCLCPP_INFO(this->get_logger(), "Done with spin");
        successfulCapture = _successfulCapture.get();
        if (!successfulCapture) {
          break;
        }

        // Check the state. We may want to not keep a capture if a spin was aborted/cancelled?
        if (!spin_state.started) {
          RCLCPP_INFO(this->get_logger(), "NEVER STARTED");
        } else {
          if (spin_state.result == rclcpp_action::ResultCode::ABORTED ||
              spin_state.result == rclcpp_action::ResultCode::CANCELED) {
            RCLCPP_INFO(this->get_logger(), "Didn't finish. Invalidate capture?");
          }
        }

        // If we want to get more granular with checks, it could be worth validating that we hit the
        // right angles. Like if it is aborted, we try to make the difference up one more time
        // before reporting and error and quitting.
      }
    }

    // Get transform, and save it to keep the position
    pubPositions();

    RCLCPP_INFO(this->get_logger(), "Capture Ended");
    canCapture = true;
    setCaptureState(CaptureState::READY);
    robot_mutex.unlock();

    return successfulCapture;
  }

  void doBatchCaptureServiceAsync(
      std::shared_ptr<eyeful_ros_msgs::srv::TriggerCapture::Response> response) {
    bool successfulCapture = doBatchCapture();

    if (successfulCapture) {
      response->message = "Success";
    } else {
      response->message = "Error";
      setCameraState(eyeful_tower::CameraReady::ERROR);
    }
    response->success = successfulCapture;
  }

  void doCapture(std::shared_ptr<std_srvs::srv::Trigger::Response> response) {
    robot_mutex.lock();
    canCapture = false;
    setCaptureState(CaptureState::CAPTURING);
    bool successfulCapture = SetCapture();

    if (successfulCapture) {
      RCLCPP_INFO(this->get_logger(), "Sending drive");
      sendDriveBlocking();
      for (int i = 0; i < numSpinStops; i++) {
        successfulCapture = waitAndCapture();

        if (!successfulCapture) {
          break;
        }
        RCLCPP_INFO(this->get_logger(), "Sending spin");
        sendSpinBlocking();
        RCLCPP_INFO(this->get_logger(), "Done with spin");

        // Check the state. We may want to not keep a capture if a spin was aborted/cancelled?
        if (!spin_state.started) {
          RCLCPP_INFO(this->get_logger(), "NEVER STARTED");
        } else {
          if (spin_state.result == rclcpp_action::ResultCode::ABORTED ||
              spin_state.result == rclcpp_action::ResultCode::CANCELED) {
            RCLCPP_INFO(this->get_logger(), "Didn't finish. Invalidate capture?");
          }
        }

        // If we want to get more granular with checks, it could be worth validating that we hit the
        // right angles. Like if it is aborted, we try to make the difference up one more time
        // before reporting and error and quitting.
      }
    }

    // Get transform, and save it to keep the position
    pubPositions();

    RCLCPP_INFO(this->get_logger(), "Capture Ended");
    canCapture = true;

    if (successfulCapture) {
      response->message = "Success";
    } else {
      response->message = "Error";
      setCameraState(eyeful_tower::CameraReady::ERROR);
    }
    response->success = successfulCapture;
    setCaptureState(CaptureState::READY);
    robot_mutex.unlock();
  }

  // Writing the IMU rotation data to CSV.
  // Each line will be the RPY of the robot at the time a capture was taken
  // If we need it per camera, we will need to do some transforms on top to go
  // to each camera.
  void imuToCSV() {
    std::stringstream csvStream;
    csvStream << "Roll,Pitch,Yaw" << std::endl;
    RCLCPP_INFO(this->get_logger(), "Generating IMU CSV");

    // Go through imu record list
    for (const sensor_msgs::msg::Imu::SharedPtr& imu : imuCaptureValues) {
      // Get orientation data
      tf2::Quaternion quat(
          imu->orientation.x, imu->orientation.y, imu->orientation.z, imu->orientation.w);
      tf2::Matrix3x3 mat(quat);

      // Convert to RPY
      double r, p, y;
      mat.getRPY(r, p, y);

      // Add to CSV data
      csvStream << r << "," << p << "," << y << std::endl;
    }

    std::fstream file;
    file.open("/home/pal/capture.csv", std::ios::out | std::ios::app);
    file << csvStream.str() << std::endl;
    file.close();
    RCLCPP_INFO(this->get_logger(), "IMU CSV Saved");
  }

  // Wait for IMU data to settle
  bool waitAndCapture() {
    std::unique_lock<std::mutex> lk(imuCond_m);
    if (imuCond.wait_for(lk, 2500ms, [this] { return this->imuReady.load(); })) {
      return eyeful_tower->Capture();
    } else {
      RCLCPP_ERROR(this->get_logger(), "TIME OUT WAITING FOR IMU.");
      return false;
    }
  }

  // Wait for IMU data to settle
  bool waitAndCaptureRaw() {
    std::unique_lock<std::mutex> lk(imuCond_m);
    if (imuCond.wait_for(lk, 10000ms, [this] { return this->imuReady.load(); })) {
      eyeful_tower->TriggerRawCapture();
      return true;
    } else {
      RCLCPP_ERROR(this->get_logger(), "TIME OUT WAITING FOR IMU.");
      return false;
    }
  }

  // This will be in a thread for the batch captures so it can both happen while moving.
  bool setCaptureAndFirstSettings() {
    bool success = SetCapture();
    if (success) {
      success &= eyeful_tower->ApplySettingsFirst();
    }

    return success;
  }

  bool SetCapture() {
    switch (capture_type) {
      case CaptureType::DOUBLE:
        return eyeful_tower->SetupBatchCapture();
        break;

      case CaptureType::SINGLE:
        return eyeful_tower->SetupBuiltInCapture();
        break;

      default:
        return eyeful_tower->SetupBatchCapture();
        break;
    }
  }

  void sendState() {
    std_msgs::msg::Int8 captureStateMsg;
    std_msgs::msg::Int8 cameraStateMsg;

    captureStateMsg.data = (int8_t)capture_state.load();

    if (eyeful_tower != NULL) {
      cameraStateMsg.data = (int8_t)eyeful_tower->GetReadyState();
    } else {
      cameraStateMsg.data = (int8_t)eyeful_tower::CameraReady::WAITING;
    }

    capture_state_pub->publish(captureStateMsg);
    camera_state_pub->publish(cameraStateMsg);
  }

  void sendPose() {
    geometry_msgs::msg::TransformStamped map_base;
    try {
      map_base = tf_buffer->lookupTransform("map", "base_footprint", tf2::TimePointZero);
    } catch (const tf2::TransformException& ex) {
      RCLCPP_INFO(this->get_logger(), "No transforms.");
      return;
    }

    geometry_msgs::msg::Pose pose;
    pose.position.x = map_base.transform.translation.x;
    pose.position.y = map_base.transform.translation.y;
    pose.position.z = map_base.transform.translation.z;
    pose.orientation = map_base.transform.rotation;

    poseLock.lock();
    curr_pose = pose;
    poseLock.unlock();
    pose_pub->publish(pose);
  }

  void setCaptureState(CaptureState newState) {
    capture_state.store(newState);
  }

  void setCameraState(eyeful_tower::CameraReady newState) {
    camera_state.store(newState);
  }

  void sendSpinBlocking() {
    auto yaw = (2 * M_PI) / numSpinStops;
    auto goal = nav2_msgs::action::Spin::Goal();
    auto nav_goal = nav2_msgs::action::NavigateToPose::Goal();
    poseLock.lock();
    auto _curr_pose = curr_pose;
    poseLock.unlock();

    tf2::Quaternion goal_rot_quat;
    goal_rot_quat.setRPY(0, 0, yaw);

    tf2::Quaternion curr_rot_quat(
        _curr_pose.orientation.x,
        _curr_pose.orientation.y,
        _curr_pose.orientation.z,
        _curr_pose.orientation.w);

    auto goal_quat = goal_rot_quat * curr_rot_quat;

    nav_goal.pose.header.frame_id = "map";
    nav_goal.pose.header.stamp = this->get_clock()->now();
    nav_goal.pose.pose.position = _curr_pose.position;
    nav_goal.pose.pose.orientation.x = goal_quat.x();
    nav_goal.pose.pose.orientation.y = goal_quat.y();
    nav_goal.pose.pose.orientation.z = goal_quat.z();
    nav_goal.pose.pose.orientation.w = goal_quat.w();

    auto nav_goal_options =
        rclcpp_action::Client<nav2_msgs::action::NavigateToPose>::SendGoalOptions();

    nav_goal_options.result_callback =
        std::bind(&EyefulController::navigateToPoseResultCallback, this, _1);

    nav_pose_client->wait_for_action_server();
    auto handle = nav_pose_client->async_send_goal(nav_goal, nav_goal_options);

    // This is a complicated way of waiting for the action to finish, not just the goal being
    // accepted
    RCLCPP_INFO(this->get_logger(), "Returning pose action");
    nav_pose_client->async_get_result(handle.get()).get();
  }

  void spinGoalCallback(
      const rclcpp_action::ClientGoalHandle<nav2_msgs::action::Spin>::SharedPtr& goal) {
    if (!goal) {
      RCLCPP_INFO(this->get_logger(), "Spin goal refused");
      spin_state.started = false;
    } else {
      RCLCPP_INFO(this->get_logger(), "Spin goal accepted");
      spin_state.started = true;
    }
  }

  void spinFeedbackCallback(
      rclcpp_action::ClientGoalHandle<nav2_msgs::action::Spin>::SharedPtr,
      const std::shared_ptr<const nav2_msgs::action::Spin::Feedback> feedback) {
    RCLCPP_INFO(this->get_logger(), "Spun: %f", feedback->angular_distance_traveled);
  }

  void spinResultCallback(
      const rclcpp_action::ClientGoalHandle<nav2_msgs::action::Spin>::WrappedResult& result) {
    switch (result.code) {
      case rclcpp_action::ResultCode::SUCCEEDED:
        RCLCPP_INFO(this->get_logger(), "Done");
        break;
      case rclcpp_action::ResultCode::CANCELED:
        RCLCPP_INFO(this->get_logger(), "Cancelled");
        break;
      case rclcpp_action::ResultCode::ABORTED:
        RCLCPP_INFO(this->get_logger(), "Spin Aborted");
        break;
      default:
        break;
    }

    spin_state.result = result.code;
  }

  // TODO: maybe make these actions another node
  // This will automatically stop if an object is detected infront of it.
  // When we do the action implementation, we should notify that the robot stopped short.
  // We can just continue a capture or ask if we want to skip capture?
  // With fully autonomous, how do we do this without a front facing sensor?
  void sendDriveBlocking() {
    auto goal = nav2_msgs::action::DriveOnHeading::Goal();
    goal.target.x = 0.3048 * 1.25; // 0.3048m = 1ft
    goal.speed = 0.25;
    goal.time_allowance.sec = 15;

    // TODO: Monitor feedback, and have a ready for when the goal was reached or failed.
    auto drive_goal_options =
        rclcpp_action::Client<nav2_msgs::action::DriveOnHeading>::SendGoalOptions();

    drive_goal_options.goal_response_callback =
        std::bind(&EyefulController::driveGoalCallback, this, _1);
    drive_goal_options.feedback_callback =
        std::bind(&EyefulController::driveFeedbackCallback, this, _1, _2);
    drive_goal_options.result_callback =
        std::bind(&EyefulController::driveResultCallback, this, _1);

    drive_action_client->wait_for_action_server();
    auto handle = drive_action_client->async_send_goal(goal, drive_goal_options);

    // This is a complicated way of waiting for the drive to finish, not just the goal being
    // accepted
    drive_action_client->async_get_result(handle.get()).get();
  }

  void driveGoalCallback(
      const rclcpp_action::ClientGoalHandle<nav2_msgs::action::DriveOnHeading>::SharedPtr& goal) {
    if (!goal) {
      RCLCPP_INFO(this->get_logger(), "Drive goal refused");
      drive_state.started = false;
    } else {
      RCLCPP_INFO(this->get_logger(), "Drive goal accepted");
      drive_state.started = true;
    }
  }

  void driveFeedbackCallback(
      rclcpp_action::ClientGoalHandle<nav2_msgs::action::DriveOnHeading>::SharedPtr,
      const std::shared_ptr<const nav2_msgs::action::DriveOnHeading::Feedback> feedback) {
    RCLCPP_INFO(this->get_logger(), "Travelled: %f", feedback->distance_traveled);
  }

  void driveResultCallback(
      const rclcpp_action::ClientGoalHandle<nav2_msgs::action::DriveOnHeading>::WrappedResult&
          result) {
    switch (result.code) {
      case rclcpp_action::ResultCode::SUCCEEDED:
        RCLCPP_INFO(this->get_logger(), "Done");
        break;
      case rclcpp_action::ResultCode::CANCELED:
        RCLCPP_INFO(this->get_logger(), "Cancelled");
        break;
      case rclcpp_action::ResultCode::ABORTED:
        RCLCPP_INFO(this->get_logger(), "Aborted");
        break;
      default:
        break;
    }

    drive_state.result = result.code;
  }

  void formatCameras(
      const std::shared_ptr<std_srvs::srv::Trigger::Request>,
      std::shared_ptr<std_srvs::srv::Trigger::Response> response) {
    if (robotReady) {
      std::thread format_thread(std::bind(&EyefulController::doFormat, this, _1), response);
      format_thread.detach();
      // If you clear the cameras, that means no positions were captured.
      capture_transforms = std::vector<geometry_msgs::msg::TransformStamped>();
      eyeful_ros_msgs::msg::CapturePoseList msg;
      capture_pos_pub->publish(msg);
      RCLCPP_INFO(this->get_logger(), "Cleared captures.");
    }
  }

  void doFormat(std::shared_ptr<std_srvs::srv::Trigger::Response> response) {
    robot_mutex.lock();
    canCapture = false;
    setCaptureState(CaptureState::FORMATTING);

    bool formatted = eyeful_tower->FormatCameras();

    RCLCPP_INFO(this->get_logger(), "Sending ready back after format.");

    if (formatted) {
      setCaptureState(CaptureState::READY);
      canCapture = true;
      response->message = "Successfully formatted cameras.";
    } else {
      setCaptureState(CaptureState::ERROR);
      canCapture = false;
      response->message = "ERROR FORMATTING";
    }

    response->success = formatted;
    robot_mutex.unlock();
  }

  // TODO: if we add more options, we will need a custom message.
  void setCaptureType(
      const std::shared_ptr<std_srvs::srv::SetBool::Request> request,
      std::shared_ptr<std_srvs::srv::SetBool::Response> response) {
    if (request->data) {
      response->message = "Using double captures.";
      capture_type = CaptureType::DOUBLE;
    } else {
      response->message = "Using single capture.";
      capture_type = CaptureType::SINGLE;
    }
    response->success = true;
  }

  void setShutter(
      const std::shared_ptr<eyeful_ros_msgs::srv::SetShutter::Request> request,
      std::shared_ptr<eyeful_ros_msgs::srv::SetShutter::Response> response) {
    // TODO: Need to thread so I can wait for the mutex and not hold up the callback
    std::string shutterStr = request->shutter;
    std::string message = "";
    CrInt64u result = 0;

    if (request->batch_id == eyeful_tower::BatchId::FIRST) {
      result = eyeful_tower->SetShutter(shutterStr);
    } else if (request->batch_id == eyeful_tower::BatchId::SECOND) {
      result = eyeful_tower->SetShutter2(shutterStr);
    }

    // If result is valid
    if (result != 0) {
      message = "Shutter set.";
    } else {
      message = "Error setting shutter.";
    }

    response->message = message;
    response->success = result != 0;
    RCLCPP_INFO(this->get_logger(), "%s", message.c_str());
  }

  void setIso(
      const std::shared_ptr<eyeful_ros_msgs::srv::SetIso::Request> request,
      std::shared_ptr<eyeful_ros_msgs::srv::SetIso::Response> response) {
    // TODO: Need to thread so I can wait for the mutex and not hold up the callback
    if (request->batch_id == eyeful_tower::BatchId::FIRST) {
      eyeful_tower->SetIso(request->iso);
      response->message = "ISO Set";
      response->success = true;
    } else if (request->batch_id == eyeful_tower::BatchId::SECOND) {
      eyeful_tower->SetIso2(request->iso);
      response->message = "ISO Set";
      response->success = true;
    } else {
      response->message = "ISO not set. Invalid ID.";
      response->success = false;
    }
    RCLCPP_INFO(this->get_logger(), "%s", response->message.c_str());
  }

  void sendCapturePose(
      const std::shared_ptr<eyeful_ros_msgs::srv::SendCapturePose::Request> request,
      std::shared_ptr<eyeful_ros_msgs::srv::SendCapturePose::Response> response) {
    if (robotReady) {
      std::thread capture_thread(
          std::bind(&EyefulController::autoCaptureThread, this, _1, _2), response, request->pose);
      capture_thread.detach();
    }
  }

  void autoCaptureThread(
      std::shared_ptr<eyeful_ros_msgs::srv::SendCapturePose::Response> response,
      const geometry_msgs::msg::Pose pose) {
    setCaptureState(CaptureState::CAPTURING);
    RCLCPP_INFO(this->get_logger(), "Started auto capture");
    // Send the action to navigate
    auto result = sendNavGoalCapture(pose);
    // Wait for the action to navigate
    // After action is done, call internal service here to trigger capture
    if (result.code == rclcpp_action::ResultCode::SUCCEEDED) {
      RCLCPP_INFO(this->get_logger(), "Movement done");
      driveForward = false;
      auto request = std::make_shared<eyeful_ros_msgs::srv::TriggerCapture::Request>();
      request->move_forward = false;
      auto result_future = capture_srv_client->async_send_request(request);
      auto result = result_future.wait_for(std::chrono::seconds(120));
      if (result != std::future_status::ready) {
        RCLCPP_INFO(this->get_logger(), "Capture failed.");
        capture_srv_client->remove_pending_request(result_future);
      } else {
        auto srv_result = result_future.get();
        response->success = srv_result->success;
        response->message = srv_result->message;
      }

    } else {
      response->success = false;
      response->message = "Failed to navigate to position";
    }

    setCaptureState(CaptureState::READY);
  }

  void autoCaptureActionThread(
      const std::shared_ptr<rclcpp_action::ServerGoalHandle<eyeful_ros_msgs::action::AdvNavPose>>
          goalHandle) {
    setCaptureState(CaptureState::CAPTURING);
    RCLCPP_INFO(this->get_logger(), "Started auto capture");
    auto goal = goalHandle->get_goal();
    auto capture_result = std::make_shared<eyeful_ros_msgs::action::AdvNavPose::Result>();
    auto capture_feedback = std::make_shared<eyeful_ros_msgs::action::AdvNavPose::Feedback>();

    // Send the action to navigate
    auto result = sendNavGoalCapture(goal->pose);
    RCLCPP_INFO(this->get_logger(), "Got nav goal");
    // Wait for the action to navigate
    // After action is done, call internal service here to trigger capture
    if (result.code == rclcpp_action::ResultCode::SUCCEEDED) {
      RCLCPP_INFO(this->get_logger(), "Movement done");
      driveForward = false;
      auto request = std::make_shared<eyeful_ros_msgs::srv::TriggerCapture::Request>();
      request->move_forward = false;
      auto success = doBatchCapture();
      if (!success) {
        RCLCPP_INFO(this->get_logger(), "Capture failed.");
        // capture_srv_client->remove_pending_request(result_future);
        capture_result->finished = false;
        goalHandle->abort(capture_result);
      } else {
        // auto srv_result = result_future.get();
        // response->success = srv_result->success;
        // response->message = srv_result->message;
        capture_result->finished = true;
        goalHandle->succeed(capture_result);
      }

    } else {
      // response->success = false;
      // response->message = "Failed to navigate to position";
      RCLCPP_INFO(this->get_logger(), "Movement failed");
      capture_result->finished = false;
      goalHandle->abort(capture_result);
    }

    setCaptureState(CaptureState::READY);
  }

  // Result that comes back from the PAL nav goal action
  rclcpp_action::ClientGoalHandle<nav2_msgs::action::NavigateToPose>::WrappedResult
  sendNavGoalCapture(const geometry_msgs::msg::Pose pose) {
    auto goal = nav2_msgs::action::NavigateToPose::Goal();
    goal.pose.header.frame_id = "map";
    goal.pose.header.stamp = this->get_clock()->now();
    goal.pose.pose = pose;
    RCLCPP_INFO(this->get_logger(), "Sending pose action %f %f", pose.position.x, pose.position.y);

    // TODO: Monitor feedback, and have a ready for when the goal was reached or failed.
    auto nav_goal_options =
        rclcpp_action::Client<nav2_msgs::action::NavigateToPose>::SendGoalOptions();

    // nav_goal_options.goal_response_callback = std::bind(&EyefulController::spinGoalCallback,
    // this, _1); nav_goal_options.feedback_callback =
    // std::bind(&EyefulController::spinFeedbackCallback, this, _1, _2);
    nav_goal_options.result_callback =
        std::bind(&EyefulController::navigateToPoseResultCallback, this, _1);

    nav_pose_client->wait_for_action_server();
    auto handle = nav_pose_client->async_send_goal(goal, nav_goal_options);

    // This is a complicated way of waiting for the action to finish, not just the goal being
    // accepted
    RCLCPP_INFO(this->get_logger(), "Returning pose action");
    return nav_pose_client->async_get_result(handle.get()).get();
  }

  // This will call capture on succeed and maybe aborted
  void navigateToPoseResultCallback(
      const rclcpp_action::ClientGoalHandle<nav2_msgs::action::NavigateToPose>::WrappedResult&
          result) {
    switch (result.code) {
      case rclcpp_action::ResultCode::SUCCEEDED:
        RCLCPP_INFO(this->get_logger(), "Succeeded. Can call service");
        break;
      case rclcpp_action::ResultCode::ABORTED:
        RCLCPP_INFO(this->get_logger(), "navigate to pose aborted");
        break;
      case rclcpp_action::ResultCode::CANCELED:
        RCLCPP_INFO(this->get_logger(), "CANCELLED");
        break;
      default:
        RCLCPP_INFO(this->get_logger(), "UHHHHHHHH");
    }
  }

  void setDriveMode(
      const std::shared_ptr<eyeful_ros_msgs::srv::SetDriveMode::Request> request,
      std::shared_ptr<eyeful_ros_msgs::srv::SetDriveMode::Response> response) {
    // TODO: Need to thread so I can wait for the mutex and not hold up the callback
    bool driveModeSet = false;
    if (request->batch_id == eyeful_tower::BatchId::FIRST) {
      driveModeSet = eyeful_tower->SetDriveMode1(request->drive_mode);
    } else if (request->batch_id == eyeful_tower::BatchId::SECOND) {
      driveModeSet = eyeful_tower->SetDriveMode2(request->drive_mode);
    }

    if (!driveModeSet) {
      response->message = "Drive mode invalid.";
      response->success = false;
    } else {
      response->message = "Drive modes set.";
      response->success = true;
    }

    RCLCPP_INFO(this->get_logger(), "%s", response->message.c_str());
  }
};

int main(int argc, char* argv[]) {
  rclcpp::init(argc, argv);

  rclcpp::executors::MultiThreadedExecutor executor;
  auto eyeful_node = std::make_shared<EyefulController>();

  executor.add_node(eyeful_node);
  executor.spin();

  rclcpp::shutdown();
  return 0;
}

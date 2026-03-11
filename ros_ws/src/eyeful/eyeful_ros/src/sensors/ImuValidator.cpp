// (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

#include <atomic>
#include <chrono>
#include <functional>
#include <memory>
#include <mutex>
#include <string>
#include <thread>

#include "geometry_msgs/msg/twist_stamped.hpp"
#include "geometry_msgs/msg/vector3_stamped.hpp"
#include "rclcpp/rclcpp.hpp"
#include "sensor_msgs/msg/imu.hpp"
#include "std_msgs/msg/bool.hpp"

#include "message_filters/subscriber.h"
#include "message_filters/sync_policies/approximate_time.h"
#include "message_filters/time_synchronizer.h"

using namespace std::chrono_literals;
using std::placeholders::_1;
using std::placeholders::_2;
using std::placeholders::_3;
using std::placeholders::_4;

class ImuValidator : public rclcpp::Node {
 private:
  double acc_delta = 0.5;
  double ang_vel_delta = 0.05;

  double tower_acc_delta = 0.2;
  double tower_ang_vel_delta = 0.05;

  rclcpp::Publisher<std_msgs::msg::Bool>::SharedPtr imu_ready_publisher;

  message_filters::Subscriber<sensor_msgs::msg::Imu> pal_imu_sync_sub;
  message_filters::Subscriber<sensor_msgs::msg::Imu> tower_imu_sync_sub;
  message_filters::Subscriber<geometry_msgs::msg::Vector3Stamped> tower_acc_sync_sub;
  message_filters::Subscriber<geometry_msgs::msg::TwistStamped> base_cmd_vel_sub;
  typedef message_filters::sync_policies::ApproximateTime<
      sensor_msgs::msg::Imu,
      sensor_msgs::msg::Imu,
      geometry_msgs::msg::TwistStamped,
      geometry_msgs::msg::Vector3Stamped>
      approx_policy;
  std::shared_ptr<message_filters::Synchronizer<approx_policy>> imu_sync;

  void imuSyncCallback(
      const sensor_msgs::msg::Imu::ConstSharedPtr& pal_imu,
      const sensor_msgs::msg::Imu::ConstSharedPtr& tower_imu,
      const geometry_msgs::msg::TwistStamped::ConstSharedPtr& cmd_vel,
      const geometry_msgs::msg::Vector3Stamped::ConstSharedPtr& tower_acc) {
    // Use angular velocity from PAL
    auto pal_ang_vel_x = pal_imu->angular_velocity.x;
    auto pal_ang_vel_y = pal_imu->angular_velocity.y;
    auto pal_ang_vel_z = pal_imu->angular_velocity.z;

    auto pal_ang_vel_in = inBounds(pal_ang_vel_x, 0, ang_vel_delta) &&
        inBounds(pal_ang_vel_y, 0, ang_vel_delta) && inBounds(pal_ang_vel_z, 0, ang_vel_delta);

    // Tower, angular velocity and linear acceleration should be checked
    auto lin_acc_x = tower_acc->vector.x;
    auto lin_acc_y = tower_acc->vector.y;
    auto lin_acc_z = tower_acc->vector.z;

    auto ang_vel_x = tower_imu->angular_velocity.x;
    auto ang_vel_y = tower_imu->angular_velocity.y;
    auto ang_vel_z = tower_imu->angular_velocity.z;

    auto lin_acc_in = inBounds(lin_acc_x, 0, tower_acc_delta) &&
        inBounds(lin_acc_y, 0, tower_acc_delta) && inBounds(lin_acc_z, 0, tower_acc_delta);
    auto ang_vel_in = inBounds(ang_vel_x, 0, tower_ang_vel_delta) &&
        inBounds(ang_vel_y, 0, tower_ang_vel_delta) && inBounds(ang_vel_z, 0, tower_ang_vel_delta);

    // Robot only linearly moves around X, and agnularly around Z
    auto cmd_lin_vel = cmd_vel->twist.linear.x;
    auto cmd_ang_vel = cmd_vel->twist.angular.z;

    bool cmd_is_zero = cmd_lin_vel == 0 && cmd_ang_vel == 0;

    std_msgs::msg::Bool msg;
    // msg.data = pal_ang_vel_in && lin_acc_in && ang_vel_in && cmd_is_zero;
    msg.data = lin_acc_in && ang_vel_in && cmd_is_zero;

    imu_ready_publisher->publish(msg);
  }

  bool inBounds(double value, double target, double delta) {
    double min = target - delta;
    double max = target + delta;

    if (value > max || value < min) {
      return false;
    }

    return true;
  }

 public:
  ImuValidator() : Node("imu_validator") {
    // Latching this topic so that at the start I can send a "false"
    rclcpp::QoS qos_profile(100);
    qos_profile.reliable();
    qos_profile.transient_local();

    imu_ready_publisher =
        this->create_publisher<std_msgs::msg::Bool>("/eyeful/imu_ready", qos_profile);

    rclcpp::QoS pal_sync_qos_profile(100);
    pal_sync_qos_profile.reliable();

    pal_imu_sync_sub.subscribe(this, "/base_imu", pal_sync_qos_profile.get_rmw_qos_profile());
    tower_imu_sync_sub.subscribe(this, "/imu/data", pal_sync_qos_profile.get_rmw_qos_profile());
    base_cmd_vel_sub.subscribe(
        this, "/mobile_base_controller/cmd_vel_out", pal_sync_qos_profile.get_rmw_qos_profile());
    // The free acceleration topic broadcasts a local non-gravity orientation that will be 0's when
    // standing still
    tower_acc_sync_sub.subscribe(
        this, "/filter/free_acceleration", pal_sync_qos_profile.get_rmw_qos_profile());

    imu_sync = std::make_shared<message_filters::Synchronizer<approx_policy>>(
        approx_policy(100),
        pal_imu_sync_sub,
        tower_imu_sync_sub,
        base_cmd_vel_sub,
        tower_acc_sync_sub);

    imu_sync->registerCallback(std::bind(&ImuValidator::imuSyncCallback, this, _1, _2, _3, _4));

    std_msgs::msg::Bool msg;
    msg.data = false;
    imu_ready_publisher->publish(msg);
  }
};

int main(int argc, char* argv[]) {
  rclcpp::init(argc, argv);

  rclcpp::executors::MultiThreadedExecutor executor;
  auto imu_node = std::make_shared<ImuValidator>();

  executor.add_node(imu_node);
  executor.spin();

  rclcpp::shutdown();
  return 0;
}

// (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

#include <atomic>
#include <chrono>
#include <functional>
#include <memory>
#include <mutex>
#include <sstream>
#include <string>
#include <thread>

#include "rclcpp/rclcpp.hpp"

using namespace std::chrono_literals;

/**
 * This node is designed to wait for the Ouster sensor to be ready.
 *
 */

class IPSensorChecker : public rclcpp::Node {
 private:
  int returnValue = 1;
  int retries = 60;
  int retryCount = 0;
  std::string command;
  std::string ip;
  rclcpp::TimerBase::SharedPtr timer;
  std::shared_future<void> future;
  bool timerDone = false;

  void timerCallback() {
    returnValue = system(command.c_str());
    retryCount++;
  }

 public:
  IPSensorChecker() : Node("sensor_checker") {
    this->declare_parameter("ip", rclcpp::PARAMETER_STRING);
    this->declare_parameter("retries", rclcpp::PARAMETER_INTEGER);

    ip = this->get_parameter("ip").as_string();
    retries = this->get_parameter("retries").as_int();

    std::stringstream cmd;
    cmd << "ping -c1 -s1 " << ip << " > /dev/null 2>&1";
    command = cmd.str();

    timer = this->create_wall_timer(1000ms, std::bind(&IPSensorChecker::timerCallback, this));
  }

  int GetCmdReturn() {
    return returnValue;
  }

  const std::string& GetIP() {
    return ip;
  }

  int GetRetries() {
    return retries;
  }

  int GetRetryCount() {
    return retryCount;
  }
};

int main(int argc, char const* argv[]) {
  rclcpp::init(argc, argv);
  rclcpp::executors::SingleThreadedExecutor executor;

  auto sensorChecker = std::make_shared<IPSensorChecker>();
  executor.add_node(sensorChecker);

  int ret = 1;
  while (sensorChecker->GetRetryCount() < sensorChecker->GetRetries()) {
    executor.spin_once();
    ret = sensorChecker->GetCmdReturn();

    if (ret == 0) {
      break;
    }

    std::this_thread::sleep_for(100ms);
  }

  rclcpp::shutdown();
  return ret;
}

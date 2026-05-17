// Copyright (c) Meta Platforms, Inc. and affiliates.

#pragma once
#include <vector>

#include "eyeful/Camera.h"

namespace eyeful {

class MultipleCameras {
 public:
  explicit MultipleCameras(
      SCRSDK::CrSdkControlMode control_mode = SCRSDK::CrSdkControlMode_Remote,
      size_t num_expected_cameras = 0);
  MultipleCameras(
      std::vector<std::array<unsigned char, 4>>& ips,
      SCRSDK::CrSdkControlMode control_mode = SCRSDK::CrSdkControlMode_Remote);
  ~MultipleCameras();
  size_t getCameraCount();
  std::vector<std::unique_ptr<Camera>> cameras;
  void captureImages(unsigned short int expected_exposures, std::chrono::milliseconds timeout);
  void captureCustomBracket(std::vector<CrInt64u>& shutter_speeds);
  bool transferImages(std::string path, int threads = 1);

 private:
  size_t camera_count_;
};
} // namespace eyeful

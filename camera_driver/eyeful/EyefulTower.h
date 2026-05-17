// Copyright (c) Meta Platforms, Inc. and affiliates.

#pragma once

#include <CrDeviceProperty.h>
#include <CrTypes.h>
#include <atomic>
#include <chrono>
#include <condition_variable>
#include <string>
#include "MultipleCameras.h"

namespace eyeful_tower {
inline static constexpr CrInt64u DRIVE_MODE = SCRSDK::CrDrive_Continuous_Bracket_10Ev_9pics;
inline static constexpr CrInt64u BATCH_DRIVE_MODE = SCRSDK::CrDrive_Continuous_Bracket_30Ev_5pics;
inline static constexpr unsigned short int EXPECTED_EXPOSURES = 9;
inline static constexpr unsigned short int EXPECTED_BATCH_EXPOSURES = 5;
inline static constexpr float BRACKET_STEP_SIZE = 0.3;
inline static constexpr std::chrono::milliseconds TIMEOUT = std::chrono::milliseconds(30000);
inline static constexpr float APERTURE = 8.0;

enum CameraReady {
  ERROR = -1,
  READY = 0,
  WAITING = 1,
};

enum BatchId {
  FIRST = 0,
  SECOND = 1,
};
} // namespace eyeful_tower

class UserInput {
 public:
  void wait_for_input();
  void notify_input();
  void set_expose();
  void clear_expose();
  void set_quit();
  bool quit();
  bool expose();

 private:
  std::atomic<bool> expose_{false};
  std::atomic<bool> quit_{false};
  std::condition_variable cv_;
  std::mutex mutex_;
};

/*
  Representing the Eyeful Tower. This will be exposed and usable by other libraries.

  This can be pulled in to the ROS side.
*/
class EyefulTower {
 public:
  EyefulTower(
      std::vector<std::array<unsigned char, 4>>& ips,
      const std::string& shutter1 = "1/100",
      const std::string& shutter2 = "1/250",
      int iso = 500,
      int iso2 = 500);
  ~EyefulTower();
  bool SetupBuiltInCapture();
  bool SetupBatchCapture();
  bool FormatCameras();
  CrInt64u GetShutter() const;
  CrInt64u SetShutter(const std::string& shutter1);
  CrInt64u GetShutter2() const;
  CrInt64u SetShutter2(const std::string& shutter2);
  int GetIso() const;
  void SetIso(const int iso);
  int GetIso2() const;
  void SetIso2(const int iso);
  CrInt64u GetDriveMode1() const;
  bool SetDriveMode1(const CrInt64u mode);
  CrInt64u GetDriveMode2() const;
  bool SetDriveMode2(const CrInt64u mode);
  void SetupSecondCapture(const std::string& shutter, int iso);
  void SetupFirstCapture(const std::string& shutter, int iso);
  bool ApplySettingsFirst();
  bool ApplySettingsSecond();
  void TriggerRawCapture();
  eyeful_tower::CameraReady GetReadyState();

  bool Capture();

 private:
  enum CaptureType { BUILT_IN_BRACKET, BATCH_BRACKET, CUSTOM_BRACKET };
  eyeful::MultipleCameras multipleCameras;
  size_t numCameras;
  CrInt64u shutter1;
  CrInt64u shutter2;
  CrInt64u driveMode1;
  CrInt64u driveMode2;
  int iso;
  int iso2;
  unsigned short int expectedExposures = 0;
  CaptureType captureType = BUILT_IN_BRACKET;
  eyeful_tower::CameraReady initState;
  bool captureBuiltIn();
  bool captureBatch();
  bool SetInitProperties(Camera::IsoInfo& iso_info);
  void setReadyState(bool);
  void setExpectedExposures(CrInt64u);
};

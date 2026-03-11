// (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

#include "EyefulTower.h"

#include <CameraRemote_SDK.h>
#include <CrDeviceProperty.h>
#include <CrTypes.h>
#include <magic_enum/magic_enum.hpp>
#include "Camera.h"
#include "logging/Logging.h"

namespace SDK = SCRSDK;
using namespace std::chrono_literals;

void UserInput::wait_for_input() {
  EYEFUL_LOGI("Waiting for user input");
  std::unique_lock<std::mutex> lock(mutex_);
  // I think we could still get a spurious wake up because of when we reset expose to false
  // I don't think it matters
  cv_.wait(lock, [this] { return (expose() == true || quit() == true); });
}
void UserInput::notify_input() {
  EYEFUL_LOGD("Notified user input");
  std::unique_lock<std::mutex> lock(mutex_);
  cv_.notify_all();
}

void UserInput::set_expose() {
  expose_.store(true);
}

void UserInput::clear_expose() {
  expose_.store(false);
}

void UserInput::set_quit() {
  quit_.store(true);
}

bool UserInput::quit() {
  return quit_.load();
}

bool UserInput::expose() {
  return expose_.load();
}

EyefulTower::EyefulTower(
    std::vector<std::array<unsigned char, 4>>& ips,
    const std::string& shutter1,
    const std::string& shutter2,
    int iso,
    int iso2)
    : multipleCameras(ips), initState(eyeful_tower::CameraReady::WAITING) {
  EYEFUL_LOGI("Eyeful Tower starting up");
  std::this_thread::sleep_for(30000ms);

  this->shutter1 = Camera::string2speed(shutter1);
  this->shutter2 = Camera::string2speed(shutter2);

  this->driveMode1 = eyeful_tower::BATCH_DRIVE_MODE;
  this->driveMode2 = eyeful_tower::BATCH_DRIVE_MODE;

  numCameras = multipleCameras.getCameraCount();

  this->iso = std::max(100, iso);
  this->iso2 = std::max(100, iso2);

  Camera::IsoInfo iso_info;
  iso_info.iso_mode = SDK::CrISOMode::CrISO_Normal;
  iso_info.iso_value = iso;

  bool success = SetInitProperties(iso_info);

  // the example application has this sleep in a similar spot. Seems necessary to actually take
  // image I have made no effort to tune it
  std::this_thread::sleep_for(1000ms);

  if (success) {
    EYEFUL_LOGI("Cameras Ready");
    this->initState = eyeful_tower::CameraReady::READY;
  } else {
    EYEFUL_LOGE("Error Initializing cameras. Retry.");
    this->initState = eyeful_tower::CameraReady::ERROR;
  }
}

eyeful_tower::CameraReady EyefulTower::GetReadyState() {
  return this->initState;
}

EyefulTower::~EyefulTower() {}

bool EyefulTower::SetupBuiltInCapture() {
  EYEFUL_LOGI("Setting up built in capture");
  Camera::IsoInfo iso_info;
  iso_info.iso_mode = SDK::CrISOMode::CrISO_Normal;
  iso_info.iso_value = iso;
  bool success = true;

  for (size_t n = 0; n < numCameras; n++) {
    success &= multipleCameras.cameras[n]->setShutterSpeed(shutter1);
    success &= multipleCameras.cameras[n]->setIso(iso_info);
    success &= multipleCameras.cameras[n]->setDriveMode(driveMode1);
  }

  captureType = CaptureType::BUILT_IN_BRACKET;
  return success;
}

bool EyefulTower::SetupBatchCapture() {
  // Might as well do the first one during setup...
  EYEFUL_LOGI("Setting up batch capture");
  bool success = true;

  // We test that both iso and shutter for both captures are valid, so these don't cause surprise
  // failures during captures
  Camera::IsoInfo iso1_info;
  iso1_info.iso_mode = SDK::CrISOMode::CrISO_Normal;
  iso1_info.iso_value = iso;

  Camera::IsoInfo iso2_info;
  iso2_info.iso_mode = SDK::CrISOMode::CrISO_Normal;
  iso2_info.iso_value = iso2;

  EYEFUL_LOGI("Starting settings validation tests...");
  EYEFUL_LOGI("Batch 1 values: {} {} {}", iso, shutter1, driveMode1);
  for (size_t n = 0; n < numCameras; n++) {
    success &= multipleCameras.cameras[n]->setIso(iso1_info);
    success &= multipleCameras.cameras[n]->setShutterSpeed(shutter1);
    success &= multipleCameras.cameras[n]->setDriveMode(driveMode1);
  }
  EYEFUL_LOGI("Tested first batch: {}", success);

  EYEFUL_LOGI("Batch 2 values: {} {} {}", iso2, shutter2, driveMode2);

  for (size_t n = 0; n < numCameras; n++) {
    success &= multipleCameras.cameras[n]->setIso(iso2_info);
    success &= multipleCameras.cameras[n]->setShutterSpeed(shutter2);
    success &= multipleCameras.cameras[n]->setDriveMode(driveMode2);
  }
  EYEFUL_LOGI("Tested second batch: {}", success);

  captureType = CaptureType::BATCH_BRACKET;

  setReadyState(success);
  return success;
}

void EyefulTower::setReadyState(bool success) {
  // If it fails, we assume error. Waiting will only be for initializing.
  this->initState = success ? eyeful_tower::CameraReady::READY : eyeful_tower::CameraReady::ERROR;
}

void EyefulTower::setExpectedExposures(CrInt64u driveMode) {
  switch (driveMode) {
    case SCRSDK::CrDriveMode::CrDrive_Continuous_Bracket_10Ev_5pics:
    case SCRSDK::CrDriveMode::CrDrive_Continuous_Bracket_13Ev_5pics:
    case SCRSDK::CrDriveMode::CrDrive_Continuous_Bracket_15Ev_5pics:
    case SCRSDK::CrDriveMode::CrDrive_Continuous_Bracket_17Ev_5pics:
    case SCRSDK::CrDriveMode::CrDrive_Continuous_Bracket_20Ev_5pics:
    case SCRSDK::CrDriveMode::CrDrive_Continuous_Bracket_30Ev_5pics: {
      expectedExposures = 5;
    } break;

    case SCRSDK::CrDriveMode::CrDrive_Continuous_Bracket_10Ev_7pics:
    case SCRSDK::CrDriveMode::CrDrive_Continuous_Bracket_13Ev_7pics:
    case SCRSDK::CrDriveMode::CrDrive_Continuous_Bracket_15Ev_7pics:
    case SCRSDK::CrDriveMode::CrDrive_Continuous_Bracket_17Ev_7pics:
    case SCRSDK::CrDriveMode::CrDrive_Continuous_Bracket_20Ev_7pics: {
      expectedExposures = 7;
    } break;

    case SCRSDK::CrDriveMode::CrDrive_Continuous_Bracket_10Ev_9pics: {
      expectedExposures = 9;
    } break;

    default:
      break;
  }

  EYEFUL_LOGI("Expected Exposures: {}", expectedExposures);
}

bool EyefulTower::FormatCameras() {
  for (size_t i = 0; i < numCameras; ++i) {
    if (multipleCameras.cameras[i] == NULL || !multipleCameras.cameras[i]->isConnected()) {
      EYEFUL_LOGE(
          "({}) Is not connected. Stopping format process", multipleCameras.cameras[i]->getLogId());
      return false;
    }
  }

  const auto cameraModel = multipleCameras.cameras[0]->getCameraModel();
  for (size_t i = 1; i < numCameras; ++i) {
    EYEFUL_CHECK_EQ(
        cameraModel.compare(multipleCameras.cameras[i]->getCameraModel()),
        0,
        "Not all cameras are the same model");
  }

  if (cameraModel.compare("ILCE-1") != 0) {
    EYEFUL_LOGF("Unsupported camera model {}", cameraModel);
    return false;
  }

  std::vector<Camera::MediaSlot> slots;
  std::function<std::optional<std::future<bool>>(Camera*, Camera::MediaSlot)> format_function;
  if (cameraModel.compare("ILCE-1") == 0) {
    EYEFUL_LOGI("Setting quick format for {} cameras", cameraModel);
    format_function = &Camera::quickFormatMedia;
    slots = {Camera::MediaSlot::SLOT1, Camera::MediaSlot::SLOT2};
  } else {
    EYEFUL_LOGI("Setting full format for {} cameras", cameraModel);
    format_function = &Camera::formatMedia;
    slots = {Camera::MediaSlot::SLOT1};
  }

  std::vector<std::optional<std::future<bool>>> format_futures(numCameras);
  for (auto& slot : slots) {
    int fails = 0;
    bool out;
    auto slot_name = magic_enum::enum_name(slot);
    EYEFUL_LOGI("Beginning {} formatting", slot_name);
    fails = 0;
    for (size_t i = 0; i < numCameras; ++i) {
      format_futures[i] = format_function(multipleCameras.cameras[i].get(), slot);
      EYEFUL_CHECK_TRUE(format_futures[i].has_value());
    }

    // This timeout comes from playing with the cameras and not any sort of real experiments
    // quick format should return significantly before this
    std::chrono::milliseconds timeout = 50s;
    for (size_t i = 0; i < numCameras; ++i) {
      if (format_futures[i]->wait_for(timeout) == std::future_status::ready) {
        out = format_futures[i]->get();
        if (!out) {
          // The Camera class will give a verbose warning to go with this error
          EYEFUL_LOGE(
              "({}) SD Card not formatted correctly", multipleCameras.cameras[i]->getLogId());
          ++fails;
        }
      } else {
        EYEFUL_LOGE(
            "({}) Timeout out while waiting to format {}",
            multipleCameras.cameras[i]->getLogId(),
            slot_name);
        ++fails;
      }
    }
    EYEFUL_LOGI("{} format attempt complete, there were {} failures", slot_name, fails);

    // If you move to slot 2 very quickly (100s of ms) the camera will report that quick format is
    // not enabled. If you move to slot 2 kinda quickly (1s) the camera will report that it quick
    // formatted the slot but it actually doesn't
    std::this_thread::sleep_for(5000ms);
    EYEFUL_LOGI("After waiting for slot ready: {}", slot_name);
  }

  return true;
}

CrInt64u EyefulTower::GetShutter() const {
  return shutter1;
}

bool EyefulTower::SetInitProperties(Camera::IsoInfo& iso_info) {
  // Sony SDK mentions to wait so the SDK can find the IP.
  // What is strange, is that property setting won't happen, but
  // you can trigger events on the camera like taking photos.
  bool success = true;
  for (size_t n = 0; n < numCameras; n++) {
    success &= multipleCameras.cameras[n]->setPcPriority();
    success &= multipleCameras.cameras[n]->setIso(iso_info);
    success &= multipleCameras.cameras[n]->setDateTime();
  }

  return success;
}

CrInt64u EyefulTower::SetShutter(const std::string& shutter_speed) {
  shutter1 = Camera::string2speed(shutter_speed);
  return shutter1;
}

void EyefulTower::SetupFirstCapture(const std::string& shutter, int iso) {
  SetShutter(shutter);
  SetIso(iso);
}

void EyefulTower::SetupSecondCapture(const std::string& shutter, int iso) {
  SetShutter2(shutter);
  SetIso2(iso);
}

void EyefulTower::SetIso(const int iso) {
  this->iso = std::max(100, iso);
}

void EyefulTower::SetIso2(const int iso) {
  this->iso2 = std::max(100, iso);
}

CrInt64u EyefulTower::GetDriveMode1() const {
  return driveMode1;
}

bool EyefulTower::SetDriveMode1(const CrInt64u mode) {
  if (mode > SCRSDK::CrDrive_Continuous_Bracket_03Ev_3pics ||
      mode <= SCRSDK::CrDrive_Continuous_Bracket_30Ev_2pics_Minus) {
    driveMode1 = mode;
    return true;
  }

  return false;
}

CrInt64u EyefulTower::GetDriveMode2() const {
  return driveMode2;
}

bool EyefulTower::SetDriveMode2(const CrInt64u mode) {
  if (mode > SCRSDK::CrDrive_Continuous_Bracket_03Ev_3pics ||
      mode <= SCRSDK::CrDrive_Continuous_Bracket_30Ev_2pics_Minus) {
    driveMode2 = mode;
    return true;
  }

  return false;
}

int EyefulTower::GetIso() const {
  return iso;
}

int EyefulTower::GetIso2() const {
  return iso2;
}

CrInt64u EyefulTower::GetShutter2() const {
  return shutter2;
}

CrInt64u EyefulTower::SetShutter2(const std::string& shutter_speed) {
  shutter2 = Camera::string2speed(shutter_speed);
  return shutter2;
}

bool EyefulTower::captureBuiltIn() {
  if (this->initState == eyeful_tower::CameraReady::READY) {
    setExpectedExposures(driveMode1);
    multipleCameras.captureImages(expectedExposures, eyeful_tower::TIMEOUT);

    return true;
  }

  return false;
}

bool EyefulTower::ApplySettingsFirst() {
  if (this->initState == eyeful_tower::CameraReady::READY) {
    std::this_thread::sleep_for(1000ms);
    Camera::IsoInfo iso1_info;
    iso1_info.iso_mode = SDK::CrISOMode::CrISO_Normal;
    iso1_info.iso_value = iso;

    bool success = true;
    for (size_t n = 0; n < numCameras; n++) {
      success &= multipleCameras.cameras[n]->setIso(iso1_info);
      success &= multipleCameras.cameras[n]->setShutterSpeed(shutter1);
      success &= multipleCameras.cameras[n]->setDriveMode(driveMode1);
    }

    if (success) {
      setExpectedExposures(driveMode1);
    }

    return success;
  }

  return false;
}

bool EyefulTower::ApplySettingsSecond() {
  if (this->initState == eyeful_tower::CameraReady::READY) {
    std::this_thread::sleep_for(1000ms);
    Camera::IsoInfo iso2_info;
    iso2_info.iso_mode = SDK::CrISOMode::CrISO_Normal;
    iso2_info.iso_value = iso2;

    bool success = true;
    for (size_t n = 0; n < numCameras; n++) {
      success &= multipleCameras.cameras[n]->setIso(iso2_info);
      success &= multipleCameras.cameras[n]->setShutterSpeed(shutter2);
      success &= multipleCameras.cameras[n]->setDriveMode(driveMode2);
    }

    if (success) {
      setExpectedExposures(driveMode2);
    }

    return success;
  }

  return false;
}

void EyefulTower::TriggerRawCapture() {
  if (this->initState == eyeful_tower::CameraReady::READY) {
    multipleCameras.captureImages(expectedExposures, eyeful_tower::TIMEOUT);
  }
}

bool EyefulTower::captureBatch() {
  if (this->initState == eyeful_tower::CameraReady::READY) {
    std::this_thread::sleep_for(2000ms);
    Camera::IsoInfo iso1_info;
    iso1_info.iso_mode = SDK::CrISOMode::CrISO_Normal;
    iso1_info.iso_value = iso;

    bool success = true;
    for (size_t n = 0; n < numCameras; n++) {
      success &= multipleCameras.cameras[n]->setIso(iso1_info);
      success &= multipleCameras.cameras[n]->setShutterSpeed(shutter1);
    }

    if (!success) {
      return false;
    }
    setExpectedExposures(driveMode1);
    multipleCameras.captureImages(expectedExposures, eyeful_tower::TIMEOUT);

    // TODO: can I get a flag to wait for from the SDK?
    // This is just an experimental value.
    std::this_thread::sleep_for(2000ms);
    Camera::IsoInfo iso2_info;
    iso2_info.iso_mode = SDK::CrISOMode::CrISO_Normal;
    iso2_info.iso_value = iso2;

    for (size_t n = 0; n < numCameras; n++) {
      success &= multipleCameras.cameras[n]->setIso(iso2_info);
      success &= multipleCameras.cameras[n]->setShutterSpeed(shutter2);
    }

    if (!success) {
      // If we fail here, we may need to do some recovery process.
      // If we get here, that means the first half of the bracket was taken, but not the second.
      // So we might need to do something to nullify the capture. For now, I will assume if the
      // first ones, go through these ones will, and I won't ever get here.
      return false;
    }

    setExpectedExposures(driveMode2);
    multipleCameras.captureImages(expectedExposures, eyeful_tower::TIMEOUT);

    return true;
  }

  return false;
}

bool EyefulTower::Capture() {
  switch (captureType) {
    case CaptureType::BUILT_IN_BRACKET:
      return captureBuiltIn();
    case CaptureType::BATCH_BRACKET:
      return captureBatch();
    case CaptureType::CUSTOM_BRACKET:
    default:
      EYEFUL_LOGW("Unknown or custom capture type, no action taken");
      return false;
  }
}

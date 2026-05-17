// Copyright (c) Meta Platforms, Inc. and affiliates.

#include <CameraRemote_SDK.h>
#include <CrDefines.h>
#include <CrDeviceProperty.h>
#include <CrTypes.h>
#include <cstddef>
#include <list>
#include <thread>
#include <vector>
#include "logging/Logging.h"

#include "eyeful/Camera.h"
#include "eyeful/MultipleCameras.h"

namespace eyeful {
namespace SDK = SCRSDK;
using namespace std::chrono_literals;

inline CrInt32 hexIpFromIp(unsigned char ipArr[4]) {
  return ipArr[0] | (ipArr[1] << 8) | (ipArr[2] << 16) | (ipArr[3] << 24);
}

/**
 * This constructor will mostly be temporary to work around the bug found in the enumerate camera
 * function
 *
 */
MultipleCameras::MultipleCameras(
    std::vector<std::array<unsigned char, 4>>& ips,
    SCRSDK::CrSdkControlMode mode) {
  const auto init = SDK::Init();
  if (!init) {
    EYEFUL_LOGE("Failed to initialize Sony SDK");
    exit(1);
  }

  camera_count_ = ips.size();
  cameras.resize(camera_count_);

  // The actual mac doesn't matter, each one just needs to be different
  CrInt8u mac[6] = {0x00, 0x00, 0x00, 0x00, 0x00, 0x00};
  for (size_t n = 0; n < camera_count_; n++) {
    CrInt32 hexIp = hexIpFromIp(ips.at(n).data());

    // If there are any errors, just quit. If you are using this mode, I assume you want all cameras
    // listed. Not connecting to all will be a fatal error.
    SDK::ICrCameraObjectInfo* cam = nullptr;
    auto err = SDK::CreateCameraObjectInfoEthernetConnection(
        &cam, SDK::CrCameraDeviceModel_ILCE_1, hexIp, mac, 0);
    if (CR_FAILED(err)) {
      EYEFUL_LOGE("Failed to create camera object: {}", ips.at(n)[3]);
      SDK::Release();
      exit(1);
    }

    cameras[n] = std::make_unique<Camera>(cam);
    bool connected = cameras[n]->connect(mode);
    if (!connected) {
      EYEFUL_LOGE("Failed to connect to camera: {}", ips.at(n)[3]);
      SDK::Release();
      exit(1);
    }

    // Increment the mac so it is different for each camera
    mac[5]++;
  }
}

MultipleCameras::MultipleCameras(SDK::CrSdkControlMode mode, size_t num_expected_cameras) {
  const auto init = SDK::Init();
  if (!init) {
    EYEFUL_LOGE("Failed to initialize Sony SDK");
    exit(1);
  }

  SDK::ICrEnumCameraObjectInfo* camera_list = nullptr;
  const auto enum_status = SDK::EnumCameraObjects(&camera_list);

  // In addition to failing due to no cameras being connected, this will fail if
  // the CrAdapter Sony SDK files are linked incorrectly or are in the wrong place
  if (CR_FAILED(enum_status) || camera_list == nullptr) {
    EYEFUL_LOGE("No cameras detected. Connect a camera and retry.");
    SDK::Release();
    std::exit(1);
  }
  camera_count_ = camera_list->GetCount();
  cameras.resize(camera_count_);
  EYEFUL_LOGI("Camera enumeration successful. {} detected", camera_count_);
  for (size_t n = 0; n < camera_count_; n++) {
    cameras[n] = std::make_unique<Camera>(camera_list->GetCameraObjectInfo(n));
    cameras[n]->connect(mode);
  }
  camera_list->Release();

  if (camera_count_ != num_expected_cameras && num_expected_cameras > 0) {
    EYEFUL_LOGE("Detected {} cameras while {} was expected.", camera_count_, num_expected_cameras);

    for (size_t n = 0; n < camera_count_; n++) {
      const auto cam_log_id = cameras[n]->getLogId();
      EYEFUL_LOGI("Detected camera: {}", cam_log_id);
    }
    SDK::Release();
    std::exit(1);
  }

  // Experimentally determined sleep
  // Without it, we get bus errors, or the cameras will miss the shutter command
  EYEFUL_LOGI("Waiting for cameras to fully initialize");
  std::this_thread::sleep_for(2500ms);
}

MultipleCameras::~MultipleCameras() {
  for (auto& camera : cameras) {
    camera->disconnect();
  }

  // Need to ensure the camera classes are destructed before the SDK release
  cameras.clear();
  SDK::Release();
}

size_t MultipleCameras::getCameraCount() {
  return camera_count_;
}

void MultipleCameras::captureImages(
    const unsigned short int expected_exposures,
    const std::chrono::milliseconds timeout) {
  EYEFUL_LOGI("Holding down shutter button");
  for (auto& camera : cameras) {
    camera->shutterButtonDown();
  }

  bool done = false;
  int count = 0;
  const int max_count = 60;
  const auto sleep_time = timeout / max_count;
  // This won't work well in continuous exposure mode
  // It also might make more conceptual sense to put the polling loop in the camera class, and
  // then wait for it here using promises or similar, TODO ?
  while (!done && count < max_count) {
    std::this_thread::sleep_for(sleep_time);
    count++;
    done = true;
    for (size_t n = 0; n < camera_count_; n++) {
      if (!(cameras[n]->exposures() == expected_exposures)) {
        done = false;
        if (count == max_count) {
          EYEFUL_LOGE("({}) timed out waiting for exposure", cameras[n]->getLogId());
        } else {
          break;
        }
      }
    }
  }

  EYEFUL_LOGI("Releasing shutter button");
  for (auto& camera : cameras) {
    camera->shutterButtonUp();
  }

  const auto total_time = count * sleep_time.count();
  EYEFUL_CHECK_LT(count, max_count, "Timed out waiting for exposures at {}ms", total_time);
  EYEFUL_LOGD(
      "{}ms to capture {} exposures ({} iterations at {}ms per iteration) ",
      total_time,
      expected_exposures,
      count,
      sleep_time.count());
}

void MultipleCameras::captureCustomBracket(std::vector<CrInt64u>& shutter_speeds) {
  for (size_t i = 0; i < camera_count_; ++i) {
    EYEFUL_CHECK_TRUE(cameras[i]->setDriveMode(SCRSDK::CrDrive_Single));
  }

  std::vector<std::optional<std::future<void>>> speed_futures(camera_count_);

  // timeout for setting shutter speed and taking images
  // we shouldn't come close to hitting it unless something is very broken
  const std::chrono::milliseconds timeout = 1500ms;

  for (auto& shutter_speed : shutter_speeds) {
    EYEFUL_LOGD("Setting shutter speed to {}", Camera::speed2string(shutter_speed));
    for (size_t i = 0; i < camera_count_; ++i) {
      speed_futures[i] = cameras[i]->setPropertyAsync(
          SDK::CrDevicePropertyCode::CrDeviceProperty_ShutterSpeed,
          shutter_speed,
          SDK::CrDataType::CrDataType_UInt32Array);
      EYEFUL_CHECK_TRUE(speed_futures[i].has_value());
    }
    for (size_t i = 0; i < camera_count_; ++i) {
      [[maybe_unused]] auto ready = speed_futures[i]->wait_for(timeout);
      cameras[i]->ClearPropertyPromise(SDK::CrDevicePropertyCode::CrDeviceProperty_ShutterSpeed);
      EYEFUL_CHECK(ready == std::future_status::ready);
    }

    captureImages(1, timeout);

    // this magic sleep keeps us from getting CrError_Api_InvalidCalled when setting shutter speeds
    std::this_thread::sleep_for(2000ms);
  }
  EYEFUL_LOGI("Bracket Complete");
}

bool MultipleCameras::transferImages(std::string path, int threads) {
  std::list<std::future<bool>> transfer_futures;

  EYEFUL_LOGI("Utilizing {} threads for transferring images.", threads);

  bool status = true;
  for (size_t i = 0; i < cameras.size(); ++i) {
    transfer_futures.emplace_back(
        std::async(
            std::launch::async,
            [](std::string path, Camera* camera) { return camera->transferFiles(path); },
            path,
            cameras[i].get()));
    // Limit the number of futures to the desired threads
    while (transfer_futures.size() >= static_cast<size_t>(threads)) {
      for (auto it = transfer_futures.begin(); it != transfer_futures.end(); ++it) {
        if (it->wait_for(std::chrono::seconds(1)) == std::future_status::ready) {
          status &= it->get();
          transfer_futures.erase(it);
          break;
        }
      }
    }
    if (!status) {
      EYEFUL_LOGE(
          "Failed to transfer images part way through. Waiting for remaining threads to complete.");
      break;
    }
  }

  for (auto& fut : transfer_futures) {
    status &= fut.get();
  }

  if (!status) {
    // Reattempt with a single thread. Failures with high thread count can occur
    // if wired connection is slow
    if (threads > 1) {
      EYEFUL_LOGW("Reattempting to transfer with a single thread.");
      return transferImages(path, 1);
    }

    EYEFUL_LOGE("Failed to transfer all images. You will need to restart the transfers.");
  }
  return status;
}

} // namespace eyeful

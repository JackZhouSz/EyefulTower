// Copyright (c) Meta Platforms, Inc. and affiliates.

#include <fmt/format.h>
#include <magic_enum/magic_enum.hpp>
#include <cstdlib>
#include <iostream>
#include <string>

#include "eyeful/Camera.h"
#include "eyeful/MultipleCameras.h"
#include "logging/Logging.h"

using namespace std::chrono_literals;

int main() {
  EYEFUL_LOGI("Eyeful SD Formatter Starting Up");

  eyeful::MultipleCameras multipleCameras;
  const auto ncams = multipleCameras.getCameraCount();

  // We only use one type of camera per system
  const auto cameraModel = multipleCameras.cameras[0]->getCameraModel();
  for (size_t i = 1; i < ncams; ++i) {
    EYEFUL_CHECK_EQ(
        cameraModel.compare(multipleCameras.cameras[i]->getCameraModel()),
        0,
        "Not all cameras are the same model");
  }

  if (cameraModel.compare("ILCE-1") != 0) {
    EYEFUL_LOGF("Unsupported camera model {}", cameraModel);
  }

  fmt::print("Would you like to format {} {} cameras? (y/n)\n", ncams, cameraModel);
  std::string response;
  while (true) {
    std::getline(std::cin, response);
    if ((response.compare("y") == 0) || (response.compare("Y") == 0) ||
        (response.compare("yes") == 0)) {
      break;
    } else if (
        (response.compare("n") == 0) || (response.compare("N") == 0) ||
        (response.compare("no") == 0)) {
      EYEFUL_LOGI("Exiting without formatting any cameras, goodbye!");
      exit(0);
    } else {
      fmt::print("{} is not a valid response. Please enter 'y' or 'n'\n", response);
    }
  }

  std::string confirm_sentence = "I want to erase all the data.";
  fmt::print(
      "This will erase all the data on the SD Cards. Please type the following sentence exactly to proceed:\n");
  fmt::print("{}\n", confirm_sentence);
  while (true) {
    std::getline(std::cin, response);
    if (confirm_sentence.compare(response) == 0) {
      break;
    } else {
      fmt::print("Input did not match, please enter the sentence exactly as written\n");
      fmt::print("{}\n", confirm_sentence);
    }
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

  std::vector<std::optional<std::future<bool>>> format_futures(ncams);
  for (auto& slot : slots) {
    int fails = 0;
    bool out;
    auto slot_name = magic_enum::enum_name(slot);
    EYEFUL_LOGI("Beginning {} formatting", slot_name);
    fails = 0;
    for (size_t i = 0; i < ncams; ++i) {
      format_futures[i] = format_function(multipleCameras.cameras[i].get(), slot);
      EYEFUL_CHECK_TRUE(format_futures[i].has_value());
    }

    // This timeout comes from playing with the cameras and not any sort of real experiments
    // quick format should return significantly before this
    std::chrono::milliseconds timeout = 50s;
    for (size_t i = 0; i < ncams; ++i) {
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
    if (slot != slots.back()) {
      std::this_thread::sleep_for(3000ms);
    }
  }
}

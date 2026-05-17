// Copyright (c) Meta Platforms, Inc. and affiliates.

#include "BracketGenerator.h"

#include <algorithm>
#include <cmath>
#include <iterator>

#include <CrTypes.h>

#include "eyeful/Camera.h"

#include "logging/Logging.h"

namespace bracket_gen {
static const std::vector<CrInt64u> kAllShutterSpeeds = {
    // This list contains 1/3ev steps. The camera needs to be in the 0.3ev exposure step mode.
    // On A1s, this setting is in Exposure/Color->Exposure Comp.->Exposure Step.
    // This setting can not be accessed by the SDK
    0x00017D00, // 1/32000 min electronic shutter speed on A1
    0x00016400, // 1/25600
    0x00014E20, // 1/20000
    0x00013E80, // 1/16000
    0x00013200, // 1/12800
    0x00012710, // 1/10000
    // must be set to electronic shutter mode to access the smaller value shutter speeds,
    // auto does not work
    // This setting can no be accessed by the SDK on the A1
    0x00011F40, // 1/8000 min mechanical shutter speed on A1
    0x00011900, // 1/6400
    0x00011388, // 1/5000
    0x00010FA0, // 1/4000
    0x00010C80, // 1/3200
    0x000109C4, // 1/2500
    0x000107D0, // 1/2000
    0x00010640, // 1/1600
    0x000104E2, // 1/1250
    0x000103E8, // 1/1000
    0x00010320, // 1/800
    0x00010280, // 1/640
    0x000101F4, // 1/500
    0x00010190, // 1/400
    0x00010140, // 1/320
    0x000100FA, // 1/250
    0x000100C8, // 1/200
    0x000100A0, // 1/160
    0x0001007D, // 1/125
    0x00010064, // 1/100
    0x00010050, // 1/80
    0x0001003C, // 1/60
    0x00010032, // 1/50
    0x00010028, // 1/40
    0x0001001E, // 1/30
    0x00010019, // 1/25
    0x00010014, // 1/20
    0x0001000F, // 1/15
    0x0001000D, // 1/13
    0x0001000A, // 1/10
    0x00010008, // 1/8
    0x00010006, // 1/6
    0x00010005, // 1/5
    0x00010004, // 1/4
    0x00010003, // 1/3
    0x0004000A, // 0.4
    0x0005000A, // 0.5
    0x0006000A, // 0.6
    0x0008000A, // 0.8
    0x000A000A, // 1
    0x000D000A, // 1.3
    0x0010000A, // 1.6
    0x0014000A, // 2
    0x0019000A, // 2.5
    0x001E000A, // 3
    0x0028000A, // 4
    0x0032000A, // 5
    0x003C000A, // 6
    0x0050000A, // 8
    0x0064000A, // 10
    0x0082000A, // 13
    0x0096000A, // 15
    0x00C8000A, // 20
    0x00FA000A, // 25
    0x012C000A, // 30 max shutter speed on the A1
};

std::vector<CrInt64u> genShutterSpeedList(
    const CrInt64u center_speed,
    const unsigned int number_of_images,
    float bracket_step_size,
    const bool electronic_shutter_mode) {
  std::vector<CrInt64u> result;

  if (number_of_images % 2 != 1) {
    EYEFUL_LOGE("Number of images must be odd");
    return result;
  }

  if (bracket_step_size <= 0) {
    EYEFUL_LOGE("Bracket step size must be positive");
    return result;
  }

  double whole_num;
  int step_decimal = std::round(std::modf(bracket_step_size, &whole_num) * 10);
  if (step_decimal != 0 && step_decimal != 3 && step_decimal != 6 && step_decimal != 7) {
    EYEFUL_LOGE(
        "Bracket step size must be a multiple of 0.3. Given value is {}", step_decimal / 10.0);
    return result;
  }

  if (step_decimal == 7) {
    // The camera rounds 1/3 down to 0.3 and 2/3 up to 0.7, so two "0.3" steps brings you to "0.7"
    // not 0.6. This corrects for that
    bracket_step_size -= 0.1;
  }

  const int shutter_step_size_multiplier = 3;
  const int step = static_cast<int>(std::round(bracket_step_size * shutter_step_size_multiplier));
  const int steps_from_center = (number_of_images - 1) / 2;

  auto all_shutter_speed_begin = kAllShutterSpeeds.begin();
  if (!electronic_shutter_mode) {
    const int me_shutter_offset = 6;
    std::advance(all_shutter_speed_begin, me_shutter_offset);
    EYEFUL_LOGD(
        "Using mechanical minimum shutter speed {}",
        Camera::speed2string(*all_shutter_speed_begin));
  }

  auto shutter_index = std::find(all_shutter_speed_begin, kAllShutterSpeeds.end(), center_speed);
  if (shutter_index == kAllShutterSpeeds.end()) {
    EYEFUL_LOGE("Center speed {} not found", Camera::speed2string(center_speed));
    return result;
  }

  const auto step_to_start = steps_from_center * step;

  if (std::distance(all_shutter_speed_begin, shutter_index) < step_to_start) {
    EYEFUL_LOGE("Bracket would go below minimum shutter speed");
    return result;
  }
  std::advance(shutter_index, -step_to_start);

  for (unsigned int n = 0; n < number_of_images; ++n) {
    result.push_back(*shutter_index);

    if (std::distance(shutter_index, kAllShutterSpeeds.end()) < step_to_start) {
      EYEFUL_LOGE("Bracket would go above maximum shutter speed");
      return result;
    }

    std::advance(shutter_index, step);
  }

  std::string bracket_string = "[";
  for (const auto& s : result) {
    bracket_string += Camera::speed2string(s) + ", ";
  }
  bracket_string.pop_back();
  bracket_string[bracket_string.length() - 1] = ']';
  EYEFUL_LOGI("Full bracket is {}", bracket_string);

  return result;
}
} // namespace bracket_gen

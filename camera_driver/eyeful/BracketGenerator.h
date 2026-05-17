// Copyright (c) Meta Platforms, Inc. and affiliates.

#pragma once

#include <CrTypes.h>
#include <vector>
namespace bracket_gen {
std::vector<CrInt64u> genShutterSpeedList(
    CrInt64u center_speed,
    unsigned int number_of_images,
    float bracket_step_size,
    bool electronic_shutter_mode = false);
} // namespace bracket_gen

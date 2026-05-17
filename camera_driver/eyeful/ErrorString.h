// Copyright (c) Meta Platforms, Inc. and affiliates.

#pragma once

#include <CrTypes.h>

#include <CrError.h>
#include <string>
#include <unordered_map>
namespace error2string {
std::string decode(CrInt32u error);
} // namespace error2string

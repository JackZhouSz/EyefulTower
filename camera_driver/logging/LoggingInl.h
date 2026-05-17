// Copyright (c) Meta Platforms, Inc. and affiliates.

#pragma once

#include <array>
#include <mutex>
#include <string_view>

#include <fmt/core.h>

namespace eyeful {

namespace detail {
namespace logging {

// Type-erased function that allows us to stuff more things into the logging_impl.cpp file
// See https://fmt.dev/11.0/api/#type-erasure
bool vlog(
    std::string_view file,
    int line,
    eyeful::LoggingConfig::Level level,
    fmt::string_view fmt_string,
    fmt::format_args fmt_args);

template <typename... Args>
bool log(
    const std::string_view file,
    const int line,
    const eyeful::LoggingConfig::Level level,
    const fmt::format_string<Args...> fmt,
    Args&&... args) {
  return vlog(file, line, level, fmt, fmt::make_format_args(args...));
}

// Note: The ##__VA_ARGS__ only works on gcc and probalbly MSVC. It doesn't work on clang.
// Make it convenient to implement the various EYEFUL_LOG* macros, and hide from user.
#define EYEFUL_LOG_IMPL(level, fmt_string, ...) \
  ::eyeful::detail::logging::log(__FILE__, __LINE__, level, fmt_string, ##__VA_ARGS__)

// Make it convenient to implement the various EYEFUL_LOG*_ONCE macros, and hide from user.

// Use macro expansion to create, for each use of LOG_EVERY_N(), static
// variables with the __LINE__ expansion as part of the variable name.
#define EYEFUL_LOG_ONCE_VARNAME(base, line) EYEFUL_LOG_ONCE_VARNAME_CONCAT(base, line)
#define EYEFUL_LOG_ONCE_VARNAME_CONCAT(base, line) base##line

#define EYEFUL_LOG_ONCE_FLAG EYEFUL_LOG_ONCE_VARNAME(flag_, __LINE__)

#define EYEFUL_LOG_ONCE_IMPL(level, fmt_string, ...)                                         \
  {                                                                                          \
    static std::once_flag EYEFUL_LOG_ONCE_FLAG;                                              \
    std::call_once(                                                                          \
        EYEFUL_LOG_ONCE_FLAG, [&]() { EYEFUL_LOG_IMPL(level, fmt_string, ##__VA_ARGS__); }); \
  }

void flush();

#define EYEFUL_CHECK_IMPL(condition_, label_, ...) \
  do {                                             \
    if (condition_) {                              \
    }                                              \
  } while (0)

#define EYEFUL_CHECK_DETAIL_OP1(val1, val2, op, ...) \
  if ((val1)op(val2)) {                              \
  }

} // namespace logging
} // namespace detail
} // namespace eyeful

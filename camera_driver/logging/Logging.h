// (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

#pragma once

#include <array>
#include <filesystem>
#include <utility>

#include <fmt/core.h>

namespace eyeful {

namespace logging {
// Use `eyeful::logging::runtime` to wrap any runtime format strings.
using fmt::runtime;
} // namespace logging

struct LoggingConfig {
  enum class Mode { Stdout, File, None };
  enum class Level { Fatal, Error, Warning, Info, Debug, Trace };
  enum class Sinks {
    None = 0,
    Glog = 1 << 1,
  };

  // Human-readable name -> enum mappings, useful for e.g. CLI11.
  // Given as an array of pairs rather than e.g. a map to allow CLI11 to print in the right order.
  static const std::array<std::pair<std::string, Mode>, 3>& getModeMap();
  static const std::array<std::pair<std::string, Level>, 6>& getLevelMap();

  // Users can either directly modify these fields, or just use aggregated initialization (perhaps
  // with designated initializers).
  Mode mode = Mode::Stdout;
  Level level = Level::Trace;
  Sinks sinks = Sinks::None;

  // Users can specify the output directory for the log file, if it's needed (e.g. for FILE logger).
  std::filesystem::path output_dir;
};

inline LoggingConfig::Sinks operator|(LoggingConfig::Sinks lhs, LoggingConfig::Sinks rhs) {
  using ut = std::underlying_type_t<LoggingConfig::Sinks>;
  return static_cast<LoggingConfig::Sinks>(static_cast<ut>(lhs) | static_cast<ut>(rhs));
}

// Users are allowed to configure logging.
//
// Note that this is *not* thread-safe, and should only be called when the user is certain that
// there are no other log statements happening, e.g. right at the beginning of the program.
void configureLogging(const LoggingConfig& config);

} // namespace eyeful

// Implementation details that aren't relevant to the public API
#include "LoggingInl.h"

// In rare circumstances, it may be useful to explicitly flush the logging stream.
#define EYEFUL_LOG_FLUSH() eyeful::detail::logging::flush()

// Fatal log, abort() the program immediately as the failure is not meant to be recoverable
#define EYEFUL_LOGF(fmt_string, ...)                                               \
  EYEFUL_LOG_IMPL(eyeful::LoggingConfig::Level::Fatal, fmt_string, ##__VA_ARGS__); \
  EYEFUL_LOG_FLUSH();                                                              \
  abort()

// The main logging macros
#define EYEFUL_LOGE(fmt_string, ...) \
  EYEFUL_LOG_IMPL(eyeful::LoggingConfig::Level::Error, fmt_string, ##__VA_ARGS__)
#define EYEFUL_LOGW(fmt_string, ...) \
  EYEFUL_LOG_IMPL(eyeful::LoggingConfig::Level::Warning, fmt_string, ##__VA_ARGS__)
#define EYEFUL_LOGI(fmt_string, ...) \
  EYEFUL_LOG_IMPL(eyeful::LoggingConfig::Level::Info, fmt_string, ##__VA_ARGS__)
#define EYEFUL_LOGD(fmt_string, ...) \
  EYEFUL_LOG_IMPL(eyeful::LoggingConfig::Level::Debug, fmt_string, ##__VA_ARGS__)
#define EYEFUL_LOGT(fmt_string, ...) \
  EYEFUL_LOG_IMPL(eyeful::LoggingConfig::Level::Trace, fmt_string, ##__VA_ARGS__)

#define EYEFUL_CHECK(condition, ...) EYEFUL_CHECK_IMPL(condition, #condition, __VA_ARGS__)

#define EYEFUL_CHECK_TRUE(val, ...) \
  EYEFUL_CHECK_IMPL(static_cast<bool>(val), "(" #val ")", ##__VA_ARGS__)

#define EYEFUL_CHECK_EQ(val1, val2, ...) EYEFUL_CHECK_DETAIL_OP1(val1, val2, ==, ##__VA_ARGS__)
#define EYEFUL_CHECK_NE(val1, val2, ...) EYEFUL_CHECK_DETAIL_OP1(val1, val2, !=, ##__VA_ARGS__)
#define EYEFUL_CHECK_GE(val1, val2, ...) EYEFUL_CHECK_DETAIL_OP1(val1, val2, >=, ##__VA_ARGS__)
#define EYEFUL_CHECK_GT(val1, val2, ...) EYEFUL_CHECK_DETAIL_OP1(val1, val2, >, ##__VA_ARGS__)
#define EYEFUL_CHECK_LE(val1, val2, ...) EYEFUL_CHECK_DETAIL_OP1(val1, val2, <=, ##__VA_ARGS__)
#define EYEFUL_CHECK_LT(val1, val2, ...) EYEFUL_CHECK_DETAIL_OP1(val1, val2, <, ##__VA_ARGS__)

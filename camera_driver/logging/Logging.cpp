// (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

#include "Logging.h"

#include <cassert>
#include <cstdio>
#include <ctime>

#include <chrono>
#include <filesystem>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <string>

namespace eyeful {

namespace {

constinit const std::array kLevelString = {"FATAL", "ERROR", "WARN", "INFO", "DEBUG", "TRACE"};
constinit const std::array kLevelColorStart = {
    /* LoggingConfig::Level::Fatal   -> */ "\u001b[31m", // Red
    /* LoggingConfig::Level::Error   -> */ "\u001b[31m", // Red
    /* LoggingConfig::Level::Warning -> */ "\u001b[33m", // Yellow
    /* LoggingConfig::Level::Info    -> */ "\u001b[32m", // Green
    /* LoggingConfig::Level::Debug   -> */ "\u001b[36m", // Blue
    /* LoggingConfig::Level::Trace   -> */ "" // No color
};
constexpr const char* kLevelColorEnd = "\u001b[0m";

size_t levelToIndex(const eyeful::LoggingConfig::Level level) {
  return static_cast<size_t>(level);
}

class FileLogger {
 public:
  explicit FileLogger(const std::filesystem::path& path_str) {
    std::filesystem::path path = std::filesystem::absolute(path_str);

    // Create the parent directory if it doesn't exist.
    std::filesystem::create_directories(path.parent_path());

    // Use <iostream> to output to console, since fmt::print seems to make the VR code unhappy.
    std::cout << "Eyeful log file: " << path << std::endl;
    file_ = std::fopen(path.string().c_str(), "w");
  }

  ~FileLogger() {
    if (file_) {
      std::fclose(file_);
    }
  }

  FileLogger(const FileLogger&) = delete;
  FileLogger(FileLogger&&) = delete;
  FileLogger& operator=(const FileLogger&) = delete;
  FileLogger& operator=(FileLogger&&) = delete;

  FILE* getFile() {
    return file_;
  }

 private:
  FILE* file_ = nullptr;
};

LoggingConfig& getLoggingConfigSingleton() {
  static LoggingConfig config;
  return config;
}

const LoggingConfig& getLoggingConfig() {
  return getLoggingConfigSingleton();
}

std::FILE* getLoggerFileSingleton() {
  const auto now_time = std::chrono::system_clock::to_time_t(std::chrono::system_clock::now());
  std::stringstream ss;
  ss << "eyeful_log_" << std::put_time(std::localtime(&now_time), "%Y-%m-%dT%H-%M-%S") << ".txt";
  static FileLogger logger(getLoggingConfig().output_dir / ss.str());
  return logger.getFile();
}

[[maybe_unused]] bool operator&(LoggingConfig::Sinks lhs, LoggingConfig::Sinks rhs) {
  using ut = std::underlying_type_t<LoggingConfig::Sinks>;
  return (static_cast<ut>(lhs) & static_cast<ut>(rhs));
}

} // namespace

const std::array<std::pair<std::string, eyeful::LoggingConfig::Mode>, 3>&
eyeful::LoggingConfig::getModeMap() {
  static const std::array<std::pair<std::string, eyeful::LoggingConfig::Mode>, 3> map{
      {{"Stdout", eyeful::LoggingConfig::Mode::Stdout},
       {"File", eyeful::LoggingConfig::Mode::File},
       {"None", eyeful::LoggingConfig::Mode::None}}};
  return map;
}

const std::array<std::pair<std::string, eyeful::LoggingConfig::Level>, 6>&
eyeful::LoggingConfig::getLevelMap() {
  static const std::array<std::pair<std::string, eyeful::LoggingConfig::Level>, 6> map{
      {{"Fatal", eyeful::LoggingConfig::Level::Fatal},
       {"Error", eyeful::LoggingConfig::Level::Error},
       {"Warning", eyeful::LoggingConfig::Level::Warning},
       {"Info", eyeful::LoggingConfig::Level::Info},
       {"Debug", eyeful::LoggingConfig::Level::Debug},
       {"Trace", eyeful::LoggingConfig::Level::Trace}}};
  return map;
}

void configureLogging(const LoggingConfig& config) {
  getLoggingConfigSingleton() = config;
}

namespace detail::logging {

bool vlog(
    const std::string_view file,
    const int line,
    const eyeful::LoggingConfig::Level level,
    const fmt::string_view fmt_string,
    const fmt::format_args fmt_args) {
  if (level > getLoggingConfig().level) {
    return false;
  }

  // Figure out whether we want to wrap the user's fmt_string with our own prefixes
  std::string wrapped_fmt_string;
  switch (getLoggingConfig().mode) {
    case LoggingConfig::Mode::Stdout: // fallthrough
    case LoggingConfig::Mode::File: {
      wrapped_fmt_string = fmt::format(
          "[{}:{}][{:>5}]: {}", file, line, kLevelString[levelToIndex(level)], fmt_string);
      break;
    }
    case LoggingConfig::Mode::None: {
      break;
    }
    default: {
      throw std::runtime_error("Invalid logging mode specified!");
    }
  }

  const auto formatted = fmt::vformat(wrapped_fmt_string, fmt_args);

  // And then actually write out the formatted string (potentially with prefixes) as specified.
  switch (getLoggingConfig().mode) {
    case LoggingConfig::Mode::Stdout: {
      fmt::print("{}{}{}\n", kLevelColorStart[levelToIndex(level)], formatted, kLevelColorEnd);
      break;
    }
    case LoggingConfig::Mode::File: {
      fmt::print(getLoggerFileSingleton(), "{}\n", formatted);
      flush();
      break;
    }
    case LoggingConfig::Mode::None: {
      break;
    }
    default: {
      throw std::runtime_error("Invalid logging mode specified!");
    }
  }

  return true;
}

void flush() {
  switch (getLoggingConfig().mode) {
    case LoggingConfig::Mode::Stdout: {
      std::fflush(stdout);
      std::fflush(stderr);
      break;
    }

    case LoggingConfig::Mode::File: {
      std::fflush(getLoggerFileSingleton());
      break;
    }
    case LoggingConfig::Mode::None: {
      break;
    }
    default: {
      throw std::runtime_error("Invalid logging mode specified!");
    }
  }
}

} // namespace detail::logging
} // namespace eyeful

// Copyright (c) Meta Platforms, Inc. and affiliates.

#include <CLI/CLI.hpp>
#include <magic_enum/magic_enum.hpp>
#include <filesystem>
#include <string>

#include "logging/Logging.h"

#include "eyeful/Camera.h"
#include "eyeful/MultipleCameras.h"

struct TransferOptions {
  std::string dataset_name;
  size_t num_expected_cameras = 0;
  int threads = 10;
};

std::vector<std::array<unsigned char, 4>> ips = {
    {192, 168, 1, 40},
    {192, 168, 1, 41},
    {192, 168, 1, 42},
    {192, 168, 1, 43},
    {192, 168, 1, 44},
    {192, 168, 1, 45},
    {192, 168, 1, 46},
    {192, 168, 1, 47},
    {192, 168, 1, 48},
    {192, 168, 1, 49},
    {192, 168, 1, 50},
    {192, 168, 1, 51},
    {192, 168, 1, 52},
    {192, 168, 1, 53},
};

namespace SDK = SCRSDK;
using namespace std::chrono_literals;

std::string capturePath;

bool validateCaptureDirectory() {
  // Should be set before running this
  const char* value = std::getenv("EYEFUL_CAPTURE_DIR");
  return (value != nullptr && std::strlen(value) > 0);
}

std::string ensureDirectoryExists(const std::string& path) {
  try {
#ifdef _WIN32
    std::string newPath =
        (std::filesystem::path(capturePath) / std::filesystem::path(path)).string();
#else
    std::string newPath = std::filesystem::path(capturePath) / std::filesystem::path(path);
#endif

    if (!std::filesystem::exists(newPath)) {
      std::filesystem::create_directories(newPath);
      std::cout << "Created directory: " << newPath << std::endl;
    } else if (!std::filesystem::is_directory(newPath)) {
      throw CLI::ValidationError("Path exists but is not a directory: " + newPath);
    }

    return path;
  } catch (const std::filesystem::filesystem_error& e) {
    throw CLI::ValidationError("Failed to create directory: " + std::string(e.what()));
  }
}

int main(int argc, char** argv) {
  EYEFUL_LOGI("Camera transfer initiating...");
  TransferOptions options;

  if (!validateCaptureDirectory()) {
    EYEFUL_LOGF("EYEFUL_CAPTURE_DIR not set.");
    return 1;
  }

  capturePath = std::getenv("EYEFUL_CAPTURE_DIR");

  CLI::App app;
  app.add_option("-d", options.dataset_name, "Name of the dataset.")
      ->required()
      ->transform(ensureDirectoryExists);

  app.add_option("-n", options.num_expected_cameras, "Expected number of cameras.")
      ->default_val(14);
  app.add_option("-t", options.threads, "Number of threads.")->default_val(10);

  CLI11_PARSE(app, argc, argv);

#ifdef _WIN32
  std::string outputDir =
      (std::filesystem::path(capturePath) / std::filesystem::path(options.dataset_name)).string();
#else
  std::string outputDir =
      std::filesystem::path(capturePath) / std::filesystem::path(options.dataset_name);
#endif

  EYEFUL_LOGI("Waiting for cameras to initialize.");
  eyeful::MultipleCameras multipleCameras(ips, SDK::CrSdkControlMode_ContentsTransfer);

  std::this_thread::sleep_for(10000ms);
  EYEFUL_LOGI("Cameras initialized.");
  const auto ncams = multipleCameras.getCameraCount();

  const std::string& cameraModel = multipleCameras.cameras[0]->getCameraModel();
  if (cameraModel.compare("ILCE-1") != 0) {
    EYEFUL_LOGF("Unsupported camera model {}", cameraModel);
  }

  // We only use one type of camera per system
  for (size_t i = 1; i < ncams; ++i) {
    EYEFUL_CHECK_EQ(
        cameraModel,
        multipleCameras.cameras[i]->getCameraModel(),
        "Not all cameras are the same model");
  }

  bool transfer_success = multipleCameras.transferImages(outputDir, options.threads);

  EYEFUL_LOGI("Content transfer finished.");
  if (transfer_success) {
    EYEFUL_LOGI("GOOD TRANSFER");
    return 0;
  } else {
    EYEFUL_LOGI("BAD TRANSFER");
    return 1;
  }
}

// Copyright (c) Meta Platforms, Inc. and affiliates.

#include "eyeful/EyefulTower.h"

#include <array>
#include <vector>

int main() {
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
  EyefulTower eyeful_tower(ips);
  eyeful_tower.SetupBatchCapture();
  eyeful_tower.Capture();
}

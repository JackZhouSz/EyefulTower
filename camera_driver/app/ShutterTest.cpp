// (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

#include "eyeful/EyefulTower.h"

#include <array>
#include <vector>

int main() {
  std::vector<std::array<unsigned char, 4>> ips = {
      {192, 168, 1, 40},
  };

  std::string shutter1 = "1/100";
  std::string shutter2 = "1/500"; // 1/500 will get the bottom range in 1/32000

  EyefulTower eyeful_tower(ips);

  eyeful_tower.SetupFirstCapture(shutter1, 500);
  eyeful_tower.SetupSecondCapture(shutter2, 100);

  eyeful_tower.SetupBatchCapture();
  eyeful_tower.Capture();
  eyeful_tower.Capture();
}

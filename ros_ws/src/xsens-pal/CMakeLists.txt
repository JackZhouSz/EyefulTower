# Copyright (c) Meta Platforms, Inc. and affiliates.

#Set minimum required CMake version and project name.
cmake_minimum_required(VERSION 3.5)
project(meta_xsens_config)

find_package(ament_cmake REQUIRED)
find_package(pal_module_cmake QUIET)

ament_package()

# Register pal modules
if (pal_module_cmake_FOUND)
  pal_register_modules(
    module/xsens_module.yaml
  )
  pal_register_module_sets(
    module/xsens_set.yaml
  )
endif()

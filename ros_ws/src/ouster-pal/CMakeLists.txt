# (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

#Set minimum required CMake version and project name.
cmake_minimum_required(VERSION 3.5)
project(meta_ouster_config)

find_package(ament_cmake REQUIRED)
find_package(pal_module_cmake QUIET)

install(
  DIRECTORY
    config
  DESTINATION
    share/${PROJECT_NAME}
)

ament_package()

# Register pal modules
if (pal_module_cmake_FOUND)
  pal_register_modules(
    module/ouster_module.yaml
  )
  pal_register_module_sets(
    module/ouster_set.yaml
  )
endif()

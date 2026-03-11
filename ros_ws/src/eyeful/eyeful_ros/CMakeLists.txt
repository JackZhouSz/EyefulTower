cmake_minimum_required(VERSION 3.8)
project(eyeful_ros)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()
# find dependencies
find_package(ament_cmake REQUIRED)
# uncomment the following section in order to fill in
# further dependencies manually.
# find_package(<dependency> REQUIRED)

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  # the following line skips the linter which checks for copyrights
  # comment the line when a copyright and license is added to all source files
  set(ament_cmake_copyright_FOUND TRUE)
  # the following line skips cpplint (only works in a git repo)
  # comment the line when this package is in a git repo and when
  # a copyright and license is added to all source files
  set(ament_cmake_cpplint_FOUND TRUE)
  ament_lint_auto_find_test_dependencies()
endif()

add_subdirectory(deps/camera_driver)

# Setting up the sony stuff. Do we want to make this conditional? And try to find a user defined locations?
set(SONY_CAMERA_SDK_INCLUDE_DIR "/usr/local/include/CRSDK")
set(SONY_CAMERA_SHARED_PATH "$ENV{HOME}/CRSDK")

include_directories(
  SYSTEM ${SONY_CAMERA_SDK_INCLUDE_DIR}
  ${CMAKE_CURRENT_SOURCE_DIR}/deps/camera_driver
)

set(CMAKE_INSTALL_RPATH "/usr/local/lib")

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(std_msgs REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(tf2 REQUIRED)
find_package(tf2_ros REQUIRED)
find_package(rclcpp_action REQUIRED)
find_package(nav2_msgs REQUIRED)
find_package(std_srvs REQUIRED)
find_package(eyeful_ros_msgs REQUIRED)
find_package(message_filters REQUIRED)
find_package(pal_module_cmake QUIET)

add_executable(pal_controller src/EyefulController.cpp)
ament_target_dependencies(pal_controller
  geometry_msgs
  sensor_msgs
  rclcpp
  tf2
  tf2_ros
  std_msgs
  nav2_msgs
  rclcpp_action
  std_srvs
  eyeful_ros_msgs
)

target_link_libraries(pal_controller eyeful)

install(TARGETS pal_controller
  DESTINATION lib/${PROJECT_NAME}
)

add_executable(imu_validator src/sensors/ImuValidator.cpp)
ament_target_dependencies(imu_validator
  geometry_msgs
  message_filters
  sensor_msgs
  rclcpp
  tf2
  tf2_ros
  std_msgs
  nav2_msgs
  rclcpp_action
  std_srvs
  eyeful_ros_msgs
)

install(TARGETS imu_validator
  DESTINATION lib/${PROJECT_NAME}
)

add_executable(sensor_wait src/sensors/IPSensorChecker.cpp)
ament_target_dependencies(sensor_wait
  rclcpp
)

install(TARGETS sensor_wait
  DESTINATION lib/${PROJECT_NAME}
)

# We need the CrAdapter directory next to the executable
install(DIRECTORY ${SONY_CAMERA_SHARED_PATH}/CrAdapter
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()

# Register pal modules
if (pal_module_cmake_FOUND)
  pal_register_modules(
    module/999_eyeful_ros_module.yaml
    module/sensor_waits.yaml
  )
  pal_register_module_sets(
    module/999_eyeful_set.yaml
    module/sensor_waits_set.yaml
  )
endif()

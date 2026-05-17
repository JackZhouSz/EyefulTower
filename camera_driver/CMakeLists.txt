# Copyright (c) Meta Platforms, Inc. and affiliates.

cmake_minimum_required(VERSION 3.8)

project(eyeful VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
    # Ignoring the zero variadic marco warning
    add_compile_options(-Wall -Wextra -Wpedantic -Wno-gnu-zero-variadic-macro-arguments)
elseif(CMAKE_CXX_COMPILER_ID MATCHES "MSVC")
    # Windows-specific compiler flags for MSVC
    add_compile_options(/W4)
    # Disable some common warnings that might not be relevant
    add_compile_options(/wd4251 /wd4275)  # DLL interface warnings

     add_definitions(-D_UNICODE -DUNICODE)
endif()

# Add fmt from third-party directory


# Platform-specific Sony Camera SDK paths
if(WIN32)
    # Windows: Assume CRSDK is in user's home directory
    set(USER_HOME_DIR "$ENV{USERPROFILE}")
    set(SONY_CAMERA_SDK_BASE_DIR "${USER_HOME_DIR}/CRSDK" CACHE PATH "Base path to Sony Camera SDK")
    set(SONY_CAMERA_SDK_LIB_DIR "${SONY_CAMERA_SDK_BASE_DIR}/lib" CACHE PATH "Path to Sony Camera SDK libraries")
    set(SONY_CAMERA_SDK_INCLUDE_DIR "${SONY_CAMERA_SDK_BASE_DIR}/include" CACHE PATH "Path to Sony Camera SDK include files")
    message(STATUS "Windows detected - using CRSDK from ${SONY_CAMERA_SDK_BASE_DIR}")
else()
    set(SONY_CAMERA_SDK_LIB_DIR "/usr/local/lib" CACHE PATH "Path to Sony Camera SDK libraries")
    set(SONY_CAMERA_SDK_INCLUDE_DIR "/usr/local/include" CACHE PATH "Path to Sony Camera SDK include files")
endif()

set(CMAKE_POSITION_INDEPENDENT_CODE ON)
add_subdirectory(third-party/magic_enum)
add_subdirectory(third-party/fmt)

include_directories(
    ${CMAKE_CURRENT_SOURCE_DIR}
    ${CMAKE_CURRENT_SOURCE_DIR}/logging
    ${CMAKE_CURRENT_SOURCE_DIR}/eyeful
    ${CMAKE_CURRENT_SOURCE_DIR}/third-party/magic_enum/include
    ${CMAKE_CURRENT_SOURCE_DIR}/third-party/cli11/include
)

include_directories(SYSTEM
    ${SONY_CAMERA_SDK_INCLUDE_DIR}
    ${SONY_CAMERA_SDK_INCLUDE_DIR}/CRSDK
)

# Logging library
add_library(logging
    logging/Logging.cpp
    logging/Logging.h
)
target_link_libraries(logging PUBLIC fmt::fmt)

# Base Eyeful library
set(EYEFUL_SOURCES
    eyeful/BracketGenerator.cpp
    eyeful/BracketGenerator.h
    eyeful/Camera.cpp
    eyeful/Camera.h
    eyeful/ErrorString.cpp
    eyeful/ErrorString.h
    eyeful/MultipleCameras.cpp
    eyeful/MultipleCameras.h
    eyeful/EyefulTower.cpp
    eyeful/EyefulTower.h
)

add_library(eyeful ${EYEFUL_SOURCES})
target_link_libraries(eyeful PUBLIC logging magic_enum fmt::fmt)


# SD Formater
add_executable(sd_format
    app/Format.cpp
)
target_link_libraries(sd_format PRIVATE eyeful)

# Transferer
add_executable(transfer
    app/Transfer.cpp
)
target_link_libraries(transfer PRIVATE eyeful)

# Simple eyeful test app
add_executable(eyeful_test
    app/EyefulTest.cpp
)
target_link_libraries(eyeful_test PRIVATE eyeful)

# Shutter value testing app
add_executable(shutter_test
    app/ShutterTest.cpp
)
target_link_libraries(shutter_test PRIVATE eyeful)

# Find Sony Camera SDK library with platform-specific handling
if(WIN32)
    # On Windows, look for .lib files for linking
    find_library(CR_CORE_LIB
        NAMES Cr_Core libCr_Core
        PATHS ${SONY_CAMERA_SDK_LIB_DIR}
        PATH_SUFFIXES lib x64/lib x86/lib Release Debug
    )

    # Also check for common Windows library directory structures
    if(NOT CR_CORE_LIB)
        find_library(CR_CORE_LIB
            NAMES Cr_Core libCr_Core
            PATHS "${SONY_CAMERA_SDK_BASE_DIR}"
            PATH_SUFFIXES lib lib/x64 lib/x86 lib/Release lib/Debug
        )
    endif()
else()
    # Unix/Linux/macOS: Original behavior
    find_library(CR_CORE_LIB Cr_Core PATHS ${SONY_CAMERA_SDK_LIB_DIR})
endif()

if(CR_CORE_LIB)
    target_link_libraries(eyeful PUBLIC ${CR_CORE_LIB})
    message(STATUS "Found Sony Camera SDK library: ${CR_CORE_LIB}")
else()
    message(WARNING "Sony Camera SDK library not found in ${SONY_CAMERA_SDK_LIB_DIR}. Please install it according to the README instructions.")
endif()

# Post-build step to copy CrAdapter and DLLs from home directory to build directory
if(WIN32)
    # Windows: Copy CrAdapter directory and DLLs to build directory
    set(CRSDK_ADAPTER_SOURCE "${SONY_CAMERA_SDK_BASE_DIR}/CrAdapter")
    set(CRSDK_ADAPTER_DEST "${CMAKE_BINARY_DIR}/CrAdapter")

    # Check if source directory exists
    if(EXISTS "${CRSDK_ADAPTER_SOURCE}")
        # Copy CrAdapter directory to build output
        add_custom_command(
            TARGET eyeful
            POST_BUILD
            COMMAND ${CMAKE_COMMAND} -E echo "Copying CrAdapter from ${CRSDK_ADAPTER_SOURCE} to ${CRSDK_ADAPTER_DEST}"
            COMMAND ${CMAKE_COMMAND} -E copy_directory "${CRSDK_ADAPTER_SOURCE}" "${CRSDK_ADAPTER_DEST}"
            COMMENT "Copying Sony Camera SDK CrAdapter to build directory"
        )

        # Copy CrAdapter directory to each executable's directory AND copy main SDK DLLs
        set(EXECUTABLE_TARGETS transfer sd_format eyeful_test shutter_test)

        foreach(TARGET_NAME ${EXECUTABLE_TARGETS})
            # Copy CrAdapter directory
            add_custom_command(
                TARGET ${TARGET_NAME}
                POST_BUILD
                COMMAND ${CMAKE_COMMAND} -E copy_directory "${CRSDK_ADAPTER_SOURCE}" "$<TARGET_FILE_DIR:${TARGET_NAME}>/CrAdapter"
                COMMENT "Copying CrAdapter directory to ${TARGET_NAME} executable directory"
            )

            # Copy main SDK DLLs directly to executable directory (same directory as executable)
            add_custom_command(
                TARGET ${TARGET_NAME}
                POST_BUILD
                COMMAND ${CMAKE_COMMAND} -E copy_if_different "${SONY_CAMERA_SDK_LIB_DIR}/Cr_Core.dll" "$<TARGET_FILE_DIR:${TARGET_NAME}>/"
                COMMAND ${CMAKE_COMMAND} -E copy_if_different "${SONY_CAMERA_SDK_LIB_DIR}/monitor_protocol.dll" "$<TARGET_FILE_DIR:${TARGET_NAME}>/"
                COMMAND ${CMAKE_COMMAND} -E copy_if_different "${SONY_CAMERA_SDK_LIB_DIR}/monitor_protocol_pf.dll" "$<TARGET_FILE_DIR:${TARGET_NAME}>/"
                COMMENT "Copying Sony SDK DLLs to ${TARGET_NAME} executable directory"
            )
        endforeach()

        message(STATUS "Post-build step configured to copy CrAdapter and SDK DLLs to executable directories")
    else()
        message(WARNING "CrAdapter source directory not found at ${CRSDK_ADAPTER_SOURCE}. Skipping copy step.")
    endif()

elseif(UNIX)
    # Unix/Linux/macOS: Original logic
    # Get the home directory
    execute_process(
        COMMAND sh -c "echo $HOME"
        OUTPUT_VARIABLE HOME_DIR
        OUTPUT_STRIP_TRAILING_WHITESPACE
    )

    set(CRSDK_ADAPTER_SOURCE "${HOME_DIR}/CRSDK/CrAdapter")

    # macOS needs a special path for the shared libraries
    if(APPLE)
        set(CRSDK_ADAPTER_DEST "${CMAKE_BINARY_DIR}/Contents/Frameworks/CrAdapter")
    else()
        set(CRSDK_ADAPTER_DEST "${CMAKE_BINARY_DIR}/CrAdapter")
    endif()

    # Check if source directory exists
    if(EXISTS "${CRSDK_ADAPTER_SOURCE}")
        # Copying the Sony SDK shared libraries to the build
        add_custom_command(
            TARGET eyeful
            POST_BUILD
            COMMAND ${CMAKE_COMMAND} -E echo "Copying CrAdapter from ${CRSDK_ADAPTER_SOURCE} to ${CRSDK_ADAPTER_DEST}"
            COMMAND ${CMAKE_COMMAND} -E copy_directory "${CRSDK_ADAPTER_SOURCE}" "${CRSDK_ADAPTER_DEST}"
            COMMENT "Copying Sony Camera SDK CrAdapter to build directory"
        )

        message(STATUS "Post-build step configured to copy CrAdapter from ${CRSDK_ADAPTER_SOURCE} to ${CRSDK_ADAPTER_DEST}")
    else()
        message(WARNING "CrAdapter source directory not found at ${CRSDK_ADAPTER_SOURCE}. Skipping copy step.")
    endif()
endif()

# Windows-specific installation rules
if(WIN32)
    # Install executables to standard Windows location
    install(TARGETS transfer sd_format eyeful_test shutter_test
        RUNTIME DESTINATION bin
        LIBRARY DESTINATION lib
        ARCHIVE DESTINATION lib
    )

    # Install the eyeful library
    install(TARGETS eyeful logging
        RUNTIME DESTINATION bin
        LIBRARY DESTINATION lib
        ARCHIVE DESTINATION lib
    )

    # Install headers to standard location (Program Files)
    install(DIRECTORY eyeful/
        DESTINATION include/eyeful
        FILES_MATCHING PATTERN "*.h"
    )

    install(DIRECTORY logging/
        DESTINATION include/logging
        FILES_MATCHING PATTERN "*.h"
    )

    # Install Sony SDK headers if they exist in the CRSDK directory
    if(EXISTS "${SONY_CAMERA_SDK_INCLUDE_DIR}")
        install(DIRECTORY "${SONY_CAMERA_SDK_INCLUDE_DIR}/"
            DESTINATION include/CRSDK
            FILES_MATCHING PATTERN "*.h" PATTERN "*.hpp"
        )
    endif()

    # Install CrAdapter directory
    if(EXISTS "${SONY_CAMERA_SDK_BASE_DIR}/CrAdapter")
        install(DIRECTORY "${SONY_CAMERA_SDK_BASE_DIR}/CrAdapter/"
            DESTINATION bin/CrAdapter
        )
    endif()

    message(STATUS "Windows install targets configured. Use 'cmake --build . --target install' to install.")
    message(STATUS "Default install prefix: ${CMAKE_INSTALL_PREFIX}")
    message(STATUS "To change install location, use: -DCMAKE_INSTALL_PREFIX=C:/path/to/install")
endif()

message(STATUS "  Project version: ${PROJECT_VERSION}")
message(STATUS "  C++ Standard: ${CMAKE_CXX_STANDARD}")
message(STATUS "  Sony Camera SDK lib dir: ${SONY_CAMERA_SDK_LIB_DIR}")

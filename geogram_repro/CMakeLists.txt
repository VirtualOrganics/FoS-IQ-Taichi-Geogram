cmake_minimum_required(VERSION 3.15)
project(geogram_repro CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Path to our vendored Geogram build
set(GEOGRAM_ROOT ${CMAKE_CURRENT_SOURCE_DIR}/../geom_bridge/geogram_vendor)
set(GEOGRAM_BUILD_DIR ${GEOGRAM_ROOT}/build/Darwin-clang-dynamic-Release)

# Create executable
add_executable(repro_periodic_laguerre repro_periodic_laguerre.cpp)

# Link to Geogram
target_link_libraries(repro_periodic_laguerre PRIVATE
    ${GEOGRAM_BUILD_DIR}/lib/libgeogram.dylib
)

# Include Geogram headers
target_include_directories(repro_periodic_laguerre PRIVATE
    ${GEOGRAM_ROOT}/src/lib
)

# Default to Debug for assertions (can override with -DCMAKE_BUILD_TYPE=Release)
if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Debug CACHE STRING "Build type" FORCE)
endif()

message(STATUS "Build type: ${CMAKE_BUILD_TYPE}")
message(STATUS "Geogram root: ${GEOGRAM_ROOT}")
message(STATUS "Geogram build: ${GEOGRAM_BUILD_DIR}")

# Optional: Enable sanitizers via command-line flags
# Example: cmake -DCMAKE_CXX_FLAGS="-fsanitize=address,undefined" ..


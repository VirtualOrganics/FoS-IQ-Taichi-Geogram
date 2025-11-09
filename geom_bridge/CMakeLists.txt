# CMakeLists.txt for geom_bridge
# Builds pybind11 extension linking to Geogram

cmake_minimum_required(VERSION 3.15)
project(geom_bridge)

# Release mode: -O3 -DNDEBUG for performance + stability
if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE RelWithDebInfo CACHE STRING "Build type" FORCE)
endif()

# C++11 required (Section 0)
set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find Python and pybind11
find_package(Python COMPONENTS Interpreter Development REQUIRED)
find_package(pybind11 CONFIG REQUIRED)

# Path to pre-built Geogram
set(GEOGRAM_ROOT ${CMAKE_CURRENT_SOURCE_DIR}/geogram_vendor)
set(GEOGRAM_BUILD_DIR ${GEOGRAM_ROOT}/build/Darwin-clang-dynamic-Release)

# Create Python extension module
pybind11_add_module(geom_bridge bridge.cpp)

# Link to pre-built Geogram libraries
target_link_libraries(geom_bridge PRIVATE
    ${GEOGRAM_BUILD_DIR}/lib/libgeogram.dylib
)

# Include Geogram headers
target_include_directories(geom_bridge PRIVATE
    ${GEOGRAM_ROOT}/src/lib
)

# Compile options: Release optimization + NDEBUG
target_compile_options(geom_bridge PRIVATE -O3 -DNDEBUG)
target_compile_definitions(geom_bridge PRIVATE NDEBUG)


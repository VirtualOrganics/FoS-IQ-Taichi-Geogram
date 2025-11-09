#!/bin/bash
# build_geom_bridge.sh — Build script for geom_bridge extension
# From Blueprint Section 12

set -e  # Exit on error

echo "=========================================="
echo "Building geom_bridge (Geogram + pybind11)"
echo "=========================================="

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Detect Python from active venv or system
if [ -n "$VIRTUAL_ENV" ]; then
    PYTHON_EXECUTABLE="$VIRTUAL_ENV/bin/python"
    echo "Using venv Python: $PYTHON_EXECUTABLE"
else
    PYTHON_EXECUTABLE=$(which python3)
    echo "Using system Python: $PYTHON_EXECUTABLE"
fi

# Get pybind11 cmake dir
PYBIND11_CMAKE=$($PYTHON_EXECUTABLE -c "import pybind11; print(pybind11.get_cmake_dir())")
echo "pybind11 CMake dir: $PYBIND11_CMAKE"

# Create build directory
BUILD_DIR="build"
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

# Configure
echo ""
echo "Configuring with CMake..."
cmake .. \
    -DCMAKE_BUILD_TYPE=Release \
    -DPython_EXECUTABLE="$PYTHON_EXECUTABLE" \
    -Dpybind11_DIR="$PYBIND11_CMAKE"

# Build
echo ""
echo "Building..."
cmake --build . --config Release -j$(sysctl -n hw.ncpu)

# Copy extension to parent directory for easy import
echo ""
echo "Copying extension module..."
cp geom_bridge*.so ..

echo ""
echo "=========================================="
echo "Build complete!"
echo "Extension: $(ls -1 ../geom_bridge*.so)"
echo "=========================================="


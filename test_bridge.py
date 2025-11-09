#!/usr/bin/env python
"""
Test script for geom_bridge
Tests the API from Blueprint Section 13
"""

import sys
import numpy as np

# Add geom_bridge to path
sys.path.insert(0, '/Users/chimel/Desktop/Cursor_FoS-Custom-Grid/FoS-IQ-Taichi-Geogram/geom_bridge')

try:
    from geom_bridge import compute_power_cells
    print("✓ geom_bridge imported successfully!")
except ImportError as e:
    print(f"✗ Failed to import geom_bridge: {e}")
    sys.exit(1)

# Test with small dataset (N=100)
print("\n" + "="*50)
print("Test: N=100 particles in periodic cube")
print("="*50)

N = 100
np.random.seed(42)

# Random points in [0,1]^3
points_norm = np.random.rand(N, 3).astype(np.float64)

# Random weights (r^2), typical foam radii ~0.01-0.05
radii = 0.02 + 0.01 * np.random.rand(N)
weights = (radii ** 2).astype(np.float64)

print(f"\nInput:")
print(f"  Points shape: {points_norm.shape}")
print(f"  Weights shape: {weights.shape}")
print(f"  Points range: [{points_norm.min():.3f}, {points_norm.max():.3f}]")
print(f"  Weights range: [{weights.min():.6f}, {weights.max():.6f}]")

# Call the bridge
print("\nCalling compute_power_cells()...")
result = compute_power_cells(points_norm, weights, periodic=True)

print(f"\nResult:")
print(f"  Volume: {len(result.volume)} values")
print(f"  Area: {len(result.area)} values")
print(f"  FSC: {len(result.fsc)} values")
print(f"  Flags: {len(result.flags)} values")

# Convert to numpy for analysis
V = np.array(result.volume)
S = np.array(result.area)
FSC = np.array(result.fsc)
flags = np.array(result.flags)

print(f"\nMetrics:")
print(f"  Volume - min: {V.min():.6f}, mean: {V.mean():.6f}, max: {V.max():.6f}")
print(f"  Area - min: {S.min():.6f}, mean: {S.mean():.6f}, max: {S.max():.6f}")
print(f"  FSC - min: {FSC.min()}, mean: {FSC.mean():.1f}, max: {FSC.max()}")
print(f"  Flags - non-zero: {np.count_nonzero(flags)}/{N}")

# Compute IQ (Blueprint Section 6)
IQ = 36 * np.pi * (V ** 2) / (S ** 3)
print(f"\nIQ (isoperimetric quotient):")
print(f"  min: {IQ.min():.4f}")
print(f"  mean: {IQ.mean():.4f}")
print(f"  max: {IQ.max():.4f}")

# Check total volume (should be ~1.0 for unit cube)
total_volume = V.sum()
print(f"\nTotal volume: {total_volume:.6f} (expect ~1.0 for unit cube)")

print("\n" + "="*50)
print("✓ Test completed successfully!")
print("="*50)


#!/usr/bin/env python
"""Test timing for N=5k"""

import sys
import time
import numpy as np

sys.path.insert(0, '/Users/chimel/Desktop/Cursor_FoS-Custom-Grid/FoS-IQ-Taichi-Geogram/geom_bridge')

from geom_bridge import compute_power_cells

print("\n" + "="*60)
print("Testing N=5000")
print("="*60)

np.random.seed(42)
N = 5000
points_norm = np.random.rand(N, 3).astype(np.float64)
radii = 0.01 + 0.005 * np.random.rand(N)
weights = (radii ** 2).astype(np.float64)

print(f"Running compute_power_cells...")
t0 = time.time()
result = compute_power_cells(points_norm, weights, periodic=True)
t_geom = (time.time() - t0) * 1000  # ms

V = np.array(result.volume)
S = np.array(result.area)
FSC = np.array(result.fsc)
flags = np.array(result.flags)
IQ = 36 * np.pi * (V ** 2) / (S ** 3)

print(f"\n✅ Results:")
print(f"  t_geom = {t_geom:.2f} ms")
print(f"  Total volume: {V.sum():.6f}")
print(f"  IQ range: [{IQ.min():.4f}, {IQ.max():.4f}], mean: {IQ.mean():.4f}")
print(f"  Degenerate: {np.count_nonzero(flags)}/{N}")
print("="*60)


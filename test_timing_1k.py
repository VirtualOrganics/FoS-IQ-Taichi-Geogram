#!/usr/bin/env python
"""Test timing for N=1k"""

import sys
import time
import numpy as np

sys.path.insert(0, '/Users/chimel/Desktop/Cursor_FoS-Custom-Grid/FoS-IQ-Taichi-Geogram/geom_bridge')

from geom_bridge import compute_power_cells

print("\n" + "="*60)
print("Testing N=1000 (Blueprint Day 1-2 requirement)")
print("="*60)

np.random.seed(42)
N = 1000
points_norm = np.random.rand(N, 3).astype(np.float64)
radii = 0.02 + 0.01 * np.random.rand(N)
weights = (radii ** 2).astype(np.float64)

# Warmup
_ = compute_power_cells(points_norm[:10], weights[:10], periodic=True)

# Timing
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
print(f"  Volume range: [{V.min():.6f}, {V.max():.6f}]")
print(f"  IQ range: [{IQ.min():.4f}, {IQ.max():.4f}], mean: {IQ.mean():.4f}")
print(f"  FSC range: [{FSC.min()}, {FSC.max()}], mean: {FSC.mean():.1f}")
print(f"  Degenerate: {np.count_nonzero(flags)}/{N}")

print(f"\n📊 Blueprint Section 10 target: t_geom ≈ 20-60 ms for N=10k")
print(f"   Our N=1k: {t_geom:.2f} ms → extrapolated N=10k: ~{t_geom*10:.0f} ms")
print("="*60)


#!/usr/bin/env python
"""
Test timing for N=1k, 10k (Blueprint Day 1-2 requirement)
"""

import sys
import time
import numpy as np

sys.path.insert(0, '/Users/chimel/Desktop/Cursor_FoS-Custom-Grid/FoS-IQ-Taichi-Geogram/geom_bridge')

from geom_bridge import compute_power_cells

def test_timing(N):
    """Test compute_power_cells timing for given N"""
    print(f"\n{'='*60}")
    print(f"Testing N={N}")
    print('='*60)
    
    np.random.seed(42)
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
    IQ = 36 * np.pi * (V ** 2) / (S ** 3)
    
    print(f"t_geom = {t_geom:.2f} ms")
    print(f"IQ range: [{IQ.min():.4f}, {IQ.max():.4f}], mean: {IQ.mean():.4f}")
    print(f"Total volume: {V.sum():.6f}")
    
    return t_geom

# Test as per Blueprint Day 1-2
print("\n" + "="*60)
print("Blueprint Day 1-2: Log t_geom on N=1k/10k")
print("="*60)

t_1k = test_timing(1000)
t_10k = test_timing(10000)

print(f"\n{'='*60}")
print("Summary:")
print(f"  N=1k:  t_geom = {t_1k:.2f} ms")
print(f"  N=10k: t_geom = {t_10k:.2f} ms")
print(f"  Scaling: {t_10k/t_1k:.2f}x")
print("="*60)

# Blueprint target: N=10k in 20-60 ms (with real Geogram)
print("\nNote: Current placeholder. Real Geogram implementation expected:")
print("  N=10k: 20-60 ms (Section 10)")


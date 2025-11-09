#!/usr/bin/env python
"""Direct test of geom_bridge with N=100 to isolate the crash"""

import sys
sys.path.insert(0, 'geom_bridge')

import numpy as np
from geom_bridge import compute_power_cells

print("Testing N=100 with jittered grid...")

# Jittered grid like in the main code
def jittered_grid_positions01(n, seed=0):
    np.random.seed(seed)
    m = int(round(n ** (1/3)))
    m = max(4, m)
    gx = np.linspace(0.05, 0.95, m)
    pts = np.stack(np.meshgrid(gx, gx, gx, indexing='ij'), axis=-1).reshape(-1,3)
    if len(pts) < n:
        k = n - len(pts)
        jitter = (np.random.rand(k,3) - 0.5) * (1.0/m) * 0.2
        pts = np.concatenate([pts, pts[:k] + jitter], axis=0)
    pts = pts[:n]
    pts += (np.random.rand(n,3) - 0.5) * (1.0/m) * 0.1
    return np.mod(pts, 1.0)

N = 100
pts = jittered_grid_positions01(N).astype(np.float64)
w = np.full(N, 0.02**2, dtype=np.float64)  # r=0.02 → w=r²

print(f"pts shape: {pts.shape}, dtype: {pts.dtype}")
print(f"w shape: {w.shape}, dtype: {w.dtype}")
print(f"pts range: [{pts.min():.6f}, {pts.max():.6f}]")
print(f"w range: [{w.min():.6f}, {w.max():.6f}]")

# Ensure contiguous
pts = np.ascontiguousarray(pts)
w = np.ascontiguousarray(w)

print("\nCalling compute_power_cells...")
try:
    result = compute_power_cells(pts, w)
    print(f"✅ SUCCESS!")
    print(f"  V sum: {np.sum(result.volume):.6f}")
    print(f"  S sum: {np.sum(result.area):.3f}")
    print(f"  Flags nonzero: {np.count_nonzero(result.flags)}")
except Exception as e:
    print(f"❌ EXCEPTION: {e}")
    import traceback
    traceback.print_exc()


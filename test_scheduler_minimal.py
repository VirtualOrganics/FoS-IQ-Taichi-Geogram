#!/usr/bin/env python
"""Minimal test mimicking exact scheduler data flow"""

import sys
sys.path.insert(0, 'src')
sys.path.insert(0, 'geom_bridge')

import numpy as np
from sim_stub import TaichiSimStub
from geom_bridge import compute_power_cells

print("="*70)
print("Minimal Scheduler Data Flow Test")
print("="*70)

# 1. Create sim
sim = TaichiSimStub(N=100)

# 2. Get positions and radii (like scheduler does)
print("\n1. Getting data from sim...")
P = sim.get_positions01()  # (N, 3)
r = sim.get_radii()         # (N,)
W = r * r                   # weights = r²

print(f"P shape: {P.shape}, dtype: {P.dtype}, contiguous: {P.flags['C_CONTIGUOUS']}")
print(f"W shape: {W.shape}, dtype: {W.dtype}, contiguous: {W.flags['C_CONTIGUOUS']}")
print(f"P range: [{P.min():.6f}, {P.max():.6f}]")
print(f"W range: [{W.min():.6f}, {W.max():.6f}]")

# 3. Make contiguous copies (like geom_worker does)
print("\n2. Making contiguous copies...")
P_copy = np.ascontiguousarray(P, dtype=np.float64)
W_copy = np.ascontiguousarray(W, dtype=np.float64)

print(f"P_copy contiguous: {P_copy.flags['C_CONTIGUOUS']}")
print(f"W_copy contiguous: {W_copy.flags['C_CONTIGUOUS']}")

# 4. Call Geogram (like geom_worker does)
print("\n3. Calling compute_power_cells...")
try:
    result = compute_power_cells(P_copy, W_copy)
    print(f"✅ SUCCESS!")
    print(f"  V sum: {np.sum(result.volume):.6f}")
    print(f"  S sum: {np.sum(result.area):.3f}")
    print(f"  FSC mean: {np.mean(result.fsc):.1f}")
    print(f"  Flags nonzero: {np.count_nonzero(result.flags)}")
except Exception as e:
    print(f"❌ EXCEPTION: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "="*70)
print("Test PASSED - ready to try full scheduler!")
print("="*70)


#!/usr/bin/env python
"""Test batching at N=1000 to isolate crash"""

import sys
sys.path.insert(0, 'src')
sys.path.insert(0, 'geom_bridge')

import numpy as np
from sim_stub import TaichiSimStub
from geom_worker_sync import GeomWorkerSync

print("="*70)
print("Batching Test at N=1000")
print("="*70)

# 1. Create sim with N=1000
sim = TaichiSimStub(N=1000)

# 2. Get data
print("\n1. Getting data...")
P = sim.get_positions01()  # (1000, 3)
r = sim.get_radii()        # (1000,)
W = r * r

print(f"P shape: {P.shape}")
print(f"W shape: {W.shape}")
print(f"P range: [{P.min():.6f}, {P.max():.6f}]")
print(f"W range: [{W.min():.6f}, {W.max():.6f}]")

# 3. Call batched compute (like geom_worker does)
print("\n2. Calling _compute_batched with max_chunk=512...")
worker = GeomWorkerSync(max_chunk=512)

try:
    V, S, FSC, flags = worker._compute_batched(P, W, max_chunk=512)
    print(f"✅ SUCCESS!")
    print(f"  V sum: {np.sum(V):.6f}")
    print(f"  S sum: {np.sum(S):.3f}")
    print(f"  FSC mean: {np.mean(FSC):.1f}")
    print(f"  Flags nonzero: {np.count_nonzero(flags)}")
except Exception as e:
    print(f"❌ EXCEPTION: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "="*70)
print("Batching test PASSED!")
print("="*70)


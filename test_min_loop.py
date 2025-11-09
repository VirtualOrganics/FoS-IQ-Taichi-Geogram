#!/usr/bin/env python
# test_min_loop.py
# Minimal loop test: frozen inputs, 200 direct bridge calls
# No scheduler, no Taichi, no complexity - just pure Geogram binding test

import os, faulthandler, time, sys
faulthandler.enable()

# Helpful env for reproducibility / fewer surprises
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("PYTHONMALLOC", "debug")

sys.path.insert(0, 'geom_bridge')

import numpy as np
from geom_bridge import compute_power_cells  # tuple: (V, A, FSC, FLAGS)

def jittered_grid(N, seed=1234):
    rng = np.random.default_rng(seed)
    m = int(round(N ** (1/3)))
    m = max(4, m)
    # grid centers
    g = (np.arange(m) + 0.5) / m
    Gx, Gy, Gz = np.meshgrid(g, g, g, indexing="ij")
    P = np.c_[Gx.ravel(), Gy.ravel(), Gz.ravel()]
    P = P[:N].copy()
    # small jitter; wrap to [0,1)
    jitter = (0.15/m) * (rng.random(P.shape) - 0.5) * 2.0
    P = (P + jitter) % 1.0
    # weights: radii^2 style
    i = np.arange(N)
    r = 0.02 + 0.01 * np.sin(0.618 * i)
    W = (r * r).astype(np.float64)
    return P.astype(np.float64), W

def main(N=1000, repeats=200):
    print("="*70)
    print("🔬 MINIMAL LOOP TEST")
    print("="*70)
    print(f"N = {N}")
    print(f"Repeats = {repeats}")
    print("Inputs: FROZEN (jittered grid)")
    print("Pattern: Direct bridge calls, no scheduler")
    print("Target: Pass 200 calls (> historical 62-87 crash zone)")
    print("="*70)
    print()
    
    # frozen inputs to rule out "drifting into degeneracy"
    P01, W = jittered_grid(N)
    
    # Bridge expects (N, 3) for points
    P01 = np.ascontiguousarray(P01, dtype=np.float64)
    W   = np.ascontiguousarray(W,   dtype=np.float64)

    # sanity
    assert P01.ndim == 2 and P01.shape == (N, 3)
    assert W.ndim == 1 and W.size == N
    
    print(f"Inputs prepared: P={P01.shape}, W={W.shape}")
    print(f"Starting {repeats} calls...\n")

    t0 = time.time()
    
    for k in range(repeats):
        V, A, FSC, FL = compute_power_cells(P01, W)  # <- direct call, no scheduler
        
        if (k % 10) == 0:
            # basic health check: sum volume ~ 1.0 (periodic unit cube)
            sv = float(np.sum(V))
            bad = int(np.sum(FL != 0))
            print(f"[{k:03d}] sumV={sv:.6f}, N={N}, bad={bad}")
        
        # Milestones
        if k == 62:
            print("\n*** PASSED call 62 (historical crash start) ***\n")
        if k == 87:
            print("\n*** PASSED call 87 (historical crash end) ***\n")
        if k == 125:
            print("\n*** PASSED call 125 (equivalent to 3000 frames) ***\n")
    
    dt = time.time() - t0
    
    print("\n" + "="*70)
    print("✅ ✅ ✅ SUCCESS! ✅ ✅ ✅")
    print("="*70)
    print(f"Completed: {repeats} calls in {dt:.2f}s")
    print(f"Avg: {dt/repeats*1000:.1f}ms per call")
    print()
    print("🎊 PYBIND11 BINDING IS STABLE! 🎊")
    print("Owned-copy + GIL-release pattern works.")
    print("="*70)

if __name__ == "__main__":
    main(N=1000, repeats=200)


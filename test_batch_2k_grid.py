#!/usr/bin/env python
"""Test batching with GRID positions (no random overlaps)"""

import faulthandler, sys, os, numpy as np

faulthandler.enable()
os.environ.setdefault("OMP_NUM_THREADS", "1")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from geom_worker import GeomWorker


def run():
    print("\nTest: N=2000 on REGULAR GRID (batched 2x1000)")
    
    # Create regular grid in [0,1]³
    N = 2000
    n_side = int(np.ceil(N**(1/3)))
    print(f"Grid: {n_side}³ = {n_side**3} points")
    
    x = np.linspace(0.05, 0.95, n_side)
    xx, yy, zz = np.meshgrid(x, x, x)
    P = np.stack([xx.ravel(), yy.ravel(), zz.ravel()], axis=1)[:N]  # Nx3
    
    W = np.full(N, 0.02**2)  # uniform weights
    
    print(f"Positions shape: {P.shape}")
    print(f"Weights shape: {W.shape}")
    print(f"P range: [{P.min():.3f}, {P.max():.3f}]")
    
    # Create worker with max_chunk=1000
    worker = GeomWorker(max_chunk=1000)
    print(f"Worker created, sending request...")
    
    ok = worker.try_request(P, W)
    if not ok:
        print("Worker busy!")
        return
    
    print("Waiting for result...")
    import time
    for i in range(100):
        result = worker.try_result()
        if result:
            V, S, FSC, flags, t_ms = result
            print(f"\n✅ SUCCESS!")
            print(f"  Got {len(V)} results in {t_ms:.1f}ms")
            print(f"  V: μ={V.mean():.6f}, range=[{V.min():.6f}, {V.max():.6f}]")
            print(f"  Degenerate cells: {(flags != 0).sum()}")
            return
        time.sleep(0.1)
    
    print("Timeout!")


if __name__ == "__main__":
    run()


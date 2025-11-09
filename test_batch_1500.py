#!/usr/bin/env python
"""Test batching at N=1500 (should work via batching)"""

import faulthandler, sys, os, numpy as np

faulthandler.enable()
os.environ.setdefault("OMP_NUM_THREADS", "1")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from sim_stub import TaichiSimStub
from scheduler import FoamScheduler
from geom_worker import GeomWorker


def run():
    print("\nTest: N=1500 with max_chunk=1000 (batching)")
    
    N = 1500
    sim = TaichiSimStub(N=N)
    
    # Create worker with small chunk size
    worker = GeomWorker(max_chunk=1000)
    print(f"Worker created with max_chunk=1000")
    
    # Get data
    P = sim.get_positions01()
    r = sim.get_radii()
    W = r*r
    
    print(f"Positions shape: {P.shape}")
    print(f"Weights shape: {W.shape}")
    print(f"Sending to worker...")
    
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
            print(f"  Got {len(V)} results")
            print(f"  t_geom: {t_ms:.1f}ms")
            print(f"  V range: [{V.min():.6f}, {V.max():.6f}]")
            print(f"  S range: [{S.min():.6f}, {S.max():.6f}]")
            return
        time.sleep(0.1)
    
    print("Timeout!")


if __name__ == "__main__":
    print(f"Python: {sys.executable}")
    run()


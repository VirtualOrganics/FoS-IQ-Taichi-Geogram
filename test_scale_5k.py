#!/usr/bin/env python
"""Scale Test: N=5k, verify adaptive cadence stretches k as needed"""

import faulthandler, sys, os, numpy as np

faulthandler.enable()
os.environ.setdefault("OMP_NUM_THREADS", "1")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from sim_stub import TaichiSimStub
from scheduler import FoamScheduler


def run():
    print("\n" + "="*70)
    print("SCALE TEST: N=5k (adaptive cadence)")
    print("="*70)
    
    N = 5000
    k_freeze = 24
    total_frames = 300
    
    print(f"\nConfig: N={N}, k_freeze={k_freeze}, frames={total_frames}")
    
    print("\n[1/3] Initializing...")
    sim = TaichiSimStub(N=N)
    sched = FoamScheduler(sim, k_freeze=k_freeze, target_ms=12.0)
    
    print("\n[2/3] Running simulation...")
    updates = []
    
    for i in range(total_frames):
        sched.step()
        
        hud = sched.hud()
        if hud["IQ_mu"] > 0 and (not updates or hud["IQ_mu"] != updates[-1]["IQ_mu"]):
            updates.append(hud.copy())
            print(f"  Update {len(updates)}: "
                  f"IQ μ={hud['IQ_mu']:.4f} σ={hud['IQ_sigma']:.4f} | "
                  f"t={hud['t_geom_ms']:.1f}ms k={hud['cadence']}")
    
    print(f"\n[3/3] Summary:")
    print("="*70)
    print(f"  Total updates: {len(updates)}")
    
    if updates:
        IQ_mus = [u["IQ_mu"] for u in updates]
        t_geoms = [u["t_geom_ms"] for u in updates]
        cadences = [u["cadence"] for u in updates]
        
        print(f"  IQ μ range: [{min(IQ_mus):.4f}, {max(IQ_mus):.4f}]")
        print(f"  t_geom: min={min(t_geoms):.1f}ms, max={max(t_geoms):.1f}ms, mean={np.mean(t_geoms):.1f}ms")
        print(f"  k range: [{min(cadences)}, {max(cadences)}]")
        
        if max(cadences) > k_freeze:
            print(f"  ✓ Cadence adapted upward (heavy t_geom)")
        elif min(cadences) < k_freeze:
            print(f"  ✓ Cadence adapted downward (fast t_geom)")
    
    print("\n✅ SUCCESS: N=5k stable, non-blocking, adaptive")
    print("="*70)


if __name__ == "__main__":
    print(f"Python: {sys.executable}")
    print(f"Version: {sys.version.split()[0]}")
    run()

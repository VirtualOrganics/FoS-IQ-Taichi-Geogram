#!/usr/bin/env python
"""Gradual test: N=1000, slowly increasing frame counts"""

import sys, time
sys.path.insert(0, 'src')

from sim_stub import TaichiSimStub
from scheduler import FoamScheduler

def test_frames(n_frames):
    """Test for exactly n_frames"""
    print(f"\n{'='*50}")
    print(f"Testing {n_frames} frames...")
    print('='*50)
    
    sim = TaichiSimStub(N=1000)
    sched = FoamScheduler(sim, k_freeze=24)
    
    t0 = time.time()
    
    for i in range(n_frames):
        sched.step()
        
        if (i+1) % 100 == 0:
            hud = sched.hud()
            print(f"  {i+1:4d} | Geom: {sched.results_seen:3d} | "
                  f"IQ={hud['IQ_mu']:.3f}±{hud['IQ_sigma']:.3f}")
    
    elapsed = time.time() - t0
    print(f"✅ PASSED {n_frames} frames ({sched.results_seen} Geom calls) in {elapsed:.1f}s")
    return True

# Gradually increase
for target in [100, 200, 500, 1000, 1500, 2000, 2500, 3000]:
    try:
        test_frames(target)
    except Exception as e:
        print(f"\n❌ CRASHED at target={target}")
        print(f"Exception: {e}")
        import traceback
        traceback.print_exc()
        break

print("\n" + "="*50)
print("Test complete!")


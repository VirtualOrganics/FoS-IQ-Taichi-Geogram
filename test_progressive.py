#!/usr/bin/env python
"""Progressive test: start at 100 frames, increase by 500 until crash"""

import sys, time
sys.path.insert(0, 'src')

from sim_stub import TaichiSimStub
from scheduler import FoamScheduler

print("="*70)
print("PROGRESSIVE STABILITY TEST")
print("="*70)

sim = TaichiSimStub(N=1000)
sched = FoamScheduler(sim, k_freeze=24)

# Start at 100, go to 2500 in steps of 500
for target in [100, 500, 1000, 1500, 2000, 2500]:
    print(f"\nTesting {target} frames...")
    t0 = time.time()
    
    try:
        while sched.frame < target:
            sched.step()
            
            if sched.frame % 100 == 0 and sched.frame > 0:
                hud = sched.hud()
                print(f"  Frame {sched.frame:4d} | Geom: {sched.results_seen:3d} | "
                      f"IQ={hud['IQ_mu']:.3f}±{hud['IQ_sigma']:.3f}")
        
        elapsed = time.time() - t0
        print(f"✅ PASSED {target} frames in {elapsed:.1f}s")
        
    except KeyboardInterrupt:
        print(f"\n⚠️  Interrupted at frame {sched.frame}")
        break
    except Exception as e:
        print(f"\n❌ CRASHED at frame {sched.frame} (Geom call ~{sched.results_seen})")
        print(f"Exception: {e}")
        import traceback
        traceback.print_exc()
        break

print(f"\n Final: Survived to frame {sched.frame}, {sched.results_seen} Geogram calls")


#!/usr/bin/env python
"""REAL marathon test: N=1000 for 3000+ frames
Historical crash: ~1500-2100 frames (62-87 Geogram calls)
Target: Survive 3000 frames (~125 Geogram calls)
"""

import sys, time
sys.path.insert(0, 'src')

from sim_stub import TaichiSimStub
from scheduler import FoamScheduler

print("="*70)
print("🏃 REAL MARATHON TEST")
print("="*70)
print("N = 1000")
print("k_freeze = 24 (adaptive)")
print("Target: 3000 frames (~125 Geogram calls)")
print("Historical crash zone: 1500-2100 frames")
print("Fix: GEO::SmartPointer<PeriodicDelaunay3d>")
print("="*70)
print()

sim = TaichiSimStub(N=1000)
sched = FoamScheduler(sim, k_freeze=24)

t0 = time.time()
crash_zone_passed = False

try:
    for i in range(3000):
        sched.step()
        
        if i % 100 == 0 and i > 0:
            hud = sched.hud()
            elapsed = time.time() - t0
            fps = i / elapsed
            geom_calls = sched.results_seen
            print(f"Frame {i:4d} | Geom calls: {geom_calls:3d} | "
                  f"IQ μ={hud['IQ_mu']:.3f} σ={hud['IQ_sigma']:.3f} | "
                  f"k={hud['cadence']:2d} | FPS={fps:.1f}")
        
        # Historical crash zone
        if i == 1500 and not crash_zone_passed:
            print("\n" + "⚠️ "*35)
            print("⚠️  ENTERING HISTORICAL CRASH ZONE (1500-2100)")
            print("⚠️ "*35 + "\n")
        
        if i == 2100:
            crash_zone_passed = True
            print("\n" + "🎉"*35)
            print("🎉 PASSED HISTORICAL CRASH ZONE!")
            print("🎉"*35 + "\n")
    
    # Success!
    elapsed = time.time() - t0
    geom_calls = sched.results_seen
    
    print("\n" + "="*70)
    print("✅ MARATHON COMPLETED!")
    print("="*70)
    print(f"Frames: 3000")
    print(f"Geogram calls: {geom_calls}")
    print(f"Time: {elapsed:.1f}s")
    print(f"Avg FPS: {3000/elapsed:.1f}")
    print()
    print("🎊 Bruno's SmartPointer fix CONFIRMED WORKING! 🎊")
    print("="*70)
    
except Exception as e:
    frame = sched.frame
    geom_calls = sched.results_seen
    print(f"\n❌ CRASH at frame {frame} (Geom call ~{geom_calls})")
    print(f"Exception: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)


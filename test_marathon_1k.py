#!/usr/bin/env python
"""Marathon test: N=1000 for 3000 frames to verify Bruno's fix"""

import sys, time
sys.path.insert(0, 'src')

from sim_stub import TaichiSimStub
from scheduler import FoamScheduler

print("="*70)
print("🏃 MARATHON TEST: N=1000 for 3000 frames")
print("  Previous crash point: ~1500-2100 frames")
print("  Bruno's fix: GEO::SmartPointer<PeriodicDelaunay3d>")
print("="*70)

sim = TaichiSimStub(N=1000)
sched = FoamScheduler(sim, k_freeze=24)

t0 = time.time()

for i in range(3000):
    sched.step()
    
    if i % 100 == 0:
        hud = sched.hud()
        elapsed = time.time() - t0
        fps = (i+1) / elapsed if elapsed > 0 else 0
        print(f"Frame {i:4d}: IQ μ={hud['IQ_mu']:.3f} σ={hud['IQ_sigma']:.3f} | "
              f"k={hud['cadence']:2d} | t_geom={hud.get('t_geom_ms', 0):.1f}ms | FPS={fps:.1f}")
    
    # Milestones
    if i == 1500:
        print("\n" + "🎉"*35)
        print("🎉 PASSED 1500 FRAMES (old crash point)!")
        print("🎉"*35 + "\n")
    if i == 2100:
        print("\n" + "🚀"*35)
        print("🚀 PASSED 2100 FRAMES (maximum old survival)!")
        print("🚀"*35 + "\n")

elapsed = time.time() - t0
print("\n" + "="*70)
print(f"✅ MARATHON COMPLETED!")
print(f"  Frames: 3000")
print(f"  Time: {elapsed:.1f}s")
print(f"  Avg FPS: {3000/elapsed:.1f}")
print(f"  Geom calls: ~{sched.results_seen}")
print("\n🎊 Bruno's SmartPointer fix CONFIRMED! 🎊")
print("="*70)


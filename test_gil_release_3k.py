#!/usr/bin/env python
"""
DEFINITIVE TEST: N=1000 for 3000 frames with GIL-release binding
Historical crash: ~1500 frames (62 Geogram calls)
Target: 3000+ frames (125+ Geogram calls)
"""

import sys, time
sys.path.insert(0, 'src')

from sim_stub import TaichiSimStub
from scheduler import FoamScheduler

print("="*70)
print("🔬 DEFINITIVE TEST: GIL-Release + Owned-Copy Binding")
print("="*70)
print("N = 1000")
print("Target: 3000 frames (125+ Geogram calls)")
print("Historical crash zone: 1500-2100 frames")
print()
print("Fixes applied:")
print("  ✓ SmartPointer<PeriodicDelaunay3d> (Bruno's pattern)")
print("  ✓ Owned std::vector copies (no NumPy views)")
print("  ✓ GIL released during Geogram computation")
print("  ✓ Fresh NumPy returns (no memory aliasing)")
print("="*70)
print()

sim = TaichiSimStub(N=1000)
sched = FoamScheduler(sim, k_freeze=24)

t0 = time.time()

try:
    for i in range(3000):
        sched.step()
        
        if i % 100 == 0 and i > 0:
            hud = sched.hud()
            elapsed = time.time() - t0
            fps = i / elapsed
            geom_calls = sched.results_seen
            print(f"Frame {i:4d} | Geom: {geom_calls:3d} | "
                  f"IQ={hud['IQ_mu']:.3f}±{hud['IQ_sigma']:.3f} | "
                  f"FPS={fps:.1f}")
        
        # Milestones
        if i == 1500:
            print("\n" + "🎯"*35)
            print("🎯 FRAME 1500 - Historical crash start")
            print("🎯"*35 + "\n")
        if i == 2100:
            print("\n" + "🎉"*35)
            print("🎉 FRAME 2100 - PASSED HISTORICAL CRASH ZONE!")
            print("🎉"*35 + "\n")
    
    # Success!
    elapsed = time.time() - t0
    geom_calls = sched.results_seen
    
    print("\n" + "="*70)
    print("✅ ✅ ✅ TEST PASSED! ✅ ✅ ✅")
    print("="*70)
    print(f"Frames completed: 3000")
    print(f"Geogram calls: {geom_calls}")
    print(f"Time: {elapsed:.1f}s")
    print(f"Avg FPS: {3000/elapsed:.1f}")
    print()
    print("🎊 GIL-RELEASE + OWNED-COPY FIX WORKS! 🎊")
    print("The crash was a pybind11 memory lifetime issue.")
    print("Geogram + SmartPointer is stable.")
    print("="*70)
    
except KeyboardInterrupt:
    print(f"\n⚠️  User interrupted at frame {sched.frame}")
except Exception as e:
    frame = sched.frame
    geom_calls = sched.results_seen
    print(f"\n❌ CRASH at frame {frame} (Geom call ~{geom_calls})")
    print(f"Exception: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)


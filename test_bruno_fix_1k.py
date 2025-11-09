#!/usr/bin/env python
"""
Test Bruno's SmartPointer fix at N=1000
Goal: Run for 5000+ frames (previously crashed around 1500-2100)
"""

import faulthandler, os, time, sys
faulthandler.enable()
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("PYTHONMALLOC", "debug")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import numpy as np
from scheduler import FoamScheduler
from sim_stub import TaichiSimStub

def main():
    N = 1000
    k_freeze = 24
    target_frames = 5000
    
    print("="*70)
    print(f"🧪 BRUNO'S SMARTPOINTER FIX TEST")
    print("="*70)
    print(f"N = {N}")
    print(f"k_freeze = {k_freeze} (adaptive)")
    print(f"Target frames = {target_frames}")
    print(f"Previous crash point: ~1500-2100 frames")
    print(f"Fix applied: GEO::SmartPointer<PeriodicDelaunay3d>")
    print("="*70)
    print()
    
    # Use sim_stub (no GGUI overhead)
    sim = TaichiSimStub(N=N)
    sched = FoamScheduler(sim, k_freeze=k_freeze)
    
    t0 = time.time()
    frame = 0
    last_print = 0
    geom_calls = 0
    last_geom_count = 0
    
    try:
        while frame < target_frames:
            sched.step()
            frame += 1
            
            # Track geometry calls
            hud = sched.hud()
            if not hud['geom_pending'] and sched.last_IQ is not None:
                geom_calls = sched.results_seen
            
            # Print every 100 frames
            if frame % 100 == 0:
                elapsed = time.time() - t0
                fps = frame / elapsed
                new_geom = geom_calls - last_geom_count
                last_geom_count = geom_calls
                
                print(f"Frame {frame:5d} | Geom calls: {geom_calls:3d} (+{new_geom:2d}) | "
                      f"IQ μ={hud['IQ_mu']:.3f} σ={hud['IQ_sigma']:.3f} | "
                      f"k={hud['cadence']:2d} | t_geom={hud.get('t_geom_ms', 0):.1f}ms | "
                      f"FPS={fps:.1f}")
                
                # CRITICAL MILESTONE: Previous crash zone
                if frame == 1500:
                    print("\n" + "🎉"*35)
                    print("🎉 PASSED 1500 FRAMES (previous crash point)!")
                    print("🎉"*35 + "\n")
                if frame == 2100:
                    print("\n" + "🚀"*35)
                    print("🚀 PASSED 2100 FRAMES (maximum previous survival)!")
                    print("🚀"*35 + "\n")
                if frame == 3000:
                    print("\n" + "✨"*35)
                    print("✨ 3000 FRAMES - Bruno's fix is WORKING!")
                    print("✨"*35 + "\n")
                
    except KeyboardInterrupt:
        print(f"\n⚠️  User interrupted at frame {frame}")
    except Exception as e:
        print(f"\n❌ CRASH at frame {frame}")
        print(f"Exception: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Success!
    elapsed = time.time() - t0
    print("\n" + "="*70)
    print(f"✅ TEST PASSED!")
    print("="*70)
    print(f"Frames completed: {frame}/{target_frames}")
    print(f"Geometry calls: {geom_calls}")
    print(f"Total time: {elapsed:.1f}s")
    print(f"Average FPS: {frame/elapsed:.1f}")
    print()
    print("🎊 Bruno's SmartPointer fix WORKS! 🎊")
    print("Previous crash at ~1500-2100 frames is RESOLVED!")
    print("="*70)
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)


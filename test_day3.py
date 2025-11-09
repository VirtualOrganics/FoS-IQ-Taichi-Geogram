#!/usr/bin/env python
"""
Day 3 Integration Test: FREEZE → MEASURE → ADJUST → RELAX
Tests the full scheduler + controller + Geogram bridge
"""

import sys
import time

# Add src to path
sys.path.insert(0, '/Users/chimel/Desktop/Cursor_FoS-Custom-Grid/FoS-IQ-Taichi-Geogram/src')

from sim_stub import TaichiSimStub
from scheduler import FoamScheduler


def main():
    print("\n" + "="*70)
    print("Day 3 Integration Test: FREEZE → MEASURE → ADJUST → RELAX")
    print("="*70)
    
    # 1. Create simulator
    print("\n[1/4] Creating simulator...")
    N = 100  # Start small for fast testing
    sim = TaichiSimStub(N=N)
    
    # 2. Create scheduler
    print("\n[2/4] Creating scheduler...")
    k_freeze = 24  # Update geometry every 24 frames
    scheduler = FoamScheduler(sim, k_freeze=k_freeze)
    print(f"  Cadence: k_freeze = {k_freeze} frames")
    
    # 3. Run simulation loop
    print("\n[3/4] Running simulation...")
    num_cycles = 5  # Run 5 geometry update cycles
    frames_per_cycle = k_freeze
    total_frames = num_cycles * frames_per_cycle
    
    print(f"  Target: {num_cycles} cycles × {frames_per_cycle} frames = {total_frames} frames")
    print(f"  Expected: {num_cycles} geometry updates\n")
    
    updates_seen = 0
    last_IQ_mu = 0.0
    
    t0 = time.time()
    for frame in range(total_frames):
        # Run one scheduler step (RELAX + maybe FREEZE/ADJUST)
        scheduler.step()
        
        # Check for geometry updates
        hud = scheduler.hud()
        if hud["IQ_mu"] != last_IQ_mu and hud["IQ_mu"] > 0:
            updates_seen += 1
            last_IQ_mu = hud["IQ_mu"]
            
            print(f"  Frame {frame:3d}: Geometry update #{updates_seen}")
            print(f"    IQ μ={hud['IQ_mu']:.4f}, σ={hud['IQ_sigma']:.4f}")
            print(f"    t_geom={hud['t_geom_ms']:.2f} ms, k={hud['cadence']}")
            
            sim_stats = sim.stats()
            print(f"    Radii: μ={sim_stats['mean_r']:.5f}, σ={sim_stats['std_r']:.5f}")
    
    t_total = (time.time() - t0) * 1000  # ms
    
    # 4. Summary
    print("\n[4/4] Summary:")
    print("="*70)
    print(f"  Total frames: {total_frames}")
    print(f"  Geometry updates: {updates_seen}/{num_cycles} expected")
    print(f"  Total time: {t_total:.1f} ms ({t_total/total_frames:.2f} ms/frame)")
    
    final_hud = scheduler.hud()
    print(f"\n  Final IQ: μ={final_hud['IQ_mu']:.4f}, σ={final_hud['IQ_sigma']:.4f}")
    
    final_stats = sim.stats()
    print(f"  Final radii: μ={final_stats['mean_r']:.5f}, σ={final_stats['std_r']:.5f}")
    
    # Validation
    print("\n" + "="*70)
    if updates_seen >= num_cycles:
        print("✅ SUCCESS: All geometry updates completed!")
        print("✅ Day 3 integration working: FREEZE → MEASURE → ADJUST → RELAX")
        if updates_seen > num_cycles:
            print(f"✅ Adaptive cadence working: got {updates_seen} updates (k tightened from fast t_geom)")
    else:
        print(f"⚠️  WARNING: Expected {num_cycles} updates, got {updates_seen}")
    
    print("="*70)
    
    return updates_seen >= num_cycles


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


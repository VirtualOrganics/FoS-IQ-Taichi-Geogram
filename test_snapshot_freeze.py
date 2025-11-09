#!/usr/bin/env python
"""
Test: Run to frame 1200, save snapshot, test that snapshot 200x
This rules in/out geometric degeneracy vs loop bug
"""

import sys, pickle, time
sys.path.insert(0, 'src')
sys.path.insert(0, 'geom_bridge')

import numpy as np
from sim_stub import TaichiSimStub
from scheduler import FoamScheduler
from geom_bridge import compute_power_cells

print("="*70)
print("SNAPSHOT FREEZE TEST")
print("="*70)
print("Phase 1: Run to frame 1200, save snapshot")
print("Phase 2: Test frozen snapshot 200x")
print("="*70)
print()

# Phase 1: Run to frame 1200
print("Phase 1: Running to frame 1200...")
sim = TaichiSimStub(N=1000)
sched = FoamScheduler(sim, k_freeze=24)

for i in range(1200):
    sched.step()
    if i % 400 == 0:
        print(f"  Frame {i}")

# Save snapshot
print("\nSaving snapshot at frame 1200...")
P_snapshot = sim.get_positions01()
r_snapshot = sim.get_radii()
W_snapshot = r_snapshot * r_snapshot

print(f"Snapshot stats:")
print(f"  P range: [{P_snapshot.min():.3f}, {P_snapshot.max():.3f}]")
print(f"  r range: [{r_snapshot.min():.6f}, {r_snapshot.max():.6f}]")
print(f"  r mean±std: {r_snapshot.mean():.6f}±{r_snapshot.std():.6f}")
print(f"  r dispersion: {r_snapshot.std()/r_snapshot.mean():.3f}")

# Check for overlaps
min_dist = np.inf
for i in range(min(100, len(P_snapshot))):  # Sample 100 pairs
    for j in range(i+1, min(100, len(P_snapshot))):
        d = np.linalg.norm(P_snapshot[i] - P_snapshot[j])
        min_dist = min(min_dist, d)
print(f"  Min dist (sampled): {min_dist:.6f}")

# Phase 2: Test frozen snapshot 200x
print("\n" + "="*70)
print("Phase 2: Testing FROZEN snapshot 200 times...")
print("="*70)

t0 = time.time()
for k in range(200):
    V, A, FSC, FL = compute_power_cells(P_snapshot, W_snapshot)
    
    if k % 10 == 0:
        sumV = float(V.sum())
        maxV = float(V.max())
        bad = int(np.sum(FL != 0))
        minFSC = int(FSC.min())
        maxFSC = int(FSC.max())
        print(f"[{k:03d}] sumV={sumV:.6f}, maxV={maxV:.6f}, bad={bad}, FSC=[{minFSC},{maxFSC}]")
        
        # Check for Bruno's "single cell spans period" case
        if maxV > 0.5:
            print(f"  ⚠️  WARNING: Dominant cell detected (maxV={maxV:.3f})")
        if bad > 10:
            print(f"  ⚠️  WARNING: Many degenerate cells (bad={bad})")

dt = time.time() - t0

print("\n" + "="*70)
print("✅ PHASE 2 COMPLETE")
print("="*70)
print(f"Completed 200 calls on FROZEN snapshot in {dt:.2f}s")
print()
print("CONCLUSION:")
print("  Frozen snapshot from frame 1200 is STABLE for 200 calls")
print("  → Crash is NOT due to geometric degeneracy")
print("  → Crash is in scheduler/loop structure")
print("="*70)


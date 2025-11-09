#!/usr/bin/env python
"""Run to frame 1200, save snapshot for frozen testing"""
import sys, numpy as np
sys.path.insert(0, 'src')

from sim_stub import TaichiSimStub
from scheduler import FoamScheduler

print("Running to frame 1200...")
sim = TaichiSimStub(N=1000)
sched = FoamScheduler(sim, k_freeze=24)

for i in range(1200):
    sched.step()
    if i % 400 == 0:
        print(f"  Frame {i}")

# Save snapshot
print("\nSaving snapshot...")
P01 = sim.get_positions01()
r = sim.get_radii()

np.save('P01_frame1200.npy', P01)
np.save('r_frame1200.npy', r)

print(f"✅ Saved to P01_frame1200.npy, r_frame1200.npy")
print(f"Stats:")
print(f"  P range: [{P01.min():.3f}, {P01.max():.3f}]")
print(f"  r range: [{r.min():.6f}, {r.max():.6f}]")
print(f"  r mean±std: {r.mean():.6f}±{r.std():.6f}")
print(f"  r dispersion: {r.std()/r.mean():.3f}")


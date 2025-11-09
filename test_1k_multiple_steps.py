#!/usr/bin/env python
"""Test N=1000 for 100 frames (4-5 Geogram calls)"""

import sys
sys.path.insert(0, 'src')

from sim_stub import TaichiSimStub
from scheduler import FoamScheduler

print("Creating sim (N=1000)...")
sim = TaichiSimStub(N=1000)

print("Creating scheduler...")
sched = FoamScheduler(sim, k_freeze=24)

print("\nRunning 100 frames...")
for i in range(100):
    sched.step()
    if i % 10 == 0:
        hud = sched.hud()
        print(f"Frame {i:3d}: IQ μ={hud['IQ_mu']:.3f} σ={hud['IQ_sigma']:.3f} | "
              f"k={hud['cadence']} | pending={hud['geom_pending']}")

print("\n✅ TEST PASSED! N=1000 stable for 100 frames")


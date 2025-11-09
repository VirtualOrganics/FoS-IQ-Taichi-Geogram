#!/usr/bin/env python
"""Test 1000 frames"""
import sys, time
sys.path.insert(0, 'src')

from sim_stub import TaichiSimStub
from scheduler import FoamScheduler

print("Starting 3000 frame test...")
sim = TaichiSimStub(N=1000)
sched = FoamScheduler(sim, k_freeze=24)

t0 = time.time()
for i in range(3000):
    sched.step()
    if i % 100 == 0:
        hud = sched.hud()
        print(f'Frame {i:4d} | Geom: {sched.results_seen:3d} | IQ={hud["IQ_mu"]:.3f}')

print(f'✅ 1000 frames in {time.time()-t0:.1f}s')


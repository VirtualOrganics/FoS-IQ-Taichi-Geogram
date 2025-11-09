#!/usr/bin/env python
"""Test 2000 frames - past historical crash"""
import sys, time
sys.path.insert(0, 'src')

from sim_stub import TaichiSimStub
from scheduler import FoamScheduler

print("Starting 2000 frame test (past historical crash 1500-2100)...")
sim = TaichiSimStub(N=1000)
sched = FoamScheduler(sim, k_freeze=24)

t0 = time.time()
for i in range(2000):
    sched.step()
    if i % 100 == 0:
        hud = sched.hud()
        print(f'Frame {i:4d} | Geom: {sched.results_seen:3d} | IQ={hud["IQ_mu"]:.3f}')
    
    if i == 1500:
        print("*** PASSED frame 1500 ***")

print(f'✅ 2000 frames in {time.time()-t0:.1f}s')


#!/usr/bin/env python
"""Run 1000 frames TWICE to reach 2000 total"""
import sys, time
sys.path.insert(0, 'src')

from sim_stub import TaichiSimStub
from scheduler import FoamScheduler

print("Creating sim and scheduler...")
sim = TaichiSimStub(N=1000)
sched = FoamScheduler(sim, k_freeze=24)

print("\nRun 1: Frames 0-1000...")
t0 = time.time()
for i in range(1000):
    sched.step()
    if i % 500 == 0:
        print(f"  Frame {i}")

print(f"✅ First 1000 frames in {time.time()-t0:.1f}s")

print("\nRun 2: Frames 1000-2000...")
t0 = time.time()
for i in range(1000):
    sched.step()
    if i % 500 == 0:
        print(f"  Frame {1000+i}")

print(f"✅ Second 1000 frames in {time.time()-t0:.1f}s")
print(f"\n🎊 Total: 2000 frames, past historical crash!")


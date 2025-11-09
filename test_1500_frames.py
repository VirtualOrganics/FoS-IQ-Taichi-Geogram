#!/usr/bin/env python
"""Test exactly 1500 frames - historical crash point"""
import sys
sys.path.insert(0, 'src')

print("Importing...")
from sim_stub import TaichiSimStub
from scheduler import FoamScheduler

print("Creating sim...")
sim = TaichiSimStub(N=1000)

print("Creating scheduler...")
sched = FoamScheduler(sim, k_freeze=24)

print("Starting 1500 frame loop...")
for i in range(1500):
    sched.step()
    if i % 500 == 0:
        print(f'Frame {i}')

print('✅ 1500 frames completed')


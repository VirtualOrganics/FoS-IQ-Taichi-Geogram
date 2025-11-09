#!/usr/bin/env python
"""Small loop: 50 frames"""

import sys
sys.path.insert(0, 'src')

from sim_stub import TaichiSimStub
from scheduler import FoamScheduler

print("Creating sim and scheduler...")
sim = TaichiSimStub(N=1000)
sched = FoamScheduler(sim, k_freeze=24)

print("Running 50 frames...")
for i in range(50):
    sched.step()
    if i % 10 == 0:
        print(f"  Frame {i} OK")

print("✅ 50 frames completed")


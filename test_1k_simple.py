#!/usr/bin/env python
import sys
sys.path.insert(0, 'src')
from sim_stub import TaichiSimStub
from scheduler import FoamScheduler

sim = TaichiSimStub(N=1000)
sched = FoamScheduler(sim, k_freeze=24)

for i in range(1000):
    sched.step()
    if i % 500 == 0:
        print(f'Frame {i}')

print('✅ 1000 frames')

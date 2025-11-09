#!/usr/bin/env python
"""Ultra-minimal: Create scheduler, call step() once"""

import sys
sys.path.insert(0, 'src')

print("1. Importing...")
from sim_stub import TaichiSimStub
from scheduler import FoamScheduler

print("2. Creating sim...")
sim = TaichiSimStub(N=100)

print("3. Creating scheduler...")
sched = FoamScheduler(sim, k_freeze=24)

print("4. Calling step()...")
sched.step()

print("5. ✅ SUCCESS - one step completed")


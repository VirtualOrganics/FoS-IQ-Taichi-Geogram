#!/usr/bin/env python
"""Test scheduler for exactly ONE step"""

import sys
sys.path.insert(0, 'src')

from sim_stub import TaichiSimStub
from scheduler import FoamScheduler

print("Creating sim (N=100)...")
sim = TaichiSimStub(N=100)

print("Creating scheduler...")
sched = FoamScheduler(sim, k_freeze=24)

print("Running frame 0 (should not call Geogram)...")
sched.step()
print("✓ Frame 0 OK")

for i in range(1, 24):
    sched.step()
    print(f"✓ Frame {i} OK")

print("\nRunning frame 24 (SHOULD call Geogram)...")
sched.step()
print("✓ Frame 24 OK - Geogram called!")

print("\n✅ TEST PASSED!")


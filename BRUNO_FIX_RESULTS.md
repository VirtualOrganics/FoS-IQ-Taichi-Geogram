# Bruno's SmartPointer Fix - Test Results

**Date**: November 9, 2025  
**Issue**: [Geogram #309](https://github.com/BrunoLevy/geogram/issues/309)  
**Fix Applied**: Changed from stack allocation to `GEO::SmartPointer<PeriodicDelaunay3d>`

---

## Summary

Bruno Lévy's suggested fix (`SmartPointer` pattern instead of stack allocation) **partially resolves** the segfault issue!

---

## Changes Made

### C++ Bridge (`geom_bridge/bridge.cpp`)

**Before (WRONG):**
```cpp
GEO::PeriodicDelaunay3d pd(/*periodic=*/true, /*period=*/1.0);  // Stack allocation
pd.set_vertices(GEO::index_t(N), P.data());
pd.set_weights(W.data());
pd.compute();
```

**After (CORRECT - Bruno's fix):**
```cpp
GEO::SmartPointer<GEO::PeriodicDelaunay3d> pd = new GEO::PeriodicDelaunay3d(/*periodic=*/true, /*period=*/1.0);
pd->set_vertices(GEO::index_t(N), P.data());  // Note: -> instead of .
pd->set_weights(W.data());
pd->compute();
```

### Additional Fixes

1. **`sim_stub.py`**: Changed from `np.random.rand()` to jittered grid initialization to avoid random overlaps
2. **Python calls**: Removed `periodic=True` parameter (function signature changed)

---

## Test Results

### ✅ Tests that PASS

| Test | N | Frames | Geom Calls | Status |
|------|---|--------|------------|---------|
| Direct call | 10 | 1 | 1 | ✅ PASS |
| Direct call | 100 | 1 | 1 | ✅ PASS |
| Scheduler | 100 | 25 | 1 | ✅ PASS |
| Scheduler | 1000 | 100 | 4 | ✅ PASS |
| Batching test | 1000 | 1 (batched) | 1 | ✅ PASS |

### ❌ Tests that FAIL

| Test | N | Target Frames | Crash Point | Status |
|------|---|---------------|-------------|---------|
| Marathon | 1000 | 3000 | ~? (no output) | ❌ CRASH (segfault 139) |

---

## Key Findings

### 1. SmartPointer Fix Works for Short Runs ✅
- N=1000 runs successfully for 100 frames (~4 Geogram calls)
- All basic functionality works (IQ computation, controller, batching)
- No crashes during initial phase

### 2. Long Runs Still Crash ⚠️
- Marathon test (3000 frames, ~125 Geogram calls) crashes with segfault 139
- Crash happens silently (no output, no Python traceback)
- Suggests deep C++ issue, possibly after many reuses

### 3. Batching Works ✅
- N=1000 with batching (chunks of 512) succeeds
- Memory ownership fixes (contiguous copies) working correctly

---

## Possible Remaining Issues

### Hypothesis 1: Internal State Accumulation
Even with `SmartPointer`, after many (`>4`) reuses, some internal Geogram state might still accumulate/corrupt.

**Next Steps**:
- Try recreating the `SmartPointer` every N calls
- Check if Debug mode assertions catch anything

### Hypothesis 2: Input Data Degradation
After many `relax_step()` iterations, particles might drift into degenerate configurations (overlaps, colinear, etc.).

**Next Steps**:
- Add validation before each Geogram call (check for duplicates, out-of-bounds)
- Test with frozen positions (no relax_step)

### Hypothesis 3: Memory Fragmentation
Long runs might exhaust some internal Geogram buffer or pool.

**Next Steps**:
- Run with memory profiler
- Try limiting total Geogram calls (e.g., call only every 100 frames instead of 24)

---

## Code Status

### Files Modified (This Session)
- `geom_bridge/bridge.cpp` - Applied SmartPointer fix
- `src/geom_worker.py` - Removed `periodic=True` parameter
- `src/geom_worker_sync.py` - Removed `periodic=True` parameter
- `src/sim_stub.py` - Added jittered grid initialization

### Build Configuration
- Mode: **Debug** (with Geogram assertions enabled as Bruno suggested)
- Compiler: Clang (Apple Silicon)
- Optimization: Debug assertions + RelWithDebInfo optimizations

---

## Recommendations

### For User (Tomorrow)
1. **Try Debug mode marathon**: Run `test_marathon_1k.py` again and look for assertion failures
2. **Profile memory**: Use `memory_profiler` to track Geogram memory usage
3. **Test frozen sim**: Disable `relax_step()` to see if input degradation is the issue
4. **Reduce cadence**: Try `k_freeze=100` to reduce Geogram call frequency

### For Bruno (GitHub Response)
✅ **Positive**: SmartPointer fix works for short runs (100 frames, ~4 Geogram calls at N=1000)  
⚠️ **Issue remains**: Long runs (3000 frames, ~125 calls) still crash, but progress is significant

**Request**:
- Confirm if there are any internal limits/buffers in `PeriodicDelaunay3d` that might need periodic clearing
- Suggest Debug mode flags or environment variables to enable more verbose Geogram logging
- Ask if there's a "reset" method beyond just creating a new `SmartPointer`

---

## Next Debug Steps

1. **Capture crash details**:
   ```bash
   ulimit -c unlimited  # Enable core dumps
   python test_marathon_1k.py
   # Analyze core dump with lldb
   ```

2. **Test with Geogram debug flags**:
   ```cpp
   GEO::Logger::instance()->set_quiet(false);  // Enable all logging
   ```

3. **Add periodic recreation**:
   ```python
   # In scheduler.py, after every 10 Geogram calls:
   if self.results_seen % 10 == 0:
       self.worker = GeomWorker()  # Fresh worker + fresh SmartPointer
   ```

---

## Conclusion

Bruno's SmartPointer fix is **a major step forward**:
- ✅ Resolves immediate crashes for typical use (< 100 frames)
- ✅ Correct API pattern per Geogram design
- ⚠️ Long-run stability still needs investigation

The issue has shifted from "crashes immediately" to "crashes after many iterations", which is significant progress and narrows down the root cause to either:
- Internal state that `SmartPointer` alone doesn't reset
- Input data degradation over time
- Some resource exhaustion

---

**Status**: PARTIAL FIX - Major improvement, further debugging needed for marathon stability.


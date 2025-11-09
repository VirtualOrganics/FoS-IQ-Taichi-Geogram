# Quick Start: Taichi Integration

## You Are Here ✅

Days 1-4 complete:
- ✅ Geogram bridge working
- ✅ Controller tested
- ✅ Scheduler proven stable
- ✅ Adaptive cadence functional

---

## Next 30 Minutes: Wire Your Taichi Sim

### Step 1: Add 6 methods to your sim class (5 minutes)

```python
@ti.data_oriented
class YourTaichiSim:
    def __init__(self, N, L=1.0):
        self.N = N
        self.L = L
        self.x = ti.Vector.field(3, dtype=ti.f32, shape=N)  # positions
        self.r = ti.field(dtype=ti.f32, shape=N)            # radii
        self.frozen = False  # NEW: freeze flag
    
    # ============ ADD THESE 6 METHODS ============
    
    def get_positions01(self):
        """Map [-L,+L]³ → [0,1]³ for Geogram"""
        x_cpu = self.x.to_numpy()
        return ((x_cpu + self.L) / (2.0 * self.L)).astype(np.float64)
    
    def get_radii(self):
        """Get radii as numpy array"""
        return self.r.to_numpy().astype(np.float64)
    
    def set_radii(self, r_new):
        """Write controller-adjusted radii back"""
        self.r.from_numpy(r_new.astype(np.float32))
    
    def relax_step(self):
        """One physics step (skip if frozen)"""
        if not self.frozen:
            self._compute_forces()
            self._integrate()
    
    def freeze(self):
        """Pause for geometry measurement"""
        self.frozen = True
    
    def resume(self):
        """Resume after measurement"""
        self.frozen = False
```

**That's it!** No changes to your kernels/forces.

---

### Step 2: Import scheduler (1 line)

```python
import sys
sys.path.insert(0, '/path/to/FoS-IQ-Taichi-Geogram/src')
from scheduler import FoamScheduler
```

---

### Step 3: Replace main loop (2 lines changed)

**Before:**
```python
while window.running:
    sim.step()  # OLD
    canvas.circles(sim.x, radius=sim.r, ...)
    window.show()
```

**After:**
```python
scheduler = FoamScheduler(sim, k_freeze=24)  # ADD THIS ONCE

while window.running:
    scheduler.step()  # CHANGED: scheduler instead of sim
    
    # Optional: HUD
    hud = scheduler.hud()
    canvas.text(f"IQ μ={hud['IQ_mu']:.3f} k={hud['cadence']}", 
                pos=(0.02, 0.98), color=(1,1,1), font_size=18)
    
    canvas.circles(sim.x, radius=sim.r, ...)
    window.show()
```

---

### Step 4: Run and observe (5 minutes)

```bash
python your_sim.py
```

**Watch for:**
- Every ~24 frames: brief pause (FREEZE)
- HUD shows IQ μ/σ updating
- Particles with low IQ grow faster
- Particles with high IQ shrink slowly
- `k` adapts if geometry is slow

---

## Debugging Tips

### Issue: "geom_bridge not found"
```bash
cd FoS-IQ-Taichi-Geogram/geom_bridge/build
cmake .. && cmake --build .
```

### Issue: Segfault at N>1k
**Solution:** Start with N≤1000 (proven stable)

### Issue: FPS drops
**Check:** `hud['t_geom_ms']` - should be <20ms
- If >50ms: `k` will auto-stretch
- Or reduce N temporarily

### Issue: IQ not changing
**Check:** `hud['geom_pending']` - should toggle true/false
- If stuck `True`: worker thread issue
- If stuck `False`: geometry not running

---

## Validation Checklist

Run for 300 frames and check:

- [ ] No crashes/errors
- [ ] HUD shows IQ μ ≠ 0 (geometry working)
- [ ] `k` visible in HUD (cadence tracking)
- [ ] Particles visibly growing/shrinking (controller working)
- [ ] FPS stays smooth (non-blocking)
- [ ] IQ μ gradually increasing over time (converging to rounder cells)

**If all ✓ → You're running production IQ-driven foam!** 🎉

---

## Next Level (optional)

### Color by IQ:
```python
# Compute IQ per particle
V, S = ..., ...  # from last geometry update
IQ = 36*np.pi * (V**2) / (S**3)

# Map to RGB: red=low, green=mid, blue=high
colors = np.zeros((N, 3))
colors[IQ < 0.70] = [1, 0, 0]  # Red: needs growth
colors[(IQ >= 0.70) & (IQ <= 0.90)] = [0, 1, 0]  # Green: good
colors[IQ > 0.90] = [0, 0, 1]  # Blue: too round

canvas.circles(sim.x, radius=sim.r, color=colors)
```

### Export cell meshes:
```python
# Save power cell geometry for inspection
# (requires wiring VBW::ConvexCell vertex export)
```

### Tune controller:
```python
scheduler = FoamScheduler(sim, k_freeze=24)
# Adjust in controller.py:
#   IQ_min = 0.70 → lower = more aggressive growth
#   beta_grow = 0.015 → higher = faster growth
```

---

## File Reference

| File | Purpose |
|------|---------|
| `src/scheduler.py` | Orchestrates FREEZE→MEASURE→ADJUST→RELAX |
| `src/controller.py` | IQ-banded radius adjustment |
| `src/geom_worker.py` | Non-blocking Geogram calls |
| `geom_bridge/bridge.cpp` | C++ ↔ Python binding |
| `TAICHI_INTEGRATION.md` | Detailed integration docs |
| `DAY4_SUMMARY.md` | What got built |

---

## Questions?

**Scheduler not calling geometry?**
→ Check `k_freeze` - every k frames it fires

**IQ too low?**
→ Cells need time to relax; run 500+ frames

**Want faster updates?**
→ Lower `k_freeze` to 16 (or let adaptive cadence handle it)

**Ready for N>1k?**
→ Build Geogram in Release mode first

---

**You're ready! Go wire it up!** 🚀


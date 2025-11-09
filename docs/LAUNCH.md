# 🚀 Launch Instructions

## Live Foam Viewer (with IQ coloring)

```bash
cd /Users/chimel/Desktop/Cursor_FoS-Custom-Grid
source venv/bin/activate
python FoS-IQ-Taichi-Geogram/run_geogram_foam.py
```

**What you'll see:**
- 3D window with 1000 particles
- Particles colored by IQ:
  - 🔵 **Blue** = Low IQ (<0.70) → Growing
  - ⚪ **Gray** = Good IQ (0.70-0.90)
  - 🔴 **Red** = High IQ (>0.90) → Shrinking
- HUD showing: IQ μ/σ, cadence k, t_geom
- Particles slowly swirling (toy dynamics)

**Every ~24 frames:**
- Brief pause (FREEZE)
- Geogram computes exact power cells
- Controller adjusts radii based on IQ
- Colors update to reflect new IQ
- Adaptive k adjusts if needed

---

## Headless Tests (terminal only)

**Day 3 integration test (N=100):**
```bash
python FoS-IQ-Taichi-Geogram/test_day3.py
```

**Scale test N=1k:**
```bash
python FoS-IQ-Taichi-Geogram/test_scale_1k.py
```

**Batching test N=1500:**
```bash
python FoS-IQ-Taichi-Geogram/test_batch_1500.py
```

---

## Configuration

**In `run_geogram_foam.py`, change:**

```python
main(N=1000, k_freeze=24)
```

- **N:** Particle count (≤1000 = single-shot, >1000 = batched)
- **k_freeze:** Update cadence (auto-adapts based on t_geom)

**To use your real Taichi sim:**

Replace this line:
```python
sim = TaichiSim(N=N)
```

With:
```python
sim = YourRealTaichiSim(N=N, ...)
```

Your sim just needs 6 methods (see `TAICHI_INTEGRATION.md`)

---

## Keyboard Controls (GGUI default)

- **Mouse drag:** Rotate camera
- **Mouse wheel:** Zoom
- **ESC:** Exit

---

## Troubleshooting

**"No module named 'geom_bridge'"**
```bash
cd FoS-IQ-Taichi-Geogram/geom_bridge/build
cmake -DCMAKE_BUILD_TYPE=RelWithDebInfo .. && cmake --build .
```

**Window doesn't appear**
- Check Taichi installed: `pip show taichi`
- Check GGUI backend: Try `ti.init(arch=ti.cpu)` if GPU fails

**Segfault at N>1k**
- Normal with random positions
- Use jittered grid (already in `run_geogram_foam.py`)
- Or lower N to ≤1000

**FPS drops**
- Check HUD: if t_geom > 50ms, adaptive k will stretch
- Lower N temporarily
- Or increase k_freeze manually

---

## Performance Guide

| N    | t_geom  | k (adaptive) | FPS  | Mode        |
|------|---------|--------------|------|-------------|
| 100  | ~5ms    | 16-24        | 200+ | Single-shot |
| 1000 | ~18ms   | 20-24        | 100+ | Single-shot |
| 1500 | ~34ms   | 24-32        | 60+  | Batched 2×  |
| 2000 | ~50ms   | 32-40        | 40+  | Batched 2×  |

*Tested on M2 Mac. Your mileage may vary.*

---

## What's Happening Under the Hood

1. **RELAX:** Taichi GPU runs physics (`sim.step_kernel()`)
2. **FREEZE:** Every k frames, pause dynamics
3. **MEASURE:** Geogram computes exact V, S → IQ (CPU, batched if N>1000)
4. **ADJUST:** Controller modifies radii based on IQ bands
5. **RESUME:** Continue relaxing with new radii
6. **REPEAT:** Adaptive k adjusts based on t_geom

---

## Next Steps

1. **Run it!** See IQ-driven foam live
2. **Swap in your real sim** (see `TAICHI_INTEGRATION.md`)
3. **Tune controller** (`src/controller.py`):
   - `IQ_min`, `IQ_max` (band thresholds)
   - `beta_grow`, `beta_shrink` (rates)
4. **Add more visualization:**
   - Export cell meshes
   - Show force vectors
   - Display cell stats
5. **Scale up:** Try N=2000+ with batching

---

**Enjoy your IQ-driven foam!** 🧼✨


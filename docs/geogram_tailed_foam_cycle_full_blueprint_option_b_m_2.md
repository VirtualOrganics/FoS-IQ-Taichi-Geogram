# Geogram‑Tailed Foam Cycle — Full Blueprint (Option B, M2)

**Target machine:** MacBook Pro 2023 (M2, 16 GB, Metal)

**Core idea:** Keep Taichi for real‑time **RELAX** (60–120 FPS) and visualization. Replace the analytic in‑house clipper with a trusted **Geogram** geometry service that runs during frozen snapshots to compute **exact power‑cell metrics** (V, S, FSC, IQ) on a periodic cube. Maintain the discrete cadence:

```
while !converged:
  FREEZE()                     # halt motion on GPU
  METRICS = GEOMETRY(points, weights)  # Geogram (CPU), exact power cells
  ADJUST(METRICS)              # IQ-banded controller (zero-sum)
  RELAX(frames=K)              # soft forces + PBD on GPU
```

---

## 0) Non‑negotiables
- **Exact geometry at measure-time** (Laguerre / power diagram, periodic).
- **Deterministic & reproducible** (same inputs ⇒ same outputs).
- **Local bounded cost** in RELAX (grid neighbors only; no JFA propagation).
- **No background stalls:** Geometry runs in a worker thread; UI/GPU loop responsive.
- **Scales on M2:** 10k–50k seeds practical; 100k with tuned cadence.

---

## 1) System Architecture

```
┌────────────────────────────────────────────────────────────┐
│                 Taichi Live Loop (Metal GPU)               │
│  • RELAX: forces + PBD (60–120 FPS)                        │
│  • UI: IQ histograms, overlaps, FPS                        │
│  • FREEZE: snapshot positions & radii → host staging       │
└──────────────┬─────────────────────────────────────────────┘
               │  (numpy arrays: points_norm, weights)
               ▼
┌────────────────────────────────────────────────────────────┐
│          Geogram Geometry Service (CPU, worker)            │
│  • PeriodicDelaunay3d → power cells                        │
│  • Per‑site: volume, area, FSC (face count)                │
│  • Optional: face adjacency/mesh for debug                 │
└──────────────┬─────────────────────────────────────────────┘
               │  (metrics numpy arrays)
               ▼
┌────────────────────────────────────────────────────────────┐
│      Controller (CPU)                                      │
│  • IQ = 36π V² / S³ (raw)                                  │
│  • Banded, zero‑sum radius updates with clamps             │
└──────────────┬─────────────────────────────────────────────┘
               │  (updated radii → Taichi fields)
               ▼
        Resume RELAX on GPU
```

---

## 2) Data Model (SoA)

**GPU (Taichi)**
- `pos[N]: f32x3` (simulation space `[-L,L]^3`, periodic)
- `rad[N]: f32` (Minkowski radii; weights = r²)
- `vel[N]: f32x3` (RELAX only)
- Grid/neighbor buffers for RELAX (cell size ≈ mean spacing)

**CPU staging (numpy)**
- `points_gpu[N,3]` ← from Taichi
- `points_norm[N,3] = (points_gpu + L) / (2L)` (in `[0,1]^3`)
- `weights[N] = rad²`

**Geometry results (numpy)**
- `volume[N], area[N], fsc[N]`
- `iq_raw[N] = (36π * volume²) / area³` (no clamp; clamp for viz only)
- Optional: debug `faces[]`, `neighbors[]`

---

## 3) Periodicity & Units
- **Input to Geogram:** points in `[0,1]^3`, squared weights.
- **Output scaling:**
  - `V_sim = V_geo * (2L)^3`
  - `S_sim = S_geo * (2L)^2`
  - IQ is scale‑invariant ⇒ same in both spaces.
- **Wrap rule on GPU:** always maintain `pos` modulo domain; **FREEZE** copies already wrapped positions.

---

## 4) Geometry Service (pybind11)

**C++ API (exposed to Python)**
```cpp
struct GeometryResult {
  std::vector<double> volume; // size N
  std::vector<double> area;   // size N
  std::vector<int>    fsc;    // face count per cell
  std::vector<int>    flags;  // 0=ok, >0 degenerate/repair applied
};

GeometryResult compute_power_cells(
    const double* points_norm, // N×3, row-major
    const double* weights,     // N
    int N,
    bool periodic // always true
);
```

**Implementation notes**
- Use `geogram::PeriodicDelaunay3d`.
- Build Laguerre (power) diagram from the Delaunay structure.
- For each site: accumulate exact `V` and `S`; count faces (`FSC`).
- Handle degeneracies with Geogram’s predicates; set `flags[i]` on repair.

**Build**
- CMake + pybind11; produce `geom_bridge.cpython-*.so`.
- Ship a script `tools/build_geom_bridge.sh` pinning Geogram version.

---

## 5) Freeze Scheduler & Cadence

**Config**
- `GEOGRAM_UPDATE_INTERVAL` (default 16–24 RELAX frames)
- `MAX_GEOM_LATENCY_MS` (UI warning threshold; default 150 ms)

**Policy**
- Every `k` RELAX frames: FREEZE → dispatch geometry job.
- If a previous job is still running: **skip** this window (never block RELAX).
- Maintain a small queue (depth 1) to avoid back‑pressure.

---

## 6) Controller (IQ‑band, zero‑sum)

**Inputs:** `V[i], S[i], IQ[i]`, optional `flags[i]`.

**Pre‑filter:** if `flags[i] != 0` or `S[i] < S_min` → carry previous metrics for that i.

**Skewness:** `skew[i] = 1 − clamp(IQ[i], 0, 1)` (for ranking only).

**Decile policy (recommended):**
- `K = worst_decile(skew)` (ties stable‑sort by prior IQ to reduce flapping)
- Proposals:
  - `dV[i] = +β_s * V[i]` for `i ∈ K`  (β_s ≈ 1–2%)
  - `dV[j] = −β_e * V̄`   for `j ∉ K`  (β_e ≈ 0.1–0.3%)
- **Zero‑sum renormalization:**
  - `Spos = Σ_{i∈K} dV[i]`, `Sneg = −Σ_{j∉K} dV[j]`
  - If `|Spos − Sneg| > ε`, scale the **shrink** pool to match `Spos` (preserve expansion intent).
- Convert to radius updates: `dr = dV / (4π r²)`; clamp `|dr| ≤ Δr_max * r` (Δr_max ≈ 0.5–1.0%).
- Persist a per‑cell momentum term (EMA on `dr`) to smooth oscillations (controller‑side only).

---

## 7) RELAX (GPU) — Forces + PBD

**Neighbors:** uniform grid, cell ≈ mean spacing, 27 buckets; rebuild each frame.

**Forces:**
- Mild attraction: `F_attr = −k_a * d * u` (local only)
- Contact repulsion: `F_rep = k_r * max(0, r_sum − d) * u`
- Small damping; integrator: semi‑implicit Euler.

**PBD:** 4–8 iterations/frame, project overlaps by ±½ along `u`; periodic wrap after update.

**Budgets (M2, N≈10k):** 3–8 ms/frame (60–120 FPS).

---

## 8) Visualization & Debugging
- **Particles:** spheres scaled by `rad`; color by IQ band.
- **HUD:** FPS, overlaps %, `t_relax`, last `t_geom`, IQ μ/σ, overflow/degeneracy count.
- **Optional:** draw a small subset of Geogram edges (per cycle) for low‑IQ cells.
- **Dumps:** `debug_geogram/cycle_####.{csv,obj,json}` for selected cells.

---

## 9) Failure Modes & Safeguards
- **Geometry latency spike:** if `t_geom > MAX_GEOM_LATENCY_MS`, auto‑increase `GEOGRAM_UPDATE_INTERVAL` by ×1.5 (ceil), log warning.
- **Degenerate cells from Geogram:** flag → reuse previous metrics; controller excludes flagged cells.
- **Metric outliers:** winsorize IQ at [p1, p99] for **ranking only** (never for stored values).
- **Volume drift:** enforce exact zero‑sum each cycle; log cumulative drift (should be ~0).

---

## 10) Performance Targets (M2, release build)
- **N = 10k**: `t_geom ≈ 20–60 ms` (periodic Delaunay + power metrics)
- **N = 50k**: `t_geom ≈ 80–180 ms` (increase interval to 24–48)
- **RELAX:** 60–120 FPS (3–8 ms/frame)
- **Amortized:** 60–100 FPS depending on cadence.

---

## 11) Blue‑Noise Init & Weights

**Positions:** Fast Poisson‑disk (Bridson) on CPU; verify no lattice regularization: initially **disable** attraction forces (PBD only) for first few cycles.

**Weights / target volumes:**
- If a target volume field `V*` exists: initialize radii so `V ≈ V*` using `r = (3V/(4π))^(1/3)` and normalize to domain mean.
- Otherwise: start uniform `r0`, let controller evolve radii.

---

## 12) File/Module Layout
```
src/
  config.py                 # cadence, thresholds, UI flags
  state.py                  # Taichi fields (pos, rad, vel, grid)
  relax.py                  # forces(), integrate(), pbd()
  scheduler.py              # FREEZE cadence, worker orchestration
  geometry_service.py       # bridge call, scaling, guards
  controller.py             # IQ-banded zero-sum updates
  viz.py                    # window, HUD, color maps
  main.py                   # glue loop

geom_bridge/
  CMakeLists.txt
  bridge.cpp                # pybind11 → Geogram
  geogram_vendor/           # pinned submodule or prebuilt
  build_geom_bridge.sh
```

---

## 13) Public Python API (bridge)
```python
import numpy as np
from geom_bridge import compute_power_cells

res = compute_power_cells(points_norm: np.ndarray, weights: np.ndarray, periodic: bool)
# res.volume (N,), res.area (N,), res.fsc (N,), res.flags (N,)
```

---

## 14) Taichi Glue (pseudocode)
```python
# scheduler.py
if frames_since_geom >= GEOGRAM_UPDATE_INTERVAL and not worker_busy():
    pts = to_numpy_pos_wrapped()                 # N×3
    r   = to_numpy_rad()
    submit_geometry_job( (pts + L) / (2*L), r**2 )

# geometry_service.py (on completion)
V, S, FSC, flags = result
IQ = 36*np.pi * (V**2) / (S**3)
apply_controller(IQ, V, flags)
```

---

## 15) Testing & Validation
1. **Unit tests**
   - Scaling round‑trip `[−L,L]^3 ↔ [0,1]^3`.
   - Controller zero‑sum under edge cases (identical IQs, all flagged).
2. **Micro‑suites** (N=1k)
   - Random + uniform weights; expect stable IQ distribution; no zero‑face cells.
   - Compare against Geogram CLI (golden JSON) for invariants.
3. **Soak** (N=10k, 5k cycles)
   - Log IQ μ↑, σ↓ trends; latency histograms; no UI stutter.

---

## 16) Roadmap
- **Day 1–2:** Build `geom_bridge` (native, pybind11). Log `t_geom` on N=1k/10k.
- **Day 3:** Integrate scheduler; end‑to‑end FREEZE→MEASURE→ADJUST→RELAX.
- **Day 4:** Controller tuning sweep; HUD metrics; debug dumps.
- **Day 5+:** Optional mesh overlay; incremental Delaunay exploration; profile & polish.

---

## 17) Known Non‑Goals (for now)
- Full mesh streaming each frame (edges) — only on demand for debug subsets.
- On‑GPU power‑cell construction (Metal) — revisit if Geogram becomes a bottleneck.
- Multi‑material / anisotropic metrics — future extension.

---

## 18) FAQ
- **Why Geogram over meshless on M2?** Meshless repo is CPU/OpenMP on macOS (no CUDA path), approximate, and lacks native periodicity. Geogram gives **exact periodic** power cells with predictable latency.
- **Does RELAX run while geometry runs?** Yes; geometry executes in a worker. We freeze **only** to take a consistent snapshot and to apply controller updates.
- **What if geometry misses a window?** Skip, keep relaxing; next window will catch up.

---

## 19) Acceptance Criteria
- N=10k: `t_geom ≤ 60 ms` median; RELAX ≥ 60 FPS; IQ μ increases or stabilizes across 100 cycles.
- Zero‑sum drift ≤ 1e‑6 of total volume across 1k cycles.
- No hard stalls of UI; worst‑case `t_geom` logged; scheduler adapts interval.

---

## 20) One‑Page Bring‑Up Checklist
- [ ] Build pybind11 bridge; `compute_power_cells()` returns arrays for N=1k.
- [ ] Wire scheduler; snapshot/submit/receive metrics.
- [ ] Scale metrics back; IQ computed; controller applies updates; radii clamped.
- [ ] HUD shows `t_geom`, IQ μ/σ, overlaps %, latency warnings.
- [ ] Run N=10k for 500 cycles; verify stability, no zero‑sum drift, acceptable latency.


# Taichi Integration Guide

## Required Methods (6 total)

Your Taichi simulator class needs to implement exactly these 6 methods:

```python
import taichi as ti
import numpy as np

@ti.data_oriented
class YourTaichiSim:
    def __init__(self, N, L=1.0):
        """
        Args:
            N: Number of particles
            L: Box half-width (sim runs in [-L, +L]³)
        """
        self.N = N
        self.L = L
        
        # Taichi fields
        self.x = ti.Vector.field(3, dtype=ti.f32, shape=N)  # Positions in [-L, +L]³
        self.r = ti.field(dtype=ti.f32, shape=N)            # Radii
        self.v = ti.Vector.field(3, dtype=ti.f32, shape=N)  # Velocities
        self.frozen = False  # For FREEZE/RESUME
        
    # ========================================================================
    # REQUIRED INTERFACE (called by scheduler)
    # ========================================================================
    
    def get_positions01(self) -> np.ndarray:
        """
        Returns: Nx3 array in [0,1]³ (wrapped, normalized)
        
        Maps internal [-L, +L]³ to [0,1]³ for Geogram bridge.
        """
        x_cpu = self.x.to_numpy()  # Nx3 in [-L, +L]
        x_norm = (x_cpu + self.L) / (2.0 * self.L)  # → [0,1]³
        return x_norm.astype(np.float64)
    
    def get_radii(self) -> np.ndarray:
        """
        Returns: N-length array of radii
        """
        return self.r.to_numpy().astype(np.float64)
    
    def set_radii(self, r_new: np.ndarray):
        """
        Write controller-adjusted radii back to Taichi field.
        
        Args:
            r_new: N-length array from controller
        """
        self.r.from_numpy(r_new.astype(np.float32))
    
    def relax_step(self):
        """
        One RELAX step: compute forces, update velocities, advect positions.
        
        Skip this if frozen (though scheduler calls it every frame).
        """
        if not self.frozen:
            self._compute_forces()
            self._integrate()
    
    def freeze(self):
        """
        Pause dynamics (snapshot for Geogram measurement).
        """
        self.frozen = True
    
    def resume(self):
        """
        Resume dynamics after geometry update.
        """
        self.frozen = False
    
    # ========================================================================
    # YOUR INTERNAL KERNELS (example stubs)
    # ========================================================================
    
    @ti.kernel
    def _compute_forces(self):
        """Your force computation (PBD, Morse, etc.)"""
        pass  # Implement your physics here
    
    @ti.kernel
    def _integrate(self):
        """Velocity integration + position advection + PBC wrap"""
        for i in self.x:
            if not self.frozen:
                self.v[i] += dt * self.f[i] / self.m[i]
                self.x[i] += dt * self.v[i]
                # Wrap to [-L, +L]³
                for d in ti.static(range(3)):
                    if self.x[i][d] > self.L:
                        self.x[i][d] -= 2*self.L
                    elif self.x[i][d] < -self.L:
                        self.x[i][d] += 2*self.L
```

---

## Wiring with Scheduler

```python
from scheduler import FoamScheduler

# Create your Taichi sim
sim = YourTaichiSim(N=5000, L=1.0)

# Wrap with scheduler
scheduler = FoamScheduler(sim, k_freeze=24, target_ms=12.0)

# Main loop (GGUI)
window = ti.ui.Window("Foam", (800, 800))
canvas = window.get_canvas()

while window.running:
    # One scheduler step (RELAX + maybe FREEZE/ADJUST)
    scheduler.step()
    
    # HUD overlay
    hud = scheduler.hud()
    canvas.text(
        f"IQ μ={hud['IQ_mu']:.3f} σ={hud['IQ_sigma']:.3f} | "
        f"t_geom={hud['t_geom_ms']:.1f}ms k={hud['cadence']}",
        pos=(0.02, 0.98),
        color=(1, 1, 1),
        font_size=18
    )
    
    # Draw particles
    canvas.circles(sim.x.to_numpy(), radius=sim.r.to_numpy(), color=(0.8, 0.6, 0.3))
    window.show()
```

---

## Key Points

1. **Coordinate Systems**:
   - Sim stores: `[-L, +L]³` (Taichi GPU fields)
   - Bridge expects: `[0,1]³` (CPU numpy)
   - `get_positions01()` does the mapping

2. **Freeze/Resume**:
   - `freeze()`: Set a flag to skip advection
   - `resume()`: Clear flag after Geogram completes
   - Scheduler calls these automatically

3. **Radii Updates**:
   - Controller computes `r_new` from `V,S,IQ`
   - `set_radii()` writes back to GPU field
   - Next `relax_step()` uses updated radii for forces

4. **Adaptive Cadence**:
   - Scheduler auto-adjusts `k` based on `t_geom`
   - No manual tuning needed
   - HUD shows current `k` and timing

---

## Example: Minimal Working Sim

See `src/sim_stub.py` for a complete CPU-only stub that implements this interface.

To upgrade to real Taichi:
1. Replace `self._positions01` with Taichi fields
2. Implement your force kernels in `_compute_forces()`
3. Add PBC wrapping in `_integrate()`
4. Wire the 6 required methods as shown above

**Done = when your Taichi sim works with `FoamScheduler` exactly like the stub does.**


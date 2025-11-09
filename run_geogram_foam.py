#!/usr/bin/env python
"""
Geogram-Tailed Foam Viewer
Live IQ-driven foam simulator with GGUI visualization
"""

import faulthandler, os, time, numpy as np, sys

# Stability: enable crash dumps + deterministic allocations
faulthandler.enable()
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("PYTHONMALLOC", "debug")

import taichi as ti
ti.init(arch=ti.gpu, kernel_profiler=False)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from scheduler import FoamScheduler


# ============================================================================
# Safe Initialization (jittered grid - no random overlaps)
# ============================================================================

def jittered_grid_positions01(n, seed=0):
    """
    Create N positions in [0,1]³ using jittered grid.
    Avoids random overlaps that cause Geogram degeneracies.
    """
    np.random.seed(seed)
    # Cube root rounding
    m = int(round(n ** (1/3)))
    m = max(4, m)
    gx = np.linspace(0.05, 0.95, m)
    pts = np.stack(np.meshgrid(gx, gx, gx, indexing='ij'), axis=-1).reshape(-1, 3)
    
    if len(pts) < n:
        # Pad with small jittered repeats
        k = n - len(pts)
        jitter = (np.random.rand(k, 3) - 0.5) * (1.0/m) * 0.2
        pts = np.concatenate([pts, pts[:k] + jitter], axis=0)
    
    pts = pts[:n]
    # Small jitter everywhere
    pts += (np.random.rand(n, 3) - 0.5) * (1.0/m) * 0.1
    return np.mod(pts, 1.0)


# ============================================================================
# Minimal Taichi Sim (swap with your real one!)
# ============================================================================

@ti.data_oriented
class TaichiSim:
    """
    Lightweight Taichi sim with toy dynamics.
    Replace this with your real physics!
    """
    def __init__(self, N=1000, L=0.5):
        self.N = N
        self.L = L
        self.x = ti.Vector.field(3, dtype=ti.f32, shape=N)
        self.r = ti.field(dtype=ti.f32, shape=N)
        
        # Init: jittered grid (prevents Geogram degeneracy)
        x0 = jittered_grid_positions01(N).astype(np.float32)
        self.x.from_numpy((x0 - 0.5) * (2.0 * L))   # store in [-L, +L]
        self.r.from_numpy(np.full(N, 0.02, np.float32))
        self._frozen = False

    @ti.kernel
    def step_kernel(self):
        """Toy relax: curl dynamics with brownian motion for spreading"""
        for i in range(self.N):
            p = self.x[i]
            # Curl field (makes particles swirl)
            v = ti.Vector([-p.y, p.x, p.z * 0.5]) * 0.002
            # Deterministic pseudo-random based on position (more stable than ti.random())
            r = ti.Vector([
                ti.sin(p.x * 12.9898 + p.y * 78.233) * 0.003,
                ti.sin(p.y * 12.9898 + p.z * 78.233) * 0.003,
                ti.sin(p.z * 12.9898 + p.x * 78.233) * 0.003
            ])
            p += v + r
            # Wrap to [-L, +L]
            for k in ti.static(range(3)):
                if p[k] > self.L:
                    p[k] -= 2.0 * self.L
                if p[k] < -self.L:
                    p[k] += 2.0 * self.L
            self.x[i] = p

    # ========================================================================
    # REQUIRED INTERFACE (called by scheduler)
    # ========================================================================
    
    def get_positions01(self):
        """Map [-L, +L]³ → [0,1]³ for Geogram"""
        return ((self.x.to_numpy() + self.L) / (2.0 * self.L)).astype(np.float64)

    def get_radii(self):
        """Get radii as numpy array"""
        return self.r.to_numpy().astype(np.float64)

    def set_radii(self, r_new):
        """Write controller-adjusted radii back"""
        self.r.from_numpy(r_new.astype(np.float32))

    def relax_step(self):
        """One physics step"""
        if not self._frozen:
            self.step_kernel()

    def freeze(self):
        """Pause for measurement"""
        self._frozen = True

    def resume(self):
        """Resume after measurement"""
        self._frozen = False


# ============================================================================
# IQ Color Mapping
# ============================================================================

def iq_to_rgb(IQ, lo=0.70, hi=0.90):
    """
    Map IQ to RGB colors:
    - Blue: IQ < 0.70 (low, needs growth)
    - Gray: 0.70 ≤ IQ ≤ 0.90 (good)
    - Red: IQ > 0.90 (too round, shrinking)
    """
    c = np.zeros((len(IQ), 3), np.float32)
    low  = IQ < lo
    mid  = (IQ >= lo) & (IQ <= hi)
    high = IQ > hi
    
    c[low]  = [0.2, 0.5, 1.0]  # Blue
    c[mid]  = [0.7, 0.7, 0.7]  # Gray
    c[high] = [1.0, 0.3, 0.2]  # Red
    
    return c


# ============================================================================
# Main Viewer
# ============================================================================

def main(N=1000, k_freeze=24):
    """
    Launch live IQ-driven foam viewer.
    
    Args:
        N: Number of particles (≤1000 recommended)
        k_freeze: Geometry update cadence (frames)
    """
    print("\n" + "="*70)
    print("🧼 Geogram-Tailed Foam Viewer")
    print("="*70)
    print(f"\nConfig:")
    print(f"  N = {N}")
    print(f"  k_freeze = {k_freeze} (adaptive)")
    print(f"  Batching: max_chunk=1000")
    print(f"\nColors:")
    print(f"  🔵 Blue = Low IQ (<0.70) → Growing")
    print(f"  ⚪ Gray = Good IQ (0.70-0.90)")
    print(f"  🔴 Red = High IQ (>0.90) → Shrinking")
    print("\nStarting...\n")
    
    # Create sim (swap with your real Taichi sim here!)
    sim = TaichiSim(N=N)
    
    # Wrap with scheduler
    sched = FoamScheduler(sim, k_freeze=k_freeze)

    # CRITICAL: Allocate Taichi fields for rendering (GGUI needs fields, not NumPy!)
    x_render = ti.Vector.field(3, dtype=ti.f32, shape=N)
    c_render = ti.Vector.field(3, dtype=ti.f32, shape=N)

    # GGUI setup
    window = ti.ui.Window(f"Geogram Foam — N={N}", (1280, 720))
    canvas = window.get_canvas()
    scene  = window.get_scene()
    camera = ti.ui.Camera()
    camera.position(1.5, 1.2, 1.8)  # Pull back to see full cube
    camera.lookat(0.0, 0.0, 0.0)
    camera.fov(45)

    sphere_radius = 0.04  # Larger for visibility in [-1,1] space

    t0 = time.time()
    frame = 0
    
    # Debug: Check initial positions
    X_init = sim.x.to_numpy()
    print(f"\nDEBUG: Position stats at start:")
    print(f"  X shape: {X_init.shape}")
    print(f"  X range: [{X_init.min():.3f}, {X_init.max():.3f}]")
    print(f"  X mean: ({X_init.mean(axis=0)})")
    print(f"  X std: ({X_init.std(axis=0)})")
    
    while window.running:
        # One scheduler step (RELAX + maybe FREEZE/ADJUST)
        sched.step()

        # Get positions: [-L, +L] → [-1, 1] for rendering
        # sim.L = 0.5, so sim.x is in [-0.5, +0.5]
        # Scale by 2 to get [-1, +1] for better camera view
        X_np = (sim.x.to_numpy() / sim.L).astype(np.float32)  # [-1, +1]
        x_render.from_numpy(X_np)
        
        # Get colors
        IQ = sched.get_last_IQ()
        if IQ is None:
            colors = np.full((sim.N, 3), 0.6, dtype=np.float32)
        else:
            colors = iq_to_rgb(IQ.astype(np.float32))
        
        # Ensure correct shape and dtype
        colors = np.asarray(colors, dtype=np.float32)
        assert colors.shape == (sim.N, 3), f"Color shape mismatch: {colors.shape}"
        c_render.from_numpy(colors)

        # Render scene
        scene.set_camera(camera)
        scene.ambient_light((0.8, 0.8, 0.8))
        scene.point_light(pos=(2, 2, 2), color=(1, 1, 1))
        
        # Draw reference cube (optional, for orientation)
        # scene.mesh(vertices, indices, color=(0.2, 0.2, 0.2))  # Uncomment if you want cube outline
        
        # CRITICAL: Pass Taichi fields, not NumPy arrays!
        scene.particles(x_render, radius=sphere_radius, per_vertex_color=c_render)

        canvas.scene(scene)

        # HUD overlay
        hud = sched.hud()
        txt = (f"IQ μ={hud['IQ_mu']:.3f} σ={hud['IQ_sigma']:.3f} | "
               f"k={hud['cadence']} | pending={hud['geom_pending']} | "
               f"t_geom={hud['t_geom_ms']:.1f}ms")
        
        window.GUI.begin("HUD", 0.01, 0.01, 0.5, 0.08)
        window.GUI.text(txt)
        window.GUI.end()

        window.show()
        frame += 1
        
        # Debug: print first few frames
        if frame <= 5:
            print(f"Frame {frame}: X_np range=[{X_np.min():.3f}, {X_np.max():.3f}], "
                  f"unique={len(np.unique(X_np, axis=0))}, "
                  f"colors unique={len(np.unique(colors, axis=0))}")
        
        # Optional: print status every 100 frames
        if frame % 100 == 0:
            elapsed = time.time() - t0
            fps = frame / elapsed
            print(f"Frame {frame}: FPS={fps:.1f}, {txt}")


if __name__ == "__main__":
    # TEST: N=100 to diagnose if crash is N-related
    # Was crashing at N=1000 after ~1600 frames
    main(N=100, k_freeze=24)


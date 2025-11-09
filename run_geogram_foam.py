#!/usr/bin/env python
"""
Geogram-Tailed Foam Viewer
Live IQ-driven foam simulator with GGUI visualization
"""

import os, time, numpy as np, sys, json

# PERFORMANCE: Disable debug tools for production runs
os.environ.pop("PYTHONMALLOC", None)  # Remove debug malloc if set
os.environ.setdefault("OMP_NUM_THREADS", "1")

import taichi as ti
ti.init(arch=ti.gpu, kernel_profiler=False)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from scheduler import FoamScheduler


# ============================================================================
# Settings Management
# ============================================================================

CONFIG_FILE = "foam_settings.json"

DEFAULT_SETTINGS = {
    "N": 100,  # Start safe, slider goes to 10k
    "k_freeze": 24,
    "auto_cadence": True,
    "IQ_min": 0.65,
    "IQ_max": 0.85,
    "beta_grow": 1.5,  # Increased from 1.0 for more dramatic size changes
    "beta_shrink": 1.2,  # Increased from 0.7 for more dramatic size changes
}

# Memory safety check
MAX_SAFE_N = 10000  # Hard limit to prevent system crashes

def load_settings():
    """Load settings from JSON file, or return defaults"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                settings = json.load(f)
                print(f"✓ Loaded settings from {CONFIG_FILE}")
                return settings
        except Exception as e:
            print(f"⚠ Failed to load {CONFIG_FILE}: {e}")
    return DEFAULT_SETTINGS.copy()

def save_settings(settings):
    """Save settings to JSON file"""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(settings, f, indent=2)
        print(f"✓ Saved settings to {CONFIG_FILE}")
    except Exception as e:
        print(f"⚠ Failed to save {CONFIG_FILE}: {e}")


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
        """
        Toy relax with STRONG radius-dependent dynamics.
        Larger radius → more aggressive spreading (visible size changes!)
        """
        for i in range(self.N):
            p = self.x[i]
            r = self.r[i]
            
            # STRONG radius-dependent diffusion (5x stronger than before!)
            # This makes radius changes VERY visible
            diffusion_strength = r * 0.5  # Was 0.1, now 0.5 for dramatic effect
            
            # Deterministic pseudo-random based on position
            noise = ti.Vector([
                ti.sin(p.x * 12.9898 + p.y * 78.233),
                ti.sin(p.y * 12.9898 + p.z * 78.233),
                ti.sin(p.z * 12.9898 + p.x * 78.233)
            ]) * diffusion_strength
            
            # Radius-dependent curl (larger cells push neighbors more)
            curl_strength = r * 0.01  # NEW: curl also scales with radius
            curl = ti.Vector([-p.y, p.x, p.z * 0.3]) * curl_strength
            
            # Update position
            p += noise + curl
            
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

def main(settings=None):
    """
    Launch live IQ-driven foam viewer.
    
    Args:
        settings: Dict with N, k_freeze, IQ_min, IQ_max, beta_grow, beta_shrink, auto_cadence
    """
    if settings is None:
        settings = load_settings()
    
    N = settings.get("N", 100)
    k_freeze = settings.get("k_freeze", 24)
    
    # Safety check to prevent system crashes
    if N > MAX_SAFE_N:
        print(f"\n⚠️  ERROR: N={N} exceeds MAX_SAFE_N={MAX_SAFE_N}")
        print(f"⚠️  Clamping to N={MAX_SAFE_N} to prevent system crash")
        N = MAX_SAFE_N
        settings["N"] = N
    
    print("\n" + "="*70)
    print("🧼 Geogram-Tailed Foam Viewer")
    print("="*70)
    print(f"\nConfig:")
    print(f"  N = {N}")
    print(f"  k_freeze = {k_freeze}")
    print(f"  IQ band = [{settings.get('IQ_min', 0.65):.2f}, {settings.get('IQ_max', 0.85):.2f}]")
    print(f"  Batching: max_chunk=1000")
    print(f"\nColors:")
    print(f"  🔵 Blue = Low IQ → Growing")
    print(f"  ⚪ Gray = Good IQ → Stable")
    print(f"  🔴 Red = High IQ → Shrinking")
    print("\nStarting...\n")
    
    # Create sim (swap with your real Taichi sim here!)
    sim = TaichiSim(N=N)
    
    # Wrap with scheduler
    sched = FoamScheduler(sim, k_freeze=k_freeze)
    
    # Apply loaded settings to controller
    sched.controller.set_iq_band(settings.get("IQ_min", 0.65), settings.get("IQ_max", 0.85))
    sched.controller.set_beta_grow(settings.get("beta_grow", 1.0))
    sched.controller.set_beta_shrink(settings.get("beta_shrink", 0.7))
    
    # Apply cadence setting
    if not settings.get("auto_cadence", True):
        sched.set_k_freeze(k_freeze)
    else:
        sched.set_k_freeze(None)  # Auto

    # CRITICAL: Allocate Taichi fields for rendering (GGUI needs fields, not NumPy!)
    x_render = ti.Vector.field(3, dtype=ti.f32, shape=N)
    c_render = ti.Vector.field(3, dtype=ti.f32, shape=N)

    # GGUI setup
    window = ti.ui.Window(f"Geogram Foam — N={N}", (1280, 720))
    canvas = window.get_canvas()
    canvas.set_background_color((0.05, 0.05, 0.1))
    scene  = window.get_scene()
    camera = ti.ui.Camera()
    
    # Custom orbit camera state
    cam_theta = 0.8  # Azimuthal angle (around vertical axis)
    cam_phi = 0.6    # Polar angle (up-down)
    cam_distance = 2.5  # Distance from origin
    cam_center = np.array([0.0, 0.0, 0.0])  # Look-at point
    
    def update_camera(theta, phi, distance):
        """Update camera position for orbit around center"""
        x = distance * np.sin(phi) * np.cos(theta)
        y = distance * np.cos(phi)
        z = distance * np.sin(phi) * np.sin(theta)
        camera.position(x, y, z)
        camera.lookat(cam_center[0], cam_center[1], cam_center[2])
        camera.fov(45)
    
    update_camera(cam_theta, cam_phi, cam_distance)
    
    # Mouse tracking for orbit
    last_mouse_x, last_mouse_y = None, None

    sphere_radius = 0.04  # Larger for visibility in [-1,1] space

    t0 = time.time()
    frame = 0
    
    # GUI update throttle (update VALUES every N frames, but always SHOW panel)
    gui_update_interval = 10  # Update text/sliders every 10 frames
    
    # Pre-allocate buffers (PERFORMANCE: reuse, don't recreate)
    colors_buf = np.full((N, 3), 0.6, dtype=np.float32)  # Reusable color buffer
    
    # Cached GUI values (updated periodically)
    cached_hud = {"IQ_mu": 0.0, "IQ_sigma": 0.0, "geom_pending": False, 
                  "cadence": 24, "t_geom_ms": 0.0, "auto_cadence": True}
    cached_pct = (0.0, 0.0, 0.0)  # (low, mid, high)
    
    # Restart state
    restart_requested = False
    new_N = N
    
    # Pause state (toggled with SPACEBAR)
    paused = False
    
    while window.running and not restart_requested:
        # Handle keyboard input
        if window.get_event(ti.ui.PRESS):
            if window.event.key == ti.ui.SPACE:
                paused = not paused
                print(f"{'⏸ PAUSED' if paused else '▶ RESUMED'}")
        
        # === Camera Controls ===
        
        # SHIFT + drag = orbit rotate
        mouse_x, mouse_y = window.get_cursor_pos()
        shift_held = window.is_pressed(ti.ui.SHIFT)
        left_button = window.is_pressed(ti.ui.LMB)
        
        if shift_held and left_button:
            if last_mouse_x is not None:
                dx = mouse_x - last_mouse_x
                dy = mouse_y - last_mouse_y
                
                cam_theta -= dx * 3.0  # Horizontal rotation
                cam_phi = np.clip(cam_phi - dy * 3.0, 0.1, np.pi - 0.1)  # Vertical
                
                update_camera(cam_theta, cam_phi, cam_distance)
            
            last_mouse_x, last_mouse_y = mouse_x, mouse_y
        else:
            last_mouse_x, last_mouse_y = None, None
        
        # Zoom with Q/E keys (easy to reach!)
        if window.is_pressed('q'):
            cam_distance *= 1.02  # Zoom out
            cam_distance = np.clip(cam_distance, 0.5, 10.0)
            update_camera(cam_theta, cam_phi, cam_distance)
        if window.is_pressed('e'):
            cam_distance *= 0.98  # Zoom in
            cam_distance = np.clip(cam_distance, 0.5, 10.0)
            update_camera(cam_theta, cam_phi, cam_distance)
        
        # Pan with WASD (moves look-at center)
        pan_speed = 0.01
        if window.is_pressed('w'):
            cam_center[1] += pan_speed  # Pan up
            update_camera(cam_theta, cam_phi, cam_distance)
        if window.is_pressed('s'):
            cam_center[1] -= pan_speed  # Pan down
            update_camera(cam_theta, cam_phi, cam_distance)
        if window.is_pressed('a'):
            cam_center[0] -= pan_speed  # Pan left
            update_camera(cam_theta, cam_phi, cam_distance)
        if window.is_pressed('d'):
            cam_center[0] += pan_speed  # Pan right
            update_camera(cam_theta, cam_phi, cam_distance)
        
        # One scheduler step (RELAX + maybe FREEZE/ADJUST) - skip if paused
        if not paused:
            sched.step()

        # Get positions: [-L, +L] → [-1, 1] for rendering (OPTIMIZED: no copy if not needed)
        X_np = (sim.x.to_numpy() / sim.L).astype(np.float32)
        x_render.from_numpy(X_np)
        
        # Get colors (OPTIMIZED: reuse buffer, update in-place)
        IQ = sched.get_last_IQ()
        if IQ is not None:
            colors_buf[:] = iq_to_rgb(IQ.astype(np.float32))
        else:
            colors_buf[:] = 0.6  # Gray when no IQ yet
        
        c_render.from_numpy(colors_buf)
        
        # Render scene (camera updated above with custom orbit)
        scene.set_camera(camera)
        scene.ambient_light((0.8, 0.8, 0.8))
        scene.point_light(pos=(2, 2, 2), color=(1, 1, 1))
        
        # Draw reference cube (optional, for orientation)
        # scene.mesh(vertices, indices, color=(0.2, 0.2, 0.2))  # Uncomment if you want cube outline
        
        # CRITICAL: Pass Taichi fields, not NumPy arrays!
        scene.particles(x_render, radius=sphere_radius, per_vertex_color=c_render)

        canvas.scene(scene)

        # ===== CONTROL PANEL (ALWAYS VISIBLE, values updated periodically) =====
        # Update cached values every N frames to reduce overhead
        if frame % gui_update_interval == 0:
            cached_hud = sched.hud()
            
            # Compute IQ distribution stats (OPTIMIZED: boolean masks, no np.unique)
            if IQ is not None:
                IQ_min_current = sched.controller.IQ_min
                IQ_max_current = sched.controller.IQ_max
                pct_low  = float(np.mean(IQ < IQ_min_current) * 100)
                pct_mid  = float(np.mean((IQ >= IQ_min_current) & (IQ <= IQ_max_current)) * 100)
                pct_high = float(np.mean(IQ > IQ_max_current) * 100)
                cached_pct = (pct_low, pct_mid, pct_high)
        
        # Draw GUI EVERY frame (no flicker), using cached values
        hud = cached_hud
        pct_low, pct_mid, pct_high = cached_pct
        
        window.GUI.begin("Control Panel", 0.01, 0.01, 0.30, 0.80)
        
        # --- Simulation Section ---
        window.GUI.text("[ Simulation ]")
        
        # N input and restart button
        new_N = window.GUI.slider_int("N particles", new_N, 50, 10000)
        
        # Safety warning for large N
        if new_N > 5000:
            window.GUI.text("⚠ WARNING: N>5k may be unstable!")
        
        if window.GUI.button("Restart with New N"):
            restart_requested = True
        
        # Save/Load buttons
        if window.GUI.button("Save Settings"):
            current_settings = {
                "N": new_N,
                "k_freeze": hud['cadence'],
                "auto_cadence": hud['auto_cadence'],
                "IQ_min": sched.controller.IQ_min,
                "IQ_max": sched.controller.IQ_max,
                "beta_grow": sched.controller.beta_grow,
                "beta_shrink": sched.controller.beta_shrink,
            }
            save_settings(current_settings)
        
        if window.GUI.button("Load Defaults"):
            # Load default settings and trigger restart
            settings.update(DEFAULT_SETTINGS)
            new_N = settings["N"]
            sched.controller.set_iq_band(settings["IQ_min"], settings["IQ_max"])
            sched.controller.set_beta_grow(settings["beta_grow"])
            sched.controller.set_beta_shrink(settings["beta_shrink"])
            if settings["auto_cadence"]:
                sched.set_k_freeze(None)
            else:
                sched.set_k_freeze(settings["k_freeze"])
        
        window.GUI.text("")  # Spacer
        
        # === Relaxation Time Control ===
        window.GUI.text("[ Relaxation / Loop Time ]")
        
        auto_cadence = hud['auto_cadence']
        k_current = hud['cadence']
        
        # Show current cycle time
        window.GUI.text(f"Frames per cycle: {k_current}")
        
        # Calculate time in seconds (time particles have to reposition)
        elapsed = time.time() - t0
        fps = frame / max(elapsed, 1e-6)
        relax_time_sec = k_current / max(fps, 1.0)
        window.GUI.text(f"≈ {relax_time_sec:.2f} sec to relax")
        window.GUI.text("")
        
        # Manual slider (only if auto is off)
        if auto_cadence:
            window.GUI.text("(Auto: adjusts for target FPS)")
        else:
            k_new = window.GUI.slider_int("Manual k_freeze", k_current, 8, 200)
            if k_new != k_current:
                sched.set_k_freeze(k_new)
        
        # Auto cadence checkbox
        auto_new = window.GUI.checkbox("Auto cadence", auto_cadence)
        if auto_new != auto_cadence:
            sched.set_k_freeze(None if auto_new else k_current)
        
        window.GUI.text("")  # Spacer
        
        # --- IQ Band Section ---
        window.GUI.text("[ IQ Band ]")
        
        IQ_min = sched.controller.IQ_min
        IQ_max = sched.controller.IQ_max
        
        IQ_min_new = window.GUI.slider_float("IQ_min", IQ_min, 0.40, 0.95)
        IQ_max_new = window.GUI.slider_float("IQ_max", IQ_max, 0.45, 0.99)
        
        # Apply if changed (with validation)
        if IQ_min_new != IQ_min or IQ_max_new != IQ_max:
            sched.controller.set_iq_band(IQ_min_new, IQ_max_new)
        
        window.GUI.text("")  # Spacer
        
        # --- Rates Section ---
        window.GUI.text("[ Rates ]")
        
        beta_grow = sched.controller.beta_grow
        beta_shrink = sched.controller.beta_shrink
        
        beta_grow_new = window.GUI.slider_float("beta_grow", beta_grow, 0.0, 2.0)
        beta_shrink_new = window.GUI.slider_float("beta_shrink", beta_shrink, 0.0, 2.0)
        
        if beta_grow_new != beta_grow:
            sched.controller.set_beta_grow(beta_grow_new)
        if beta_shrink_new != beta_shrink:
            sched.controller.set_beta_shrink(beta_shrink_new)
        
        window.GUI.text("")  # Spacer
        
        # --- Stats Section ---
        window.GUI.text("[ Stats ]")
        window.GUI.text(f"IQ μ: {hud['IQ_mu']:.3f}")
        window.GUI.text(f"IQ σ: {hud['IQ_sigma']:.3f}")
        window.GUI.text(f"Below/Within/Above: {pct_low:.0f}% / {pct_mid:.0f}% / {pct_high:.0f}%")
        window.GUI.text("")
        
        # Performance
        elapsed = time.time() - t0
        fps = frame / max(elapsed, 1e-6)
        window.GUI.text(f"FPS: {fps:.1f}")
        window.GUI.text(f"t_geom: {hud['t_geom_ms']:.1f} ms")
        window.GUI.text(f"Frame: {frame}")
        window.GUI.text(f"Pending: {hud['geom_pending']}")
        window.GUI.text(f"Status: {'⏸ PAUSED' if paused else '▶ Running'}")
        
        window.GUI.text("")
        window.GUI.text("[ Controls ]")
        window.GUI.text("SPACEBAR: Pause/Resume")
        window.GUI.text("")
        window.GUI.text("Camera:")
        window.GUI.text("  • SHIFT + drag = orbit rotate")
        window.GUI.text("  • Q/E = zoom out/in")
        window.GUI.text("  • WASD = pan up/left/down/right")
        
        window.GUI.end()
        # ===== END CONTROL PANEL =====

        window.show()
        frame += 1
        
        # Print status every 500 frames (PERFORMANCE: reduce TTY back-pressure)
        if frame % 500 == 0:
            elapsed = time.time() - t0
            fps = frame / elapsed
            print(f"Frame {frame}: FPS={fps:.1f}, IQ μ={hud['IQ_mu']:.3f} σ={hud['IQ_sigma']:.3f} | "
                  f"k={hud['cadence']} | t_geom={hud['t_geom_ms']:.1f}ms")
    
    # === After window closes ===
    # Save current settings before exit/restart
    final_settings = {
        "N": new_N if restart_requested else N,
        "k_freeze": hud['cadence'],
        "auto_cadence": hud['auto_cadence'],
        "IQ_min": sched.controller.IQ_min,
        "IQ_max": sched.controller.IQ_max,
        "beta_grow": sched.controller.beta_grow,
        "beta_shrink": sched.controller.beta_shrink,
    }
    save_settings(final_settings)
    
    # Return restart flag and new N
    return restart_requested, new_N


if __name__ == "__main__":
    # Load settings and run, with restart loop
    settings = load_settings()
    
    while True:
        restart, new_N = main(settings)
        if not restart:
            break  # User closed window normally
        
        # Restart with new N
        print(f"\n🔄 Restarting with N={new_N}...\n")
        settings["N"] = new_N


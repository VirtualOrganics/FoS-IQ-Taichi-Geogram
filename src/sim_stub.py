# sim_stub.py
# HARDENED: Guaranteed C-order, owned buffers in getters

import numpy as np


def jittered_grid_positions01(n, seed=42):
    """Generate jittered grid positions (avoids random overlaps that crash Geogram)"""
    np.random.seed(seed)
    m = int(round(n ** (1/3)))
    m = max(4, m)
    gx = np.linspace(0.05, 0.95, m)
    pts = np.stack(np.meshgrid(gx, gx, gx, indexing='ij'), axis=-1).reshape(-1,3)
    if len(pts) < n:
        k = n - len(pts)
        jitter = (np.random.rand(k,3) - 0.5) * (1.0/m) * 0.2
        pts = np.concatenate([pts, pts[:k] + jitter], axis=0)
    pts = pts[:n]
    pts += (np.random.rand(n,3) - 0.5) * (1.0/m) * 0.1
    return np.mod(pts, 1.0)


class TaichiSimStub:
    """
    HARDENED stub: Always returns owned, C-contiguous arrays.
    NO .ravel() views, NO aliasing.
    """
    
    def __init__(self, N=100, box_size=1.0):
        """
        Initialize stub with N particles.
        
        Args:
            N: number of particles
            box_size: domain size (for periodic [0, box_size]³)
        """
        self.N = N
        self.box_size = box_size
        
        # Initialize positions with jittered grid (SAFE - avoids Geogram degeneracies)
        self.positions = jittered_grid_positions01(N, seed=42)
        
        # Initialize radii (typical foam: mean spacing ~ 0.02-0.03)
        mean_r = 0.02
        self.radii = mean_r + 0.01 * np.random.randn(N)
        self.radii = np.clip(self.radii, 0.01, 0.05)  # clamp to reasonable range
        
        # Velocities (for RELAX step)
        self.velocities = np.zeros((N, 3))
        
        self.frozen = False
        self.relax_step_count = 0
        
        print(f"✓ TaichiSimStub initialized: N={N}, box_size={box_size}")
    
    def get_positions01(self):
        """
        Return positions in [0,1]³ coordinate system.
        GUARANTEED: (N, 3) C-contiguous float64, OWNED (not a view).
        """
        # Ensure C-order, owned buffer - NO views
        return np.ascontiguousarray(self.positions, dtype=np.float64)
    
    def get_radii(self):
        """
        Return radii array.
        GUARANTEED: (N,) C-contiguous float64, OWNED (not a view).
        """
        # Ensure C-order, owned buffer - NO views
        return np.ascontiguousarray(self.radii, dtype=np.float64)
    
    def set_radii(self, r_new):
        """Update radii from controller"""
        self.radii[:] = r_new
    
    def relax_step(self):
        """
        Single RELAX step (placeholder).
        Real implementation: Taichi GPU forces + PBD
        """
        if self.frozen:
            return  # no movement during FREEZE
        
        # Placeholder: random walk + periodic wrap
        self.positions += 0.001 * np.random.randn(self.N, 3)
        self.positions = self.positions % self.box_size
        
        self.relax_step_count += 1
    
    def freeze(self):
        """Pause particle advection for FREEZE snapshot"""
        self.frozen = True
    
    def resume(self):
        """Resume particle advection after FREEZE"""
        self.frozen = False
    
    def stats(self):
        """Return simulation stats"""
        return {
            "N": self.N,
            "relax_steps": self.relax_step_count,
            "mean_r": float(self.radii.mean()),
            "std_r": float(self.radii.std()),
        }

# sim_stub.py
# Minimal Taichi simulator stub for testing scheduler integration
# This demonstrates the required interface - replace with real Taichi implementation

import numpy as np


class TaichiSimStub:
    """
    Minimal stub showing required interface for FoamScheduler.
    
    Required methods:
        get_positions01() -> np.ndarray (N, 3) in [0,1]³
        get_radii() -> np.ndarray (N,)
        set_radii(r_new: np.ndarray)
        relax_step()
        freeze()
        resume()
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
        
        # Initialize positions randomly in [0,1]³
        np.random.seed(42)
        self.positions = np.random.rand(N, 3)
        
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
        """Return positions in [0,1]³ coordinate system"""
        return self.positions.copy()
    
    def get_radii(self):
        """Return radii (numpy view)"""
        return self.radii
    
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


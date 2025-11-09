# scheduler.py
# Cadence + FREEZE/RESUME glue

import numpy as np
# from geom_worker import GeomWorker  # Threaded version
from geom_worker_sync import GeomWorkerSync as GeomWorker  # Single-threaded test
from controller import apply_iq_banded_controller


def _sanitize(P01, r, eps=1e-9):
    """
    Sanitize inputs before Geogram calls to prevent edge cases:
    - Wrap positions to [0, 1)
    - Clip radii to safe range
    - De-duplicate exact overlaps with tiny jitter
    """
    # Wrap to [0, 1) with epsilon safety
    P01 = np.mod(P01, 1.0)
    P01[P01 >= 1.0] = 1.0 - eps
    
    # Clip radii to prevent zero/negative
    r = np.clip(r, 1e-6, 1.0)
    
    # Check for exact duplicates → add tiny jitter
    uniq = np.unique(P01.view([('', P01.dtype)]*3)).size
    if uniq < len(P01):
        P01 = np.mod(P01 + (np.random.rand(*P01.shape) - 0.5) * eps, 1.0)
    
    # Ensure C-contiguous float64
    return (np.require(P01, np.float64, ['C']), 
            np.require(r, np.float64, ['C']))


class FoamScheduler:
    def __init__(self, taichi_sim, k_freeze=24, target_ms=12.0):
        """
        Initialize scheduler.
        
        Args:
            taichi_sim: Taichi simulator with required methods
            k_freeze: FREEZE cadence (frames between geometry updates)
            target_ms: Target t_geom for adaptive cadence (~80 FPS headroom)
        """
        self.sim = taichi_sim
        self.k = k_freeze
        self.target_ms = target_ms
        self.frame = 0
        self.worker = GeomWorker()
        self.pending = False
        self.last_IQ = None
        self.last_IQ_stats = (0.0, 0.0)
        self.last_t_geom_ms = 0.0
        
        # Worker recycling (prevents long-run state buildup)
        self.results_seen = 0
        self.recycle_every = 300  # Recycle worker after 300 geometry results

    @staticmethod
    def wrap01(x):
        """Wrap positions to [0,1]³ (assumes already normalized upstream)"""
        return x - np.floor(x)

    def step(self):
        """
        Call each render tick. Runs RELAX every frame.
        Every k frames: FREEZE -> fire Geogram job (non-blocking).
        When result returns: ADJUST radii, then keep RELAXing.
        """
        # Always run one RELAX step
        self.sim.relax_step()

        # 1) Try collect geometry result if any
        if self.pending:
            got = self.worker.try_result()
            if got is not None:
                V, S, FSC, flags, t_ms = got
                r = self.sim.get_radii()                     # numpy view
                r_new, IQ = apply_iq_banded_controller(r, V, S, flags)
                self.sim.set_radii(r_new)                    # write back
                self.last_IQ = IQ                            # store for coloring
                self.last_IQ_stats = (float(IQ.mean()), float(IQ.std()))
                self.last_t_geom_ms = float(t_ms)
                
                # Adaptive cadence with better backoff thresholds
                if t_ms > 32 and self.k < 96:      # Heavy → relax cadence
                    self.k += 8
                elif t_ms < 12 and self.k > 16:    # Cheap → tighten a bit
                    self.k -= 4
                
                self.pending = False
                
                # Worker recycling: prevent long-run state buildup
                self.results_seen += 1
                if self.results_seen % self.recycle_every == 0:
                    self.worker = GeomWorker()  # Safe worker reset

        # 2) Fire new geometry job on cadence, if none pending
        if (self.frame % self.k == 0) and not self.pending:
            self.sim.freeze()                                # pause particle advection
            P = self.sim.get_positions01()                   # Nx3, already [0,1]³
            r = self.sim.get_radii()
            
            # Sanitize inputs before Geogram call (prevent edge cases)
            P, r = _sanitize(P, r)
            W = r*r                                         # weights = r²
            
            ok = self.worker.try_request(P, W)               # P is Nx3, W is N
            self.sim.resume()
            self.pending = ok

        self.frame += 1

    def hud(self):
        """Return HUD metrics dictionary"""
        mu, sigma = self.last_IQ_stats
        return {
            "IQ_mu": mu,
            "IQ_sigma": sigma,
            "geom_pending": self.pending,
            "cadence": self.k,
            "t_geom_ms": self.last_t_geom_ms,
        }
    
    def get_last_IQ(self):
        """Return last computed IQ array (for coloring)"""
        return self.last_IQ


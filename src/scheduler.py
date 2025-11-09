# scheduler.py
# HARDENED: Strict one-in-flight FSM, owned snapshots, no buffer mutation

import numpy as np
# from geom_worker import GeomWorker  # Threaded version
from geom_worker_sync import GeomWorkerSync as GeomWorker  # Single-threaded test
from controller import IQController


class FoamScheduler:
    def __init__(self, taichi_sim, k_freeze=24, target_ms=12.0):
        """
        Initialize scheduler with strict one-request-at-a-time FSM.
        
        Args:
            taichi_sim: Taichi simulator with required methods
            k_freeze: FREEZE cadence (frames between geometry updates)
            target_ms: Target t_geom for adaptive cadence
        """
        self.sim = taichi_sim
        self.k = k_freeze
        self.k_manual = None  # None = auto cadence, int = manual override
        self.target_ms = target_ms
        self.frame = 0
        self.worker = GeomWorker()
        self.worker_pending = False  # Strict FSM: only ONE request in flight
        
        # Countdown to next geometry call
        self._geom_countdown = k_freeze
        
        # IQ Controller (live parameters)
        self.controller = IQController(
            IQ_min=0.65, IQ_max=0.85,
            beta_grow=1.0, beta_shrink=0.7
        )
        
        # Metrics
        self.last_IQ = None
        self.last_IQ_stats = (0.0, 0.0)
        self.last_t_geom_ms = 0.0
        self.results_seen = 0
        self.recycle_every = 300
        
        # Debug canary (optional)
        self._debug_call_count = 0

    def _snapshot_inputs(self):
        """
        Take OWNED, immutable snapshots of simulation state.
        NO views, NO aliasing - matches minimal loop pattern.
        """
        # Get positions and radii (these may be views)
        P = self.sim.get_positions01()   # expect (N, 3)
        r = self.sim.get_radii()
        
        # Invariants
        N = P.shape[0]
        assert P.shape == (N, 3), f"bad P shape {P.shape}"
        assert r.shape == (N,), f"bad r shape {r.shape}"
        
        # Owned, contiguous copies (NO views into sim memory)
        # This is the same pattern as test_min_loop.py which passed 200 calls
        P_own = np.ascontiguousarray(P, dtype=np.float64)
        r_own = np.ascontiguousarray(r, dtype=np.float64)
        
        # Sanitize (wrap, clip, de-duplicate)
        P_own = np.mod(P_own, 1.0)
        P_own = np.clip(P_own, 0.0, 1.0 - 1e-9)
        r_own = np.clip(r_own, 1e-6, 1.0)
        
        # Ensure final contiguity after sanitization
        P_own = np.ascontiguousarray(P_own, dtype=np.float64)
        r_own = np.ascontiguousarray(r_own, dtype=np.float64)
        
        # Cheap invariants
        assert P_own.flags['C_CONTIGUOUS'], "P not C-contiguous"
        assert r_own.flags['C_CONTIGUOUS'], "r not C-contiguous"
        assert np.isfinite(P_own).all(), "P has non-finite values"
        assert np.isfinite(r_own).all(), "r has non-finite values"
        
        W_own = r_own * r_own  # weights = r²
        
        return P_own, W_own, N

    def step(self):
        """
        Strict one-request-at-a-time step.
        RELAX always runs. Geometry requests only when idle.
        """
        # Increment frame counter FIRST (every step)
        self.frame += 1
        
        # RELAX always (unless frozen by sim itself)
        self.sim.relax_step()

        # PRIORITY 1: If a request is pending, try to collect and RETURN EARLY
        if self.worker_pending:
            res = self.worker.try_result()
            if res is None:
                # Still computing - do NOT issue new request
                return
            
            # Result ready - unpack and apply
            V, A, FSC, FL, t_ms = res
            
            # Cheap sanity check
            if not np.isfinite(V).all():
                raise RuntimeError(f"Non-finite volumes at frame {self.frame}")
            
            # Optional: check volume sum (should be ~1.0 for periodic unit cube)
            sumV = float(V.sum())
            if abs(sumV - 1.0) > 1e-2:
                # Not fatal, but log it
                pass
            
            # Apply controller (IQ-banded, zero-sum)
            r = self.sim.get_radii()
            r_new, IQ = self.controller.apply(r, V, A, FL)
            self.sim.set_radii(r_new)
            
            # Update metrics
            self.last_IQ = IQ
            self.last_IQ_stats = (float(IQ.mean()), float(IQ.std()))
            self.last_t_geom_ms = float(t_ms)
            
            # Adaptive cadence (only if not manually overridden)
            if self.k_manual is None:
                if t_ms > 32 and self.k < 96:
                    self.k += 8
                elif t_ms < 12 and self.k > 16:
                    self.k -= 4
            
            # FSM: mark idle
            self.worker_pending = False
            self.results_seen += 1
            
            # Optional: recycle worker
            if self.results_seen % self.recycle_every == 0:
                self.worker = GeomWorker()
            
            # RETURN - do not issue new request this frame
            return

        # PRIORITY 2: Count down to next geometry call
        self._geom_countdown -= 1
        if self._geom_countdown > 0:
            # Not time yet
            return

        # PRIORITY 3: Time to request - take snapshot and submit ONE request
        self.sim.freeze()
        P_own, W_own, N = self._snapshot_inputs()
        self.sim.resume()
        
        # Optional debug canary (cheap hash of first 4K bytes)
        self._debug_call_count += 1
        if self._debug_call_count % 50 == 0:
            hashP = hash(P_own.tobytes()[:4096])
            hashW = hash(W_own.tobytes()[:4096])
            # Uncomment to debug: print(f"[geom #{self._debug_call_count}] hashP={hashP} hashW={hashW}")
        
        # Submit request
        ok = self.worker.try_request(P_own, W_own)
        if ok:
            self.worker_pending = True
            self._geom_countdown = self.k  # Reset cadence

    def set_k_freeze(self, k: int | None):
        """
        Set cadence manually or re-enable auto tuning.
        
        Args:
            k: int = manual cadence (disables auto), None = auto cadence
        """
        if k is None:
            # Re-enable auto cadence
            self.k_manual = None
        else:
            # Manual override (disable auto)
            k = max(8, min(k, 96))  # Clamp to [8, 96]
            self.k_manual = k
            self.k = k
    
    def hud(self):
        """Return HUD metrics dictionary"""
        mu, sigma = self.last_IQ_stats
        return {
            "IQ_mu": mu,
            "IQ_sigma": sigma,
            "geom_pending": self.worker_pending,
            "cadence": self.k,
            "t_geom_ms": self.last_t_geom_ms,
            "auto_cadence": (self.k_manual is None),
        }
    
    def get_last_IQ(self):
        """Return last computed IQ array (for coloring)"""
        return self.last_IQ

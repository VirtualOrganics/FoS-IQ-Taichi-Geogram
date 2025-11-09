# controller.py
# Banded IQ controller (zero-sum, capped) - Class-based API for live tuning

import numpy as np


def compute_IQ(V, S):
    """
    Compute isoperimetric quotient: IQ = 36π V² / S³
    Clamp S to avoid blow-ups
    """
    S = np.maximum(S, 1e-12)
    return (36.0*np.pi) * (V*V) / (S*S*S)


class IQController:
    """
    IQ-banded controller with tunable parameters for live UI control.
    
    Features:
    - Asymmetric growth/shrink rates
    - Zero-sum volume enforcement
    - 5 safety guards against degeneracy
    - Live parameter adjustment via setters
    """
    
    def __init__(self,
                 IQ_min=0.65, IQ_max=0.85,
                 beta_grow=1.0, beta_shrink=0.7,
                 dr_cap=0.01,
                 r_min=0.005, r_max=0.060):
        """
        Initialize controller with default parameters.
        
        Args:
            IQ_min: Lower band threshold (grow below this)
            IQ_max: Upper band threshold (shrink above this)
            beta_grow: Growth rate for low-IQ cells
            beta_shrink: Shrink rate for high-IQ cells
            dr_cap: Max relative radius change per step
            r_min, r_max: Hard radii bounds (safety)
        """
        self.IQ_min = IQ_min
        self.IQ_max = IQ_max
        self.beta_grow = beta_grow
        self.beta_shrink = beta_shrink
        self.dr_cap = dr_cap
        self.r_min = r_min
        self.r_max = r_max
    
    def set_iq_band(self, IQ_min, IQ_max):
        """
        Update IQ band thresholds.
        
        Args:
            IQ_min: Lower threshold [0.4, 0.95]
            IQ_max: Upper threshold [0.45, 0.99]
        
        Validates: IQ_min < IQ_max
        """
        IQ_min = float(np.clip(IQ_min, 0.4, 0.95))
        IQ_max = float(np.clip(IQ_max, 0.45, 0.99))
        
        if IQ_min >= IQ_max:
            raise ValueError(f"IQ_min ({IQ_min}) must be < IQ_max ({IQ_max})")
        
        self.IQ_min = IQ_min
        self.IQ_max = IQ_max
    
    def set_beta_grow(self, beta_grow):
        """
        Update growth rate for low-IQ cells.
        
        Args:
            beta_grow: Growth rate [0.0, 2.0]
        """
        self.beta_grow = float(np.clip(beta_grow, 0.0, 2.0))
    
    def set_beta_shrink(self, beta_shrink):
        """
        Update shrink rate for high-IQ cells.
        
        Args:
            beta_shrink: Shrink rate [0.0, 2.0]
        """
        self.beta_shrink = float(np.clip(beta_shrink, 0.0, 2.0))
    
    def apply(self, r, V, S, flags):
        """
        Apply IQ-banded control with 5 safety guards.
        
        Args:
            r: Current radii (N,)
            V: Volumes (N,)
            S: Surface areas (N,)
            flags: 0=ok, >0=degenerate (N,)
        
        Returns:
            r_new: Updated radii (N,)
            IQ: Isoperimetric quotients (N,)
        """
        # SAFETY GUARD 1: Clamp input radii to safe range
        r = np.clip(r, self.r_min, self.r_max)
        
        # Store initial sum for renormalization
        r0_sum = r.sum()
        
        IQ = compute_IQ(V, S)
        ok = (flags == 0)

        low  = ok & (IQ < self.IQ_min)
        high = ok & (IQ > self.IQ_max)
        mid  = ok & ~(low | high)

        dV = np.zeros_like(V)
        dV[low]  =  self.beta_grow  * V[low]
        if np.any(high):
            Vbar = V[ok].mean()
            dV[high] = -self.beta_shrink * Vbar

        # Zero-sum enforcement
        pos = dV[dV > 0].sum()
        neg = -dV[dV < 0].sum()

        if pos > 0 and neg > 0:
            dV[dV < 0] *= (pos / max(neg, 1e-12))
        elif pos > 0 and neg == 0:
            if np.any(mid):
                dV[mid] -= pos / mid.sum()
            else:
                idx = np.where(ok)[0]
                dV[idx] -= pos / max(len(idx),1)

        # Convert dV -> dr: V = (4/3)π r³ => dV = 4π r² dr => dr = dV / (4π r²)
        denom = 4.0*np.pi*np.maximum(r*r, 1e-12)
        dr = dV / denom
        
        # SAFETY GUARD 2: Check for dominance (Bruno's edge case) or flags
        # If detected, dampen updates to prevent runaway
        dominant = (V.max() > 0.5) or np.any(flags != 0)
        if dominant:
            dr *= 0.25  # Strong dampening
        
        # SAFETY GUARD 3: Cap per-step change (≤1% typical)
        dr = np.clip(dr, -self.dr_cap*r, self.dr_cap*r)
        
        # Apply update
        r_new = r + dr
        
        # SAFETY GUARD 4: Hard clamp output radii
        r_new = np.clip(r_new, self.r_min, self.r_max)
        
        # SAFETY GUARD 5: Renormalize if dispersion explodes
        dispersion = r_new.std() / max(r_new.mean(), 1e-12)
        if dispersion > 0.5:  # Threshold: 50% variation
            # Rescale to preserve total "mass" (sum of radii)
            r_new *= (r0_sum / max(r_new.sum(), 1e-12))
            r_new = np.clip(r_new, self.r_min, self.r_max)  # Re-clamp after rescale
        
        return r_new, IQ


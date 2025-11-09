# controller.py
# Banded IQ controller (zero-sum, capped)

import numpy as np


def compute_IQ(V, S):
    """
    Compute isoperimetric quotient: IQ = 36π V² / S³
    Clamp S to avoid blow-ups
    """
    S = np.maximum(S, 1e-12)
    return (36.0*np.pi) * (V*V) / (S*S*S)


def apply_iq_banded_controller(r, V, S, flags,
                               IQ_min=0.70, IQ_max=0.90,
                               beta_grow=0.015, beta_shrink=0.002,
                               dr_cap=0.01):
    """
    IQ-banded controller with asymmetric growth/shrink.
    
    Args:
        r: current radii (N,)
        V: volumes (N,)
        S: surface areas (N,)
        flags: 0=ok, >0=degenerate (N,)
        IQ_min: lower band threshold
        IQ_max: upper band threshold
        beta_grow: growth rate for low-IQ cells
        beta_shrink: shrink rate for high-IQ cells
        dr_cap: max relative radius change
    
    Returns:
        r_new: updated radii (N,)
        IQ: isoperimetric quotients (N,)
    """
    IQ = compute_IQ(V, S)
    ok = (flags == 0)

    low  = ok & (IQ < IQ_min)
    high = ok & (IQ > IQ_max)
    mid  = ok & ~(low | high)

    dV = np.zeros_like(V)
    dV[low]  =  beta_grow  * V[low]
    if np.any(high):
        Vbar = V[ok].mean()
        dV[high] = -beta_shrink * Vbar

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
    r_new = r + np.clip(dr, -dr_cap*r, dr_cap*r)
    return r_new, IQ


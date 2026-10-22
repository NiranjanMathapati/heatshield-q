"""
classical_solver.py
Greedy classical baseline for cooling-resource allocation.

Strategy: rank zones by priority weight (descending) and greedily assign
cooling stations until the budget is exhausted.
"""

import numpy as np


def run_greedy(weights, budget: int) -> dict:
    """
    Greedy allocation: pick the top-`budget` zones by priority weight.

    Parameters
    ----------
    weights : array-like of float  (priority score per zone)
    budget  : int  (number of stations to allocate)

    Returns
    -------
    dict with:
        allocation      : np.ndarray of 0/1 per zone
        benefit         : float  (Σ wᵢ·xᵢ)
        zones_selected  : int
        sorted_indices  : indices sorted by weight (desc)
        sorted_weights  : weights in that order
    """
    weights = np.asarray(weights, dtype=float)
    n = len(weights)
    if weights.ndim != 1 or n == 0 or not np.all(np.isfinite(weights)):
        raise ValueError("weights must be a non-empty finite one-dimensional array")
    if not isinstance(budget, (int, np.integer)) or not 0 <= budget <= n:
        raise ValueError(f"budget must be an integer between 0 and {n}")

    sorted_idx = np.argsort(weights)[::-1]          # highest first
    allocation = np.zeros(n, dtype=int)
    allocation[sorted_idx[:budget]] = 1

    benefit = float(np.dot(weights, allocation))

    return {
        "allocation":     allocation,
        "benefit":        benefit,
        "zones_selected": int(allocation.sum()),
        "sorted_indices": sorted_idx,
        "sorted_weights": weights[sorted_idx],
    }

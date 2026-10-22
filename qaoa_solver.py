"""
qaoa_solver.py
Genuine Qiskit QAOA implementation for binary resource allocation.

Problem
-------
  Maximise   Σᵢ wᵢ·xᵢ            (risk-weighted coverage)
  Subject to Σᵢ xᵢ = budget      (use all stations)
             xᵢ ∈ {0, 1}

Approach
--------
  1. Encode as QUBO (minimisation).
  2. Convert QUBO → Ising Hamiltonian via x = (1 − z) / 2.
  3. Build a parametrised QAOA ansatz with p layers.
  4. Optimise γ, β parameters with COBYLA (gradient-free).
  5. Sample the final circuit; return the best feasible bitstring.
"""

import warnings
import numpy as np
from scipy.optimize import minimize

warnings.filterwarnings("ignore")

# ── Qiskit imports ────────────────────────────────────────────────────────────
from qiskit import QuantumCircuit, transpile  # noqa: E402
from qiskit_aer import AerSimulator          # noqa: E402


# ─────────────────────────────────────────────────────────────────────────────
# QUBO construction
# ─────────────────────────────────────────────────────────────────────────────

def build_qubo(weights: np.ndarray, budget: int, penalty: float | None = None):
    """
    Build the QUBO matrix for the allocation problem.

    Objective (minimisation):
        E = −Σᵢ wᵢ·xᵢ  +  λ·(Σᵢ xᵢ − budget)²

    Expanding the quadratic penalty (using xᵢ² = xᵢ for binary vars):
        diagonal :  Q[i,i]  = −wᵢ + λ·(1 − 2·budget)
        off-diag :  Q[i,j]  = 2λ          (i < j)
        constant :  λ·budget²  (not stored in Q, returned separately)

    Returns
    -------
    Q        : (n×n) upper-triangular QUBO matrix
    penalty  : the λ value used
    constant : energy offset due to constraint constant term
    """
    weights = np.asarray(weights, dtype=float)
    if weights.ndim != 1 or weights.size == 0:
        raise ValueError("weights must be a non-empty one-dimensional array")
    if not np.all(np.isfinite(weights)):
        raise ValueError("weights must contain only finite values")
    n = len(weights)
    if not isinstance(budget, (int, np.integer)) or not 0 <= budget <= n:
        raise ValueError(f"budget must be an integer between 0 and {n}")
    if penalty is not None and (not np.isfinite(penalty) or penalty <= 0):
        raise ValueError("penalty must be a finite positive number")
    if penalty is None:
        penalty = float(np.max(weights)) * 3.0 + 1.0

    Q = np.zeros((n, n))

    for i in range(n):
        Q[i, i] = -weights[i] + penalty * (1.0 - 2.0 * budget)

    for i in range(n):
        for j in range(i + 1, n):
            Q[i, j] = 2.0 * penalty

    constant = penalty * budget**2
    return Q, penalty, constant


def compute_qubo_energy(x: np.ndarray, Q: np.ndarray) -> float:
    """Evaluate the QUBO objective for a binary vector x."""
    n = len(x)
    energy = 0.0
    for i in range(n):
        energy += Q[i, i] * x[i]
        for j in range(i + 1, n):
            energy += Q[i, j] * x[i] * x[j]
    return energy


# ─────────────────────────────────────────────────────────────────────────────
# QUBO → Ising
# ─────────────────────────────────────────────────────────────────────────────

def qubo_to_ising(Q: np.ndarray, n: int):
    """
    Convert QUBO to Ising Hamiltonian using  xᵢ = (1 − zᵢ) / 2.

    H_C = Σᵢ hᵢ Zᵢ  +  Σᵢ<ⱼ Jᵢⱼ ZᵢZⱼ  +  offset

    Returns  h (n,), J (n×n upper), offset (float)
    """
    h = np.zeros(n)
    J = np.zeros((n, n))
    offset = 0.0

    for i in range(n):
        # diagonal term: Q[i,i]·xᵢ = Q[i,i]·(1−zᵢ)/2
        h[i]   -= Q[i, i] / 2.0
        offset += Q[i, i] / 2.0

        for j in range(i + 1, n):
            # Q[i,j]·xᵢxⱼ = Q[i,j]·(1−zᵢ)(1−zⱼ)/4
            J[i, j] = Q[i, j] / 4.0
            h[i]   -= Q[i, j] / 4.0
            h[j]   -= Q[i, j] / 4.0
            offset += Q[i, j] / 4.0

    return h, J, offset


# ─────────────────────────────────────────────────────────────────────────────
# QAOA circuit
# ─────────────────────────────────────────────────────────────────────────────

def _rzz(qc: QuantumCircuit, theta: float, q0: int, q1: int) -> None:
    """RZZ(θ) decomposed into standard gates: CNOT · RZ(θ) · CNOT."""
    qc.cx(q0, q1)
    qc.rz(theta, q1)
    qc.cx(q0, q1)


def build_qaoa_circuit(
    n: int,
    p: int,
    gamma: np.ndarray,
    beta: np.ndarray,
    h: np.ndarray,
    J: np.ndarray,
) -> QuantumCircuit:
    """
    Construct the QAOA circuit with p alternating layers.

    Layer l:
      Cost unitary   : e^{−iγₗ H_C} → RZZ and RZ gates
      Mixer unitary  : e^{−iβₗ Hₘ}  → RX gates (transverse field)
    """
    qc = QuantumCircuit(n, n)

    # Initialise |+⟩^⊗n
    qc.h(range(n))

    for layer in range(p):
        g = float(gamma[layer])
        b = float(beta[layer])

        # ── Cost Hamiltonian unitary ─────────────────────────────────────
        # ZZ interactions: e^{−iγ Jᵢⱼ ZᵢZⱼ} = RZZ(2γJᵢⱼ)
        for i in range(n):
            for j in range(i + 1, n):
                if abs(J[i, j]) > 1e-12:
                    _rzz(qc, 2.0 * g * J[i, j], i, j)

        # Z bias: e^{−iγ hᵢ Zᵢ} = RZ(2γhᵢ)
        for i in range(n):
            if abs(h[i]) > 1e-12:
                qc.rz(2.0 * g * h[i], i)

        # ── Mixer Hamiltonian unitary ────────────────────────────────────
        # e^{−iβ Σ Xᵢ} = ⊗ RX(2β)
        for i in range(n):
            qc.rx(2.0 * b, i)

    qc.measure(range(n), range(n))
    return qc


# ─────────────────────────────────────────────────────────────────────────────
# Main solver
# ─────────────────────────────────────────────────────────────────────────────

def run_qaoa(
    weights,
    budget: int,
    p: int = 1,
    shots: int = 1024,
    penalty: float | None = None,
    random_seed: int = 42,
    max_iter: int = 150,
) -> dict:
    """
    Run QAOA for the cooling-resource allocation problem.

    Parameters
    ----------
    weights      : priority scores for each zone (list or 1-D array)
    budget       : number of cooling stations to allocate
    p            : number of QAOA layers (circuit depth)
    shots        : measurement shots per circuit evaluation
    penalty      : QUBO constraint penalty λ (auto-chosen if None)
    random_seed  : NumPy seed for reproducibility
    max_iter     : COBYLA maximum function evaluations

    Returns
    -------
    dict with keys:
        allocation      : np.ndarray of 0/1 per zone
        benefit         : float  (Σ wᵢ·xᵢ for selected zones)
        zones_selected  : int
        energy_history  : list of expectation values per iteration
        final_counts    : dict  {bitstring: count}
        gamma_opt       : optimised γ array
        beta_opt        : optimised β array
        opt_result      : scipy OptimizeResult
        fallback_used   : bool  (True if QAOA found no feasible solution)
        n_qubits        : n
        p_layers        : p
    """
    np.random.seed(random_seed)
    weights = np.asarray(weights, dtype=float)
    n = len(weights)
    if weights.ndim != 1 or n == 0 or not np.all(np.isfinite(weights)):
        raise ValueError("weights must be a non-empty finite one-dimensional array")
    if not isinstance(budget, (int, np.integer)) or not 0 <= budget <= n:
        raise ValueError(f"budget must be an integer between 0 and {n}")
    if not isinstance(p, int) or p < 1:
        raise ValueError("p must be a positive integer")
    if not isinstance(shots, int) or shots < 1:
        raise ValueError("shots must be a positive integer")

    # ── Problem encoding ─────────────────────────────────────────────────
    Q, lam, _const = build_qubo(weights, budget, penalty)
    h, J, offset   = qubo_to_ising(Q, n)

    simulator     = AerSimulator()
    energy_history: list[float] = []

    # ── Objective for COBYLA ─────────────────────────────────────────────
    def objective(params: np.ndarray) -> float:
        g = params[:p]
        b = params[p:]
        try:
            qc = build_qaoa_circuit(n, p, g, b, h, J)
            qc_t = transpile(qc, simulator, optimization_level=0)
            counts = simulator.run(qc_t, shots=shots).result().get_counts()

            exp_val = 0.0
            total   = sum(counts.values())
            for bs, cnt in counts.items():
                x = np.array([int(c) for c in reversed(bs)])
                exp_val += (cnt / total) * compute_qubo_energy(x, Q)

            energy_history.append(exp_val)
            return exp_val
        except Exception:
            return 1e6

    # ── Initial parameters ───────────────────────────────────────────────
    # γ ∈ [0, π],  β ∈ [0, π/2]
    x0 = np.concatenate([
        np.random.uniform(0.1, np.pi,     p),
        np.random.uniform(0.1, np.pi / 2, p),
    ])

    opt_result = minimize(
        objective, x0,
        method="COBYLA",
        options={"maxiter": max_iter, "rhobeg": 0.5, "catol": 0.05},
    )

    gamma_opt = opt_result.x[:p]
    beta_opt  = opt_result.x[p:]

    # ── Final sampling with optimised parameters ─────────────────────────
    qc_final  = build_qaoa_circuit(n, p, gamma_opt, beta_opt, h, J)
    qc_ft     = transpile(qc_final, simulator, optimization_level=0)
    final_counts = simulator.run(qc_ft, shots=shots * 4).result().get_counts()

    # ── Extract best feasible allocation ─────────────────────────────────
    best_alloc:  np.ndarray | None = None
    best_benefit = -np.inf
    fallback_used = False

    for bs, cnt in final_counts.items():
        x = np.array([int(c) for c in reversed(bs)])
        if x.sum() == budget:
            benefit = float(np.dot(weights, x))
            if benefit > best_benefit:
                best_benefit = benefit
                best_alloc   = x.copy()

    # Fallback: greedy top-budget zones. This keeps the equality constraint valid.
    if best_alloc is None:
        fallback_used = True
        idx = np.argsort(weights)[::-1][:budget]
        best_alloc = np.zeros(n, dtype=int)
        best_alloc[idx] = 1
        best_benefit = float(np.dot(weights, best_alloc))

    return {
        "allocation":     best_alloc,
        "benefit":        best_benefit,
        "zones_selected": int(best_alloc.sum()),
        "energy_history": energy_history,
        "final_counts":   final_counts,
        "gamma_opt":      gamma_opt,
        "beta_opt":       beta_opt,
        "opt_result":     opt_result,
        "fallback_used":  fallback_used,
        "qubo_matrix":    Q,
        "penalty":        lam,
        "n_qubits":       n,
        "p_layers":       p,
    }

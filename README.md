# HEATSHIELD-Q 🔥⚛️

**Quantum-powered campus cooling-resource allocator**  
_Hackathon MVP · Track 6: Climate Change & Sustainability_

---

## Problem Statement

Extreme heat events put campus populations at risk. With limited cooling resources
(stations, hydration points, medical kits), administrators need to decide **which zones
get protected first**. HEATSHIELD-Q solves this as a combinatorial optimisation problem
using the **Quantum Approximate Optimization Algorithm (QAOA)** via Qiskit.

---

## Features

| Page | What it does |
|------|-------------|
| 🌡️ **Heat-Risk Dashboard** | 5 campus zones with population, heat-risk, vulnerability, and 4 interactive Plotly charts |
| ⚛️ **Quantum Optimizer** | Genuine Qiskit QAOA — QUBO formulation → Ising Hamiltonian → parameterised circuit → COBYLA optimisation → bitstring decoding |
| 📊 **Comparison** | Side-by-side QAOA vs greedy classical — honest, no fabricated quantum advantage |

---

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

> Tested with Python 3.10 / 3.11.  
> All computation runs on a **local Qiskit AerSimulator** — no IBM account, no internet required.

### 2. Run the app

```bash
streamlit run app.py
```

The app opens automatically at `http://localhost:8501`.

---

## Project Structure

```
heatshield_q/
├── app.py              # Streamlit UI (Dashboard · Optimizer · Comparison)
├── campus_data.py      # Simulated zone data + priority weights
├── qaoa_solver.py      # QUBO → Ising → QAOA circuit → result decoding
├── classical_solver.py # Greedy baseline
├── requirements.txt
└── README.md
```

---

## QAOA Implementation Details

```
1. Build QUBO matrix Q
   • Q[i,i]  = −wᵢ + λ(1 − 2·budget)     (objective + diagonal penalty)
   • Q[i,j]  = 2λ                          (off-diagonal penalty, i < j)
   • λ chosen as  max(wᵢ)·3 + 1

2. Convert QUBO → Ising (substitution xᵢ = (1 − zᵢ)/2)
   • h[i]  = −Q[i,i]/2  − Σⱼ Q[i,j]/4
   • J[i,j] = Q[i,j]/4
   • H_C = Σ hᵢZᵢ + Σ Jᵢⱼ ZᵢZⱼ

3. Build QAOA circuit (p layers)
   • Initialise  |+⟩⊗n  with H gates
   • Cost unitary:   RZZ(2γJᵢⱼ) + RZ(2γhᵢ)
   • Mixer unitary:  RX(2β) on every qubit

4. Optimise (γ, β) with COBYLA minimising ⟨H_C⟩

5. Sample final circuit; return best feasible bitstring (Σxᵢ = budget)
```

---

## Honest Limitations

- For **n = 5 zones**, the classical greedy algorithm is already optimal.
  QAOA advantage is expected only at **n ≥ 20–50** where exhaustive search becomes intractable.
- QAOA solutions are **probabilistic** — re-runs may differ.
- The app uses `optimization_level=0` transpilation for speed; real hardware would require noise mitigation.

---

## Tech Stack

- **Qiskit ≥ 1.0** — quantum circuit construction
- **Qiskit-Aer ≥ 0.14** — local statevector / QASM simulator
- **SciPy COBYLA** — gradient-free parameter optimisation
- **Streamlit** — interactive dashboard
- **Plotly** — charts (radar, bubble, grouped bar, convergence)
- **Pandas / NumPy** — data handling


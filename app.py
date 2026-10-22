"""
app.py  –  HEATSHIELD-Q  |  Quantum Campus Heat-Resource Allocator
Hackathon MVP · Track 6: Climate Change & Sustainability

Run:  streamlit run app.py
"""

import time
import warnings
import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

warnings.filterwarnings("ignore")

# ── Page config (MUST be first Streamlit call) ────────────────────────────────
st.set_page_config(
    page_title="HEATSHIELD-Q · Quantum Heat Allocator",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={"About": "HEATSHIELD-Q — Quantum-powered campus heat-relief allocation."},
)

# ── Safe imports ──────────────────────────────────────────────────────────────
try:
    from campus_data import CAMPUS_ZONES, RESOURCE_BUDGET, TOTAL_ZONES
    from qaoa_solver import run_qaoa
    from classical_solver import run_greedy
    _IMPORTS_OK = True
except ImportError as _err:
    _IMPORTS_OK = False
    _IMPORT_ERROR = str(_err)

# ─────────────────────────────────────────────────────────────────────────────
# Global CSS
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(
    """
<style>
/* ── Fonts ── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Space+Grotesk:wght@400;500;600;700&display=swap');

/* ── Base ── */
html, body, [class*="css"] { font-family: 'Inter', system-ui, sans-serif; }
.stApp {
    background: linear-gradient(160deg, #080d18 0%, #0d1224 55%, #080d18 100%);
}
.main .block-container {
    padding-top: 1.2rem;
    padding-bottom: 3rem;
    max-width: 1380px;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0b0f1e 0%, #080d18 100%);
    border-right: 1px solid rgba(255,107,53,.18);
}
[data-testid="stSidebar"] * { color: #c4cad8 !important; }
[data-testid="stSidebar"] .stRadio label { font-size: .82rem; }

/* ── Hero header ── */
.hero {
    background: linear-gradient(135deg,rgba(255,107,53,.09),rgba(255,68,68,.04),rgba(255,107,53,.09));
    border: 1px solid rgba(255,107,53,.22);
    border-radius: 20px;
    padding: 1.8rem 2.4rem;
    margin-bottom: 1.6rem;
    position: relative; overflow: hidden;
}
.hero::after {
    content:''; position:absolute; top:-60px; right:-40px;
    width:320px; height:320px;
    background: radial-gradient(circle,rgba(255,107,53,.07) 0%,transparent 68%);
    pointer-events: none;
}
.hero-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: clamp(1.5rem, 3vw, 2.2rem);
    font-weight: 700;
    background: linear-gradient(90deg,#ff6b35,#ff4040,#ffcc00);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    background-clip: text;
    margin: 0 0 .3rem 0;
}
.hero-sub { color: #7a85a0; font-size: .95rem; margin: 0; }

/* ── Section titles ── */
.sec-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.15rem; font-weight: 600; color: #dde1ec;
    border-left: 3px solid #ff6b35;
    padding-left: .7rem;
    margin: 1.6rem 0 .9rem 0;
}

/* ── Zone cards ── */
.zcard {
    background: linear-gradient(135deg,#181e30,#131826);
    border: 1px solid rgba(255,107,53,.17);
    border-radius: 14px;
    padding: 1.1rem 1rem 1rem;
    min-height: 195px;
    position: relative; overflow: hidden;
    transition: transform .2s, box-shadow .2s;
}
.zcard:hover { transform: translateY(-3px); box-shadow: 0 8px 30px rgba(255,107,53,.14); border-color: rgba(255,107,53,.35); }
.zcard-accent { position:absolute; top:0; left:0; right:0; height:3px; border-radius:14px 14px 0 0; }
.zcard-accent-high   { background: linear-gradient(90deg,#ff2200,#ff5533); }
.zcard-accent-medium { background: linear-gradient(90deg,#ff6b35,#ffcc00); }
.zcard-accent-low    { background: linear-gradient(90deg,#44bb77,#22aaff); }
.zicon  { font-size: 1.9rem; margin-bottom: .35rem; display:block; }
.zname  { font-family:'Space Grotesk',sans-serif; font-size:1rem; font-weight:600; color:#e0e4f0; margin-bottom:.3rem; }
.zstat  { font-size:.78rem; color:#6b7590; line-height:1.6; }
.zval   { color:#ff7b47; font-weight:600; }
.zbadge {
    display:inline-block; padding:.18rem .65rem;
    border-radius:20px; font-size:.7rem; font-weight:600; margin-top:.45rem;
}
.zbadge-high   { background:rgba(255,34,0,.15);  color:#ff6655; border:1px solid rgba(255,34,0,.25); }
.zbadge-medium { background:rgba(255,165,0,.15); color:#ffa822; border:1px solid rgba(255,165,0,.25); }
.zbadge-low    { background:rgba(68,187,119,.15);color:#44bb77; border:1px solid rgba(68,187,119,.25); }

/* ── Stat tiles (result cards) ── */
.stile {
    background: linear-gradient(135deg,#181e30,#131826);
    border: 1px solid rgba(255,107,53,.25);
    border-radius: 12px;
    padding: 1.1rem 1rem;
    text-align: center;
    transition: box-shadow .2s;
}
.stile:hover { box-shadow: 0 4px 22px rgba(255,107,53,.12); }
.stile-val   { font-family:'Space Grotesk',sans-serif; font-size:1.85rem; font-weight:700; color:#ff6b35; }
.stile-lbl   { font-size:.72rem; color:#6b7590; text-transform:uppercase; letter-spacing:.07em; margin-top:.2rem; }

/* ── Allocation badges ── */
.asel {
    background: linear-gradient(135deg,rgba(255,107,53,.25),rgba(255,68,68,.15));
    border: 1px solid rgba(255,107,53,.55);
    border-radius: 10px; padding: .75rem .9rem;
    color: #ff9b6a; font-size:.85rem;
}
.askip {
    background: rgba(22,28,44,.55);
    border: 1px solid rgba(80,90,115,.25);
    border-radius: 10px; padding: .75rem .9rem;
    color: #3f4d66; font-size:.85rem;
}

/* ── Info banners ── */
.info-quantum {
    background:rgba(90,55,210,.08); border:1px solid rgba(120,80,230,.22);
    border-radius:8px; padding:.75rem 1rem; color:#b09af0; font-size:.84rem;
    margin:.8rem 0;
}
.info-warn {
    background:rgba(255,200,0,.06); border:1px solid rgba(255,200,0,.2);
    border-radius:8px; padding:.75rem 1rem; color:#ccac40; font-size:.84rem;
    margin:.8rem 0;
}
.info-good {
    background:rgba(50,180,100,.07); border:1px solid rgba(50,180,100,.2);
    border-radius:8px; padding:.75rem 1rem; color:#55cc88; font-size:.84rem;
    margin:.8rem 0;
}

/* ── Buttons ── */
.stButton>button {
    background: linear-gradient(135deg,#ff6b35,#e83030) !important;
    color:#fff !important; border:none !important;
    border-radius:12px !important;
    padding:.7rem 1.8rem !important;
    font-family:'Space Grotesk',sans-serif !important;
    font-size:.95rem !important; font-weight:600 !important;
    letter-spacing:.02em !important;
    box-shadow: 0 4px 20px rgba(255,107,53,.3) !important;
    transition: all .25s !important;
}
.stButton>button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 32px rgba(255,107,53,.5) !important;
}

/* ── Sliders ── */
[data-testid="stSlider"] [role="slider"] { background:#ff6b35 !important; }

/* ── Expander ── */
details { border:1px solid rgba(255,107,53,.15) !important; border-radius:8px !important; }

/* ── Divider ── */
hr { border-color: rgba(255,107,53,.12) !important; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width:6px; }
::-webkit-scrollbar-track { background:transparent; }
::-webkit-scrollbar-thumb { background:rgba(255,107,53,.3); border-radius:3px; }
</style>
""",
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────────────────────────────────────
# Guard: dependency check
# ─────────────────────────────────────────────────────────────────────────────
if not _IMPORTS_OK:
    st.error(f"❌ Import error: `{_IMPORT_ERROR}`")
    st.code("pip install qiskit qiskit-aer streamlit pandas plotly numpy scipy")
    st.stop()

# ─────────────────────────────────────────────────────────────────────────────
# Shared plotly theme
# ─────────────────────────────────────────────────────────────────────────────
_PLAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter", color="#c4cad8", size=12),
    margin=dict(l=24, r=24, t=44, b=24),
    legend=dict(
        bgcolor="rgba(20,26,44,.85)",
        bordercolor="rgba(255,107,53,.18)",
        borderwidth=1,
    ),
)

# Zone colour palette (5 zones)
_ZONE_CLR  = ["#ff4040", "#ff6b35", "#ffcc00", "#44bb77", "#22aaff"]
_ZONE_FILL = [
    "rgba(255,64,64,.12)", "rgba(255,107,53,.12)", "rgba(255,204,0,.12)",
    "rgba(68,187,119,.12)", "rgba(34,170,255,.12)",
]

# ─────────────────────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        """
        <div style="text-align:center;padding:1rem 0 1.5rem">
          <div style="font-size:2.8rem">🔥</div>
          <div style="font-family:'Space Grotesk',sans-serif;font-size:1.35rem;
                      font-weight:700;
                      background:linear-gradient(90deg,#ff6b35,#ffcc00);
                      -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                      background-clip:text;">HEATSHIELD-Q</div>
          <div style="display:inline-block;background:rgba(255,107,53,.13);
                      border:1px solid rgba(255,107,53,.28);border-radius:20px;
                      padding:.18rem .65rem;font-size:.7rem;color:#ff9066;margin-top:.4rem">
            ⚛️ Quantum Edition
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    page = st.radio(
        "nav",
        ["🌡️ Heat-Risk Dashboard", "⚛️ Quantum Optimizer", "📊 Comparison"],
        label_visibility="collapsed",
    )

    st.divider()
    st.markdown("**System**", unsafe_allow_html=False)
    st.success("🟢 Simulator Online")
    c1, c2 = st.columns(2)
    c1.metric("Budget", f"{RESOURCE_BUDGET} 🧊")
    c2.metric("Zones", str(TOTAL_ZONES))
    st.divider()
    st.markdown(
        "<div style='color:#3f4d66;font-size:.72rem;text-align:center'>"
        "Track 6 · Climate & Sustainability<br>"
        "Powered by Qiskit + QAOA<br>"
        "Local AerSimulator · No cloud needed"
        "</div>",
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# PAGE 1 — Heat-Risk Dashboard
# ─────────────────────────────────────────────────────────────────────────────
def page_dashboard() -> None:
    df = CAMPUS_ZONES.copy()

    st.markdown(
        """
        <div class="hero">
          <h1 class="hero-title">🌡️ Campus Heat-Risk Dashboard</h1>
          <p class="hero-sub">
            Real-time heat-vulnerability assessment across 5 campus zones ·
            Informing cooling-resource allocation during extreme heat events
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Summary KPIs ─────────────────────────────────────────────────────
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("👥 Total Population", f"{df['population'].sum():,}")
    k2.metric("🌡️ Avg Heat-Risk", f"{df['heat_risk'].mean():.1f} / 10")
    k3.metric("🧊 Cooling Stations", f"{RESOURCE_BUDGET}")
    k4.metric(
        "📊 Zone Coverage",
        f"{RESOURCE_BUDGET}/{TOTAL_ZONES}",
        delta="Insufficient — optimise!",
        delta_color="inverse",
    )

    st.divider()

    # ── Zone cards ────────────────────────────────────────────────────────
    st.markdown('<div class="sec-title">Campus Zone Overview</div>', unsafe_allow_html=True)
    cols = st.columns(TOTAL_ZONES)
    for col, row in zip(cols, df.itertuples(index=False)):
        risk = row.heat_risk
        if risk >= 8:
            acc_cls, badge_cls, badge_lbl = "zcard-accent-high",   "zbadge-high",   "🔴 High Risk"
        elif risk >= 6:
            acc_cls, badge_cls, badge_lbl = "zcard-accent-medium", "zbadge-medium", "🟡 Moderate"
        else:
            acc_cls, badge_cls, badge_lbl = "zcard-accent-low",    "zbadge-low",    "🟢 Low Risk"

        with col:
            st.markdown(
                f"""
                <div class="zcard">
                  <div class="zcard-accent {acc_cls}"></div>
                  <span class="zicon">{row.icon}</span>
                  <div class="zname">{row.zone}</div>
                  <div class="zstat">Population: <span class="zval">{row.population:,}</span></div>
                  <div class="zstat">Heat Risk:  <span class="zval">{row.heat_risk}/10</span></div>
                  <div class="zstat">Vulnerability: <span class="zval">{row.vulnerability}/10</span></div>
                  <div class="zstat">Priority Score: <span class="zval">{row.priority:.3f}</span></div>
                  <span class="zbadge {badge_cls}">{badge_lbl}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.divider()

    # ── Charts ────────────────────────────────────────────────────────────
    st.markdown('<div class="sec-title">Risk Analysis Visualisations</div>', unsafe_allow_html=True)
    r1c1, r1c2 = st.columns(2)

    # Chart 1 — grouped bar: heat-risk + vulnerability
    with r1c1:
        fig = go.Figure()
        fig.add_trace(go.Bar(
            name="Heat Risk",
            x=df["zone"], y=df["heat_risk"],
            marker=dict(
                color=df["heat_risk"],
                colorscale="YlOrRd",
                showscale=False,
                line=dict(color="rgba(255,107,53,.4)", width=1),
            ),
            text=df["heat_risk"], textposition="auto",
        ))
        fig.add_trace(go.Bar(
            name="Vulnerability",
            x=df["zone"], y=df["vulnerability"],
            marker=dict(color="rgba(80,160,255,.65)",
                        line=dict(color="rgba(80,160,255,.8)", width=1)),
            text=df["vulnerability"], textposition="auto",
        ))
        fig.update_layout(
            **_PLAYOUT,
            title="Heat-Risk vs Vulnerability Score",
            barmode="group",
            yaxis=dict(range=[0, 12], showgrid=True, gridcolor="rgba(255,255,255,.04)"),
            xaxis=dict(showgrid=False),
        )
        st.plotly_chart(fig, use_container_width=True)

    # Chart 2 — bubble: risk vs vulnerability, size=population
    with r1c2:
        fig2 = go.Figure()
        for i, row in df.iterrows():
            fig2.add_trace(go.Scatter(
                x=[row["heat_risk"]], y=[row["vulnerability"]],
                mode="markers+text",
                text=[row["zone"]], textposition="top center",
                name=row["zone"],
                marker=dict(
                    size=row["population"] / 80,
                    color=_ZONE_CLR[i],
                    line=dict(color="rgba(255,255,255,.25)", width=1.5),
                    opacity=.85,
                ),
            ))
        fig2.update_layout(
            **_PLAYOUT,
            title="Risk Profile  (bubble size ∝ population)",
            xaxis=dict(title="Heat Risk Score", range=[4, 11],
                       showgrid=True, gridcolor="rgba(255,255,255,.04)"),
            yaxis=dict(title="Vulnerability Score", range=[3, 10],
                       showgrid=True, gridcolor="rgba(255,255,255,.04)"),
            showlegend=True,
        )
        st.plotly_chart(fig2, use_container_width=True)

    r2c1, r2c2 = st.columns(2)

    # Chart 3 — horizontal priority bar
    with r2c1:
        bar_colors = [
            "#ff3030" if p > .65 else "#ff8833" if p > .5 else "#22aaff"
            for p in df["priority"]
        ]
        fig3 = go.Figure(go.Bar(
            x=df["priority"], y=df["zone"], orientation="h",
            marker=dict(color=bar_colors, line=dict(color="rgba(255,255,255,.07)", width=1)),
            text=[f"{p:.4f}" for p in df["priority"]], textposition="auto",
        ))
        fig3.update_layout(
            **_PLAYOUT,
            title="Allocation Priority Score by Zone",
            xaxis=dict(title="Priority Score", showgrid=True, gridcolor="rgba(255,255,255,.04)"),
            yaxis=dict(showgrid=False),
            showlegend=False,
        )
        st.plotly_chart(fig3, use_container_width=True)

    # Chart 4 — radar chart
    with r2c2:
        cats = ["Population", "Heat Risk", "Vulnerability", "Priority ×10"]
        fig4 = go.Figure()
        for i, row in df.iterrows():
            vals = [
                row["pop_norm"] * 10,
                row["heat_risk"],
                row["vulnerability"],
                row["priority"] * 10,
            ]
            fig4.add_trace(go.Scatterpolar(
                r=vals + [vals[0]],
                theta=cats + [cats[0]],
                fill="toself", name=row["zone"],
                fillcolor=_ZONE_FILL[i],
                line=dict(color=_ZONE_CLR[i], width=2),
            ))
        fig4.update_layout(
            **_PLAYOUT,
            title="Multi-Dimensional Zone Risk Radar",
            polar=dict(
                radialaxis=dict(visible=True, range=[0, 10],
                                gridcolor="rgba(255,255,255,.08)", tickfont=dict(size=9)),
                angularaxis=dict(gridcolor="rgba(255,255,255,.08)"),
                bgcolor="rgba(0,0,0,0)",
            ),
        )
        st.plotly_chart(fig4, use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# PAGE 2 — Quantum Optimizer
# ─────────────────────────────────────────────────────────────────────────────
def page_quantum() -> None:
    df      = CAMPUS_ZONES.copy()
    weights = df["priority"].values

    st.markdown(
        """
        <div class="hero">
          <h1 class="hero-title">⚛️ Quantum Resource Optimizer</h1>
          <p class="hero-sub">
            QAOA on a local Qiskit AerSimulator · No cloud · No paid APIs ·
            Genuine quantum circuit optimisation
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="info-quantum">
          <strong>⚛️ How QAOA works here:</strong><br>
          The allocation problem is encoded as a <em>Quadratic Unconstrained Binary Optimisation
          (QUBO)</em> problem, mapped to an Ising Hamiltonian, and solved with the
          <em>Quantum Approximate Optimization Algorithm (QAOA)</em>.<br>
          A parameterised quantum circuit alternates between a <em>cost unitary</em>
          e<sup>−iγH<sub>C</sub></sup> and a <em>mixer unitary</em> e<sup>−iβH<sub>M</sub></sup>.
          The COBYLA optimiser tunes γ and β to minimise the expected energy.
          The best measured bitstring is decoded into a zone allocation.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.divider()

    # ── Configuration ─────────────────────────────────────────────────────
    st.markdown('<div class="sec-title">⚙️ QAOA Configuration</div>', unsafe_allow_html=True)
    cfg1, cfg2, cfg3 = st.columns(3)
    with cfg1:
        budget = st.slider(
            "🧊 Cooling Stations Budget", 1, TOTAL_ZONES, RESOURCE_BUDGET,
            help="Number of cooling stations to allocate across all zones.",
        )
    with cfg2:
        p_layers = st.slider(
            "⚛️ QAOA Circuit Depth (p)", 1, 3, 1,
            help="Number of alternating cost+mixer layers. Higher p can improve solution quality but takes longer.",
        )
    with cfg3:
        shots = st.select_slider(
            "📊 Measurement Shots",
            options=[512, 1024, 2048, 4096], value=1024,
            help="Samples drawn from the final quantum circuit. More shots → more accurate distribution.",
        )
    max_iter = st.slider(
        "🧭 Optimizer evaluations", 30, 150, 80, step=10,
        help="Maximum COBYLA objective evaluations.",
    )

    # ── Problem details expander ──────────────────────────────────────────
    with st.expander("📐 Problem Formulation & Circuit Details", expanded=False):
        left, right = st.columns(2)
        with left:
            st.markdown(
                f"""
**Optimisation objective (maximisation):**
```
Maximise  Σᵢ wᵢ·xᵢ    (risk-weighted coverage)
s.t.      Σᵢ xᵢ = {budget},   xᵢ ∈ {{0,1}}
```
**QUBO re-encoding (minimisation):**
```
Minimise  −Σᵢ wᵢ·xᵢ  +  λ·(Σᵢ xᵢ − {budget})²
```
**Ising Hamiltonian:**
```
H_C = Σᵢ hᵢ Zᵢ  +  Σᵢ<ⱼ Jᵢⱼ ZᵢZⱼ
```
**QAOA ansatz:**
```
|ψ(γ,β)⟩ = ∏ₗ e{{−iβₗHₘ}} e{{−iγₗH_C}} |+⟩^n
```
                """
            )
        with right:
            st.markdown("**Priority weights (wᵢ):**")
            for _, row in df.iterrows():
                st.markdown(f"- {row['icon']} **{row['zone']}**: `{row['priority']:.4f}`")
            st.markdown(
                f"""
**Circuit parameters:**
- Qubits: **{TOTAL_ZONES}** (one per zone)
- Budget: **{budget}** cooling stations
- QAOA layers: **{p_layers}**
- Optimizer: **COBYLA** (gradient-free)
- Shots: **{shots}** per evaluation
                """
            )

    st.divider()

    # ── Run button ────────────────────────────────────────────────────────
    btn_col, info_col = st.columns([1, 3])
    with btn_col:
        run_clicked = st.button("🚀 Optimize Allocation", use_container_width=True)
    with info_col:
        st.markdown(
            "<div class='info-warn'>⏱️ Estimated runtime: <strong>20 – 90 s</strong> "
            "depending on depth and shots. The optimiser runs up to your selected COBYLA "
            "iterations, each executing a full quantum circuit.</div>",
            unsafe_allow_html=True,
        )

    # ── Execution ─────────────────────────────────────────────────────────
    if run_clicked:
        # Clear stale results when config changes
        st.session_state.pop("qaoa_result", None)
        st.session_state.pop("qaoa_budget", None)

        prog = st.progress(0, text="Initialising quantum circuit …")
        with st.spinner("⚛️ Running QAOA on local simulator …"):
            prog.progress(15, text="Building QUBO matrix …")
            time.sleep(0.2)
            prog.progress(30, text="Converting to Ising Hamiltonian …")
            time.sleep(0.2)
            prog.progress(45, text="Optimising γ & β parameters …")

            t0 = time.time()
            try:
                result = run_qaoa(
                    weights=weights,
                    budget=budget,
                    p=p_layers,
                    shots=shots,
                    max_iter=max_iter,
                )
                elapsed = time.time() - t0
                prog.progress(100, text="Done ✅")
                st.session_state["qaoa_result"] = result
                st.session_state["qaoa_budget"] = budget
                st.session_state["qaoa_config"] = {
                    "budget": budget, "p": p_layers, "shots": shots, "elapsed": elapsed
                }
                st.success(
                    f"✅ QAOA completed in **{elapsed:.1f} s** "
                    f"· {len(result['energy_history'])} optimiser iterations"
                )
                if result["fallback_used"]:
                    st.warning(
                        "⚠️ No feasible bitstring was sampled — "
                        "greedy fallback applied for display. Try increasing shots or QAOA depth."
                    )
            except Exception as exc:
                prog.empty()
                st.error(f"❌ QAOA failed: {exc}")
                st.exception(exc)
                return

    # ── Display results ───────────────────────────────────────────────────
    if "qaoa_result" not in st.session_state:
        st.markdown(
            "<div class='info-quantum' style='text-align:center'>Click "
            "<strong>🚀 Optimize Allocation</strong> to run the quantum solver.</div>",
            unsafe_allow_html=True,
        )
        return

    result = st.session_state["qaoa_result"]
    budget_used = st.session_state["qaoa_budget"]
    allocation  = result["allocation"]

    config = st.session_state.get("qaoa_config", {})
    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "problem": "maximize priority-weighted zone coverage with an exact station budget",
        "config": config,
        "budget": int(budget_used),
        "benefit": float(result["benefit"]),
        "zones_selected": int(result["zones_selected"]),
        "allocation": [
            {"zone": str(row.zone), "priority": float(row.priority), "selected": bool(allocation[i])}
            for i, row in enumerate(df.itertuples(index=False))
        ],
        "optimizer": {
            "success": bool(result["opt_result"].success),
            "message": str(result["opt_result"].message),
            "evaluations": int(result["opt_result"].nfev),
            "fallback_used": bool(result["fallback_used"]),
        },
        "measurement_counts": {str(k): int(v) for k, v in result["final_counts"].items()},
    }
    st.download_button(
        "⬇️ Download run report (JSON)", data=json.dumps(report, indent=2),
        file_name="heatshield_q_run_report.json", mime="application/json",
    )

    st.divider()
    st.markdown('<div class="sec-title">📊 Optimisation Results</div>', unsafe_allow_html=True)

    # KPI tiles
    k1, k2, k3, k4 = st.columns(4)
    cov_pct = result["benefit"] / float(weights.sum()) * 100
    iters   = len(result["energy_history"])
    for col, val, lbl in [
        (k1, f"{result['benefit']:.4f}", "Priority Benefit"),
        (k2, f"{result['zones_selected']}/{budget_used}", "Zones Allocated"),
        (k3, f"{cov_pct:.1f}%", "Risk Coverage"),
        (k4, str(iters), "Optimiser Iterations"),
    ]:
        col.markdown(
            f'<div class="stile"><div class="stile-val">{val}</div>'
            f'<div class="stile-lbl">{lbl}</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown("")

    # Zone allocation decisions
    st.markdown('<div class="sec-title">🗺️ Zone Allocation Decision</div>', unsafe_allow_html=True)
    zcols = st.columns(TOTAL_ZONES)
    for i, (col, (_, row)) in enumerate(zip(zcols, df.iterrows())):
        sel = bool(allocation[i])
        css = "asel" if sel else "askip"
        mark = "✅ ALLOCATED" if sel else "⬜ Not selected"
        with col:
            st.markdown(
                f'<div class="{css}">'
                f'{row["icon"]} <strong>{row["zone"]}</strong><br>'
                f'<small>{mark}</small><br>'
                f'<small>Priority {row["priority"]:.3f}</small>'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.markdown("")

    # Charts: energy convergence + measurement histogram
    if result["energy_history"]:
        ch1, ch2 = st.columns(2)

        with ch1:
            ehist = result["energy_history"]
            fig_e = go.Figure()
            fig_e.add_trace(go.Scatter(
                y=ehist, mode="lines",
                line=dict(color="#ff6b35", width=2),
                fill="tozeroy", fillcolor="rgba(255,107,53,.08)",
                name="⟨H_C⟩",
            ))
            fig_e.add_hline(
                y=min(ehist), line_dash="dash", line_color="#ffcc00",
                annotation_text=f"Min {min(ehist):.4f}",
                annotation_font_color="#ffcc00",
            )
            fig_e.update_layout(
                **_PLAYOUT,
                title="QAOA Energy Convergence  ⟨H_C⟩",
                xaxis=dict(title="Iteration", showgrid=True, gridcolor="rgba(255,255,255,.04)"),
                yaxis=dict(title="Expectation Value", showgrid=True, gridcolor="rgba(255,255,255,.04)"),
                showlegend=False,
            )
            st.plotly_chart(fig_e, use_container_width=True)

        with ch2:
            counts = result["final_counts"]
            top12  = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:12]
            bs_labels = [b for b, _ in top12]
            bs_vals   = [c for _, c in top12]
            opt_bs    = "".join(str(int(b)) for b in reversed(allocation))

            bar_cls = [
                "#ffcc00" if lbl == opt_bs else "#ff6b35" if i < 3 else "#2e3a58"
                for i, lbl in enumerate(bs_labels)
            ]
            fig_h = go.Figure(go.Bar(
                x=bs_labels, y=bs_vals,
                marker_color=bar_cls,
                text=bs_vals, textposition="auto",
            ))
            fig_h.update_layout(
                **_PLAYOUT,
                title="Quantum Measurement Distribution (top 12)",
                xaxis=dict(title="Bitstring (qubit 0 = rightmost)", showgrid=False, tickangle=40),
                yaxis=dict(title="Shots", showgrid=True, gridcolor="rgba(255,255,255,.04)"),
                showlegend=False,
            )
            st.plotly_chart(fig_h, use_container_width=True)

    # Optimal parameters expander
    with st.expander("🔬 Optimal QAOA Parameters", expanded=False):
        pc1, pc2, pc3 = st.columns(3)
        with pc1:
            st.markdown("**γ (phase-separation):**")
            for i, g in enumerate(result["gamma_opt"]):
                st.markdown(f"- γ₍{i+1}₎ = **{g:.5f}** rad")
        with pc2:
            st.markdown("**β (mixing):**")
            for i, b in enumerate(result["beta_opt"]):
                st.markdown(f"- β₍{i+1}₎ = **{b:.5f}** rad")
        with pc3:
            st.markdown("**Optimiser:**")
            st.markdown(f"- Message: `{result['opt_result'].message}`")
            st.markdown(f"- Final energy: **{result['opt_result'].fun:.6f}**")
            st.markdown(f"- n_qubits: **{result['n_qubits']}**")
            st.markdown(f"- p_layers: **{result['p_layers']}**")
            st.markdown(f"- Fallback used: **{result['fallback_used']}**")


# ─────────────────────────────────────────────────────────────────────────────
# PAGE 3 — Classical Comparison
# ─────────────────────────────────────────────────────────────────────────────
def page_comparison() -> None:
    df      = CAMPUS_ZONES.copy()
    weights = df["priority"].values

    st.markdown(
        """
        <div class="hero">
          <h1 class="hero-title">📊 QAOA vs Classical Comparison</h1>
          <p class="hero-sub">
            Honest, side-by-side benchmarking of quantum and classical resource allocation.
            No fabricated results. No false quantum-advantage claims.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="info-warn">
          ⚠️ <strong>Honest Assessment:</strong> For 5 zones the classical greedy
          algorithm already finds the optimal solution in O(n log n) time.
          QAOA's potential advantage emerges at scale (50+ binary variables) where
          classical methods face an exponentially hard search space.
          Results shown here reflect genuine algorithm outputs — no post-processing
          to artificially favour either approach.
        </div>
        """,
        unsafe_allow_html=True,
    )

    has_qaoa = "qaoa_result" in st.session_state
    if not has_qaoa:
        st.info("⚛️ Run the **Quantum Optimizer** page first to enable the full comparison.")

    # Choose budget
    budget = st.session_state.get("qaoa_budget", RESOURCE_BUDGET)

    # Always compute classical
    c_res   = run_greedy(weights, budget)
    c_alloc = c_res["allocation"]

    # ── Side-by-side columns ─────────────────────────────────────────────
    col_q, col_c = st.columns(2)

    with col_q:
        st.markdown(
            """
            <div style="text-align:center;padding:.4rem 0 .8rem">
              <span style="font-size:1.6rem">⚛️</span><br>
              <span style="font-family:'Space Grotesk';font-size:1.1rem;font-weight:600;color:#ff6b35">
                QAOA (Quantum)
              </span><br>
              <span style="font-size:.78rem;color:#6b7590">
                Quantum Approximate Optimization Algorithm
              </span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if has_qaoa:
            q_res   = st.session_state["qaoa_result"]
            q_alloc = q_res["allocation"]
            qa1, qa2 = st.columns(2)
            qa1.metric("Benefit Score",   f"{q_res['benefit']:.4f}")
            qa2.metric("Zones Selected",  f"{q_res['zones_selected']}")
            qa3, qa4 = st.columns(2)
            qa3.metric("Risk Coverage",   f"{q_res['benefit']/weights.sum()*100:.1f}%")
            qa4.metric("Iterations",      f"{len(q_res['energy_history'])}")
            st.markdown("**Allocated zones:**")
            for i, (_, row) in enumerate(df.iterrows()):
                if q_alloc[i]:
                    st.markdown(f"✅ {row['icon']} {row['zone']}  `{row['priority']:.3f}`")
        else:
            st.markdown("*Run the Quantum Optimizer to populate this column.*")

    with col_c:
        st.markdown(
            """
            <div style="text-align:center;padding:.4rem 0 .8rem">
              <span style="font-size:1.6rem">🖥️</span><br>
              <span style="font-family:'Space Grotesk';font-size:1.1rem;font-weight:600;color:#22aaff">
                Greedy Classical
              </span><br>
              <span style="font-size:.78rem;color:#6b7590">
                Priority-ranked greedy assignment
              </span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        ca1, ca2 = st.columns(2)
        ca1.metric("Benefit Score",  f"{c_res['benefit']:.4f}")
        ca2.metric("Zones Selected", f"{c_res['zones_selected']}")
        ca3, ca4 = st.columns(2)
        ca3.metric("Risk Coverage",  f"{c_res['benefit']/weights.sum()*100:.1f}%")
        ca4.metric("Method",         "Greedy")
        st.markdown("**Allocated zones:**")
        for i, (_, row) in enumerate(df.iterrows()):
            if c_alloc[i]:
                st.markdown(f"✅ {row['icon']} {row['zone']}  `{row['priority']:.3f}`")

    st.divider()

    # ── Charts (only when QAOA results exist) ────────────────────────────
    if has_qaoa:
        q_res   = st.session_state["qaoa_result"]
        q_alloc = q_res["allocation"]

        st.markdown('<div class="sec-title">📈 Allocation Comparison Charts</div>',
                    unsafe_allow_html=True)
        ch1, ch2 = st.columns(2)

        with ch1:
            # Grouped bar: selected vs not per zone
            fig1 = go.Figure()
            fig1.add_trace(go.Bar(
                name="⚛️ QAOA", x=df["zone"], y=q_alloc,
                marker_color=["#ff6b35" if v else "#1a2035" for v in q_alloc],
                text=["✅" if v else "⬜" for v in q_alloc],
                textposition="auto",
            ))
            fig1.add_trace(go.Bar(
                name="🖥️ Classical", x=df["zone"], y=c_alloc,
                marker_color=["#22aaff" if v else "#1a2035" for v in c_alloc],
                text=["✅" if v else "⬜" for v in c_alloc],
                textposition="auto",
            ))
            fig1.update_layout(
                **_PLAYOUT,
                title="Zone Selection: QAOA vs Classical",
                barmode="group",
                yaxis=dict(range=[0, 1.4], showticklabels=False, showgrid=False),
                xaxis=dict(showgrid=False),
            )
            st.plotly_chart(fig1, use_container_width=True)

        with ch2:
            # Performance metrics grouped bar
            metrics = ["Benefit Score", "Risk Coverage (%)", "Zones Selected"]
            qaoa_vals = [
                q_res["benefit"],
                q_res["benefit"] / weights.sum() * 100,
                q_res["zones_selected"],
            ]
            cls_vals = [
                c_res["benefit"],
                c_res["benefit"] / weights.sum() * 100,
                c_res["zones_selected"],
            ]
            fig2 = go.Figure()
            fig2.add_trace(go.Bar(
                name="⚛️ QAOA", x=metrics, y=qaoa_vals,
                marker_color="#ff6b35",
                text=[f"{v:.3f}" if i < 2 else str(int(v)) for i, v in enumerate(qaoa_vals)],
                textposition="auto",
            ))
            fig2.add_trace(go.Bar(
                name="🖥️ Classical", x=metrics, y=cls_vals,
                marker_color="#22aaff",
                text=[f"{v:.3f}" if i < 2 else str(int(v)) for i, v in enumerate(cls_vals)],
                textposition="auto",
            ))
            fig2.update_layout(
                **_PLAYOUT,
                title="Performance Metrics Comparison",
                barmode="group",
                xaxis=dict(showgrid=False),
                yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,.04)"),
            )
            st.plotly_chart(fig2, use_container_width=True)

        # ── Comparison table ─────────────────────────────────────────────
        st.markdown('<div class="sec-title">🔎 Zone-by-Zone Breakdown</div>',
                    unsafe_allow_html=True)
        tbl = []
        for i, (_, row) in enumerate(df.iterrows()):
            tbl.append({
                "Zone":        f"{row['icon']} {row['zone']}",
                "Priority":    f"{row['priority']:.4f}",
                "Heat Risk":   f"{row['heat_risk']}/10",
                "Population":  f"{row['population']:,}",
                "QAOA":        "✅ Selected" if q_alloc[i] else "⬜ Skipped",
                "Classical":   "✅ Selected" if c_alloc[i] else "⬜ Skipped",
                "Agreement":   "🤝" if q_alloc[i] == c_alloc[i] else "🔀 Differ",
            })
        st.dataframe(pd.DataFrame(tbl), use_container_width=True, hide_index=True)

        # ── Agreement summary ─────────────────────────────────────────────
        agreement = int(sum(q_alloc[i] == c_alloc[i] for i in range(len(q_alloc))))
        ag1, ag2, ag3 = st.columns(3)
        ag1.metric("Zone Agreement", f"{agreement}/{TOTAL_ZONES} zones")
        ag2.metric("QAOA Benefit",       f"{q_res['benefit']:.4f}")
        ag3.metric("Classical Benefit",  f"{c_res['benefit']:.4f}")

        # ── Scientific analysis ───────────────────────────────────────────
        st.divider()
        st.markdown('<div class="sec-title">🔬 Scientific Analysis</div>', unsafe_allow_html=True)
        diff = q_res["benefit"] - c_res["benefit"]
        if abs(diff) < 1e-4:
            analysis = (
                "Both approaches achieved <strong>equivalent performance</strong> on this instance. "
                "For 5 zones, greedy reliably finds the optimal solution — this is expected and scientifically correct."
            )
            icon = "🤝"
        elif diff > 0:
            analysis = (
                f"QAOA achieved <strong>{diff:.4f} higher benefit</strong> this run. "
                "Note: QAOA results vary due to quantum randomness; re-running may yield different values."
            )
            icon = "⚛️"
        else:
            analysis = (
                f"Classical achieved <strong>{abs(diff):.4f} higher benefit</strong> — expected at small scale. "
                "Greedy is optimal for n = 5 and O(n log n) time. QAOA advantage grows with problem size."
            )
            icon = "📚"

        st.markdown(
            f"""
            <div class="info-quantum">
              {icon} <strong>Analysis:</strong> {analysis}
              <br><br>
              <strong>Scalability insight:</strong> For 5 zones the search space is
              only 2<sup>5</sup> = 32 bitstrings. At 50 zones it is 2<sup>50</sup> ≈ 10<sup>15</sup>
              — intractable for exhaustive search. QAOA explores this space via
              <em>quantum superposition</em> and <em>entanglement</em>, making it a
              promising approach for real-world campus deployments with hundreds of zones.
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            "<div class='info-quantum'>Run the <strong>Quantum Optimizer</strong> "
            "to unlock the full comparison charts and analysis.</div>",
            unsafe_allow_html=True,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Router
# ─────────────────────────────────────────────────────────────────────────────
if page == "🌡️ Heat-Risk Dashboard":
    page_dashboard()
elif page == "⚛️ Quantum Optimizer":
    page_quantum()
else:
    page_comparison()


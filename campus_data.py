"""
campus_data.py
Simulated campus zone data for HEATSHIELD-Q.
Five zones with population, heat-risk, and vulnerability scores.
"""
import pandas as pd
import numpy as np


def get_campus_data() -> pd.DataFrame:
    """Return a DataFrame with campus zone heat-risk data."""
    data = {
        "zone_id": [0, 1, 2, 3, 4],
        "zone": [
            "Library",
            "Student Union",
            "Sports Complex",
            "Dormitory A",
            "Science Building",
        ],
        "icon": ["📚", "🍽️", "🏃", "🏠", "🔬"],
        # Estimated occupant count during peak heat hours
        "population": [800, 1200, 600, 1500, 400],
        # Heat-risk score: 1 (cool/shaded) – 10 (direct sun, concrete, no shade)
        "heat_risk": [7, 8, 9, 6, 7],
        # Vulnerability score: 1 (healthy adults) – 10 (elderly, medical needs)
        "vulnerability": [6, 7, 5, 8, 7],
    }

    df = pd.DataFrame(data)

    # ── Derived metrics ─────────────────────────────────────────────────────
    pop_max = df["population"].max()

    # Normalised versions (0-1 scale)
    df["pop_norm"] = df["population"] / pop_max
    df["risk_norm"] = df["heat_risk"] / 10.0
    df["vuln_norm"] = df["vulnerability"] / 10.0

    # Priority score: higher → zone needs a cooling resource more urgently
    #   40 % weight on population, 40 % on heat-risk, 20 % on vulnerability
    df["priority"] = (
        0.40 * df["pop_norm"]
        + 0.40 * df["risk_norm"]
        + 0.20 * df["vuln_norm"]
    )

    # Composite risk (for display purposes)
    df["composite_risk"] = (
        0.5 * df["heat_risk"]
        + 0.3 * df["vulnerability"]
        + 0.2 * df["pop_norm"] * 10
    ).round(2)

    return df.reset_index(drop=True)


# ── Module-level constants (imported by app.py) ──────────────────────────────
CAMPUS_ZONES: pd.DataFrame = get_campus_data()
RESOURCE_BUDGET: int = 3          # cooling stations available
TOTAL_ZONES: int = len(CAMPUS_ZONES)

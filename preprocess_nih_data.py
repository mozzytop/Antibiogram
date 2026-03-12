"""
preprocess_nih_data.py
======================
Run this script ONCE on your local machine to pre-process the NIH AMR
susceptibility data (NIH ABX.csv) into a compact summary CSV.

The output CSV contains per-organism-group, per-antibiotic susceptibility
percentages — small enough for Streamlit Cloud.

Usage:
    python3 preprocess_nih_data.py
"""

import os
import pandas as pd

# ── Locate the NIH CSV ──────────────────────────────────────────────────────
INPUT_PATHS = [
    "NIH ABX.csv",
    "../NIH ABX.csv",
    os.path.expanduser("~/Desktop/NIH ABX.csv"),
]

input_path = None
for p in INPUT_PATHS:
    if os.path.exists(p):
        input_path = p
        break

if input_path is None:
    print("ERROR: Could not find 'NIH ABX.csv'.")
    print("Place it in this directory or on your Desktop.")
    raise SystemExit(1)

print(f"Reading {input_path} (this may take a moment)...")

# The file has a comment header line starting with #
# Columns: Measurement sign, BioSample, Organism group, Scientific name,
#           Antibiotic, Resistance phenotype, Testing standard
df = pd.read_csv(input_path, comment="#")
df.columns = [
    "measurement_sign", "biosample", "organism_group",
    "scientific_name", "antibiotic", "resistance_phenotype",
    "testing_standard",
]

print(f"  Loaded {len(df):,} rows, {df['organism_group'].nunique()} organism groups, "
      f"{df['antibiotic'].nunique()} antibiotics")

# ── Filter out "not defined" phenotypes ─────────────────────────────────────
df = df[df["resistance_phenotype"].isin(["susceptible", "intermediate", "resistant",
                                          "susceptible-dose dependent", "nonsusceptible"])]

# Normalize phenotypes: merge "susceptible-dose dependent" into "intermediate",
# "nonsusceptible" into "resistant"
df["resistance_phenotype"] = df["resistance_phenotype"].replace({
    "susceptible-dose dependent": "intermediate",
    "nonsusceptible": "resistant",
})

print(f"  After filtering: {len(df):,} rows with defined phenotypes")

# ── Aggregate: per organism_group × antibiotic ──────────────────────────────
grouped = df.groupby(["organism_group", "antibiotic"])

summary_rows = []
for (org, abx), grp in grouped:
    total = len(grp)
    if total < 3:  # Skip tiny sample sizes
        continue
    s = (grp["resistance_phenotype"] == "susceptible").sum()
    i = (grp["resistance_phenotype"] == "intermediate").sum()
    r = (grp["resistance_phenotype"] == "resistant").sum()
    summary_rows.append({
        "organism_group": org,
        "antibiotic": abx,
        "n_isolates": total,
        "pct_susceptible": round(100.0 * s / total, 1),
        "pct_intermediate": round(100.0 * i / total, 1),
        "pct_resistant": round(100.0 * r / total, 1),
    })

summary = pd.DataFrame(summary_rows)

# ── Save ────────────────────────────────────────────────────────────────────
os.makedirs("data", exist_ok=True)
out_path = "data/nih_susceptibility_summary.csv"
summary.to_csv(out_path, index=False)

print(f"\n  Done! {out_path}  ({len(summary):,} rows, "
      f"{summary['organism_group'].nunique()} organisms, "
      f"{summary['antibiotic'].nunique()} antibiotics)")
print("  Commit the data/ folder to your repo.")

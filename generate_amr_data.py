"""
generate_amr_data.py
====================
Run this script ONCE on your local machine (where the AMR Python package is installed).
It exports the AMR package's databases to CSV files that get committed to your repo.
The main Streamlit app reads these CSVs — no R needed at runtime on Streamlit Cloud.

Usage:
    python generate_amr_data.py
"""

import os
import pandas as pd

print("Loading AMR package (this may take a moment — R is initializing)...")
import AMR

os.makedirs("data", exist_ok=True)

datasets = {
    "amr_microorganisms":    AMR.microorganisms,
    "amr_antimicrobials":    AMR.antimicrobials,
    "amr_clinical_breakpoints": AMR.clinical_breakpoints,
}

for name, df in datasets.items():
    path = f"data/{name}.csv"
    df.to_csv(path, index=False)
    print(f"  ✓  {path}  ({len(df):,} rows)")

# Also pre-compute a useful summary: top organisms by prevalence
top_orgs = (
    AMR.microorganisms
    .query("kingdom in ['Bacteria', 'Fungi'] and status == 'accepted'")
    .sort_values("prevalence")
    .head(500)[["mo", "fullname", "genus", "species", "kingdom", "phylum", "class",
                "gramstain" if "gramstain" in AMR.microorganisms.columns else "fullname"]]
)
top_orgs.to_csv("data/amr_top_organisms.csv", index=False)
print(f"  ✓  data/amr_top_organisms.csv  ({len(top_orgs):,} rows)")

print("\nAll done! Commit the data/ folder to your repo.")
print("Streamlit Cloud will read these CSVs without needing R installed.")

# Bugs & Drugs — Antimicrobial Stewardship Tool

## What's New in This Version

### Tab 1: Sensitivity Grid (New)
- 70+ organisms × 32 antibiotics, Sanford Guide-style color-coded matrix
- Hover any cell for antibiotic/organism context
- Filter by organism group, antibiotic class, or free-text search
- Sticky headers for easy scrolling

### Tab 2: Treatment Details (Existing + Expanded)
- Tiered therapy profiles with US dosing for bacteria, fungi, viruses
- MDR Focus toggle for salvage regimens
- PDF export

### Tab 3: Organism Search — AMR Database (New)
- Full AMR (for R) taxonomy database: 78,000+ taxa
- Clinical breakpoints (EUCAST/CLSI)
- Requires one-time setup (see below)

---

## Setup: AMR Database Integration

The AMR database tab reads pre-exported CSV files from the `data/` folder.
These are generated from the AMR Python package (which requires R).

**Run this once on your local machine:**

```bash
# 1. Install AMR Python package (requires R to be installed)
pip install AMR

# 2. Export AMR data to CSV files
python generate_amr_data.py
```

This creates:
- `data/amr_microorganisms.csv`
- `data/amr_antimicrobials.csv`
- `data/amr_clinical_breakpoints.csv`
- `data/amr_top_organisms.csv`

**Then commit the `data/` folder to your repo.** Streamlit Cloud reads the CSVs
directly — no R installation needed at runtime.

---

## Deploying to Streamlit Cloud

1. Push all files (including `data/` CSVs) to GitHub
2. Connect your repo at [share.streamlit.io](https://share.streamlit.io)
3. Set main file: `app.py`
4. No special `packages.txt` needed (R is not required at runtime)

---

## Running Locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

---

## Sensitivity Data Sources

- Sanford Guide 2024
- IDSA Guidelines (MRSA, Candidiasis, CDiff, etc.)
- CDC treatment recommendations
- ASHP Clinical Practice Guidelines

> **For clinical decision support only. Always correlate with local antibiogram and patient factors.**

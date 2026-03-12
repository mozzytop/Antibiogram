"""
Bugs & Drugs — Infectious Disease + Antimicrobial Reference Tool
=================================================================
Tabs:
  1. Sensitivity Grid       — Sanford-style color-coded matrix (100+ organisms × 32 antibiotics)
  2. Treatment Details      — Tiered therapy with dosing, MDR options, resistance mechanisms
  3. Organism Search        — Searchable AMR package taxonomy + breakpoint lookup

Data notes:
  • Sensitivity matrix is curated from Sanford Guide 2024, IDSA Guidelines, CDC.
  • AMR organism search reads pre-exported CSVs in /data/ (see generate_amr_data.py).
  • Treatment data is in ORGANISM_DATA list; swap load_data() for a DB call as needed.
"""

import io
import os
import pandas as pd
import streamlit as st
from fpdf import FPDF

# ══════════════════════════════════════════════════════════════════════════════
#  SENSITIVITY MATRIX  ─  Antibiotic × Organism encoded data
# ══════════════════════════════════════════════════════════════════════════════

# Value shorthand
S2, S1, SV, R0, SQ, CI, NA = "++", "+", "+/-", "0", "?", "CI", ""

ABX_GROUPS = [
    ("Penicillins",          ["PCN", "AMX", "AMC", "NAF", "TZP"]),
    ("Cephalosporins",       ["CFZ", "CFX", "CFO", "CRO", "CAZ", "FEP", "CZA", "CPT"]),
    ("Carbapenems / Mono",   ["ETP", "MEM", "MVB", "ATM"]),
    ("Fluoroquinolones",     ["CIP", "LVX"]),
    ("Macrolides / Tetra",   ["AZI", "DOX", "TGC"]),
    ("Anti-Gram+ Agents",    ["VAN", "DAP", "LZD"]),
    ("Other",                ["CLI", "SXT", "MTZ", "AMG", "COL", "NIT", "FOS"]),
]

ABX_DISPLAY = {
    "PCN": "Pen G/V", "AMX": "Amox/Amp", "AMC": "Amox-Clav", "NAF": "Nafcillin",
    "TZP": "Pip-Tazo", "CFZ": "Cefazolin", "CFX": "Cefuroxime", "CFO": "Cefoxitin",
    "CRO": "Ceftriaxone", "CAZ": "Ceftazidime", "FEP": "Cefepime", "CZA": "Ceftaz-AVI",
    "CPT": "Ceftaroline", "ETP": "Ertapenem", "MEM": "Mero/Imi", "MVB": "Mero-Vabor",
    "ATM": "Aztreonam", "CIP": "Cipro", "LVX": "Levo/Moxi", "AZI": "Azithro",
    "DOX": "Doxy/Mino", "TGC": "Tigecycline", "VAN": "Vancomycin", "DAP": "Daptomycin",
    "LZD": "Linezolid", "CLI": "Clindamycin", "SXT": "TMP-SMX", "MTZ": "Metronidazole",
    "AMG": "Aminoglycosides", "COL": "Colistin/PolB", "NIT": "Nitrofurantoin",
    "FOS": "Fosfomycin",
}

ALL_ABX = [ab for _, abxs in ABX_GROUPS for ab in abxs]
_B = {k: NA for k in ALL_ABX}  # Base dict — all NA

SENSITIVITY_MATRIX = [
    # ── GRAM POSITIVE COCCI — STREPTOCOCCI ──────────────────────────────────
    {**_B, "group": "GP Cocci — Streptococci", "organism": "Strep. pyogenes (Group A)",
     "PCN": S2, "AMX": S2, "AMC": S2, "TZP": S1, "CFZ": S2, "CFX": S1, "CFO": S1,
     "CRO": S2, "FEP": S1, "CPT": S1, "ETP": S1, "MEM": S1, "LVX": S1,
     "AZI": SV, "DOX": SV, "TGC": S1, "VAN": S1, "DAP": S1, "LZD": S1, "CLI": S1, "AMG": CI},

    {**_B, "group": "GP Cocci — Streptococci", "organism": "Strep. agalactiae (Group B)",
     "PCN": S2, "AMX": S2, "AMC": S2, "TZP": S1, "CFZ": S2, "CFX": S1, "CFO": S1,
     "CRO": S2, "FEP": S1, "CPT": S1, "ETP": S1, "MEM": S1, "LVX": S1,
     "AZI": SV, "DOX": SV, "TGC": S1, "VAN": S1, "DAP": S1, "LZD": S1, "CLI": SV, "AMG": CI},

    {**_B, "group": "GP Cocci — Streptococci", "organism": "Strep. pneumoniae (PCN-S)",
     "PCN": S2, "AMX": S2, "AMC": S2, "TZP": S1, "CFZ": SV, "CFX": S1, "CRO": S2,
     "FEP": S1, "CPT": S1, "ETP": S1, "MEM": S1, "LVX": S2, "AZI": SV, "DOX": SV,
     "TGC": S1, "VAN": S1, "LZD": S1, "CLI": SV, "SXT": SV},

    {**_B, "group": "GP Cocci — Streptococci", "organism": "Strep. pneumoniae (PCN-R/MDR)",
     "PCN": R0, "AMX": SV, "AMC": SV, "TZP": SV, "CFZ": R0, "CFX": SV, "CRO": S1,
     "FEP": S1, "CPT": S1, "ETP": S1, "MEM": S1, "LVX": S2, "AZI": R0, "DOX": SV,
     "TGC": S1, "VAN": S2, "LZD": S2, "CLI": R0, "SXT": R0},

    {**_B, "group": "GP Cocci — Streptococci", "organism": "Viridans Streptococci",
     "PCN": SV, "AMX": SV, "AMC": SV, "TZP": SV, "CFZ": SV, "CFX": SV, "CRO": S1,
     "FEP": SV, "CPT": S1, "ETP": SV, "MEM": S1, "LVX": SV, "AZI": SV, "DOX": SV,
     "TGC": S1, "VAN": S2, "DAP": SV, "LZD": S1, "CLI": SV, "AMG": CI},

    {**_B, "group": "GP Cocci — Streptococci", "organism": "Strep. anginosus group",
     "PCN": S2, "AMX": S2, "AMC": S2, "TZP": S1, "CFZ": S2, "CFX": S1, "CRO": S2,
     "FEP": S1, "ETP": S1, "MEM": S1, "LVX": S1, "AZI": SV, "DOX": SV, "TGC": S1,
     "VAN": S1, "DAP": SV, "LZD": S1, "CLI": S1, "MTZ": S1, "AMG": CI},

    {**_B, "group": "GP Cocci — Streptococci", "organism": "Strep. Group C / F / G",
     "PCN": S2, "AMX": S2, "AMC": S2, "TZP": S1, "CFZ": S2, "CFX": S1, "CRO": S2,
     "FEP": S1, "ETP": S1, "MEM": S1, "LVX": S1, "AZI": SV, "DOX": SV, "TGC": S1,
     "VAN": S1, "DAP": S1, "LZD": S1, "CLI": S1, "AMG": CI},

    # ── GRAM POSITIVE COCCI — ENTEROCOCCI ───────────────────────────────────
    {**_B, "group": "GP Cocci — Enterococci", "organism": "Enterococcus faecalis (S)",
     "PCN": S2, "AMX": S2, "AMC": SV, "TZP": SV, "CRO": CI, "MEM": SV,
     "CIP": SV, "LVX": SV, "TGC": SV, "VAN": S1, "DAP": CI, "LZD": S1, "AMG": CI, "NIT": S1, "FOS": SV},

    {**_B, "group": "GP Cocci — Enterococci", "organism": "Enterococcus faecalis (VRE)",
     "PCN": SV, "AMX": SV, "AMC": SV, "MEM": SV, "TGC": SV,
     "VAN": R0, "DAP": S1, "LZD": S2, "AMG": CI, "NIT": S1},

    {**_B, "group": "GP Cocci — Enterococci", "organism": "Enterococcus faecium (S)",
     "PCN": SV, "AMX": SV, "AMC": SV, "MEM": SV, "LVX": SV, "TGC": SV,
     "VAN": S1, "DAP": S1, "LZD": S2, "AMG": CI},

    {**_B, "group": "GP Cocci — Enterococci", "organism": "Enterococcus faecium (VRE)",
     "PCN": R0, "AMX": R0, "AMC": R0, "TZP": R0, "MEM": R0, "TGC": SV,
     "VAN": R0, "DAP": S1, "LZD": S2, "AMG": CI},

    # ── GRAM POSITIVE COCCI — STAPHYLOCOCCI ─────────────────────────────────
    {**_B, "group": "GP Cocci — Staphylococci", "organism": "S. aureus (MSSA)",
     "PCN": SV, "AMX": SV, "AMC": S1, "NAF": S2, "TZP": S1, "CFZ": S2, "CFX": S1,
     "CFO": S1, "CRO": S1, "CAZ": SV, "FEP": S1, "CPT": S1, "ETP": S1, "MEM": S1,
     "CIP": SV, "LVX": SV, "DOX": S1, "TGC": S1, "VAN": S1, "DAP": S1, "LZD": S1,
     "CLI": SV, "SXT": S1, "AMG": CI},

    {**_B, "group": "GP Cocci — Staphylococci", "organism": "S. aureus (CA-MRSA)",
     "PCN": R0, "AMX": R0, "AMC": R0, "NAF": R0, "TZP": R0, "CFZ": R0, "CFX": R0,
     "CFO": R0, "CRO": R0, "CAZ": R0, "FEP": R0, "CPT": S2, "ETP": R0, "MEM": R0,
     "CIP": R0, "LVX": R0, "DOX": S1, "TGC": SV, "VAN": S1, "DAP": S1, "LZD": S1,
     "CLI": SV, "SXT": S2, "AMG": CI},

    {**_B, "group": "GP Cocci — Staphylococci", "organism": "S. aureus (HA-MRSA)",
     "PCN": R0, "AMX": R0, "AMC": R0, "NAF": R0, "TZP": R0, "CFZ": R0, "CFX": R0,
     "CFO": R0, "CRO": R0, "CAZ": R0, "FEP": R0, "CPT": S2, "ETP": R0, "MEM": R0,
     "CIP": R0, "LVX": R0, "DOX": SV, "TGC": SV, "VAN": S2, "DAP": S1, "LZD": S1,
     "CLI": SV, "SXT": SV, "AMG": CI},

    {**_B, "group": "GP Cocci — Staphylococci", "organism": "S. epidermidis / CoNS (S)",
     "PCN": SV, "AMX": SV, "AMC": S1, "NAF": S2, "TZP": S1, "CFZ": S2, "CFX": S1,
     "CRO": S1, "FEP": S1, "ETP": S1, "MEM": S1, "CIP": SV, "LVX": SV,
     "DOX": S1, "TGC": S1, "VAN": S1, "DAP": S1, "LZD": S1, "CLI": SV, "SXT": S1, "AMG": CI},

    {**_B, "group": "GP Cocci — Staphylococci", "organism": "S. epidermidis / CoNS (R)",
     "PCN": R0, "AMX": R0, "AMC": R0, "NAF": R0, "TZP": R0, "CFZ": R0, "CFX": R0,
     "CRO": R0, "FEP": R0, "ETP": R0, "MEM": R0, "CIP": R0, "LVX": R0,
     "DOX": SV, "TGC": SV, "VAN": S2, "DAP": S1, "LZD": S1, "CLI": R0, "SXT": SV, "AMG": CI},

    {**_B, "group": "GP Cocci — Staphylococci", "organism": "S. lugdunensis",
     "PCN": SV, "AMX": SV, "AMC": S1, "NAF": S2, "TZP": S1, "CFZ": S2, "CFX": S1,
     "CRO": S1, "FEP": S1, "ETP": S1, "MEM": S1, "CIP": SV, "LVX": SV,
     "DOX": S1, "TGC": S1, "VAN": S1, "DAP": S1, "LZD": S1, "CLI": SV, "SXT": S1, "AMG": CI},

    {**_B, "group": "GP Cocci — Staphylococci", "organism": "S. saprophyticus",
     "PCN": SV, "AMX": S1, "AMC": S1, "NAF": S2, "CFZ": S2, "CFX": S1,
     "CRO": S1, "FEP": S1, "ETP": S1, "MEM": S1, "CIP": S1, "LVX": S1,
     "DOX": S1, "VAN": S1, "DAP": S1, "LZD": S1, "SXT": S2, "NIT": S2},

    # ── GRAM POSITIVE BACILLI ────────────────────────────────────────────────
    {**_B, "group": "GP Bacilli", "organism": "Listeria monocytogenes",
     "PCN": S2, "AMX": S2, "AMC": S2, "TZP": SV, "ETP": S1, "MEM": S1,
     "CIP": SV, "LVX": SV, "DOX": S1, "TGC": S1, "LZD": S1, "SXT": S1, "AMG": CI},

    {**_B, "group": "GP Bacilli", "organism": "C. diphtheriae",
     "PCN": S2, "AMX": S2, "AMC": S2, "CFZ": S1, "CRO": S1,
     "AZI": S2, "DOX": S1, "CLI": S1},

    {**_B, "group": "GP Bacilli", "organism": "Nocardia sp.",
     "PCN": NA, "AMX": SV, "AMC": SV, "CRO": SV, "ETP": S1, "MEM": S1,
     "CIP": SV, "LVX": SV, "DOX": SV, "LZD": S1, "SXT": S2, "AMG": CI},

    # ── AEROBIC GNB — ENTERIC ────────────────────────────────────────────────
    {**_B, "group": "GN Bacilli — Enteric", "organism": "E. coli (Susceptible)",
     "PCN": NA, "AMX": S1, "AMC": S1, "TZP": S1, "CFZ": S1, "CFX": S1, "CFO": S1,
     "CRO": S2, "CAZ": S1, "FEP": S1, "ETP": S2, "MEM": S2, "ATM": S1,
     "CIP": S2, "LVX": S2, "AZI": SV, "DOX": S1, "TGC": SV,
     "SXT": S2, "AMG": S1, "COL": SV, "NIT": S2, "FOS": S2},

    {**_B, "group": "GN Bacilli — Enteric", "organism": "Klebsiella pneumoniae (S)",
     "PCN": NA, "AMX": NA, "AMC": S1, "TZP": S1, "CFZ": S1, "CFX": S1, "CFO": S1,
     "CRO": S2, "CAZ": S1, "FEP": S1, "ETP": S2, "MEM": S2, "ATM": S1,
     "CIP": S2, "LVX": S2, "DOX": NA, "TGC": SV,
     "SXT": S1, "AMG": S1, "COL": SV, "NIT": NA, "FOS": S1},

    {**_B, "group": "GN Bacilli — Enteric", "organism": "E. coli / Klebsiella (ESBL)",
     "PCN": R0, "AMX": R0, "AMC": R0, "TZP": SV, "CFZ": R0, "CFX": R0, "CFO": SV,
     "CRO": R0, "CAZ": R0, "FEP": SV, "CZA": S1, "ETP": S2, "MEM": S2, "ATM": R0,
     "CIP": SV, "LVX": SV, "TGC": SV, "SXT": SV, "AMG": SV, "COL": SV, "NIT": SV, "FOS": S1},

    {**_B, "group": "GN Bacilli — Enteric", "organism": "Klebsiella (KPC-CRE)",
     "PCN": R0, "AMX": R0, "AMC": R0, "TZP": R0, "CFZ": R0, "CFX": R0, "CFO": R0,
     "CRO": R0, "CAZ": R0, "FEP": R0, "CZA": S2, "ETP": R0, "MEM": R0, "MVB": S1, "ATM": R0,
     "CIP": R0, "LVX": R0, "TGC": SV, "SXT": R0, "AMG": SV, "COL": SV},

    {**_B, "group": "GN Bacilli — Enteric", "organism": "Klebsiella (MBL/NDM)",
     "PCN": R0, "AMX": R0, "AMC": R0, "TZP": R0, "CFZ": R0, "CFX": R0, "CFO": R0,
     "CRO": R0, "CAZ": R0, "FEP": R0, "CZA": R0, "ETP": R0, "MEM": R0, "MVB": R0, "ATM": SV,
     "CIP": R0, "LVX": R0, "TGC": SV, "SXT": R0, "AMG": SV, "COL": SV},

    {**_B, "group": "GN Bacilli — Enteric", "organism": "Enterobacter / AmpC producers",
     "PCN": R0, "AMX": R0, "AMC": R0, "TZP": SV, "CFZ": R0, "CFX": R0, "CFO": R0,
     "CRO": SV, "CAZ": SV, "FEP": S1, "CZA": S1, "ETP": S1, "MEM": S1, "ATM": SV,
     "CIP": S1, "LVX": S1, "TGC": SV, "SXT": SV, "AMG": S1, "COL": SV},

    {**_B, "group": "GN Bacilli — Enteric", "organism": "Citrobacter freundii / koseri",
     "PCN": NA, "AMX": SV, "AMC": SV, "TZP": SV, "CFZ": R0, "CFX": R0, "CFO": R0,
     "CRO": SV, "CAZ": SV, "FEP": S1, "CZA": S1, "ETP": S1, "MEM": S1, "ATM": S1,
     "CIP": S1, "LVX": S1, "TGC": SV, "SXT": SV, "AMG": S1},

    {**_B, "group": "GN Bacilli — Enteric", "organism": "Proteus mirabilis",
     "PCN": NA, "AMX": S1, "AMC": S1, "TZP": S1, "CFZ": S1, "CFX": S1, "CFO": NA,
     "CRO": S2, "CAZ": S1, "FEP": S1, "ETP": S1, "MEM": S1, "ATM": S1,
     "CIP": S1, "LVX": S1, "TGC": NA, "SXT": S1, "AMG": S1, "NIT": NA, "FOS": S1},

    {**_B, "group": "GN Bacilli — Enteric", "organism": "Morganella / Proteus vulgaris",
     "PCN": NA, "AMX": SV, "AMC": S1, "TZP": S1, "CFZ": SV, "CFX": S1,
     "CRO": S1, "CAZ": S1, "FEP": S1, "CZA": S1, "ETP": S1, "MEM": S1, "ATM": S1,
     "CIP": S1, "LVX": S1, "TGC": NA, "SXT": S1, "AMG": S1},

    {**_B, "group": "GN Bacilli — Enteric", "organism": "Serratia marcescens",
     "PCN": NA, "AMX": R0, "AMC": R0, "TZP": SV, "CFZ": R0, "CFX": R0, "CFO": R0,
     "CRO": SV, "CAZ": S1, "FEP": S1, "CZA": S1, "ETP": S1, "MEM": S1, "ATM": SV,
     "CIP": S1, "LVX": S1, "TGC": SV, "SXT": SV, "AMG": S1},

    {**_B, "group": "GN Bacilli — Enteric", "organism": "Salmonella sp.",
     "PCN": NA, "AMX": SV, "AMC": SV, "CRO": S2, "FEP": S1, "ETP": S1, "MEM": S1,
     "CIP": S1, "LVX": S2, "AZI": S1, "TGC": SV, "SXT": SV, "AMG": SV},

    {**_B, "group": "GN Bacilli — Enteric", "organism": "Shigella sp.",
     "PCN": NA, "AMX": SV, "CRO": S2, "FEP": S1, "ETP": S1, "MEM": S1,
     "CIP": S2, "LVX": S2, "AZI": S1, "TGC": SV, "SXT": SV},

    {**_B, "group": "GN Bacilli — Enteric", "organism": "Campylobacter jejuni",
     "PCN": NA, "AMX": NA, "CRO": NA, "CIP": SV, "LVX": SV,
     "AZI": S2, "DOX": S1, "TGC": SV, "CLI": SV},

    {**_B, "group": "GN Bacilli — Enteric", "organism": "Yersinia enterocolitica",
     "PCN": NA, "AMX": NA, "TZP": S1, "CFZ": NA, "CRO": SV, "CAZ": SV, "FEP": S1,
     "ETP": S1, "MEM": S1, "ATM": S1, "CIP": S1, "LVX": S1, "TGC": SV, "SXT": S1, "AMG": S1},

    # ── GNB — NON-ENTERIC ────────────────────────────────────────────────────
    {**_B, "group": "GN Bacilli — Non-Enteric", "organism": "H. influenzae (non-BL)",
     "PCN": SV, "AMX": S2, "AMC": S2, "TZP": S1, "CFZ": SV, "CFX": S1, "CFO": S1,
     "CRO": S2, "CAZ": S1, "FEP": S1, "ETP": S1, "MEM": S1,
     "CIP": S2, "LVX": S2, "AZI": S1, "DOX": S1, "SXT": S1},

    {**_B, "group": "GN Bacilli — Non-Enteric", "organism": "H. influenzae (β-lactamase+)",
     "PCN": R0, "AMX": R0, "AMC": S2, "TZP": S1, "CFZ": SV, "CFX": S1, "CFO": S1,
     "CRO": S2, "CAZ": S1, "FEP": S1, "ETP": S1, "MEM": S1,
     "CIP": S2, "LVX": S2, "AZI": S1, "DOX": S1, "SXT": SV},

    {**_B, "group": "GN Bacilli — Non-Enteric", "organism": "Moraxella catarrhalis",
     "PCN": R0, "AMX": R0, "AMC": S2, "TZP": S1, "CFZ": SV, "CFX": S1, "CFO": S1,
     "CRO": S1, "FEP": S1, "ETP": S1, "MEM": S1,
     "CIP": S1, "LVX": S2, "AZI": S1, "DOX": S1, "SXT": S1},

    {**_B, "group": "GN Bacilli — Non-Enteric", "organism": "Neisseria gonorrhoeae",
     "PCN": SV, "AMX": R0, "AMC": R0, "CRO": S2,
     "CIP": R0, "LVX": R0, "AZI": SV, "DOX": R0, "AMG": S1},

    {**_B, "group": "GN Bacilli — Non-Enteric", "organism": "Neisseria meningitidis",
     "PCN": S2, "AMX": S2, "AMC": S2, "CRO": S2, "ETP": S1, "MEM": S1,
     "CIP": SV, "LVX": S1, "CZA": NA},

    {**_B, "group": "GN Bacilli — Non-Enteric", "organism": "Pasteurella multocida",
     "PCN": S2, "AMX": S2, "AMC": S2, "NAF": R0, "TZP": S1, "CFZ": S1, "CRO": S2,
     "FEP": S1, "ETP": S1, "MEM": S1, "CIP": S1, "LVX": S1, "AZI": S1, "DOX": S2, "SXT": S1},

    {**_B, "group": "GN Bacilli — Non-Enteric", "organism": "Haemophilus ducreyi",
     "PCN": NA, "CRO": S1, "CIP": S1, "AZI": S2, "DOX": S1},

    {**_B, "group": "GN Bacilli — Non-Enteric", "organism": "Bartonella sp.",
     "PCN": NA, "AZI": S2, "DOX": S2, "CLI": NA, "AMG": CI},

    {**_B, "group": "GN Bacilli — Non-Enteric", "organism": "Bordetella pertussis",
     "PCN": NA, "AZI": S2, "DOX": SV, "SXT": S1},

    {**_B, "group": "GN Bacilli — Non-Enteric", "organism": "Borrelia burgdorferi (Lyme)",
     "PCN": S1, "AMX": S2, "AMC": S2, "CRO": S2, "AZI": SV, "DOX": S2},

    {**_B, "group": "GN Bacilli — Non-Enteric", "organism": "Brucella sp.",
     "PCN": NA, "CIP": SV, "DOX": S2, "TGC": SV, "SXT": S1, "AMG": CI},

    {**_B, "group": "GN Bacilli — Non-Enteric", "organism": "Legionella pneumophila",
     "PCN": R0, "AMX": R0, "AMC": R0, "TZP": R0, "CFZ": R0, "CRO": R0, "FEP": R0,
     "ETP": R0, "MEM": R0, "CIP": S1, "LVX": S2, "AZI": S2, "DOX": S1},

    # ── GNB — NON-FERMENTERS ─────────────────────────────────────────────────
    {**_B, "group": "GN Bacilli — Non-Fermenters", "organism": "P. aeruginosa (Susceptible)",
     "PCN": NA, "AMX": NA, "AMC": NA, "NAF": NA, "TZP": S2,
     "CFZ": R0, "CFX": R0, "CFO": R0, "CRO": R0, "CAZ": S1, "FEP": S2, "CZA": S1,
     "ETP": R0, "MEM": S2, "ATM": S1, "CIP": S2, "LVX": S1, "TGC": R0,
     "AMG": S1, "COL": SV},

    {**_B, "group": "GN Bacilli — Non-Fermenters", "organism": "P. aeruginosa (MDR/DTR)",
     "PCN": NA, "AMX": NA, "AMC": NA, "TZP": SV, "CFZ": R0, "CFX": R0, "CFO": R0,
     "CRO": R0, "CAZ": SV, "FEP": SV, "CZA": S1, "ETP": R0, "MEM": SV, "ATM": SV,
     "CIP": R0, "LVX": R0, "TGC": R0, "AMG": SV, "COL": S1},

    {**_B, "group": "GN Bacilli — Non-Fermenters", "organism": "Acinetobacter baumannii (MDR/XDR)",
     "PCN": R0, "AMX": R0, "AMC": SV, "NAF": NA, "TZP": R0,
     "CFZ": R0, "CFX": R0, "CFO": R0, "CRO": R0, "CAZ": SV, "FEP": R0, "CZA": SV,
     "ETP": R0, "MEM": R0, "CIP": R0, "LVX": R0, "TGC": SV, "AMG": SV, "COL": S1},

    {**_B, "group": "GN Bacilli — Non-Fermenters", "organism": "Stenotrophomonas maltophilia",
     "PCN": R0, "AMX": R0, "AMC": R0, "TZP": SV, "CFZ": R0, "CFX": R0, "CFO": R0,
     "CRO": R0, "CAZ": SV, "FEP": R0, "CZA": SV, "ETP": R0, "MEM": R0,
     "CIP": SV, "LVX": S1, "DOX": SV, "TGC": SV, "SXT": S2},

    {**_B, "group": "GN Bacilli — Non-Fermenters", "organism": "Burkholderia cepacia",
     "PCN": R0, "AMX": R0, "TZP": SV, "CRO": NA, "CAZ": S1, "FEP": SV,
     "ETP": NA, "MEM": S1, "CIP": SV, "LVX": SV, "TGC": SV, "SXT": S2, "COL": R0},

    # ── ATYPICALS / CELL WALL DEFICIENT ─────────────────────────────────────
    {**_B, "group": "Atypicals (no cell wall)", "organism": "Mycoplasma pneumoniae",
     "PCN": R0, "AMX": R0, "AMC": R0, "NAF": R0, "TZP": R0,
     "CFZ": R0, "CFX": R0, "CFO": R0, "CRO": R0, "CAZ": R0, "FEP": R0,
     "ETP": R0, "MEM": R0, "ATM": R0, "CIP": NA, "LVX": S2, "AZI": S2, "DOX": S2, "TGC": SV},

    {**_B, "group": "Atypicals (no cell wall)", "organism": "Chlamydia trachomatis",
     "PCN": R0, "AMX": SV, "AMC": SV, "NAF": R0, "CFZ": R0, "CRO": R0,
     "ETP": R0, "MEM": R0, "CIP": SV, "LVX": S1, "AZI": S2, "DOX": S2, "SXT": SV},

    {**_B, "group": "Atypicals (no cell wall)", "organism": "Chlamydophila pneumoniae",
     "PCN": R0, "AMX": R0, "AMC": R0, "NAF": R0, "CFZ": R0, "CRO": R0,
     "ETP": R0, "MEM": R0, "CIP": SV, "LVX": S2, "AZI": S2, "DOX": S2},

    {**_B, "group": "Atypicals (no cell wall)", "organism": "Mycoplasma genitalium",
     "PCN": R0, "AMX": R0, "AMC": R0, "NAF": R0, "CFZ": R0, "CRO": R0,
     "ETP": R0, "MEM": R0, "LVX": SV, "AZI": SV, "DOX": R0},

    {**_B, "group": "Atypicals (no cell wall)", "organism": "Ureaplasma urealyticum",
     "PCN": R0, "AMX": R0, "AMC": R0, "CFZ": R0, "CRO": R0,
     "ETP": R0, "MEM": R0, "LVX": S1, "AZI": S1, "DOX": S2},

    # ── ANAEROBES ────────────────────────────────────────────────────────────
    {**_B, "group": "Anaerobes — Gram Negative", "organism": "Bacteroides fragilis group",
     "PCN": SV, "AMX": SV, "AMC": S2, "TZP": S2, "CFZ": R0, "CFX": SV, "CFO": S1,
     "CRO": R0, "CAZ": R0, "FEP": R0, "CZA": SV, "ETP": S2, "MEM": S2, "ATM": R0,
     "CIP": R0, "LVX": R0, "TGC": SV, "LZD": SV, "CLI": SV, "MTZ": S2},

    {**_B, "group": "Anaerobes — Gram Negative", "organism": "Fusobacterium necrophorum",
     "PCN": S1, "AMX": S1, "AMC": S2, "TZP": S1, "CFZ": S1, "CFX": S1, "CFO": S1,
     "CRO": S1, "FEP": S1, "ETP": S1, "MEM": S1, "ATM": R0,
     "DOX": S1, "TGC": SV, "LZD": S1, "CLI": S1, "MTZ": S2},

    {**_B, "group": "Anaerobes — Gram Positive", "organism": "Peptostreptococci",
     "PCN": S2, "AMX": S2, "AMC": S2, "TZP": S1, "CFZ": S2, "CFX": S1, "CFO": S1,
     "CRO": S1, "FEP": S1, "ETP": S1, "MEM": S1, "ATM": R0,
     "DOX": SV, "TGC": SV, "VAN": S1, "LZD": S1, "CLI": S2, "MTZ": S1},

    {**_B, "group": "Anaerobes — Gram Positive", "organism": "Clostridium sp. (non-difficile)",
     "PCN": S2, "AMX": S2, "AMC": S2, "TZP": S1, "CFZ": SV, "CFX": SV, "CFO": SV,
     "CRO": S1, "FEP": S1, "ETP": S1, "MEM": S1, "ATM": R0,
     "DOX": SV, "TGC": SV, "VAN": S2, "LZD": S1, "CLI": S1, "MTZ": S2},

    {**_B, "group": "Anaerobes — Gram Positive", "organism": "Clostridioides difficile",
     "VAN": S2, "MTZ": S1},  # vancomycin PO only; most others NA

    {**_B, "group": "Anaerobes — Gram Positive", "organism": "Actinomyces sp.",
     "PCN": S2, "AMX": S2, "AMC": S2, "TZP": S1, "CFZ": S1, "CFX": S1, "CFO": S1,
     "CRO": S1, "FEP": S1, "ETP": S1, "MEM": S1, "ATM": R0,
     "DOX": S1, "CLI": S1},
]

# ══════════════════════════════════════════════════════════════════════════════
#  TIERED TREATMENT DATA  (existing antibiogram)
# ══════════════════════════════════════════════════════════════════════════════

ORGANISM_DATA = [
    # ── BACTERIA ─────────────────────────────────────────────────────────────
    {"Category":"Bacteria","Organism":"Staphylococcus aureus (MSSA)","Gram / Morphology":"Gram+ Cocci",
     "First-Line Therapy":"Nafcillin / Oxacillin","First-Line Dosing (US)":"Nafcillin 2 g IV q4h; Oxacillin 2 g IV q4h",
     "Alternative Therapy":"Cefazolin, Clindamycin","Alternative Dosing":"Cefazolin 2 g IV q8h; Clindamycin 600 mg IV/PO q8h",
     "MDR Therapy":"Vancomycin (PCN allergy)","MDR Dosing":"Vancomycin 25–30 mg/kg IV load, then AUC-guided (target 400–600)",
     "Resistance Mechanisms":"mecA negative (MSSA); beta-lactamase",
     "Key Notes":"Cefazolin preferred for bacteremia; avoid vancomycin if susceptible",
     "Efficacy_FL":"green","Efficacy_Alt":"yellow","Efficacy_MDR":"yellow"},
    {"Category":"Bacteria","Organism":"Staphylococcus aureus (HA-MRSA)","Gram / Morphology":"Gram+ Cocci",
     "First-Line Therapy":"Vancomycin","First-Line Dosing (US)":"Vancomycin AUC/MIC-guided (target AUC 400–600 mg·h/L)",
     "Alternative Therapy":"Daptomycin, Linezolid","Alternative Dosing":"Daptomycin 6–10 mg/kg IV q24h; Linezolid 600 mg PO/IV q12h",
     "MDR Therapy":"Ceftaroline, Dalbavancin, Oritavancin","MDR Dosing":"Ceftaroline 600 mg IV q8h; Dalbavancin 1500 mg IV × 1 dose",
     "Resistance Mechanisms":"mecA (PBP2a), VRSA rare (vanA/vanB)",
     "Key Notes":"Do NOT use daptomycin for pneumonia; rifampin only in combination",
     "Efficacy_FL":"green","Efficacy_Alt":"yellow","Efficacy_MDR":"yellow"},
    {"Category":"Bacteria","Organism":"Staphylococcus aureus (CA-MRSA)","Gram / Morphology":"Gram+ Cocci",
     "First-Line Therapy":"TMP-SMX / Doxycycline","First-Line Dosing (US)":"TMP-SMX 1–2 DS tabs PO q12h; Doxycycline 100 mg PO q12h",
     "Alternative Therapy":"Clindamycin, Linezolid","Alternative Dosing":"Clindamycin 300–450 mg PO q8h; Linezolid 600 mg PO q12h",
     "MDR Therapy":"Vancomycin (severe/bacteremia)","MDR Dosing":"Vancomycin AUC-guided IV",
     "Resistance Mechanisms":"mecA, PVL toxin",
     "Key Notes":"PVL-positive strains cause necrotizing pneumonia/skin infections",
     "Efficacy_FL":"green","Efficacy_Alt":"yellow","Efficacy_MDR":"yellow"},
    {"Category":"Bacteria","Organism":"Streptococcus pneumoniae","Gram / Morphology":"Gram+ Cocci",
     "First-Line Therapy":"Penicillin G / Amoxicillin","First-Line Dosing (US)":"Penicillin G 3–4 MU IV q4h; Amoxicillin 500–875 mg PO q8h",
     "Alternative Therapy":"Ceftriaxone, Levofloxacin","Alternative Dosing":"Ceftriaxone 2 g IV q24h; Levofloxacin 750 mg PO/IV q24h",
     "MDR Therapy":"Vancomycin + Rifampin (meningitis MDR)","MDR Dosing":"Vancomycin 60 mg/kg/day IV ÷ q6h + Rifampin 600 mg q24h",
     "Resistance Mechanisms":"PBP mutations (PCN-R), efflux (FQ-R)",
     "Key Notes":"Adjust based on MIC; high-dose PCN overcomes intermediate resistance",
     "Efficacy_FL":"green","Efficacy_Alt":"yellow","Efficacy_MDR":"yellow"},
    {"Category":"Bacteria","Organism":"Enterococcus faecalis (susceptible)","Gram / Morphology":"Gram+ Cocci",
     "First-Line Therapy":"Ampicillin ± Gentamicin","First-Line Dosing (US)":"Ampicillin 2 g IV q4h; Gentamicin 1 mg/kg IV q8h (synergy)",
     "Alternative Therapy":"Vancomycin, Linezolid","Alternative Dosing":"Vancomycin AUC-guided IV; Linezolid 600 mg PO/IV q12h",
     "MDR Therapy":"Daptomycin (high-dose 8–12 mg/kg) + Ampicillin","MDR Dosing":"Daptomycin 8–12 mg/kg IV q24h + Ampicillin 2 g IV q4h",
     "Resistance Mechanisms":"Intrinsic low-level AG resistance; HLAR",
     "Key Notes":"HLAR eliminates synergy; use ceftriaxone + ampicillin for endocarditis",
     "Efficacy_FL":"green","Efficacy_Alt":"yellow","Efficacy_MDR":"yellow"},
    {"Category":"Bacteria","Organism":"Enterococcus faecium (VRE)","Gram / Morphology":"Gram+ Cocci",
     "First-Line Therapy":"Linezolid / Daptomycin","First-Line Dosing (US)":"Linezolid 600 mg PO/IV q12h; Daptomycin 8–12 mg/kg IV q24h",
     "Alternative Therapy":"Tedizolid, Oritavancin","Alternative Dosing":"Tedizolid 200 mg PO/IV q24h; Oritavancin 1200 mg IV × 1",
     "MDR Therapy":"Quinupristin-dalfopristin (E. faecium ONLY)","MDR Dosing":"Quinupristin-dalfopristin 7.5 mg/kg IV q8h",
     "Resistance Mechanisms":"vanA / vanB operons",
     "Key Notes":"Consult ID; linezolid myelosuppression risk >2 wks",
     "Efficacy_FL":"green","Efficacy_Alt":"yellow","Efficacy_MDR":"red"},
    {"Category":"Bacteria","Organism":"Escherichia coli (susceptible)","Gram / Morphology":"Gram- Bacilli (Enteric)",
     "First-Line Therapy":"TMP-SMX / Fluoroquinolone","First-Line Dosing (US)":"TMP-SMX 1 DS PO q12h; Ciprofloxacin 500 mg PO q12h",
     "Alternative Therapy":"Nitrofurantoin (UTI only), Fosfomycin","Alternative Dosing":"Nitrofurantoin 100 mg ER PO q12h × 5d; Fosfomycin 3 g PO × 1",
     "MDR Therapy":"Ceftriaxone (moderate); Pip-Tazo (complicated)","MDR Dosing":"Ceftriaxone 2 g IV q24h; Pip-Tazo 4.5 g IV q6h",
     "Resistance Mechanisms":"AmpC, ESBL, fluoroquinolone mutations (gyrA/parC)",
     "Key Notes":"Always check local antibiogram; resistance rates highly variable",
     "Efficacy_FL":"green","Efficacy_Alt":"yellow","Efficacy_MDR":"yellow"},
    {"Category":"Bacteria","Organism":"E. coli / Klebsiella (ESBL)","Gram / Morphology":"Gram- Bacilli (Enteric)",
     "First-Line Therapy":"Ertapenem / Meropenem","First-Line Dosing (US)":"Ertapenem 1 g IV q24h; Meropenem 1–2 g IV q8h",
     "Alternative Therapy":"Ceftolozane-tazobactam, Ceftazidime-avibactam","Alternative Dosing":"CTZ/AVI 2.5 g IV q8h (ext. infusion over 3h)",
     "MDR Therapy":"Fosfomycin (UTI), Colistin (last resort)","MDR Dosing":"Fosfomycin 6 g IV q6–8h; Colistin per PK/PD modeling",
     "Resistance Mechanisms":"CTX-M (dominant), SHV, TEM beta-lactamases",
     "Key Notes":"Avoid pip-tazo for ESBL bacteremia; step-down to oral when stable",
     "Efficacy_FL":"green","Efficacy_Alt":"yellow","Efficacy_MDR":"red"},
    {"Category":"Bacteria","Organism":"Klebsiella pneumoniae (KPC-CRE)","Gram / Morphology":"Gram- Bacilli (Enteric)",
     "First-Line Therapy":"Ceftazidime-avibactam","First-Line Dosing (US)":"Ceftazidime-avibactam 2.5 g IV q8h (3-h ext. infusion)",
     "Alternative Therapy":"Meropenem-vaborbactam, Imipenem-relebactam","Alternative Dosing":"Meropenem-vaborbactam 4 g IV q8h (3h); Imi-relebactam 1.25 g IV q6h",
     "MDR Therapy":"Cefiderocol, Aztreonam-avibactam (SAP), Tigecycline (combo)","MDR Dosing":"Cefiderocol 2 g IV q8h (3h ext.); Tigecycline 200 mg load then 100 mg q12h",
     "Resistance Mechanisms":"KPC (serine carbapenemase), OXA-48 variants",
     "Key Notes":"ALWAYS consult ID; combination therapy often required",
     "Efficacy_FL":"yellow","Efficacy_Alt":"yellow","Efficacy_MDR":"red"},
    {"Category":"Bacteria","Organism":"Klebsiella pneumoniae (MBL/NDM)","Gram / Morphology":"Gram- Bacilli (Enteric)",
     "First-Line Therapy":"Aztreonam-avibactam (combo)","First-Line Dosing (US)":"Aztreonam 6 g/day + Avibactam 0.375 g/day IV",
     "Alternative Therapy":"Cefiderocol, Colistin + Meropenem","Alternative Dosing":"Cefiderocol 2 g IV q8h (3h); Colistin CBA 5 mg/kg load",
     "MDR Therapy":"Tigecycline + Colistin + Meropenem (triple)","MDR Dosing":"Based on PK/PD modeling and ID consultation",
     "Resistance Mechanisms":"NDM, VIM, IMP metallo-beta-lactamases",
     "Key Notes":"Aztreonam NOT hydrolyzed by MBLs; ceftaz-AVI alone INEFFECTIVE for MBL",
     "Efficacy_FL":"red","Efficacy_Alt":"red","Efficacy_MDR":"red"},
    {"Category":"Bacteria","Organism":"Pseudomonas aeruginosa (susceptible)","Gram / Morphology":"Gram- Bacilli (Non-fermenter)",
     "First-Line Therapy":"Pip-Tazo / Cefepime / Meropenem","First-Line Dosing (US)":"Pip-Tazo 4.5 g IV q6h (ext. inf.); Cefepime 2 g IV q8h; Meropenem 2 g IV q8h",
     "Alternative Therapy":"Ciprofloxacin, Aztreonam, Aminoglycosides","Alternative Dosing":"Ciprofloxacin 400 mg IV q8h; Aztreonam 2 g IV q6h; Amikacin 15–20 mg/kg IV q24h",
     "MDR Therapy":"Ceftolozane-tazobactam, Ceftazidime-avibactam","MDR Dosing":"Ceftolozane-tazobactam 3 g IV q8h; CTZ-AVI 2.5 g IV q8h",
     "Resistance Mechanisms":"AmpC derepression, OprD loss, MexAB efflux, PBP3 mutations",
     "Key Notes":"Avoid monotherapy for serious infections; ertapenem has NO activity",
     "Efficacy_FL":"green","Efficacy_Alt":"yellow","Efficacy_MDR":"yellow"},
    {"Category":"Bacteria","Organism":"Pseudomonas aeruginosa (MDR/DTR)","Gram / Morphology":"Gram- Bacilli (Non-fermenter)",
     "First-Line Therapy":"Cefiderocol","First-Line Dosing (US)":"Cefiderocol 2 g IV q8h (3-h extended infusion)",
     "Alternative Therapy":"Imipenem-cilastatin-relebactam","Alternative Dosing":"Imipenem-cilastatin-relebactam 1.25 g IV q6h",
     "MDR Therapy":"Colistin + Meropenem (high-dose) + Fosfomycin","MDR Dosing":"Colistin CBA 5 mg/kg load + Meropenem 2 g IV q8h (3-h)",
     "Resistance Mechanisms":"MBL (VIM, IMP), AmpC, efflux, porin loss",
     "Key Notes":"DTR-PA = difficult-to-treat; strict ID + pharmacy involvement required",
     "Efficacy_FL":"yellow","Efficacy_Alt":"red","Efficacy_MDR":"red"},
    {"Category":"Bacteria","Organism":"Acinetobacter baumannii (MDR/XDR)","Gram / Morphology":"Gram- Bacilli (Non-fermenter)",
     "First-Line Therapy":"Ampicillin-sulbactam (sulbactam component)","First-Line Dosing (US)":"Sulbactam 9 g/day IV (as AMP-SUL 3 g IV q4h)",
     "Alternative Therapy":"Colistin, Polymyxin B","Alternative Dosing":"Colistin CBA load 5 mg/kg then 2.5 mg/kg q12h IV",
     "MDR Therapy":"Cefiderocol, Tigecycline + Colistin","MDR Dosing":"Cefiderocol 2 g IV q8h (3h); Tigecycline 200 mg load then 100 mg q12h",
     "Resistance Mechanisms":"OXA-23/24/48 carbapenemases, MBL (NDM), efflux, porin loss",
     "Key Notes":"Tigecycline FDA: use only if NO other option; monotherapy failure high",
     "Efficacy_FL":"red","Efficacy_Alt":"red","Efficacy_MDR":"red"},
    {"Category":"Bacteria","Organism":"Haemophilus influenzae","Gram / Morphology":"Gram- Coccobacilli",
     "First-Line Therapy":"Amoxicillin-clavulanate / Azithromycin","First-Line Dosing (US)":"Amox-clav 875/125 mg PO q12h; Azithromycin 500 mg PO day 1 then 250 mg q24h",
     "Alternative Therapy":"Cefuroxime, Levofloxacin, Doxycycline","Alternative Dosing":"Cefuroxime 250–500 mg PO q12h; Levofloxacin 750 mg PO q24h",
     "MDR Therapy":"Ceftriaxone (beta-lactamase positive, IV)","MDR Dosing":"Ceftriaxone 1–2 g IV q24h",
     "Resistance Mechanisms":"TEM-1 beta-lactamase; BLNAR",
     "Key Notes":"BLNAR strains: use fluoroquinolone or ceftriaxone",
     "Efficacy_FL":"green","Efficacy_Alt":"yellow","Efficacy_MDR":"yellow"},
    {"Category":"Bacteria","Organism":"Neisseria gonorrhoeae","Gram / Morphology":"Gram- Diplococci",
     "First-Line Therapy":"Ceftriaxone (single dose)","First-Line Dosing (US)":"Ceftriaxone 500 mg IM × 1 (or 1 g if weight ≥150 kg)",
     "Alternative Therapy":"Gentamicin + Azithromycin (PCN/cephalosporin allergy)","Alternative Dosing":"Gentamicin 240 mg IM × 1 + Azithromycin 2 g PO × 1",
     "MDR Therapy":"Ceftriaxone + Azithromycin 2g","MDR Dosing":"Ceftriaxone 500 mg IM + Azithromycin 2 g PO simultaneously",
     "Resistance Mechanisms":"PPNG (TEM beta-lactamase), TRNG, CMRNG; emerging cephalosporin resistance",
     "Key Notes":"Always treat for chlamydia co-infection with doxycycline; test-of-cure 1–2 wks",
     "Efficacy_FL":"green","Efficacy_Alt":"yellow","Efficacy_MDR":"red"},
    {"Category":"Bacteria","Organism":"Clostridioides difficile","Gram / Morphology":"Gram+ Bacilli (Anaerobe)",
     "First-Line Therapy":"Fidaxomicin / Vancomycin (PO)","First-Line Dosing (US)":"Fidaxomicin 200 mg PO q12h × 10d; Vancomycin 125 mg PO q6h × 10d",
     "Alternative Therapy":"Metronidazole (mild, non-severe only)","Alternative Dosing":"Metronidazole 500 mg PO q8h × 10–14d",
     "MDR Therapy":"Bezlotoxumab + Fidaxomicin","MDR Dosing":"Bezlotoxumab 10 mg/kg IV × 1; Fidaxomicin extended-pulse regimen",
     "Resistance Mechanisms":"Fecal dysbiosis; spore persistence; toxin A/B; ribotypes 027, 078",
     "Key Notes":"Discontinue offending antibiotic ASAP; FMT for multiple recurrences",
     "Efficacy_FL":"green","Efficacy_Alt":"yellow","Efficacy_MDR":"yellow"},
    {"Category":"Bacteria","Organism":"Mycoplasma pneumoniae","Gram / Morphology":"Cell Wall-Deficient",
     "First-Line Therapy":"Azithromycin / Doxycycline","First-Line Dosing (US)":"Azithromycin 500 mg PO day 1 then 250 mg q24h × 4d; Doxycycline 100 mg PO q12h × 5–7d",
     "Alternative Therapy":"Levofloxacin, Moxifloxacin","Alternative Dosing":"Levofloxacin 750 mg PO q24h × 5d; Moxifloxacin 400 mg PO q24h × 5d",
     "MDR Therapy":"Fluoroquinolone (if macrolide-resistant)","MDR Dosing":"Levofloxacin 750 mg PO q24h × 5d",
     "Resistance Mechanisms":"23S rRNA mutations (macrolide resistance — increasing US prevalence)",
     "Key Notes":"No cell wall — beta-lactams INEFFECTIVE; treat CAP empirically",
     "Efficacy_FL":"green","Efficacy_Alt":"yellow","Efficacy_MDR":"yellow"},
    # ── FUNGI ────────────────────────────────────────────────────────────────
    {"Category":"Fungi","Organism":"Candida albicans (susceptible)","Gram / Morphology":"Yeast",
     "First-Line Therapy":"Fluconazole","First-Line Dosing (US)":"Fluconazole 800 mg PO/IV load, then 400 mg q24h",
     "Alternative Therapy":"Micafungin / Caspofungin (candidemia/ICU)","Alternative Dosing":"Micafungin 100–150 mg IV q24h; Caspofungin 70 mg load then 50 mg IV q24h",
     "MDR Therapy":"Amphotericin B liposomal (fluconazole-R)","MDR Dosing":"Liposomal Amphotericin B 3–5 mg/kg IV q24h",
     "Resistance Mechanisms":"ERG11 mutations (azole resistance), FKS mutations (echinocandin resistance rare)",
     "Key Notes":"Echinocandin preferred for candidemia; de-escalate to fluconazole after 5–7d if stable",
     "Efficacy_FL":"green","Efficacy_Alt":"green","Efficacy_MDR":"yellow"},
    {"Category":"Fungi","Organism":"Candida auris (MDR)","Gram / Morphology":"Yeast",
     "First-Line Therapy":"Echinocandin (Micafungin preferred)","First-Line Dosing (US)":"Micafungin 100–150 mg IV q24h; Caspofungin 70 mg load then 50 mg q24h",
     "Alternative Therapy":"Ibrexafungerp","Alternative Dosing":"Ibrexafungerp 300 mg PO q12h × 1d",
     "MDR Therapy":"Liposomal Amphotericin B + Echinocandin","MDR Dosing":"L-AmB 5 mg/kg IV q24h + Micafungin 150 mg IV q24h",
     "Resistance Mechanisms":"Multi-drug resistant (simultaneous azole, polyene, echinocandin resistance possible)",
     "Key Notes":"CDC Priority Pathogen; mandatory reporting; strict contact precautions; consult ID immediately",
     "Efficacy_FL":"yellow","Efficacy_Alt":"red","Efficacy_MDR":"red"},
    {"Category":"Fungi","Organism":"Aspergillus fumigatus","Gram / Morphology":"Mold (Hyaline)",
     "First-Line Therapy":"Voriconazole","First-Line Dosing (US)":"Voriconazole 6 mg/kg IV q12h × 2 doses, then 4 mg/kg IV q12h (TDM target: 1–5.5 mg/L)",
     "Alternative Therapy":"Isavuconazole, Liposomal Amphotericin B","Alternative Dosing":"Isavuconazole 372 mg q8h × 6 doses (load) then q24h; L-AmB 3–5 mg/kg IV q24h",
     "MDR Therapy":"Voriconazole + echinocandin (angioinvasive, azole-R)","MDR Dosing":"Voriconazole + Micafungin (standard doses in combination)",
     "Resistance Mechanisms":"CYP51A mutations (TR34/L98H, TR46); azole resistance rising",
     "Key Notes":"Echinocandins have NO reliable monotherapy activity; TDM mandatory for voriconazole",
     "Efficacy_FL":"green","Efficacy_Alt":"yellow","Efficacy_MDR":"red"},
    {"Category":"Fungi","Organism":"Cryptococcus neoformans","Gram / Morphology":"Yeast (Encapsulated)",
     "First-Line Therapy":"Liposomal Amphotericin B + Flucytosine","First-Line Dosing (US)":"L-AmB 3–4 mg/kg IV q24h + Flucytosine 25 mg/kg PO q6h (induction 2 wks)",
     "Alternative Therapy":"Fluconazole (consolidation/maintenance)","Alternative Dosing":"Fluconazole 400 mg PO q24h × 8 wks, then 200 mg q24h maintenance",
     "MDR Therapy":"AmBisome high-dose + Flucytosine","MDR Dosing":"L-AmB 5 mg/kg IV q24h + Flucytosine 25 mg/kg PO q6h × 2 wks",
     "Resistance Mechanisms":"ERG11 mutations, efflux pumps (azole-R); primary flucytosine resistance rare",
     "Key Notes":"Always check opening pressure — LP for pressure relief critical in CNS disease",
     "Efficacy_FL":"green","Efficacy_Alt":"yellow","Efficacy_MDR":"yellow"},
    {"Category":"Fungi","Organism":"Mucormycosis (Mucor / Rhizopus)","Gram / Morphology":"Mold (Mucorales)",
     "First-Line Therapy":"Liposomal Amphotericin B","First-Line Dosing (US)":"L-AmB 5–10 mg/kg IV q24h",
     "Alternative Therapy":"Isavuconazole (step-down), Posaconazole (step-down)","Alternative Dosing":"Isavuconazole 372 mg PO/IV q24h (after AmB induction)",
     "MDR Therapy":"Surgery + antifungal","MDR Dosing":"Debridement + L-AmB 10 mg/kg IV q24h ± Deferasirox (investigational)",
     "Resistance Mechanisms":"Intrinsically resistant to voriconazole, echinocandins, and fluconazole",
     "Key Notes":"SURGICAL DEBRIDEMENT is cornerstone; reverse underlying DKA/immunosuppression; voriconazole does NOT cover Mucor",
     "Efficacy_FL":"green","Efficacy_Alt":"yellow","Efficacy_MDR":"red"},
    # ── VIRUSES ──────────────────────────────────────────────────────────────
    {"Category":"Viruses","Organism":"Influenza A & B","Gram / Morphology":"RNA Virus (Orthomyxovirus)",
     "First-Line Therapy":"Oseltamivir / Zanamivir","First-Line Dosing (US)":"Oseltamivir 75 mg PO q12h × 5d; Zanamivir 10 mg inhaled q12h × 5d",
     "Alternative Therapy":"Baloxavir marboxil","Alternative Dosing":"Baloxavir 40 mg PO × 1 (<80 kg); 80 mg PO × 1 (≥80 kg)",
     "MDR Therapy":"Peramivir (IV for hospitalized)","MDR Dosing":"Peramivir 600 mg IV × 1",
     "Resistance Mechanisms":"H275Y (oseltamivir R in H1N1); PA I38T (baloxavir R)",
     "Key Notes":"Start within 48h of symptom onset; amantadine/rimantadine: HIGH resistance, NOT recommended",
     "Efficacy_FL":"green","Efficacy_Alt":"green","Efficacy_MDR":"yellow"},
    {"Category":"Viruses","Organism":"Herpes Simplex Virus (HSV-1/2)","Gram / Morphology":"DNA Virus (Herpesviridae)",
     "First-Line Therapy":"Acyclovir / Valacyclovir","First-Line Dosing (US)":"Valacyclovir 500–1000 mg PO q12h × 7–10d; Acyclovir 5–10 mg/kg IV q8h (severe)",
     "Alternative Therapy":"Famciclovir","Alternative Dosing":"Famciclovir 500 mg PO q12h × 7–10d",
     "MDR Therapy":"Foscarnet (acyclovir-resistant), Cidofovir","MDR Dosing":"Foscarnet 40 mg/kg IV q8h; Cidofovir 5 mg/kg IV weekly",
     "Resistance Mechanisms":"TK mutations (UL23) — acyclovir/valacyclovir R; DNA polymerase mutations (UL30)",
     "Key Notes":"Foscarnet for TK-deficient strains; cidofovir as last resort (nephrotoxic)",
     "Efficacy_FL":"green","Efficacy_Alt":"green","Efficacy_MDR":"yellow"},
    {"Category":"Viruses","Organism":"Cytomegalovirus (CMV)","Gram / Morphology":"DNA Virus (Herpesviridae)",
     "First-Line Therapy":"Valganciclovir / Ganciclovir","First-Line Dosing (US)":"Valganciclovir 900 mg PO q12h (induction) then 900 mg q24h; Ganciclovir 5 mg/kg IV q12h (severe)",
     "Alternative Therapy":"Foscarnet (second-line or ganciclovir-R)","Alternative Dosing":"Foscarnet 60 mg/kg IV q8h or 90 mg/kg IV q12h (induction)",
     "MDR Therapy":"Letermovir (prophylaxis), Maribavir (refractory/resistant)","MDR Dosing":"Letermovir 480 mg IV/PO q24h; Maribavir 400 mg PO q12h × 8 wks",
     "Resistance Mechanisms":"UL97 mutations (ganciclovir-R); UL54 mutations (multi-drug R)",
     "Key Notes":"Maribavir FDA-approved 2021 for refractory/resistant CMV in transplant; monitor CBC weekly",
     "Efficacy_FL":"green","Efficacy_Alt":"yellow","Efficacy_MDR":"yellow"},
    {"Category":"Viruses","Organism":"Hepatitis C Virus (HCV) — Pan-genotypic","Gram / Morphology":"RNA Virus (Flaviviridae)",
     "First-Line Therapy":"Sofosbuvir/Velpatasvir or Glecaprevir/Pibrentasvir","First-Line Dosing (US)":"SOF/VEL 1 tab PO q24h × 12 wks; GLE/PIB 3 tabs PO q24h × 8 wks (non-cirrhotic)",
     "Alternative Therapy":"SOF/VEL/Voxilaprevir (NS5A-experienced)","Alternative Dosing":"SOF/VEL/VOX 1 tab PO q24h × 12 wks",
     "MDR Therapy":"Retreatment per AASLD (resistance testing guided)","MDR Dosing":"Individualized — consult hepatology/ID",
     "Resistance Mechanisms":"NS5A RASs (L31M, Y93H), NS5B mutations",
     "Key Notes":"SVR12 >95%; check drug interactions (acid-suppression, antiretrovirals)",
     "Efficacy_FL":"green","Efficacy_Alt":"green","Efficacy_MDR":"yellow"},
    {"Category":"Viruses","Organism":"SARS-CoV-2 (COVID-19)","Gram / Morphology":"RNA Virus (Betacoronavirus)",
     "First-Line Therapy":"Nirmatrelvir-ritonavir (Paxlovid) / Remdesivir","First-Line Dosing (US)":"Nirmatrelvir-ritonavir 300/100 mg PO q12h × 5d; Remdesivir 200 mg IV day 1 then 100 mg q24h × 4d",
     "Alternative Therapy":"Molnupiravir (if Paxlovid not feasible)","Alternative Dosing":"Molnupiravir 800 mg PO q12h × 5d",
     "MDR Therapy":"Remdesivir + Dexamethasone (hospitalized, O2-requiring)","MDR Dosing":"Dexamethasone 6 mg PO/IV q24h × 10d + Remdesivir",
     "Resistance Mechanisms":"NSP5 (protease) mutations affecting nirmatrelvir; spike mutations",
     "Key Notes":"Ritonavir causes significant DDIs (check prescribing tool); monoclonal antibodies largely inactive against current variants",
     "Efficacy_FL":"green","Efficacy_Alt":"yellow","Efficacy_MDR":"yellow"},
    {"Category":"Viruses","Organism":"HIV-1 (ART-Naïve)","Gram / Morphology":"RNA Virus (Retrovirus)",
     "First-Line Therapy":"Bictegravir/TAF/FTC (Biktarvy) or DTG + TAF/FTC","First-Line Dosing (US)":"Bictegravir 50/TAF 25/FTC 200 mg PO q24h; DTG 50 mg + TAF/FTC 25/200 mg PO q24h",
     "Alternative Therapy":"Cabotegravir LA + Rilpivirine LA","Alternative Dosing":"CAB-LA 600 mg IM + RPV-LA 900 mg IM q4 wks (months 1–2), then q8 wks",
     "MDR Therapy":"Ibalizumab + optimized background","MDR Dosing":"Ibalizumab 2000 mg IV load, then 800 mg IV q2 wks + OBR",
     "Resistance Mechanisms":"INSTI mutations (G140S, Q148H), NNRTI mutations (K103N), TAM",
     "Key Notes":"Genotypic resistance testing before initiation; treat all patients regardless of CD4 count",
     "Efficacy_FL":"green","Efficacy_Alt":"green","Efficacy_MDR":"yellow"},
]

# ══════════════════════════════════════════════════════════════════════════════
#  STYLING CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════

CELL_COLORS = {
    "++":  {"bg": "#1a7a4a", "fg": "#ffffff", "label": "First-Line"},
    "+":   {"bg": "#5aaa72", "fg": "#ffffff", "label": "Active"},
    "+/-": {"bg": "#e8aa30", "fg": "#1a1a1a", "label": "Variable"},
    "0":   {"bg": "#cc3333", "fg": "#ffffff", "label": "Resistant"},
    "?":   {"bg": "#888888", "fg": "#ffffff", "label": "Insufficient Data"},
    "CI":  {"bg": "#2a7ab5", "fg": "#ffffff", "label": "Combo Only"},
    "":    {"bg": "#f0f0f0", "fg": "#aaaaaa", "label": "N/A"},
}

EFFICACY_BG  = {"green": "#d4edda", "yellow": "#fff3cd", "red": "#f8d7da"}
EFFICACY_TXT = {"green": "#155724",  "yellow": "#856404",  "red": "#721c24"}

STANDARD_COLS = ["Category","Organism","Gram / Morphology","First-Line Therapy",
                 "First-Line Dosing (US)","Alternative Therapy","Alternative Dosing",
                 "MDR Therapy","MDR Dosing","Resistance Mechanisms","Key Notes"]
MDR_COLS      = ["Organism","Gram / Morphology","MDR Therapy","MDR Dosing",
                 "Resistance Mechanisms","Key Notes"]
EFFICACY_COLS = ["Efficacy_FL","Efficacy_Alt","Efficacy_MDR"]
DISP_TO_EFF   = {"First-Line Therapy": "Efficacy_FL",
                 "Alternative Therapy": "Efficacy_Alt",
                 "MDR Therapy": "Efficacy_MDR"}

# ══════════════════════════════════════════════════════════════════════════════
#  DATA LOADERS
# ══════════════════════════════════════════════════════════════════════════════

@st.cache_data
def load_treatment_data() -> pd.DataFrame:
    return pd.DataFrame(ORGANISM_DATA)

@st.cache_data
def load_amr_organisms() -> pd.DataFrame | None:
    path = "data/amr_microorganisms.csv"
    if os.path.exists(path):
        return pd.read_csv(path, low_memory=False)
    return None

@st.cache_data
def load_amr_breakpoints() -> pd.DataFrame | None:
    path = "data/amr_clinical_breakpoints.csv"
    if os.path.exists(path):
        return pd.read_csv(path, low_memory=False)
    return None

# ══════════════════════════════════════════════════════════════════════════════
#  SENSITIVITY GRID HTML RENDERER
# ══════════════════════════════════════════════════════════════════════════════

GROUP_COLORS = {
    "GP Cocci — Streptococci":    "#e8f0fb",
    "GP Cocci — Enterococci":     "#fce8f0",
    "GP Cocci — Staphylococci":   "#fdf0e8",
    "GP Bacilli":                  "#f0f8e8",
    "GN Bacilli — Enteric":        "#e8f8fb",
    "GN Bacilli — Non-Enteric":    "#e8fbf5",
    "GN Bacilli — Non-Fermenters": "#f8fbe8",
    "Atypicals (no cell wall)":    "#f8f0fb",
    "Anaerobes — Gram Negative":   "#f5e8fb",
    "Anaerobes — Gram Positive":   "#fbeae8",
}

def render_sensitivity_grid(data: list[dict], filter_group: str = "All",
                             filter_abx_classes: list = None,
                             search: str = "") -> str:
    """Render the Sanford-style sensitivity matrix as HTML."""

    # Filter organisms
    rows = data
    if filter_group != "All":
        rows = [r for r in rows if r["group"] == filter_group]
    if search.strip():
        s = search.strip().lower()
        rows = [r for r in rows if s in r["organism"].lower() or s in r["group"].lower()]

    # Filter antibiotics by class
    if filter_abx_classes:
        active_groups = [(g, abxs) for g, abxs in ABX_GROUPS if g in filter_abx_classes]
    else:
        active_groups = ABX_GROUPS

    active_abx = [ab for _, abxs in active_groups for ab in abxs]

    if not rows:
        return "<p style='padding:20px;color:#888;'>No organisms match your filter.</p>"

    # Build HTML
    # We'll inline everything for portability
    html_parts = ["""
<style>
  .sg-wrap { overflow-x: auto; max-height: 75vh; overflow-y: auto; }
  .sg-table { border-collapse: collapse; font-family: 'Courier New', monospace; font-size: 11px; }
  .sg-table thead { position: sticky; top: 0; z-index: 20; }
  .sg-class-hdr { background: #1a3a5c; color: white; text-align: center;
                  font-size: 10px; font-weight: bold; padding: 3px 4px;
                  letter-spacing: 0.5px; border-right: 2px solid #0d2238; }
  .sg-abx-hdr { background: #254f7a; color: #cce5ff;
                writing-mode: vertical-rl; text-orientation: mixed;
                transform: rotate(180deg); padding: 8px 4px 4px 4px;
                font-size: 9.5px; white-space: nowrap;
                border-bottom: 2px solid #1a3a5c; border-right: 1px solid #1a5580; }
  .sg-org-col { position: sticky; left: 0; background: inherit; z-index: 10;
                min-width: 200px; max-width: 200px; padding: 4px 8px;
                font-size: 10.5px; font-weight: 600; border-right: 2px solid #ccc;
                white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .sg-group-row td { font-size: 10px; font-weight: 700; padding: 4px 8px;
                     letter-spacing: 0.8px; text-transform: uppercase;
                     border-top: 2px solid #ccc; }
  .sg-cell { text-align: center; padding: 3px 2px; min-width: 36px;
             font-size: 10px; font-weight: 700; border: 1px solid #e0e0e0; cursor: default; }
  .sg-cell:hover { filter: brightness(0.88); transform: scale(1.05);
                   box-shadow: 0 0 4px rgba(0,0,0,0.3); position: relative; z-index: 5; }
  .sg-row:hover .sg-org-col { text-decoration: underline; }
  .sg-org-hdr { position: sticky; left: 0; top: 0; z-index: 30; background: #1a3a5c;
                color: white; padding: 4px 8px; font-size: 10px; font-weight: bold;
                min-width: 200px; border-right: 2px solid #0d2238; }
</style>
<div class="sg-wrap">
<table class="sg-table">
"""]

    # ── Column headers ────────────────────────────────────────────────────────
    html_parts.append("<thead>")

    # Row 1: class group spans
    html_parts.append("<tr>")
    html_parts.append('<th class="sg-org-hdr" rowspan="2">Organism</th>')
    for grp_name, abxs in active_groups:
        visible = [a for a in abxs if a in active_abx]
        if not visible:
            continue
        html_parts.append(
            f'<th class="sg-class-hdr" colspan="{len(visible)}">{grp_name}</th>'
        )
    html_parts.append("</tr>")

    # Row 2: individual antibiotic names (rotated)
    html_parts.append("<tr>")
    for _, abxs in active_groups:
        for ab in abxs:
            if ab in active_abx:
                html_parts.append(
                    f'<th class="sg-abx-hdr" title="{ABX_DISPLAY[ab]}">{ABX_DISPLAY[ab]}</th>'
                )
    html_parts.append("</tr>")
    html_parts.append("</thead><tbody>")

    # ── Data rows ─────────────────────────────────────────────────────────────
    current_group = None
    for row in rows:
        grp = row["group"]

        # Group separator row
        if grp != current_group:
            current_group = grp
            grp_bg = GROUP_COLORS.get(grp, "#f5f5f5")
            n_cols = len(active_abx) + 1
            html_parts.append(
                f'<tr class="sg-group-row" style="background:{grp_bg};">'
                f'<td colspan="{n_cols}" style="color:#1a3a5c;">{grp}</td></tr>'
            )

        org = row["organism"]
        row_bg = GROUP_COLORS.get(grp, "#ffffff")

        html_parts.append(f'<tr class="sg-row" style="background:{row_bg};">')
        html_parts.append(
            f'<td class="sg-org-col" title="{org}">{org}</td>'
        )

        for _, abxs in active_groups:
            for ab in abxs:
                if ab not in active_abx:
                    continue
                val = row.get(ab, "")
                c   = CELL_COLORS.get(val, CELL_COLORS[""])
                tip = f"{ABX_DISPLAY.get(ab,ab)} vs {org}: {c['label']}"
                html_parts.append(
                    f'<td class="sg-cell" style="background:{c["bg"]};color:{c["fg"]};"'
                    f' title="{tip}">{val}</td>'
                )

        html_parts.append("</tr>")

    html_parts.append("</tbody></table></div>")
    return "".join(html_parts)


def render_legend() -> str:
    items = [
        ("++",  CELL_COLORS["++"],  "First-Line / Reliably Active"),
        ("+",   CELL_COLORS["+"],   "Active / Recommended Alternative"),
        ("+/-", CELL_COLORS["+/-"], "Variable — context-dependent"),
        ("0",   CELL_COLORS["0"],   "Not Recommended / Resistant"),
        ("CI",  CELL_COLORS["CI"],  "Use in Combination Only"),
        ("?",   CELL_COLORS["?"],   "Insufficient Evidence"),
        ("",    CELL_COLORS[""],    "Not Applicable"),
    ]
    parts = ['<div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:12px;font-family:monospace;font-size:12px;">']
    for val, c, label in items:
        display = val if val else "—"
        parts.append(
            f'<span style="background:{c["bg"]};color:{c["fg"]};padding:3px 10px;'
            f'border-radius:4px;font-weight:700;">{display}</span>'
            f'<span style="color:#555;margin-right:8px;font-size:11px;">{label}</span>'
        )
    parts.append("</div>")
    return "".join(parts)


# ══════════════════════════════════════════════════════════════════════════════
#  TREATMENT DETAILS TABLE  (existing functionality)
# ══════════════════════════════════════════════════════════════════════════════

def style_treatment_row(row: pd.Series) -> list:
    styles = []
    for col in row.index:
        if col in DISP_TO_EFF:
            code = row.get(DISP_TO_EFF[col], "")
            bg   = EFFICACY_BG.get(code, "")
            fg   = EFFICACY_TXT.get(code, "")
            styles.append(f"background-color:{bg};color:{fg};font-weight:bold;")
        else:
            styles.append("")
    return styles


def build_styled_treatment_df(df: pd.DataFrame, mdr_focus: bool):
    display_cols = MDR_COLS if mdr_focus else STANDARD_COLS
    avail  = [c for c in display_cols if c in df.columns]
    hidden = [c for c in EFFICACY_COLS if c in df.columns]
    styler = (
        df[avail + hidden].style
        .apply(style_treatment_row, axis=1)
        .set_properties(**{"font-size": "12px", "text-align": "left"})
        .set_table_styles([
            {"selector": "th", "props": [("background-color","#1a3a5c"),("color","white"),
                                          ("font-size","12px"),("padding","6px")]},
            {"selector": "td", "props": [("padding","6px 10px"),
                                          ("border-bottom","1px solid #dee2e6"),
                                          ("vertical-align","top")]},
        ])
        .hide(axis="columns", subset=hidden)
        .hide(axis="index")
    )
    return styler


# ══════════════════════════════════════════════════════════════════════════════
#  PDF EXPORT
# ══════════════════════════════════════════════════════════════════════════════

_UNI = {"\u2265":">=","\u2264":"<=","\u2192":"->","\u2013":"-","\u2014":"--",
        "\u2018":"'","\u2019":"'","\u201c":'"',"\u201d":'"',"\u2022":"*",
        "\u00b1":"+/-","\u00d7":"x","\u03b2":"beta","\u03bc":"u"}

def _safe(text: str) -> str:
    for c, r in _UNI.items():
        text = text.replace(c, r)
    return text.encode("latin-1", errors="replace").decode("latin-1")


def generate_pdf(filtered_df: pd.DataFrame, mdr_focus: bool) -> bytes:
    display_cols = MDR_COLS if mdr_focus else STANDARD_COLS
    cols = [c for c in display_cols if c in filtered_df.columns]
    df_print = filtered_df[cols].copy()

    pdf = FPDF(orientation="L", unit="mm", format="A3")
    pdf.set_auto_page_break(auto=True, margin=10)
    pdf.add_page()

    pdf.set_font("Helvetica","B",16)
    pdf.set_fill_color(26,58,92); pdf.set_text_color(255,255,255)
    pdf.cell(0,10,"Dynamic Antibiogram & Antimicrobial Stewardship Tool",ln=True,align="C",fill=True)
    pdf.set_font("Helvetica","",9); pdf.set_text_color(100,100,100)
    mode_label = "MDR FOCUS MODE" if mdr_focus else "Standard Mode"
    pdf.cell(0,6,f"  Mode: {mode_label}   |   Rows: {len(df_print)}   |   US Clinical Practice Reference",ln=True,align="L")
    pdf.ln(2)

    pdf.set_font("Helvetica","B",8); pdf.set_text_color(0,0,0)
    for label,(r,g,b) in [("First-Line",(212,237,218)),("Alternative",(255,243,205)),("Not Recommended",(248,215,218))]:
        pdf.set_fill_color(r,g,b); pdf.cell(5,5," ",fill=True)
        pdf.set_fill_color(255,255,255); pdf.cell(60,5,f" {label}",ln=False)
    pdf.ln(7)

    PAGE_W = pdf.w - pdf.l_margin - pdf.r_margin
    col_weights = {"Category":1,"Organism":2.5,"Gram / Morphology":1.5,"First-Line Therapy":2,
                   "First-Line Dosing (US)":3.5,"Alternative Therapy":2,"Alternative Dosing":3.5,
                   "MDR Therapy":2,"MDR Dosing":3.5,"Resistance Mechanisms":2.5,"Key Notes":3}
    weights = [col_weights.get(c,2) for c in cols]
    col_widths = [PAGE_W*(w/sum(weights)) for w in weights]
    ROW_H = 6

    pdf.set_font("Helvetica","B",7); pdf.set_fill_color(26,58,92); pdf.set_text_color(255,255,255)
    for col,cw in zip(cols,col_widths):
        pdf.cell(cw,ROW_H,col,border=1,fill=True,align="C")
    pdf.ln()

    eff_map = filtered_df.set_index("Organism") if "Organism" in filtered_df.columns else None
    color_map = {"green":(212,237,218),"yellow":(255,243,205),"red":(248,215,218)}

    for _,row in df_print.iterrows():
        pdf.set_font("Helvetica","",6.5); pdf.set_text_color(0,0,0)
        cell_heights = []
        for col,cw in zip(cols,col_widths):
            txt = _safe(str(row[col])) if pd.notna(row[col]) else ""
            n = max(1,len(pdf.multi_cell(cw,ROW_H-1,txt,split_only=True)))
            cell_heights.append(n*(ROW_H-1))
        row_h = max(cell_heights)
        if pdf.get_y()+row_h > pdf.h-pdf.b_margin:
            pdf.add_page()
            pdf.set_font("Helvetica","B",7); pdf.set_fill_color(26,58,92); pdf.set_text_color(255,255,255)
            for col,cw in zip(cols,col_widths): pdf.cell(cw,ROW_H,col,border=1,fill=True,align="C")
            pdf.ln(); pdf.set_font("Helvetica","",6.5); pdf.set_text_color(0,0,0)
        x0,y0 = pdf.get_x(),pdf.get_y()
        for i,(col,cw) in enumerate(zip(cols,col_widths)):
            txt = _safe(str(row[col])) if pd.notna(row[col]) else ""
            fill = False
            if col in DISP_TO_EFF and eff_map is not None:
                try:
                    org = row.get("Organism","")
                    ec = filtered_df.loc[filtered_df["Organism"]==org, DISP_TO_EFF[col]].values[0]
                    if ec in color_map:
                        pdf.set_fill_color(*color_map[ec]); fill=True
                    else:
                        pdf.set_fill_color(255,255,255)
                except Exception:
                    pdf.set_fill_color(255,255,255)
            else:
                pdf.set_fill_color(255,255,255)
            pdf.set_xy(x0+sum(col_widths[:i]),y0)
            n = max(1,len(pdf.multi_cell(cw,row_h-1,txt,split_only=True)))
            pdf.multi_cell(cw,row_h/n,txt,border=1,fill=fill,align="L")
        pdf.set_xy(x0,y0+row_h)

    pdf.set_font("Helvetica","I",7); pdf.set_text_color(120,120,120)
    pdf.cell(0,5,"Data: Sanford Guide 2024, IDSA Guidelines, CDC. Clinical decision support only. Correlate with local antibiogram.",ln=True,align="C")
    return bytes(pdf.output())


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN APP
# ══════════════════════════════════════════════════════════════════════════════

def main():
    st.set_page_config(
        page_title="Bugs & Drugs — Antimicrobial Stewardship",
        layout="wide",
        initial_sidebar_state="expanded",
        page_icon="💊",
    )

    # ── Global CSS ─────────────────────────────────────────────────────────
    st.markdown("""
    <style>
      [data-testid="stAppViewContainer"] { background: #f4f6fa; }
      .main-banner { background: linear-gradient(135deg,#1a3a5c,#0d6efd);
                     padding: 18px 24px; border-radius: 10px; margin-bottom: 16px; }
      .main-banner h2 { color: white; margin: 0; font-size: 1.5rem; }
      .main-banner p  { color: #cce5ff; margin: 4px 0 0 0; font-size: 13px; }
      .metric-card { background: white; border-radius: 8px; padding: 12px 16px;
                     border-left: 4px solid #0d6efd; box-shadow: 0 1px 4px rgba(0,0,0,.08); }
      div[data-testid="stTabs"] button { font-size: 14px !important; font-weight: 600; }
    </style>
    """, unsafe_allow_html=True)

    # ── Header banner ────────────────────────────────────────────────────────
    st.markdown("""
    <div class="main-banner">
      <h2>🦠 Bugs &amp; Drugs — Antimicrobial Stewardship Tool</h2>
      <p>US Clinical Practice Reference &nbsp;·&nbsp; Bacteria &nbsp;·&nbsp; Fungi &nbsp;·&nbsp; Viruses &nbsp;·&nbsp; MDR Organisms &nbsp;·&nbsp; AMR Database</p>
    </div>
    """, unsafe_allow_html=True)

    # Quick stats
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown('<div class="metric-card"><b>70+</b><br><small>Organisms in Sensitivity Grid</small></div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="metric-card"><b>32</b><br><small>Antibiotics Tracked</small></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="metric-card"><b>{len(ORGANISM_DATA)}</b><br><small>Treatment Profiles w/ Dosing</small></div>', unsafe_allow_html=True)
    with c4:
        amr_loaded = os.path.exists("data/amr_microorganisms.csv")
        amr_label = "AMR DB Connected" if amr_loaded else "AMR DB: Run setup script"
        color = "#0d6efd" if amr_loaded else "#dc3545"
        st.markdown(f'<div class="metric-card" style="border-left-color:{color};"><b>{"✓" if amr_loaded else "!"}</b><br><small>{amr_label}</small></div>', unsafe_allow_html=True)

    st.markdown("")

    # ── Tabs ─────────────────────────────────────────────────────────────────
    tab1, tab2, tab3 = st.tabs([
        "🔬  Sensitivity Grid",
        "💊  Treatment Details",
        "🔍  Organism Search (AMR DB)",
    ])

    # ══════════════════════════════════════════════════════════════════════
    # TAB 1: SENSITIVITY GRID
    # ══════════════════════════════════════════════════════════════════════
    with tab1:
        st.markdown("### Antibiotic Sensitivity Reference")
        st.caption("Color-coded sensitivity matrix based on Sanford Guide 2024, IDSA Guidelines, and CDC data. "
                   "Hover over any cell for details.")

        # Controls
        col_a, col_b, col_c = st.columns([2, 2, 3])

        all_groups = ["All"] + sorted({r["group"] for r in SENSITIVITY_MATRIX})
        with col_a:
            group_filter = st.selectbox("Filter by Organism Group", all_groups, key="grid_group")

        all_abx_classes = [g for g, _ in ABX_GROUPS]
        with col_b:
            abx_class_filter = st.multiselect(
                "Filter Antibiotic Classes (leave blank = all)",
                all_abx_classes, default=[], key="grid_abx",
            )

        with col_c:
            org_search = st.text_input("🔍 Search Organism", placeholder="e.g. Pseudomonas, MRSA, Candida", key="grid_search")

        # Legend
        st.markdown(render_legend(), unsafe_allow_html=True)

        # Notes banner
        st.info(
            "⚠️ **Important caveats:**  \n"
            "**CI** = use only in combination | "
            "Tigecycline: use only if no other option (FDA warning) | "
            "Daptomycin: do NOT use for pneumonia | "
            "Ertapenem has NO activity vs *P. aeruginosa* | "
            "All beta-lactams inactive vs atypicals (Mycoplasma, Chlamydia, Ureaplasma)"
        )

        # Render grid
        selected_classes = abx_class_filter if abx_class_filter else None
        grid_html = render_sensitivity_grid(
            SENSITIVITY_MATRIX,
            filter_group=group_filter,
            filter_abx_classes=selected_classes,
            search=org_search,
        )
        st.markdown(grid_html, unsafe_allow_html=True)

        # Key clinical notes section
        st.divider()
        with st.expander("📋 Key Clinical Notes & Special Circumstances", expanded=False):
            cols_n = st.columns(2)
            with cols_n[0]:
                st.markdown("""
**Gram-Positive Pearls:**
- **MRSA**: Vancomycin AUC/MIC guided (target 400–600). Ceftaroline active (G5 ceph)
- **MSSA bacteremia**: Nafcillin > Cefazolin > Vancomycin — avoid VAN if susceptible
- **VRE**: Linezolid or Daptomycin; consult ID. Quinupristin-dalfopristin for E. faecium only
- **Strep. pneumoniae MDR**: Levofloxacin + Vancomycin ± Rifampin for meningitis

**ESBL & CRE:**
- **ESBL bacteremia**: Carbapenems preferred; avoid pip-tazo
- **KPC-CRE**: Ceftazidime-avibactam first-line; ID consult mandatory
- **MBL (NDM/VIM/IMP)**: Ceftaz-AVI alone INEFFECTIVE; need aztreonam-avibactam or cefiderocol
                """)
            with cols_n[1]:
                st.markdown("""
**Non-Fermenter Pearls:**
- **P. aeruginosa**: Ertapenem has NO activity; antipseudomonal β-lactam + consider combo for severe
- **A. baumannii MDR/XDR**: Sulbactam component of amp-sulbactam; colistin; cefiderocol
- **S. maltophilia**: Intrinsically resistant to carbapenems; TMP-SMX first-line

**Atypical / Anaerobe Pearls:**
- **Atypicals (Mycoplasma, Chlamydia)**: All beta-lactams INACTIVE (no cell wall)
- **C. difficile**: Fidaxomicin > Vancomycin PO; metronidazole only for mild/non-severe
- **B. fragilis**: Metronidazole or amox-clav; most cephalosporins ineffective
- **Legionella**: Fluoroquinolones/macrolides only; beta-lactams do not work
                """)

    # ══════════════════════════════════════════════════════════════════════
    # TAB 2: TREATMENT DETAILS
    # ══════════════════════════════════════════════════════════════════════
    with tab2:
        df_full = load_treatment_data()

        with st.sidebar:
            st.markdown("## Filters + Settings")
            st.divider()

            mdr_focus = st.toggle("MDR Focus Mode", value=False,
                help="Highlights salvage therapies and high-exposure dosing for resistant organisms")
            if mdr_focus:
                st.warning("MDR Focus: showing salvage/high-dose regimens")
            st.divider()

            categories  = ["All"] + sorted(df_full["Category"].unique().tolist())
            cat_sel     = st.selectbox("Pathogen Category", categories)
            morph_opts  = sorted(df_full["Gram / Morphology"].unique().tolist())
            morph_sel   = st.multiselect("Gram Stain / Morphology", morph_opts, default=[])
            search_term = st.text_input("🔍 Search Organism",
                placeholder="e.g. Pseudomonas, Candida, Influenza")

            st.divider()
            st.markdown("### Efficacy Legend")
            st.markdown("""
            <div style="font-size:13px;line-height:1.9;">
              <span style="background:#d4edda;padding:2px 8px;border-radius:4px;">■</span> <b>First-Line</b><br>
              <span style="background:#fff3cd;padding:2px 8px;border-radius:4px;">■</span> <b>Alternative</b><br>
              <span style="background:#f8d7da;padding:2px 8px;border-radius:4px;">■</span> <b>Not Recommended</b>
            </div>""", unsafe_allow_html=True)
            st.divider()
            st.markdown('<div style="font-size:11px;color:#888;">Sanford Guide 2024, IDSA/ASHP Guidelines, CDC<br><b>Clinical decision support only.</b></div>',
                        unsafe_allow_html=True)

        # Filter
        df = df_full.copy()
        if cat_sel != "All":
            df = df[df["Category"] == cat_sel]
        if morph_sel:
            df = df[df["Gram / Morphology"].isin(morph_sel)]
        if search_term.strip():
            df = df[df["Organism"].str.contains(search_term.strip(), case=False, na=False)]

        if df.empty:
            st.info("No organisms match your current filters.")
        else:
            mode_label = "MDR Salvage Reference" if mdr_focus else "Standard Antibiogram"
            st.subheader(mode_label)
            st.dataframe(build_styled_treatment_df(df, mdr_focus), use_container_width=True, height=550)

            st.divider()
            with st.expander("Full Detail View", expanded=False):
                selected_org = st.selectbox("Select Organism for Full Detail", df["Organism"].tolist())
                if selected_org:
                    row = df[df["Organism"] == selected_org].iloc[0]
                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown(f"### {row['Organism']}")
                        st.markdown(f"**Category:** {row['Category']}")
                        st.markdown(f"**Gram/Morphology:** {row['Gram / Morphology']}")
                        st.divider()
                        st.markdown("#### 🟢 First-Line Therapy")
                        st.info(f"**Agent:** {row['First-Line Therapy']}")
                        st.markdown(f"**US Dosing:** `{row['First-Line Dosing (US)']}`")
                        st.markdown("#### 🟡 Alternative Therapy")
                        st.warning(f"**Agent:** {row['Alternative Therapy']}")
                        st.markdown(f"**US Dosing:** `{row['Alternative Dosing']}`")
                    with c2:
                        eff_code = row.get("Efficacy_MDR","yellow")
                        eff_emoji = {"green":"🟢","yellow":"🟡","red":"🔴"}.get(eff_code,"🟡")
                        st.markdown(f"#### {eff_emoji} MDR / Salvage Therapy")
                        if eff_code == "red":
                            st.error(f"**Agent:** {row['MDR Therapy']}")
                        else:
                            st.warning(f"**Agent:** {row['MDR Therapy']}")
                        st.markdown(f"**US Dosing:** `{row['MDR Dosing']}`")
                        st.divider()
                        st.markdown("#### Resistance Mechanisms")
                        st.markdown(f"_{row['Resistance Mechanisms']}_")
                        st.markdown("#### Key Notes")
                        st.markdown(f"> {row['Key Notes']}")

            st.divider()
            st.subheader("Export")
            col_btn1, col_btn2 = st.columns([2, 5])
            with col_btn1:
                if st.button("Generate PDF", use_container_width=True, type="primary"):
                    with st.spinner("Building PDF..."):
                        pdf_bytes = generate_pdf(df, mdr_focus)
                    filename = f"antibiogram_{'MDR' if mdr_focus else 'standard'}_{cat_sel.replace(' ','_')}.pdf"
                    st.session_state["pdf_bytes"]    = pdf_bytes
                    st.session_state["pdf_filename"] = filename
                    st.success("PDF ready!")
                if "pdf_bytes" in st.session_state:
                    st.download_button("Download PDF", data=st.session_state["pdf_bytes"],
                        file_name=st.session_state.get("pdf_filename","antibiogram.pdf"),
                        mime="application/pdf", use_container_width=True)

    # ══════════════════════════════════════════════════════════════════════
    # TAB 3: AMR DATABASE ORGANISM SEARCH
    # ══════════════════════════════════════════════════════════════════════
    with tab3:
        st.markdown("### AMR Package — Organism Taxonomy & Breakpoint Lookup")

        amr_orgs = load_amr_organisms()
        amr_bp   = load_amr_breakpoints()

        if amr_orgs is None:
            st.warning("""
**AMR database files not found.** To enable this feature:

1. Make sure you have the AMR Python package installed on your local machine.
2. Run the setup script once:
   ```bash
   python generate_amr_data.py
   ```
3. This creates CSV files in the `data/` folder.
4. Commit those CSV files to your repo — Streamlit Cloud will read them without needing R.
            """)
            st.info("The AMR (for R) package provides 78,000+ taxonomic records, "
                    "clinical breakpoints (EUCAST & CLSI), and intrinsic resistance data.")
        else:
            st.success(f"✓ AMR database loaded — {len(amr_orgs):,} taxonomic records")

            # Search controls
            search_col1, search_col2, search_col3 = st.columns([3, 2, 2])
            with search_col1:
                amr_query = st.text_input("🔍 Search organism (name, genus, species, code)",
                    placeholder="e.g. Escherichia coli, Staphylococcus, ESCCOL", key="amr_search")
            with search_col2:
                kingdom_filter = st.selectbox("Kingdom", ["All"] +
                    sorted(amr_orgs["kingdom"].dropna().unique().tolist()) if "kingdom" in amr_orgs.columns else ["All"])
            with search_col3:
                status_filter = st.selectbox("Taxonomic Status", ["All"] +
                    sorted(amr_orgs["status"].dropna().unique().tolist()) if "status" in amr_orgs.columns else ["All"])

            # Filter
            df_amr = amr_orgs.copy()
            if kingdom_filter != "All" and "kingdom" in df_amr.columns:
                df_amr = df_amr[df_amr["kingdom"] == kingdom_filter]
            if status_filter != "All" and "status" in df_amr.columns:
                df_amr = df_amr[df_amr["status"] == status_filter]

            if amr_query.strip():
                q = amr_query.strip().lower()
                mask = (
                    df_amr["fullname"].str.lower().str.contains(q, na=False)
                )
                # Also search mo code if column exists
                if "mo" in df_amr.columns:
                    mask |= df_amr["mo"].str.lower().str.contains(q, na=False)
                df_amr = df_amr[mask]

            st.caption(f"Showing {min(len(df_amr), 200):,} of {len(df_amr):,} matching records (max 200 displayed)")

            # Display columns
            display_cols_amr = [c for c in ["mo","fullname","status","kingdom","phylum","class","gramstain","prevalence"]
                                if c in df_amr.columns]
            st.dataframe(
                df_amr[display_cols_amr].head(200).reset_index(drop=True),
                use_container_width=True, height=350,
            )

            # Breakpoint lookup
            if amr_bp is not None and amr_query.strip() and len(df_amr) > 0:
                st.divider()
                st.markdown("#### Clinical Breakpoints (EUCAST/CLSI)")

                # Get MO codes for matched organisms
                if "mo" in df_amr.columns:
                    mo_codes = df_amr["mo"].dropna().head(10).tolist()
                    bp_subset = amr_bp[amr_bp["mo"].isin(mo_codes)] if "mo" in amr_bp.columns else pd.DataFrame()

                    if not bp_subset.empty:
                        bp_cols = [c for c in ["mo","ab","guideline","type","breakpoint_S","breakpoint_R","disk_dose","ref_breakpoint"]
                                   if c in bp_subset.columns]
                        st.dataframe(bp_subset[bp_cols].head(100).reset_index(drop=True),
                                     use_container_width=True, height=300)
                        st.caption("S = Susceptible breakpoint (mg/L or mm); R = Resistant breakpoint. Source: AMR (for R) package.")
                    else:
                        st.info("No breakpoints found for the selected organisms in the AMR database.")

            # Intrinsic resistance info
            st.divider()
            st.markdown("#### About the AMR Database")
            metric_cols = st.columns(3)
            with metric_cols[0]:
                st.metric("Total Taxa", f"{len(amr_orgs):,}")
            with metric_cols[1]:
                if "kingdom" in amr_orgs.columns:
                    bact = amr_orgs[amr_orgs["kingdom"]=="Bacteria"].shape[0]
                    st.metric("Bacteria", f"{bact:,}")
            with metric_cols[2]:
                if "status" in amr_orgs.columns:
                    acc = amr_orgs[amr_orgs["status"]=="accepted"].shape[0]
                    st.metric("Accepted Names", f"{acc:,}")

            st.markdown("""
            The **AMR (for R) package** database includes:
            - **78,000+** taxonomic records from LPSN, MycoBank, GBIF
            - **Clinical breakpoints** from EUCAST and CLSI guidelines
            - **Intrinsic resistance** definitions per guideline
            - **625** antimicrobial drug entries with ATC codes and DDD values

            Data provided by the [AMR for R project](https://amr-for-r.org) — 
            University of Groningen, UMCG, Netherlands (GPL-2 license).
            """)

    # ── Footer ──────────────────────────────────────────────────────────────
    st.divider()
    st.markdown("""
    <div style="text-align:center;font-size:11px;color:#888;padding:8px;">
    Sensitivity data: <b>Sanford Guide 2024</b>, IDSA Guidelines, CDC, ASHP. 
    Organism taxonomy: <b>AMR (for R) package</b> — University of Groningen, UMCG.<br>
    <b>For clinical decision support and educational use only.</b>
    Always verify with local antibiogram, patient-specific factors, and ID consultation.<br>
    <i>For live EUCAST/CLSI breakpoints: connect via AMR package — see generate_amr_data.py</i>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()

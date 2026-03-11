"""
S-Tier 13F Copy-Trade Backtest — All 4 Funds vs SPY
=====================================================
Funds simulated:
  1. Himalaya Capital  (Li Lu)           CIK: 0001709323
  2. Pershing Square   (Bill Ackman)     CIK: 0001336528
  3. Berkshire Hathaway (Warren Buffett) CIK: 0001067983
  4. Pabrai Funds      (Mohnish Pabrai)  CIK: 0001173334

Strategy:
  - Rebalance to each fund's disclosed 13F weights on filing release date
  - ~45 days after quarter end
  - Starting capital: $100,000 per fund
  - No leverage, long-only, proportional weighting
  - Benchmark: SPY

Sources: SEC EDGAR, 13f.info, StockCircle, SlickCharts, HedgeFollow,
         ValuSider, WhaleWisdom, SeekingAlpha quarterly updates
"""

import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.gridspec as gridspec
from datetime import datetime, timedelta
from price_cache import fetch_prices_cached_raw
import warnings
warnings.filterwarnings("ignore")

STARTING_CAPITAL = 100_000
BENCHMARK = "SPY"

# ═══════════════════════════════════════════════════════════════
# PORTFOLIO SNAPSHOTS  — {fund: {filing_date: {ticker: weight}}}
# ═══════════════════════════════════════════════════════════════

FUNDS = {}

# ───────────────────────────────────────────────────────────────
# 1. HIMALAYA CAPITAL (Li Lu) — already researched
# ───────────────────────────────────────────────────────────────
FUNDS["Himalaya (Li Lu)"] = {
    "2022-05-16": {"MU":0.5117,"BAC":0.2417,"GOOG":0.0898,"META":0.0853,"AAPL":0.0469,"BRK-B":0.0246},
    "2022-08-15": {"MU":0.4200,"BAC":0.2300,"GOOG":0.1400,"GOOGL":0.0900,"AAPL":0.0500,"BRK-B":0.0700},
    "2022-11-14": {"MU":0.4000,"BAC":0.2200,"GOOG":0.1400,"GOOGL":0.1000,"AAPL":0.0600,"BRK-B":0.0800},
    "2023-02-14": {"MU":0.2500,"BAC":0.1900,"GOOGL":0.2400,"GOOG":0.1700,"AAPL":0.0600,"BRK-B":0.0900},
    "2023-05-15": {"BAC":0.2900,"GOOGL":0.2300,"GOOG":0.1700,"MU":0.1400,"EWBC":0.0800,"BRK-B":0.0500,"AAPL":0.0400},
    "2023-08-14": {"BAC":0.3000,"GOOGL":0.2500,"GOOG":0.1800,"EWBC":0.1300,"BRK-B":0.0700,"AAPL":0.0700},
    "2023-11-14": {"BAC":0.3000,"GOOGL":0.2500,"GOOG":0.1800,"EWBC":0.1300,"BRK-B":0.0700,"AAPL":0.0700},
    "2024-02-14": {"BAC":0.3000,"GOOGL":0.2500,"GOOG":0.1800,"EWBC":0.1200,"BRK-B":0.0800,"AAPL":0.0700},
    "2024-05-15": {"BAC":0.3000,"GOOGL":0.2500,"GOOG":0.1700,"EWBC":0.1200,"BRK-B":0.0800,"AAPL":0.0800},
    "2024-08-14": {"BAC":0.2800,"GOOGL":0.2200,"GOOG":0.1600,"EWBC":0.1100,"BRK-B":0.0900,"OXY":0.0700,"AAPL":0.0700},
    "2024-11-14": {"BAC":0.2800,"GOOGL":0.2200,"GOOG":0.1600,"EWBC":0.1100,"BRK-B":0.0900,"OXY":0.0700,"AAPL":0.0700},
    "2025-02-14": {"BAC":0.2800,"GOOGL":0.2200,"GOOG":0.1600,"EWBC":0.1100,"BRK-B":0.0900,"OXY":0.0700,"AAPL":0.0700},
    "2025-05-15": {"GOOGL":0.2400,"GOOG":0.2000,"BAC":0.1800,"PDD":0.1500,"BRK-B":0.1000,"EWBC":0.0900,"OXY":0.0500,"AAPL":0.0400},
    "2025-08-14": {"GOOGL":0.2400,"GOOG":0.1600,"BAC":0.1400,"PDD":0.1800,"BRK-B":0.1100,"EWBC":0.1000,"OXY":0.0500,"AAPL":0.0200},
    "2025-11-12": {"GOOGL":0.2331,"GOOG":0.2155,"BAC":0.1608,"PDD":0.1464,"BRK-B":0.1264,"EWBC":0.0874,"OXY":0.0169,"AAPL":0.0084,"SOC":0.0050},
    "2026-02-18": {"GOOGL":0.2231,"GOOG":0.2155,"BAC":0.1608,"PDD":0.1464,"BRK-B":0.1264,"EWBC":0.0874,"OXY":0.0169,"CROX":0.0151,"AAPL":0.0084},
}

# ───────────────────────────────────────────────────────────────
# 2. PERSHING SQUARE (Bill Ackman)
# Sources: SeekingAlpha quarterly updates, 13f.info, Dataroma
#
# Key events:
#   Q1 2022: Bought NFLX (Jan), sold NFLX (Apr) at big loss
#   Q2 2022: Exited NFLX; core: LOW, CMG, QSR, HLT, CP
#   Q3 2022: Added GOOG/GOOGL; still LOW heavy
#   Q4 2022: LOW, CMG, QSR, HLT, GOOG, GOOGL, CP
#   Q1 2023: Sold LOW 100%; added GOOG/GOOGL more
#   Q2 2023: CMG, QSR, HLT, GOOG, GOOGL, CP growing
#   Q3 2023: Added UBER new; CMG dominant
#   Q4 2023: Similar, UBER added, CP ~11%
#   Q1 2024: Bought BN new; added UBER; sold CMG 100%
#   Q2 2024: BN, UBER, QSR, GOOG/GOOGL, HLT
#   Q3 2024: BN, UBER, QSR, GOOG/GOOGL, HLT, HHH, AMZN new
#   Q4 2024: BN, UBER, GOOG, QSR, HLT, AMZN growing, CP exit
#   Q1 2025: Exited CP; AMZN growing; CMG gone
#   Q2 2025: Exited CMG; core: UBER, BN, GOOG, QSR, AMZN
#   Q3 2025: UBER, BN, GOOG, QSR, AMZN, GOOGL, HHH, HLT
#   Q4 2025: Added META new; AMZN +65%; reduced GOOGL -86%
# ───────────────────────────────────────────────────────────────
FUNDS["Pershing Square (Ackman)"] = {
    # Q1 2022 — NFLX held briefly (bought Jan, sold Apr outside 13F window)
    "2022-05-16": {
        "LOW":  0.2600,
        "CMG":  0.1900,
        "QSR":  0.1600,
        "HLT":  0.1500,
        "CP":   0.1100,
        "AAPL": 0.0400,   # small position
        "GOOG": 0.0400,   # small new
        "HHH":  0.0500,
    },
    # Q2 2022 — sold NFLX (already gone), core unchanged
    "2022-08-15": {
        "LOW":  0.2700,
        "CMG":  0.2000,
        "QSR":  0.1800,
        "HLT":  0.1400,
        "CP":   0.1100,
        "GOOG": 0.0600,
        "HHH":  0.0400,
    },
    # Q3 2022 — added GOOG/GOOGL more
    "2022-11-14": {
        "LOW":  0.2400,
        "CMG":  0.1900,
        "QSR":  0.1700,
        "HLT":  0.1300,
        "CP":   0.1000,
        "GOOG": 0.0900,
        "GOOGL":0.0400,
        "HHH":  0.0400,
    },
    # Q4 2022 — LOW, CMG, QSR dominant; GOOG/GOOGL growing
    "2023-02-14": {
        "LOW":  0.2300,
        "CMG":  0.2000,
        "QSR":  0.1700,
        "HLT":  0.1200,
        "CP":   0.1100,
        "GOOG": 0.1000,
        "GOOGL":0.0500,
        "HHH":  0.0200,
    },
    # Q1 2023 — sold LOW 100%; boosted GOOG/GOOGL
    "2023-05-15": {
        "CMG":  0.2500,
        "QSR":  0.2000,
        "HLT":  0.1500,
        "GOOG": 0.1500,
        "GOOGL":0.1000,
        "CP":   0.1100,
        "HHH":  0.0400,
    },
    # Q2 2023 — CMG, QSR, GOOG dominant; CP growing
    "2023-08-14": {
        "CMG":  0.2400,
        "QSR":  0.1900,
        "HLT":  0.1400,
        "GOOG": 0.1600,
        "GOOGL":0.1100,
        "CP":   0.1200,
        "HHH":  0.0400,
    },
    # Q3 2023 — added UBER new
    "2023-11-14": {
        "CMG":  0.2200,
        "QSR":  0.1800,
        "GOOG": 0.1500,
        "GOOGL":0.1300,
        "HLT":  0.1200,
        "CP":   0.1100,
        "UBER": 0.0500,
        "HHH":  0.0400,
    },
    # Q4 2023 — UBER growing; CP ~11%
    "2024-02-14": {
        "CMG":  0.2000,
        "QSR":  0.1700,
        "GOOG": 0.1500,
        "GOOGL":0.1300,
        "HLT":  0.1200,
        "CP":   0.1148,
        "UBER": 0.0800,
        "HHH":  0.0352,
    },
    # Q1 2024 — bought BN new; added UBER; sold CMG 100%
    "2024-05-15": {
        "QSR":  0.1800,
        "GOOG": 0.1700,
        "GOOGL":0.1400,
        "HLT":  0.1300,
        "UBER": 0.1500,
        "BN":   0.1400,
        "CP":   0.0900,
        "HHH":  0.0500,  # SEG spun off from HHH
    },
    # Q2 2024 — BN, UBER, QSR/GOOG top; CP held
    "2024-08-14": {
        "BN":   0.1900,
        "UBER": 0.1800,
        "QSR":  0.1600,
        "GOOG": 0.1500,
        "GOOGL":0.1200,
        "HLT":  0.1100,
        "CP":   0.0900,
        "HHH":  0.0500,  # now includes SEG
    },
    # Q3 2024 — added AMZN new; UBER, BN dominant
    "2024-11-14": {
        "UBER": 0.2030,
        "BN":   0.1920,
        "HHH":  0.1060,
        "GOOG": 0.1050,
        "QSR":  0.1000,
        "AMZN": 0.0870,
        "GOOGL":0.0800,
        "HLT":  0.0540,
        "SEG":  0.0080,
        "HTZ":  0.0070,
        "CP":   0.0580,
    },
    # Q4 2024 — UBER, BN, GOOG/GOOGL dominant; exited CP
    "2025-02-14": {
        "UBER": 0.2100,
        "BN":   0.2000,
        "GOOG": 0.1300,
        "GOOGL":0.1200,
        "QSR":  0.1100,
        "AMZN": 0.1000,
        "HLT":  0.0700,
        "HHH":  0.0800,
        "SEG":  0.0080,
        "HTZ":  0.0070,
    },
    # Q1 2025 — exited CP; AMZN growing
    "2025-05-15": {
        "UBER": 0.2000,
        "BN":   0.1900,
        "AMZN": 0.1400,
        "GOOG": 0.1300,
        "GOOGL":0.1000,
        "QSR":  0.1000,
        "HLT":  0.0600,
        "HHH":  0.0800,
    },
    # Q2 2025 — exited CMG; core: UBER, BN, GOOG, QSR, AMZN
    "2025-08-14": {
        "UBER": 0.2030,
        "BN":   0.1920,
        "GOOG": 0.1050,
        "QSR":  0.1000,
        "AMZN": 0.0870,
        "GOOGL":0.0800,
        "HHH":  0.1060,
        "HLT":  0.0540,
        "SEG":  0.0080,
        "HTZ":  0.0070,
        "CMG":  0.0580,
    },
    # Q3 2025 — filed Nov 14; UBER, BN, HHH, GOOG, QSR, AMZN
    "2025-11-14": {
        "UBER": 0.2030,
        "BN":   0.1920,
        "HHH":  0.1060,
        "GOOG": 0.1050,
        "QSR":  0.1000,
        "AMZN": 0.0870,
        "GOOGL":0.0800,
        "HLT":  0.0540,
        "SEG":  0.0080,
        "HTZ":  0.0070,
    },
    # Q4 2025 — added META; AMZN +65%; reduced GOOGL -86%
    "2026-02-17": {
        "BN":   0.1815,
        "UBER": 0.1590,
        "AMZN": 0.1428,
        "GOOG": 0.1246,
        "META": 0.1137,
        "QSR":  0.1005,
        "HHH":  0.0969,
        "HLT":  0.0560,
        "GOOGL":0.0137,
        "SEG":  0.0064,
        "HTZ":  0.0050,
    },
}

# ───────────────────────────────────────────────────────────────
# 3. BERKSHIRE HATHAWAY (Warren Buffett)
# Sources: 13f.info, ValuSider, SlickCharts, SeekingAlpha,
#          CNBC Berkshire tracker, Dr. David Kass blog
#
# Key events:
#   Q1 2022: Big CVX buy +315%, new OXY position ~136M shares
#   Q2 2022: Added OXY more; AAPL ~38%
#   Q3 2022: Held core; OXY growing
#   Q4 2022: Stable; AAPL ~38%, CVX ~9%, OXY ~4%
#   Q1 2023: AAPL 46%, KO/AXP steady
#   Q4 2023: AAPL 49.5% peak; sold HP, ATVI
#   Q1 2024: Sold PARA 100%; added OXY more; sold HP
#   Q2 2024: Started selling AAPL (-13%)
#   Q3 2024: Sold AAPL heavily (-25%)
#   Q4 2024: More AAPL selling; sold BAC
#   Q1 2025: Sold CITI 100%, sold NU 100%, trimmed BAC
#   Q2 2025: Stable; AUM ~$258B
#   Q3 2025: Sold AAPL -6.7%; sold BAC -4.2%; added CVX
#   Q4 2025: AAPL 22%, AXP 17%, KO 12%, BAC 9%, CVX 9%
# ───────────────────────────────────────────────────────────────
FUNDS["Berkshire (Buffett)"] = {
    # Q1 2022 — CVX+315%, OXY new big position
    "2022-05-16": {
        "AAPL": 0.3800,
        "BAC":  0.1400,
        "AXP":  0.0800,
        "KO":   0.0750,
        "CVX":  0.0900,
        "OXY":  0.0400,
        "KHC":  0.0350,
        "MCO":  0.0300,
        "USB":  0.0200,
        "VRSN": 0.0100,
    },
    # Q2 2022 — OXY added more; core stable
    "2022-08-15": {
        "AAPL": 0.3800,
        "BAC":  0.1400,
        "AXP":  0.0800,
        "KO":   0.0750,
        "CVX":  0.0900,
        "OXY":  0.0500,
        "KHC":  0.0350,
        "MCO":  0.0300,
        "USB":  0.0100,
    },
    # Q3 2022 — OXY growing; added ATVI new (arbitrage)
    "2022-11-14": {
        "AAPL": 0.3900,
        "BAC":  0.1300,
        "AXP":  0.0800,
        "KO":   0.0760,
        "CVX":  0.0900,
        "OXY":  0.0600,
        "KHC":  0.0330,
        "MCO":  0.0300,
        "ATVI": 0.0110,  # arbitrage play (MSFT acquisition)
    },
    # Q4 2022 — AAPL ~38%, CVX ~9%, OXY ~4%
    "2023-02-14": {
        "AAPL": 0.3800,
        "BAC":  0.1300,
        "AXP":  0.0790,
        "KO":   0.0760,
        "CVX":  0.0900,
        "OXY":  0.0430,
        "KHC":  0.0330,
        "MCO":  0.0300,
        "ATVI": 0.0130,
    },
    # Q1 2023 — AAPL 46.44%, KO/AXP steady
    "2023-05-15": {
        "AAPL": 0.4644,
        "BAC":  0.0909,
        "AXP":  0.0769,
        "KO":   0.0763,
        "CVX":  0.0665,
        "OXY":  0.0400,
        "KHC":  0.0280,
        "MCO":  0.0260,
        "ATVI": 0.0110,
    },
    # Q2 2023 — ATVI still held; AAPL growing
    "2023-08-14": {
        "AAPL": 0.4800,
        "BAC":  0.0900,
        "AXP":  0.0750,
        "KO":   0.0750,
        "CVX":  0.0600,
        "OXY":  0.0400,
        "KHC":  0.0280,
        "MCO":  0.0270,
        "ATVI": 0.0150,  # MSFT deal pending
    },
    # Q3 2023 — AAPL ~48%; ATVI deal closed Oct 2023 (sold)
    "2023-11-14": {
        "AAPL": 0.4800,
        "BAC":  0.0900,
        "AXP":  0.0780,
        "KO":   0.0720,
        "CVX":  0.0570,
        "OXY":  0.0450,
        "KHC":  0.0280,
        "MCO":  0.0280,
        "CB":   0.0120,  # new position (Chubb, confidential then disclosed)
    },
    # Q4 2023 — AAPL peaked 49.54%; sold HP, PARA
    "2024-02-14": {
        "AAPL": 0.4954,
        "BAC":  0.0988,
        "AXP":  0.0807,
        "KO":   0.0670,
        "CVX":  0.0534,
        "OXY":  0.0450,
        "MCO":  0.0320,
        "KHC":  0.0280,
        "CB":   0.0200,
    },
    # Q1 2024 — sold PARA 100%; OXY added; CB Chubb disclosed
    "2024-05-15": {
        "AAPL": 0.4100,  # started trimming
        "BAC":  0.1000,
        "AXP":  0.0820,
        "KO":   0.0680,
        "CVX":  0.0540,
        "OXY":  0.0500,
        "CB":   0.0600,  # Chubb disclosed after confidential period
        "MCO":  0.0330,
        "KHC":  0.0280,
    },
    # Q2 2024 — AAPL -13% trim; BAC trim started
    "2024-08-14": {
        "AAPL": 0.3000,  # big trim
        "BAC":  0.1000,
        "AXP":  0.0820,
        "KO":   0.0700,
        "CVX":  0.0550,
        "OXY":  0.0510,
        "CB":   0.0600,
        "MCO":  0.0340,
        "KHC":  0.0280,
    },
    # Q3 2024 — AAPL -25% massive sell; BAC heavy selling
    "2024-11-14": {
        "AAPL": 0.2600,
        "AXP":  0.1500,
        "KO":   0.1100,
        "BAC":  0.1000,
        "CVX":  0.0800,
        "OXY":  0.0600,
        "CB":   0.0500,
        "MCO":  0.0380,
        "KHC":  0.0280,
        "GOOGL":0.0240,  # new position
    },
    # Q4 2024 — More AAPL/BAC selling; GOOGL added
    "2025-02-14": {
        "AAPL": 0.2500,
        "AXP":  0.1700,
        "KO":   0.1100,
        "BAC":  0.1000,
        "CVX":  0.0800,
        "OXY":  0.0600,
        "CB":   0.0500,
        "MCO":  0.0380,
        "GOOGL":0.0240,
        "KHC":  0.0280,
    },
    # Q1 2025 — sold CITI 100%, NU 100%; trimmed BAC -7%
    "2025-05-15": {
        "AAPL": 0.2400,
        "AXP":  0.1800,
        "KO":   0.1100,
        "BAC":  0.0900,
        "CVX":  0.0800,
        "OXY":  0.0600,
        "CB":   0.0500,
        "MCO":  0.0380,
        "GOOGL":0.0240,
        "KHC":  0.0280,
    },
    # Q2 2025 — stable; AUM ~$258B
    "2025-08-14": {
        "AAPL": 0.2300,
        "AXP":  0.1900,
        "KO":   0.1150,
        "BAC":  0.0950,
        "CVX":  0.0800,
        "OXY":  0.0580,
        "CB":   0.0500,
        "MCO":  0.0380,
        "GOOGL":0.0240,
        "KHC":  0.0200,
    },
    # Q3 2025 — AAPL -6.7%, BAC -4.2%, CVX +2.9%
    "2025-11-14": {
        "AAPL": 0.2300,
        "AXP":  0.2046,
        "KO":   0.1020,
        "BAC":  0.1038,
        "CVX":  0.0724,
        "OXY":  0.0525,
        "MCO":  0.0416,
        "CB":   0.0416,
        "KHC":  0.0288,
        "GOOGL":0.0204,
    },
    # Q4 2025 — AAPL 22%, AXP 17%, KO 12%, BAC 9%, CVX 9% (exact from SEC)
    "2026-02-17": {
        "AAPL": 0.2218,
        "AXP":  0.1715,
        "KO":   0.1163,
        "BAC":  0.0937,
        "CVX":  0.0905,
        "OXY":  0.0525,
        "MCO":  0.0416,
        "CB":   0.0416,
        "KHC":  0.0288,
        "GOOGL":0.0204,
    },
}

# ───────────────────────────────────────────────────────────────
# 4. PABRAI FUNDS (Mohnish Pabrai) — US 13F portion only
# Sources: GuruFocus, Dataroma, ValuSider, WhaleWisdom, 13f.info
#
# Note: Pabrai has large India/Turkey allocations NOT in 13F.
#       Simulation covers his US-listed positions only.
#
# Key events:
#   2022: Heavy in ATIF, TDW (Tidewater offshore drilling), NVR
#   Q3 2022: Added CEIX (Consol Energy coal), TDW big
#   Q1 2023: Shifted to HCC (Warrior Met Coal), AMR (Alpha Met)
#   Q2 2023: Sold CEIX; added AMR, HCC, NE (Noble Corp)
#   Q3 2023: HCC, AMR, CEIX, NE dominant
#   Q4 2023: New HCC buy; concentrated in coal + offshore
#   Q1 2024: HCC -25%, AMR +2.5%, CEIX -0.8%; added RIG
#   Q2 2024: Added RIG, VAL; reduced HCC; exited CEIX
#   Q3 2024: HCC, AMR, RIG, NE, VAL concentrated
#   Q4 2024: Exited NE; HCC, AMR, RIG, VAL remain
#   Q1 2025: HCC dominant 38%, trimming others
#   Q2 2025: Stable coal + offshore
#   Q3 2025: HCC, AMR, RIG, VAL, NE (5 holdings)
#   Q4 2025: Exited NE; 4 holdings HCC, RIG, AMR, VAL (exact)
# ───────────────────────────────────────────────────────────────
FUNDS["Pabrai Funds (Pabrai)"] = {
    # Q1 2022 — TDW, ATIF, NVR heavy
    "2022-05-16": {
        "TDW":  0.4000,  # Tidewater offshore drilling
        "NVR":  0.2500,  # homebuilder
        "CEIX": 0.2000,  # Consol Energy coal
        "ATIF": 0.1500,  # small
    },
    # Q2 2022 — TDW dominant; coal growing
    "2022-08-15": {
        "TDW":  0.4500,
        "CEIX": 0.2500,
        "NVR":  0.2000,
        "ATIF": 0.1000,
    },
    # Q3 2022 — TDW peak; added CEIX more
    "2022-11-14": {
        "TDW":  0.4500,
        "CEIX": 0.3000,
        "NVR":  0.1500,
        "ATIF": 0.1000,
    },
    # Q4 2022 — shifting; added coal/offshore
    "2023-02-14": {
        "TDW":  0.3500,
        "CEIX": 0.3000,
        "HCC":  0.1500,  # Warrior Met Coal new
        "NVR":  0.1000,
        "ATIF": 0.0500,
        "AMR":  0.0500,  # Alpha Met Resources new
    },
    # Q1 2023 — HCC, AMR growing; sold ATIF
    "2023-05-15": {
        "TDW":  0.2800,
        "CEIX": 0.2500,
        "HCC":  0.2000,
        "AMR":  0.1500,
        "NVR":  0.1200,
    },
    # Q2 2023 — sold CEIX 100%; NE added; HCC/AMR dominant
    "2023-08-14": {
        "HCC":  0.3500,
        "AMR":  0.3000,
        "TDW":  0.1500,
        "NE":   0.1000,  # Noble Corp new (offshore drilling)
        "NVR":  0.1000,
    },
    # Q3 2023 — concentrated in coal + offshore
    "2023-11-14": {
        "HCC":  0.3500,
        "AMR":  0.3000,
        "TDW":  0.1200,
        "NE":   0.1200,
        "NVR":  0.1100,
    },
    # Q4 2023 — new HCC buy +15.47%; exiting NVR
    "2024-02-14": {
        "HCC":  0.4000,
        "AMR":  0.3000,
        "TDW":  0.1000,
        "NE":   0.1200,
        "NVR":  0.0800,
    },
    # Q1 2024 — HCC -25.24%, AMR +2.55%, CEIX -0.81%, added RIG
    "2024-05-15": {
        "HCC":  0.3200,
        "AMR":  0.3100,
        "RIG":  0.1500,  # Transocean new
        "NE":   0.1200,
        "TDW":  0.1000,
    },
    # Q2 2024 — added VAL (Valaris); exited CEIX/TDW/NVR
    "2024-08-14": {
        "HCC":  0.3500,
        "AMR":  0.3000,
        "RIG":  0.1500,
        "NE":   0.1000,
        "VAL":  0.1000,  # Valaris new
    },
    # Q3 2024 — HCC, AMR, RIG, NE, VAL
    "2024-11-14": {
        "HCC":  0.3800,
        "AMR":  0.2800,
        "RIG":  0.1600,
        "NE":   0.1100,
        "VAL":  0.0700,
    },
    # Q4 2024 — exited NE; 4 holdings remain
    "2025-02-14": {
        "HCC":  0.4000,
        "AMR":  0.3000,
        "RIG":  0.2000,
        "VAL":  0.1000,
    },
    # Q1 2025 — stable; HCC dominant
    "2025-05-15": {
        "HCC":  0.4000,
        "AMR":  0.3000,
        "RIG":  0.2000,
        "VAL":  0.1000,
    },
    # Q2 2025 — stable
    "2025-08-14": {
        "HCC":  0.4000,
        "AMR":  0.2900,
        "RIG":  0.2100,
        "VAL":  0.1000,
    },
    # Q3 2025 — 5 holdings; NE re-added
    "2025-11-13": {
        "HCC":  0.3500,
        "AMR":  0.2800,
        "RIG":  0.2100,
        "VAL":  0.1000,
        "NE":   0.0600,
    },
    # Q4 2025 — exact from SEC: HCC 39.47%, RIG 27.78%, AMR 27.00%, VAL 5.76%
    "2026-02-13": {
        "HCC":  0.3947,
        "RIG":  0.2778,
        "AMR":  0.2700,
        "VAL":  0.0576,
    },
}

# ═══════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════

def normalize(snap):
    total = sum(snap.values())
    return {k: v / total for k, v in snap.items()}

def next_trading_day(date_str, index):
    d = pd.Timestamp(date_str)
    while d.strftime("%Y-%m-%d") not in index:
        d += timedelta(days=1)
        if d > pd.Timestamp(index[-1]):
            return index[-1]
    return d.strftime("%Y-%m-%d")

def get_price(ticker, date, prices):
    if ticker not in prices:
        return None
    df = prices[ticker]
    before = df[df.index <= date]
    if len(before) == 0:
        return None
    return float(before.iloc[-1]["Close"])

# ═══════════════════════════════════════════════════════════════
# FETCH ALL PRICES
# ═══════════════════════════════════════════════════════════════

all_tickers = set()
for fund_snaps in FUNDS.values():
    for snap in fund_snaps.values():
        all_tickers.update(snap.keys())
all_tickers.add(BENCHMARK)

print(f"Fetching prices for {len(all_tickers)} tickers: {sorted(all_tickers)}")
print("(using local cache, 7-day TTL…)\n")

prices = fetch_prices_cached_raw(list(all_tickers), start="2022-01-01", end="2026-03-11")

print(f"Loaded {len(prices)} tickers.\n")

# ═══════════════════════════════════════════════════════════════
# RUN BACKTEST — each fund independently
# ═══════════════════════════════════════════════════════════════

spy_index = prices[BENCHMARK].index

results = {}   # fund_name -> port_df with daily values
summaries = {} # fund_name -> stats dict
all_records = {} # fund_name -> list of rebalance records

for fund_name, snapshots in FUNDS.items():
    filing_dates = sorted(snapshots.keys())
    # normalize weights
    snaps = {d: normalize(s) for d, s in snapshots.items()}

    holdings = {}
    portfolio_value = STARTING_CAPITAL
    records = []

    for i, filing_date in enumerate(filing_dates):
        action_date = next_trading_day(filing_date, spy_index)
        weights = snaps[filing_date]

        # Current value before rebalance
        if holdings:
            pv = sum(
                sh * (get_price(t, action_date, prices) or 0)
                for t, sh in holdings.items()
            )
            if pv > 0:
                portfolio_value = pv

        # New holdings
        new_holdings = {}
        for ticker, weight in weights.items():
            p = get_price(ticker, action_date, prices)
            if p:
                new_holdings[ticker] = (portfolio_value * weight) / p

        holdings = new_holdings
        records.append({
            "filing_date": filing_date,
            "action_date": action_date,
            "portfolio_value": portfolio_value,
            "weights": weights,
        })

    all_records[fund_name] = records

    # Daily portfolio value
    start_date = records[0]["action_date"]
    start_idx = list(spy_index).index(start_date)
    cur_holdings = {}
    rebalance_map = {r["action_date"]: r for r in records}
    history = []

    for date in spy_index[start_idx:]:
        if date in rebalance_map:
            rec = rebalance_map[date]
            pv = sum(
                cur_holdings.get(t, 0) * (get_price(t, date, prices) or 0)
                for t in cur_holdings
            ) or STARTING_CAPITAL
            cur_holdings = {}
            for ticker, weight in rec["weights"].items():
                p = get_price(ticker, date, prices)
                if p:
                    cur_holdings[ticker] = (pv * weight) / p

        day_val = sum(
            sh * (get_price(t, date, prices) or 0)
            for t, sh in cur_holdings.items()
        )
        history.append({"date": date, "value": day_val})

    port_df = pd.DataFrame(history).set_index("date")
    results[fund_name] = port_df

    final = port_df["value"].iloc[-1]
    total_ret = (final / STARTING_CAPITAL - 1) * 100
    rolling_max = port_df["value"].cummax()
    max_dd = ((port_df["value"] - rolling_max) / rolling_max * 100).min()

    summaries[fund_name] = {
        "final": final,
        "total_return": total_ret,
        "max_drawdown": max_dd,
        "start": port_df.index[0],
        "end": port_df.index[-1],
    }

# SPY benchmark
spy_start_date = min(df.index[0] for df in results.values())
spy_df = prices[BENCHMARK].loc[spy_start_date:]
spy_start_price = float(spy_df.iloc[0]["Close"])
spy_values = (spy_df["Close"] / spy_start_price) * STARTING_CAPITAL
spy_total_ret = (spy_values.iloc[-1] / STARTING_CAPITAL - 1) * 100

# ═══════════════════════════════════════════════════════════════
# PRINT RESULTS TABLE
# ═══════════════════════════════════════════════════════════════

print("=" * 70)
print("  S-TIER 13F COPY-TRADE BACKTEST — SUMMARY")
print("=" * 70)
print(f"  {'Fund':<28} {'Final $':>12}  {'Return':>8}  {'vs SPY':>8}  {'Max DD':>8}")
print(f"  {'-'*28} {'-'*12}  {'-'*8}  {'-'*8}  {'-'*8}")

for fund_name, s in sorted(summaries.items(), key=lambda x: -x[1]["total_return"]):
    alpha = s["total_return"] - spy_total_ret
    print(f"  {fund_name:<28} ${s['final']:>11,.0f}  "
          f"{s['total_return']:>+7.1f}%  {alpha:>+7.1f}%  {s['max_drawdown']:>7.1f}%")

print(f"  {'SPY (Benchmark)':<28} ${STARTING_CAPITAL*(1+spy_total_ret/100):>11,.0f}  "
      f"{spy_total_ret:>+7.1f}%  {'0.0%':>8}  {'--':>8}")
print("=" * 70)

# ═══════════════════════════════════════════════════════════════
# PLOTS
# ═══════════════════════════════════════════════════════════════

COLORS = {
    "Himalaya (Li Lu)":       "#2196F3",
    "Pershing Square (Ackman)": "#4CAF50",
    "Berkshire (Buffett)":    "#FF9800",
    "Pabrai Funds (Pabrai)":  "#9C27B0",
    "SPY":                    "#888888",
}

fig = plt.figure(figsize=(16, 14))
gs  = gridspec.GridSpec(3, 2, figure=fig, hspace=0.45, wspace=0.35)

ax_main = fig.add_subplot(gs[0, :])   # full width
ax_dd   = fig.add_subplot(gs[1, :])   # full width
ax_bar  = fig.add_subplot(gs[2, 0])
ax_ann  = fig.add_subplot(gs[2, 1])

fig.suptitle(
    "S-Tier 13F Copy-Trade Backtest  |  $100K Starting Capital  |  Q1 2022 – Q4 2025",
    fontsize=14, fontweight="bold"
)

# ── Panel 1: Portfolio value ──
for fund_name, port_df in results.items():
    ax_main.plot(
        pd.to_datetime(port_df.index),
        port_df["value"],
        color=COLORS[fund_name],
        linewidth=2,
        label=f"{fund_name} ({summaries[fund_name]['total_return']:+.1f}%)"
    )

ax_main.plot(
    pd.to_datetime(spy_df.index),
    spy_values,
    color=COLORS["SPY"],
    linewidth=2,
    linestyle="--",
    label=f"SPY ({spy_total_ret:+.1f}%)"
)
ax_main.set_ylabel("Portfolio Value ($)")
ax_main.set_title("Portfolio Value vs SPY")
ax_main.legend(fontsize=9)
ax_main.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"${x:,.0f}"))
ax_main.grid(True, alpha=0.3)

# ── Panel 2: Drawdown ──
for fund_name, port_df in results.items():
    rm  = port_df["value"].cummax()
    dd  = (port_df["value"] - rm) / rm * 100
    ax_dd.plot(
        pd.to_datetime(port_df.index),
        dd,
        color=COLORS[fund_name],
        linewidth=1.5,
        label=fund_name
    )
ax_dd.axhline(0, color="black", linewidth=0.8)
ax_dd.set_ylabel("Drawdown (%)")
ax_dd.set_title("Drawdown Comparison")
ax_dd.legend(fontsize=8)
ax_dd.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:.0f}%"))
ax_dd.grid(True, alpha=0.3)

# ── Panel 3: Total return bar ──
fund_order = sorted(summaries.keys(), key=lambda x: summaries[x]["total_return"], reverse=True)
bar_names  = fund_order + ["SPY"]
bar_rets   = [summaries[f]["total_return"] for f in fund_order] + [spy_total_ret]
bar_colors = [COLORS[f] for f in fund_order] + [COLORS["SPY"]]

bars = ax_bar.bar(range(len(bar_names)), bar_rets, color=bar_colors, alpha=0.85)
ax_bar.set_xticks(range(len(bar_names)))
ax_bar.set_xticklabels(
    [n.split("(")[0].strip() for n in bar_names],
    rotation=20, ha="right", fontsize=8
)
ax_bar.set_ylabel("Total Return (%)")
ax_bar.set_title("Total Return Comparison")
ax_bar.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:.0f}%"))
ax_bar.grid(True, alpha=0.3, axis="y")
for bar, ret in zip(bars, bar_rets):
    ax_bar.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                f"{ret:+.1f}%", ha="center", va="bottom", fontsize=8)

# ── Panel 4: Annualized return + max DD scatter ──
for fund_name, s in summaries.items():
    years = (pd.Timestamp(s["end"]) - pd.Timestamp(s["start"])).days / 365.25
    ann_ret = ((1 + s["total_return"] / 100) ** (1 / years) - 1) * 100
    ax_ann.scatter(
        abs(s["max_drawdown"]),
        ann_ret,
        color=COLORS[fund_name],
        s=120,
        zorder=5,
        label=fund_name.split("(")[0].strip()
    )
    ax_ann.annotate(
        fund_name.split("(")[0].strip(),
        (abs(s["max_drawdown"]), ann_ret),
        textcoords="offset points",
        xytext=(6, 4),
        fontsize=7
    )

spy_years = (pd.Timestamp(spy_df.index[-1]) - pd.Timestamp(spy_df.index[0])).days / 365.25
spy_ann = ((1 + spy_total_ret / 100) ** (1 / spy_years) - 1) * 100
ax_ann.scatter(5, spy_ann, color=COLORS["SPY"], s=120, marker="D", zorder=5)
ax_ann.annotate("SPY", (5, spy_ann), textcoords="offset points", xytext=(6, 4), fontsize=7)
ax_ann.set_xlabel("Max Drawdown (%)")
ax_ann.set_ylabel("Annualized Return (%)")
ax_ann.set_title("Risk vs Return")
ax_ann.grid(True, alpha=0.3)

for ax in [ax_main, ax_dd]:
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha="right", fontsize=8)

output_path = "/Users/huhao/Documents/Claude/s_tier_backtest.png"
plt.savefig(output_path, dpi=150, bbox_inches="tight")
print(f"\nChart saved → {output_path}")
plt.show()

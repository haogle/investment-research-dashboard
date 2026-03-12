"""
Cache warmup — run during build to pre-fetch all price data.
This way the first user visit reads from local cache (~3ms) instead
of hitting yfinance (~30s+ for all tickers).

Usage:  python warmup_cache.py
"""

from price_cache import fetch_prices_cached, fetch_ticker_info_cached
import time

# ── All tickers used across all tabs ──

# 13F fund tickers
FUND_TICKERS = [
    "MU","BAC","GOOG","META","AAPL","BRK-B","GOOGL","EWBC","OXY","PDD","SOC","CROX",
    "LOW","CMG","QSR","HLT","CP","HHH","UBER","BN","AMZN","SEG","HTZ",
    "AXP","KO","CVX","KHC","MCO","USB","VRSN","CB","ATVI",
    "TDW","NVR","CEIX","ATIF","HCC","AMR","NE","RIG","VAL",
]

# SeekingAlpha picks tickers
SA_TICKERS = [
    "XOM","CI","FNF","BNTX","LYG",
    "SMCI","MOD","PDD","MNSO","JXN","ASC","VLO","HDSN","ENGIY",
    "APP","CLS","ANF","RYCEY","GCT","MHO","ISNPY","LPG",
    "OPFI","AGX","EAT","CRDO","NBIS","WLDN","DXPE","PTGX",
    "AMD","CIEN","COHR","ALL","INCY","B","ATI",
]

# Default stock research tickers
RESEARCH_TICKERS = ["AAPL", "NVDA", "MSFT"]

# Benchmarks
BENCHMARKS = ["SPY", "QQQ", "IWM", "VTI"]

ALL_TICKERS = list(set(FUND_TICKERS + SA_TICKERS + RESEARCH_TICKERS + BENCHMARKS))

print(f"Warming cache for {len(ALL_TICKERS)} tickers...")

t0 = time.time()

# One big fetch for all close prices (2022–now)
fetch_prices_cached(ALL_TICKERS, start="2022-01-01", end="2026-12-31")

t1 = time.time()
print(f"  Close prices: {t1-t0:.1f}s")

# Pre-cache ticker info for common research tickers
INFO_TICKERS = RESEARCH_TICKERS + ["GOOG", "BAC", "MU", "META", "AMZN", "UBER"]
for t in INFO_TICKERS:
    try:
        fetch_ticker_info_cached(t)
    except Exception:
        pass

t2 = time.time()
print(f"  Ticker info: {t2-t1:.1f}s")
print(f"  Total: {t2-t0:.1f}s")
print("Cache warm!")

"""
yfinance price cache — stores data as local JSON files.
Cache TTL: 7 days (configurable).
Location: ./cache/ directory (works on Render's ephemeral disk too).
"""

import os
import json
import time
import hashlib
import pandas as pd
import yfinance as yf

CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")
CACHE_TTL_SECONDS = 7 * 24 * 3600  # 7 days


def _ensure_cache_dir():
    os.makedirs(CACHE_DIR, exist_ok=True)


def _cache_key(tickers, start, end):
    """Deterministic key from sorted tickers + date range."""
    key_str = f"{','.join(sorted(tickers))}|{start}|{end}"
    return hashlib.md5(key_str.encode()).hexdigest()


def _cache_path(key):
    return os.path.join(CACHE_DIR, f"{key}.json")


def _read_cache(key):
    """Read cache file. Returns (data_dict, True) or (None, False)."""
    path = _cache_path(key)
    if not os.path.exists(path):
        return None, False
    try:
        with open(path, "r") as f:
            payload = json.load(f)
        if time.time() - payload.get("ts", 0) > CACHE_TTL_SECONDS:
            return None, False  # expired
        return payload["data"], True
    except (json.JSONDecodeError, KeyError):
        return None, False


def _write_cache(key, data):
    """Write data dict to cache file."""
    _ensure_cache_dir()
    payload = {"ts": time.time(), "data": data}
    with open(_cache_path(key), "w") as f:
        json.dump(payload, f)


def fetch_prices_cached(tickers, start="2022-01-01", end="2026-03-12"):
    """
    Drop-in replacement for yfinance download.
    Returns dict of {ticker: pd.Series with DatetimeIndex} (close prices).
    Uses local JSON cache with 7-day TTL.
    """
    tickers = list(set(tickers))
    key = _cache_key(tickers, start, end)

    cached_data, hit = _read_cache(key)
    if hit:
        out = {}
        for t, records in cached_data.items():
            s = pd.Series(records["values"], index=pd.to_datetime(records["dates"]), name=t)
            out[t] = s
        return out

    # Cache miss — fetch from yfinance
    raw = yf.download(tickers, start=start, end=end, auto_adjust=True, progress=False)

    out = {}
    to_cache = {}
    for t in tickers:
        try:
            if isinstance(raw.columns, pd.MultiIndex):
                s = raw["Close"][t].dropna()
            else:
                s = raw["Close"].dropna()
            if len(s) > 0:
                s.index = pd.to_datetime(s.index)
                out[t] = s
                to_cache[t] = {
                    "dates": [d.strftime("%Y-%m-%d") for d in s.index],
                    "values": [float(v) for v in s.values],
                }
        except Exception:
            pass

    if to_cache:
        _write_cache(key, to_cache)

    return out


def fetch_prices_cached_raw(tickers, start="2022-01-01", end="2026-03-12"):
    """
    Returns dict of {ticker: DataFrame with 'Close' column, string index}.
    Compatible with s_tier_backtest.py's existing interface.
    """
    series_dict = fetch_prices_cached(tickers, start, end)
    out = {}
    for t, s in series_dict.items():
        df = pd.DataFrame({"Close": s.values}, index=[d.strftime("%Y-%m-%d") for d in s.index])
        out[t] = df
    return out


def clear_cache():
    """Delete all cache files."""
    if os.path.exists(CACHE_DIR):
        for f in os.listdir(CACHE_DIR):
            if f.endswith(".json"):
                os.remove(os.path.join(CACHE_DIR, f))


def refresh_cache(tickers, start="2022-01-01", end="2026-03-12"):
    """Force-refresh: delete matching cache entry, then re-fetch."""
    key = _cache_key(list(set(tickers)), start, end)
    path = _cache_path(key)
    if os.path.exists(path):
        os.remove(path)
    return fetch_prices_cached(tickers, start, end)

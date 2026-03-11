"""
Investment Research Dashboard
Run: streamlit run dashboard.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime
from price_cache import fetch_prices_cached, refresh_cache, fetch_ohlc_cached, fetch_ticker_info_cached
import warnings
warnings.filterwarnings("ignore")

st.set_page_config(page_title="Investment Research Dashboard",
                   page_icon="📊", layout="wide")

st.title("📊 Investment Research Dashboard")

with st.sidebar:
    st.header("⚙️ Settings")
    starting_capital = st.number_input("Starting Capital ($)", value=100_000, step=10_000, min_value=1000)
    benchmark = st.selectbox("Benchmark", ["SPY","QQQ","IWM","VTI"], index=0)
    st.markdown("---")
    if st.button("🔄 Refresh Price Cache"):
        from price_cache import clear_cache
        clear_cache()
        st.cache_data.clear()
        st.success("Cache cleared! Prices will re-fetch on next load.")
    st.caption("Data cached locally (7-day TTL)")
    st.caption("Data: Yahoo Finance | For research only")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🏔️ 13F Fund Tracker",
    "🎯 SeekingAlpha Picks",
    "🔍 Stock Research",
    "🧪 Custom Backtest",
    "📁 Upload Data",
])

# ─────────────────────────────────────────────────────────────
# SHARED UTILITY
# ─────────────────────────────────────────────────────────────
def hex_to_rgba(hex_color, alpha=0.15):
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)
    return f"rgba({r},{g},{b},{alpha})"

def normalize_weights(snap):
    total = sum(snap.values())
    return {k: v/total for k,v in snap.items()}

def fetch_prices(tickers, start="2022-01-01", end="2026-03-12"):
    """Fetch prices with local JSON cache (7-day TTL)."""
    return fetch_prices_cached(tickers, start=start, end=end)

def get_px(ticker, date, prices):
    """Get price on or before date. date can be str or Timestamp."""
    if ticker not in prices:
        return None
    s = prices[ticker]
    d = pd.Timestamp(date)
    sub = s[s.index <= d]
    return float(sub.iloc[-1]) if len(sub) > 0 else None


# ═════════════════════════════════════════════════════════════
# TAB 1 — 13F FUND TRACKER
# ═════════════════════════════════════════════════════════════
with tab1:
    st.header("13F Copy-Trade Simulator")
    st.caption("Rebalances to each fund's 13F weights on the filing release date (~45 days after quarter end).")

    FUND_DATA = {
        "Himalaya Capital (Li Lu)": {
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
        },
        "Pershing Square (Ackman)": {
            "2022-05-16": {"LOW":0.2600,"CMG":0.1900,"QSR":0.1600,"HLT":0.1500,"CP":0.1100,"GOOG":0.0400,"HHH":0.0500,"AAPL":0.0400},
            "2022-08-15": {"LOW":0.2700,"CMG":0.2000,"QSR":0.1800,"HLT":0.1400,"CP":0.1100,"GOOG":0.0600,"HHH":0.0400},
            "2022-11-14": {"LOW":0.2400,"CMG":0.1900,"QSR":0.1700,"HLT":0.1300,"CP":0.1000,"GOOG":0.0900,"GOOGL":0.0400,"HHH":0.0400},
            "2023-02-14": {"LOW":0.2300,"CMG":0.2000,"QSR":0.1700,"HLT":0.1200,"CP":0.1100,"GOOG":0.1000,"GOOGL":0.0500,"HHH":0.0200},
            "2023-05-15": {"CMG":0.2500,"QSR":0.2000,"HLT":0.1500,"GOOG":0.1500,"GOOGL":0.1000,"CP":0.1100,"HHH":0.0400},
            "2023-08-14": {"CMG":0.2400,"QSR":0.1900,"HLT":0.1400,"GOOG":0.1600,"GOOGL":0.1100,"CP":0.1200,"HHH":0.0400},
            "2023-11-14": {"CMG":0.2200,"QSR":0.1800,"GOOG":0.1500,"GOOGL":0.1300,"HLT":0.1200,"CP":0.1100,"UBER":0.0500,"HHH":0.0400},
            "2024-02-14": {"CMG":0.2000,"QSR":0.1700,"GOOG":0.1500,"GOOGL":0.1300,"HLT":0.1200,"CP":0.1148,"UBER":0.0800,"HHH":0.0352},
            "2024-05-15": {"QSR":0.1800,"GOOG":0.1700,"GOOGL":0.1400,"HLT":0.1300,"UBER":0.1500,"BN":0.1400,"CP":0.0900,"HHH":0.0200},
            "2024-08-14": {"BN":0.1900,"UBER":0.1800,"QSR":0.1600,"GOOG":0.1500,"GOOGL":0.1200,"HLT":0.1100,"CP":0.0900,"HHH":0.0500},
            "2024-11-14": {"UBER":0.2030,"BN":0.1920,"HHH":0.1060,"GOOG":0.1050,"QSR":0.1000,"AMZN":0.0870,"GOOGL":0.0800,"HLT":0.0540,"CP":0.0580,"SEG":0.0080,"HTZ":0.0070},
            "2025-02-14": {"UBER":0.2100,"BN":0.2000,"GOOG":0.1300,"GOOGL":0.1200,"QSR":0.1100,"AMZN":0.1000,"HLT":0.0700,"HHH":0.0800,"SEG":0.0080,"HTZ":0.0070},
            "2025-05-15": {"UBER":0.2000,"BN":0.1900,"AMZN":0.1400,"GOOG":0.1300,"GOOGL":0.1000,"QSR":0.1000,"HLT":0.0600,"HHH":0.0800},
            "2025-08-14": {"UBER":0.2030,"BN":0.1920,"GOOG":0.1050,"QSR":0.1000,"AMZN":0.0870,"GOOGL":0.0800,"HHH":0.1060,"HLT":0.0540,"SEG":0.0080,"HTZ":0.0070,"CMG":0.0580},
            "2025-11-14": {"UBER":0.2030,"BN":0.1920,"HHH":0.1060,"GOOG":0.1050,"QSR":0.1000,"AMZN":0.0870,"GOOGL":0.0800,"HLT":0.0540,"SEG":0.0080,"HTZ":0.0070},
            "2026-02-17": {"BN":0.1815,"UBER":0.1590,"AMZN":0.1428,"GOOG":0.1246,"META":0.1137,"QSR":0.1005,"HHH":0.0969,"HLT":0.0560,"GOOGL":0.0137,"SEG":0.0064,"HTZ":0.0050},
        },
        "Berkshire Hathaway (Buffett)": {
            "2022-05-16": {"AAPL":0.3800,"BAC":0.1400,"AXP":0.0800,"KO":0.0750,"CVX":0.0900,"OXY":0.0400,"KHC":0.0350,"MCO":0.0300,"USB":0.0200,"VRSN":0.0100},
            "2022-08-15": {"AAPL":0.3800,"BAC":0.1400,"AXP":0.0800,"KO":0.0750,"CVX":0.0900,"OXY":0.0500,"KHC":0.0350,"MCO":0.0300},
            "2022-11-14": {"AAPL":0.3900,"BAC":0.1300,"AXP":0.0800,"KO":0.0760,"CVX":0.0900,"OXY":0.0600,"KHC":0.0330,"MCO":0.0300},
            "2023-02-14": {"AAPL":0.3800,"BAC":0.1300,"AXP":0.0790,"KO":0.0760,"CVX":0.0900,"OXY":0.0430,"KHC":0.0330,"MCO":0.0300},
            "2023-05-15": {"AAPL":0.4644,"BAC":0.0909,"AXP":0.0769,"KO":0.0763,"CVX":0.0665,"OXY":0.0400,"KHC":0.0280,"MCO":0.0260},
            "2023-08-14": {"AAPL":0.4800,"BAC":0.0900,"AXP":0.0750,"KO":0.0750,"CVX":0.0600,"OXY":0.0400,"KHC":0.0280,"MCO":0.0270},
            "2023-11-14": {"AAPL":0.4800,"BAC":0.0900,"AXP":0.0780,"KO":0.0720,"CVX":0.0570,"OXY":0.0450,"KHC":0.0280,"MCO":0.0280,"CB":0.0120},
            "2024-02-14": {"AAPL":0.4954,"BAC":0.0988,"AXP":0.0807,"KO":0.0670,"CVX":0.0534,"OXY":0.0450,"MCO":0.0320,"KHC":0.0280,"CB":0.0200},
            "2024-05-15": {"AAPL":0.4100,"BAC":0.1000,"AXP":0.0820,"KO":0.0680,"CVX":0.0540,"OXY":0.0500,"CB":0.0600,"MCO":0.0330,"KHC":0.0280},
            "2024-08-14": {"AAPL":0.3000,"BAC":0.1000,"AXP":0.0820,"KO":0.0700,"CVX":0.0550,"OXY":0.0510,"CB":0.0600,"MCO":0.0340,"KHC":0.0280},
            "2024-11-14": {"AAPL":0.2600,"AXP":0.1500,"KO":0.1100,"BAC":0.1000,"CVX":0.0800,"OXY":0.0600,"CB":0.0500,"MCO":0.0380,"KHC":0.0280,"GOOGL":0.0240},
            "2025-02-14": {"AAPL":0.2500,"AXP":0.1700,"KO":0.1100,"BAC":0.1000,"CVX":0.0800,"OXY":0.0600,"CB":0.0500,"MCO":0.0380,"GOOGL":0.0240,"KHC":0.0280},
            "2025-05-15": {"AAPL":0.2400,"AXP":0.1800,"KO":0.1100,"BAC":0.0900,"CVX":0.0800,"OXY":0.0600,"CB":0.0500,"MCO":0.0380,"GOOGL":0.0240,"KHC":0.0280},
            "2025-08-14": {"AAPL":0.2300,"AXP":0.1900,"KO":0.1150,"BAC":0.0950,"CVX":0.0800,"OXY":0.0580,"CB":0.0500,"MCO":0.0380,"GOOGL":0.0240,"KHC":0.0200},
            "2025-11-14": {"AAPL":0.2300,"AXP":0.2046,"KO":0.1020,"BAC":0.1038,"CVX":0.0724,"OXY":0.0525,"MCO":0.0416,"CB":0.0416,"KHC":0.0288,"GOOGL":0.0204},
            "2026-02-17": {"AAPL":0.2218,"AXP":0.1715,"KO":0.1163,"BAC":0.0937,"CVX":0.0905,"OXY":0.0525,"MCO":0.0416,"CB":0.0416,"KHC":0.0288,"GOOGL":0.0204},
        },
        "Pabrai Funds (Pabrai)": {
            "2022-05-16": {"TDW":0.4000,"NVR":0.2500,"CEIX":0.2000,"ATIF":0.1500},
            "2022-08-15": {"TDW":0.4500,"CEIX":0.2500,"NVR":0.2000,"ATIF":0.1000},
            "2022-11-14": {"TDW":0.4500,"CEIX":0.3000,"NVR":0.1500,"ATIF":0.1000},
            "2023-02-14": {"TDW":0.3500,"CEIX":0.3000,"HCC":0.1500,"NVR":0.1000,"AMR":0.0500},
            "2023-05-15": {"TDW":0.2800,"CEIX":0.2500,"HCC":0.2000,"AMR":0.1500,"NVR":0.1200},
            "2023-08-14": {"HCC":0.3500,"AMR":0.3000,"TDW":0.1500,"NE":0.1000,"NVR":0.1000},
            "2023-11-14": {"HCC":0.3500,"AMR":0.3000,"TDW":0.1200,"NE":0.1200,"NVR":0.1100},
            "2024-02-14": {"HCC":0.4000,"AMR":0.3000,"TDW":0.1000,"NE":0.1200,"NVR":0.0800},
            "2024-05-15": {"HCC":0.3200,"AMR":0.3100,"RIG":0.1500,"NE":0.1200,"TDW":0.1000},
            "2024-08-14": {"HCC":0.3500,"AMR":0.3000,"RIG":0.1500,"NE":0.1000,"VAL":0.1000},
            "2024-11-14": {"HCC":0.3800,"AMR":0.2800,"RIG":0.1600,"NE":0.1100,"VAL":0.0700},
            "2025-02-14": {"HCC":0.4000,"AMR":0.3000,"RIG":0.2000,"VAL":0.1000},
            "2025-05-15": {"HCC":0.4000,"AMR":0.3000,"RIG":0.2000,"VAL":0.1000},
            "2025-08-14": {"HCC":0.4000,"AMR":0.2900,"RIG":0.2100,"VAL":0.1000},
            "2025-11-13": {"HCC":0.3500,"AMR":0.2800,"RIG":0.2100,"VAL":0.1000,"NE":0.0600},
            "2026-02-13": {"HCC":0.3947,"RIG":0.2778,"AMR":0.2700,"VAL":0.0576},
        },
    }

    col1, col2 = st.columns([1, 2])
    with col1:
        selected_funds = st.multiselect("Select Funds",list(FUND_DATA.keys()),
            default=["Himalaya Capital (Li Lu)","Pershing Square (Ackman)"])
        start_year = st.selectbox("Start Year", [2022,2023,2024], index=0)

    if not selected_funds:
        st.info("Select at least one fund.")
    else:
        @st.cache_data(show_spinner="Fetching prices…")
        def fetch_13f_prices():
            tickers = {benchmark}
            for snaps in FUND_DATA.values():
                for s in snaps.values():
                    tickers.update(s.keys())
            return fetch_prices(list(tickers))

        prices_13f = fetch_13f_prices()

        def run_backtest(snapshots, capital, start_yr):
            # Only use filings from start_year onward
            filing_dates = sorted(
                [pd.Timestamp(d) for d in snapshots if int(d[:4]) >= start_yr]
            )
            snaps_ts = {pd.Timestamp(d): normalize_weights(s)
                        for d, s in snapshots.items() if pd.Timestamp(d) in filing_dates}

            bench_s = prices_13f.get(benchmark)
            if bench_s is None or len(filing_dates) == 0:
                return pd.DataFrame()

            # trading day index (Timestamps)
            idx = bench_s.index[bench_s.index >= filing_dates[0]]

            cur_holdings = {}   # {ticker: shares}
            port_val = capital
            last_filed = None
            history = []

            for date in idx:
                # Check if a new filing is available
                due = [fd for fd in filing_dates if fd <= date and fd != last_filed]
                if due:
                    fd = due[-1]
                    if fd != last_filed:
                        pv = sum(sh * (get_px(t, date, prices_13f) or 0)
                                 for t, sh in cur_holdings.items()) or port_val
                        cur_holdings = {}
                        for t, w in snaps_ts[fd].items():
                            p = get_px(t, date, prices_13f)
                            if p:
                                cur_holdings[t] = (pv * w) / p
                        last_filed = fd

                val = sum(sh * (get_px(t, date, prices_13f) or 0)
                          for t, sh in cur_holdings.items())
                history.append({"date": date, "value": val if val > 0 else port_val})

            return pd.DataFrame(history).set_index("date")

        # Build chart
        COLORS = ["#2196F3","#4CAF50","#FF9800","#9C27B0"]
        fig = make_subplots(rows=2, cols=2,
            subplot_titles=["Portfolio Value","Drawdown","Total Return %",""],
            specs=[[{"colspan":2},None],[{},{}]])

        bench_series = prices_13f[benchmark]
        bench_start  = bench_series[bench_series.index >= pd.Timestamp(f"{start_year}-01-01")]
        spy_norm     = (bench_series / float(bench_start.iloc[0])) * starting_capital

        summary_rows = []

        for i, fname in enumerate(selected_funds):
            color = COLORS[i % len(COLORS)]
            port_df = run_backtest(FUND_DATA[fname], starting_capital, start_year)
            if port_df.empty:
                continue

            total_ret  = (port_df["value"].iloc[-1] / starting_capital - 1) * 100
            bench_ret  = (float(bench_series.iloc[-1]) / float(bench_start.iloc[0]) - 1) * 100
            rm         = port_df["value"].cummax()
            dd         = (port_df["value"] - rm) / rm * 100
            max_dd     = float(dd.min())

            # Align SPY to port index
            spy_aligned = spy_norm.reindex(port_df.index, method="ffill")

            label = fname.split("(")[0].strip()
            fig.add_trace(go.Scatter(x=port_df.index, y=port_df["value"],
                name=label, line=dict(color=color, width=2)), row=1, col=1)
            fig.add_trace(go.Scatter(x=port_df.index, y=dd,
                name=label, showlegend=False,
                line=dict(color=color, width=1.5),
                fill="tozeroy", fillcolor=hex_to_rgba(color)), row=2, col=1)

            summary_rows.append({
                "Fund": label,
                "Final $": f"${port_df['value'].iloc[-1]:,.0f}",
                "Return": f"{total_ret:+.1f}%",
                "vs SPY": f"{total_ret - bench_ret:+.1f}%",
                "Max DD": f"{max_dd:.1f}%",
                "_ret": total_ret,
                "_color": color,
            })

        # SPY on portfolio chart
        fig.add_trace(go.Scatter(x=spy_aligned.index, y=spy_aligned.values,
            name=benchmark, line=dict(color="#888888", width=2, dash="dash")), row=1, col=1)

        # Return bar
        bench_ret_val = (float(bench_series.iloc[-1]) / float(bench_start.iloc[0]) - 1) * 100
        for row in summary_rows:
            fig.add_trace(go.Bar(x=[row["Fund"]], y=[row["_ret"]],
                showlegend=False, marker_color=row["_color"]), row=2, col=2)
        fig.add_trace(go.Bar(x=[benchmark], y=[bench_ret_val],
            showlegend=False, marker_color="#888888"), row=2, col=2)

        fig.update_layout(height=620, template="plotly_dark",
            legend=dict(orientation="h", yanchor="bottom", y=1.02))
        fig.update_yaxes(tickprefix="$", row=1, col=1)
        fig.update_yaxes(ticksuffix="%", row=2, col=1)
        fig.update_yaxes(ticksuffix="%", row=2, col=2)
        st.plotly_chart(fig, use_container_width=True)

        disp = [{k:v for k,v in r.items() if not k.startswith("_")} for r in summary_rows]
        st.dataframe(pd.DataFrame(disp), use_container_width=True, hide_index=True)

        # Current holdings
        st.subheader("Latest 13F Holdings")
        hcols = st.columns(len(selected_funds))
        for i, fname in enumerate(selected_funds):
            latest = max(FUND_DATA[fname].keys())
            norm   = normalize_weights(FUND_DATA[fname][latest])
            df_h   = pd.DataFrame([{"Ticker":t,"Weight":f"{w*100:.1f}%"}
                                    for t,w in sorted(norm.items(),key=lambda x:-x[1])])
            with hcols[i]:
                st.markdown(f"**{fname.split('(')[0].strip()}** `{latest}`")
                st.dataframe(df_h, use_container_width=True, hide_index=True)


# ═════════════════════════════════════════════════════════════
# TAB 2 — SEEKINGALPHA PICKS
# ═════════════════════════════════════════════════════════════
with tab2:
    st.header("SeekingAlpha Top-10 Picks Backtest")
    st.caption("Equal-weight, buy first trading day of year, sell last trading day.")

    SA_PICKS = {
        2022: ["XOM","CI","FNF","BAC","BNTX","LYG"],
        2023: ["SMCI","MOD","PDD","MNSO","JXN","ASC","VLO","HDSN","ENGIY"],
        2024: ["APP","CLS","ANF","RYCEY","MOD","META","GCT","MHO","ISNPY","LPG"],
        2025: ["CLS","OPFI","AGX","EAT","GCT","CRDO","NBIS","WLDN","DXPE","PTGX"],
        2026: ["CLS","MU","AMD","CIEN","COHR","ALL","INCY","B","WLDN","ATI"],
    }
    YEAR_ENDS = {2022:"2022-12-30",2023:"2023-12-29",2024:"2024-12-31",
                 2025:"2025-12-31",2026:"2026-03-11"}

    sel_years = st.multiselect("Select Years", list(SA_PICKS.keys()), default=list(SA_PICKS.keys()))

    @st.cache_data(show_spinner="Fetching SA prices…")
    def fetch_sa():
        tickers = {benchmark}
        for picks in SA_PICKS.values():
            tickers.update(picks)
        return fetch_prices(list(tickers))

    sa_px = fetch_sa()

    annual = {}
    for yr in sel_years:
        bench_s = sa_px.get(benchmark, pd.Series())
        start_ts = pd.Timestamp(f"{yr}-01-01")
        end_ts   = pd.Timestamp(YEAR_ENDS[yr])
        buy_candidates  = bench_s[bench_s.index >= start_ts]
        sell_candidates = bench_s[bench_s.index <= end_ts]
        if buy_candidates.empty or sell_candidates.empty:
            continue
        buy_d  = buy_candidates.index[0]
        sell_d = sell_candidates.index[-1]

        rets = {}
        for t in SA_PICKS[yr]:
            p0 = get_px(t, buy_d, sa_px)
            p1 = get_px(t, sell_d, sa_px)
            if p0 and p1:
                rets[t] = p1/p0 - 1

        sp0 = get_px(benchmark, buy_d, sa_px)
        sp1 = get_px(benchmark, sell_d, sa_px)
        annual[yr] = {"returns": rets, "spy": sp1/sp0-1 if sp0 and sp1 else 0,
                      "buy": buy_d, "sell": sell_d}

    if annual:
        mcols = st.columns(len(annual))
        for i,(yr,data) in enumerate(annual.items()):
            pr = np.mean(list(data["returns"].values())) if data["returns"] else 0
            with mcols[i]:
                st.metric(f"{yr}{' YTD' if yr==2026 else ''}",
                          f"{pr:+.1%}", delta=f"α {pr-data['spy']:+.1%}")

        # Heatmap
        all_t = sorted({t for d in annual.values() for t in d["returns"]})
        heat_df = pd.DataFrame(
            {str(yr): {t: annual[yr]["returns"].get(t, np.nan)*100 for t in all_t}
             for yr in annual}
        )
        fig_h = px.imshow(heat_df.T, text_auto=".0f", color_continuous_scale="RdYlGn",
                           zmin=-80, zmax=300, title="Return Heatmap (%)", aspect="auto")
        fig_h.update_layout(template="plotly_dark", height=450)
        st.plotly_chart(fig_h, use_container_width=True)

        # Annual bar
        yrs   = list(annual.keys())
        prets = [np.mean(list(annual[y]["returns"].values()))*100 for y in yrs]
        srets = [annual[y]["spy"]*100 for y in yrs]
        fig_b = go.Figure()
        fig_b.add_trace(go.Bar(x=[str(y) for y in yrs], y=prets, name="SA Portfolio",
                               marker_color="#2196F3"))
        fig_b.add_trace(go.Bar(x=[str(y) for y in yrs], y=srets, name=benchmark,
                               marker_color="#888888"))
        fig_b.update_layout(barmode="group", template="plotly_dark", height=350,
                            yaxis_ticksuffix="%", title="Annual Return vs SPY")
        st.plotly_chart(fig_b, use_container_width=True)

        # Cumulative
        cum_p = cum_s = starting_capital
        for yr, data in annual.items():
            pr = np.mean(list(data["returns"].values())) if data["returns"] else 0
            cum_p *= (1+pr); cum_s *= (1+data["spy"])
        c1,c2,c3 = st.columns(3)
        c1.metric("Portfolio (cumulative)", f"${cum_p:,.0f}", f"{(cum_p/starting_capital-1)*100:+.1f}%")
        c2.metric(f"{benchmark} (cumulative)", f"${cum_s:,.0f}", f"{(cum_s/starting_capital-1)*100:+.1f}%")
        c3.metric("Cumulative Alpha", f"{(cum_p/starting_capital - cum_s/starting_capital)*100:+.1f}%")

        for yr, data in annual.items():
            with st.expander(f"📋 {yr} detail"):
                rows = [{"Ticker":t, "Return":f"{r:+.1%}",
                         "P&L ($)":f"${(starting_capital/max(len(data['returns']),1))*r:+,.0f}",
                         "✓/✗":"✅" if r>0 else "❌"}
                        for t,r in sorted(data["returns"].items(),key=lambda x:-x[1])]
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


# ═════════════════════════════════════════════════════════════
# TAB 3 — STOCK RESEARCH
# ═════════════════════════════════════════════════════════════
with tab3:
    st.header("Stock Research")
    c1,c2,c3 = st.columns([2,1,1])
    with c1:
        ticker_in = st.text_input("Tickers (comma-separated)", value="AAPL, NVDA, MSFT")
    with c2:
        period = st.selectbox("Period", ["6mo","1y","2y","3y","5y"], index=1)
    with c3:
        chart_type = st.selectbox("Chart Type", ["Line","Area","Candlestick"], index=0)

    t_list = [t.strip().upper() for t in ticker_in.split(",") if t.strip()]

    if t_list:
        @st.cache_data(show_spinner="Loading…", ttl=300)
        def fetch_research(tickers, per):
            # period-based lookups: convert to start/end dates for cache
            from datetime import timedelta
            period_map = {"6mo": 180, "1y": 365, "2y": 730, "3y": 1095, "5y": 1825}
            days = period_map.get(per, 365)
            end_dt = datetime.today()
            start_dt = end_dt - timedelta(days=days)
            return fetch_prices(tickers, start=start_dt.strftime("%Y-%m-%d"),
                                end=end_dt.strftime("%Y-%m-%d"))

        res_px = fetch_research(t_list, period)
        fig_p  = go.Figure()
        for t, s in res_px.items():
            if chart_type == "Line":
                fig_p.add_trace(go.Scatter(x=s.index, y=s, name=t))
            elif chart_type == "Area":
                fig_p.add_trace(go.Scatter(x=s.index, y=s, name=t, fill="tozeroy"))
            elif chart_type == "Candlestick" and len(t_list)==1:
                from datetime import timedelta
                period_map = {"6mo": 180, "1y": 365, "2y": 730, "3y": 1095, "5y": 1825}
                days = period_map.get(period, 365)
                end_dt = datetime.today()
                start_dt = end_dt - timedelta(days=days)
                raw2 = fetch_ohlc_cached(t_list[0], start_dt.strftime("%Y-%m-%d"),
                                         end_dt.strftime("%Y-%m-%d"))
                if not raw2.empty:
                    fig_p.add_trace(go.Candlestick(x=raw2.index,open=raw2["Open"],
                        high=raw2["High"],low=raw2["Low"],close=raw2["Close"],name=t))
        fig_p.update_layout(template="plotly_dark", height=420,
                            title=f"Price — {', '.join(t_list)}", yaxis_tickprefix="$")
        st.plotly_chart(fig_p, use_container_width=True)

        if len(t_list) > 1:
            fig_n = go.Figure()
            for t, s in res_px.items():
                norm = (s / s.iloc[0] - 1) * 100
                fig_n.add_trace(go.Scatter(x=norm.index, y=norm, name=t))
            fig_n.update_layout(template="plotly_dark", height=300,
                                title="Normalized Return (%)", yaxis_ticksuffix="%")
            st.plotly_chart(fig_n, use_container_width=True)

        st.subheader("Key Stats")
        scols = st.columns(len(t_list))
        for i, t in enumerate(t_list):
            with scols[i]:
                try:
                    info = fetch_ticker_info_cached(t)
                    st.markdown(f"**{t} — {info.get('shortName','')[:25]}**")
                    for k,v in {
                        "Price": f"${info.get('currentPrice', info.get('regularMarketPrice','N/A'))}",
                        "Market Cap": f"${info.get('marketCap',0)/1e9:.1f}B" if info.get('marketCap') else "N/A",
                        "P/E (TTM)": info.get('trailingPE','N/A'),
                        "EPS (TTM)": f"${info.get('trailingEps','N/A')}",
                        "52W High": f"${info.get('fiftyTwoWeekHigh','N/A')}",
                        "52W Low": f"${info.get('fiftyTwoWeekLow','N/A')}",
                        "Revenue": f"${info.get('totalRevenue',0)/1e9:.1f}B" if info.get('totalRevenue') else "N/A",
                        "Div Yield": f"{info.get('dividendYield',0)*100:.2f}%" if info.get('dividendYield') else "None",
                    }.items():
                        st.markdown(f"- **{k}:** {v}")
                except Exception:
                    st.warning(f"No data for {t}")


# ═════════════════════════════════════════════════════════════
# TAB 4 — CUSTOM BACKTEST
# ═════════════════════════════════════════════════════════════
with tab4:
    st.header("Custom Portfolio Backtest")
    c1, c2 = st.columns([2,1])
    with c1:
        custom_in = st.text_area("TICKER WEIGHT (one per line)",
                                 value="AAPL 25\nNVDA 25\nMSFT 20\nGOOG 15\nAMZN 15", height=180)
    with c2:
        cs = st.date_input("Start", value=datetime(2022,1,1))
        ce = st.date_input("End",   value=datetime.today())

    if st.button("▶ Run", type="primary", key="custom_run"):
        lines = [l.strip() for l in custom_in.strip().splitlines() if l.strip()]
        ct, cw = [], []
        for line in lines:
            parts = line.split()
            if len(parts) >= 2:
                ct.append(parts[0].upper())
                cw.append(float(parts[1]))
        if ct:
            tw = sum(cw); cw = [w/tw for w in cw]
            with st.spinner("Running…"):
                cpx = fetch_prices(ct + [benchmark],
                                   start=cs.strftime("%Y-%m-%d"),
                                   end=ce.strftime("%Y-%m-%d"))
                if benchmark in cpx and ct:
                    idx = cpx[benchmark].index
                    allocs = {t: (starting_capital*w)/float(cpx[t].iloc[0])
                              for t,w in zip(ct,cw) if t in cpx}
                    vals = []
                    for d in idx:
                        v = sum(sh*(get_px(t,d,cpx) or get_px(t,idx[-1],cpx) or 0)
                                for t,sh in allocs.items())
                        vals.append(v)
                    port_s  = pd.Series(vals, index=idx)
                    bench_s = (cpx[benchmark]/cpx[benchmark].iloc[0])*starting_capital

                    fig_c = go.Figure()
                    fig_c.add_trace(go.Scatter(x=port_s.index, y=port_s,
                        name="My Portfolio", line=dict(color="#2196F3",width=2.5)))
                    fig_c.add_trace(go.Scatter(x=bench_s.index, y=bench_s,
                        name=benchmark, line=dict(color="#888888",width=2,dash="dash")))
                    fig_c.update_layout(template="plotly_dark", height=400,
                                        yaxis_tickprefix="$")
                    st.plotly_chart(fig_c, use_container_width=True)

                    pr = (port_s.iloc[-1]/starting_capital-1)*100
                    br = (bench_s.iloc[-1]/starting_capital-1)*100
                    rm = port_s.cummax()
                    dd = ((port_s-rm)/rm*100).min()
                    m1,m2,m3,m4 = st.columns(4)
                    m1.metric("Portfolio", f"{pr:+.1f}%")
                    m2.metric(benchmark,   f"{br:+.1f}%")
                    m3.metric("Alpha",     f"{pr-br:+.1f}%")
                    m4.metric("Max DD",    f"{dd:.1f}%")

                    fig_pie = go.Figure(go.Pie(labels=ct, values=[w*100 for w in cw], hole=0.4))
                    fig_pie.update_layout(template="plotly_dark", height=300, title="Weights")
                    st.plotly_chart(fig_pie, use_container_width=True)


# ═════════════════════════════════════════════════════════════
# TAB 5 — UPLOAD DATA
# ═════════════════════════════════════════════════════════════
with tab5:
    st.header("Upload Excel / CSV")
    uploaded = st.file_uploader("Drop file", type=["xlsx","xls","csv"])

    if uploaded:
        try:
            if uploaded.name.endswith(".csv"):
                df_up = pd.read_csv(uploaded)
            else:
                sheets = pd.ExcelFile(uploaded).sheet_names
                sheet  = st.selectbox("Sheet", sheets)
                df_up  = pd.read_excel(uploaded, sheet_name=sheet)

            st.dataframe(df_up.head(50), use_container_width=True)

            ticker_col = next((c for c in df_up.columns
                               if c.lower() in ["ticker","symbol","stock","code","股票代码"]), None)
            if ticker_col:
                t_up = df_up[ticker_col].dropna().astype(str).tolist()
                st.success(f"Found {len(t_up)} tickers in '{ticker_col}'")

                us = st.date_input("Start", value=datetime(2023,1,1), key="up_s")
                ue = st.date_input("End",   value=datetime.today(),   key="up_e")

                if st.button("▶ Backtest", type="primary", key="up_run"):
                    with st.spinner("Running…"):
                        upx = fetch_prices(t_up + [benchmark],
                                           start=us.strftime("%Y-%m-%d"),
                                           end=ue.strftime("%Y-%m-%d"))
                        vt = [t for t in t_up if t in upx]
                        if vt:
                            idx = upx[benchmark].index
                            a2  = {t:(starting_capital/len(vt))/float(upx[t].iloc[0]) for t in vt}
                            v2  = [sum(sh*(get_px(t,d,upx) or 0) for t,sh in a2.items()) for d in idx]
                            p2  = pd.Series(v2, index=idx)
                            b2  = (upx[benchmark]/upx[benchmark].iloc[0])*starting_capital

                            fig2 = go.Figure()
                            fig2.add_trace(go.Scatter(x=p2.index,y=p2,name="Uploaded",
                                line=dict(color="#4CAF50",width=2.5)))
                            fig2.add_trace(go.Scatter(x=b2.index,y=b2,name=benchmark,
                                line=dict(color="#888888",width=2,dash="dash")))
                            fig2.update_layout(template="plotly_dark",height=380,yaxis_tickprefix="$")
                            st.plotly_chart(fig2, use_container_width=True)

                            r2 = (p2.iloc[-1]/starting_capital-1)*100
                            b2r= (b2.iloc[-1]/starting_capital-1)*100
                            c1,c2,c3 = st.columns(3)
                            c1.metric("Return",  f"{r2:+.1f}%")
                            c2.metric(benchmark, f"{b2r:+.1f}%")
                            c3.metric("Alpha",   f"{r2-b2r:+.1f}%")

                            rows = [{"Ticker":t,
                                     "Return":f"{float(upx[t].iloc[-1])/float(upx[t].iloc[0])-1:+.1%}"}
                                    for t in vt]
                            st.dataframe(pd.DataFrame(rows).sort_values("Return",ascending=False),
                                         use_container_width=True, hide_index=True)
            else:
                st.warning("No ticker column found. Columns: " + str(list(df_up.columns)))
        except Exception as e:
            st.error(f"Error: {e}")
    else:
        st.info("Upload any Excel/CSV with a Ticker column. Your seekalpha.xlsx works directly.")
        st.markdown("""
        **Supported formats:**
        - Column named `Ticker`, `Symbol`, `Stock`, or `股票代码`
        - Optional `Weight` column
        - Multi-sheet Excel (sheet selector appears automatically)
        """)

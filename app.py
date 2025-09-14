import streamlit as st
import pandas as pd
import requests
import datetime

# ---------------- NSE API (Primary) ---------------- #
def fetch_from_nse(symbol: str):
    try:
        url = f"https://www.nseindia.com/api/equity-stockIndices?index=NIFTY%2050"
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json"
        }
        session = requests.Session()
        resp = session.get(url, headers=headers, timeout=10)
        if resp.status_code != 200:
            raise Exception(f"NSE API error: {resp.status_code}")

        data = resp.json()
        stocks = data.get("data", [])
        df = pd.DataFrame(stocks)
        if df.empty:
            return None

        df["Date"] = datetime.datetime.now()
        df.set_index("Date", inplace=True)
        df.rename(columns={"lastPrice": "Close"}, inplace=True)
        df["Open"] = df["Close"]
        df["High"] = df["dayHigh"].replace(-1, df["Close"])
        df["Low"] = df["dayLow"].replace(-1, df["Close"])
        df["Volume"] = 0
        return df[["Open", "High", "Low", "Close", "Volume"]].tail(10)
    except Exception as e:
        st.warning(f"NSE fetch failed: {e}")
        return None

# ---------------- Groww API (Fallback) ---------------- #
def fetch_from_groww(symbol: str):
    try:
        url = f"https://groww.in/v1/api/charting_service/v2/chart/exchange/NSE/segment/CASH/{symbol}?interval=1d"
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code != 200:
            return None

        data = resp.json()
        candles = data.get("candles", [])
        if not candles:
            return None

        df = pd.DataFrame(candles, columns=["Date", "Open", "High", "Low", "Close", "Volume"])
        df["Date"] = pd.to_datetime(df["Date"], unit="ms")
        df.set_index("Date", inplace=True)
        return df
    except Exception as e:
        st.warning(f"Groww fetch failed: {e}")
        return None

# ---------------- Support/Resistance Logic ---------------- #
def calculate_levels(df):
    last_close = df["Close"].iloc[-1]
    support = df["Low"].min()
    resistance = df["High"].max()
    s1 = last_close - (resistance - support) * 0.5
    r1 = last_close + (resistance - support) * 0.5
    stop_loss = support if last_close > (support + resistance) / 2 else resistance
    return {
        "Last Close": last_close,
        "Support": support,
        "Resistance": resistance,
        "S1": s1,
        "R1": r1,
        "Stop Loss": stop_loss
    }

# ---------------- Streamlit App ---------------- #
st.title("Market Support & Resistance App")

# Symbol input
symbol = st.text_input("Enter Symbol (e.g. NIFTY, RELIANCE)").strip().upper()

# Quick buttons
quick_symbols = ["NIFTY", "BANKNIFTY", "FINNIFTY", "RELIANCE", "TCS"]
cols = st.columns(len(quick_symbols))
for i, sym in enumerate(quick_symbols):
    if cols[i].button(sym):
        symbol = sym

if symbol:
    # Fetch data: NSE primary, Groww fallback
    df = fetch_from_nse(symbol)
    if df is None:
        st.info("⚠️ NSE failed, trying Groww fallback...")
        df = fetch_from_groww(symbol)

    if df is None:
        st.error(f"No data available for {symbol}")
    else:
        # Calculate levels
        levels = calculate_levels(df)
        st.subheader("Support & Resistance Levels")
        for k, v in levels.items():
            st.write(f"{k}: {v:.2f}")

        # Plot chart using Streamlit's line_chart
        st.subheader(f"{symbol} Close Price Chart")
        st.line_chart(df["Close"])

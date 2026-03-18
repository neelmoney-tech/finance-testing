import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="QuantScanner Lite", layout="wide")

# --- MANUAL INDICATOR MATH (Replaces pandas_ta) ---
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

@st.cache_data(ttl=3600)
def fetch_data(tickers):
    data = {}
    progress_bar = st.sidebar.progress(0)
    for i, ticker in enumerate(tickers):
        try:
            df = yf.download(ticker, period="2y", interval="1d", progress=False)
            if not df.empty:
                # Calculate indicators manually to avoid numba/llvmlite errors
                df['SMA_20'] = df['Close'].rolling(window=20).mean()
                df['SMA_200'] = df['Close'].rolling(window=200).mean()
                df['RSI'] = calculate_rsi(df['Close'])
                data[ticker] = df
        except:
            continue
        progress_bar.progress((i + 1) / len(tickers))
    return data

# --- PATTERN DETECTION ---
def detect_vcp(df):
    if len(df) < 200 or df['Close'].iloc[-1] < df['SMA_200'].iloc[-1]:
        return None
    recent = df.tail(30).copy()
    # Volatility Check: High-Low range in 10-day chunks
    waves = [recent.iloc[0:10], recent.iloc[10:20], recent.iloc[20:30]]
    ranges = [(w['High'].max() - w['Low'].min()) / w['Low'].min() for w in waves]
    if ranges[0] > ranges[1] > ranges[2]:
        return "VCP"
    return None

def detect_rocket(df):
    if len(df) < 75: return None
    surge_zone = df.tail(75).head(60)
    if (surge_zone['High'].max() - surge_zone['Low'].min()) / surge_zone['Low'].min() > 0.8:
        base = df.tail(15)
        if (base['High'].max() - base['Low'].min()) / base['Low'].min() < 0.2:
            return "Rocket"
    return None

# --- MAIN UI ---
st.title("📈 Zero-Error Quant Scanner")
st.info("System running in Lightweight Mode (No Numba/LLVMLite dependencies).")

st.sidebar.header("Scanner Settings")
tickers_input = st.sidebar.text_area("Tickers (comma separated)", "AAPL, MSFT, TSLA, NVDA, AMD, GOOGL, AMZN, NFLX")
ticker_list = [x.strip() for x in tickers_input.split(",")]

if st.sidebar.button("Run Global Scan"):
    all_stocks = fetch_data(ticker_list)
    
    # Categorize
    rsi_signals = [t for t, df in all_stocks.items() if df['RSI'].iloc[-1] > 70 or df['RSI'].iloc[-1] < 30]
    sma_near = [t for t, df in all_stocks.items() if abs(df['Close'].iloc[-1] - df['SMA_20'].iloc[-1])/df['SMA_20'].iloc[-1] < 0.02]
    golden_cross = [t for t, df in all_stocks.items() if df['SMA_20'].iloc[-1] > df['SMA_200'].iloc[-1]]
    vcp_list = [t for t, df in all_stocks.items() if detect_vcp(df)]
    rocket_list = [t for t, df in all_stocks.items() if detect_rocket(df)]

    t1, t2, t3, t4, t5 = st.tabs(["RSI", "Near 20 SMA", "Trend (20/200)", "VCP Pattern", "Rocket Base"])

    def show_content(tab, matches, label):
        with tab:
            if not matches:
                st.write("No stocks found matching this criteria.")
            else:
                sel = st.selectbox(f"View {label} Chart", matches, key=label)
                df = all_stocks[sel]
                fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
                fig.add_trace(go.Scatter(x=df.index, y=df['SMA_20'], name="20 SMA", line=dict(color='orange')))
                fig.add_trace(go.Scatter(x=df.index, y=df['SMA_200'], name="200 SMA", line=dict(color='red')))
                fig.update_layout(template="plotly_dark", height=500)
                st.plotly_chart(fig, use_container_width=True)

    show_content(t1, rsi_signals, "RSI")
    show_content(t2, sma_near, "SMA20")
    show_content(t3, golden_cross, "Trend")
    show_content(t4, vcp_list, "VCP")
    show_content(t5, rocket_list, "Rocket")

import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- CONFIGURATION ---
st.set_page_config(page_title="QuantScanner Pro", layout="wide")

@st.cache_data(ttl=3600)
def fetch_data(tickers):
    data = {}
    progress_bar = st.sidebar.progress(0)
    for i, ticker in enumerate(tickers):
        try:
            df = yf.download(ticker, period="2y", interval="1d", progress=False)
            if not df.empty:
                # Basic Indicators
                df['RSI'] = ta.rsi(df['Close'], length=14)
                df['SMA_20'] = ta.sma(df['Close'], length=20)
                df['SMA_200'] = ta.sma(df['Close'], length=200)
                data[ticker] = df
        except Exception as e:
            pass
        progress_bar.progress((i + 1) / len(tickers))
    return data

# --- PATTERN DETECTION FUNCTIONS ---

def detect_rsi_signals(df):
    last_rsi = df['RSI'].iloc[-1]
    if last_rsi > 70: return "Overbought"
    if last_rsi < 30: return "Oversold"
    return None

def detect_sma_proximity(df):
    last_close = df['Close'].iloc[-1]
    last_sma20 = df['SMA_20'].iloc[-1]
    diff = abs(last_close - last_sma20) / last_sma20
    return "Near 20 SMA" if diff <= 0.02 else None

def detect_trend_alignment(df):
    if df['SMA_20'].iloc[-1] > df['SMA_200'].iloc[-1]:
        return "Bullish Alignment"
    return None

def detect_vcp(df):
    """
    Checks for Stage 2 uptrend and decreasing volatility (High-Low range) 
    over the last 3 chunks of 10 days.
    """
    if df['Close'].iloc[-1] < df['SMA_200'].iloc[-1]:
        return None
    
    recent = df.tail(30).copy()
    waves = [recent.iloc[0:10], recent.iloc[10:20], recent.iloc[20:30]]
    ranges = [(w['High'].max() - w['Low'].min()) / w['Low'].min() for w in waves]
    
    if ranges[0] > ranges[1] > ranges[2]:
        return "VCP Detected"
    return None

def detect_rocket_base(df):
    """
    Surge of >80% in <60 days followed by 15 days of <20% consolidation.
    """
    surge_period = df.tail(75).head(60)
    low_price = surge_period['Low'].min()
    high_price = surge_period['High'].max()
    
    if (high_price - low_price) / low_price > 0.8:
        base_period = df.tail(15)
        base_range = (base_period['High'].max() - base_period['Low'].min()) / base_period['Low'].min()
        if base_range < 0.2:
            return "Rocket Base"
    return None

# --- UI LOGIC ---

st.title("📈 QuantScanner Pro")
st.markdown("Scan markets for high-probability setups and patterns.")

# Sidebar Settings
st.sidebar.header("Scanner Settings")
index_choice = st.sidebar.selectbox("Select Index", ["S&P 500", "Nifty 50", "Custom"])

if index_choice == "S&P 500":
    tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META", "BRK-B", "V", "JNJ"] # Sample list
elif index_choice == "Nifty 50":
    tickers = ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS"] # Sample list
else:
    custom_input = st.sidebar.text_area("Enter Tickers (comma separated)", "AAPL, TSLA, BTC-USD")
    tickers = [x.strip() for x in custom_input.split(",")]

if st.sidebar.button("Run Scanner"):
    all_data = fetch_data(tickers)
    
    results = {
        "RSI": [], "SMA Proximity": [], "Trend Alignment": [], 
        "VCP Pattern": [], "Rocket Base": []
    }

    for ticker, df in all_data.items():
        if detect_rsi_signals(df): results["RSI"].append(ticker)
        if detect_sma_proximity(df): results["SMA Proximity"].append(ticker)
        if detect_trend_alignment(df): results["Trend Alignment"].append(ticker)
        if detect_vcp(df): results["VCP Pattern"].append(ticker)
        if detect_rocket_base(df): results["Rocket Base"].append(ticker)

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🔥 RSI Signals", "📏 20 SMA Proximity", "🌊 Trend Alignment", "💎 VCP Pattern", "🚀 Rocket Base"
    ])

    def render_tab_content(tab, category, data_dict):
        with tab:
            selected_ticker = st.selectbox(f"Select a {category} stock to view chart:", ["None"] + results[category], key=category)
            if selected_ticker != "None":
                df = data_dict[selected_ticker]
                fig = go.Figure(data=[go.Candlestick(
                    x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Price"
                )])
                fig.add_trace(go.Scatter(x=df.index, y=df['SMA_20'], line=dict(color='orange', width=1), name="20 SMA"))
                fig.add_trace(go.Scatter(x=df.index, y=df['SMA_200'], line=dict(color='red', width=2), name="200 SMA"))
                fig.update_layout(title=f"{selected_ticker} Technical View", height=600, template="plotly_dark")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.write(f"Stocks matching this criteria: {', '.join(results[category]) if results[category] else 'None found'}")

    render_tab_content(tab1, "RSI", all_data)
    render_tab_content(tab2, "SMA Proximity", all_data)
    render_tab_content(tab3, "Trend Alignment", all_data)
    render_tab_content(tab4, "VCP Pattern", all_data)
    render_tab_content(tab5, "Rocket Base", all_data)

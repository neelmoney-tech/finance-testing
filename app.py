import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from config import *
from utils import fetch_stock_data, fetch_crypto_data, get_market_symbols
from indicators import calculate_rsi, calculate_sma, detect_vcp, detect_rocket_base

st.set_page_config(page_title=APP_TITLE, page_icon=APP_ICON, layout="wide")

# Custom CSS for dark theme polish
st.markdown("""
    <style>
    .main { background-color: #0E1117; }
    .stMetric { background-color: #161B22; border: 1px solid #30363D; padding: 15px; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# Sidebar
st.sidebar.title("🔍 Scanner Settings")
market = st.sidebar.selectbox("Market", ["NSE (India)", "US Stocks", "Crypto"])
timeframe = st.sidebar.selectbox("Timeframe", ["1D", "1W"])
auto_refresh = st.sidebar.toggle("Auto Refresh (Every 10m)")

symbols = get_market_symbols(market)
yf_tf = "1d" if timeframe == "1D" else "1wk"

st.title(f"{APP_ICON} {APP_TITLE}")
st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# Processing Loop
results = []

with st.spinner(f"Analyzing {len(symbols)} symbols..."):
    for symbol in symbols:
        try:
            if market == "Crypto":
                df = fetch_crypto_data(symbol, timeframe.lower())
            else:
                df = fetch_stock_data(symbol, interval=yf_tf)
            
            if df is None or len(df) < 200: continue

            # Technicals
            df['RSI'] = calculate_rsi(df['Close'], RSI_PERIOD)
            df['SMA20'] = calculate_sma(df['Close'], SMA_FAST)
            df['SMA200'] = calculate_sma(df['Close'], SMA_SLOW)
            
            curr_price = df['Close'].iloc[-1]
            prev_price = df['Close'].iloc[-2]
            curr_rsi = df['RSI'].iloc[-1]
            curr_sma20 = df['SMA20'].iloc[-1]
            curr_sma200 = df['SMA200'].iloc[-1]
            
            # Strategies
            is_vcp = detect_vcp(df)
            is_rocket = detect_rocket_base(df)
            
            results.append({
                "Symbol": symbol,
                "Price": round(curr_price, 2),
                "Change %": round(((curr_price - prev_price) / prev_price) * 100, 2),
                "RSI": round(curr_rsi, 2),
                "Above SMA20": curr_price > curr_sma20,
                "Above SMA200": curr_price > curr_sma200,
                "Golden Cross": (df['SMA20'].iloc[-1] > df['SMA200'].iloc[-1]) and (df['SMA20'].iloc[-2] <= df['SMA200'].iloc[-2]),
                "VCP": is_vcp,
                "Rocket": is_rocket,
                "RawData": df
            })
        except Exception as e:
            continue

if not results:
    st.error("No data could be retrieved. Check your internet connection or API limits.")
    st.stop()

df_results = pd.DataFrame(results)

# Dashboard Layout
t1, t2, t3, t4, t5, t6 = st.tabs(["RSI", "20 SMA Trend", "MA Crossovers", "VCP Pattern", "Rocket Base", "Confluence"])

def render_mini_chart(df, symbol):
    fig = go.Figure(data=[go.Scatter(y=df['Close'].tail(30), mode='lines', line=dict(color=THEME_COLOR, width=2))])
    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=60, width=150, showlegend=False, 
                      xaxis_visible=False, yaxis_visible=False, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    return fig

def display_screen(filtered_df, strategy_name):
    if filtered_df.empty:
        st.info(f"No symbols currently matching the {strategy_name} criteria.")
        return
    
    cols = st.columns(min(len(filtered_df), 4))
    for i, (_, row) in enumerate(filtered_df.iterrows()):
        with cols[i % 4]:
            st.metric(row['Symbol'], f"{row['Price']}", f"{row['Change %']}%")
            st.plotly_chart(render_mini_chart(row['RawData'], row['Symbol']), config={'displayModeBar': False})

with t1:
    st.subheader("RSI Screener")
    c1, c2 = st.columns(2)
    with c1:
        st.write("🔥 **Overbought (>70)**")
        display_screen(df_results[df_results['RSI'] > 70], "RSI Overbought")
    with c2:
        st.write("🧊 **Oversold (<30)**")
        display_screen(df_results[df_results['RSI'] < 30], "RSI Oversold")

with t2:
    st.subheader("20 SMA Trend Following")
    display_screen(df_results[df_results['Above SMA20'] == True], "20 SMA Trend")

with t3:
    st.subheader("Moving Average Crossovers")
    st.write("**Golden Cross (20 SMA crossing above 200 SMA)**")
    display_screen(df_results[df_results['Golden Cross'] == True], "Golden Cross")

with t4:
    st.subheader("VCP Pattern (Volatility Contraction)")
    display_screen(df_results[df_results['VCP'] == True], "VCP")

with t5:
    st.subheader("Rocket Base Breakouts")
    display_screen(df_results[df_results['Rocket'] == True], "Rocket Base")

with t6:
    st.subheader("Multi-Indicator Confluence")
    st.caption("Criteria: Above 20 SMA + Above 200 SMA + RSI Bullish (>50)")
    confluence = df_results[(df_results['Above SMA20']) & (df_results['Above SMA200']) & (df_results['RSI'] > 50)]
    display_screen(confluence, "Confluence")

# Data Table
st.divider()
st.subheader("All Scanned Assets")
st.dataframe(df_results.drop(columns=['RawData']), use_container_width=True)

import yfinance as yf
import ccxt
import pandas as pd
import streamlit as st
from config import DEFAULT_INDIAN_STOCKS, DEFAULT_US_STOCKS, DEFAULT_CRYPTO

@st.cache_data(ttl=3600)
def fetch_stock_data(symbol, period="1y", interval="1d"):
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval)
        if df.empty: return None
        return df
    except Exception:
        return None

@st.cache_data(ttl=3600)
def fetch_crypto_data(symbol, timeframe='1d'):
    try:
        exchange = ccxt.binance()
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=200)
        df = pd.DataFrame(ohlcv, columns=['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
        df['Timestamp'] = pd.to_datetime(df['Timestamp'], unit='ms')
        df.set_index('Timestamp', inplace=True)
        return df
    except Exception:
        return None

def get_market_symbols(market_type):
    if market_type == "NSE (India)": return DEFAULT_INDIAN_STOCKS
    if market_type == "US Stocks": return DEFAULT_US_STOCKS
    return DEFAULT_CRYPTO

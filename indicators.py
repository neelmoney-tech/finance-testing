import pandas as pd
import numpy as np

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_sma(series, window):
    return series.rolling(window=window).mean()

def detect_vcp(df, window=20):
    """
    Volatility Contraction Pattern logic: 
    Checks if the high-low range is narrowing over 3 specific stages.
    """
    if len(df) < window: return False
    ranges = (df['High'] - df['Low']) / df['Close']
    recent_range = ranges.iloc[-5:].mean()
    prev_range = ranges.iloc[-15:-5].mean()
    return recent_range < prev_range * 0.8

def detect_rocket_base(df):
    """
    Consolidation followed by a volume spike and price breakout.
    """
    if len(df) < 20: return False
    avg_vol = df['Volume'].iloc[-20:-1].mean()
    current_vol = df['Volume'].iloc[-1]
    
    max_high = df['High'].iloc[-20:-1].max()
    breakout = df['Close'].iloc[-1] > max_high
    vol_spike = current_vol > avg_vol * 2
    
    return breakout and vol_spike

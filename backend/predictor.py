# backend/predictor.py
import time
import json
import pandas as pd
import yfinance as yf
import numpy as np


# -------------------------------
# Utilities
# -------------------------------
def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
    df = df.loc[:, ~pd.Index(df.columns).duplicated()].copy()
    return df


def _fetch_data(symbol: str, period="6mo", interval="1d", retries=4) -> pd.DataFrame:
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            df = yf.download(
                symbol,
                period=period,
                interval=interval,
                progress=False,
                threads=False,
            )
            if df is not None and not df.empty:
                return _normalize_columns(df)
            last_err = Exception("Empty data from Yahoo Finance")
        except json.JSONDecodeError as e:
            last_err = e
        except Exception as e:
            last_err = e
        time.sleep(1.5 * attempt)

    try:
        df = yf.Ticker(symbol).history(period=period, interval=interval)
        if df is not None and not df.empty:
            return _normalize_columns(df)
    except Exception as e:
        last_err = e

    raise last_err


# -------------------------------
# Core Prediction Logic
# -------------------------------
def get_prediction(symbol: str) -> dict:
    df = _fetch_data(symbol)

    required = {"Open", "High", "Low", "Close"}
    if not required.issubset(df.columns):
        raise Exception(f"Unexpected columns: {df.columns}")

    close = df["Close"]

    current_price = float(close.iloc[-1])

    # ===============================
    # 1️⃣ TECHNICAL INDICATORS
    # ===============================

    signals = []

    # ---- Moving Average Trend ----
    ma_short = close.rolling(5).mean().iloc[-1]
    ma_long = close.rolling(20).mean().iloc[-1]

    if ma_short > ma_long:
        signals.append("BUY")
    elif ma_short < ma_long:
        signals.append("SELL")

    # ---- RSI (14) ----
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = -delta.clip(upper=0).rolling(14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    rsi_val = rsi.iloc[-1]

    if rsi_val < 30:
        signals.append("BUY")
    elif rsi_val > 70:
        signals.append("SELL")

    # ---- Momentum (7-day) ----
    if len(close) >= 7:
        momentum = close.iloc[-1] - close.iloc[-7]
        if momentum > 0:
            signals.append("BUY")
        elif momentum < 0:
            signals.append("SELL")

    # ===============================
    # 2️⃣ FINAL DECISION (VOTING)
    # ===============================
    buy_votes = signals.count("BUY")
    sell_votes = signals.count("SELL")

    if buy_votes > sell_votes:
        signal = "BUY"
        predicted_price = round(current_price * 1.01, 2)
    elif sell_votes > buy_votes:
        signal = "SELL"
        predicted_price = round(current_price * 0.99, 2)
    else:
        signal = "HOLD"
        predicted_price = round(current_price, 2)

    # ===============================
    # 3️⃣ OHLC + HISTORY
    # ===============================
    last = df.iloc[-1]
    ohlc = {
        "Open": float(last["Open"]),
        "High": float(last["High"]),
        "Low": float(last["Low"]),
        "Close": float(last["Close"]),
    }

    history = df[["Close"]].tail(180).reset_index()
    history.columns = ["Date", "Close"]
    history["Date"] = pd.to_datetime(history["Date"], errors="coerce")
    history["Close"] = pd.to_numeric(history["Close"], errors="coerce")
    history = history.dropna()

    return {
        "current_price": round(current_price, 2),
        "predicted_price": predicted_price,
        "signal": signal,
        "ohlc": ohlc,
        "history": history,
        "debug_signals": signals,  # optional (can remove later)
    }

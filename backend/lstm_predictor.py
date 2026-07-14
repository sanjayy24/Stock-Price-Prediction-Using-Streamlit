import numpy as np
import yfinance as yf

def get_lstm_prediction(symbol):
    data = yf.download(symbol, period="1y", progress=False)

    if data.empty:
        raise ValueError("No data for LSTM model")

    prices = data["Close"].values[-30:]
    avg_change = np.mean(np.diff(prices))

    current_price = prices[-1]
    predicted_price = current_price + avg_change

    signal = "BUY" if predicted_price > current_price else "SELL"

    return {
        "current_price": round(float(current_price), 2),
        "predicted_price": round(float(predicted_price), 2),
        "signal": signal
    }

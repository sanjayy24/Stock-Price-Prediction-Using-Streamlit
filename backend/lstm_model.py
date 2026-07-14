import numpy as np
import yfinance as yf
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout


def get_lstm_prediction(symbol):
    # -------------------------
    # 1. Fetch Data
    # -------------------------
    df = yf.download(symbol, period="2y", progress=False)

    if df.empty:
        raise ValueError("No data available")

    data = df[["Close"]].values

    # -------------------------
    # 2. Scale Data
    # -------------------------
    scaler = MinMaxScaler(feature_range=(0, 1))
    scaled_data = scaler.fit_transform(data)

    # -------------------------
    # 3. Create Sequences
    # -------------------------
    sequence_length = 60
    X = []
    y = []

    for i in range(sequence_length, len(scaled_data)):
        X.append(scaled_data[i-sequence_length:i])
        y.append(scaled_data[i])

    X, y = np.array(X), np.array(y)

    # -------------------------
    # 4. Train/Test Split
    # -------------------------
    split = int(0.8 * len(X))
    X_train, X_test = X[:split], X[split:]
    y_train, y_test = y[:split], y[split:]

    # -------------------------
    # 5. Build Stacked LSTM
    # -------------------------
    model = Sequential()

    model.add(LSTM(50, return_sequences=True, input_shape=(X.shape[1], 1)))
    model.add(Dropout(0.2))

    model.add(LSTM(50, return_sequences=False))
    model.add(Dropout(0.2))

    model.add(Dense(25))
    model.add(Dense(1))

    model.compile(optimizer="adam", loss="mean_squared_error")

    # -------------------------
    # 6. Train Model
    # -------------------------
    model.fit(X_train, y_train, batch_size=32, epochs=5, verbose=0)

    # -------------------------
    # 7. Prediction
    # -------------------------
    last_60_days = scaled_data[-60:]
    last_60_days = np.reshape(last_60_days, (1, 60, 1))

    predicted_price = model.predict(last_60_days)
    predicted_price = scaler.inverse_transform(predicted_price)

    current_price = df["Close"].iloc[-1]

    signal = "BUY" if predicted_price[0][0] > current_price else "SELL"

    return {
        "current_price": round(float(current_price), 2),
        "predicted_price": round(float(predicted_price[0][0]), 2),
        "signal": signal
    }

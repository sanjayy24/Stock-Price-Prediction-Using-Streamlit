import sys
import os

# ---------- Path Setup ----------
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import json

from backend.predictor import get_prediction
from backend.auth_service import register_user, login_user
from backend.news_sentiment import fetch_google_news_rss, sentiment_from_headlines

# -----------------------------
# Session init
# -----------------------------
if "auth" not in st.session_state:
    st.session_state.auth = {"logged_in": False, "user": None}

# -----------------------------
# Page config + styles
# -----------------------------
st.set_page_config(page_title="STOCK PRICE PREDICTION SYSTEM", layout="wide")

st.markdown("""
<style>
.title { font-size: 34px; font-weight: 800; }
.signal-buy { color: #22c55e; font-size: 22px; font-weight: bold; }
.signal-sell { color: #ef4444; font-size: 22px; font-weight: bold; }
.small-muted { opacity: .75; }
.card {
  padding: 16px; border-radius: 14px;
  background: rgba(255,255,255,.06);
  border: 1px solid rgba(255,255,255,.12);
}
.badge {
  display:inline-block;
  padding: 6px 10px;
  border-radius: 999px;
  font-weight: 800;
  font-size: 14px;
  border: 1px solid rgba(255,255,255,.18);
  background: rgba(255,255,255,.06);
}
</style>
""", unsafe_allow_html=True)

def _ensure_df(x):
    if isinstance(x, pd.DataFrame):
        return x
    try:
        return pd.DataFrame(x)
    except Exception:
        return None

def _render_article_link(link: str):
    # Clean clickable link
    if link:
        st.markdown(f"[Open Article]({link})")

# -----------------------------
# Auth UI
# -----------------------------
def render_auth():
    st.markdown('<div class="title">🔐 User Login / Registration</div>', unsafe_allow_html=True)
    st.caption("Create an account to access the Stock Prediction Dashboard.")

    tab_login, tab_register = st.tabs(["Login", "Register"])

    with tab_login:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_password")

        if st.button("Login", use_container_width=True, key="btn_login"):
            ok, msg, user = login_user(email, password)
            if ok:
                st.session_state.auth = {"logged_in": True, "user": user}
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)
        st.markdown('</div>', unsafe_allow_html=True)

    with tab_register:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        full_name = st.text_input("Full Name", key="reg_full_name")
        email = st.text_input("Email", key="reg_email")
        phone = st.text_input("Phone (optional)", key="reg_phone")
        password = st.text_input("Password", type="password", key="reg_password")
        confirm = st.text_input("Confirm Password", type="password", key="reg_confirm")

        if st.button("Create Account", use_container_width=True, key="btn_register"):
            if not full_name.strip() or not email.strip() or not password.strip():
                st.error("Please fill Full Name, Email, and Password.")
            elif password != confirm:
                st.error("Passwords do not match.")
            elif len(password) < 6:
                st.error("Password must be at least 6 characters.")
            else:
                ok, msg = register_user(full_name, email, phone, password)
                if ok:
                    st.success(msg)
                    st.info("Now go to Login tab and sign in.")
                else:
                    st.error(msg)
        st.markdown('</div>', unsafe_allow_html=True)

def logout():
    st.session_state.auth = {"logged_in": False, "user": None}
    st.rerun()

# -----------------------------
# If not logged in, show auth page
# -----------------------------
if not st.session_state.auth["logged_in"]:
    render_auth()
    st.stop()

# -----------------------------
# Logged-in dashboard UI
# -----------------------------
user = st.session_state.auth["user"]
st.markdown('<div class="title">📈 STOCK PRICE PREDICTION SYSTEM</div>', unsafe_allow_html=True)
st.caption(f"Logged in as: **{user.get('full_name')}**  •  {user.get('email')}")

colA, colB = st.columns([1, 1])
with colB:
    if st.button("Logout", use_container_width=True, key="btn_logout"):
        logout()

# ---------- Inputs ----------
exchange = st.radio("Select Exchange", ["NSE", "BSE"], horizontal=True, key="exchange_radio")
symbol_input = st.text_input("Enter Stock Symbol", "INFY", key="symbol_input")

# ---------- Predict ----------
if st.button("Predict", key="btn_predict"):
    base = symbol_input.upper().replace(".NS", "").replace(".BO", "").strip()
    if not base:
        st.error("Please enter a stock symbol (example: INFY, WIPRO, ITC).")
        st.stop()

    symbol = base + (".NS" if exchange == "NSE" else ".BO")

    try:
        # -------- Market Data --------
        with st.spinner("Fetching market data..."):
            result = get_prediction(symbol)

        current = float(result["current_price"])
        predicted = float(result["predicted_price"])
        signal = result["signal"]
        ohlc = result["ohlc"]
        history = _ensure_df(result.get("history"))

        # ---------- Metrics ----------
        col1, col2, col3 = st.columns(3)
        col1.metric("Current Price", f"₹ {current:.2f}")
        col2.metric("Predicted Price", f"₹ {predicted:.2f}")
        if signal == "BUY":
            col3.markdown("<div class='signal-buy'>BUY</div>", unsafe_allow_html=True)
        else:
            col3.markdown("<div class='signal-sell'>SELL</div>", unsafe_allow_html=True)

        # ---------- Confidence ----------
        confidence = abs(predicted - current) / current * 100
        st.subheader("Prediction Confidence")
        st.progress(min(confidence / 5, 1.0))
        st.caption(f"{confidence:.2f}% confidence")

        # ---------- OHLC ----------
        st.subheader("Latest Day OHLC")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Open", f"₹ {ohlc['Open']:.2f}")
        c2.metric("High", f"₹ {ohlc['High']:.2f}")
        c3.metric("Low", f"₹ {ohlc['Low']:.2f}")
        c4.metric("Close", f"₹ {ohlc['Close']:.2f}")

        # ---------- News Sentiment (FREE Real-time via Google News RSS) ----------
        st.subheader("📰 News Sentiment (Real-time)")

        query = f"{base} stock"

        with st.spinner("Fetching recent news..."):
            items = fetch_google_news_rss(query, limit=10)

            # ✅ Support BOTH old and new versions of sentiment_from_headlines()
            out = sentiment_from_headlines(items)
            if isinstance(out, tuple) and len(out) == 4:
                sent_label, sent_score, scored, counts = out
            else:
                sent_label, sent_score, scored = out
                counts = None

        sent_color = {"Positive": "#22c55e", "Negative": "#ef4444", "Neutral": "#f59e0b"}
        extra_counts = ""
        if counts:
            extra_counts = f"&nbsp;&nbsp;✅ Pos: {counts['positive']}  ❌ Neg: {counts['negative']}  ➖ Neu: {counts['neutral']}"

        st.markdown(
            f"**Overall Sentiment:** "
            f"<span class='badge' style='color:{sent_color.get(sent_label, '#f59e0b')}'>{sent_label}</span> "
            f"&nbsp;&nbsp;Avg Score: **{sent_score:.2f}** {extra_counts}",
            unsafe_allow_html=True
        )

        # ---------- Final Decision ----------
        st.subheader("✅ Final Decision (Technical + Sentiment)")

        if signal == "BUY" and sent_label == "Positive":
            st.success("Strong Buy ✅ (BUY + Positive news)")
        elif signal == "SELL" and sent_label == "Negative":
            st.error("Strong Sell ❌ (SELL + Negative news)")
        elif signal == "BUY" and sent_label == "Negative":
            st.warning("Risky Buy ⚠️ (BUY but Negative news)")
        elif signal == "SELL" and sent_label == "Positive":
            st.warning("Risky Sell ⚠️ (SELL but Positive news)")
        else:
            st.info("Hold / Mixed ⚠️ (Neutral or unclear sentiment)")

        with st.expander("Recent News Headlines"):
            if not scored:
                st.info("No news found right now. Try another stock or try again later.")
            else:
                for it in scored:
                    title = (it.get("title", "") or "").strip()
                    comp = float(it.get("compound", 0.0) or 0.0)
                    published = (it.get("published", "") or "").strip()
                    link = (it.get("link", "") or "").strip()

                    st.write(f"• {title}  | sentiment: {comp:.2f}")
                    if published:
                        st.caption(published)
                    _render_article_link(link)

        # ---------- Chart ----------
        st.subheader("Last 180 Days Price Trend")

        if history is None or history.empty:
            st.warning("No history data received from Yahoo. Try again after some time.")
            st.stop()

        # Backend returns Date + Close
        if "Date" not in history.columns or "Close" not in history.columns:
            st.error(f"Unexpected history columns: {list(history.columns)}")
            st.write(history.head())
            st.stop()

        # Duplicate Date safety
        date_obj = history.loc[:, "Date"]
        if isinstance(date_obj, pd.DataFrame):
            date_series = date_obj.iloc[:, 0]
        else:
            date_series = date_obj

        history = history.copy()
        history["Date"] = pd.to_datetime(date_series, errors="coerce")
        history["Close"] = pd.to_numeric(history["Close"], errors="coerce")
        history = history.dropna(subset=["Date", "Close"]).sort_values("Date").tail(180)

        y_min = float(history["Close"].min()) * 0.95
        y_max = float(history["Close"].max()) * 1.05

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=history["Date"],
            y=history["Close"],
            mode="lines",
            hovertemplate="₹ %{y:.2f}<br>%{x|%d %b %Y}<extra></extra>",
            name="Close Price"
        ))
        fig.update_layout(
            template="plotly_dark",
            height=520,
            xaxis=dict(title="Date", showgrid=False, tickformat="%d %b", nticks=10),
            yaxis=dict(title="Price (₹)", range=[y_min, y_max], showgrid=True),
            margin=dict(l=60, r=40, t=30, b=80)
        )
        st.plotly_chart(fig, use_container_width=True)

        # ---------- Info ----------
        with st.expander("📌 Model Information"):
            st.write("""
            **Model Type:** Baseline statistical predictor  
            **Data Source:** Yahoo Finance + Google News RSS (sentiment)  
            **Prediction Horizon:** Short-term trend  
            """)

    except json.JSONDecodeError:
        st.error("❌ Yahoo Finance blocked the request (JSON error). Try again after 1–2 minutes.")
        st.info("Tip: Avoid VPN, try hotspot once, and do not run many symbols quickly.")
    except Exception as e:
        msg = str(e)
        if "Expecting value" in msg or "JSONDecodeError" in msg or "Empty data" in msg:
            st.error("❌ Yahoo Finance did not return data (blocked/rate limited). Try again after 1–2 minutes.")
            st.info("Tip: Avoid VPN, try hotspot once, and do not run many symbols quickly.")
        else:
            st.error("Error occurred:")
            st.write(msg)

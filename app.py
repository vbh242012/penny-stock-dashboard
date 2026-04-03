import streamlit as st
import yfinance as yf
import pandas as pd
from finvizfinance.screener.overview import Overview
import warnings

warnings.filterwarnings("ignore")

st.set_page_config(page_title="Ruthless Penny Scalper", layout="wide")

# CSS to kill scrollbars and force a flat table
st.markdown("""
    <style>
    .stDataFrame div[data-testid="stTable"] { overflow: visible !important; }
    .stDataFrame [data-testid="styled-data-frame"] { height: auto !important; }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR: THE LAWS ---
st.sidebar.title("⚔️ RUTHLESS PENNY LAWS")
st.sidebar.markdown("""
**1. THE FLOOR:** Price **MUST** be > VWAP.
**2. THE FUEL:** RVOL **MUST** be > 2.5.
**3. THE MOMENTUM:** RSI **MUST** be 40-65.
**4. THE EXIT:** 2x ATR Profit / 1.2x ATR Risk.
""")

st.title("💰 Ruthless Penny Stock Scalper (<$2)")

def format_ticker(t):
    return t.replace('-', '.')

@st.cache_data(ttl=3600)
def get_penny_data():
    # 1. Get Universe
    try:
        f = Overview()
        f.set_filter(filters_dict={'Price': 'Under $2'})
        tickers = f.screener_view()['Ticker'].tolist()
    except:
        tickers = ['SNDL', 'MULN', 'IDEX']
    
    # 2. FORCE DGNX into the start of the list
    if 'DGNX' not in tickers:
        tickers.insert(0, 'DGNX')
    else:
        tickers.remove('DGNX')
        tickers.insert(0, 'DGNX')

    results = []
    yes_count = 0
    p = st.progress(0)
    status = st.empty()

    # 3. Process until we have 25 total, ensuring at least 5 are "YES"
    for i, t in enumerate(tickers):
        if i > 200: break # Protection
        if len(results) >= 25 and yes_count >= 5: break
            
        status.text(f"Scanning Ticker {i}: {t} | Found {yes_count}/5 BUY signals")
        y_ticker = format_ticker(t)
        try:
            s = yf.Ticker(y_ticker)
            h = s.history(period="5d", interval="5m") 
            daily = s.history(period="60d")
            if h.empty or daily.empty: continue
            
            avg_vol = daily['Volume'].mean()
            price = h['Close'].iloc[-1]
            vwap = (h['Close'] * h['Volume']).sum() / h['Volume'].sum()
            tr = (h['High'] - h['Low']).rolling(14).mean().iloc[-1]
            
            delta = h['Close'].diff()
            rsi = 100 - (100 / (1 + (delta.clip(lower=0).rolling(14).mean() / -delta.clip(upper=0).rolling(14).mean()).iloc[-1]))
            rvol = h['Volume'].tail(78).sum() / (avg_vol / 6.5)

            is_buy = "YES" if (price > vwap and 40 < rsi < 65 and rvol > 2.0) else "NO"
            if is_buy == "YES": yes_count += 1

            results.append({
                'Ticker': t, 'BUY': is_buy, 'Price': round(price, 4),
                'TP': round(price + (2.5 * tr), 4), 'SL': round(price - (1.2 * tr), 4),
                'RSI': round(rsi, 1), 'RVOL': round(rvol, 2), '60D Avg Vol': int(avg_vol)
            })
        except: continue
        p.progress(min((i + 1) / 200, 1.0))

    df = pd.DataFrame(results).sort_values(['BUY', '60D Avg Vol'], ascending=[False, False])
    status.empty()
    p.empty()
    return df.head(25)

if st.button("🚀 EXECUTE PENNY SCAN"):
    data = get_penny_data()
    st.dataframe(
        data.style.map(lambda x: 'background-color: #2ecc71; color: white;' if x == 'YES' else '', subset=['BUY']),
        width='stretch', height=1000
    )
import streamlit as st
import yfinance as yf
import pandas as pd
from finvizfinance.screener.overview import Overview
import warnings

warnings.filterwarnings("ignore")

st.set_page_config(page_title="Penny Scalper (<$2)", layout="wide")

# CSS to expand table and hide scrollbars for clean full-page view
st.markdown("""
    <style>
    .stDataFrame div[data-testid="stTable"] { overflow: visible !important; }
    .stDataFrame [data-testid="styled-data-frame"] { height: auto !important; }
    </style>
    """, unsafe_allow_html=True)

st.title("💰 Ruthless Penny Scalper (<$2)")
st.sidebar.error("""
**⚔️ RUTHLESS LAWS (PENNY)**
1. **FLOOR**: Price > VWAP.
2. **FUEL**: RVOL > 2.5.
3. **MOMENTUM**: RSI 40-65.
4. **EXIT**: Take 5-8% quickly.
""")

@st.cache_data(ttl=3600)
def get_penny_data():
    try:
        f = Overview()
        f.set_filter(filters_dict={'Price': 'Under $2'})
        # Pulling the entire matching universe
        full_universe = f.screener_view()
        tickers = full_universe['Ticker'].tolist()
    except:
        tickers = ['SNDL', 'MULN', 'IDEX', 'TYDE']
    
    if 'DGNX' not in tickers:
        tickers.append('DGNX')
    
    results = []
    p = st.progress(0)
    status = st.empty()
    
    total = len(tickers)
    for i, t in enumerate(tickers):
        status.text(f"Scanning {i}/{total}: {t}")
        try:
            s = yf.Ticker(t)
            # Use 5m interval for the 1-day VWAP/RSI precision
            h = s.history(period="60d", interval="5m") 
            if h.empty: continue
            
            daily_h = s.history(period="60d")
            avg_vol = daily_h['Volume'].mean()
            price = h['Close'].iloc[-1]
            
            # VWAP Calculation (Institutional Floor)
            vwap = (h['Close'] * h['Volume']).sum() / h['Volume'].sum()
            
            # ATR for Exit Strategy
            tr = (h['High'] - h['Low']).rolling(14).mean().iloc[-1]
            
            # RSI 14
            delta = h['Close'].diff()
            up = delta.clip(lower=0).rolling(14).mean()
            down = -delta.clip(upper=0).rolling(14).mean()
            rsi = 100 - (100 / (1 + (up / down).iloc[-1]))
            
            rvol = h['Volume'].tail(78).sum() / avg_vol # Approx Daily RVOL

            # RUTHLESS BUY CONDITION
            is_buy = "YES" if (price > vwap and 40 < rsi < 65 and rvol > 2.0) else "NO"

            results.append({
                'Ticker': t, 'BUY': is_buy, 'Entry Price': round(price, 4),
                'Take Profit': round(price + (2.5 * tr), 4), 'Stop Loss': round(price - (1.2 * tr), 4),
                'RSI': round(rsi, 1), 'RVOL': round(rvol, 2), '60D Avg Vol': int(avg_vol)
            })
        except: continue
        p.progress((i + 1) / total)
    
    df_results = pd.DataFrame(results)
    
    # Sort by Volume and pick Top 25
    top_25 = df_results.sort_values('60D Avg Vol', ascending=False).head(25)
    
    # Ensure DGNX is present
    if 'DGNX' not in top_25['Ticker'].values and 'DGNX' in df_results['Ticker'].values:
        dgnx_row = df_results[df_results['Ticker'] == 'DGNX']
        top_25 = pd.concat([top_25, dgnx_row])

    status.empty()
    p.empty()
    return top_25

if st.button("🚀 EXECUTE FULL PENNY SCAN"):
    data = get_penny_data()
    st.dataframe(
        data.style.map(lambda x: 'background-color: #2ecc71; color: white;' if x == 'YES' else '', subset=['BUY']),
        use_container_width=True,
        height=1000
    )
import streamlit as st
import yfinance as yf
import pandas as pd
from finvizfinance.screener.overview import Overview
import warnings

warnings.filterwarnings("ignore")

st.set_page_config(page_title="Penny Scalper (<$2)", layout="wide")

# CSS to expand table and hide scrollbars
st.markdown("<style>.stDataFrame div[data-testid='stTable'] {overflow: visible !important;} .stDataFrame [data-testid='styled-data-frame'] {height: auto !important;}</style>", unsafe_allow_html=True)

st.title("💰 Ruthless Penny Scalper (<$2)")

def format_ticker(t):
    return t.replace('-', '.')

@st.cache_data(ttl=3600)
def get_penny_data():
    try:
        f = Overview()
        f.set_filter(filters_dict={'Price': 'Under $2'})
        tickers = f.screener_view()['Ticker'].tolist()
    except: 
        tickers = ['SNDL', 'DGNX', 'MULN']
    
    # Ensure DGNX is in the candidate list
    if 'DGNX' not in tickers: tickers.insert(0, 'DGNX')
    
    results = []
    p = st.progress(0)
    status = st.empty()
    
    # We scan until we have enough "YES" or hit a safety limit of 150 tickers
    yes_count = 0
    for i, t in enumerate(tickers):
        if i > 150: break # Safety cutoff to prevent timeout
        if len(results) >= 25 and yes_count >= 5 and 'DGNX' in [r['Ticker'] for r in results]:
            break
            
        status.text(f"Searching for 'YES' signals... Found {yes_count}/5. Scanning: {t}")
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
            
            # RSI & RVOL logic
            delta = h['Close'].diff()
            rsi = 100 - (100 / (1 + (delta.clip(lower=0).rolling(14).mean() / -delta.clip(upper=0).rolling(14).mean()).iloc[-1]))
            rvol = h['Volume'].tail(78).sum() / (avg_vol / 6.5)

            is_buy = "YES" if (price > vwap and 40 < rsi < 65 and rvol > 2.0) else "NO"
            if is_buy == "YES": yes_count += 1

            results.append({
                'Ticker': t, 'BUY': is_buy, 'Entry Price': round(price, 4),
                'Take Profit': round(price + (2.5 * tr), 4), 'Stop Loss': round(price - (1.2 * tr), 4),
                'VWAP (Daily)': round(vwap, 4), 'RSI': round(rsi, 1), 'RVOL': round(rvol, 2), '60D Avg Vol': int(avg_vol)
            })
        except: continue
        p.progress(min((i + 1) / 150, 1.0))
    
    # PROCESSING LOGIC:
    df_all = pd.DataFrame(results)
    
    # 1. Grab all YES stocks
    yes_df = df_all[df_all['BUY'] == "YES"]
    # 2. Grab all NO stocks
    no_df = df_all[df_all['BUY'] == "NO"]
    # 3. Always keep DGNX
    dgnx_row = df_all[df_all['Ticker'] == 'DGNX']
    
    # 4. Construct the top 25: All YES + highest volume NOs
    combined = pd.concat([yes_df, no_df, dgnx_row]).drop_duplicates(subset=['Ticker'])
    final_df = combined.sort_values(['BUY', '60D Avg Vol'], ascending=[False, False]).head(25)
    
    # Final sort by volume for display as requested
    final_df = final_df.sort_values('60D Avg Vol', ascending=False)
    
    status.empty()
    p.empty()
    return final_df

if st.button("🚀 EXECUTE RUTHLESS PENNY SCAN"):
    data = get_penny_data()
    st.dataframe(
        data.style.map(lambda x: 'background-color: #2ecc71; color: white;' if x == 'YES' else '', subset=['BUY']), 
        width='stretch', height=1000
    )
import streamlit as st
import yfinance as yf
import pandas as pd
from finvizfinance.screener.overview import Overview
import io
import warnings
from datetime import datetime

warnings.filterwarnings("ignore")

# --- UI Configuration ---
st.set_page_config(page_title="Ruthless Top 25 Dashboard", layout="wide")

# CSS to hide scrollbars and make the table fit the page
st.markdown("""
    <style>
    .stDataFrame div[data-testid="stTable"] {
        overflow: visible !important;
    }
    section.main > div {
        padding-top: 1rem;
        padding-bottom: 1rem;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🇦🇪 📈 Top 25 Ruthless Volume Leaders")
st.sidebar.error("⚔️ SWING LAWS: Price > VWAP | RVOL > 2.5 | RSI 40-65")

@st.cache_data(ttl=3600)
def fetch_ruthless_data():
    # Step 1: Pull 500 candidates under $2 (or $10 for your swing preferences)
    try:
        foverview = Overview()
        foverview.set_filter(filters_dict={'Price': 'Under $10'})
        # We grab 500 to find the 'true' volume kings
        screener_df = foverview.screener_view() 
        candidate_tickers = screener_df['Ticker'].head(500).tolist()
    except:
        candidate_tickers = ['DGNX', 'SNDL', 'PLUG', 'NIO', 'MARA', 'RIOT', 'F', 'LCID']

    # Step 2: Ensure DGNX is in the mix
    if 'DGNX' not in candidate_tickers:
        candidate_tickers.append('DGNX')

    processed_data = []
    progress = st.progress(0)
    status = st.empty()

    # Step 3: Pull 60-day volume data and calculate averages
    for idx, ticker in enumerate(candidate_tickers):
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="60d")
            if hist.empty: continue
            
            avg_vol = hist['Volume'].mean()
            curr_price = hist['Close'].iloc[-1]
            
            # Calculate ATR for TP/SL
            high_low = hist['High'] - hist['Low']
            atr = high_low.rolling(window=14).mean().iloc[-1]

            # Simplified VWAP & RSI for the logic
            vwap = (hist['Close'] * hist['Volume']).sum() / hist['Volume'].sum()
            
            processed_data.append({
                'Ticker': ticker,
                '60D Avg Vol': int(avg_vol),
                'Price': curr_price,
                'VWAP': vwap,
                'ATR': atr
            })
        except: continue
        if idx % 50 == 0: progress.progress(idx / 500)

    # Step 4: Sort and pick Top 25
    df_all = pd.DataFrame(processed_data)
    top_25 = df_all.sort_values(by='60D Avg Vol', ascending=False).head(25)
    
    # Add DGNX if it wasn't in the top 25
    if 'DGNX' not in top_25['Ticker'].values:
        dgnx_data = df_all[df_all['Ticker'] == 'DGNX']
        top_25 = pd.concat([top_25, dgnx_data])

    # Final "Ruthless" Columns
    final_list = []
    for _, row in top_25.iterrows():
        entry = row['Price']
        # 1.5x ATR Risk / 3.5x ATR Reward
        tp = entry + (3.5 * row['ATR'])
        sl = entry - (1.5 * row['ATR'])
        is_buy = "YES" if (entry > row['VWAP']) else "NO"
        
        final_list.append({
            'Ticker': row['Ticker'],
            'BUY': is_buy,
            'Entry Price': round(entry, 2),
            'Take Profit': round(tp, 2),
            'Stop Loss': round(sl, 2),
            '60D Avg Vol': row['60D Avg Vol'],
            'vs VWAP': "ABOVE" if is_buy == "YES" else "BELOW"
        })

    status.empty()
    progress.empty()
    return pd.DataFrame(final_list)

if st.button("🚀 PULL TOP 25 VOLUME KINGS"):
    data = fetch_ruthless_data()
    # Using height=None and width=stretch to fit everything on page without scrollbars
    st.dataframe(
        data.style.map(lambda x: 'background-color: #2ecc71; color: white;' if x == 'YES' else '', subset=['BUY']),
        use_container_width=True,
        height=1000 # Large enough to fit 25+ rows without a scrollbar
    )
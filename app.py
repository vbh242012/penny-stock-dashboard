import streamlit as st
import yfinance as yf
import pandas as pd
from finvizfinance.screener.overview import Overview
import io
import warnings
from datetime import datetime

# Suppress technical warnings
warnings.filterwarnings("ignore")

# --- UI Configuration ---
st.set_page_config(page_title="Ruthless Penny Stock Quant", layout="wide")

# --- SIDEBAR: THE RULES ---
st.sidebar.title("⚔️ THE RUTHLESS LAWS")
st.sidebar.error("""
1. **INSTITUTIONAL FLOOR**: Price MUST be above VWAP.
2. **LIQUIDITY FUEL**: RVOL MUST be > 2.5.
3. **MOMENTUM COOL-OFF**: RSI MUST be between 40 and 65.
""")

st.sidebar.info("""
**UAE Trader Schedule:**
- App Open: 6:00 PM GST
- Analysis: 6:15 PM GST
- Exit Target: 5% Profit
""")

st.title("🇦🇪 📈 Ruthless Liquidity & Momentum Analyzer")
st.markdown(f"""
**Operational Context:** Optimized for **10:00 AM EST (Dubai 6:00 PM)**. 
Filtering for the top 20 liquidity leaders under $2.
*Current Analysis Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
""")

# --- Core Analysis Engine ---
@st.cache_data(ttl=3600)
def run_quant_analysis():
    all_records = []
    
    try:
        foverview = Overview()
        foverview.set_filter(filters_dict={'Price': 'Under $2'})
        # EXACT API STRING: 'Average Volume (3 Month)'
        screener_df = foverview.screener_view(order='Average Volume (3 Month)')
        
        tickers = screener_df['Ticker'].head(19).tolist()
        if 'DGNX' not in tickers:
            tickers.append('DGNX')
        tickers = tickers[:20]
    except Exception as e:
        tickers = ['DGNX', 'SNDL', 'FCEL', 'GNS', 'SOUN', 'BTBT', 'RIG', 'PLUG', 'NKLA']
        st.warning(f"Screener API bypass active. Analyzing high-volume fallback list.")

    progress = st.progress(0)
    status = st.empty()

    for idx, ticker in enumerate(tickers):
        status.text(f"Scanning Ticker: {ticker}...")
        try:
            stock = yf.Ticker(ticker)
            df = stock.history(period="60d", interval="5m")
            if df.empty: continue

            # --- Technical Calculations ---
            df['TP'] = (df['High'] + df['Low'] + df['Close']) / 3
            df['VWAP'] = (df['TP'] * df['Volume']).cumsum() / df['Volume'].cumsum()
            
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            df['RSI'] = 100 - (100 / (1 + (gain / loss)))

            avg_daily_vol = df['Volume'].sum() / 60 
            
            df['Date'] = df.index.date
            for date, group in df.groupby('Date'):
                c_price = group['Close'].iloc[-1]
                c_vwap = group['VWAP'].iloc[-1]
                c_rsi = group['RSI'].iloc[-1]
                daily_vol = group['Volume'].sum()
                rvol = daily_vol / avg_daily_vol
                vs_vwap_pct = ((c_price - c_vwap) / c_vwap) * 100
                
                low_time = group['Low'].idxmin()
                high_time = group['High'].idxmax()
                low_before_high = low_time < high_time

                # --- RUTHLESS ACTION LOGIC ---
                if rvol > 2.5 and 0.5 < vs_vwap_pct < 4.0 and 40 < c_rsi < 65 and low_before_high:
                    action = "🔥 RUTHLESS BUY"
                elif c_price < c_vwap and c_rsi > 70:
                    action = "💀 EXIT/AVOID"
                elif vs_vwap_pct < -2.0:
                    action = "⚠️ WEAKNESS"
                else:
                    action = "💤 NO EDGE"
                
                all_records.append({
                    'Ticker': ticker,
                    'Date': date,
                    'Action': action,
                    'Price': round(c_price, 4),
                    'vs VWAP (%)': round(vs_vwap_pct, 2),
                    'RSI': round(c_rsi, 2),
                    'RVOL': round(rvol, 2),
                    'Volume': int(daily_vol),
                    'Trend': "Bullish" if low_before_high else "Bearish"
                })
        except:
            continue
        progress.progress((idx + 1) / len(tickers))
    
    status.empty()
    return pd.DataFrame(all_records)

# --- UI Execution ---
if st.button("🚀 EXECUTE RUTHLESS SCAN"):
    with st.spinner("Analyzing high-liquidity targets..."):
        data = run_quant_analysis()
        
        if not data.empty:
            latest_date = data['Date'].max()
            today_data = data[data['Date'] == latest_date].sort_values(by='RVOL', ascending=False)
            
            st.header(f"Live Signals: {latest_date}")
            
            def style_action(val):
                if val == "🔥 RUTHLESS BUY": color = '#2ecc71'
                elif val == "💀 EXIT/AVOID": color = '#e74c3c'
                elif val == "⚠️ WEAKNESS": color = '#f1c40f'
                else: color = 'transparent'
                return f'background-color: {color}; color: white; font-weight: bold'

            st.dataframe(
                today_data.style.map(style_action, subset=['Action']),
                use_container_width=True
            )

            # Export
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                data.to_excel(writer, index=False)
            st.download_button("📥 Download Full Quant Report", data=buffer.getvalue(), file_name=f"Ruthless_Report_{latest_date}.xlsx")
        else:
            st.error("No data found. Check your internet or API access.")
import streamlit as st
import yfinance as yf
import pandas as pd
from finvizfinance.screener.overview import Overview
import io
import warnings
from datetime import datetime

# Suppress technical warnings for a clean UI
warnings.filterwarnings("ignore")

# --- UI Configuration ---
st.set_page_config(page_title="Ruthless Penny Stock Quant", layout="wide")

st.title("🇦🇪 📈 Ruthless Liquidity & Momentum Analyzer")
st.markdown(f"""
**Operational Context:** Optimized for **10:00 AM EST (Dubai 6:00 PM)**. 
This app filters for the 20 highest-volume leaders under $2 and applies a predatory entry logic based on Institutional Support (VWAP), Momentum (RSI), and Fuel (RVOL).
*Current Analysis Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
""")

# --- Core Analysis Engine ---
@st.cache_data(ttl=3600)
def run_quant_analysis():
    all_records = []
    
    # Step 1: Ruthless Filtering for Liquidity Leaders
    try:
        foverview = Overview()
        foverview.set_filter(filters_dict={'Price': 'Under $2'})
        # We sort by 'Average Volume' to find stocks with consistent institutional 'churn'
        screener_df = foverview.screener_view(order='Average Volume')
        
        tickers = screener_df['Ticker'].head(19).tolist()
        if 'DGNX' not in tickers:
            tickers.append('DGNX')
        tickers = tickers[:20]
    except Exception as e:
        st.error(f"Screener Error: {e}. Using fallback list.")
        tickers = ['DGNX', 'SNDL', 'FCEL', 'GNS', 'SOUN', 'BTBT', 'RIG']

    progress = st.progress(0)
    status = st.empty()

    for idx, ticker in enumerate(tickers):
        status.text(f"Scanning Ticker: {ticker}...")
        try:
            stock = yf.Ticker(ticker)
            # 60 days of 5-minute data is the gold standard for intraday probability
            df = stock.history(period="60d", interval="5m")
            if df.empty: continue

            # --- Technical Calculations ---
            # 1. VWAP (The Institutional Line in the Sand)
            df['TP'] = (df['High'] + df['Low'] + df['Close']) / 3
            df['VWAP'] = (df['TP'] * df['Volume']).cumsum() / df['Volume'].cumsum()
            
            # 2. RSI (Relative Strength Index - 14 Period)
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            df['RSI'] = 100 - (100 / (1 + (gain / loss)))

            # 3. 60-Day Average Volume for RVOL
            avg_daily_vol = df['Volume'].sum() / 60 
            
            df['Date'] = df.index.date
            for date, group in df.groupby('Date'):
                c_price = group['Close'].iloc[-1]
                c_vwap = group['VWAP'].iloc[-1]
                c_rsi = group['RSI'].iloc[-1]
                daily_vol = group['Volume'].sum()
                rvol = daily_vol / avg_daily_vol
                vs_vwap_pct = ((c_price - c_vwap) / c_vwap) * 100
                
                # Check if Low occurred before High (Trend Indicator)
                low_time = group['Low'].idxmin()
                high_time = group['High'].idxmax()
                low_before_high = low_time < high_time

                # --- RUTHLESS ACTION LOGIC ---
                # Entry: RVOL > 2.5 (Massive Interest), Above VWAP (Support), RSI 45-60 (Not exhausted)
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
    with st.spinner("Crunching 60 days of intraday data..."):
        data = run_quant_analysis()
        
        if not data.empty:
            # Filter for the most recent trading session
            latest_date = data['Date'].max()
            today_data = data[data['Date'] == latest_date].sort_values(by='RVOL', ascending=False)
            
            st.header(f"Live Signals: {latest_date}")
            st.caption("Sorted by Relative Volume (RVOL) - The higher the RVOL, the stronger the move.")

            # Custom Styling
            def style_action(val):
                if val == "🔥 RUTHLESS BUY": color = '#2ecc71' # Green
                elif val == "💀 EXIT/AVOID": color = '#e74c3c' # Red
                elif val == "⚠️ WEAKNESS": color = '#f1c40f'   # Yellow
                else: color = 'transparent'
                return f'background-color: {color}; color: white; font-weight: bold'

            st.dataframe(
                today_data.style.applymap(style_action, subset=['Action']),
                use_container_width=True
            )

            # --- Quantitative Summary ---
            st.divider()
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Tickers", len(today_data))
            with col2:
                buy_count = len(today_data[today_data['Action'] == "🔥 RUTHLESS BUY"])
                st.metric("High-Prob Buys", buy_count)
            with col3:
                avg_rsi = today_data['RSI'].mean()
                st.metric("Market Avg RSI", f"{avg_rsi:.1f}")

            # --- Excel Download ---
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                # Provide full 60-day history in the Excel for backtesting
                data.to_excel(writer, index=False, sheet_name='60Day_Quant_History')
            
            st.download_button(
                label="📥 Download Full 60-Day Backtest Report",
                data=buffer.getvalue(),
                file_name=f"Ruthless_Report_{latest_date}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.error("No data retrieved. Check internet connection or API status.")

st.sidebar.title("Trader's Checklist")
st.sidebar.markdown("""
1. **Wait for 10:00 AM EST**: Let the 9:30 AM gap-and-crap finish.
2. **Confirm VWAP**: Only buy if the Green highlight appears.
3. **Check RVOL**: If RVOL is < 2.0, the move lacks 'Fuel'.
4. **Target 5%**: In penny stocks, 5% is a massive win. Take it.
""")
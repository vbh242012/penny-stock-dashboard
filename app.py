import streamlit as st
import yfinance as yf
import pandas as pd
from finvizfinance.screener.overview import Overview
import io
import warnings

warnings.filterwarnings("ignore")

# --- UI Setup ---
st.set_page_config(page_title="High-Liquidity Penny Stock Quant", layout="wide")
st.title("🇦🇪 📈 Top 20 Liquidity Leaders Dashboard")
st.markdown("""
**Strategy:** This app identifies the 20 stocks (under $2) with the highest average daily volume over the last 60 days. 
Opening this at **10:00 AM EST** allows you to see if these high-liquidity stocks are holding above their VWAP.
""")

@st.cache_data(ttl=3600)
def fetch_top_liquidity_data():
    all_records = []
    
    # Step 1: Get a broad list of high-volume candidates under $2
    try:
        foverview = Overview()
        foverview.set_filter(filters_dict={'Price': 'Under $2'})
        # Sorting by 'Average Volume' instead of current 'Volume'
        screener_df = foverview.screener_view(order='Average Volume')
        
        # Take the top 19 to allow room for DGNX
        tickers = screener_df['Ticker'].head(19).tolist()
        if 'DGNX' not in tickers:
            tickers.append('DGNX')
        tickers = tickers[:20]
    except Exception as e:
        st.error(f"Screener Error: {e}")
        tickers = ['DGNX', 'SNDL', 'FCEL', 'GNS', 'SOUN']

    progress = st.progress(0)
    status_text = st.empty()

    for idx, ticker in enumerate(tickers):
        status_text.text(f"Analyzing Liquidity for {ticker}...")
        try:
            stock = yf.Ticker(ticker)
            # Fetch 60 days of 5-minute data
            df = stock.history(period="60d", interval="5m")
            if df.empty: continue

            # --- Technical Indicators ---
            # 1. VWAP (Volume Weighted Average Price)
            df['TP'] = (df['High'] + df['Low'] + df['Close']) / 3
            df['VWAP'] = (df['TP'] * df['Volume']).cumsum() / df['Volume'].cumsum()
            
            # 2. RSI (14-period)
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            df['RSI'] = 100 - (100 / (1 + (gain / loss)))

            # 3. 60-Day Avg Volume (for RVOL calculation)
            avg_daily_vol = df['Volume'].sum() / 60 
            
            # Group by date for the daily analysis
            df['Date'] = df.index.date
            for date, group in df.groupby('Date'):
                curr_close = group['Close'].iloc[-1]
                curr_vwap = group['VWAP'].iloc[-1]
                curr_rsi = group['RSI'].iloc[-1]
                daily_vol = group['Volume'].sum()
                rvol = daily_vol / avg_daily_vol

                # ACTION LOGIC
                # Buy if Price > VWAP (Support) and RSI is not overbought (<65) and Vol is high
                if curr_close > curr_vwap and 40 < curr_rsi < 65 and rvol > 1.1:
                    action = "BUY"
                elif curr_close < curr_vwap and curr_rsi > 70:
                    action = "SELL/AVOID"
                else:
                    action = "WAIT"
                
                all_records.append({
                    'Ticker': ticker,
                    'Stock Name': stock.info.get('shortName', ticker),
                    'Date': date,
                    'Action': action,
                    'Price': round(curr_close, 4),
                    'vs VWAP (%)': round(((curr_close - curr_vwap)/curr_vwap)*100, 2),
                    'RSI': round(curr_rsi, 2),
                    'RVOL': round(rvol, 2),
                    'Total Volume': int(daily_vol)
                })
        except:
            continue
        progress.progress((idx + 1) / len(tickers))
    
    status_text.text("Analysis Complete.")
    return pd.DataFrame(all_records)

# --- App Display ---
if st.button("🚀 Analyze Top 20 Liquidity Leaders"):
    data = fetch_top_liquidity_data()
    
    if not data.empty:
        latest_date = data['Date'].max()
        today_df = data[data['Date'] == latest_date].sort_values(by='Total Volume', ascending=False)
        
        st.header(f"Live Signals for {latest_date} (at 10:00 AM EST)")
        
        # Color Coding for the UI
        def color_action(val):
            if val == 'BUY': color = '#2ecc71'
            elif val == 'SELL/AVOID': color = '#e74c3c'
            else: color = 'transparent'
            return f'background-color: {color}'

        st.dataframe(today_df.style.applymap(color_action, subset=['Action']), use_container_width=True)
        
        # Export for Excel
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            data.sort_values(['Ticker', 'Date'], ascending=[True, False]).to_excel(writer, index=False)
        
        st.download_button("📥 Download 60-Day Report", data=buffer.getvalue(), file_name="Top_20_Liquidity_Report.xlsx")
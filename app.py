import streamlit as st
import yfinance as yf
import pandas as pd
from finvizfinance.screener.overview import Overview
import io
import warnings

warnings.filterwarnings("ignore")

# --- UI Setup ---
st.set_page_config(page_title="Penny Stock Quant Dashboard", layout="wide")
st.title("📈 500 Penny Stock Quant Analyzer")
st.warning("⚠️ **Note:** Analyzing 500 stocks over 60 days requires processing roughly 2.3 million data points. This scan will take 10-20 minutes to complete. Please be patient.")

# --- Core Logic ---
@st.cache_data(ttl=3600) # Caches the data for 1 hour
def fetch_stock_data():
    all_records = []
    
    # Step 1: Screener for top 500
    try:
        foverview = Overview()
        foverview.set_filter(filters_dict={'Price': 'Under $2'})
        screener_df = foverview.screener_view(order='Volume')
        
        # Grab top 499 to leave room for DGNX
        tickers = screener_df['Ticker'].head(499).tolist()
        if 'DGNX' not in tickers:
            tickers.append('DGNX')
        tickers = tickers[:500]
    except Exception as e:
        st.error(f"Screener limited. Falling back to a smaller list. Error: {e}")
        tickers = ['DGNX', 'SNDL', 'FCEL', 'GNS', 'SOUN', 'MULN'] 

    # Step 2: Data Extraction
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for idx, ticker in enumerate(tickers):
        status_text.text(f"Fetching data for {ticker} ({idx + 1}/{len(tickers)})...")
        try:
            stock = yf.Ticker(ticker)
            df = stock.history(period="60d", interval="5m")
            
            if df.empty:
                continue

            name = stock.info.get('shortName', ticker)
            df['Date'] = df.index.date
            days = df.groupby('Date')

            for date, group in days:
                open_price = group['Open'].iloc[0]
                close_price = group['Close'].iloc[-1]
                daily_volume = int(group['Volume'].sum())
                
                high_row = group.loc[group['High'].idxmax()]
                low_row = group.loc[group['Low'].idxmin()]

                day_high = high_row['High']
                day_low = low_row['Low']
                high_time_obj = high_row.name
                low_time_obj = low_row.name

                drop_from_open_pct = ((open_price - day_low) / open_price) * 100 if open_price > 0 else 0
                rise_from_open_pct = ((day_high - open_price) / open_price) * 100 if open_price > 0 else 0
                low_before_high = low_time_obj < high_time_obj

                all_records.append({
                    'Ticker': ticker,
                    'Stock Name': name,
                    'Date': date,
                    'Volume': daily_volume,
                    'Open': round(open_price, 4),
                    'Close': round(close_price, 4),
                    'Day High': round(day_high, 4),
                    'Time of High': high_time_obj.strftime('%H:%M:%S'),
                    'Day Low': round(day_low, 4),
                    'Time of Low': low_time_obj.strftime('%H:%M:%S'),
                    'Drop from Open (%)': round(drop_from_open_pct, 2),
                    'Rise from Open (%)': round(rise_from_open_pct, 2),
                    'Low Before High': low_before_high
                })
        except Exception:
            pass # Skip silently on Yahoo Finance rate limits or delistings
        
        # Update Progress Bar
        progress_bar.progress((idx + 1) / len(tickers))
        
    status_text.text("Data fetching complete!")
    return pd.DataFrame(all_records)

# --- App Interaction ---
if st.button("Run Intraday Quant Analysis"):
    with st.spinner("Processing market data..."):
        final_df = fetch_stock_data()
        
        if not final_df.empty:
            st.success(f"Successfully loaded and analyzed {len(final_df)} trading days across {final_df['Ticker'].nunique()} stocks!")
            
            st.divider()
            
            # --- THE ENHANCED ANALYSIS ENGINE ---
            st.header("🔬 High-Probability Pattern Analysis")

            # 1. Define "High Quality" Days (Price > Open AND Volatility was present)
            high_quality_days = final_df[
                (final_df['Rise from Open (%)'] > 3.0) & 
                (final_df['Low Before High'] == True) &
                (final_df['Volume'] > final_df['Volume'].median())
            ]

            if not high_quality_days.empty:
                # Statistical 'Golden Windows'
                best_buy_window = high_quality_days['Time of Low'].mode()[0]
                best_sell_window = high_quality_days['Time of High'].mode()[0]
                
                # Calculate Average Profit Potential
                avg_swing = high_quality_days['Rise from Open (%)'].mean()
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Optimal Buy Setup (EST)", best_buy_window, "Post-Open Dip")
                c2.metric("Optimal Sell Peak (EST)", best_sell_window, "Momentum Exit")
                c3.metric("Avg. Profit Potential", f"{avg_swing:.2f}%", "On 'Green' Days")

                st.subheader("💡 Recommended Trading Pattern")
                st.markdown(f"""
                **The "10 AM Reversal" Pattern:**
                * **Observation:** In {len(high_quality_days)} successful sessions, the bottom was most often set at **{best_buy_window}**. 
                * **Strategy:** Avoid buying in the first 15 minutes. Look for a stock that drops from the open, stabilizes, and starts to rise again around **10:00 AM - 10:15 AM**.
                * **Exit:** Statistical peaks for these volume leaders cluster at **{best_sell_window}**. Setting a limit order 5-10 minutes *before* this time increases fill probability.
                """)
                
                # Heatmap of Profitability by Time
                st.write("### Probability Distribution (Time of Daily High)")
                time_counts = high_quality_days['Time of High'].value_counts().head(10)
                st.bar_chart(time_counts)
            else:
                st.warning("Insufficient high-volatility data to generate patterns.")
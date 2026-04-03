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
            
            # --- THE ANALYSIS ENGINE ---
            st.header("🧠 Intraday Trading Insights")
            
            # Filter for "Tradable Days": Low happened before High, and stock moved up more than 2%
            tradable_days = final_df[(final_df['Low Before High'] == True) & (final_df['Rise from Open (%)'] > 2.0)]
            
            if not tradable_days.empty:
                best_buy = tradable_days['Time of Low'].mode()[0]
                best_sell = tradable_days['Time of High'].mode()[0]
                win_rate = (len(tradable_days) / len(final_df)) * 100
                
                col1, col2, col3 = st.columns(3)
                col1.metric("Optimal Historical Buy Time (EST)", best_buy, "Based on daily lows")
                col2.metric("Optimal Historical Sell Time (EST)", best_sell, "Based on daily highs")
                col3.metric("Ideal Setup Frequency", f"{win_rate:.1f}%", "Days where Low preceded High > 2%")
                
                st.info(f"**Analysis Conclusion:** Historically, over the last 60 days for these volume leaders, the most frequent intraday dip occurred at **{best_buy}**. The most frequent peak of the day occurred at **{best_sell}**. Note that this represents statistical frequency, not a guarantee of future movement.")
            else:
                st.warning("Not enough volatility data to calculate optimal times.")

            st.divider()

            # --- DATA DISPLAY ---
            st.header("Raw Dataset")
            display_df = final_df.copy()
            display_df['Volume'] = display_df['Volume'].apply(lambda x: f"{x:,}")
            st.dataframe(display_df, use_container_width=True)
            
            # Export
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                final_df.to_excel(writer, index=False, sheet_name='Quant Data')
            
            st.download_button(
                label="📥 Download Full Dataset as Excel",
                data=buffer.getvalue(),
                file_name="500_Stocks_Quant_Data.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.error("No data could be fetched. You may have hit an API limit.")
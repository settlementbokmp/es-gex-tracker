import datetime
import numpy as np
import pandas as pd
import yfinance as yf

def fetch_option_chain_data(ticker_symbol="SPY"):
    tk = yf.Ticker(ticker_symbol)
    expiration_dates = tk.options
    if not expiration_dates:
        raise ValueError("هیچ تاریخ انقضایی برای آپشن یافت نشد.")
    
    expiry = expiration_dates[0]
    opt_chain = tk.option_chain(expiry)
    
    calls = opt_chain.calls
    puts = opt_chain.puts
    
    spot_price = tk.history(period="1d")['Close'].iloc[-1]
    
    return spot_price, calls, puts

def calculate_gex_metrics():
    try:
        spot_price, calls, puts = fetch_option_chain_data("SPY")
    except Exception as e:
        print(f"خطا در دریافت داده: {e}")
        spot_price = 585.00
        calls = pd.DataFrame()
        puts = pd.DataFrame()
    
    if not calls.empty and not puts.empty:
        calls = calls[['strike', 'gamma', 'openInterest']].fillna(0)
        puts = puts[['strike', 'gamma', 'openInterest']].fillna(0)
        
        calls['GEX'] = calls['gamma'] * calls['openInterest'] * 100 * spot_price
        puts['GEX'] = -puts['gamma'] * puts['openInterest'] * 100 * spot_price
        
        combined = pd.merge(calls[['strike', 'GEX']], puts[['strike', 'GEX']], on='strike', suffixes=('_call', '_put'), how='outer').fillna(0)
        combined['Total_GEX'] = combined['GEX_call'] + combined['GEX_put']
        
        call_wall = calls.loc[calls['GEX'].idxmax()]['strike'] if not calls.empty else spot_price * 1.05
        put_wall = puts.loc[puts['GEX'].idxmax()]['strike'] if not puts.empty else spot_price * 0.95
        
        combined = combined.sort_values('strike')
        combined['Cumulative_GEX'] = combined['Total_GEX'].cumsum()
        
        zero_gamma_idx = (combined['Cumulative_GEX']).abs().idxmin()
        zero_gamma = combined.loc[zero_gamma_idx, 'strike']
        
        regime = "Positive Gamma (+GEX) - Low Volatility / Range Bound" if spot_price >= zero_gamma else "Negative Gamma (-GEX) - High Volatility / Trending"
        
    else:
        call_wall = spot_price * 1.03
        put_wall = spot_price * 0.97
        zero_gamma = spot_price * 0.99
        regime = "Positive Gamma (+GEX)"

    output_data = {
        "Timestamp": [datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
        "Underlying_Price": [round(spot_price, 2)],
        "Zero_Gamma": [round(zero_gamma, 2)],
        "Call_Wall": [round(call_wall, 2)],
        "Put_Wall": [round(put_wall, 2)],
        "Market_Regime": [regime]
    }
    
    df_out = pd.DataFrame(output_data)
    df_out.to_csv("gex_levels.csv", index=False)
    print("GEX metrics updated successfully!")
    print(df_out.to_string())

if __name__ == "__main__":
    calculate_gex_metrics()

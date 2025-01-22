from tradingview_ta import TA_Handler, Interval
import time

# Function to fetch technical analysis data
def get_technical_analysis(asset, interval):
    handler = TA_Handler(
        symbol=asset,
        exchange="FX_IDC",  # Use "FX_IDC" for forex pairs
        screener="forex",
        interval=interval,
        timeout=10
    )
    analysis = handler.get_analysis()
    return analysis

# Function to generate buy/sell signals
def generate_signal(analysis):
    # Example: Simple Moving Average Crossover
    short_ma = analysis.indicators["EMA10"]  # 10-period EMA
    long_ma = analysis.indicators["EMA20"]  # 20-period EMA

    if short_ma > long_ma:
        return "buy"
    elif short_ma < long_ma:
        return "sell"
    else:
        return "hold"

# Main trading loop
print("Starting trading bot...")
while True:
    try:
        # Set trading parameters
        asset = "EURUSD"  # Asset to monitor
        interval = Interval.INTERVAL_1_MINUTE  # Timeframe for analysis

        # Fetch technical analysis data
        analysis = get_technical_analysis(asset, interval)

        # Generate buy/sell signal
        signal = generate_signal(analysis)
        print(f"Signal: {signal} (Asset: {asset}, Time: {time.strftime('%Y-%m-%d %H:%M:%S')})")

        # Wait before the next iteration
        time.sleep(60)  # Check every 1 minute

    except Exception as e:
        print(f"An error occurred: {e}")
        break
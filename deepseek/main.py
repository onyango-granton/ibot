from iqoptionapi.stable_api import IQ_Option
import time

# Replace with your IQ Option credentials
email = "grantononyango@gmail.com"
password = "0724600680@Gt"

# Connect to IQ Option
print("Connecting to IQ Option...")
iq = IQ_Option(email, password)
iq.connect()

# Check if connection is successful
if iq.check_connect():
    print("Connected successfully!")
else:
    print("Connection failed. Check your credentials or network connection.")
    exit()

# Set trading parameters
asset = "GBPCHF-OTC"  # Asset to trade
amount = 10       # Amount to invest per trade
expiration_time = 1  # Expiration time in minutes
trade_type = "binary"  # "binary" or "digital"

# Function to check if an asset is open for trading
def is_asset_open(asset, trade_type):
    open_time = iq.get_all_open_time()
    return open_time[trade_type][asset]['open']

# Function to fetch historical data
def get_historical_data(asset, interval, count):
    candles = iq.get_candles(asset, interval, count, time.time())
    return [candle['close'] for candle in candles]

# Function to calculate moving averages
def calculate_moving_averages(data, short_window, long_window):
    short_ma = sum(data[-short_window:]) / short_window
    long_ma = sum(data[-long_window:]) / long_window
    return short_ma, long_ma

# Function to place a trade
def place_trade(action, amount, asset, trade_type, expiration_time):
    if action == "buy":
        trade_id = iq.buy(amount, asset, "call", expiration_time)
    elif action == "sell":
        trade_id = iq.buy(amount, asset, "put", expiration_time)
    else:
        return None

    return trade_id

# Main trading loop
print("Starting trading bot...")
while True:
    try:
        # Check if the asset is open for trading
        if is_asset_open(asset, trade_type):
            # Fetch historical data (e.g., last 50 candles with 1-minute interval)
            historical_data = get_historical_data(asset, 60, 50)

            # Calculate moving averages
            short_window = 10
            long_window = 20
            short_ma, long_ma = calculate_moving_averages(historical_data, short_window, long_window)

            # Generate buy/sell signals
            if short_ma > long_ma:
                print("Buy signal generated!")
                trade_result = place_trade("buy", amount, asset, trade_type, expiration_time)
            elif short_ma < long_ma:
                print("Sell signal generated!")
                trade_result = place_trade("sell", amount, asset, trade_type, expiration_time)
            else:
                print("No signal. Waiting...")
                trade_result = None

            # Check if the trade was successful
            if trade_result:
                if trade_result[0] is False:
                    print(f"Trade failed: {trade_result[1]}")
                    if "active is suspended" in trade_result[1]:
                        print(f"{asset} is currently suspended. Retrying later...")
                else:
                    print(f"Trade placed successfully! Trade ID: {trade_result}")
        else:
            print(f"{asset} is currently suspended. Retrying later...")

        # Wait before the next iteration
        time.sleep(60)  # Check every 1 minute

    except Exception as e:
        print(f"An error occurred: {e}")
        break

# Disconnect from IQ Option
print("Disconnecting from IQ Option...")
iq.disconnect()
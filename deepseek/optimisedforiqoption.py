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
asset = "EURUSD"  # Asset to monitor
expiration_time = 1  # Expiration time in minutes (1 minute for binary options)

# Function to fetch the current market price
def get_current_price(asset):
    candles = iq.get_candles(asset, 60, 1, time.time())  # 1-minute candles
    if candles:
        return candles[0]['close']  # Latest closing price
    else:
        return None

# Function to calculate moving averages
def calculate_moving_average(prices, window):
    if len(prices) >= window:
        return sum(prices[-window:]) / window
    else:
        return None

# Function to generate buy/sell signals
def generate_signal(prices):
    # Example: Simple Moving Average Crossover
    short_window = 10
    long_window = 20

    short_ma = calculate_moving_average(prices, short_window)
    long_ma = calculate_moving_average(prices, long_window)

    if short_ma is not None and long_ma is not None:
        if short_ma > long_ma:
            return "buy"
        elif short_ma < long_ma:
            return "sell"
    return "hold"

# Main trading loop
print("Starting trading bot for 1-minute binary options...")
prices = []  # Store historical prices for analysis

while True:
    try:
        # Fetch the current market price
        current_price = get_current_price(asset)
        if current_price is not None:
            prices.append(current_price)  # Add the latest price to the list

            # Generate buy/sell signal
            signal = generate_signal(prices)
            print(f"Signal: {signal} (Asset: {asset}, Price: {current_price}, Time: {time.strftime('%Y-%m-%d %H:%M:%S')})")

            # Keep the list size manageable (e.g., last 50 prices)
            if len(prices) > 50:
                prices.pop(0)
        else:
            print("Failed to fetch the current price.")

        # Wait before the next iteration
        time.sleep(60)  # Check every 1 minute

    except Exception as e:
        print(f"An error occurred: {e}")
        break

# Disconnect from IQ Option
print("Disconnecting from IQ Option...")
iq.disconnect()
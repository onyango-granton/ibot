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

# Initialize variables to track accuracy
total_signals = 0
correct_signals = 0

# Open a log file to write outputs
log_file = open("trading_log.txt", "a")  # Append mode
log_file.write("\n--- New Trading Session ---\n")

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
            current_time = time.strftime('%Y-%m-%d %H:%M:%S')  # Correct timestamp
            log_message = f"Signal: {signal} (Asset: {asset}, Price: {current_price}, Time: {current_time})\n"
            print(log_message.strip())  # Print to console
            log_file.write(log_message)  # Write to log file

            # If the signal is buy or sell, wait for the trade to expire
            if signal in ["buy", "sell"]:
                total_signals += 1
                entry_price = current_price

                # Wait for the trade to expire (1 minute)
                time.sleep(60)

                # Fetch the price at expiration
                expiration_price = get_current_price(asset)
                if expiration_price is not None:
                    # Determine if the signal was correct
                    if signal == "buy" and expiration_price > entry_price:
                        correct_signals += 1
                    elif signal == "sell" and expiration_price < entry_price:
                        correct_signals += 1

                    # Calculate accuracy
                    accuracy = (correct_signals / total_signals) * 100 if total_signals > 0 else 0
                    outcome_message = (
                        f"Trade Outcome: Entry Price = {entry_price}, Expiration Price = {expiration_price}\n"
                        f"Accuracy: {accuracy:.2f}% (Correct: {correct_signals}, Total: {total_signals})\n"
                    )
                    print(outcome_message.strip())  # Print to console
                    log_file.write(outcome_message)  # Write to log file
                else:
                    error_message = "Failed to fetch the expiration price.\n"
                    print(error_message.strip())  # Print to console
                    log_file.write(error_message)  # Write to log file

            # Keep the list size manageable (e.g., last 50 prices)
            if len(prices) > 50:
                prices.pop(0)
        else:
            error_message = "Failed to fetch the current price.\n"
            print(error_message.strip())  # Print to console
            log_file.write(error_message)  # Write to log file

        # Wait before the next iteration
        time.sleep(60)  # Check every 1 minute

    except Exception as e:
        error_message = f"An error occurred: {e}\n"
        print(error_message.strip())  # Print to console
        log_file.write(error_message)  # Write to log file
        break

# Disconnect from IQ Option
print("Disconnecting from IQ Option...")
iq.disconnect()

# Close the log file
log_file.write("--- End of Trading Session ---\n")
log_file.close()
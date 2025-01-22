from iqoptionapi.stable_api import IQ_Option

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

# Check if EUR/USD is open for binary options trading
asset = "EURUSD"
open_time = iq.get_all_open_time()
is_open = open_time["binary"][asset]["open"]

if is_open:
    print(f"{asset} is open for trading.")
else:
    print(f"{asset} is currently closed for trading.")

# Disconnect (optional, as the script will exit)
print("Exiting script.")
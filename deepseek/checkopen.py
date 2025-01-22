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

# Function to get active assets
def get_active_assets(trade_type="binary"):
    # Fetch the status of all assets
    open_time = iq.get_all_open_time()

    # Filter assets that are open for trading
    active_assets = []
    for asset, status in open_time[trade_type].items():
        if status['open']:
            active_assets.append(asset)

    return active_assets

# Get active assets for binary options
active_binary_assets = get_active_assets("binary")
print("Active Binary Options Assets:")
print(active_binary_assets)

# Get active assets for digital options
active_digital_assets = get_active_assets("digital")
print("Active Digital Options Assets:")
print(active_digital_assets)

# Disconnect from IQ Option
print("Disconnecting from IQ Option...")
iq.disconnect()
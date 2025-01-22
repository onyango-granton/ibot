from iqoptionapi.stable_api import IQ_Option
import time

# Login credentials
USERNAME = "grantononyango@gmail.com"
PASSWORD = "0724600680@Gt"

# Connect to IQ Option
iq = IQ_Option(USERNAME, PASSWORD)
iq.connect()

# Check if connected
if iq.check_connect():
    print("Connected to IQ Option")
else:
    print("Failed to connect. Check your credentials.")
    exit()

# Get available instruments for binary options
def get_binary_pairs():
    # Fetch available assets
    all_assets = iq.get_all_open_time()
    binary_assets = all_assets['binary']
    
    print("Available Binary Pairs:")
    for pair, info in binary_assets.items():
        if info['open']:
            print(f"{pair} - Active")
        else:
            print(f"{pair} - Inactive")


get_binary_pairs()

all_assets = iq.get_all_open_time()
print(all_assets)

# Disconnect
iq.disconnect()

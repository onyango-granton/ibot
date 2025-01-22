import numpy as np
import pandas as pd
import websockets
import json
import asyncio
import logging

class DerivTradingBot:import requests
import websocket
import json

# IQ Option API URL
API_URL = "https://api.iqoption.com/api"

# Authenticate
session = requests.Session()
session.auth = ('your_email', 'your_password')
response = session.get(f"{API_URL}/login")
print(response.json())

# WebSocket for real-time data
def on_message(ws, message):
    data = json.loads(message)
    print(data)
    # Implement your trading strategy here
    action = trading_strategy(data)
    if action in ["buy", "sell"]:
        place_trade(action, 10)  # Place a trade with $10

def on_error(ws, error):
    print(error)

def on_close(ws):
    print("### closed ###")

def on_open(ws):
    print("### opened ###")

websocket.enableTrace(True)
ws = websocket.WebSocketApp("wss://iqoption.com/echo/websocket",
                          on_message = on_message,
                          on_error = on_error,
                          on_close = on_close)
ws.on_open = on_open
ws.run_forever()

# Trading strategy
def trading_strategy(data):
    # Example: Simple Moving Average Crossover
    short_window = 10
    long_window = 50

    short_ma = sum(data[-short_window:]) / short_window
    long_ma = sum(data[-long_window:]) / long_window

    if short_ma > long_ma:
        return "buy"
    elif short_ma < long_ma:
        return "sell"
    else:
        return "hold"

# Place a trade
def place_trade(action, amount):
    trade_url = f"{API_URL}/trade"
    payload = {
        "action": action,
        "amount": amount,
        "asset": "EURUSD",
        "type": "binary"  # or "digital" depending on your preference
    }
    response = session.post(trade_url, json=payload)
    print(response.json())
    def __init__(self, api_key):
        self.api_key = api_key
        self.ws_url = "wss://ws.binaryws.com/websockets/v3?app_id=" + api_key
        
        self.config = {
            'market': 'synthetic_index',
            'underlying': 'random_index',
            'symbol': '1HZ10V',
            'contract_type': 'callput',
            'duration': 60,  # 60 seconds
            'stake': 1,
            'until_condition': 'win',
            'default_action': 'CALL'
        }
        
        # Trading parameters
        self.bb_period = 20
        self.bb_std = 2
        self.stoch_k_period = 5
        self.stoch_d_period = 3
        self.smooth_period = 3
        self.price_history = []
        
    def calculate_stochastic(self, df, high_col='high', low_col='low', close_col='price',
                           k_period=14, d_period=3, smooth_k=3):
        """Calculate Stochastic Oscillator"""
        df['highest_high'] = df[high_col].rolling(window=k_period).max()
        df['lowest_low'] = df[low_col].rolling(window=k_period).min()
        
        df['%K'] = 100 * (df[close_col] - df['lowest_low']) / (df['highest_high'] - df['lowest_low'])
        
        if smooth_k > 1:
            df['%K'] = df['%K'].rolling(window=smooth_k).mean()
        
        df['%D'] = df['%K'].rolling(window=d_period).mean()
        df = df.drop(['highest_high', 'lowest_low'], axis=1)
        
        return df

    def calculate_indicators(self):
        """Calculate indicators from price history"""
        if len(self.price_history) < self.bb_period:
            return None
            
        df = pd.DataFrame(self.price_history)
        
        # Calculate Bollinger Bands
        df['bb_middle'] = df['price'].rolling(window=self.bb_period).mean()
        std = df['price'].rolling(window=self.bb_period).std()
        df['bb_upper'] = df['bb_middle'] + (std * self.bb_std)
        df['bb_lower'] = df['bb_middle'] - (std * self.bb_std)
        
        # Calculate high/low for Stochastic
        df['high'] = df['price'].rolling(window=self.stoch_k_period).max()
        df['low'] = df['price'].rolling(window=self.stoch_k_period).min()
        
        # Calculate Stochastic
        df = self.calculate_stochastic(
            df,
            k_period=self.stoch_k_period,
            d_period=self.stoch_d_period,
            smooth_k=self.smooth_period
        )
        
        return df

    async def process_tick(self, tick_data):
        """Process each new tick and generate trading signals"""
        if 'tick' not in tick_data:
            return
            
        tick = tick_data['tick']
        self.price_history.append({
            'timestamp': tick['epoch'],
            'price': tick['quote']
        })
        
        df = self.calculate_indicators()
        if df is None or df.empty:
            return
            
        current_price = tick['quote']
        last_row = df.iloc[-1]
        
        if (last_row['%K'] < 20 and last_row['%D'] < 20 and
            current_price < last_row['bb_lower']):
            await self.place_trade('CALL')
            
        elif (last_row['%K'] > 80 and last_row['%D'] > 80 and
              current_price > last_row['bb_upper']):
            await self.place_trade('PUT')

    async def place_trade(self, direction, websocket):
        """Execute trade on Deriv platform"""
        contract_request = {
            "proposal": 1,
            "amount": self.config['stake'],
            "barrier": None,
            "basis": "stake",
            "contract_type": direction,
            "currency": "USD",
            "duration": self.config['duration'],
            "duration_unit": "s",
            "symbol": self.config['symbol']
        }
        
        try:
            await websocket.send(json.dumps(contract_request))
            response = await websocket.recv()
            response_data = json.loads(response)
            
            if 'proposal' in response_data:
                buy_request = {
                    "buy": 1,
                    "price": response_data['proposal']['ask_price'],
                    "proposal": response_data['proposal']['id']
                }
                await websocket.send(json.dumps(buy_request))
                result = await websocket.recv()
                result_data = json.loads(result)
                if 'buy' in result_data:
                    print(f"Trade executed: {direction} at {result_data['buy']['buy_price']}")
        except Exception as e:
            print(f"Error placing trade: {e}")

    async def run(self):
        """Main method to run the trading bot"""
        async with websockets.connect(self.ws_url) as websocket:
            # Subscribe to ticks
            ticks_request = {
                "ticks": self.config['symbol'],
                "subscribe": 1
            }
            await websocket.send(json.dumps(ticks_request))
            
            print(f"Bot started - Trading {self.config['symbol']}")
            
            try:
                while True:
                    response = await websocket.recv()
                    data = json.loads(response)
                    
                    if 'tick' in data:
                        await self.process_tick(data)
                    elif 'error' in data:
                        print(f"Error received: {data['error']['message']}")
                        
            except websockets.exceptions.ConnectionClosed:
                print("Connection closed")
            except Exception as e:
                print(f"Error in main loop: {e}")

async def main():
    # Initialize logging
    logging.basicConfig(level=logging.INFO)
    
    # Replace with your actual API key from Deriv
    api_key = "9otNvRBFoONROBX"
    
    bot = DerivTradingBot(api_key)
    await bot.run()

if __name__ == "__main__":
    asyncio.run(main())
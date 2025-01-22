import numpy as np
import pandas as pd
import websockets
import json
import asyncio
import logging
from datetime import datetime

class DerivTradingBot:
    def __init__(self, app_id, api_token):
        self.app_id = app_id
        self.api_token = api_token
        self.ws_url = f"wss://ws.binaryws.com/websockets/v3?app_id={app_id}"
        
        self.config = {
            'market': 'synthetic_index',
            'underlying': 'random_index',
            'symbol': '1HZ10V',
            'contract_type': 'callput',
            'duration': 60,
            'stake': 1,
            'until_condition': 'win',
            'default_action': 'CALL'
        }
        
        self.bb_period = 20
        self.bb_std = 2
        self.stoch_k_period = 5
        self.stoch_d_period = 3
        self.smooth_period = 3
        self.price_history = []
        self.last_price = None

    async def authenticate(self, websocket):
        auth_request = {
            "authorize": self.api_token
        }
        await websocket.send(json.dumps(auth_request))
        response = await websocket.recv()
        auth_response = json.loads(response)
        
        if 'error' in auth_response:
            raise Exception(f"Authentication failed: {auth_response['error']['message']}")
        
        return auth_response.get('authorize')

    async def process_tick(self, tick_data):
        """Process and display incoming tick data"""
        current_price = tick_data['tick']['quote']
        timestamp = datetime.fromtimestamp(tick_data['tick']['epoch']).strftime('%H:%M:%S')
        
        # Calculate price change
        if self.last_price is not None:
            price_change = current_price - self.last_price
            direction = "↑" if price_change > 0 else "↓" if price_change < 0 else "→"
            logging.info(f"Time: {timestamp} | Price: {current_price:.5f} | Change: {direction} {abs(price_change):.5f}")
        else:
            logging.info(f"Time: {timestamp} | Price: {current_price:.5f} | Initial tick")
        
        self.last_price = current_price
        self.price_history.append(current_price)
        
        # Keep only the last 100 prices to avoid memory issues
        if len(self.price_history) > 100:
            self.price_history.pop(0)

    async def run(self):
        try:
            async with websockets.connect(self.ws_url) as websocket:
                logging.info("Connecting to Deriv API...")
                
                auth_response = await self.authenticate(websocket)
                if not auth_response:
                    logging.error("Authentication failed!")
                    return
                
                logging.info(f"Successfully authenticated with account id: {auth_response.get('account_id')}")
                
                # Subscribe to ticks
                ticks_request = {
                    "ticks": self.config['symbol'],
                    "subscribe": 1
                }
                await websocket.send(json.dumps(ticks_request))
                logging.info(f"Subscribed to {self.config['symbol']} ticks")
                logging.info("\nMonitoring price movements...")
                logging.info("-" * 60)
                
                while True:
                    try:
                        response = await websocket.recv()
                        data = json.loads(response)
                        
                        if 'tick' in data:
                            await self.process_tick(data)
                        elif 'error' in data:
                            logging.error(f"Error received: {data['error']['message']}")
                            if data['error']['code'] == 'InvalidToken':
                                logging.error("Invalid API token. Please check your credentials.")
                                break
                    except websockets.exceptions.ConnectionClosed:
                        logging.warning("Connection closed unexpectedly. Attempting to reconnect...")
                        break
                    
        except websockets.exceptions.InvalidStatusCode as e:
            logging.error(f"Failed to connect: Invalid status code {e}")
            logging.error("Please check your app ID and API token and ensure they have proper permissions.")
        except Exception as e:
            logging.error(f"An error occurred: {e}")

async def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Replace these with your actual credentials from Deriv
    app_id = "67456"  # ← Replace this!
    api_token = "lSjydstL5UK4BWz"  # ← Replace this!
    
    while True:
        try:
            bot = DerivTradingBot(app_id, api_token)
            await bot.run()
            
            logging.info("Waiting 5 seconds before reconnecting...")
            await asyncio.sleep(5)
        except Exception as e:
            logging.error(f"Bot crashed with error: {e}")
            logging.info("Restarting in 5 seconds...")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())
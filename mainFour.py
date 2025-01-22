import numpy as np
import pandas as pd
import websockets
import json
import asyncio
import logging

class DerivTradingBot:
    def __init__(self, app_id, api_token):
        self.app_id = app_id
        self.api_token = api_token
        # Separate app_id in URL and use api_token for authentication
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
        
        # Trading parameters
        self.bb_period = 20
        self.bb_std = 2
        self.stoch_k_period = 5
        self.stoch_d_period = 3
        self.smooth_period = 3
        self.price_history = []

    async def authenticate(self, websocket):
        """Authenticate with the Deriv API using the API token"""
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
        """Process incoming tick data"""
        # Add your tick processing logic here
        price = tick_data['tick']['quote']
        self.price_history.append(price)
        # Add your trading strategy implementation here
        pass

    async def run(self):
        """Main method to run the trading bot"""
        try:
            async with websockets.connect(self.ws_url) as websocket:
                logging.info("Connecting to Deriv API...")
                
                # Authenticate first
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
    # Set up logging
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
            
            # Wait before attempting to reconnect
            logging.info("Waiting 5 seconds before reconnecting...")
            await asyncio.sleep(5)
        except Exception as e:
            logging.error(f"Bot crashed with error: {e}")
            logging.info("Restarting in 5 seconds...")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())
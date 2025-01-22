import numpy as np
import pandas as pd
import websockets
import json
import asyncio
import logging

class DerivTradingBot:
    def __init__(self, api_key):
        self.api_key = api_key
        # Updated WebSocket URL format
        self.ws_url = f"wss://ws.binaryws.com/websockets/v3?app_id={api_key}"
        
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
        
        # Trading parameters remain the same
        self.bb_period = 20
        self.bb_std = 2
        self.stoch_k_period = 5
        self.stoch_d_period = 3
        self.smooth_period = 3
        self.price_history = []

    async def authenticate(self, websocket):
        """Authenticate with the Deriv API"""
        auth_request = {
            "authorize": self.api_key
        }
        await websocket.send(json.dumps(auth_request))
        response = await websocket.recv()
        auth_response = json.loads(response)
        
        if 'error' in auth_response:
            raise Exception(f"Authentication failed: {auth_response['error']['message']}")
        
        return auth_response.get('authorize')

    async def run(self):
        """Main method to run the trading bot"""
        try:
            async with websockets.connect(self.ws_url) as websocket:
                print("Connecting to Deriv API...")
                
                # Authenticate first
                auth_response = await self.authenticate(websocket)
                if not auth_response:
                    print("Authentication failed!")
                    return
                
                print("Successfully authenticated!")
                
                # Subscribe to ticks
                ticks_request = {
                    "ticks": self.config['symbol'],
                    "subscribe": 1
                }
                await websocket.send(json.dumps(ticks_request))
                print(f"Subscribed to {self.config['symbol']} ticks")
                
                while True:
                    try:
                        response = await websocket.recv()
                        data = json.loads(response)
                        
                        if 'tick' in data:
                            await self.process_tick(data)
                        elif 'error' in data:
                            print(f"Error received: {data['error']['message']}")
                            if data['error']['code'] == 'InvalidToken':
                                print("Invalid API token. Please check your API key.")
                                break
                    except websockets.exceptions.ConnectionClosed:
                        print("Connection closed unexpectedly. Attempting to reconnect...")
                        break
                    
        except websockets.exceptions.InvalidStatusCode as e:
            print(f"Failed to connect: Invalid status code {e}")
            print("Please check your API key and ensure it has proper permissions.")
        except Exception as e:
            print(f"An error occurred: {e}")

async def main():
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Replace this with your actual API key from Deriv
    api_key = "YOUR API TOKEN"  # ← Replace this!
    
    while True:
        try:
            bot = DerivTradingBot(api_key)
            await bot.run()
            
            # Wait before attempting to reconnect
            print("Waiting 5 seconds before reconnecting...")
            await asyncio.sleep(5)
        except Exception as e:
            print(f"Bot crashed with error: {e}")
            print("Restarting in 5 seconds...")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())
import numpy as np
import pandas as pd
import websockets
import json
import asyncio
import logging
from datetime import datetime
import csv
import os

class DerivTradingBot:
    def __init__(self, app_id, api_token):
        self.app_id = app_id
        self.api_token = api_token
        self.ws_url = f"wss://ws.binaryws.com/websockets/v3?app_id={app_id}"
        
        # Setup file logging
        self.trades_file = 'trades_log.csv'
        self.setup_csv_file()
        
        self.config = {
            'market': 'synthetic_index',
            'underlying': 'random_index',
            'symbol': '1HZ10V',
            'contract_type': 'CALL',
            'duration': 60,
            'duration_unit': 's',
            'stake': 1.00,
            'basis': 'stake',
            'currency': 'USD'
        }
        
        self.bb_period = 20
        self.bb_std = 2
        self.price_history = []
        self.last_price = None
        self.in_trade = False
        self.trade_count = 0
        self.max_trades = 10
        self.current_contract_id = None

    def setup_csv_file(self):
        """Set up CSV file for logging trades"""
        if not os.path.exists(self.trades_file):
            with open(self.trades_file, 'w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow([
                    'Timestamp',
                    'Contract ID',
                    'Type',
                    'Entry Price',
                    'Exit Price',
                    'Profit/Loss',
                    'Status'
                ])

    def log_trade(self, contract_id, trade_type, entry_price, exit_price=None, profit_loss=None, status="OPEN"):
        """Log trade to CSV file"""
        with open(self.trades_file, 'a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                contract_id,
                trade_type,
                entry_price,
                exit_price,
                profit_loss,
                status
            ])

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

    async def subscribe_to_contract(self, websocket, contract_id):
        proposal_request = {
            "proposal_open_contract": 1,
            "contract_id": contract_id,
            "subscribe": 1
        }
        await websocket.send(json.dumps(proposal_request))
        logging.info(f"To track this trade on Deriv terminal, use Contract ID: {contract_id}")

    async def place_trade(self, websocket, action):
        if self.in_trade or self.trade_count >= self.max_trades:
            return

        contract_type = "CALL" if action == "buy" else "PUT"
        
        proposal_request = {
            "proposal": 1,
            "amount": self.config['stake'],
            "basis": self.config['basis'],
            "contract_type": contract_type,
            "currency": self.config['currency'],
            "duration": self.config['duration'],
            "duration_unit": self.config['duration_unit'],
            "symbol": self.config['symbol']
        }

        try:
            await websocket.send(json.dumps(proposal_request))
            proposal_response = await websocket.recv()
            proposal_data = json.loads(proposal_response)

            if 'error' in proposal_data:
                logging.error(f"Proposal error: {proposal_data['error']['message']}")
                return

            if 'proposal' in proposal_data:
                buy_request = {
                    "buy": proposal_data['proposal']['id'],
                    "price": self.config['stake']
                }
                
                await websocket.send(json.dumps(buy_request))
                buy_response = await websocket.recv()
                buy_data = json.loads(buy_response)

                if 'buy' in buy_data:
                    self.in_trade = True
                    self.trade_count += 1
                    self.current_contract_id = buy_data['buy']['contract_id']
                    
                    # Log the new trade
                    self.log_trade(
                        contract_id=self.current_contract_id,
                        trade_type=contract_type,
                        entry_price=self.last_price
                    )
                    
                    logging.info(f"Trade #{self.trade_count} placed: {contract_type} at {self.last_price}")
                    logging.info(f"Contract ID: {self.current_contract_id} (Use this ID to track on Deriv terminal)")
                    
                    await self.subscribe_to_contract(websocket, self.current_contract_id)
                elif 'error' in buy_data:
                    logging.error(f"Buy error: {buy_data['error']['message']}")

        except Exception as e:
            logging.error(f"Error placing trade: {e}")

    def should_trade(self):
        if len(self.price_history) < self.bb_period:
            return None

        prices = np.array(self.price_history)
        sma = np.mean(prices[-self.bb_period:])
        std = np.std(prices[-self.bb_period:])
        upper_band = sma + (self.bb_std * std)
        lower_band = sma - (self.bb_std * std)

        current_price = self.last_price

        if current_price < lower_band:
            return "buy"
        elif current_price > upper_band:
            return "sell"
        
        return None

    async def process_tick(self, tick_data, websocket):
        current_price = tick_data['tick']['quote']
        timestamp = datetime.fromtimestamp(tick_data['tick']['epoch']).strftime('%H:%M:%S')
        
        if self.last_price is not None:
            price_change = current_price - self.last_price
            direction = "↑" if price_change > 0 else "↓" if price_change < 0 else "→"
            logging.info(f"Time: {timestamp} | Price: {current_price:.5f} | Change: {direction} {abs(price_change):.5f}")
        else:
            logging.info(f"Time: {timestamp} | Price: {current_price:.5f} | Initial tick")
        
        self.last_price = current_price
        self.price_history.append(current_price)
        
        if len(self.price_history) > self.bb_period * 2:
            self.price_history.pop(0)

        if not self.in_trade:
            action = self.should_trade()
            if action:
                await self.place_trade(websocket, action)

    async def run(self):
        try:
            async with websockets.connect(self.ws_url) as websocket:
                logging.info("Connecting to Deriv API...")
                
                auth_response = await self.authenticate(websocket)
                if not auth_response:
                    logging.error("Authentication failed!")
                    return
                
                logging.info(f"Successfully authenticated with account id: {auth_response.get('account_id')}")
                
                ticks_request = {
                    "ticks": self.config['symbol'],
                    "subscribe": 1
                }
                await websocket.send(json.dumps(ticks_request))
                logging.info(f"Subscribed to {self.config['symbol']} ticks")
                logging.info("\nMonitoring price movements and trading...")
                logging.info("-" * 60)
                
                while True:
                    try:
                        response = await websocket.recv()
                        data = json.loads(response)
                        
                        if 'tick' in data:
                            await self.process_tick(data, websocket)
                        elif 'proposal_open_contract' in data:
                            contract_data = data['proposal_open_contract']
                            if contract_data['is_sold']:
                                profit = contract_data['profit']
                                exit_price = contract_data['sell_price']
                                
                                # Update the trade log with completed trade info
                                self.log_trade(
                                    contract_id=self.current_contract_id,
                                    trade_type=contract_data['contract_type'],
                                    entry_price=contract_data['entry_tick'],
                                    exit_price=exit_price,
                                    profit_loss=profit,
                                    status="CLOSED"
                                )
                                
                                logging.info(f"Trade completed! Contract ID: {self.current_contract_id}")
                                logging.info(f"Profit/Loss: {profit}")
                                self.in_trade = False
                                self.current_contract_id = None
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
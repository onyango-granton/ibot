import numpy as np
import pandas as pd
import websockets
import json
import asyncio
import logging
from datetime import datetime
from typing import List, Optional

class DerivTradingBot:
    def __init__(self, app_id, api_token):
        self.app_id = app_id
        self.api_token = api_token
        self.ws_url = f"wss://ws.binaryws.com/websockets/v3?app_id={app_id}"
        
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
        
        # Technical Analysis Parameters
        self.bb_period = 20
        self.bb_std = 2
        self.rsi_period = 14
        self.rsi_overbought = 70
        self.rsi_oversold = 30
        self.ema_short = 9
        self.ema_medium = 21
        self.ema_long = 50
        self.atr_period = 14
        self.min_volume_threshold = 0.5  # Minimum volume multiplier of average volume
        
        # Price and indicator storage
        self.price_history: List[float] = []
        self.volume_history: List[float] = []
        self.last_price: Optional[float] = None
        self.in_trade = False
        self.trade_count = 0
        self.max_trades = 10
        self.current_contract_id = None
        
        # Trading performance metrics
        self.wins = 0
        self.losses = 0
        self.total_profit = 0
        
        # Risk management
        self.max_daily_loss = -5.00  # Maximum daily loss in currency units
        self.trailing_stop_pips = 10  # Trailing stop in pips
        self.risk_reward_ratio = 2.0  # Minimum risk-reward ratio for trades

# [Previous imports and initial class definition remain the same until the authenticate method]

    async def authenticate(self, websocket):
        """Authenticate with the Deriv API"""
        auth_request = {
            "authorize": self.api_token
        }
        await websocket.send(json.dumps(auth_request))
        response = await websocket.recv()
        auth_response = json.loads(response)
        
        if 'error' in auth_response:
            raise Exception(f"Authentication failed: {auth_response['error']['message']}")
        
        return auth_response.get('authorize')

    async def place_trade(self, websocket, action):
        """Place a trade with Deriv"""
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
            # Request proposal
            await websocket.send(json.dumps(proposal_request))
            proposal_response = await websocket.recv()
            proposal_data = json.loads(proposal_response)

            if 'error' in proposal_data:
                logging.error(f"Proposal error: {proposal_data['error']['message']}")
                return

            # Buy contract
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
                    logging.info(f"Trade #{self.trade_count} placed: {contract_type} at {self.last_price}")
                    
                    # Subscribe to contract updates
                    await self.subscribe_to_contract(websocket, self.current_contract_id)
                elif 'error' in buy_data:
                    logging.error(f"Buy error: {buy_data['error']['message']}")

        except Exception as e:
            logging.error(f"Error placing trade: {e}")

    async def subscribe_to_contract(self, websocket, contract_id):
        """Subscribe to contract updates"""
        proposal_request = {
            "proposal_open_contract": 1,
            "contract_id": contract_id,
            "subscribe": 1
        }
        await websocket.send(json.dumps(proposal_request))

# [Rest of the previous code remains the same]

    def calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """Calculate Relative Strength Index"""
        if len(prices) < period + 1:
            return 50  # Default to neutral if not enough data
            
        deltas = np.diff(prices)
        seed = deltas[:period+1]
        up = seed[seed >= 0].sum()/period
        down = -seed[seed < 0].sum()/period
        rs = up/down if down != 0 else 0
        return 100 - (100/(1+rs))

    def calculate_ema(self, prices: List[float], period: int) -> float:
        """Calculate Exponential Moving Average"""
        prices_array = np.array(prices)
        weights = np.exp(np.linspace(-1., 0., period))
        weights /= weights.sum()
        
        if len(prices) < period:
            return prices[-1]  # Return last price if not enough data
            
        ema = np.convolve(prices_array, weights, mode='valid')[-1]
        return ema

    def calculate_atr(self, highs: List[float], lows: List[float], closes: List[float], period: int) -> float:
        """Calculate Average True Range"""
        if len(highs) < period + 1:
            return 0
            
        true_ranges = []
        for i in range(1, len(closes)):
            true_range = max(
                highs[i] - lows[i],  # Current high - current low
                abs(highs[i] - closes[i-1]),  # Current high - previous close
                abs(lows[i] - closes[i-1])  # Current low - previous close
            )
            true_ranges.append(true_range)
            
        return np.mean(true_ranges[-period:])

    def calculate_volume_profile(self) -> bool:
        """Analyze volume profile for trade confirmation"""
        if len(self.volume_history) < 20:
            return False
            
        recent_volume = np.mean(self.volume_history[-5:])
        average_volume = np.mean(self.volume_history[-20:])
        
        return recent_volume > (average_volume * self.min_volume_threshold)

    def should_trade(self) -> Optional[str]:
        """Enhanced trading strategy with multiple confirmations"""
        if len(self.price_history) < max(self.bb_period, self.rsi_period, self.ema_long):
            return None

        # Calculate technical indicators
        prices = np.array(self.price_history)
        
        # Bollinger Bands
        sma = np.mean(prices[-self.bb_period:])
        std = np.std(prices[-self.bb_period:])
        upper_band = sma + (self.bb_std * std)
        lower_band = sma - (self.bb_std * std)
        
        # Moving Averages
        ema_short = self.calculate_ema(self.price_history, self.ema_short)
        ema_medium = self.calculate_ema(self.price_history, self.ema_medium)
        ema_long = self.calculate_ema(self.price_history, self.ema_long)
        
        # RSI
        rsi = self.calculate_rsi(self.price_history, self.rsi_period)
        
        # Current price and trend analysis
        current_price = self.last_price
        trend_strength = (ema_short - ema_long) / ema_long * 100
        
        # Volume confirmation
        volume_confirmed = self.calculate_volume_profile()
        
        # Trading signals with multiple confirmations
        buy_signals = [
            current_price < lower_band,  # Price below lower BB
            rsi < self.rsi_oversold,  # RSI oversold
            ema_short > ema_medium,  # Short-term momentum
            trend_strength > 0.5,  # Strong upward trend
            volume_confirmed  # Volume confirmation
        ]
        
        sell_signals = [
            current_price > upper_band,  # Price above upper BB
            rsi > self.rsi_overbought,  # RSI overbought
            ema_short < ema_medium,  # Short-term momentum
            trend_strength < -0.5,  # Strong downward trend
            volume_confirmed  # Volume confirmation
        ]
        
        # Calculate signal strength (percentage of conditions met)
        buy_strength = sum(buy_signals) / len(buy_signals)
        sell_strength = sum(sell_signals) / len(sell_signals)
        
        # Required minimum signal strength (80% of conditions must be met)
        min_signal_strength = 0.8
        
        # Check daily loss limit
        if self.total_profit <= self.max_daily_loss:
            logging.warning("Daily loss limit reached. Stopping trading.")
            return None
        
        # Generate trading signals with strong confirmation
        if buy_strength >= min_signal_strength:
            # Calculate potential reward and risk
            potential_reward = upper_band - current_price
            potential_risk = current_price - lower_band
            
            if potential_reward / potential_risk >= self.risk_reward_ratio:
                return "buy"
        
        elif sell_strength >= min_signal_strength:
            potential_reward = current_price - lower_band
            potential_risk = upper_band - current_price
            
            if potential_reward / potential_risk >= self.risk_reward_ratio:
                return "sell"
        
        return None

    async def process_tick(self, tick_data, websocket):
        """Enhanced tick processing with performance tracking"""
        current_price = tick_data['tick']['quote']
        timestamp = datetime.fromtimestamp(tick_data['tick']['epoch']).strftime('%H:%M:%S')
        
        # Update price history
        self.last_price = current_price
        self.price_history.append(current_price)
        
        # Estimate volume from tick data (if available)
        if 'volume' in tick_data['tick']:
            self.volume_history.append(tick_data['tick']['volume'])
        
        # Maintain data history length
        max_history = max(self.bb_period, self.rsi_period, self.ema_long) * 2
        if len(self.price_history) > max_history:
            self.price_history.pop(0)
        if len(self.volume_history) > max_history:
            self.volume_history.pop(0)
        
        # Log price movements
        if len(self.price_history) > 1:
            price_change = current_price - self.price_history[-2]
            direction = "↑" if price_change > 0 else "↓" if price_change < 0 else "→"
            logging.info(f"Time: {timestamp} | Price: {current_price:.5f} | Change: {direction} {abs(price_change):.5f}")
        
        # Check trading conditions if not in a trade
        if not self.in_trade and len(self.price_history) >= max(self.bb_period, self.rsi_period, self.ema_long):
            action = self.should_trade()
            if action:
                await self.place_trade(websocket, action)

    async def run(self):
        """Main bot execution loop with enhanced error handling"""
        while True:
            try:
                async with websockets.connect(self.ws_url) as websocket:
                    logging.info("Connecting to Deriv API...")
                    
                    # Authentication
                    auth_response = await self.authenticate(websocket)
                    if not auth_response:
                        raise Exception("Authentication failed")
                    
                    logging.info(f"Authenticated with account id: {auth_response.get('account_id')}")
                    
                    # Subscribe to market data
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
                                await self.process_tick(data, websocket)
                            elif 'proposal_open_contract' in data:
                                await self.handle_contract_update(data)
                            elif 'error' in data:
                                await self.handle_error(data)
                                
                        except websockets.exceptions.ConnectionClosed:
                            logging.warning("Connection closed. Reconnecting...")
                            break
                            
            except Exception as e:
                logging.error(f"Error in main loop: {e}")
                await asyncio.sleep(5)

    async def handle_contract_update(self, data):
        """Handle contract updates and track performance"""
        contract_data = data['proposal_open_contract']
        
        if contract_data['is_sold']:
            profit = contract_data['profit']
            self.total_profit += profit
            
            if profit > 0:
                self.wins += 1
            else:
                self.losses += 1
            
            win_rate = (self.wins / (self.wins + self.losses)) * 100 if (self.wins + self.losses) > 0 else 0
            
            logging.info(f"""
            Trade completed:
            Profit/Loss: {profit}
            Total Profit: {self.total_profit}
            Win Rate: {win_rate:.2f}%
            """)
            
            self.in_trade = False
            self.current_contract_id = None

    async def handle_error(self, data):
        """Handle API errors"""
        error_msg = data['error']['message']
        error_code = data['error']['code']
        
        logging.error(f"API Error {error_code}: {error_msg}")
        
        if error_code == 'InvalidToken':
            raise Exception("Invalid API token")

# Rest of the code remains the same (main() function, etc.)
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
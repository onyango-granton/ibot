import numpy as np
import pandas as pd
import logging
from datetime import datetime, timedelta
from iqoptionapi.stable_api import IQ_Option
import time
from typing import List, Optional

class IQOptionTradingBot:
    def __init__(self, email, password):
        self.email = email
        self.password = password
        self.api = IQ_Option(self.email, self.password)
        
        self.config = {
            'asset': 'EURUSD',  # Trading asset
            'duration': 1,      # Duration in minutes
            'amount': 1.00,     # Trade amount
            'mode': 'PRACTICE'  # PRACTICE or REAL
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
        self.min_volume_threshold = 0.5
        
        # Price and indicator storage
        self.price_history: List[float] = []
        self.volume_history: List[float] = []
        self.last_price: Optional[float] = None
        self.in_trade = False
        self.trade_count = 0
        self.max_trades = 10
        
        # Trading performance metrics
        self.wins = 0
        self.losses = 0
        self.total_profit = 0
        
        # Risk management
        self.max_daily_loss = -5.00
        self.trailing_stop_pips = 10
        self.risk_reward_ratio = 2.0

    #def connect(self):
    #    """Connect to IQ Option API"""
    #    logging.info("Connecting to IQ Option...")
    #    _, check = self.api.connect()
    #    
    #    if check:
    #        logging.info("Successfully connected to IQ Option")
    #        self.api.change_balance(self.config['mode'])
    #        return True
    #    else:
    #        logging.error("Connection failed")
    #        return False

    
    def get_historical_data(self):
        """Get historical candle data"""
        end = int(time.time())
        start = end - (self.bb_period + self.ema_long) * 60  # Get enough data for indicators
        
        candles = self.api.get_candles(
            self.config['asset'],
            60,  # 1-minute candles
            (self.bb_period + self.ema_long),
            end
        )
        
        for candle in candles:
            self.price_history.append(candle['close'])
            self.volume_history.append(candle['volume'])

    def calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """Calculate Relative Strength Index"""
        if len(prices) < period + 1:
            return 50
            
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
            return prices[-1]
            
        ema = np.convolve(prices_array, weights, mode='valid')[-1]
        return ema

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
            current_price < lower_band,
            rsi < self.rsi_oversold,
            ema_short > ema_medium,
            trend_strength > 0.5,
            volume_confirmed
        ]
        
        sell_signals = [
            current_price > upper_band,
            rsi > self.rsi_overbought,
            ema_short < ema_medium,
            trend_strength < -0.5,
            volume_confirmed
        ]
        
        # Calculate signal strength
        buy_strength = sum(buy_signals) / len(buy_signals)
        sell_strength = sum(sell_signals) / len(sell_signals)
        
        min_signal_strength = 0.8
        
        # Check daily loss limit
        if self.total_profit <= self.max_daily_loss:
            logging.warning("Daily loss limit reached. Stopping trading.")
            return None
        
        if buy_strength >= min_signal_strength:
            potential_reward = upper_band - current_price
            potential_risk = current_price - lower_band
            
            if potential_reward / potential_risk >= self.risk_reward_ratio:
                return "call"
        
        elif sell_strength >= min_signal_strength:
            potential_reward = current_price - lower_band
            potential_risk = upper_band - current_price
            
            if potential_reward / potential_risk >= self.risk_reward_ratio:
                return "put"
        
        return None

    def place_trade(self, direction):
        """Place a trade on IQ Option"""
        if self.in_trade or self.trade_count >= self.max_trades:
            return False

        check, id = self.api.buy(
            self.config['amount'],
            self.config['asset'],
            direction,
            self.config['duration']
        )
        
        if check:
            self.in_trade = True
            self.trade_count += 1
            logging.info(f"Trade #{self.trade_count} placed: {direction.upper()} at {self.last_price}")
            return id
        else:
            logging.error("Trade placement failed")
            return False

    def check_trade_result(self, trade_id):
        """Check the result of a trade"""
        result = self.api.check_win_v4(trade_id)
        
        if result:
            profit = result[1]
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

    def connect(self):
        """Connect to IQ Option API with enhanced error handling"""
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                logging.info(f"Connecting to IQ Option (Attempt {retry_count + 1}/{max_retries})...")
                
                # Attempt connection
                status, reason = self.api.connect()
                
                if status:
                    # Verify connection
                    if self.api.check_connect():
                        logging.info("Successfully connected to IQ Option")
                        
                        # Set account mode (PRACTICE/REAL)
                        mode_check = self.api.change_balance(self.config['mode'])
                        if mode_check:
                            logging.info("Successfully set trading mode")
                            balance = self.api.get_balance()
                            logging.info(f"Current balance: {balance}")
                            logging.info(f"Trading mode: {self.config['mode']}")
                            return True
                        else:
                            logging.error(f"Failed to set trading mode. Check 'change_balance' return value.")
                            reason = self.api.get_last_error()  # Assuming get_last_error() is a function to retrieve the last error message
                            logging.error(f"Last error: {reason}")
                else:
                    logging.error(f"Connection failed: {reason}")
                
                retry_count += 1
                if retry_count < max_retries:
                    wait_time = 5 * retry_count
                    logging.info(f"Waiting {wait_time} seconds before retrying...")
                    time.sleep(wait_time)
                
            except Exception as e:
                logging.error(f"Connection error: {str(e)}")
                retry_count += 1
                if retry_count < max_retries:
                    time.sleep(5 * retry_count)
        
        logging.error("Failed to connect after maximum retries")
        return False

    async def get_real_time_candles(self, size=60):
        """Subscribe to real-time candle data"""
        self.api.start_candles_stream(
            self.config['asset'],
            size,
            1  # How many candles to receive
        )
        
    async def stop_real_time_candles(self):
        """Stop candle data stream"""
        self.api.stop_candles_stream(
            self.config['asset']
        )

    def run(self):
        """Main bot execution loop"""
        if not self.connect():
            return
        
        logging.info("Starting bot...")
        logging.info(f"Trading {self.config['asset']} in {self.config['mode']} mode")
        
        # Get initial historical data
        self.get_historical_data()
        
        try:
            # Start real-time data stream
            self.api.start_candles_stream(
                self.config['asset'],
                60,  # 1-minute candles
                1
            )
            
            while True:
                try:
                    # Get real-time candle data
                    candles = self.api.get_realtime_candles(
                        self.config['asset'],
                        60
                    )
                    
                    if candles:
                        # Process the latest candle
                        latest_candle = next(iter(candles.values()))
                        current_price = latest_candle['close']
                        self.last_price = current_price
                        self.price_history.append(current_price)
                        self.volume_history.append(latest_candle['volume'])
                        
                        # Maintain data history length
                        max_history = max(self.bb_period, self.rsi_period, self.ema_long) * 2
                        if len(self.price_history) > max_history:
                            self.price_history.pop(0)
                        if len(self.volume_history) > max_history:
                            self.volume_history.pop(0)
                        
                        # Log current price
                        logging.info(f"Current price: {current_price}")
                        
                        # Check for trading signals
                        if not self.in_trade:
                            action = self.should_trade()
                            if action:
                                trade_id = self.place_trade(action)
                                if trade_id:
                                    time.sleep(self.config['duration'] * 60)
                                    self.check_trade_result(trade_id)
                    
                    time.sleep(1)  # Avoid excessive API calls
                    
                except Exception as e:
                    logging.error(f"Error in candle processing: {e}")
                    time.sleep(5)
                    
        except KeyboardInterrupt:
            logging.info("Bot stopped by user")
            # Clean up
            self.api.stop_candles_stream(self.config['asset'])
        except Exception as e:
            logging.error(f"Critical error: {e}")
        finally:
            # Ensure we stop the candle stream
            self.api.stop_candles_stream(self.config['asset'])

def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Your IQ Option credentials
    email = "grantononyango@gmail.com"  # Replace with your actual email
    password = "0724600680@Gt"        # Replace with your actual password
    
    bot = None
    while True:
        try:
            if bot is None:
                bot = IQOptionTradingBot(email, password)
            
            if bot.connect():
                bot.run()
            else:
                logging.error("Could not establish connection. Waiting 30 seconds before retry...")
                time.sleep(30)
                bot = None  # Reset bot instance
                
        except Exception as e:
            logging.error(f"Bot crashed with error: {e}")
            logging.info("Restarting in 30 seconds...")
            time.sleep(30)
            bot = None  # Reset bot instance

if __name__ == "__main__":
    main()
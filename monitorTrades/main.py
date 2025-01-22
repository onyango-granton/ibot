import numpy as np
import pandas as pd
import logging
from datetime import datetime
from iqoptionapi.stable_api import IQ_Option
import time
from typing import List, Optional
import colorama
from colorama import Fore, Back, Style

class IQOptionMonitor:
    def __init__(self, email, password):
        colorama.init()  # Initialize colorama for colored terminal output
        self.email = email
        self.password = password
        self.api = IQ_Option(self.email, self.password)
        self.api.connect()
        
        self.config = {
            'asset': 'USDJPY',  # Asset to monitor
            'mode': 'PRACTICE'  # PRACTICE mode only
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
        
        # Alert thresholds
        self.price_change_threshold = 0.0001  # Minimum price change to trigger alert
        self.volume_surge_threshold = 1.5     # Volume increase vs average to trigger alert
        
        # Price and indicator storage
        self.price_history: List[float] = []
        self.volume_history: List[float] = []
        self.last_price: Optional[float] = None
        self.last_alert_time = None
        self.alert_cooldown = 300  # 5 minutes between alerts
        
        # Initialize monitoring log file
        self.initialize_monitor_log()

    def initialize_monitor_log(self):
        """Initialize CSV file for price and indicator logging"""
        self.monitor_log_file = f'price_monitor_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        with open(self.monitor_log_file, 'w') as f:
            f.write("timestamp,price,rsi,ema_short,ema_medium,ema_long,bb_upper,bb_lower,bb_middle,volume,signal\n")

    def log_market_data(self, price, indicators, volume, signal=None):
        """Log market data to CSV file"""
        with open(self.monitor_log_file, 'a') as f:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"{timestamp},{price},{indicators['rsi']},{indicators['ema_short']},"
                   f"{indicators['ema_medium']},{indicators['ema_long']},{indicators['bb_upper']},"
                   f"{indicators['bb_lower']},{indicators['bb_sma']},{volume},{signal}\n")

    def print_alert(self, message, signal_type="INFO"):
        """Print colored alert message to terminal"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if signal_type == "BUY":
            color = Fore.GREEN
            bg_color = Back.BLACK
        elif signal_type == "SELL":
            color = Fore.RED
            bg_color = Back.BLACK
        elif signal_type == "WARNING":
            color = Fore.YELLOW
            bg_color = Back.BLACK
        else:
            color = Fore.WHITE
            bg_color = Back.BLACK
        
        print(f"{bg_color}{color}[{timestamp}] {signal_type}: {message}{Style.RESET_ALL}")

    def check_for_signals(self, price, indicators, volume):
        """Check for trading signals based on indicators"""
        current_time = time.time()

        print(indicators['rsi'])
        
        # Don't send alerts too frequently
        if (self.last_alert_time and 
            current_time - self.last_alert_time < self.alert_cooldown):
            return
        
        signals = []
        
        # RSI signals
        if indicators['rsi'] <= self.rsi_oversold:
            signals.append(("BUY", f"RSI Oversold: {indicators['rsi']:.2f}"))
        elif indicators['rsi'] >= self.rsi_overbought:
            signals.append(("SELL", f"RSI Overbought: {indicators['rsi']:.2f}"))
        
        # Bollinger Bands signals
        if price <= indicators['bb_lower']:
            signals.append(("BUY", f"Price below lower BB: {price:.5f} < {indicators['bb_lower']:.5f}"))
        elif price >= indicators['bb_upper']:
            signals.append(("SELL", f"Price above upper BB: {price:.5f} > {indicators['bb_upper']:.5f}"))
        
        # EMA crossover signals
        if (len(self.price_history) >= 2):
            prev_indicators = self.calculate_indicators(self.price_history[:-1])
            if prev_indicators:
                # Short EMA crosses above Medium EMA
                if (indicators['ema_short'] > indicators['ema_medium'] and 
                    prev_indicators['ema_short'] <= prev_indicators['ema_medium']):
                    signals.append(("BUY", "Short EMA crossed above Medium EMA"))
                # Short EMA crosses below Medium EMA
                elif (indicators['ema_short'] < indicators['ema_medium'] and 
                    prev_indicators['ema_short'] >= prev_indicators['ema_medium']):
                    signals.append(("SELL", "Short EMA crossed below Medium EMA"))
        
        # Volume surge check
        if len(self.volume_history) > 20:
            avg_volume = np.mean(self.volume_history[-20:])
            if volume > avg_volume * self.volume_surge_threshold:
                signals.append(("WARNING", f"Volume surge: {volume:.2f} vs avg {avg_volume:.2f}"))
        
        # Print signals
        if signals:
            self.last_alert_time = current_time
            for signal_type, message in signals:
                self.print_alert(message, signal_type)
                self.log_market_data(price, indicators, volume, signal_type)

    # ... [Previous methods remain the same: connect(), get_historical_data(), 
    #      calculate_indicators(), calculate_rsi(), calculate_ema()] ...


    def connect(self):
        """Connect to IQ Option API with enhanced error handling"""
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                logging.info(f"Connecting to IQ Option (Attempt {retry_count + 1}/{max_retries})...")
                status, reason = self.api.connect()
                
                if status:
                    if self.api.check_connect():
                        logging.info("Successfully connected to IQ Option")
                        self.api.change_balance(self.config['mode'])
                        return True
                else:
                    logging.error(f"Connection failed: {reason}")
                
                retry_count += 1
                if retry_count < max_retries:
                    time.sleep(5 * retry_count)
                
            except Exception as e:
                logging.error(f"Connection error: {str(e)}")
                retry_count += 1
                if retry_count < max_retries:
                    time.sleep(5 * retry_count)
        
        logging.error("Failed to connect after maximum retries")
        return False

    def get_historical_data(self):
        """Get historical candle data"""
        logging.info("Fetching historical data...")
        end = int(time.time())
        start = end - (self.bb_period + self.ema_long) * 60
        
        try:
            candles = self.api.get_candles(
                self.config['asset'],
                60,  # 1-minute candles
                (self.bb_period + self.ema_long),
                end
            )
            
            for candle in candles:
                self.price_history.append(candle['close'])
                self.volume_history.append(candle['volume'])
            
            logging.info(f"Retrieved {len(candles)} historical candles")
            
        except Exception as e:
            logging.error(f"Error fetching historical data: {str(e)}")

    def calculate_indicators(self, prices: List[float]):
        """Calculate technical indicators"""
        try:
            # RSI
            rsi = self.calculate_rsi(prices, self.rsi_period)
            
            # EMAs
            ema_short = self.calculate_ema(prices, self.ema_short)
            ema_medium = self.calculate_ema(prices, self.ema_medium)
            ema_long = self.calculate_ema(prices, self.ema_long)
            
            # Bollinger Bands
            prices_array = np.array(prices[-self.bb_period:])
            sma = np.mean(prices_array)
            std = np.std(prices_array)
            upper_band = sma + (self.bb_std * std)
            lower_band = sma - (self.bb_std * std)
            
            return {
                'rsi': round(rsi, 2),
                'ema_short': round(ema_short, 5),
                'ema_medium': round(ema_medium, 5),
                'ema_long': round(ema_long, 5),
                'bb_upper': round(upper_band, 5),
                'bb_lower': round(lower_band, 5),
                'bb_sma': round(sma, 5)
            }
            
        except Exception as e:
            logging.error(f"Error calculating indicators: {str(e)}")
            return None

    def calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """Calculate Relative Strength Index"""
        try:
            if len(prices) < period + 1:
                return 50
                
            deltas = np.diff(prices)
            seed = deltas[:period+1]
            up = seed[seed >= 0].sum()/period
            down = -seed[seed < 0].sum()/period
            rs = up/down if down != 0 else 0
            return 100 - (100/(1+rs))
            
        except Exception as e:
            logging.error(f"Error calculating RSI: {str(e)}")
            return 50

    def calculate_ema(self, prices: List[float], period: int) -> float:
        """Calculate EMA"""
        try:
            if len(prices) < period:
                return prices[-1]
                
            prices_array = np.array(prices)
            weights = np.exp(np.linspace(-1., 0., period))
            weights /= weights.sum()
            
            ema = np.convolve(prices_array, weights, mode='valid')[-1]
            return ema
            
        except Exception as e:
            logging.error(f"Error calculating EMA: {str(e)}")
            return prices[-1]



    def run(self):
        """Main monitoring loop"""
        if not self.connect():
            return
        
        self.print_alert(f"Starting price monitor for {self.config['asset']}", "INFO")
        self.get_historical_data()
        last_logged_price = None
        
        while True:
            try:
                candles = self.api.get_candles(
                    self.config['asset'],
                    60,
                    1,
                    int(time.time())
                )
                
                if candles:
                    current_price = candles[0]['close']
                    current_volume = candles[0]['volume']
                    
                    if last_logged_price != current_price:
                        price_change = (current_price - last_logged_price) if last_logged_price else 0
                        if abs(price_change) >= self.price_change_threshold:
                            self.print_alert(
                                f"Price Update: {current_price:.5f} (Change: {price_change:+.5f})",
                                "INFO"
                            )
                        last_logged_price = current_price
                    
                    self.last_price = current_price
                    self.price_history.append(current_price)
                    self.volume_history.append(current_volume)
                    
                    # Maintain data history
                    max_history = max(self.bb_period, self.rsi_period, self.ema_long) * 2
                    if len(self.price_history) > max_history:
                        self.price_history.pop(0)
                    if len(self.volume_history) > max_history:
                        self.volume_history.pop(0)
                    
                    # Calculate indicators and check for signals
                    indicators = self.calculate_indicators(self.price_history)
                    if indicators:
                        self.check_for_signals(current_price, indicators, current_volume)
                
                time.sleep(1)
                
            except Exception as e:
                self.print_alert(f"Error in monitoring loop: {str(e)}", "WARNING")
                time.sleep(5)

def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s.%(msecs)03d - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.FileHandler('price_monitor.log'),
            logging.StreamHandler()
        ]
    )
    
    email = "your_email@example.com"
    password = "your_password"
    
    monitor = IQOptionMonitor(email, password)
    monitor.run()

if __name__ == "__main__":
    main()
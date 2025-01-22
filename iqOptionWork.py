import numpy as np
import pandas as pd
import logging
from datetime import datetime, timedelta
from iqoptionapi.stable_api import IQ_Option
import time
from typing import List, Optional
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from collections import deque
import matplotlib.dates as mdates

class IQOptionTradingBot:
    def __init__(self, email, password):
        self.email = email
        self.password = password
        self.api = IQ_Option(self.email, self.password)
        self.api.connect()
        
        self.config = {
            'asset': 'EURUSD',  # Trading asset
            'duration': 1,      # Duration in minutes
            'amount': 1.00,     # Trade amount
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
        self.atr_period = 14
        self.min_volume_threshold = 0.5
        
        # Price and indicator storage
        #self.price_history: List[float] = []
        #self.volume_history: List[float] = []
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
        
        # Initialize trade log file
        self.initialize_trade_log()

        # Modified price and indicator storage for charting
        self.max_points = 100  # Number of points to display on chart
        self.price_history = deque(maxlen=self.max_points)
        self.volume_history = deque(maxlen=self.max_points)
        self.timestamps = deque(maxlen=self.max_points)
        self.indicators = {
            'ema_short': deque(maxlen=self.max_points),
            'ema_medium': deque(maxlen=self.max_points),
            'ema_long': deque(maxlen=self.max_points),
            'bb_upper': deque(maxlen=self.max_points),
            'bb_lower': deque(maxlen=self.max_points),
            'rsi': deque(maxlen=self.max_points)
        }
        
        # Chart setup
        self.setup_charts()

    def initialize_trade_log(self):
        """Initialize CSV file for detailed trade logging"""
        self.trade_log_file = f'trades_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        with open(self.trade_log_file, 'w') as f:
            f.write("timestamp,action,price,indicators,result\n")

    def log_trade_data(self, action, price, indicators, result=None):
        """Log trade data to CSV file"""
        with open(self.trade_log_file, 'a') as f:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"{timestamp},{action},{price},{indicators},{result}\n")


    def connect(self):
        """Connect to IQ Option API with enhanced error handling"""
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                logging.info(f"Connecting to IQ Option (Attempt {retry_count + 1}/{max_retries})...")
                
                # Force close any existing connections
                self.api.logout()
                
                # Attempt connection
                status, reason = self.api.connect()
                
                if status:
                    if self.api.check_connect():
                        logging.info("Successfully connected to IQ Option")
                        self.api.change_balance(self.config['mode'])
                        balance = self.api.get_balance()
                        logging.info(f"Current balance: {balance}")
                        return True
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

    def get_historical_data(self):
        """Get historical candle data with synchronized storage"""
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
            
            # Clear existing data
            self.timestamps.clear()
            self.price_history.clear()
            self.volume_history.clear()
            for indicator in self.indicators.values():
                indicator.clear()
            
            # Add historical data in chronological order
            for candle in candles:
                self.timestamps.append(datetime.fromtimestamp(candle['from']))
                self.price_history.append(candle['close'])
                self.volume_history.append(candle['volume'])
            
            logging.info(f"Retrieved {len(candles)} historical candles")
            
        except Exception as e:
            logging.error(f"Error fetching historical data: {str(e)}")

    def calculate_indicators(self, prices: List[float]):
        """Calculate and log all technical indicators"""
        try:
            if len(prices) < self.bb_period:
                logging.error("Not enough price data to calculate indicators.")
                return None
            
            # Convert prices to numpy array for calculations
            prices_array = np.array(prices)
            
            # Ensure we have enough data for RSI calculation
            if len(prices_array) < self.rsi_period + 1:
                logging.error("Not enough price data for RSI calculation.")
                return None
            
            # RSI
            rsi = self.calculate_rsi(prices_array, self.rsi_period)
            
            # EMAs
            ema_short = self.calculate_ema(prices_array, self.ema_short)
            ema_medium = self.calculate_ema(prices_array, self.ema_medium)
            ema_long = self.calculate_ema(prices_array, self.ema_long)
            
            # Bollinger Bands
            bb_prices = prices_array[-self.bb_period:]
            sma = np.mean(bb_prices)
            std = np.std(bb_prices)
            upper_band = sma + (self.bb_std * std)
            lower_band = sma - (self.bb_std * std)
            
            indicators = {
                'rsi': float(rsi),
                'ema_short': float(ema_short),
                'ema_medium': float(ema_medium),
                'ema_long': float(ema_long),
                'bb_upper': float(upper_band),
                'bb_lower': float(lower_band),
                'bb_sma': float(sma)
            }
            
            logging.info(f"Technical Indicators: {indicators}")
            return indicators
            
        except Exception as e:
            logging.error(f"Error calculating indicators: {str(e)}")
            return None
        
    def calculate_rsi(self, prices: np.ndarray, period: int = 14) -> float:
        """Calculate Relative Strength Index with error handling"""
        try:
            if len(prices) < period + 1:
                return 50.0
                
            # Calculate price changes
            deltas = np.diff(prices)
            
            # Get gains and losses
            gains = np.where(deltas > 0, deltas, 0)
            losses = np.where(deltas < 0, -deltas, 0)
            
            # Calculate average gains and losses
            avg_gain = np.mean(gains[-period:])
            avg_loss = np.mean(losses[-period:])
            
            if avg_loss == 0:
                return 100.0
                
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            
            return float(rsi)
            
        except Exception as e:
            logging.error(f"Error calculating RSI: {str(e)}")
            return 50.0

    def calculate_ema(self, prices: np.ndarray, period: int) -> float:
        """Calculate EMA with error handling"""
        try:
            if len(prices) < period:
                return float(prices[-1])
            
            # Calculate multiplier
            multiplier = 2.0 / (period + 1)
            
            # Initialize EMA with SMA
            ema = np.mean(prices[-period:])
            
            # Calculate EMA
            for price in prices[-period:]:
                ema = (price - ema) * multiplier + ema
            
            return float(ema)
            
        except Exception as e:
            logging.error(f"Error calculating EMA: {str(e)}")
            return float(prices[-1])
        

    def calculate_volume_profile(self) -> bool:
        """Analyze volume profile with logging"""
        try:
            if len(self.volume_history) < 20:
                logging.info("Insufficient volume history")
                return False
                
            # Convert to numpy array for calculations
            volume_array = np.array(list(self.volume_history))
            
            # Calculate recent and average volume
            recent_volume = np.mean(volume_array[-5:])
            average_volume = np.mean(volume_array[-20:])
            
            volume_ratio = float(recent_volume / average_volume)
            logging.info(f"Volume ratio: {volume_ratio:.2f}")
            
            return volume_ratio > self.min_volume_threshold
            
        except Exception as e:
            logging.error(f"Error calculating volume profile: {str(e)}")
            return False

    def should_trade(self) -> Optional[str]:
        """Enhanced trading strategy with detailed logging"""
        try:
            if len(self.price_history) < max(self.bb_period, self.rsi_period, self.ema_long):
                return None

            # Get current price
            current_price = float(list(self.price_history)[-1])
            self.last_price = current_price

            # Calculate indicators
            indicators = self.calculate_indicators(list(self.price_history))
            if not indicators:
                logging.warning("No indicators available for trading decision")
                return None

            # Calculate trend strength
            trend_strength = (indicators['ema_short'] - indicators['ema_long']) / indicators['ema_long'] * 100
            
            # Check volume
            volume_confirmed = self.calculate_volume_profile()
            
            conditions_log = {
                'price_vs_bb_upper': current_price > indicators['bb_upper'],
                'price_vs_bb_lower': current_price < indicators['bb_lower'],
                'rsi_overbought': indicators['rsi'] > self.rsi_overbought,
                'rsi_oversold': indicators['rsi'] < self.rsi_oversold,
                'trend_strength': trend_strength,
                'volume_confirmed': volume_confirmed
            }
            
            logging.info(f"Trading Conditions: {conditions_log}")
            
            # Log market conditions to CSV
            self.log_trade_data(
                "analysis",
                current_price,
                str(indicators)
            )
            
            if self.total_profit <= self.max_daily_loss:
                logging.warning("Daily loss limit reached")
                return None

            # Trading logic
            if volume_confirmed:
                # Potential sell signal
                if current_price > indicators['bb_upper'] and indicators['rsi'] > self.rsi_overbought:
                    #return "put"
                    return None
                
                # Potential buy signal
                if current_price < indicators['bb_lower'] and indicators['rsi'] < self.rsi_oversold:
                    #return "call"
                    return None
            
            return None  # No trade signal
            
        except Exception as e:
            logging.error(f"Error in should_trade: {str(e)}")
            return None

    def place_trade(self, direction):
        """Place a trade with enhanced logging"""
        try:
            if self.in_trade or self.trade_count >= self.max_trades:
                logging.info(f"Trade blocked - In trade: {self.in_trade}, Count: {self.trade_count}")
                return False

            logging.info(f"""
            Placing trade:
            Direction: {direction.upper()}
            Amount: {self.config['amount']}
            Asset: {self.config['asset']}
            Price: {self.last_price}
            """)

            check, id = self.api.buy(
                self.config['amount'],
                self.config['asset'],
                direction,
                self.config['duration']
            )
            
            if check:
                self.in_trade = True
                self.trade_count += 1
                self.log_trade_data("entry", self.last_price, "", id)
                return id
            else:
                logging.error("Trade placement failed")
                return False
                
        except Exception as e:
            logging.error(f"Error placing trade: {str(e)}")
            return False

    def check_trade_result(self, trade_id):
        """Check trade result with enhanced logging"""
        try:
            result = self.api.check_win_v4(trade_id)
            
            if result:
                profit = result[1]
                self.total_profit += profit
                
                if profit > 0:
                    self.wins += 1
                else:
                    self.losses += 1
                
                win_rate = (self.wins / (self.wins + self.losses)) * 100 if (self.wins + self.losses) > 0 else 0
                
                result_log = {
                    'trade_id': trade_id,
                    'profit': profit,
                    'total_profit': self.total_profit,
                    'win_rate': f"{win_rate:.2f}%",
                    'wins': self.wins,
                    'losses': self.losses
                }
                
                logging.info(f"Trade Result: {result_log}")
                
                self.log_trade_data(
                    "exit",
                    self.last_price,
                    "",
                    f"profit={profit}"
                )
                
                self.in_trade = False
                
        except Exception as e:
            logging.error(f"Error checking trade result: {str(e)}")


    def setup_charts(self):
        """Initialize the real-time chart display with proper styling"""
        plt.style.use('dark_background')
        self.fig = plt.figure(figsize=(15, 10))
        
        # Price and indicators subplot
        self.ax1 = self.fig.add_subplot(211)
        self.ax1.set_title('Price and Indicators', pad=20)
        self.ax1.set_ylabel('Price')
        self.price_line, = self.ax1.plot([], [], 'w-', label='Price', linewidth=1.5)
        self.ema_short_line, = self.ax1.plot([], [], 'y-', label=f'EMA {self.ema_short}', linewidth=1)
        self.ema_long_line, = self.ax1.plot([], [], 'r-', label=f'EMA {self.ema_long}', linewidth=1)
        self.bb_upper_line, = self.ax1.plot([], [], 'g--', label='BB Upper', linewidth=1)
        self.bb_lower_line, = self.ax1.plot([], [], 'g--', label='BB Lower', linewidth=1)
        self.ax1.legend(loc='upper left')
        self.ax1.grid(True, alpha=0.2)
        
        # RSI subplot
        self.ax2 = self.fig.add_subplot(212)
        self.ax2.set_title('RSI', pad=20)
        self.ax2.set_ylabel('RSI')
        self.rsi_line, = self.ax2.plot([], [], 'c-', label='RSI', linewidth=1.5)
        self.ax2.axhline(y=self.rsi_overbought, color='r', linestyle='--', alpha=0.5)
        self.ax2.axhline(y=self.rsi_oversold, color='g', linestyle='--', alpha=0.5)
        self.ax2.set_ylim(0, 100)
        self.ax2.grid(True, alpha=0.2)
        self.ax2.legend(loc='upper left')
        
        plt.tight_layout(pad=2.0)
        self.fig.canvas.draw()
        plt.ion()



    def update_chart(self, frame):
        """Update function for the animation with proper indicator display"""
        try:
            if len(self.timestamps) < 2:
                return self.price_line, self.ema_short_line, self.ema_long_line, \
                    self.bb_upper_line, self.bb_lower_line, self.rsi_line

            # Convert data to lists
            times = list(self.timestamps)
            prices = list(self.price_history)
            
            # Ensure all data arrays have the same length
            min_length = min(len(times), len(prices))
            times = times[-min_length:]
            prices = prices[-min_length:]
            
            # Calculate indicators for all available price data
            indicators = self.calculate_indicators(prices)
            if indicators:
                # Update price chart
                self.price_line.set_data(times, prices)
                
                # Create arrays for indicators
                ema_short_data = [self.calculate_ema(np.array(prices[:i+1]), self.ema_short) 
                                for i in range(len(prices))]
                ema_long_data = [self.calculate_ema(np.array(prices[:i+1]), self.ema_long) 
                            for i in range(len(prices))]
                
                # Calculate Bollinger Bands for each point
                bb_upper_data = []
                bb_lower_data = []
                for i in range(len(prices)):
                    if i >= self.bb_period - 1:
                        window = prices[max(0, i-self.bb_period+1):i+1]
                        sma = np.mean(window)
                        std = np.std(window)
                        bb_upper_data.append(sma + self.bb_std * std)
                        bb_lower_data.append(sma - self.bb_std * std)
                    else:
                        bb_upper_data.append(prices[i])
                        bb_lower_data.append(prices[i])
                
                # Calculate RSI for each point
                rsi_data = [self.calculate_rsi(np.array(prices[:i+1]), self.rsi_period) 
                        for i in range(len(prices))]
                
                # Update all lines
                self.ema_short_line.set_data(times, ema_short_data)
                self.ema_long_line.set_data(times, ema_long_data)
                self.bb_upper_line.set_data(times, bb_upper_data)
                self.bb_lower_line.set_data(times, bb_lower_data)
                self.rsi_line.set_data(times, rsi_data)
                
                # Update price chart limits
                price_min = min(min(prices), min(bb_lower_data))
                price_max = max(max(prices), max(bb_upper_data))
                price_padding = (price_max - price_min) * 0.1
                self.ax1.set_ylim(price_min - price_padding, price_max + price_padding)
                
                # Update axis limits
                self.ax1.set_xlim(times[0], times[-1])
                self.ax2.set_xlim(times[0], times[-1])
            
            # Format x-axis dates
            self.ax1.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
            self.ax2.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
            
            # Rotate x-axis labels
            plt.setp(self.ax1.xaxis.get_majorticklabels(), rotation=45)
            plt.setp(self.ax2.xaxis.get_majorticklabels(), rotation=45)
            
            # Adjust layout
            self.fig.tight_layout()
            
            # Draw the updates
            self.fig.canvas.draw()
            self.fig.canvas.flush_events()
            
        except Exception as e:
            logging.error(f"Error updating chart: {str(e)}")
        
        return self.price_line, self.ema_short_line, self.ema_long_line, \
            self.bb_upper_line, self.bb_lower_line, self.rsi_line


    def run(self):
        if not self.connect():
            return
        
        logging.info("Starting bot...")
        logging.info(f"Trading {self.config['asset']} in {self.config['mode']} mode")
        
        self.get_historical_data()
        
        # Calculate initial indicators
        if len(self.price_history) > 0:
            indicators = self.calculate_indicators(list(self.price_history))
            if indicators:
                for key, value in indicators.items():
                    if key in self.indicators:
                        self.indicators[key].append(value)
        
        # Initialize animation with longer interval
        ani = FuncAnimation(
            self.fig,
            self.update_chart,
            interval=1000,  # Update every second
            blit=False     # Set to False for more reliable updates
        )
        
        plt.show(block=False)
        
        while True:
            try:
                candles = self.api.get_candles(
                    self.config['asset'],
                    60,
                    1,
                    int(time.time())
                )
                
                if candles:
                    current_time = datetime.fromtimestamp(candles[0]['from'])
                    current_price = candles[0]['close']
                    
                    # Only append if it's a new timestamp
                    if not self.timestamps or current_time > self.timestamps[-1]:
                        self.timestamps.append(current_time)
                        self.price_history.append(current_price)
                        self.volume_history.append(candles[0]['volume'])
                        
                        # Calculate and store indicators
                        indicators = self.calculate_indicators(list(self.price_history))
                        if indicators:
                            for key, value in indicators.items():
                                if key in self.indicators:
                                    self.indicators[key].append(value)
                    
                    # Trading logic
                    if not self.in_trade:
                        action = self.should_trade()
                        if action:
                            trade_id = self.place_trade(action)
                            if trade_id:
                                time.sleep(self.config['duration'] * 60)
                                self.check_trade_result(trade_id)
                
                plt.pause(0.1)  # Allow time for the chart to update
                time.sleep(1)
                
            except Exception as e:
                logging.error(f"Error in main loop: {str(e)}")
                time.sleep(5)
                
def main():
    # Set up logging configuration
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s.%(msecs)03d - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.FileHandler('trading_bot.log'),
            logging.StreamHandler()
        ]
    )
    
    email = "grantononyango@gmail.com"
    password = "0724600680@Gt"
    
    bot = IQOptionTradingBot(email, password)
    bot.run()

if __name__ == "__main__":
    main()
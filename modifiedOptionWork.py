import numpy as np
import pandas as pd
import logging
from datetime import datetime, timedelta
from iqoptionapi.stable_api import IQ_Option
import time
from typing import List, Optional
import traceback

class IQOptionTradingBot:
    def __init__(self, email, password):
        self.email = email
        self.password = password
        self.api = IQ_Option(self.email, self.password)
        self.api.connect()
        
        
        self.config = {
            'asset': 'USDJPY',  # Trading asset
            'duration': 5,      # Duration in minutes
            'amount': 100.00,     # Trade amount
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
        
        # Initialize trade log file
        self.initialize_trade_log()

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
        """Get historical candle data with logging"""
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
        """Calculate and log all technical indicators"""
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
            
            indicators = {
                'rsi': round(rsi, 2),
                'ema_short': round(ema_short, 5),
                'ema_medium': round(ema_medium, 5),
                'ema_long': round(ema_long, 5),
                'bb_upper': round(upper_band, 5),
                'bb_lower': round(lower_band, 5),
                'bb_sma': round(sma, 5)
            }
            
            logging.info(f"Technical Indicators: {indicators}")
            return indicators
            
        except Exception as e:
            logging.error(f"Error calculating indicators: {str(e)}")
            return None

    def calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """Calculate Relative Strength Index with error handling"""
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
        """Calculate EMA with error handling"""
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

    def calculate_volume_profile(self) -> bool:
        """Analyze volume profile with logging"""
        try:
            if len(self.volume_history) < 20:
                logging.info("Insufficient volume history")
                return False
                
            recent_volume = np.mean(self.volume_history[-5:])
            average_volume = np.mean(self.volume_history[-20:])
            
            volume_ratio = recent_volume / average_volume
            logging.info(f"Volume ratio: {volume_ratio:.2f}")
            
            return volume_ratio > self.min_volume_threshold
            
        except Exception as e:
            logging.error(f"Error calculating volume profile: {str(e)}")
            return False

    def should_trade(self) -> Optional[str]:
        """Enhanced trading strategy with detailed logging"""
        try:
            if not self.is_good_trading_time():
                return None
            if len(self.price_history) < max(self.bb_period, self.rsi_period, self.ema_long):
                return None

            indicators = self.calculate_indicators(self.price_history)
            if not indicators:
                return None


            current_price = self.last_price


            trend_strength = (indicators['ema_short'] - indicators['ema_long']) / indicators['ema_long'] * 100
            
            volume_confirmed = self.calculate_volume_profile()

            if indicators['rsi'] > self.rsi_overbought:
                logging.info(f"RSI overbought: {indicators['rsi']}. Attempting to execute a SELL trade.")
                return "put"
            
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

            # Trading logic remains the same but with enhanced logging
            # ... (previous trading logic)
            
            return None  # No trade signal
            
        except Exception as e:
            logging.error(f"Error in should_trade: {str(e)}")
            return None

    # def place_trade(self, direction):
    #     """Place a trade with enhanced logging"""
    #     try:
    #         if self.in_trade or self.trade_count >= self.max_trades:
    #             logging.info(f"Trade blocked - In trade: {self.in_trade}, Count: {self.trade_count}")
    #             return False

    #         logging.info(f"""
    #         Placing trade:
    #         Direction: {direction.upper()}
    #         Amount: {self.config['amount']}
    #         Asset: {self.config['asset']}
    #         Price: {self.last_price}
    #         """)

    #         check, id = self.api.buy(
    #             self.config['amount'],
    #             self.config['asset'],
    #             direction,
    #             self.config['duration']
    #         )
            
    #         if check:
    #             self.in_trade = True
    #             self.trade_count += 1
    #             self.log_trade_data("entry", self.last_price, "", id)
    #             return id
    #         else:
    #             logging.error("Trade placement failed")
    #             return False
                
    #     except Exception as e:
    #         logging.error(f"Error placing trade: {str(e)}")
    #         return False


    # def place_trade(self, direction):
    #     """Place a trade with enhanced logging"""
    #     try:
    #         if self.in_trade or self.trade_count >= self.max_trades:
    #             logging.info(f"Trade blocked - In trade: {self.in_trade}, Count: {self.trade_count}")
    #             return False

    #         # Check balance before trading
    #         balance = self.api.get_balance()
    #         if balance < self.config['amount']:
    #             logging.error(f"Insufficient balance: {balance} < {self.config['amount']}")
    #             return False

    #         logging.info(f"""
    #         Placing trade:
    #         Direction: {direction.upper()}
    #         Amount: {self.config['amount']}
    #         Asset: {self.config['asset']}
    #         Price: {self.last_price}
    #         Balance: {balance}
    #         """)

    #         check, id = self.api.buy(
    #             self.config['amount'],
    #             self.config['asset'],
    #             direction,
    #             self.config['duration']
    #         )
            
    #         if check:
    #             self.in_trade = True
    #             self.trade_count += 1
    #             self.log_trade_data("entry", self.last_price, "", id)
    #             return id
    #         else:
    #             logging.error(f"Trade placement failed - Direction: {direction}, Asset: {self.config['asset']}")
    #             return False
                
    #     except Exception as e:
    #         logging.error(f"Error placing trade: {str(e)}")
    #         return False

    # def place_trade(self, direction):
    #     """Place a trade with enhanced logging"""
    #     try:
    #         if self.in_trade or self.trade_count >= self.max_trades:
    #             logging.info(f"Trade blocked - In trade: {self.in_trade}, Count: {self.trade_count}")
    #             return False

    #         # Check if we're still connected
    #         if not self.api.check_connect():
    #             logging.error("Connection lost")
    #             self.connect()
    #             return False

    #         balance = self.api.get_balance()
    #         if balance < self.config['amount']:
    #             logging.error(f"Insufficient balance: {balance} < {self.config['amount']}")
    #             return False

    #         # Get profit for asset to verify if trading is available
    #         profit = self.api.get_all_profit()[self.config['asset']]
    #         if profit is None:
    #             logging.error(f"Trading might be closed for {self.config['asset']}")
    #             return False

    #         logging.info(f"""
    #         Placing trade:
    #         Direction: {direction.upper()}
    #         Amount: {self.config['amount']}
    #         Asset: {self.config['asset']}
    #         Price: {self.last_price}
    #         Balance: {balance}
    #         Current Profit Rate: {profit}
    #         """)

    #         check, id = self.api.buy(
    #             self.config['amount'],
    #             self.config['asset'],
    #             direction,
    #             self.config['duration']
    #         )
            
    #         if check:
    #             self.in_trade = True
    #             self.trade_count += 1
    #             self.log_trade_data("entry", self.last_price, "", id)
    #             return id
    #         else:
    #             logging.error(f"Trade placement failed - Response: {check}, ID: {id}")
    #             return False
                
    #     except Exception as e:
    #         logging.error(f"Error placing trade: {str(e)}")
    #         return False

    # def place_trade(self, direction):
    #     """Place a trade with enhanced logging"""
    #     try:
    #         if not self.is_forex_market_open():
    #             logging.error("Forex market is currently closed")
    #             return False

    #         if self.in_trade or self.trade_count >= self.max_trades:
    #             logging.info(f"Trade blocked - In trade: {self.in_trade}, Count: {self.trade_count}")
    #             return False

    #         # Add a small delay before placing trade
    #         time.sleep(2)

    #         # Check if we're still connected
    #         if not self.api.check_connect():
    #             logging.error("Connection lost")
    #             self.connect()
    #             return False

    #         # Get all active assets and their status
    #         actives = self.api.get_all_open_time()
            
    #         # Check binary options availability
    #         if 'binary' in actives and self.config['asset'] in actives['binary']:
    #             asset_status = actives['binary'][self.config['asset']]
    #             if not asset_status['open']:
    #                 logging.error(f"Asset {self.config['asset']} is closed. Next open time: {asset_status.get('open_time', 'Unknown')}")
    #                 return False

    #         # Try turbo options if binary is suspended
    #         if 'turbo' in actives and self.config['asset'] in actives['turbo']:
    #             asset_status = actives['turbo'][self.config['asset']]
    #             if asset_status['open']:
    #                 logging.info("Switching to turbo options as binary is suspended")
    #                 check, id = self.api.buy_digital_spot(
    #                     self.config['asset'],
    #                     self.config['amount'],
    #                     direction.lower(),
    #                     self.config['duration']
    #                 )
    #                 if check:
    #                     logging.info(f"Turbo option trade placed successfully. ID: {id}")
    #                     return id

    #         logging.info(f"""
    #         Asset Status Check:
    #         Current UTC Time: {datetime.utcnow()}
    #         Binary Status: {actives.get('binary', {}).get(self.config['asset'], 'Not Available')}
    #         Turbo Status: {actives.get('turbo', {}).get(self.config['asset'], 'Not Available')}
    #         Direction: {direction.upper()}
    #         Amount: {self.config['amount']}
    #         Asset: {self.config['asset']}
    #         Price: {self.last_price}
    #         Balance: {self.api.get_balance()}
    #         """)

    #         # If we get here, try regular binary option
    #         check, id = self.api.buy(
    #             self.config['amount'],
    #             self.config['asset'],
    #             direction.lower(),
    #             self.config['duration']
    #         )
            
    #         if check:
    #             self.in_trade = True
    #             self.trade_count += 1
    #             self.log_trade_data("entry", self.last_price, "", id)
    #             logging.info(f"Trade placed successfully. ID: {id}")
    #             return id
    #         else:
    #             logging.error(f"Trade placement failed - Response: {check}, ID: {id}")
    #             # Try to get more detailed error information
    #             if hasattr(self.api, 'get_last_error'):
    #                 error_info = self.api.get_last_error()
    #                 logging.error(f"Last error details: {error_info}")
    #             return False
                
    #     except Exception as e:
    #         logging.error(f"Error placing trade: {str(e)}")
    #         return False        


    # def place_trade(self, direction):
    #     """Place a trade with enhanced logging"""
    #     try:
    #         if self.in_trade or self.trade_count >= self.max_trades:
    #             logging.info(f"Trade blocked - In trade: {self.in_trade}, Count: {self.trade_count}")
    #             return False

    #         # First try to get instrument type that's available
    #         instrument_type = None
            
    #         # Check regular binary options
    #         binary_profit = self.api.get_digital_current_profit(self.config['asset'])
    #         if binary_profit:
    #             instrument_type = "digital"
    #             logging.info(f"Digital options available with profit: {binary_profit}%")
    #         else:
    #             # Check turbo/binary options
    #             turbo_profit = self.api.get_all_profit()[self.config['asset']].get('turbo', None)
    #             if turbo_profit:
    #                 instrument_type = "turbo"
    #                 logging.info(f"Turbo options available with profit: {turbo_profit}%")

    #         if not instrument_type:
    #             logging.error(f"No trading instruments available for {self.config['asset']}")
    #             return False

    #         balance = self.api.get_balance()
    #         logging.info(f"""
    #         Placing trade:
    #         Type: {instrument_type}
    #         Direction: {direction.lower()}
    #         Amount: {self.config['amount']}
    #         Asset: {self.config['asset']}
    #         Price: {self.last_price}
    #         Balance: {balance}
    #         """)

    #         # Place trade based on available instrument
    #         if instrument_type == "digital":
    #             check, id = self.api.buy_digital_spot(
    #                 self.config['asset'],
    #                 self.config['amount'],
    #                 direction.lower(),
    #                 self.config['duration']
    #             )
    #         else:  # turbo
    #             check, id = self.api.buy(
    #                 self.config['amount'],
    #                 self.config['asset'],
    #                 direction.lower(),
    #                 self.config['duration']
    #             )
            
    #         if check:
    #             self.in_trade = True
    #             self.trade_count += 1
    #             self.log_trade_data("entry", self.last_price, "", id)
    #             logging.info(f"Trade placed successfully. Type: {instrument_type}, ID: {id}")
    #             return id
    #         else:
    #             logging.error(f"Trade placement failed - Type: {instrument_type}, Response: {check}, ID: {id}")
    #             return False
                
    #     except Exception as e:
    #         logging.error(f"Error placing trade: {str(e)}")
    #         return False


    # def place_trade(self, direction):
#     """Place a trade with enhanced logging"""
#     try:
#         if self.in_trade or self.trade_count >= self.max_trades:
#             logging.info(f"Trade blocked - In trade: {self.in_trade}, Count: {self.trade_count}")
#             return False

#         # First try to get instrument type that's available
#         instrument_type = None
        
#         # Check digital options
#         binary_profit = self.api.get_digital_current_profit(
#             self.config['asset'], 
#             self.config['duration']  # Add duration parameter here
#         )
#         if binary_profit:
#             instrument_type = "digital"
#             logging.info


    def place_trade(self, direction):
        """Place a trade with enhanced logging"""
        MAX_RETRIES = 3
        RETRY_DELAY = 2  # seconds
        
        try:
            if self.in_trade or self.trade_count >= self.max_trades:
                logging.info(f"Trade blocked - In trade: {self.in_trade}, Count: {self.trade_count}")
                return False

            for attempt in range(MAX_RETRIES):
                try:
                    # Check if market is active
                    actives = self.api.get_all_open_time()
                    
                    # Try both turbo and binary
                    market_closed = True
                    for option_type in ['turbo', 'binary']:
                        if (option_type in actives and 
                            self.config['asset'] in actives[option_type] and 
                            actives[option_type][self.config['asset']]['open']):
                            market_closed = False
                            break
                    
                    if market_closed:
                        logging.error(f"Market is closed for {self.config['asset']}")
                        return False

                    balance = self.api.get_balance()
                    logging.info(f"""
                    Attempt {attempt + 1}/{MAX_RETRIES}
                    Placing trade:
                    Direction: {direction.lower()}
                    Amount: {self.config['amount']}
                    Asset: {self.config['asset']}
                    Duration: {self.config['duration']}
                    Price: {self.last_price}
                    Balance: {balance}
                    """)

                    # Try binary first, then turbo if binary fails
                    check, id = self.api.buy(
                        self.config['amount'],
                        self.config['asset'],
                        direction.lower(),
                        self.config['duration']
                    )
                    
                    if not check:
                        logging.warning(f"Binary option failed, trying turbo option - Attempt {attempt + 1}")
                        check, id = self.api.buy_digital_spot(
                            self.config['asset'],
                            self.config['amount'],
                            direction.lower(),
                            self.config['duration']
                        )

                    if check:
                        self.in_trade = True
                        self.trade_count += 1
                        self.log_trade_data("entry", self.last_price, "", id)
                        logging.info(f"Trade placed successfully. ID: {id}")
                        return id
                    
                    if attempt < MAX_RETRIES - 1:
                        logging.warning(f"Trade failed, waiting {RETRY_DELAY} seconds before retry...")
                        time.sleep(RETRY_DELAY)
                        continue
                        
                except Exception as e:
                    logging.error(f"Attempt {attempt + 1} failed: {str(e)}")
                    if attempt < MAX_RETRIES - 1:
                        time.sleep(RETRY_DELAY)
                        continue
                    raise

            logging.error(f"Trade placement failed after {MAX_RETRIES} attempts")
            return False
                
        except Exception as e:
            logging.error(f"Error placing trade: {str(e)}")
            return False
        

    # def is_good_trading_time(self):
    #     """Check if current time is good for trading"""
    #     current_hour = datetime.now().hour
    #     
    #     # Avoid trading during market opens and closes
    #     high_volatility_hours = [0, 1, 8, 15, 22, 23]  # UTC hours to avoid
    #     
    #     if current_hour in high_volatility_hours:
    #         logging.info(f"Avoiding trade during high volatility hour: {current_hour}:00 UTC")
    #         return False
    #         
    #     return True


    def is_good_trading_time(self):
        """Check if current time is good for trading"""
        current_time = datetime.now()
        current_hour = current_time.hour
        current_weekday = current_time.weekday()
        
        # Weekend check (Friday close to Monday open)
        if current_weekday == 5 or current_weekday == 6:  # Saturday or Sunday
            logging.info("Weekend - Market closed")
            return False
        
        # Avoid the low liquidity period between 22:00-2:00 UTC
        if current_hour >= 22 or current_hour < 2:
            logging.info(f"Low liquidity period: {current_hour}:00 UTC")
            return False
            
        # Best trading hours for EUR pairs are when both London and NY are open
        # London: 8:00-16:00 UTC
        # New York: 13:00-21:00 UTC
        # Overlap: 13:00-16:00 UTC
        
        prime_trading_hours = range(13, 16)  # London-NY overlap
        good_trading_hours = range(7, 21)    # Extended trading hours
        
        if current_hour in prime_trading_hours:
            logging.info(f"Prime trading time: {current_hour}:00 UTC (London-NY overlap)")
            return True
        elif current_hour in good_trading_hours:
            logging.info(f"Regular trading time: {current_hour}:00 UTC")
            return True
        else:
            logging.info(f"Outside main trading hours: {current_hour}:00 UTC")
            return False


    # def check_trade_result(self, trade_id):
    #     """Check trade result with enhanced logging"""
    #     try:
    #         result = self.api.check_win_v4(trade_id)
    #         
    #         if result:
    #             profit = result[1]
    #             self.total_profit += profit
    #             
    #             if profit > 0:
    #                 self.wins += 1
    #             else:
    #                 self.losses += 1
    #             
    #             win_rate = (self.wins / (self.wins + self.losses)) * 100 if (self.wins + self.losses) > 0 else 0
    #             
    #             result_log = {
    #                 'trade_id': trade_id,
    #                 'profit': profit,
    #                 'total_profit': self.total_profit,
    #                 'win_rate': f"{win_rate:.2f}%",
    #                 'wins': self.wins,
    #                 'losses': self.losses
    #             }
    #             
    #             logging.info(f"Trade Result: {result_log}")
    #             
    #             self.log_trade_data(
    #                 "exit",
    #                 self.last_price,
    #                 "",
    #                 f"profit={profit}"
    #             )
    #             
    #             self.in_trade = False
    #             
    #     except Exception as e:
    #         logging.error(f"Error checking trade result: {str(e)}")

    def check_trade_result(self, trade_id):
        """Check trade result with enhanced logging"""
        try:
            # Try digital options first
            try:
                result = self.api.check_win_digital_v2(trade_id)
            except:
                # If failed, try regular binary options
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

    def is_forex_market_open(self) -> bool:
        """Check if forex market is open based on current time"""
        current_time = datetime.now()
        
        # Convert to UTC
        utc_time = current_time.utcnow()
        
        # Market is closed from Friday 21:00 UTC until Sunday 21:00 UTC
        if utc_time.weekday() == 5 or utc_time.weekday() == 6:  # Saturday or Sunday
            return False
        if utc_time.weekday() == 4 and utc_time.hour >= 21:  # Friday after 21:00
            return False
        if utc_time.weekday() == 0 and utc_time.hour < 21:  # Sunday before 21:00
            return False
            
        return True

    def run(self):
        """Main bot execution loop with enhanced logging"""
        if not self.connect():
            return
        
        logging.info("Starting bot...")
        logging.info(f"Trading {self.config['asset']} in {self.config['mode']} mode")
        
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
                    if last_logged_price != current_price:
                        price_change = (current_price - last_logged_price) if last_logged_price else 0
                        logging.info(f"Price Update: {current_price:.5f} (Change: {price_change:+.5f})")
                        last_logged_price = current_price
                    
                    self.last_price = current_price
                    self.price_history.append(current_price)
                    self.volume_history.append(candles[0]['volume'])
                    
                    # Maintain data history
                    max_history = max(self.bb_period, self.rsi_period, self.ema_long) * 2
                    if len(self.price_history) > max_history:
                        self.price_history.pop(0)
                    if len(self.volume_history) > max_history:
                        self.volume_history.pop(0)
                    
                    if not self.in_trade:
                        action = self.should_trade()
                        if action:
                            trade_id = self.place_trade(action)
                            if trade_id:
                                time.sleep(self.config['duration'] * 60)
                                self.check_trade_result(trade_id)
                
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
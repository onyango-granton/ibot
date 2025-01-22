import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime
from iqoptionapi.stable_api import IQ_Option
import logging
from typing import List, Dict
from dataclasses import dataclass
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json

@dataclass
class TradeResult:
    entry_time: datetime
    exit_time: datetime
    entry_price: float
    exit_price: float
    direction: str
    profit_loss: float
    strategy_name: str

class TradingSystem:
    def __init__(self):
        self.demo_api = None
        self.pairs = ['EURUSD', 'GBPUSD', 'USDJPY']
        self.timeframes = {'1m': 1, '5m': 5, '15m': 15, '1h': 60}
        
        # Strategy parameters
        self.rsi_period = 14
        self.rsi_overbought = 70
        self.rsi_oversold = 30
        self.ema_short = 9
        self.ema_long = 21
        
        # Paper trading variables
        self.paper_balance = 10000.0
        self.trade_size = 100.0
        self.paper_trades: List[TradeResult] = []
        
        # Initialize logging
        self.setup_logging()

    def setup_logging(self):
        """Configure logging system"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('trading_practice.log'),
                logging.StreamHandler()
            ]
        )

    def connect_demo_account(self, email: str, password: str) -> bool:
        """Connect to IQ Option demo account"""
        try:
            self.demo_api = IQ_Option(email, password)
            status, reason = self.demo_api.connect()
            
            if status:
                self.demo_api.change_balance('PRACTICE')
                balance = self.demo_api.get_balance()
                logging.info(f"Connected to demo account. Balance: {balance}")
                return True
            else:
                logging.error(f"Connection failed: {reason}")
                return False
                
        except Exception as e:
            logging.error(f"Error connecting to demo account: {str(e)}")
            return False

    def get_historical_data(self, symbol: str, period: str = '1mo', interval: str = '1m') -> pd.DataFrame:
        """Get historical data from Yahoo Finance"""
        try:
            # Convert forex pair format if needed
            if '/' in symbol:
                symbol = symbol.replace('/', '') + '=X'
            
            data = yf.download(symbol, period=period, interval=interval)
            if data.empty:
                raise ValueError(f"No data available for {symbol}.")
            data['Symbol'] = symbol
            logging.info(f"Downloaded {len(data)} records for {symbol}")
            print(data)
            return data
            
        except Exception as e:
            logging.error(f"Error downloading data for {symbol}: {str(e)}")
            return pd.DataFrame()

    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calculate technical indicators"""
        try:
            if data.empty:
                raise ValueError("Data is empty; cannot calculate indicators.")
            
            # RSI
            delta = data['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
            rs = gain / loss
            data['RSI'] = 100 - (100 / (1 + rs))
            
            # EMAs
            data['EMA_short'] = data['Close'].ewm(span=self.ema_short).mean()
            data['EMA_long'] = data['Close'].ewm(span=self.ema_long).mean()
            
            # Bollinger Bands
            data['BB_middle'] = data['Close'].rolling(window=20).mean()
            std = data['Close'].rolling(window=20).std()
            data['BB_upper'] = data['BB_middle'] + (std * 2)
            data['BB_lower'] = data['BB_middle'] - (std * 2)
            
            logging.info(f"Indicators calculated for {len(data)} rows.")
            return data
            
        except Exception as e:
            logging.error(f"Error calculating indicators: {str(e)}")
            return data

    def paper_trade(self, data: pd.DataFrame, strategy: str = 'RSI') -> List[TradeResult]:
        """Simulate paper trading with selected strategy"""
        trades = []
        in_position = False
        entry_price = 0
        entry_time = None
        direction = None

        if data.empty:
            logging.warning("No data to trade on.")
            return trades
        
        for i in range(len(data)):
            current_row = data.iloc[i]
            
            if strategy == 'RSI':
                # RSI-based trading logic
                if not in_position and current_row['RSI'] < self.rsi_oversold:
                    entry_price = current_row['Close']
                    entry_time = data.index[i]
                    direction = 'BUY'
                    in_position = True
                    logging.info(f"Entering position: {direction} at {entry_price}")
                elif in_position and current_row['RSI'] > 50:
                    exit_price = current_row['Close']
                    profit_loss = (exit_price - entry_price) * self.trade_size
                    trades.append(TradeResult(entry_time, data.index[i], entry_price, exit_price, direction, profit_loss, strategy))
                    in_position = False
                    logging.info(f"Exiting position: {direction} at {exit_price}. P/L: {profit_loss}")
        
        return trades

    # Additional methods remain unchanged for brevity...
   
    
    def visualize_trades(self, data: pd.DataFrame, trades: List[TradeResult], title: str):
        """Create interactive visualization of trades"""
        fig = make_subplots(rows=2, cols=1, shared_xaxis=True, 
                          vertical_spacing=0.05, 
                          row_heights=[0.7, 0.3])

        # Add candlestick chart
        fig.add_trace(
            go.Candlestick(
                x=data.index,
                open=data['Open'],
                high=data['High'],
                low=data['Low'],
                close=data['Close'],
                name='Price'
            ),
            row=1, col=1
        )

        # Add indicators
        fig.add_trace(
            go.Line(x=data.index, y=data['EMA_short'], name='EMA Short'),
            row=1, col=1
        )
        fig.add_trace(
            go.Line(x=data.index, y=data['EMA_long'], name='EMA Long'),
            row=1, col=1
        )

        # Add RSI
        fig.add_trace(
            go.Line(x=data.index, y=data['RSI'], name='RSI'),
            row=2, col=1
        )

        # Add trade entry/exit points
        for trade in trades:
            fig.add_trace(
                go.Scatter(
                    x=[trade.entry_time],
                    y=[trade.entry_price],
                    mode='markers',
                    marker=dict(
                        symbol='triangle-up' if trade.direction == 'BUY' else 'triangle-down',
                        size=15,
                        color='green' if trade.direction == 'BUY' else 'red'
                    ),
                    name=f'{trade.direction} Entry'
                ),
                row=1, col=1
            )

        # Update layout
        fig.update_layout(
            title=title,
            yaxis_title='Price',
            yaxis2_title='RSI',
            xaxis_rangeslider_visible=False
        )

        # Save the plot
        fig.write_html(f'trades_{datetime.now().strftime("%Y%m%d_%H%M%S")}.html')

    def analyze_performance(self, trades: List[TradeResult]) -> Dict:
        """Analyze trading performance"""
        if not trades:
            return {}

        total_trades = len(trades)
        profitable_trades = len([t for t in trades if t.profit_loss > 0])
        win_rate = profitable_trades / total_trades * 100
        total_profit = sum(t.profit_loss for t in trades)
        avg_profit = total_profit / total_trades
        
        return {
            'total_trades': total_trades,
            'profitable_trades': profitable_trades,
            'win_rate': round(win_rate, 2),
            'total_profit': round(total_profit, 2),
            'average_profit': round(avg_profit, 2)
        }

    def run_practice_session(self, symbol: str, timeframe: str = '15m', 
                           strategy: str = 'RSI', period: str = '1mo'):
        """Run a complete practice trading session"""
        logging.info(f"Starting practice session for {symbol}")
        
        # Get historical data
        data = self.get_historical_data(symbol, period, timeframe)
        if data.empty:
            return
        
        # Calculate indicators
        data = self.calculate_indicators(data)
        
        # Run paper trading simulation
        trades = self.paper_trade(data, strategy)
        
        # Analyze performance
        performance = self.analyze_performance(trades)
        
        # Create visualization
        self.visualize_trades(data, trades, 
                            f"{symbol} {strategy} Strategy - {timeframe} Timeframe")
        
        # Log results
        logging.info("Practice Session Results:")
        logging.info(json.dumps(performance, indent=2))
        
        return performance, trades

def main():
    # Create trading system
    system = TradingSystem()
    
    # Example usage
    symbol = 'EUR/USD'
    timeframe = '15m'
    strategy = 'RSI'
    
    # Optional: Connect to demo account
    # system.connect_demo_account("your_email", "your_password")
    
    # Run practice session
    performance, trades = system.run_practice_session(symbol, timeframe, strategy)
    
    # Print results
    print("\nTrading Practice Results:")
    print(json.dumps(performance, indent=2))

if __name__ == "__main__":
    main()
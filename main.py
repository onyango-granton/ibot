import numpy as np
import pandas as pd
from deriv_api import DerivAPI
import asyncio
import json

class DerivTradingBot:
    def __init__(self, api_key):
        self.config = {
            'market': 'synthetic_index',
            'underlying': 'random_index',
            'symbol': '1HZ10V',
            'contract_type': 'callput',
            'duration': 60,  # 60 seconds
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
        
        # Initialize Deriv API connection
        self.api = DerivAPI(app_id=api_key)
        self.price_history = []

    def calculate_stochastic(self, df, high_col='high', low_col='low', close_col='price',
                           k_period=14, d_period=3, smooth_k=3):
        """Calculate Stochastic Oscillator without pandas_ta"""
        # Calculate %K
        df['highest_high'] = df[high_col].rolling(window=k_period).max()
        df['lowest_low'] = df[low_col].rolling(window=k_period).min()
        
        df['%K'] = 100 * (df[close_col] - df['lowest_low']) / (df['highest_high'] - df['lowest_low'])
        
        # Smooth %K
        if smooth_k > 1:
            df['%K'] = df['%K'].rolling(window=smooth_k).mean()
        
        # Calculate %D
        df['%D'] = df['%K'].rolling(window=d_period).mean()
        
        # Clean up temporary columns
        df = df.drop(['highest_high', 'lowest_low'], axis=1)
        
        return df
        
    async def connect(self):
        """Establish connection to Deriv API"""
        await self.api.connect()
        
    async def subscribe_to_ticks(self):
        """Subscribe to price updates"""
        request = {
            "ticks": self.config['symbol'],
            "subscribe": 1
        }
        
        async def process_ticks(update):
            tick = update['tick']
            self.price_history.append({
                'timestamp': tick['epoch'],
                'price': tick['quote']
            })
            await self.process_tick(tick)
            
        await self.api.subscribe(request, process_ticks)
        
    def calculate_indicators(self):
        """Calculate indicators from price history"""
        if len(self.price_history) < self.bb_period:
            return None
            
        df = pd.DataFrame(self.price_history)
        
        # Calculate Bollinger Bands
        df['bb_middle'] = df['price'].rolling(window=self.bb_period).mean()
        std = df['price'].rolling(window=self.bb_period).std()
        df['bb_upper'] = df['bb_middle'] + (std * self.bb_std)
        df['bb_lower'] = df['bb_middle'] - (std * self.bb_std)
        
        # Calculate high/low for Stochastic
        df['high'] = df['price'].rolling(window=self.stoch_k_period).max()
        df['low'] = df['price'].rolling(window=self.stoch_k_period).min()
        
        # Calculate Stochastic
        df = self.calculate_stochastic(
            df,
            k_period=self.stoch_k_period,
            d_period=self.stoch_d_period,
            smooth_k=self.smooth_period
        )
        
        return df
        
    async def process_tick(self, tick):
        """Process each new tick and generate trading signals"""
        df = self.calculate_indicators()
        if df is None or df.empty:
            return
            
        # Generate trading signal
        current_price = tick['quote']
        last_row = df.iloc[-1]
        
        if (last_row['%K'] < 20 and last_row['%D'] < 20 and
            current_price < last_row['bb_lower']):
            await self.place_trade('CALL')
            
        elif (last_row['%K'] > 80 and last_row['%D'] > 80 and
              current_price > last_row['bb_upper']):
            await self.place_trade('PUT')
            
    async def place_trade(self, direction):
        """Execute trade on Deriv platform"""
        contract_request = {
            "proposal": 1,
            "amount": self.config['stake'],
            "barrier": None,
            "basis": "stake",
            "contract_type": direction,
            "currency": "USD",
            "duration": self.config['duration'],
            "duration_unit": "s",
            "symbol": self.config['symbol']
        }
        
        try:
            response = await self.api.send(contract_request)
            if response.get('proposal'):
                buy_request = {
                    "buy": 1,
                    "price": response['proposal']['ask_price'],
                    "proposal": response['proposal']['id']
                }
                result = await self.api.send(buy_request)
                print(f"Trade executed: {direction} at {result['buy']['buy_price']}")
        except Exception as e:
            print(f"Error placing trade: {e}")
            
    async def run(self):
        """Main method to run the trading bot"""
        try:
            await self.connect()
            await self.subscribe_to_ticks()
            
            # Keep the bot running
            while True:
                await asyncio.sleep(1)
        except Exception as e:
            print(f"Error: {e}")
        finally:
            await self.api.disconnect()

# Example usage
async def main():
    api_key = "YOUR_DERIV_API_KEY"  # Replace with your API key
    bot = DerivTradingBot(api_key)
    await bot.run()

if __name__ == "__main__":
    asyncio.run(main())
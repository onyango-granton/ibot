# Trade Monitoring and Simulation Bot

A robust and intelligent trading bot built with Python for automating trades on the IQ Option platform using technical indicators such as RSI, EMA, Bollinger Bands, and volume profile analysis.

---

## Features

- **Automated trade monitoring** on the EURUSD asset (modifiable)
- **Technical indicators**:
    - RSI (Relative Strength Index)
    - EMA (Exponential Moving Averages)
    - Bollinger Bands
    - Volume Profile analysis
- **Trade signals** with multi-factor confirmation logic
- **Risk management**:
    - Daily loss cap
    - Max trade limits
    - Risk-reward validation
- **Trade result tracking**: wins, losses, profit, and win rate
- **Real-time candle stream support**
- **PRACTICE and REAL modes** supported

---

## Requirements

- Python 3.7+
- IQ Option API wrapper: `iqoptionapi`
- Other Python dependencies:
    ```bash
    pip install numpy pandas
    ```

---

## Setup & Installation

1. Clone this repository:
     ```bash
     git clone https://github.com/yourusername/iqoption-trading-bot.git
     cd ibot
     ```

2. Install dependencies:
     ```bash
     pip install -r requirements.txt
     ```

3. Configure your credentials:
     Modify the instantiation of the bot with your IQ Option credentials:
     ```python
     bot = IQOptionTradingBot("your_email@example.com", "your_password")
     bot.run()
     ```

---

## Configuration

The bot uses the following default configuration:
```python
'asset': 'EURUSD',       # Target asset
'duration': 1,           # Trade duration in minutes
'amount': 1.00,          # Trade amount in USD
'mode': 'PRACTICE'       # PRACTICE or REAL
```

Risk & strategy parameters like EMA periods, RSI thresholds, and max daily loss are customizable within the `__init__()` method.

---

## How It Works

1. Connects securely to IQ Option.
2. Fetches historical candles and computes technical indicators.
3. Subscribes to real-time candle stream.
4. Continuously checks if trade conditions are met using:
     - Bollinger Band deviations
     - RSI overbought/oversold conditions
     - EMA crossovers
     - Volume confirmation
5. Places call or put trades based on signal strength and risk-reward ratio.
6. Tracks performance and respects trade/risk limits.

---

## Logging

The bot uses Python’s `logging` module to track connection status, trades, and errors. Log messages help monitor performance and debug issues.

---

## Disclaimer

This bot is for **educational purposes only**.  
Use in REAL mode at your own risk. Trading involves substantial risk and may not be suitable for all investors.

---

## License

MIT License. See the [LICENSE](LICENSE) file for details.

---

## Contributing

Pull requests and suggestions are welcome!  
Feel free to fork the repo and submit changes or improvements.
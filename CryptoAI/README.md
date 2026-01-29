# CryptoAI Trading Assistant 🚀

A sophisticated cryptocurrency trading assistant that provides **live market data** and **intelligent trade suggestions** for managing a $900-1000 wallet.

## Features ✨

- **Live Market Data**: Real-time cryptocurrency prices from CoinGecko API
- **Intelligent Trade Suggestions**: AI-powered analysis with technical indicators
- **Portfolio Management**: Track positions, profits/losses, and trade history
- **Technical Analysis**: RSI, MACD, Moving Averages, Bollinger Bands, and more
- **Market Sentiment**: Global market overview and trending cryptocurrencies
- **Risk Management**: Customizable risk profiles with stop-loss and take-profit levels
- **Simulated Trading**: Practice trading without real money

## Quick Start 🚀

### 1. Install Dependencies

```powershell
pip install -r requirements.txt
```

### 2. Configure Settings (Optional)

Edit `.env` file to customize your wallet size and risk preferences:

```
WALLET_SIZE=1000
RISK_LEVEL=medium  # low, medium, high
```

### 3. Run the Application

**Option A: Web Dashboard (Recommended)** 🌐
```powershell
python dashboard.py
```
Then open your browser to: **http://127.0.0.1:8050**

**Option B: CLI Version** 💻
```powershell
python main.py
```

## User Interfaces 🖥️

### Web Dashboard (Recommended)
Modern, interactive web interface with:
- **Real-time Updates**: Auto-refresh every 30 seconds
- **Interactive Tabs**: Trade suggestions, portfolio, market analysis, coin research
- **Live Charts**: Visual representations of data
- **One-Click Trading**: Easy trade execution with forms
- **Responsive Design**: Works on desktop and mobile
- **Dark Theme**: Easy on the eyes for long trading sessions

### CLI Interface
Terminal-based interface with:
- **Menu-Driven**: Simple navigation
- **Colored Output**: Easy to read data
- **Lightweight**: Fast and efficient
- **SSH-Friendly**: Works in remote sessions

## Main Features 📊

### 1. Live Trade Suggestions
- Analyzes top cryptocurrencies using multiple technical indicators
- Provides buy/sell signals with confidence levels
- Calculates optimal position sizes based on risk profile
- Includes stop-loss and take-profit recommendations
- Score-based ranking system (0-100)

### 2. Market Overview
- Global market statistics and sentiment analysis
- Bitcoin and Ethereum dominance
- Top gainers in the last 24 hours
- Market cap changes and trends
- Trending cryptocurrencies

### 3. Portfolio Management
- Track your simulated trades
- Real-time portfolio valuation
- Profit/loss tracking for each position
- Complete trade history
- Easy trade execution

### 4. Technical Analysis
- **RSI (Relative Strength Index)**: Identifies overbought/oversold conditions
- **MACD (Moving Average Convergence Divergence)**: Trend momentum indicator
- **Moving Averages**: SMA and EMA for trend analysis
- **Bollinger Bands**: Volatility and price level analysis
- **Support/Resistance Levels**: Key price levels
- **Trend Detection**: Identifies market direction

## Configuration ⚙️

### Risk Profiles

**Low Risk (Conservative)**
- Max position size: 10% of wallet
- Focuses on BTC, ETH, BNB
- Lower volatility tolerance

**Medium Risk (Balanced)** - Default
- Max position size: 15% of wallet
- Includes major and mid-cap coins
- Moderate volatility tolerance

**High Risk (Aggressive)**
- Max position size: 20% of wallet
- All cryptocurrencies eligible
- Higher volatility tolerance

### Trading Parameters

Edit in `.env`:
```
MAX_POSITION_SIZE=0.15    # Max 15% per trade
MIN_POSITION_SIZE=0.03    # Min 3% per trade
STOP_LOSS_PERCENT=5       # 5% stop loss
TAKE_PROFIT_PERCENT=15    # 15% take profit
```dashboard.py           # Web-based UI (Recommended)
├── main.py                # CLI application interface
├── config.py              # Configuration management
├── data_fetcher.py        # Live data fetching from APIs
├── technical_analyzer.py  # Technical analysis engine
├── trading_engine.py      # Trading strategy and suggestions
├── portfolio.py           # Portfolio management
├── requirements.txt       # Python dependencies
├── .env                   # Environment configuration
├── START_HERE.md          # Quick start guide
## Technical Indicators 📈

The system uses multiple indicators to generate signals:

1. **RSI**: Oversold (<30) = Buy, Overbought (>70) = Sell
2. **Moving Averages**: Price above MA = Bullish
3. **MACD**: Positive divergence = Buy signal
4. **Bollinger Bands**: Price near lower band = Buy
5. **Volume Analysis**: Confirms trend strength

## Project Structure 📁

```
CryptoAI/
├── main.py                 # Main application interface
├── config.py              # Configuration management
├── data_fetcher.py        # Live data fetching from APIs
├── technical_analyzer.py  # Technical analysis engine
├── trading_engine.py      # Trading strategy and suggestions
├── portfolio.py           # Portfolio management
├── requirements.txt       # Python dependencies
├── .env                   # Environment configuration
└── portfolio_data.json    # Portfolio state (auto-generated)
```

## Usage Examples 💡

### Get Trade Suggestions
```
Select option: 1

🤖 Generating Live Trade Suggestions...

#1 - ETHEREUM
Signal: BUY
Confidence: 78.5%
Current Price: $2,345.67
Suggested Investment: $120.00
Stop Loss: $2,228.39
Take Profit: $2,697.52
```

### View Portfolio
```
Select option: 3

💼 Portfolio Performance:
Current Value: $1,145.23
Total Return: +$145.23 (+14.52%)
Active Positions: 3
```

## API Rate Limits ⚠️

- CoinGecko Free Tier: 10-50 calls/minute
- The app implements caching to minimize API calls
- No API key required for basic features

## Disclaimer ⚠️

**This is a simulated trading assistant for educational purposes only.**

- Does NOT execute real trades
- Does NOT connect to real exchange accounts
- Use at your own risk for learning and research
- Always do your own research (DYOR) before investing real money
- Cryptocurrency trading carries significant risk

## Future Enhancements 🔮

- [ ] Live price charts and visualizations
- [ ] More advanced trading strategies
- [ ] Backtesting capabilities
- [ ] Webhook notifications
- [ ] Mobile app integration
- [ ] Machine learning price predictions

## Dependencies 📦

- `requests` - HTTP requests
- `pandas` - Data manipulation
- `numpy` - Numerical computing
- `ta` - Technical analysis indicators
- `ccxt` - Cryptocurrency exchange integration
- `pycoingecko` - CoinGecko API wrapper
- `colorama` - Terminal colors
- `tabulate` - Table formatting

## Support 💬

For issues or questions:
1. Check the configuration in `.env`
2. Verify internet connection
3. Ensure all dependencies are installed
4. Check API rate limits

## License 📄

MIT License - Feel free to use and modify for your own purposes.

---

**Happy Trading! 🚀📈**

Remember: The best investment is in your education. Learn, practice with simulations, then trade responsibly.

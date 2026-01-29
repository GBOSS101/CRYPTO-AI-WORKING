# 🔮 CryptoAI - BTC Prediction Market Bot

## ML-Powered Bitcoin Trading with Prediction Markets

A sophisticated cryptocurrency trading bot that combines machine learning (LSTM + XGBoost), technical analysis, and prediction market data to forecast Bitcoin price movements and execute trades.

---

## 🌟 Features

### Machine Learning Engine

- **Hybrid ML Models**: LSTM neural networks + XGBoost gradient boosting
- **Ensemble Predictions**: Combines multiple models with weighted voting
- **Auto-Training**: Automatically trains on 30+ days of historical data
- **Feature Engineering**: 40+ technical indicators and lag features

### Prediction Markets

- **Real-time Market Data**: Live BTC prices from Coinbase/CoinGecko
- **Order Book Analysis**: Deep order book imbalance detection
- **Funding Rate Tracking**: Perpetual swap funding rate monitoring
- **Fear & Greed Index**: Sentiment-based contrarian signals

### Technical Analysis

- **15+ Indicators**: RSI, MACD, Bollinger Bands, SMA, EMA, ATR, etc.
- **Multi-Timeframe**: Analyzes 1h, 4h, and 24h trends
- **Pattern Recognition**: Detects bullish/bearish patterns
- **Volume Confirmation**: Validates signals with volume data

### Automated Trading

- **Risk Management**: Configurable position sizing (10%-20% of portfolio)
- **Stop Loss & Take Profit**: Automatic exit strategies
- **Signal Confidence**: Only trades high-confidence predictions (>60%)
- **Cooldown Periods**: Prevents overtrading
- **Simulation Mode**: Test strategies risk-free

### Dashboard UI

- **Real-time Updates**: 30-second refresh interval
- **Interactive Charts**: Plotly-powered visualizations
- **Signal Strength Gauge**: Visual confidence indicators
- **Trade Recommendations**: Detailed entry/exit suggestions
- **Performance Tracking**: Win rate, P&L, and trade history

---

## 🚀 Quick Start

### 1. Installation

```powershell
# Clone or navigate to CryptoAI directory
cd c:\CryptoAI

# Install dependencies (automatic on first run)
pip install -r requirements.txt
```

### 2. Run Prediction Dashboard

```powershell
# Double-click or run:
.\start_prediction_dashboard.ps1
```

Opens web dashboard at `http://localhost:8050`

### 3. Run Prediction Bot (CLI)

```powershell
# Interactive bot with menu:
.\start_prediction_bot.ps1
```

Choose simulation or live mode, risk level, and start trading.

---

## 📊 How It Works

### Data Flow

```text
CoinGecko API → Market Data Fetcher → Feature Engineering
                                              ↓
                                        ML Models (LSTM + XGBoost)
                                              ↓
Technical Analysis ← ← ← ← ← ← ← →  Prediction Analyzer
Order Book Data                              ↓
Sentiment Data                         Trade Signals
                                              ↓
                                        Trading Bot
                                              ↓
                                   Execute Buy/Sell (if auto-trade)
```

### Signal Calculation

#### Overall Signal Formula

Overall Signal = 40% Technical + 35% ML Prediction + 15% Sentiment + 10% Order Book

- **Buy Signal**: Score > 60, Confidence > 60%
- **Strong Buy**: Score > 75, Confidence > 70%
- **Sell Signal**: Score < 40, Confidence > 60%
- **Neutral**: All other conditions

### ML Prediction Process

1. **Fetch Historical Data** (30 days, hourly)
2. **Engineer Features** (price, volume, indicators, lags)
3. **Train Models**:
   - XGBoost: 100 estimators, 7 max depth
   - LSTM: 2 layers (50 units each), dropout 0.2
4. **Generate Prediction** (24h horizon)
5. **Calculate Confidence** (model agreement)

---

## 🎯 Usage Examples

### Dashboard Mode

```powershell
.\start_prediction_dashboard.ps1
```

**Dashboard Features:**

- 📈 Real-time BTC price and predictions
- 🎯 ML model confidence and accuracy
- 📊 Signal strength gauge (0-100)
- 💡 Trade recommendations with reasons
- 😱 Fear & Greed sentiment meter
- 📉 Order book imbalance visualization
- 📈 Price chart with prediction overlay

**Actions:**

- **Train Models**: Click button to retrain on fresh data
- **Start Bot**: Activate auto-trading (simulation)
- **Adjust Risk**: Change position sizing

### Bot CLI Mode

```powershell
.\start_prediction_bot.ps1

# Select mode:
# 1. SIMULATION (no real trades)
# 2. LIVE (real trades - requires confirmation)

# Select risk:
# 1. Low (10% positions)
# 2. Medium (15% positions)
# 3. High (20% positions)
```

**Bot Output:**

```text
[14:32:15] BTC: $62,450.00
Signal: BUY | Confidence: 72% | Score: 68/100

🟢 SIMULATION BUY SIGNAL
  Amount: 0.00240000 BTC ($150.00)
  Entry: $62,450.00
  Stop Loss: $59,327.50
  Take Profit: $65,572.50
  Confidence: 72%
  Reasons: ML predicts +5.2% move, RSI oversold (<30)

💡 SIMULATION MODE - Trade not executed
```

---

## ⚙️ Configuration

### Risk Levels

Edit in `config.py`:

```python
RISK_PROFILES = {
    'low': {
        'max_position': 0.10,  # 10% of portfolio
        'preferred_assets': ['bitcoin', 'ethereum']
    },
    'medium': {
        'max_position': 0.15,  # 15% of portfolio
        'preferred_assets': ['bitcoin', 'ethereum', 'bnb']
    },
    'high': {
        'max_position': 0.20,  # 20% of portfolio
        'preferred_assets': None  # All assets
    }
}
```

### ML Model Parameters

Edit in `ml_prediction_engine.py`:

```python
# XGBoost
n_estimators = 100      # Number of trees
learning_rate = 0.05    # Step size
max_depth = 7           # Tree depth

# LSTM
units = 50              # LSTM units per layer
lookback_period = 60    # Hours of history
prediction_horizon = 24 # Hours to predict
```

### Trading Parameters

Edit in `prediction_trading_bot.py`:

```python
min_confidence = 0.65         # Min confidence for trades
cooldown_period = timedelta(hours=1)  # Time between trades
max_open_positions = 3        # Max concurrent positions
```

---

## 📁 Project Structure

```text
c:\CryptoAI\
├── prediction_market_fetcher.py    # Fetches market data
├── ml_prediction_engine.py         # LSTM + XGBoost models
├── prediction_market_analyzer.py   # Combines signals
├── prediction_trading_bot.py       # Automated trading bot
├── dashboard_predictions.py        # Web dashboard UI
├── start_prediction_dashboard.ps1  # Dashboard launcher
├── start_prediction_bot.ps1        # Bot launcher
├── requirements.txt                # Python dependencies
└── README_PREDICTIONS.md           # This file
```

**Integration with Existing CryptoAI:**

- Uses existing `portfolio.py` for position management
- Uses existing `technical_analyzer.py` for indicators
- Uses existing `config.py` for settings
- Adds ML prediction capabilities on top

---

## 🧠 Machine Learning Details

### LSTM Architecture

```text
Input Layer (60 timesteps × 6 features)
    ↓
LSTM Layer (50 units, return sequences)
    ↓
Dropout (0.2)
    ↓
LSTM Layer (50 units)
    ↓
Dropout (0.2)
    ↓
Dense Layer (25 units)
    ↓
Output Layer (1 unit - predicted price)
```

**Features Used:**

- Price, Volume, SMA(7), EMA(14), RSI, Volatility

### XGBoost Model

**Features (40+):**

- Price lags (1h, 2h, 3h, 6h, 12h, 24h)
- Returns and log returns
- Moving averages (7, 14, 21, 50 period)
- Volatility (7, 21 period)
- RSI (14 period)
- MACD and signal line
- Volume ratios
- Price position (relative to 14-day range)

**Target:** Price 24 hours ahead

### Ensemble Strategy

```text
Prediction = (
    0.40 × LSTM_prediction +
    0.30 × XGBoost_prediction +
    0.30 × Technical_trend
)

Confidence = 1 - std(predictions) / current_price
```

---

## 📈 Performance Metrics

Bot tracks:

- **Win Rate**: % of profitable trades
- **Total Profit/Loss**: USD gains/losses
- **Best/Worst Trade**: Highest/lowest % return
- **Sharpe Ratio**: Risk-adjusted returns
- **Max Drawdown**: Largest peak-to-trough decline

Access via dashboard or `trade_history.json`

---

## 🔐 Safety Features

### Simulation Mode (Default)

- No real trades executed
- Test strategies risk-free
- Full market analysis and signals
- Performance tracking

### Live Mode Safeguards

- Requires explicit confirmation
- Stop loss on all positions (5% default)
- Take profit targets (10% default)
- Maximum position limits
- Cooldown between trades

### Risk Management

- Never exceeds configured position size
- Monitors portfolio drawdown
- Pauses trading if too many losses
- Diversification across positions

---

## 🐛 Troubleshooting

### "XGBoost not installed"

```powershell
pip install xgboost
```

### "TensorFlow not installed"

```powershell
pip install tensorflow
```

### "Failed to fetch historical data"

- Check internet connection
- CoinGecko API may have rate limits (wait 1 minute)
- Try different `days` parameter

### Models not training

- Need at least 100 data points (4-5 days hourly data)
- Check if historical data is empty
- Reduce `lookback_period` if insufficient data

### Dashboard not updating

- Check 30s interval component
- Refresh browser (Ctrl+R)
- Check console for errors (F12)

---

## 🚦 Best Practices

### For Testing

1. **Start in Simulation Mode** - Always test strategies first
2. **Train Models Daily** - Retrain with fresh data
3. **Monitor Confidence** - Only trust >70% signals
4. **Check Reasons** - Understand why bot suggests trades

### For Live Trading

1. **Start Small** - Use low risk level initially
2. **Set Limits** - Define max loss per day
3. **Review Manually** - Don't blindly follow signals
4. **Diversify** - Don't put all funds in one position
5. **Monitor Closely** - Check bot frequently

### Model Tuning

1. **Increase Training Data** - Use 60+ days for better accuracy
2. **Adjust Lookback** - Try 90 or 120 periods for LSTM
3. **Feature Selection** - Remove low-importance features
4. **Hyperparameter Tuning** - Experiment with XGBoost params

---

## 📚 Resources

### Recommended Repositories (from your research)

- **Freqtrade**: <https://github.com/freqtrade/freqtrade>
- **FinRL**: <https://github.com/AI4Finance-Foundation/FinRL>
- **backtesting.py**: <https://github.com/kernc/backtesting.py>

### APIs Used

- **CoinGecko**: Free crypto market data
- **Coinbase Pro**: Order book and live prices
- **Alternative.me**: Fear & Greed Index

### Libraries

- **XGBoost**: Gradient boosting
- **TensorFlow/Keras**: Deep learning (LSTM)
- **scikit-learn**: Data preprocessing
- **TA-Lib**: Technical analysis
- **Dash/Plotly**: Interactive dashboards

---

## 🎓 How to Improve

### Add More Models

- **Prophet**: Facebook's time series forecasting
- **LightGBM**: Alternative to XGBoost
- **Transformer**: Attention-based architecture

### Advanced Features

- **News Sentiment**: Scrape crypto news headlines
- **Social Media**: Twitter sentiment analysis
- **On-Chain Data**: Blockchain metrics (whale movements)
- **Multi-Asset**: Predict ETH, SOL, BNB too

### Better Risk Management

- **Kelly Criterion**: Optimal position sizing
- **Portfolio Optimization**: Markowitz theory
- **VaR/CVaR**: Value at Risk calculations

---

## 📞 Support

For issues or questions:

1. Check `SYSTEM_REVIEW.md` for existing features
2. Review `QUICK_REFERENCE.txt` for commands
3. Check console output for error messages
4. Verify all dependencies are installed

---

## ⚠️ Disclaimer

**This is a simulated trading bot for educational purposes.**

- Cryptocurrency trading is **extremely risky**
- Past performance does not guarantee future results
- ML predictions are **not financial advice**
- Always do your own research (DYOR)
- Never invest more than you can afford to lose
- The developers are not responsible for financial losses

### Use At Your Own Risk

---

## 🎉 Quick Start Commands

```powershell
# Dashboard (web UI)
.\start_prediction_dashboard.ps1

# Bot (CLI)
.\start_prediction_bot.ps1

# Train models manually
python -c "from prediction_market_analyzer import *; a = PredictionMarketAnalyzer(); print(a.train_models())"

# Get quick prediction
python -c "from prediction_market_analyzer import *; a = PredictionMarketAnalyzer(auto_train=False); print(a.get_prediction_summary())"

# Test all components
python prediction_market_fetcher.py
python ml_prediction_engine.py
python prediction_market_analyzer.py
```

---

### Happy Trading! 🚀📈💰

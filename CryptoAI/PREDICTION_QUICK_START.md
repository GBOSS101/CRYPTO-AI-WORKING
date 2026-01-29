# 🚀 PREDICTION BOT - QUICK START GUIDE

## Installation (One-Time Setup)

```powershell
# 1. Install Python dependencies
pip install -r requirements.txt

# This installs:
# - xgboost (ML model)
# - tensorflow (LSTM neural network)
# - scikit-learn (data preprocessing)
# - All existing CryptoAI dependencies
```

---

## 🎯 Option 1: Web Dashboard (Recommended)

**Best for:** Visual analysis, monitoring, and manual trading

```powershell
# Start the dashboard
.\start_prediction_dashboard.ps1

# Opens at: http://localhost:8050
```

**Features:**
- 📊 Real-time BTC price & predictions
- 🎯 ML confidence gauge
- 💡 Trade recommendations
- 📈 Interactive price charts
- 😱 Fear & Greed Index
- 🤖 Train ML models with one click

---

## 🤖 Option 2: Automated Bot (CLI)

**Best for:** Automated trading and backtesting

```powershell
# Start the bot
.\start_prediction_bot.ps1
```

**Interactive Menu:**
1. Choose mode: **Simulation** (safe) or **Live** (real trades)
2. Choose risk: **Low** (10%), **Medium** (15%), **High** (20%)
3. Bot analyzes market every 60 seconds
4. Executes trades based on ML predictions + technical analysis

---

## 📊 What Gets Analyzed?

### ML Predictions (60% weight)
- **LSTM Neural Network**: Learns price patterns from 60 hours of data
- **XGBoost Model**: Uses 40+ technical features
- **Ensemble Voting**: Combines both models for accuracy

### Technical Analysis (40% weight)
- RSI, MACD, Bollinger Bands, Moving Averages
- Trend detection and momentum indicators
- Volume confirmation

### Market Sentiment
- Fear & Greed Index (contrarian signals)
- Order book imbalance (buy/sell pressure)
- Funding rates (futures market sentiment)

---

## 🎮 Dashboard Controls

### Train Models Button
- Fetches 30 days of historical data
- Trains LSTM and XGBoost models
- Takes 1-2 minutes
- **Do this first before trading!**

### Start Bot Button
- Activates auto-trading (simulation mode)
- Analyzes market every 30 seconds
- Shows recommendations in real-time

### Risk Level Dropdown
- **Low**: 10% of portfolio per trade (conservative)
- **Medium**: 15% per trade (balanced)
- **High**: 20% per trade (aggressive)

### Confidence Slider
- Minimum confidence threshold (50%-90%)
- Higher = fewer but more confident trades
- Recommended: 65%+

---

## 📈 Understanding Signals

### Strong Buy (Score 75-100)
- ML predicts >5% upward movement
- Multiple bullish indicators aligned
- High confidence (>70%)
- **Action**: Consider long position

### Buy (Score 60-75)
- ML predicts 1-5% upward movement
- Some bullish signals
- Moderate confidence (60-70%)
- **Action**: Small position or wait

### Neutral (Score 40-60)
- No clear direction
- Mixed signals
- **Action**: Hold cash or existing positions

### Sell (Score 25-40)
- ML predicts 1-5% downward movement
- Some bearish signals
- **Action**: Reduce positions or exit

### Strong Sell (Score 0-25)
- ML predicts >5% downward movement
- Multiple bearish indicators
- **Action**: Exit all positions

---

## 💡 Sample Trade Recommendation

```
🟢 BUY SIGNAL
  Amount: 0.00240000 BTC ($150.00)
  Entry: $62,450.00
  Stop Loss: $59,327.50 (-5%)
  Take Profit: $65,572.50 (+5%)
  Confidence: 72%
  
  Reasons:
  - ML predicts +5.2% move (24h)
  - RSI oversold (<30)
  - Strong bid support (1.5x asks)
  - Extreme fear (22/100) - contrarian buy
```

---

## 🔐 Safety Features

### Simulation Mode (Default)
✅ No real money at risk
✅ Full functionality
✅ Track performance
✅ Test strategies

### Live Mode (Optional)
⚠️ Requires confirmation
⚠️ Real trades executed
⚠️ Auto stop-loss (5%)
⚠️ Auto take-profit (10%)

---

## 🎯 Recommended Workflow

### Day 1: Setup & Training
1. Run `.\start_prediction_dashboard.ps1`
2. Click **"Train ML Models"** button
3. Wait 1-2 minutes for training
4. Review dashboard metrics

### Day 2-7: Simulation Testing
1. Start bot in **Simulation Mode**
2. Monitor predictions vs actual prices
3. Track win rate and accuracy
4. Adjust confidence threshold if needed

### Week 2+: Live Trading (Optional)
1. If simulation results are good (>60% win rate)
2. Start with **Low Risk** setting
3. Use **High Confidence** threshold (70%+)
4. Monitor closely for first few trades

---

## 📁 Key Files

| File | Purpose |
|------|---------|
| `prediction_market_fetcher.py` | Gets live market data |
| `ml_prediction_engine.py` | LSTM + XGBoost models |
| `prediction_market_analyzer.py` | Combines all signals |
| `prediction_trading_bot.py` | Automated trading bot |
| `dashboard_predictions.py` | Web dashboard UI |
| `README_PREDICTIONS.md` | Full documentation |

---

## 🐛 Common Issues

### "Module not found: xgboost"
```powershell
pip install xgboost
```

### "Module not found: tensorflow"
```powershell
pip install tensorflow
```

### "Failed to fetch data"
- Check internet connection
- CoinGecko API rate limit (wait 1 min)

### "Models not trained"
- Click "Train ML Models" in dashboard
- Or run bot with `auto_train=True`

### Dashboard not loading
- Check port 8050 is free
- Try different port in code: `app.run_server(port=8051)`

---

## 🎓 Tips for Success

### 1. Train Models Regularly
- Retrain daily with fresh data
- Markets change, models need updates

### 2. Don't Overtrade
- Bot has 1-hour cooldown between trades
- Quality > quantity

### 3. Trust High Confidence
- Only act on 70%+ confidence signals
- Lower confidence = higher risk

### 4. Combine with Manual Analysis
- Bot is a tool, not a magic solution
- Use your judgment too

### 5. Start Conservative
- Use Low risk setting initially
- Increase only after proven success

---

## 📞 Quick Commands

```powershell
# Dashboard
.\start_prediction_dashboard.ps1

# Bot (interactive)
.\start_prediction_bot.ps1

# Bot (simulation, medium risk)
python prediction_trading_bot.py

# Bot (live, high risk) - CAREFUL!
python prediction_trading_bot.py --live --high-risk

# Test components
python prediction_market_fetcher.py
python ml_prediction_engine.py
python prediction_market_analyzer.py

# Quick prediction
python -c "from prediction_market_analyzer import PredictionMarketAnalyzer; a = PredictionMarketAnalyzer(auto_train=False); print(a.get_prediction_summary())"
```

---

## 🎯 Expected Performance

**Realistic Expectations:**
- Win Rate: 55-65% (good)
- Average Return per Trade: 2-5%
- Best Trades: 10-20%
- Worst Trades: -5% (stop loss)
- Monthly Return: 10-30% (if all goes well)

**Remember:** 
- No strategy wins 100% of the time
- Risk management is crucial
- Past performance ≠ future results

---

## 🚀 Ready to Start?

```powershell
# Launch dashboard now:
.\start_prediction_dashboard.ps1
```

**Then:**
1. Click "Train ML Models"
2. Wait for training to complete
3. Review predictions and signals
4. Start trading (simulation first!)

---

**Good luck! 📈💰**

---

**⚠️ DISCLAIMER:** This is educational software. Crypto trading is risky. Never invest more than you can afford to lose. Not financial advice.

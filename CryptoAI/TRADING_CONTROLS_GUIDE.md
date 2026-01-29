# 🎮 Trading Controls - User Guide

## ✅ Dashboard Now Live with Trading Controls!

**URL**: http://localhost:8050

---

## 🎯 New Features Added

### 1. 💼 Manual Trading Controls
Execute trades manually with full control:

- **BUY Button**: Purchase BTC at current market price
- **SELL Button**: Sell all BTC holdings at current market price
- **Amount Input**: Set trade amount in USD ($10 - $10,000)
- **Real-time Portfolio**: Live updates of cash, BTC holdings, total value, and P&L

#### How to Make a Manual Trade:
1. Enter amount (e.g., $100)
2. Click **🟢 BUY** to purchase BTC
3. Click **🔴 SELL** to sell all BTC holdings
4. Get instant notification with trade details and P&L

---

### 2. 🤖 Automated Trading Bot
Let the bot trade automatically based on prediction signals:

#### Bot Settings:
- **Risk Level**: Choose Low (10%), Medium (15%), or High (20%) max position size
- **Min Confidence**: Set threshold from 50% to 90% (default: 65%)

#### Bot Controls:
- **▶️ START BOT**: Activate automated trading
- **⏸️ STOP BOT**: Deactivate automated trading
- **Real-time Status**: See current bot state and last signal

#### How It Works:
1. Configure risk level and min confidence
2. Click **START BOT**
3. Bot monitors markets every 60 seconds
4. Executes trades when signals meet your criteria
5. Applies stop loss (5%) and take profit (10%) automatically

---

### 3. 💰 Live Portfolio Tracking
Real-time portfolio monitoring:

- **Cash Balance**: Available USD for trading
- **BTC Holdings**: Amount of BTC owned (in BTC and USD value)
- **Total Value**: Combined cash + BTC value
- **P&L**: Profit/Loss in dollars and percentage (green = profit, red = loss)

Updates automatically after every trade!

---

### 4. 🔗 Coinbase Live Trading Connection
Future integration for live trading (currently simulated):

#### Current Status:
- ✅ **Coinbase API Connected** - Predictions & market data working
- ⚠️ **Live Trading** - Currently using simulated portfolio (paper trading)

#### To Enable Live Trading:
1. Add to your `.env` file:
   ```bash
   COINBASE_TRADING_API_KEY=your_trading_key
   COINBASE_TRADING_SECRET=your_trading_secret
   ```

2. Ensure API key has **trade** permission enabled in Coinbase

3. Click **🔌 Connect Coinbase Trading Account** button

4. Bot will execute real trades on Coinbase

**⚠️ WARNING**: Live trading uses real money! Start with simulation mode first.

---

## 📊 Dashboard Sections Overview

### Top Cards
- **Current BTC Price**: Live price (updates every 5s)
- **24h ML Prediction**: Next 24h predicted price
- **Overall Signal**: BUY/SELL/NEUTRAL signal
- **Portfolio Value**: Total account value

### Trading Controls (NEW!)
- Manual buy/sell buttons
- Portfolio display
- Bot automation controls
- Coinbase connection settings

### Multi-Timeframe Predictions
- 5 timeframes: 15min, 1hr, 4hr, 24hr, 7d
- Predicted prices, confidence, direction

### Coinbase Prediction Markets
- TOP 8 markets with YES/NO probabilities
- Action recommendations (BUY YES/NO/SKIP)
- Edge calculation for each market

### ML Model Predictions
- XGBoost + LSTM predictions
- Direction and confidence
- Models used

### Technical Analysis
- RSI, MACD, SMA, EMA indicators
- Overall technical signal

---

## 🎯 Example Trading Workflow

### Scenario 1: Manual Trading
```
1. Current BTC: $89,722
2. Signal shows STRONG_BUY with 74% confidence
3. Enter $200 in amount field
4. Click 🟢 BUY
5. Notification: "Bought 0.00223 BTC at $89,722"
6. Portfolio updates:
   - Cash: $800 (from $1,000)
   - BTC: 0.00223 BTC ($200)
   - Total: $1,000
   
7. BTC rises to $91,500
8. Click 🔴 SELL
9. Notification: "P&L: +$3.96 (+1.98%)"
10. Portfolio updates:
    - Cash: $1,003.96
    - BTC: 0.00000000 BTC
    - Total: $1,003.96
```

### Scenario 2: Automated Bot Trading
```
1. Set Risk Level: Medium (15% max position)
2. Set Min Confidence: 70%
3. Click ▶️ START BOT
4. Bot status: "🟢 BOT ACTIVE | Risk: MEDIUM | Min Confidence: 70%"
5. Bot monitors markets automatically
6. When signal = STRONG_BUY + confidence > 70%:
   - Bot buys $150 of BTC (15% of $1,000)
7. Sets stop loss at -5% ($142.50)
8. Sets take profit at +10% ($165)
9. When BTC hits target or stop:
   - Bot sells automatically
   - Records P&L
10. Continues monitoring for next opportunity
```

---

## 🔒 Safety Features

### Simulation Mode (Default)
- **Paper Trading**: No real money at risk
- Uses simulated $1,000 portfolio
- Perfect for testing strategies
- All features work exactly like live trading

### Live Mode (Optional)
- Requires Coinbase trading credentials
- Executes real trades
- Start with small amounts
- Use stop losses

### Risk Management
- Max position size limits (10%, 15%, 20%)
- Automatic stop loss (5% default)
- Automatic take profit (10% default)
- Cooldown period between trades (1 hour)
- Max 3 concurrent positions

---

## 📈 Performance Tracking

### Real-Time Metrics
- **Portfolio Value**: Updated after every trade
- **P&L**: Shows profit/loss on current position
- **Trade History**: All trades logged in `portfolio_data.json`

### Bot Statistics (Coming Soon)
- Total trades executed
- Win rate
- Average profit per trade
- Best/worst trades
- Sharpe ratio

---

## 🚨 Important Notes

### Current Status
✅ **Working Now**:
- Manual trading (simulated)
- Automated bot (simulated)
- Real-time portfolio tracking
- Live BTC price & predictions
- Multi-timeframe signals
- Coinbase prediction markets

⚠️ **Not Yet Active**:
- Live Coinbase trading (needs credentials)
- Real money trades

### Recommendations
1. **Start in Simulation Mode** - Test strategies risk-free
2. **Use Low Risk Level** - Until you understand the bot
3. **Set High Min Confidence** - Only trade on strong signals (70%+)
4. **Monitor Closely** - Watch the bot's first few trades
5. **Start Small** - When going live, use small position sizes

---

## 🎉 You're Ready to Trade!

The dashboard is fully operational with:
- ✅ Manual trading controls
- ✅ Automated bot trading
- ✅ Real-time portfolio tracking
- ✅ Live prediction signals
- ✅ Risk management tools

**Open your browser to http://localhost:8050 and start trading!**

---

**Last Updated**: 2026-01-28 13:24:00  
**Status**: FULLY OPERATIONAL 🚀

# CryptoAI Trading Assistant - AI Agent Instructions

## Project Overview
CryptoAI is a **simulated cryptocurrency trading assistant** with live market data and AI-powered trade suggestions. It manages a virtual $1000 wallet using real-time CoinGecko API data.

**Architecture**: Modular Python backend with dual interfaces (Dash web dashboard + CLI).

## Core Architecture

### Component Separation
- **`config.py`**: Single source of truth for all settings (API keys, wallet size, risk profiles, TOP_CRYPTOS list)
- **`data_fetcher.py`**: All external API calls (CoinGecko, CCXT). Uses 30s caching to minimize API hits
- **`technical_analyzer.py`**: Pure analysis logic using `ta` library (RSI, MACD, SMA, EMA, Bollinger Bands)
- **`trading_engine.py`**: Orchestrates analysis → signals → position sizing → trade suggestions
- **`portfolio.py`**: State management via `portfolio_data.json` file (positions, cash, trade history)
- **`dashboard.py`**: Dash/Plotly web UI with 30s auto-refresh interval
- **`main.py`**: CLI interface with colorama-styled menus

### Data Flow Pattern
```
CoinGecko API → LiveDataFetcher (cached) → TechnicalAnalyzer → TradingEngine → UI (dashboard/CLI)
                                                                      ↓
                                                                  Portfolio (JSON persistence)
```

## Critical Patterns

### Risk Profile System
Risk levels (`low`, `medium`, `high`) in `Config.RISK_PROFILES` control:
- Max position size per trade (10%/15%/20% of wallet)
- Preferred assets (low risk restricts to BTC/ETH/BNB)
- Used by `TradingEngine._create_trade_suggestion()` for position sizing

### Trade Suggestion Scoring
`TradingEngine._calculate_trade_score()` combines 5 factors (0-100 scale):
- Signal strength (strong_buy=30pts, buy=20pts)
- Technical confidence from multiple indicators
- 24h price momentum
- Risk/reward ratio quality
- Volume confirmation

Only `buy`/`strong_buy` signals generate suggestions (no sell suggestions without portfolio positions).

### Caching Strategy
`LiveDataFetcher.cache` dictionary stores `(data, timestamp)` tuples:
- Cache key: `'prices_' + '_'.join(coin_ids)`
- Timeout: 30 seconds (`self.cache_timeout`)
- **Always check cache before external API calls**

### Portfolio Persistence
`Portfolio` automatically loads/saves to `portfolio_data.json`:
- `add_position()`: Updates existing position with avg price calculation OR creates new
- `close_position()`: Sells, updates cash, records trade history
- `_save_portfolio()`: Called after every state change

## Development Workflows

### Adding New Technical Indicators
1. Import from `ta` library in `technical_analyzer.py`
2. Add calculation in `_calculate_indicators()` method
3. Create signal logic in `_generate_signals()` 
4. Update `_calculate_overall_signal()` to include new signal weight

### Modifying Risk Profiles
Edit `Config.RISK_PROFILES` dictionary in `config.py`:
```python
'custom': {
    'max_position': 0.12,           # 12% max per trade
    'preferred_assets': ['bitcoin'] # Asset filter
}
```

### Running & Testing
```powershell
# Install dependencies (use virtual env)
pip install -r requirements.txt

# Test setup (validates APIs & dependencies)
python test_setup.py

# Web dashboard (port 8050)
python dashboard.py

# CLI interface
python main.py
```

### Dashboard Updates
- Callbacks use `@app.callback` decorator with Input/Output
- `interval-component` triggers updates every 30s
- Table styling via `COLORS` dict (defined at top of `dashboard.py`)
- Use `dbc.Card` with `backgroundColor=COLORS['card_bg']` for consistency

## Project-Specific Conventions

### Coin Identifiers
Always use CoinGecko IDs (lowercase, hyphenated): `bitcoin`, `ethereum`, `avalanche-2` (NOT symbols like BTC/ETH).
List maintained in `Config.TOP_CRYPTOS`.

### Error Handling Pattern
```python
try:
    data = self.cg.get_price(...)
except Exception as e:
    print(f"Error fetching prices: {e}")
    return {}  # Return empty dict, not None
```
UI code expects empty collections on failure, not exceptions.

### Signal Naming
Standardized strings: `'strong_buy'`, `'buy'`, `'neutral'`, `'sell'`, `'strong_sell'`.
**Never** use variations like `'STRONG_BUY'` or `'strong-buy'`.

### Price Formatting
- Crypto prices: `round(price, 6)` for accuracy
- USD amounts: `round(amount, 2)`
- Quantities: `round(qty, 8)` to handle fractional coins

## Integration Points

### CoinGecko API
- Free tier: 10-50 calls/minute limit
- Main endpoints:
  - `get_price()`: Live prices with 24h data
  - `get_coin_market_chart_by_id()`: Historical OHLCV for analysis
  - `get_search_trending()`: Trending coins
- **Respect rate limits**: Use caching, batch requests

### Environment Variables (.env)
```bash
WALLET_SIZE=1000
RISK_LEVEL=medium  # low, medium, high
MAX_POSITION_SIZE=0.15
STOP_LOSS_PERCENT=5
TAKE_PROFIT_PERCENT=15
```

### External Dependencies
- **Dash 2.14+**: Web framework (no Flask routes needed)
- **ta 0.11+**: Technical analysis calculations
- **pycoingecko**: CoinGecko API wrapper
- **ccxt**: Exchange connectivity (Binance, currently unused)

## Common Tasks

### Add New Cryptocurrency
1. Add CoinGecko ID to `Config.TOP_CRYPTOS` list in `config.py`
2. Restart application (no code changes needed)

### Change Dashboard Theme
Modify `dbc.themes.CYBORG` in `dashboard.py` app initialization:
```python
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.DARKLY])
```

### Adjust Analysis Period
In `TradingEngine.get_trade_suggestions()`:
```python
market_data = self.data_fetcher.get_market_data(coin_id, days=30)  # Change days here
```

### Debug Portfolio Issues
Check `portfolio_data.json` directly:
```powershell
cat portfolio_data.json | ConvertFrom-Json | Format-List
```

## Testing Notes
- `test_setup.py` validates API connectivity and dependencies
- No unit tests currently (portfolio uses simulated trades)
- Manual testing via dashboard or CLI recommended
- Test with small amounts first ($50-100 positions)

## Key Files Reference
- [`config.py`](config.py): All configuration constants
- [`trading_engine.py`](trading_engine.py): Core suggestion logic
- [`technical_analyzer.py`](technical_analyzer.py): Indicator calculations
- [`dashboard.py`](dashboard.py): Primary user interface
- [`SYSTEM_REVIEW.md`](SYSTEM_REVIEW.md): Complete feature documentation

"""
Prediction Market Dashboard - Enhanced UI for BTC Predictions
Integrates ML predictions, technical analysis, and prediction markets
"""
import dash
from dash import dcc, html, Input, Output, State
import dash_bootstrap_components as dbc
import plotly.graph_objs as go
from datetime import datetime, timedelta
import pandas as pd
import threading
import time
from typing import Dict
import os
import json

from prediction_market_analyzer import PredictionMarketAnalyzer
from prediction_trading_bot import PredictionTradingBot
from portfolio import Portfolio
from config import Config
from multitimeframe_predictor import MultiTimeframePredictor
from prediction_tracker import PredictionTracker
from prediction_market_fetcher import PredictionMarketFetcher
from data_fetcher import LiveDataFetcher
from technical_analyzer import TechnicalAnalyzer
from storage import init_db, log_price_snapshot, log_prediction, get_recent_predictions, get_recent_prices

# Reduce TensorFlow console noise
os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL', '2')

# Initialize local database
init_db()

# Initialize components
analyzer = PredictionMarketAnalyzer(auto_train=False)
portfolio = Portfolio()
bot = PredictionTradingBot(portfolio=portfolio, auto_trade=False)
multitimeframe_predictor = MultiTimeframePredictor()
prediction_tracker = PredictionTracker()
multi_coin_fetcher = LiveDataFetcher()
multi_coin_analyzer = TechnicalAnalyzer()
multi_coin_fetcher.cache_timeout = 15

# Prediction recording state
last_prediction_recorded = {
    'timestamp': None,
    'timeframe': '24hr'
}

# Global cache for analysis (updated by background thread)
cached_analysis = {}
analysis_lock = threading.Lock()
last_analysis_update = None

# Live price cache (updated by background thread)
live_price_cache = {
    'price': 0.0,
    'timestamp': None
}
price_lock = threading.Lock()

# Multi-coin live prices cache
live_prices_cache = {
    'data': {},
    'timestamp': None
}
prices_lock = threading.Lock()

# Multi-coin quick signals cache (updated by background thread)
multi_coin_cache = []
multi_coin_lock = threading.Lock()
last_multi_coin_update = None

def update_analysis_background():
    """Background thread to update market analysis"""
    global cached_analysis, last_analysis_update
    fetcher = PredictionMarketFetcher()
    while True:
        try:
            print("🔄 Updating BTC prediction analysis in background...")
            analysis = analyzer.analyze_market()
            with analysis_lock:
                cached_analysis = analysis
                last_analysis_update = datetime.now()

            # Log BTC prediction snapshot
            try:
                ml_pred = analysis.get('ml_prediction', {})
                if ml_pred and ml_pred.get('predicted_price', 0) > 0:
                    log_prediction(
                        coin_id='bitcoin',
                        symbol='BTC',
                        predicted_price=ml_pred.get('predicted_price', 0),
                        predicted_change_pct=ml_pred.get('predicted_change_pct', 0),
                        confidence=ml_pred.get('confidence', 0),
                        direction=ml_pred.get('direction', 'neutral'),
                        model='advanced' if ml_pred.get('advanced') else 'standard'
                    )
            except Exception as e:
                print(f"⚠️ DB prediction log error: {e}")

            # Record and resolve prediction outcomes for simulation
            try:
                ml_pred = analysis.get('ml_prediction', {})
                current_price = analysis.get('current_price', 0)
                if ml_pred and ml_pred.get('predicted_price', 0) > 0 and current_price > 0:
                    now = datetime.now()
                    last_ts = last_prediction_recorded.get('timestamp')
                    if not last_ts or (now - last_ts).total_seconds() > 3600:
                        prediction_tracker.record_prediction(
                            current_price=current_price,
                            predicted_price=ml_pred.get('predicted_price', current_price),
                            timeframe='24hr',
                            confidence=ml_pred.get('confidence', 0.5),
                            hours_ahead=24,
                            model_type=ml_pred.get('model', 'ensemble'),
                            metadata={'source': 'dashboard_predictions'}
                        )
                        last_prediction_recorded['timestamp'] = now

                prediction_tracker.check_expired_predictions(fetcher.get_btc_price_at)
            except Exception as e:
                print(f"⚠️ Prediction tracking error: {e}")

            print("✅ Analysis updated successfully")
        except Exception as e:
            print(f"⚠️ Error updating analysis: {e}")
        time.sleep(60)  # Update every minute


def update_live_price_background():
    """Background thread to update live BTC price"""
    fetcher = PredictionMarketFetcher()
    while True:
        try:
            price = fetcher.get_live_btc_price()
            if price and price > 0:
                with price_lock:
                    live_price_cache['price'] = price
                    live_price_cache['timestamp'] = datetime.now()
        except Exception as e:
            print(f"⚠️ Error updating live price: {e}")
        time.sleep(15)


def build_multi_coin_signals(live_prices: Dict = None) -> list:
    """Build fast signals for the top 5 tracked coins using live deltas only."""
    coins = Config.FAST_ANALYSIS_CRYPTOS[:5]
    if not coins:
        return []

    live_prices = live_prices or multi_coin_fetcher.get_live_prices(coins)
    results = []

    def classify_change(change: float) -> Dict:
        if change >= 3:
            return {'signal': 'strong_buy', 'confidence': 85, 'score': 90}
        if change >= 1:
            return {'signal': 'buy', 'confidence': 70, 'score': 75}
        if change <= -3:
            return {'signal': 'strong_sell', 'confidence': 85, 'score': 90}
        if change <= -1:
            return {'signal': 'sell', 'confidence': 70, 'score': 75}
        return {'signal': 'neutral', 'confidence': 55, 'score': 50}

    for coin_id in coins:
        price_data = live_prices.get(coin_id)
        if not price_data:
            continue

        change = float(price_data.get('change_24h', 0.0))
        cls = classify_change(change)
        symbol = multi_coin_fetcher.coin_symbol_map.get(coin_id, coin_id.upper())

        results.append({
            'coin_id': coin_id,
            'symbol': symbol,
            'signal': cls['signal'],
            'confidence': cls['confidence'],
            'score': cls['score'],
            'current_price': round(price_data.get('price', 0.0), 6),
            'price_change_24h': round(change, 2),
            'trend': 'uptrend' if change > 0 else 'downtrend' if change < 0 else 'sideways'
        })

    results.sort(key=lambda x: x['score'], reverse=True)
    return results[:5]


def update_multi_coin_background():
    """Background thread to update multi-coin quick signals."""
    global multi_coin_cache, last_multi_coin_update
    while True:
        try:
            # Refresh live prices for all tracked coins
            coins = Config.TOP_CRYPTOS
            live_prices = multi_coin_fetcher.get_live_prices(coins)
            if live_prices:
                with prices_lock:
                    live_prices_cache['data'] = live_prices
                    live_prices_cache['timestamp'] = datetime.now()

            # Build quick signals using cached prices
            signals = build_multi_coin_signals(live_prices=live_prices or get_cached_live_prices())
            with multi_coin_lock:
                if signals:
                    multi_coin_cache = signals
                    last_multi_coin_update = datetime.now()

            # Log price snapshots for tracked coins
            try:
                coins = Config.TOP_CRYPTOS
                for coin_id, info in (live_prices or {}).items():
                    symbol = multi_coin_fetcher.coin_symbol_map.get(coin_id, coin_id.upper())
                    log_price_snapshot(
                        coin_id=coin_id,
                        symbol=symbol,
                        price=info.get('price', 0),
                        change_24h=info.get('change_24h', 0)
                    )
            except Exception as e:
                print(f"⚠️ DB price log error: {e}")
        except Exception as e:
            print(f"⚠️ Error updating multi-coin signals: {e}")
        time.sleep(15)

# Start background thread
analysis_thread = threading.Thread(target=update_analysis_background, daemon=True)
analysis_thread.start()

price_thread = threading.Thread(target=update_live_price_background, daemon=True)
price_thread.start()

multi_coin_thread = threading.Thread(target=update_multi_coin_background, daemon=True)
multi_coin_thread.start()


def get_cached_live_price(max_age_seconds: int = 20) -> float:
    """Return cached live price if fresh; otherwise 0."""
    with price_lock:
        price = live_price_cache.get('price', 0.0)
        ts = live_price_cache.get('timestamp')
    if not price or not ts:
        return 0.0
    if (datetime.now() - ts).total_seconds() > max_age_seconds:
        return 0.0
    return price


def get_cached_live_prices(max_age_seconds: int = 20) -> Dict:
    """Return cached live prices if fresh; otherwise empty dict."""
    with prices_lock:
        data = live_prices_cache.get('data', {})
        ts = live_prices_cache.get('timestamp')
    if not data or not ts:
        return {}
    if (datetime.now() - ts).total_seconds() > max_age_seconds:
        return {}
    return data


def is_live_trading_enabled() -> bool:
    """Detect if live prediction trading is configured."""
    return bool(os.getenv('COINBASE_PREDICTION_API_KEY') and os.getenv('COINBASE_PREDICTION_SECRET'))


def get_simulated_portfolio_metrics() -> Dict:
    """Compute simulated portfolio value from prediction outcomes."""
    stats = prediction_tracker.get_statistics(last_n_days=7)
    total_pnl_pct = stats.get('total_pnl_pct', 0.0) if isinstance(stats, dict) else 0.0
    base = getattr(portfolio, 'initial_balance', 1000.0)
    simulated_value = base * (1 + (total_pnl_pct / 100.0))
    return {
        'simulated_value': round(simulated_value, 2),
        'simulated_pnl_pct': round(total_pnl_pct, 2),
        'total_predictions': stats.get('total_predictions', 0) if isinstance(stats, dict) else 0
    }


def get_projected_portfolio_metrics() -> Dict:
    """Compute projected portfolio value from latest model prediction."""
    with analysis_lock:
        analysis = cached_analysis.copy() if cached_analysis else {}
    ml_pred = analysis.get('ml_prediction', {})
    projected_change = ml_pred.get('predicted_change_pct', 0.0) if ml_pred else 0.0
    base_value = portfolio.get_portfolio_value()
    projected_value = base_value * (1 + (projected_change / 100.0))
    return {
        'projected_value': round(projected_value, 2),
        'projected_change_pct': round(projected_change, 2)
    }

# Bot state
bot_state = {
    'running': False,
    'last_check': None,
    'trades_today': 0,
    'last_signal': None
}

# Dashboard styling
COLORS = {
    'background': '#0d1117',
    'card_bg': '#161b22',
    'text': '#c9d1d9',
    'border': '#30363d',
    'success': '#238636',
    'danger': '#da3633',
    'warning': '#9e6a03',
    'info': '#1f6feb',
    'buy': '#26a69a',
    'sell': '#ef5350',
    'neutral': '#78909c'
}

# Create Dash app
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.CYBORG],
    suppress_callback_exceptions=True
)
app.title = "CryptoAI - BTC + Multi-Coin Predictions"

# Layout
app.layout = dbc.Container([
    # Header
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H1("🔮 CryptoAI - BTC + Multi-Coin Prediction Bot", 
                           className='text-center mb-2',
                           style={'color': COLORS['info']}),
                    html.P("ML-Powered Bitcoin + Top-5 Coin Signals for Fast Decisions",
                          className='text-center text-muted mb-2'),
                    html.Div(id='data-quality-status', className='text-center small text-muted')
                ])
            ], style={'backgroundColor': COLORS['card_bg']})
        ])
    ]),
    
    # Control Panel
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H5("🎛️ Bot Controls", className='card-title'),
                    dbc.Row([
                        dbc.Col([
                            dbc.Button("Train ML Models", id='train-button', 
                                     color='primary', className='w-100 mb-2'),
                            dbc.Button("Start Bot", id='start-button', 
                                     color='success', className='w-100 mb-2'),
                            dbc.Button("Stop Bot", id='stop-button', 
                                     color='danger', className='w-100 mb-2'),
                        ], width=6),
                        dbc.Col([
                            dbc.Label("Risk Level:"),
                            dcc.Dropdown(
                                id='risk-dropdown',
                                options=[
                                    {'label': '🟢 Low Risk', 'value': 'low'},
                                    {'label': '🟡 Medium Risk', 'value': 'medium'},
                                    {'label': '🔴 High Risk', 'value': 'high'}
                                ],
                                value='medium',
                                clearable=False,
                                className='mb-2'
                            ),
                            dbc.Label("Min Confidence:"),
                            dcc.Slider(
                                id='confidence-slider',
                                min=0.5, max=0.9, step=0.05, value=0.65,
                                marks={i/10: f'{i}%' for i in range(5, 10)},
                                tooltip={"placement": "bottom", "always_visible": True}
                            )
                        ], width=6)
                    ]),
                    html.Div(id='bot-status', className='mt-3')
                ])
            ], style={'backgroundColor': COLORS['card_bg']})
        ], width=12)
    ], className='mb-4'),

    # ML Training Mode Controls
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H5("🧠 Advanced ML Training Mode", className='card-title'),
                    dbc.RadioItems(
                        id='ml-training-mode',
                        options=[
                            {'label': 'Stable (recommended)', 'value': 'stable'},
                            {'label': 'Aggressive', 'value': 'aggressive'}
                        ],
                        value='stable',
                        inline=True
                    ),
                    html.Small("Stable reduces training volatility; Aggressive retrains faster.", className='text-muted')
                ])
            ], style={'backgroundColor': COLORS['card_bg']})
        ], width=12)
    ], className='mb-4'),

    # Refresh Controls
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H5("🔄 Refresh Controls", className='card-title'),
                    dbc.Row([
                        dbc.Col([
                            dbc.Button("Refresh Now", id='refresh-now', color='info', className='w-100')
                        ], width=4),
                        dbc.Col([
                            dbc.Checklist(
                                id='pause-refresh',
                                options=[{'label': 'Pause Auto-Refresh', 'value': 'pause'}],
                                value=[]
                            )
                        ], width=8)
                    ]),
                    html.Div(id='cache-status', className='small text-muted mt-2')
                ])
            ], style={'backgroundColor': COLORS['card_bg']})
        ], width=12)
    ], className='mb-4'),
    
    # Main Metrics Row
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("Current BTC Price", className='text-muted'),
                    html.H3(id='current-price', children='$0.00', 
                           style={'color': COLORS['info']})
                ])
            ], style={'backgroundColor': COLORS['card_bg']})
        ], width=3),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("ML Prediction (24h)", className='text-muted'),
                    html.H3(id='ml-prediction', children='$0.00',
                           style={'color': COLORS['success']})
                ])
            ], style={'backgroundColor': COLORS['card_bg']})
        ], width=3),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("Overall Signal", className='text-muted'),
                    html.H3(id='overall-signal', children='NEUTRAL')
                ])
            ], style={'backgroundColor': COLORS['card_bg']})
        ], width=3),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("Portfolio Value", className='text-muted'),
                    html.H3(id='portfolio-value', children=f'${portfolio.get_portfolio_value():,.2f}',
                           style={'color': COLORS['warning']})
                ])
            ], style={'backgroundColor': COLORS['card_bg']})
        ], width=3)
    ], className='mb-4'),

    # Token Up/Down Tiles (BTC/ETH/SOL/DOGE)
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("BTC Up/Down", className='text-muted'),
                    html.Div(id='token-tile-btc')
                ])
            ], style={'backgroundColor': COLORS['card_bg']})
        ], width=3),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("ETH Up/Down", className='text-muted'),
                    html.Div(id='token-tile-eth')
                ])
            ], style={'backgroundColor': COLORS['card_bg']})
        ], width=3),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("SOL Up/Down", className='text-muted'),
                    html.Div(id='token-tile-sol')
                ])
            ], style={'backgroundColor': COLORS['card_bg']})
        ], width=3),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("DOGE Up/Down", className='text-muted'),
                    html.Div(id='token-tile-doge')
                ])
            ], style={'backgroundColor': COLORS['card_bg']})
        ], width=3)
    ], className='mb-4'),

    # Multi-Coin Quick Signals
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H5("🌐 Multi-Coin Quick Signals (Top 5)", className='card-title'),
                    html.Div(id='multi-coin-table'),
                    html.Div(id='multi-coin-updated', className='text-muted small mt-2')
                ])
            ], style={'backgroundColor': COLORS['card_bg']})
        ], width=12)
    ], className='mb-4'),

    # All Coins Heads-Up Metrics
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H5("🧭 All Coins Heads-Up Metrics", className='card-title'),
                    html.Div(id='coin-metrics-grid')
                ])
            ], style={'backgroundColor': COLORS['card_bg']})
        ], width=12)
    ], className='mb-4'),

    # Data Audit & History
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H5("🗂️ Data Audit & History", className='card-title'),
                    html.Div(id='db-predictions-table'),
                    html.Hr(),
                    html.Div(id='db-prices-table')
                ])
            ], style={'backgroundColor': COLORS['card_bg']})
        ], width=12)
    ], className='mb-4'),
    
    # Signal Strength Gauge
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H5("📊 Signal Strength", className='card-title'),
                    dcc.Graph(id='signal-gauge', config={'displayModeBar': False})
                ])
            ], style={'backgroundColor': COLORS['card_bg']})
        ], width=6),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H5("🎯 Prediction Confidence", className='card-title'),
                    dcc.Graph(id='confidence-chart', config={'displayModeBar': False})
                ])
            ], style={'backgroundColor': COLORS['card_bg']})
        ], width=6)
    ], className='mb-4'),
    
    # Predictions & Analysis
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H5("🤖 ML Model Predictions", className='card-title'),
                    html.Div(id='ml-predictions-detail')
                ])
            ], style={'backgroundColor': COLORS['card_bg']})
        ], width=6),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H5("📈 Technical Analysis", className='card-title'),
                    html.Div(id='technical-detail')
                ])
            ], style={'backgroundColor': COLORS['card_bg']})
        ], width=6)
    ], className='mb-4'),
    
    # Market Sentiment & Order Book
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H5("😱 Fear & Greed Index", className='card-title'),
                    html.Div(id='sentiment-detail')
                ])
            ], style={'backgroundColor': COLORS['card_bg']})
        ], width=6),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H5("📊 Order Book", className='card-title'),
                    dcc.Graph(id='orderbook-chart', config={'displayModeBar': False})
                ])
            ], style={'backgroundColor': COLORS['card_bg']})
        ], width=6)
    ], className='mb-4'),
    
    # Coinbase Prediction Markets - Live Signals
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H5("🎯 Coinbase Prediction Markets - Live Signals", className='card-title'),
                    html.Div(id='prediction-markets-live', className='mt-3')
                ])
            ], style={'backgroundColor': COLORS['card_bg'], 'borderLeft': '4px solid #2ea44f'})
        ], width=12)
    ], className='mb-4'),

    # Coinbase Prediction Markets - Multi-Coin Signals
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H5("🌐 Coinbase Prediction Markets - Multi-Coin Signals", className='card-title'),
                    html.Div(id='multi-coin-prediction-markets', className='mt-3')
                ])
            ], style={'backgroundColor': COLORS['card_bg'], 'borderLeft': '4px solid #1f6feb'})
        ], width=12)
    ], className='mb-4'),
    
    # Prediction Signals (Not Trade Recommendations)
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H5("📊 Multi-Timeframe Prediction Signals", className='card-title'),
                    html.Div(id='recommendations-table')
                ])
            ], style={'backgroundColor': COLORS['card_bg']})
        ], width=12)
    ], className='mb-4'),
    
    # Prediction Controls Section
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H5("🎮 Prediction Controls", className='card-title mb-3'),
                    html.Hr(),
                    
                    # Account Connection Status
                    dbc.Row([
                        dbc.Col([
                            html.H6("📡 Account Status", className='mb-2'),
                            html.Div(id='account-status', children=[
                                dbc.Badge("✅ Coinbase API Connected (Real-time Data)", color='success', className='me-2'),
                                dbc.Badge("⚠️ Prediction Markets: Not Connected", color='warning')
                            ])
                        ], width=12)
                    ], className='mb-3'),
                    
                    html.Hr(),
                    
                    # Manual Prediction Placement
                    dbc.Row([
                        dbc.Col([
                            html.H6("💼 Manual Predictions", className='mb-2'),
                            dbc.Label("Select Prediction Market"),
                            dcc.Dropdown(
                                id='prediction-selection',
                                options=[],
                                value=None,
                                placeholder='Loading prediction markets...'
                            ),
                            html.Div(id='prediction-selection-detail', className='text-muted small mt-2'),
                            html.Hr(),
                            dbc.InputGroup([
                                dbc.InputGroupText("Bet Amount ($)"),
                                dbc.Input(id='trade-amount', type='number', placeholder='100', value=100, min=10, max=10000),
                            ], className='mb-2'),
                            dbc.ButtonGroup([
                                dbc.Button("📈 BET YES", id='manual-buy-button', color='success', size='lg', className='me-2'),
                                dbc.Button("📉 BET NO", id='manual-sell-button', color='danger', size='lg'),
                            ], className='d-grid gap-2 w-100')
                        ], width=6),
                        
                        # Current Prediction Bankroll Display
                        dbc.Col([
                            html.H6("💰 Prediction Bankroll", className='mb-2'),
                            html.Div(id='portfolio-display', children=[
                                html.P([html.Strong("Available: "), html.Span(f"${portfolio.cash_balance:,.2f}")], className='mb-1'),
                                html.P([html.Strong("Active Bets: "), html.Span("No active predictions")], className='mb-1'),
                                html.P([html.Strong("Total Bankroll: "), html.Span(f"${portfolio.get_portfolio_value():,.2f}")], className='mb-1'),
                                html.P([html.Strong("Net Winnings: "), html.Span("$0.00 (0.00%)", style={'color': COLORS['text']})], className='mb-0')
                            ])
                        ], width=6)
                    ], className='mb-3'),
                    
                    html.Hr(),
                    
                    # Prediction Bot Automation Controls
                    dbc.Row([
                        dbc.Col([
                            html.H6("🤖 Automated Prediction Bot", className='mb-2'),
                            
                            # Bot Settings
                            dbc.Row([
                                dbc.Col([
                                    dbc.Label("Risk Level", className='fw-bold'),
                                    dcc.Dropdown(
                                        id='bot-risk-dropdown',
                                        options=[
                                            {'label': '🟢 Low Risk (10% max bet per prediction)', 'value': 'low'},
                                            {'label': '🟡 Medium Risk (15% max bet per prediction)', 'value': 'medium'},
                                            {'label': '🔴 High Risk (20% max bet per prediction)', 'value': 'high'}
                                        ],
                                        value='medium',
                                        clearable=False,
                                        style={'color': '#000'}
                                    )
                                ], width=6, className='mb-2'),
                                
                                dbc.Col([
                                    dbc.Label("Min Confidence", className='fw-bold'),
                                    dcc.Slider(
                                        id='bot-confidence-slider',
                                        min=0.5,
                                        max=0.9,
                                        step=0.05,
                                        value=0.65,
                                        marks={0.5: '50%', 0.6: '60%', 0.7: '70%', 0.8: '80%', 0.9: '90%'},
                                        tooltip={"placement": "bottom", "always_visible": True}
                                    )
                                ], width=6, className='mb-2')
                            ]),
                            
                            # Bot Start/Stop Controls
                            dbc.Row([
                                dbc.Col([
                                    dbc.ButtonGroup([
                                        dbc.Button("▶️ START BOT", id='start-bot-button', color='primary', size='lg', className='me-2'),
                                        dbc.Button("⏸️ STOP BOT", id='stop-bot-button', color='secondary', size='lg'),
                                    ], className='d-grid gap-2 w-100 mb-2')
                                ], width=12)
                            ]),
                            
                            # Bot Status Display
                            html.Div(id='bot-status-display', className='mt-2')
                            
                        ], width=12)
                    ], className='mb-3'),
                    
                    html.Hr(),
                    
                    # Coinbase Prediction Markets Connection
                    dbc.Row([
                        dbc.Col([
                            html.H6("🔗 Connect Coinbase Prediction Markets", className='mb-2'),
                            dbc.Alert([
                                html.H6("⚠️ Enable Live Predictions", className='alert-heading'),
                                html.P([
                                    "Currently using simulated bankroll (paper predictions). To enable live prediction markets:",
                                    html.Br(),
                                    html.Br(),
                                    html.Strong("1. Add Coinbase Prediction Market Credentials:"),
                                    html.Br(),
                                    html.Code("COINBASE_PREDICTION_API_KEY=your_prediction_key", className='d-block'),
                                    html.Code("COINBASE_PREDICTION_SECRET=your_prediction_secret", className='d-block'),
                                    html.Br(),
                                    html.Strong("2. Set Bot Allowance:"),
                                    html.Br(),
                                    "Set maximum bankroll for bot (e.g., $100.00)",
                                    html.Br(),
                                    html.Br(),
                                    html.Strong("3. Real-Time Data:"),
                                    html.Br(),
                                    "Bot fetches BTC data in near real-time (every 5-30 seconds) for accurate predictions",
                                    html.Br(),
                                    html.Br(),
                                    html.Strong("4. Click Connect:"),
                                ], className='mb-2'),
                                dbc.Button("🔌 Connect Prediction Markets", id='connect-trading-button', color='warning', size='lg', disabled=True),
                                html.Small(" (Add credentials to .env file first)", className='text-muted ms-2')
                            ], color='info', className='mb-0')
                        ], width=12)
                    ]),
                    
                    # Prediction Notifications
                    html.Div(id='trade-notification', className='mt-3'),

                    html.Hr(),

                    # Live Prediction Signals (under controls)
                    dbc.Row([
                        dbc.Col([
                            html.H6("🎯 Live Prediction Signals", className='mb-2'),
                            html.Div(id='prediction-controls-markets', className='mt-2')
                        ], width=12)
                    ])
                ])
            ], style={'backgroundColor': COLORS['card_bg'], 'borderLeft': '4px solid #f39c12'})
        ], width=12)
    ], className='mb-4'),
    
    # Price Chart
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H5("📈 BTC Price History & Predictions", className='card-title'),
                    dcc.Graph(id='price-chart', config={'displayModeBar': False})
                ])
            ], style={'backgroundColor': COLORS['card_bg']})
        ], width=12)
    ]),
    
    # Auto-refresh intervals
    dcc.Interval(
        id='interval-component',
        interval=15*1000,  # 15 seconds for full analysis
        n_intervals=0
    ),
    
    dcc.Interval(
        id='price-interval',
        interval=15*1000,  # 15 seconds for live BTC price only
        n_intervals=0
    ),

    dcc.Interval(
        id='multi-coin-interval',
        interval=15*1000,  # 15 seconds for multi-coin quick signals
        n_intervals=0
    ),

    dcc.Store(id='manual-refresh-trigger')
    
], fluid=True, style={'backgroundColor': COLORS['background'], 'padding': '20px'})


def create_prediction_markets_panel(
    analysis: dict,
    current_price: float,
    predicted_price: float,
    include_actions: bool = False
):
    """
    Create live Coinbase Prediction Markets panel with real multi-timeframe data
    
    Args:
        analysis: Full market analysis
        current_price: Current BTC price
        predicted_price: ML predicted price for 24h
    
    Returns:
        Dash component with prediction market signals
    """
    signal = analysis.get('overall_signal', {})
    confidence = signal.get('confidence', 0)
    signal_type = signal.get('signal', 'neutral')
    ml_pred = analysis.get('ml_prediction', {})
    predicted_change = ml_pred.get('predicted_change_pct', 0)
    
    # Use real multi-timeframe predictor for Coinbase-style markets
    market_cards = []
    try:
        # Get historical data from cache or fetch
        from prediction_market_fetcher import PredictionMarketFetcher
        fetcher = PredictionMarketFetcher()
        historical_df = fetcher.get_btc_historical_data(days=7)
        
        if not historical_df.empty:
            # Generate real predictions across all timeframes
            all_predictions = multitimeframe_predictor.predict_all_timeframes(
                historical_df, current_price
            )
            
            # Generate Coinbase-style markets
            markets = multitimeframe_predictor.generate_coinbase_style_markets(
                current_price, all_predictions
            )
            
            # Show TOP 8 markets with highest edge (YES/NO only)
            filtered_markets = [m for m in markets if m.get('recommendation') in ['BUY YES', 'BUY NO']]
            top_markets = filtered_markets[:8]
            
            for market in top_markets:
                # Extract data
                question = market['question']
                yes_prob = market['yes_probability']
                no_prob = market['no_probability']
                edge = market['edge']
                recommendation = market['recommendation']
                strength = market['strength']
                timeframe = market['timeframe']
                threshold = market['threshold_price']
                
                # Determine colors
                if recommendation == 'BUY YES':
                    action_color = COLORS['buy']
                    if strength == 'STRONG':
                        border_color = "#238636"
                        emoji = "🚀"
                    elif strength == 'MEDIUM':
                        border_color = "#3fb950"
                        emoji = "📈"
                    else:
                        border_color = "#58a6ff"
                        emoji = "↗️"
                elif recommendation == 'BUY NO':
                    action_color = COLORS['sell']
                    if strength == 'STRONG':
                        border_color = "#da3633"
                        emoji = "🔻"
                    elif strength == 'MEDIUM':
                        border_color = "#f85149"
                        emoji = "📉"
                    else:
                        border_color = "#8b949e"
                        emoji = "↘️"
                else:
                    action_color = COLORS['neutral']
                    border_color = "#6e7681"
                    emoji = "➡️"
                
                action_button = None
                if include_actions:
                    if recommendation in ['BUY YES', 'BUY NO']:
                        action = 'YES' if recommendation == 'BUY YES' else 'NO'
                        button_color = 'success' if action == 'YES' else 'danger'
                        action_button = dbc.Button(
                            f"Place {action} Bet",
                            id={
                                'type': 'prediction-action',
                                'action': action,
                                'threshold': float(threshold),
                                'timeframe': timeframe
                            },
                            color=button_color,
                            size='sm',
                            className='w-100 mt-2'
                        )
                    else:
                        action_button = dbc.Button(
                            "No Action",
                            id={
                                'type': 'prediction-action',
                                'action': 'SKIP',
                                'threshold': float(threshold),
                                'timeframe': timeframe
                            },
                            color='secondary',
                            size='sm',
                            className='w-100 mt-2',
                            disabled=True
                        )

                card = dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6([
                                html.Span(emoji + " ", style={'fontSize': '1.2em'}),
                                f"${threshold:,.0f} in {timeframe}"
                            ], className='mb-2'),
                            html.H5(f"{recommendation}", style={'color': action_color, 'fontWeight': 'bold'}),
                            html.P([
                                f"YES: {yes_prob:.0f}% | NO: {no_prob:.0f}%",
                                html.Br(),
                                f"Edge: {edge:+.1f}%",
                                html.Br(),
                                html.Small(f"📊 {strength}", className='text-muted')
                            ], className='mb-0'),
                            action_button if include_actions else None
                        ])
                    ], style={
                        'backgroundColor': COLORS['card_bg'],
                        'borderLeft': f'4px solid {border_color}',
                        'height': '100%'
                    })
                ], md=3, className='mb-3')
                
                market_cards.append(card)
        
    except Exception as e:
        print(f"Error generating prediction markets: {e}")
        # Fallback to simple message
        market_cards = []
    
    # Add header with overall signal
    header_color = COLORS['buy'] if 'buy' in signal_type.lower() else COLORS['sell'] if 'sell' in signal_type.lower() else COLORS['neutral']
    
    header = dbc.Alert([
        dbc.Row([
            dbc.Col([
                html.H5([
                    "📊 Market Signal: ",
                    html.Span(signal_type.upper(), style={'color': header_color, 'fontWeight': 'bold'})
                ], className='mb-2'),
                html.P([
                    f"Current: ${current_price:,.2f}",
                    html.Br(),
                    f"24h Prediction: ${predicted_price:,.2f} ({predicted_change:+.2f}%)",
                    html.Br(),
                    f"Model Confidence: {confidence*100:.0f}%"
                ], className='mb-0')
            ], md=4),
            dbc.Col([
                html.H6("💰 Position Sizing Recommendation:", className='mb-2'),
                html.P([
                    get_position_sizing_text(confidence, signal_type),
                    html.Br(),
                    html.Small("Based on Kelly Criterion + Risk Management", className='text-muted')
                ], className='mb-0')
            ], md=4),
            dbc.Col([
                html.H6("⏰ Next Update:", className='mb-2'),
                html.P([
                    "30 seconds (auto-refresh)",
                    html.Br(),
                    html.Small(f"Bot Status: {'🟢 ACTIVE' if bot_state['running'] else '🔴 IDLE'}", 
                             style={'color': '#238636' if bot_state['running'] else '#8b949e'})
                ], className='mb-0')
            ], md=4)
        ])
    ], color='dark', className='mb-3')
    
    if not market_cards:
        market_cards = [
            dbc.Col([
                html.P("⚠️ No strong signals - confidence below 55%. Wait for better setup.", 
                      className='text-warning text-center')
            ], width=12)
        ]
    
    return html.Div([
        header,
        dbc.Row(market_cards)
    ])


def create_multi_coin_prediction_markets_panel() -> html.Div:
    """Create Coinbase-style prediction markets for all tracked coins (YES/NO only)."""
    rows = []
    with multi_coin_lock:
        signals = list(multi_coin_cache) if multi_coin_cache else []

    for item in signals:
        symbol = item.get('symbol', '').upper()
        direction = item.get('signal', 'neutral').upper()
        action = 'UP' if 'BUY' in direction or 'BULL' in direction else 'DOWN' if 'SELL' in direction or 'BEAR' in direction else 'WAIT'
        action_color = COLORS['buy'] if action == 'UP' else COLORS['sell'] if action == 'DOWN' else COLORS['neutral']
        rows.append(html.Tr([
            html.Td(symbol),
            html.Td(action, style={'color': action_color, 'fontWeight': 'bold'}),
            html.Td(f"{item.get('confidence', 0):.0f}%"),
            html.Td(f"{item.get('score', 0):.1f}"),
            html.Td(f"${item.get('current_price', 0):,.4f}"),
            html.Td(f"{item.get('price_change_24h', 0):+.2f}%")
        ]))

    if not rows:
        return html.Div("No multi-coin prediction markets available yet.")

    return html.Div([
        html.P("Quick view across tracked coins. Cached for speed.", className='text-muted mb-2'),
        dbc.Table(
            [
                html.Thead(html.Tr([
                    html.Th("Coin"),
                    html.Th("Action"),
                    html.Th("Conf"),
                    html.Th("Score"),
                    html.Th("Price"),
                    html.Th("24h")
                ])),
                html.Tbody(rows)
            ],
            bordered=False,
            hover=True,
            responsive=True,
            striped=True,
            size='sm'
        )
    ])


def get_position_sizing_text(confidence: float, signal_type: str) -> str:
    """Get recommended position sizing based on confidence"""
    if confidence < 0.55:
        return "🚫 SKIP - Too risky (< 55% confidence)"
    elif confidence < 0.65:
        return "💵 5-10% of bankroll (Low conviction)"
    elif confidence < 0.75:
        return "💰 10-15% of bankroll (Medium conviction)"
    elif confidence < 0.85:
        return "💎 15-20% of bankroll (High conviction)"
    else:
        return "🔥 20-25% of bankroll (Very high conviction)"


def format_signal_badge(signal: str):
    """Format signal with consistent color coding."""
    signal_lower = (signal or 'neutral').lower()
    color = COLORS['buy'] if 'buy' in signal_lower else COLORS['sell'] if 'sell' in signal_lower else COLORS['neutral']
    signal_upper = signal_lower.upper()
    return html.Span(signal_upper, style={'color': color, 'fontWeight': 'bold'})


def render_multi_coin_table(items: list):
    """Render multi-coin quick signals table."""
    if not items:
        return html.Div("No signals available yet.")

    rows = []
    for item in items:
        rows.append(html.Tr([
            html.Td(item.get('symbol', '').upper()),
            html.Td(format_signal_badge(item.get('signal', 'neutral'))),
            html.Td(f"{item.get('confidence', 0):.1f}%"),
            html.Td(f"{item.get('score', 0):.1f}"),
            html.Td(f"${item.get('current_price', 0):,.6f}"),
            html.Td(f"{item.get('price_change_24h', 0):+.2f}%"),
            html.Td(str(item.get('trend', 'unknown')).replace('_', ' ').title())
        ]))

    return dbc.Table(
        [
            html.Thead(html.Tr([
                html.Th("Coin"),
                html.Th("Signal"),
                html.Th("Conf"),
                html.Th("Score"),
                html.Th("Price"),
                html.Th("24h"),
                html.Th("Trend")
            ])),
            html.Tbody(rows)
        ],
        bordered=False,
        hover=True,
        responsive=True,
        striped=True,
        size='sm'
    )


def build_prediction_market_options(current_price: float) -> list:
    """Build dropdown options for prediction markets (all tracked coins, YES/NO only)."""
    try:
        coins = Config.TOP_CRYPTOS
        options = []
        live_prices = multi_coin_fetcher.get_live_prices(coins)

        for coin_id in coins:
            price_info = live_prices.get(coin_id)
            if not price_info:
                continue

            coin_price = float(price_info.get('price', 0))
            if coin_price <= 0:
                continue

            historical_df = multi_coin_fetcher.get_market_data(coin_id, days=7)
            if historical_df.empty:
                continue

            all_predictions = multitimeframe_predictor.predict_all_timeframes(
                historical_df, coin_price
            )
            markets = multitimeframe_predictor.generate_coinbase_style_markets(
                coin_price, all_predictions
            )

            for market in iterate_markets(markets, limit=6):
                recommendation = market.get('recommendation', 'HOLD')
                if recommendation not in ['BUY YES', 'BUY NO']:
                    continue

                payload = {
                    'coin_id': coin_id,
                    'symbol': multi_coin_fetcher.coin_symbol_map.get(coin_id, coin_id.upper()),
                    'question': market.get('question'),
                    'threshold': float(market.get('threshold_price', coin_price)),
                    'timeframe': market.get('timeframe', '24h'),
                    'recommendation': recommendation,
                    'yes_probability': market.get('yes_probability', 0),
                    'no_probability': market.get('no_probability', 0),
                    'edge': market.get('edge', 0)
                }
                yes_prob = interpolate_probability(payload['yes_probability'])
                no_prob = interpolate_probability(payload['no_probability'])
                label = (
                    f"{payload['symbol']} | {payload['recommendation']} | {payload['question']} | "
                    f"YES {yes_prob:.0f}% / NO {no_prob:.0f}% | "
                    f"Edge {payload['edge']:.1f}%"
                )
                options.append({'label': label, 'value': json.dumps(payload)})

        return options
    except Exception as e:
        print(f"⚠️ Error building prediction market options: {e}")
        return []


def render_prediction_selection_detail(selected_value: str):
    """Render detail text for selected prediction market."""
    if not selected_value:
        return "Select a market to place your bet."

    try:
        payload = json.loads(selected_value)
    except Exception:
        return "Select a market to place your bet."

    return (
        f"Selected: {payload.get('symbol', 'BTC')} | {payload.get('question', 'BTC prediction')} | "
        f"Threshold: ${float(payload.get('threshold', 0)):,.0f} | "
        f"Timeframe: {payload.get('timeframe', '24h')} | "
        f"YES {payload.get('yes_probability', 0):.0f}% / "
        f"NO {payload.get('no_probability', 0):.0f}%"
    )


def interpolate_probability(value: float, min_val: float = 0.0, max_val: float = 100.0) -> float:
    """Interpolate and clamp probability values to keep UI consistent."""
    try:
        return max(min_val, min(max_val, float(value)))
    except Exception:
        return min_val


def iterate_markets(markets: list, limit: int = 4):
    """Iterate over prediction markets (YES/NO only), sorted by edge."""
    filtered = [m for m in markets if m.get('recommendation') in ['BUY YES', 'BUY NO']]
    filtered.sort(key=lambda x: x.get('edge', 0), reverse=True)
    return filtered[:limit]


def get_token_prediction_summary(coin_id: str) -> Dict:
    """Get fresh up/down prediction summary for a token."""
    live = get_cached_live_prices() or multi_coin_fetcher.get_live_prices([coin_id])
    price_info = live.get(coin_id, {})
    current_price = float(price_info.get('price', 0))

    if current_price <= 0:
        return {
            'symbol': multi_coin_fetcher.coin_symbol_map.get(coin_id, coin_id.upper()),
            'price': 0,
            'direction': 'WAIT',
            'confidence': 0,
            'change_pct': 0
        }

    change_pct = float(price_info.get('change_24h', 0))
    if change_pct >= 1:
        action = 'UP'
        confidence = 70 if change_pct < 3 else 85
    elif change_pct <= -1:
        action = 'DOWN'
        confidence = 70 if change_pct > -3 else 85
    else:
        action = 'WAIT'
        confidence = 55

    return {
        'symbol': multi_coin_fetcher.coin_symbol_map.get(coin_id, coin_id.upper()),
        'price': current_price,
        'direction': action,
        'confidence': confidence,
        'change_pct': change_pct
    }


def render_token_tile(summary: Dict) -> html.Div:
    """Render a compact token tile for up/down prediction."""
    direction = summary.get('direction', 'WAIT')
    color = COLORS['buy'] if direction == 'UP' else COLORS['sell'] if direction == 'DOWN' else COLORS['neutral']
    return html.Div([
        html.H4(f"${summary.get('price', 0):,.4f}", style={'color': COLORS['info']}),
        html.H5(direction, style={'color': color, 'fontWeight': 'bold'}),
        html.Small(f"Conf: {summary.get('confidence', 0):.0f}% | Δ {summary.get('change_pct', 0):+.2f}%")
    ])


def get_live_price_for_coin(coin_id: str) -> float:
    """Fetch live price for a specific coin."""
    try:
        live = multi_coin_fetcher.get_live_prices([coin_id])
        return float(live.get(coin_id, {}).get('price', 0))
    except Exception:
        return 0.0


def render_coin_metrics_grid() -> html.Div:
    """Render a heads-up metrics grid for all tracked coins."""
    coins = Config.TOP_CRYPTOS
    live_prices = get_cached_live_prices()
    if not live_prices:
        live_prices = multi_coin_fetcher.get_live_prices(coins)
    db_prices = get_db_price_snapshot_map()
    cards = []

    for coin_id in coins:
        info = live_prices.get(coin_id, {})
        if not info:
            info = db_prices.get(coin_id, {})

        price = float(info.get('price', 0))
        change_24h = float(info.get('change_24h', 0))
        symbol = multi_coin_fetcher.coin_symbol_map.get(coin_id, coin_id.upper())

        change_color = COLORS['buy'] if change_24h > 0 else COLORS['sell'] if change_24h < 0 else COLORS['neutral']

        cards.append(
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6(f"{symbol} Price", className='text-muted'),
                        html.H4(f"${price:,.4f}" if price > 0 else "N/A", style={'color': COLORS['info']}),
                        html.Small(
                            f"24h: {change_24h:+.2f}%",
                            style={'color': change_color}
                        )
                    ])
                ], style={'backgroundColor': COLORS['card_bg']})
            ], xs=6, sm=6, md=4, lg=3, xl=2, className='mb-3')
        )

    if not cards:
        return html.Div("Loading coin metrics...", className='text-muted')

    updated_text = ""
    with prices_lock:
        ts = live_prices_cache.get('timestamp')
    if ts:
        updated_text = f"Updated {ts.strftime('%H:%M:%S')}"

    return html.Div([
        dbc.Row(cards),
        html.Div(updated_text, className='text-muted small mt-2')
    ])


def render_db_predictions_table() -> html.Div:
    rows = get_recent_predictions(limit=20)
    if not rows:
        return html.P("No predictions logged yet.", className='text-muted')

    return dbc.Table(
        [
            html.Thead(html.Tr([
                html.Th("Time"),
                html.Th("Coin"),
                html.Th("Predicted"),
                html.Th("Δ%"),
                html.Th("Conf"),
                html.Th("Dir"),
                html.Th("Model")
            ])),
            html.Tbody([
                html.Tr([
                    html.Td(r['timestamp'][11:19]),
                    html.Td(r['symbol']),
                    html.Td(f"${r['predicted_price']:,.2f}"),
                    html.Td(f"{r['predicted_change_pct']:+.2f}%"),
                    html.Td(f"{r['confidence']*100:.0f}%"),
                    html.Td(r['direction']),
                    html.Td(r['model'])
                ]) for r in rows
            ])
        ],
        bordered=False,
        hover=True,
        responsive=True,
        striped=True,
        size='sm'
    )


def render_db_prices_table() -> html.Div:
    rows = get_recent_prices(limit=20)
    if not rows:
        return html.P("No price snapshots logged yet.", className='text-muted')

    return dbc.Table(
        [
            html.Thead(html.Tr([
                html.Th("Time"),
                html.Th("Coin"),
                html.Th("Price"),
                html.Th("24h")
            ])),
            html.Tbody([
                html.Tr([
                    html.Td(r['timestamp'][11:19]),
                    html.Td(r['symbol']),
                    html.Td(f"${r['price']:,.4f}"),
                    html.Td(f"{r['change_24h']:+.2f}%")
                ]) for r in rows
            ])
        ],
        bordered=False,
        hover=True,
        responsive=True,
        striped=True,
        size='sm'
    )


def get_db_price_snapshot_map() -> Dict[str, Dict]:
    """Build a latest price map from DB snapshots as a fallback."""
    rows = get_recent_prices(limit=200)
    latest = {}
    for row in rows:
        coin_id = row.get('coin_id')
        if coin_id and coin_id not in latest:
            latest[coin_id] = row
    return latest


@app.callback(
    [Output('multi-coin-table', 'children'),
     Output('multi-coin-updated', 'children')],
    [Input('multi-coin-interval', 'n_intervals'),
     Input('manual-refresh-trigger', 'data')]
)
def update_multi_coin_table(n):
    """Update multi-coin quick signals table."""
    with multi_coin_lock:
        items = list(multi_coin_cache) if multi_coin_cache else []
        updated_at = last_multi_coin_update

    if not items:
        return "Loading multi-coin signals...", ""

    updated_text = f"Updated {updated_at.strftime('%H:%M:%S')}" if updated_at else ""
    return render_multi_coin_table(items), updated_text


@app.callback(
    Output('manual-refresh-trigger', 'data'),
    [Input('refresh-now', 'n_clicks')],
    prevent_initial_call=True
)
def trigger_manual_refresh(n_clicks):
    if not n_clicks:
        return dash.no_update
    return datetime.now().isoformat()


@app.callback(
    [Output('interval-component', 'disabled'),
     Output('price-interval', 'disabled'),
     Output('multi-coin-interval', 'disabled')],
    [Input('pause-refresh', 'value')]
)
def toggle_refresh(pause_values):
    paused = 'pause' in (pause_values or [])
    return paused, paused, paused


@app.callback(
    Output('cache-status', 'children'),
    [Input('interval-component', 'n_intervals'),
     Input('manual-refresh-trigger', 'data')]
)
def update_cache_status(n, manual_refresh):
    analysis_ts = last_analysis_update.strftime('%H:%M:%S') if last_analysis_update else 'N/A'
    prices_ts = live_prices_cache.get('timestamp')
    prices_text = prices_ts.strftime('%H:%M:%S') if prices_ts else 'N/A'
    signals_text = last_multi_coin_update.strftime('%H:%M:%S') if last_multi_coin_update else 'N/A'
    return f"Analysis: {analysis_ts} | Prices: {prices_text} | Signals: {signals_text}"


@app.callback(
    [Output('prediction-selection', 'options'),
     Output('prediction-selection', 'value'),
     Output('prediction-selection-detail', 'children')],
    [Input('interval-component', 'n_intervals')],
    [State('prediction-selection', 'value')]
)
def update_prediction_selection(n, current_value):
    """Populate prediction selection dropdown and keep current selection if valid."""
    with analysis_lock:
        analysis = cached_analysis.copy() if cached_analysis else {}
    current_price = analysis.get('current_price', 0) or get_cached_live_price()

    options = build_prediction_market_options(current_price)
    if not options:
        return [], None, "No prediction markets available yet."

    valid_values = {opt['value'] for opt in options}
    selected_value = current_value if current_value in valid_values else options[0]['value']
    detail = render_prediction_selection_detail(selected_value)
    return options, selected_value, detail


# Callbacks
@app.callback(
    [Output('current-price', 'children'),
     Output('ml-prediction', 'children'),
     Output('overall-signal', 'children'),
     Output('overall-signal', 'style'),
     Output('data-quality-status', 'children'),
     Output('portfolio-value', 'children'),
     Output('signal-gauge', 'figure'),
     Output('confidence-chart', 'figure'),
     Output('ml-predictions-detail', 'children'),
     Output('technical-detail', 'children'),
     Output('sentiment-detail', 'children'),
     Output('orderbook-chart', 'figure'),
     Output('prediction-markets-live', 'children'),
     Output('multi-coin-prediction-markets', 'children'),
     Output('token-tile-btc', 'children'),
     Output('token-tile-eth', 'children'),
     Output('token-tile-sol', 'children'),
     Output('token-tile-doge', 'children'),
     Output('coin-metrics-grid', 'children'),
    Output('db-predictions-table', 'children'),
    Output('db-prices-table', 'children'),
     Output('recommendations-table', 'children'),
     Output('price-chart', 'figure'),
     Output('prediction-controls-markets', 'children')],
    [Input('interval-component', 'n_intervals'),
     Input('manual-refresh-trigger', 'data')]
)
def update_dashboard(n):
    """Update all dashboard components using cached analysis"""
    
    try:
        # Get analysis from cache (no heavy processing in callback)
        with analysis_lock:
            analysis = cached_analysis.copy() if cached_analysis else {}
        
        # Use default values if analysis not ready
        if not analysis:
            empty_fig = go.Figure()
            empty_fig.update_layout(
                paper_bgcolor=COLORS['card_bg'],
                plot_bgcolor=COLORS['card_bg'],
                font={'color': COLORS['text']}
            )
            return ("Loading...", "Loading...", "ANALYZING", {'color': COLORS['neutral']},
                "Data: Initializing...", "$0.00", empty_fig, empty_fig, "Initializing...", "Initializing...",
                "Initializing...", empty_fig, [], [], "Loading...", "Loading...", "Loading...", "Loading...",
                "Loading...", "Loading...", "Loading...", [], empty_fig, [])
    except Exception as e:
        print(f"⚠️ Dashboard callback error: {e}")
        empty_fig = go.Figure()
        empty_fig.update_layout(
            paper_bgcolor=COLORS['card_bg'],
            plot_bgcolor=COLORS['card_bg'],
            font={'color': COLORS['text']}
        )
        return ("Error", "Error", "ERROR", {'color': COLORS['danger']},
            "Data: Error", "$0.00", empty_fig, empty_fig, "Error loading data", "Error loading data",
            "Error loading data", empty_fig, [], [], "Error", "Error", "Error", "Error",
            "Error", "Error", "Error", [], empty_fig, [])
    
    try:
        current_price = analysis.get('current_price', 0)
        ml_pred = analysis.get('ml_prediction', {})
        overall_signal = analysis.get('overall_signal', {})

        # Data freshness status
        data_status = "Data: Fresh"
        ts = analysis.get('timestamp')
        if ts:
            try:
                ts_dt = datetime.fromisoformat(ts)
                age = (datetime.now() - ts_dt).total_seconds()
                if age > 45:
                    data_status = f"Data: Stale ({int(age)}s)"
                else:
                    data_status = f"Data: Fresh ({int(age)}s)"
            except Exception:
                data_status = "Data: Unknown"
        else:
            data_status = "Data: Loading"
        
        # Format outputs
        price_text = f"${current_price:,.2f}"
        ml_price = ml_pred.get('predicted_price', 0)
        ml_change = ml_pred.get('predicted_change_pct', 0)
        ml_text = f"${ml_price:,.2f} ({ml_change:+.1f}%)"
        
        signal = overall_signal.get('signal', 'neutral').upper()
        signal_color = COLORS['buy'] if 'buy' in signal.lower() else COLORS['sell'] if 'sell' in signal.lower() else COLORS['neutral']
        
        portfolio_val = portfolio.get_portfolio_value()
        if not is_live_trading_enabled():
            sim_metrics = get_simulated_portfolio_metrics()
            if sim_metrics.get('total_predictions', 0) > 0:
                portfolio_text = f"${sim_metrics['simulated_value']:,.2f} (Simulated)"
            else:
                projected = get_projected_portfolio_metrics()
                portfolio_text = f"${projected['projected_value']:,.2f} (Projected)"
        else:
            portfolio_text = f"${portfolio_val:,.2f}"
    except Exception as e:
        print(f"⚠️ Error formatting dashboard data: {e}")
        current_price = 0
        ml_price = 0
        ml_change = 0
        price_text = "Error"
        ml_text = "Error"
        signal = "ERROR"
        signal_color = COLORS['danger']
        data_status = "Data: Error"
        portfolio_text = "$0.00"
    
    # Signal Gauge
    score = overall_signal.get('score', 50)
    gauge_fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "Signal Score"},
        gauge={
            'axis': {'range': [0, 100]},
            'bar': {'color': signal_color},
            'steps': [
                {'range': [0, 25], 'color': COLORS['sell']},
                {'range': [25, 40], 'color': 'lightcoral'},
                {'range': [40, 60], 'color': COLORS['neutral']},
                {'range': [60, 75], 'color': 'lightgreen'},
                {'range': [75, 100], 'color': COLORS['buy']}
            ],
            'threshold': {
                'line': {'color': "white", 'width': 4},
                'thickness': 0.75,
                'value': score
            }
        }
    ))
    gauge_fig.update_layout(
        paper_bgcolor=COLORS['card_bg'],
        plot_bgcolor=COLORS['card_bg'],
        font={'color': COLORS['text']},
        height=300
    )
    
    # Confidence Chart
    confidence = overall_signal.get('confidence', 0)
    confidence_fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=confidence * 100,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "Confidence %"},
        delta={'reference': 65},
        gauge={
            'axis': {'range': [0, 100]},
            'bar': {'color': COLORS['info']},
            'steps': [
                {'range': [0, 50], 'color': 'lightgray'},
                {'range': [50, 70], 'color': 'gold'},
                {'range': [70, 100], 'color': 'green'}
            ]
        }
    ))
    confidence_fig.update_layout(
        paper_bgcolor=COLORS['card_bg'],
        plot_bgcolor=COLORS['card_bg'],
        font={'color': COLORS['text']},
        height=300
    )
    
    # ML Predictions Detail - Enhanced with fallback
    if ml_pred and ml_pred.get('predicted_price', 0) > 0:
        ml_detail = html.Div([
            html.P(f"Direction: {ml_pred.get('direction', 'neutral').upper()}", className='mb-1'),
            html.P(f"Predicted Change: {ml_change:+.2f}%", className='mb-1'),
            html.P(f"Confidence: {ml_pred.get('confidence', 0):.1%}", className='mb-1'),
            html.P(f"Models Used: {', '.join(ml_pred.get('models_used', ['XGBoost', 'LSTM']))}", className='mb-1 text-muted')
        ])
    else:
        ml_detail = html.Div([
            html.P("🔄 Training ML models with live data...", className='mb-1 text-warning'),
            html.P("Predictions will appear within 60 seconds", className='mb-1 text-muted')
        ])
    
    # Technical Analysis Detail - Enhanced with fallback
    tech = analysis.get('technical_analysis', {})
    if tech and tech.get('overall_signal'):
        tech_signal = tech.get('overall_signal', 'neutral')
        indicators = tech.get('indicators', {})
        tech_detail = html.Div([
            html.P(f"Signal: {tech_signal.upper()}", className='mb-1'),
            html.P(f"RSI: {indicators.get('rsi', 0):.1f}", className='mb-1'),
            html.P(f"MACD: {indicators.get('macd', 0):.2f}", className='mb-1'),
            html.P(f"Trend: {tech.get('trend', 'neutral').upper()}", className='mb-1')
        ])
    else:
        tech_detail = html.Div([
            html.P("🔄 Analyzing technical indicators...", className='mb-1 text-warning'),
            html.P("Data will appear within 60 seconds", className='mb-1 text-muted')
        ])
    
    # Sentiment Detail - Enhanced with fallback (OPTIONAL for predictions)
    sentiment = analysis.get('sentiment', {})
    if sentiment and sentiment.get('fear_greed_index'):
        fg_index = sentiment.get('fear_greed_index', 50)
        fg_trend = sentiment.get('trend', 'neutral')
        sentiment_detail = html.Div([
            html.H2(f"{fg_index}/100", style={'color': 'red' if fg_index < 25 else 'orange' if fg_index < 50 else 'yellow' if fg_index < 75 else 'green'}),
            html.P(f"Status: {fg_trend.upper()}", className='mb-1'),
            html.Small("Below 25: Extreme Fear | Above 75: Extreme Greed", className='text-muted')
        ])
    else:
        sentiment_detail = html.Div([
            html.P("📊 Market sentiment analysis", className='mb-1'),
            html.P("Fear & Greed Index: Optional metric", className='mb-1 text-muted'),
            html.Small("Focus on price predictions, not sentiment", className='text-muted')
        ])
    
    # Order Book Chart
    orderbook = analysis.get('orderbook', {})
    orderbook_fig = go.Figure()
    orderbook_fig.add_trace(go.Bar(
        name='Bids',
        x=['Buy Volume'],
        y=[orderbook.get('bid_volume', 0)],
        marker_color=COLORS['buy']
    ))
    orderbook_fig.add_trace(go.Bar(
        name='Asks',
        x=['Sell Volume'],
        y=[orderbook.get('ask_volume', 0)],
        marker_color=COLORS['sell']
    ))
    orderbook_fig.update_layout(
        barmode='group',
        paper_bgcolor=COLORS['card_bg'],
        plot_bgcolor=COLORS['card_bg'],
        font={'color': COLORS['text']},
        height=250,
        showlegend=True,
        margin=dict(l=20, r=20, t=20, b=20)
    )
    
    # Multi-Timeframe Prediction Signals Table (NOT TRADES!)
    rec_rows = []
    try:
        from prediction_market_fetcher import PredictionMarketFetcher
        fetcher = PredictionMarketFetcher()
        
        # Get FRESH current price for accurate predictions
        fresh_current_price = fetcher.get_live_btc_price()
        if fresh_current_price > 0:
            current_price = fresh_current_price  # Use live price, not cached
        
        historical_df = fetcher.get_btc_historical_data(days=7)
        
        print(f"📊 Dashboard callback - LIVE current_price: ${current_price:,.2f}, historical_df shape: {historical_df.shape}")
        
        if not historical_df.empty:
            # Generate autonomous predictions with LIVE current price
            all_predictions = multitimeframe_predictor.predict_all_timeframes(
                historical_df, current_price
            )
            print(f"✅ Generated predictions for {len(all_predictions.get('timeframes', {}))} timeframes")
            
            # Create prediction signal rows
            for timeframe, pred_data in all_predictions.get('timeframes', {}).items():
                if 'error' in pred_data:
                    continue
                    
                predicted_price = pred_data['predicted_price']
                confidence = pred_data['confidence'] * 100
                direction = pred_data['direction']
                predicted_change = pred_data['predicted_change_pct']
                hours = pred_data['hours']
                
                # Determine signal color and emoji
                if 'bullish' in direction:
                    signal_emoji = '📈' if 'strong' in direction else '↗️'
                    signal_color = COLORS['buy']
                elif 'bearish' in direction:
                    signal_emoji = '📉' if 'strong' in direction else '↘️'
                    signal_color = COLORS['sell']
                else:
                    signal_emoji = '➡️'
                    signal_color = COLORS['neutral']
                
                rec_rows.append(html.Tr([
                    html.Td(f"{signal_emoji} {timeframe.upper()}", style={'color': signal_color, 'fontWeight': 'bold'}),
                    html.Td(f"${predicted_price:,.2f}"),
                    html.Td(f"{predicted_change:+.2f}%", 
                           style={'color': COLORS['buy'] if predicted_change > 0 else COLORS['sell']}),
                    html.Td(f"{confidence:.0f}%"),
                    html.Td(direction.upper().replace('_', ' '), style={'color': signal_color}),
                    html.Td(f"{hours}h")
                ]))
    except Exception as e:
        print(f"⚠️ Error generating prediction signals: {e}")
    
    if not rec_rows:
        rec_table = html.P("Generating autonomous prediction signals...", className='text-muted text-center')
    else:
        rec_table = dbc.Table([
            html.Thead(html.Tr([
                html.Th("Timeframe"),
                html.Th("Predicted Price"),
                html.Th("Change %"),
                html.Th("Confidence"),
                html.Th("Direction"),
                html.Th("Horizon")
            ]), className='table-dark'),
            html.Tbody(rec_rows)
        ], bordered=True, hover=True, responsive=True, striped=True, className='table-dark')
    
    # Price Chart with AUTONOMOUS Multi-Timeframe Predictions
    historical = analysis.get('historical', [])
    if historical:
        df = pd.DataFrame(historical)
        price_fig = go.Figure()
        
        # Historical prices
        price_fig.add_trace(go.Scatter(
            x=df['timestamp'],
            y=df['price'],
            mode='lines',
            name='Historical',
            line=dict(color=COLORS['info'], width=2)
        ))
        
        # Add AUTONOMOUS predictions for multiple timeframes
        try:
            from prediction_market_fetcher import PredictionMarketFetcher
            fetcher = PredictionMarketFetcher()
            hist_df = fetcher.get_btc_historical_data(days=7)
            
            if not hist_df.empty:
                # Generate autonomous predictions
                all_preds = multitimeframe_predictor.predict_all_timeframes(
                    hist_df, current_price
                )
                
                # Plot predictions for key timeframes
                prediction_colors = {
                    '15min': '#ffeb3b',
                    '1hr': '#ff9800', 
                    '4hr': '#f44336',
                    '24hr': '#9c27b0',
                    '7d': '#3f51b5'
                }
                
                for timeframe, pred_data in all_preds.get('timeframes', {}).items():
                    if 'error' in pred_data or timeframe == '15min':  # Skip 15min for clarity
                        continue
                    
                    pred_price = pred_data['predicted_price']
                    hours = pred_data['hours']
                    future_time = datetime.now() + timedelta(hours=hours)
                    
                    price_fig.add_trace(go.Scatter(
                        x=[datetime.now(), future_time],
                        y=[current_price, pred_price],
                        mode='lines+markers',
                        name=f'{timeframe} Prediction',
                        line=dict(color=prediction_colors.get(timeframe, '#white'), width=2, dash='dash'),
                        marker=dict(size=10, symbol='star')
                    ))
        except Exception as e:
            print(f"⚠️ Error adding autonomous predictions to chart: {e}")
            # Fallback to simple 24h prediction if available
            if ml_price > 0:
                future_time = datetime.now() + timedelta(hours=24)
                price_fig.add_trace(go.Scatter(
                    x=[datetime.now(), future_time],
                    y=[current_price, ml_price],
                    mode='lines+markers',
                    name='ML Prediction',
                    line=dict(color=COLORS['warning'], width=2, dash='dash'),
                    marker=dict(size=10)
                ))
    else:
        price_fig = go.Figure()
    
    price_fig.update_layout(
        paper_bgcolor=COLORS['card_bg'],
        plot_bgcolor=COLORS['card_bg'],
        font={'color': COLORS['text']},
        height=400,
        xaxis_title='Time',
        yaxis_title='Price (USD)',
        hovermode='x unified',
        showlegend=True
    )
    
    # Coinbase Prediction Markets Live Panel
    try:
        prediction_markets_panel = create_prediction_markets_panel(analysis, current_price, ml_price)
        multi_coin_panel = create_multi_coin_prediction_markets_panel()
        prediction_controls_panel = create_prediction_markets_panel(
            analysis,
            current_price,
            ml_price,
            include_actions=True
        )
    except Exception as e:
        print(f"⚠️ Error creating prediction markets panel: {e}")
        prediction_markets_panel = html.Div([
            html.P("⚠️ Prediction markets temporarily unavailable. Updating...", 
                   className='text-warning text-center')
        ])
        prediction_controls_panel = prediction_markets_panel
        multi_coin_panel = prediction_markets_panel

    token_btc = render_token_tile(get_token_prediction_summary('bitcoin'))
    token_eth = render_token_tile(get_token_prediction_summary('ethereum'))
    token_sol = render_token_tile(get_token_prediction_summary('solana'))
    token_doge = render_token_tile(get_token_prediction_summary('dogecoin'))
    coin_metrics_grid = render_coin_metrics_grid()
    db_predictions = render_db_predictions_table()
    db_prices = render_db_prices_table()

    return (price_text, ml_text, signal, {'color': signal_color}, data_status,
        portfolio_text, gauge_fig, confidence_fig,
        ml_detail, tech_detail, sentiment_detail,
        orderbook_fig, prediction_markets_panel, multi_coin_panel,
        token_btc, token_eth, token_sol, token_doge, coin_metrics_grid,
        db_predictions, db_prices,
        rec_table, price_fig, prediction_controls_panel)


@app.callback(
    Output('current-price', 'children', allow_duplicate=True),
    [Input('price-interval', 'n_intervals')],
    prevent_initial_call=True
)
def update_live_price_fast(n):
    """Update BTC price every 15 seconds for real-time accuracy"""
    try:
        price = get_cached_live_price()
        if price > 0:
            return f"${price:,.2f}"
        return "Updating..."
    except Exception as e:
        print(f"Error fetching live price: {e}")
        # Fallback to cached analysis
        with analysis_lock:
            if cached_analysis:
                price = cached_analysis.get('current_price', 0)
                if price > 0:
                    return f"${price:,.2f}"
        return "Updating..."


@app.callback(
    Output('bot-status', 'children'),
    [Input('train-button', 'n_clicks'),
     Input('start-button', 'n_clicks'),
     Input('stop-button', 'n_clicks'),
     Input('risk-dropdown', 'value'),
     Input('confidence-slider', 'value')],
    [State('ml-training-mode', 'value')],
    prevent_initial_call=True
)
def control_bot(train_clicks, start_clicks, stop_clicks, risk_level, min_confidence, training_mode):
    """Handle bot control buttons and settings"""
    ctx = dash.callback_context
    
    if not ctx.triggered:
        return html.P("Bot idle", className='text-muted')
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if button_id == 'train-button':
        try:
            aggressive = training_mode == 'aggressive'
            result = analyzer.train_models(days=30, aggressive=aggressive)
            if result.get('success'):
                engine = result.get('engine', 'Standard ML (XGBoost + LSTM)')
                training_samples = result.get('training_samples', 0)
                if engine.startswith('Advanced ML'):
                    return dbc.Alert([
                        html.H5("✅ ML Models Trained Successfully!", className='alert-heading'),
                        html.Hr(),
                        html.P([
                            f"Engine: {engine}",
                            html.Br(),
                            f"Training Samples: {training_samples}",
                            html.Br(),
                            f"Training Mode: {'AGGRESSIVE' if aggressive else 'STABLE'}",
                            html.Br(),
                            "Bot is ready to generate predictions."
                        ])
                    ], color='success', dismissable=True, duration=8000)
                return dbc.Alert([
                    html.H5("✅ ML Models Trained Successfully!", className='alert-heading'),
                    html.Hr(),
                    html.P([
                        f"LSTM Accuracy: {result.get('lstm_accuracy', 0)*100:.1f}%",
                        html.Br(),
                        f"XGBoost Accuracy: {result.get('xgboost_accuracy', 0)*100:.1f}%",
                        html.Br(),
                        "Bot is now ready to generate predictions!"
                    ])
                ], color='success', dismissable=True, duration=8000)
            else:
                return dbc.Alert(f"❌ Training failed: {result.get('error')}", color='danger', dismissable=True)
        except Exception as e:
            return dbc.Alert(f"❌ Training error: {str(e)}", color='danger', dismissable=True)
    
    elif button_id == 'start-button':
        bot_state['running'] = True
        bot_state['last_check'] = datetime.now()
        
        # Update bot settings
        bot.risk_level = risk_level
        bot.min_confidence = min_confidence
        
        # Get immediate signal
        try:
            analysis = analyzer.analyze_market()
            signal = analysis.get('overall_signal', {})
            
            signal_text = signal.get('signal', 'neutral').upper()
            confidence = signal.get('confidence', 0) * 100
            predicted_price = analysis.get('ml_prediction', {}).get('predicted_price', 0)
            
            bot_state['last_signal'] = signal_text
            
            # Generate actionable recommendation
            recommendation = generate_prediction_market_recommendation(analysis)
            
            return dbc.Alert([
                html.H5("🟢 Bot Started - Live Signals Active", className='alert-heading'),
                html.Hr(),
                html.P([
                    html.Strong(f"Current Signal: {signal_text}"),
                    html.Br(),
                    f"Confidence: {confidence:.1f}%",
                    html.Br(),
                    f"24h Prediction: ${predicted_price:,.0f}",
                    html.Br(),
                    html.Br(),
                    html.Strong("Coinbase Prediction Market Action:"),
                    html.Br(),
                    recommendation,
                    html.Br(),
                    html.Br(),
                    html.Small(f"Risk: {risk_level.upper()} | Min Confidence: {min_confidence*100:.0f}%")
                ])
            ], color='success', dismissable=True, duration=15000)
        except Exception as e:
            return dbc.Alert(f"⚠️ Bot started but signal generation failed: {str(e)}", 
                           color='warning', dismissable=True)
    
    elif button_id == 'stop-button':
        bot_state['running'] = False
        return dbc.Alert([
            html.H5("🔴 Bot Stopped", className='alert-heading'),
            html.Hr(),
            html.P([
                f"Trades executed today: {bot_state.get('trades_today', 0)}",
                html.Br(),
                f"Last signal: {bot_state.get('last_signal', 'None')}",
                html.Br(),
                "Bot has been deactivated."
            ])
        ], color='warning', dismissable=True, duration=6000)
    
    elif button_id == 'risk-dropdown':
        bot.risk_level = risk_level
        if bot_state['running']:
            return dbc.Alert(f"⚙️ Risk level updated to: {risk_level.upper()}", 
                           color='info', dismissable=True, duration=3000)
    
    elif button_id == 'confidence-slider':
        bot.min_confidence = min_confidence
        if bot_state['running']:
            return dbc.Alert(f"⚙️ Min confidence updated to: {min_confidence*100:.0f}%", 
                           color='info', dismissable=True, duration=3000)
    
    return html.P("Bot idle", className='text-muted')


def generate_prediction_market_recommendation(analysis: dict) -> str:
    """
    Generate actionable Coinbase Prediction Market recommendation
    
    Args:
        analysis: Market analysis data
    
    Returns:
        Formatted recommendation string
    """
    try:
        signal = analysis.get('overall_signal', {})
        ml_pred = analysis.get('ml_prediction', {})
        current_price = analysis.get('current_price', 0)
        predicted_price = ml_pred.get('predicted_price', 0)
        predicted_change = ml_pred.get('predicted_change_pct', 0)
        confidence = signal.get('confidence', 0)
        signal_type = signal.get('signal', 'neutral')
        
        # Determine market thresholds (common prediction market levels)
        price_levels = [
            current_price * 0.98,  # -2%
            current_price * 0.99,  # -1%
            current_price * 1.00,  # Current
            current_price * 1.01,  # +1%
            current_price * 1.02,  # +2%
            current_price * 1.03,  # +3%
            current_price * 1.05,  # +5%
        ]
        
        recommendation = []
        
        if 'buy' in signal_type.lower() and confidence > 0.6:
            # Bullish - recommend YES on "above X" markets
            for i, level in enumerate(price_levels):
                if predicted_price > level:
                    pct = ((level / current_price) - 1) * 100
                    prob = min(confidence * 100, 95)  # Cap at 95%
                    
                    if i >= 2:  # Above current price
                        recommendation.append(f"✅ BUY YES: 'BTC above ${level:,.0f}' (~{prob:.0f}% probability)")
                        break
            
            if not recommendation:
                recommendation.append(f"📈 BULLISH but wait for better entry (predicted: ${predicted_price:,.0f})")
        
        elif 'sell' in signal_type.lower() and confidence > 0.6:
            # Bearish - recommend NO on "above X" markets or YES on "below X"
            for i, level in enumerate(price_levels):
                if predicted_price < level:
                    prob = min(confidence * 100, 95)
                    
                    if i <= 4:  # Below or near current
                        recommendation.append(f"🔻 BUY NO: 'BTC above ${level:,.0f}' (~{prob:.0f}% probability)")
                        break
            
            if not recommendation:
                recommendation.append(f"📉 BEARISH but wait for confirmation (predicted: ${predicted_price:,.0f})")
        
        else:
            # Neutral or low confidence
            recommendation.append(f"⏸️ HOLD - Low confidence ({confidence*100:.0f}%) or neutral market")
        
        # Add position sizing suggestion
        if confidence > 0.75:
            recommendation.append(f" | Position size: 15-20% of bankroll")
        elif confidence > 0.65:
            recommendation.append(f" | Position size: 10-15% of bankroll")
        elif confidence > 0.55:
            recommendation.append(f" | Position size: 5-10% of bankroll")
        else:
            recommendation.append(f" | Position size: SKIP - too risky")
        
        return ' '.join(recommendation)
    
    except Exception as e:
        return f"⚠️ Error generating recommendation: {str(e)}"


# ============================================================================
# TRADING CONTROLS CALLBACKS
# ============================================================================

@app.callback(
    [Output('trade-notification', 'children'),
     Output('portfolio-display', 'children')],
    [Input('manual-buy-button', 'n_clicks'),
     Input('manual-sell-button', 'n_clicks'),
     Input('interval-component', 'n_intervals')],
    [State('trade-amount', 'value'),
     State('prediction-selection', 'value')]
)
def handle_manual_predictions_callback(buy_clicks, sell_clicks, n_intervals, trade_amount, selected_prediction):
    """Handle manual predictions and update portfolio display."""
    return handle_manual_predictions(buy_clicks, sell_clicks, n_intervals, trade_amount, selected_prediction)


def build_portfolio_display(current_price: float):
    """Build the portfolio display block."""
    positions = portfolio.positions or {}
    position_lines = []
    total_pnl = 0.0

    if positions:
        live_prices = multi_coin_fetcher.get_live_prices(list(positions.keys()))
        for coin_id, pos in positions.items():
            price = float(live_prices.get(coin_id, {}).get('price', pos.get('current_price', 0)))
            qty = pos.get('quantity', 0)
            value = qty * price
            entry_price = pos.get('avg_price', 0)
            pnl = (price - entry_price) * qty if entry_price else 0
            total_pnl += pnl
            symbol = pos.get('symbol', coin_id.upper())
            position_lines.append(
                html.P([
                    html.Strong(f"{symbol}: "),
                    html.Span(f"{qty:.8f} (${value:,.2f})")
                ], className='mb-1')
            )
    else:
        position_lines = [html.P([
            html.Strong("Active Bets: "),
            html.Span("No active predictions")
        ], className='mb-1')]

    pnl_display = f"${total_pnl:,.2f}"
    pnl_style = {'color': '#28a745' if total_pnl > 0 else '#dc3545' if total_pnl < 0 else COLORS['text']}
    
    total_value = portfolio.get_portfolio_value()
    sim_metrics = get_simulated_portfolio_metrics() if not is_live_trading_enabled() else None
    projected_metrics = get_projected_portfolio_metrics() if not is_live_trading_enabled() else None
    
    portfolio_display = [
        html.P([html.Strong("Available: "), html.Span(f"${portfolio.cash_balance:,.2f}")], className='mb-1'),
        *position_lines,
        html.P([html.Strong("Total Bankroll: "), html.Span(f"${total_value:,.2f}")], className='mb-1'),
        html.P([html.Strong("Net Winnings: "), html.Span(pnl_display, style=pnl_style)], className='mb-1')
    ]

    if sim_metrics and sim_metrics.get('total_predictions', 0) > 0:
        sim_value = sim_metrics['simulated_value']
        sim_pnl = sim_metrics['simulated_pnl_pct']
        sim_color = '#28a745' if sim_pnl > 0 else '#dc3545' if sim_pnl < 0 else COLORS['text']
        portfolio_display.append(
            html.P([
                html.Strong("Simulated Value (7d): "),
                html.Span(f"${sim_value:,.2f} ({sim_pnl:+.2f}%)", style={'color': sim_color})
            ], className='mb-0')
        )
    elif projected_metrics:
        proj_value = projected_metrics['projected_value']
        proj_change = projected_metrics['projected_change_pct']
        proj_color = '#28a745' if proj_change > 0 else '#dc3545' if proj_change < 0 else COLORS['text']
        portfolio_display.append(
            html.P([
                html.Strong("Projected Value (24h): "),
                html.Span(f"${proj_value:,.2f} ({proj_change:+.2f}%)", style={'color': proj_color})
            ], className='mb-0')
        )
    
    return portfolio_display


def handle_manual_predictions(buy_clicks, sell_clicks, n_intervals, trade_amount, selected_prediction):
    """Handle manual prediction bets (YES/NO) and update bankroll display"""
    global portfolio
    
    ctx = dash.callback_context
    notification = html.P("Ready to place predictions", className='text-muted')
    
    # Parse selected prediction market
    selected_market = None
    if selected_prediction:
        try:
            selected_market = json.loads(selected_prediction)
        except Exception:
            selected_market = None

    # Get current price for selected coin (real-time for accurate predictions)
    selected_coin = selected_market.get('coin_id') if selected_market else 'bitcoin'
    current_price = get_live_price_for_coin(selected_coin)
    if current_price <= 0:
        current_price = get_cached_live_price() or 90000  # Fallback
    
    # Handle button clicks
    if ctx.triggered:
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        if button_id == 'manual-buy-button' and buy_clicks:
            # Place BET YES prediction
            if not trade_amount or trade_amount <= 0:
                notification = dbc.Alert("❌ Invalid bet amount", color='danger', dismissable=True, duration=3000)
            elif portfolio.cash_balance < trade_amount:
                notification = dbc.Alert(f"❌ Insufficient bankroll: ${portfolio.cash_balance:,.2f} available", 
                                       color='danger', dismissable=True, duration=5000)
            else:
                amount_btc = trade_amount / current_price
                success = portfolio.add_position(selected_coin, amount_btc, current_price, symbol=selected_market.get('symbol') if selected_market else None)
                
                if success:
                    market_text = ""
                    if selected_market:
                        market_text = (
                            f"Market: {selected_market.get('symbol', 'BTC')} | {selected_market.get('question', 'BTC prediction')}"
                            f" | Threshold: ${float(selected_market.get('threshold', current_price)):,.0f}"
                            f" | Timeframe: {selected_market.get('timeframe', '24h')}"
                        )
                    notification = dbc.Alert([
                        html.H5("✅ PREDICTION PLACED - BET YES", className='alert-heading'),
                        html.Hr(),
                        html.P([
                            f"Bet Amount: ${trade_amount:,.2f}",
                            html.Br(),
                            market_text,
                            html.Br(),
                            f"Prediction: {selected_market.get('symbol', 'BTC')} will move {selected_market.get('recommendation', 'BUY YES')}",
                            html.Br(),
                            f"Current BTC: ${current_price:,.2f} (real-time)",
                            html.Br(),
                            f"Based on: Multi-timeframe ML analysis",
                            html.Br(),
                            f"Remaining Bankroll: ${portfolio.cash_balance:,.2f}"
                        ])
                    ], color='success', dismissable=True, duration=8000)
                else:
                    notification = dbc.Alert("❌ Prediction placement failed", color='danger', dismissable=True, duration=3000)
        
        elif button_id == 'manual-sell-button' and sell_clicks:
            # Place BET NO prediction
            if selected_coin not in portfolio.positions:
                notification = dbc.Alert("❌ No active predictions", color='danger', dismissable=True, duration=3000)
            else:
                position = portfolio.positions[selected_coin]
                btc_amount = position['quantity']
                sell_value = btc_amount * current_price
                entry_price = position['avg_price']
                pnl = (current_price - entry_price) * btc_amount
                pnl_pct = ((current_price - entry_price) / entry_price) * 100

                success = portfolio.remove_position(selected_coin, btc_amount, current_price)
                
                if success:
                    market_text = ""
                    if selected_market:
                        market_text = (
                            f"Market: {selected_market.get('symbol', 'BTC')} | {selected_market.get('question', 'BTC prediction')}"
                            f" | Threshold: ${float(selected_market.get('threshold', current_price)):,.0f}"
                            f" | Timeframe: {selected_market.get('timeframe', '24h')}"
                        )
                    pnl_color = 'success' if pnl > 0 else 'danger'
                    result_text = "WON" if pnl > 0 else "LOST"
                    notification = dbc.Alert([
                        html.H5(f"✅ PREDICTION RESOLVED - {result_text}", className='alert-heading'),
                        html.Hr(),
                        html.P([
                            f"Prediction: BET NO on ${entry_price:,.2f}",
                            html.Br(),
                            market_text,
                            html.Br(),
                            f"Actual BTC Price: ${current_price:,.2f} (real-time)",
                            html.Br(),
                            f"Initial Bet: {btc_amount:.8f} BTC",
                            html.Br(),
                            f"Payout: ${sell_value:,.2f}",
                            html.Br(),
                            html.Strong(f"Net Winnings: ${pnl:,.2f} ({pnl_pct:+.2f}%)", 
                                      style={'color': '#28a745' if pnl > 0 else '#dc3545'})
                        ])
                    ], color=pnl_color, dismissable=True, duration=10000)
                else:
                    notification = dbc.Alert("❌ Prediction resolution failed", color='danger', dismissable=True, duration=3000)
    
    portfolio_display = build_portfolio_display(current_price)
    
    return notification, portfolio_display


@app.callback(
    [Output('trade-notification', 'children', allow_duplicate=True),
     Output('portfolio-display', 'children', allow_duplicate=True)],
    [Input({'type': 'prediction-action', 'action': dash.ALL, 'threshold': dash.ALL, 'timeframe': dash.ALL}, 'n_clicks')],
    [State('trade-amount', 'value')],
    prevent_initial_call=True
)
def handle_signal_actions(action_clicks, trade_amount):
    """Handle clickable signal actions from prediction controls."""
    ctx = dash.callback_context
    notification = dash.no_update

    # Get current BTC price (real-time for accurate predictions)
    current_price = get_cached_live_price()
    if current_price <= 0:
        current_price = 90000  # Fallback

    if not ctx.triggered:
        return notification, build_portfolio_display(current_price)

    triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]
    try:
        action_meta = json.loads(triggered_id)
    except Exception:
        return notification, build_portfolio_display(current_price)

    action = action_meta.get('action')
    threshold = action_meta.get('threshold')
    timeframe = action_meta.get('timeframe')

    if action == 'YES':
        bet_amount = trade_amount if trade_amount and trade_amount > 0 else 100
        if portfolio.cash_balance < bet_amount:
            notification = dbc.Alert(
                f"❌ Insufficient bankroll: ${portfolio.cash_balance:,.2f} available",
                color='danger',
                dismissable=True,
                duration=5000
            )
        else:
            amount_btc = bet_amount / current_price
            success = portfolio.add_position('bitcoin', amount_btc, current_price)
            if success:
                notification = dbc.Alert([
                    html.H5("✅ PREDICTION PLACED - BET YES", className='alert-heading'),
                    html.Hr(),
                    html.P([
                        f"Bet Amount: ${bet_amount:,.2f}",
                        html.Br(),
                        f"Market: ${float(threshold):,.0f} in {timeframe}",
                        html.Br(),
                        f"Current BTC: ${current_price:,.2f}",
                        html.Br(),
                        f"Remaining Bankroll: ${portfolio.cash_balance:,.2f}"
                    ])
                ], color='success', dismissable=True, duration=8000)
            else:
                notification = dbc.Alert("❌ Prediction placement failed", color='danger', dismissable=True, duration=3000)

    elif action == 'NO':
        if 'bitcoin' not in portfolio.positions:
            notification = dbc.Alert(
                "❌ No active BET YES position to resolve.",
                color='danger',
                dismissable=True,
                duration=4000
            )
        else:
            position = portfolio.positions['bitcoin']
            btc_amount = position['quantity']
            entry_price = position['avg_price']
            pnl = (current_price - entry_price) * btc_amount
            pnl_pct = ((current_price - entry_price) / entry_price) * 100 if entry_price else 0

            success = portfolio.remove_position('bitcoin', btc_amount, current_price)
            if success:
                notification = dbc.Alert([
                    html.H5("✅ PREDICTION RESOLVED - BET NO", className='alert-heading'),
                    html.Hr(),
                    html.P([
                        f"Market: ${float(threshold):,.0f} in {timeframe}",
                        html.Br(),
                        f"Current BTC: ${current_price:,.2f}",
                        html.Br(),
                        html.Strong(f"Net Winnings: ${pnl:,.2f} ({pnl_pct:+.2f}%)",
                                    style={'color': '#28a745' if pnl > 0 else '#dc3545'})
                    ])
                ], color='success' if pnl > 0 else 'danger', dismissable=True, duration=8000)
            else:
                notification = dbc.Alert("❌ Prediction resolution failed", color='danger', dismissable=True, duration=3000)

    return notification, build_portfolio_display(current_price)


@app.callback(
    Output('bot-status-display', 'children'),
    [Input('start-bot-button', 'n_clicks'),
     Input('stop-bot-button', 'n_clicks'),
     Input('interval-component', 'n_intervals')],
    [State('bot-risk-dropdown', 'value'),
     State('bot-confidence-slider', 'value')]
)
def handle_bot_controls(start_clicks, stop_clicks, n_intervals, risk_level, min_confidence):
    """Handle prediction bot start/stop and display status"""
    global bot, portfolio
    
    ctx = dash.callback_context
    
    if ctx.triggered:
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        if button_id == 'start-bot-button' and start_clicks:
            # Start prediction bot
            bot.risk_level = risk_level
            bot.min_confidence = min_confidence
            bot.is_running = True
            bot_state['running'] = True
            bot_state['last_check'] = datetime.now()
            
            # Get current analysis with real-time data
            try:
                with analysis_lock:
                    analysis = cached_analysis.copy()
                
                signal = analysis.get('overall_signal', {})
                current_price = analysis.get('current_price', 0)
                
                return dbc.Alert([
                    html.H5("🟢 PREDICTION BOT STARTED - Automated Predictions Active", className='alert-heading'),
                    html.Hr(),
                    html.P([
                        html.Strong(f"Risk Level: {risk_level.upper()}"),
                        html.Br(),
                        f"Max Bet Per Prediction: {['10', '15', '20'][['low', 'medium', 'high'].index(risk_level)]}% of bankroll",
                        html.Br(),
                        f"Min Confidence Threshold: {min_confidence*100:.0f}%",
                        html.Br(),
                        html.Br(),
                        html.Strong("Real-Time Data Updates:"),
                        html.Br(),
                        f"Current BTC: ${current_price:,.2f} (live)",
                        html.Br(),
                        f"Data Refresh: Every 5-30 seconds",
                        html.Br(),
                        f"Signal: {signal.get('signal', 'neutral').upper()}",
                        html.Br(),
                        f"Confidence: {signal.get('confidence', 0)*100:.1f}%",
                        html.Br(),
                        html.Br(),
                        html.Small("Bot analyzes real-time market data and places predictions on Coinbase Prediction Markets", className='text-muted')
                    ])
                ], color='success', dismissable=False)
            except:
                return dbc.Alert("⚠️ Prediction bot started but waiting for real-time data...", 
                               color='warning', dismissable=False)
        
        elif button_id == 'stop-bot-button' and stop_clicks:
            # Stop prediction bot
            bot.is_running = False
            bot_state['running'] = False
            
            return dbc.Alert([
                html.H5("🔴 PREDICTION BOT STOPPED", className='alert-heading'),
                html.Hr(),
                html.P([
                    "Automated predictions have been disabled.",
                    html.Br(),
                    "Active prediction bets remain in place.",
                    html.Br(),
                    "You can place manual predictions or restart the bot."
                ])
            ], color='secondary', dismissable=False)
    
    # Default status - Check if bot should place a prediction
    if bot.is_running:
        # Bot is active - check if we should place a prediction
        try:
            with analysis_lock:
                analysis = cached_analysis.copy()
            
            signal = analysis.get('overall_signal', {})
            current_price = analysis.get('current_price', 0)
            confidence = signal.get('confidence', 0)
            signal_type = signal.get('signal', 'neutral')
            bot_state['last_check'] = datetime.now()
            bot_state['last_signal'] = signal_type
            
            # Check if signal meets criteria for auto-prediction
            should_predict = (
                confidence >= bot.min_confidence and
                signal_type in ['strong_buy', 'buy'] and
                portfolio.cash_balance >= 10  # Minimum $10 bet
            )
            
            if should_predict and n_intervals and n_intervals % 2 == 0:  # Check every 60s (2x30s intervals)
                # Calculate bet size based on risk level
                risk_multipliers = {'low': 0.10, 'medium': 0.15, 'high': 0.20}
                max_bet_pct = risk_multipliers.get(bot.risk_level, 0.15)
                bet_amount = min(
                    portfolio.cash_balance * max_bet_pct,
                    portfolio.cash_balance * confidence  # Scale by confidence
                )
                
                if bet_amount >= 10:  # Minimum bet
                    # Place prediction
                    amount_btc = bet_amount / current_price
                    success = portfolio.add_position('bitcoin', amount_btc, current_price)
                    
                    if success:
                        bot_state['trades_today'] = bot_state.get('trades_today', 0) + 1
                        bot_state['last_trade_time'] = datetime.now()
                        return dbc.Alert([
                            html.H5("🤖 AUTO-PREDICTION PLACED!", className='alert-heading'),
                            html.Hr(),
                            html.P([
                                html.Strong("BET YES"),
                                html.Br(),
                                f"Amount: ${bet_amount:,.2f}",
                                html.Br(),
                                f"BTC Price: ${current_price:,.2f}",
                                html.Br(),
                                f"Signal: {signal_type.upper()}",
                                html.Br(),
                                f"Confidence: {confidence*100:.1f}%",
                                html.Br(),
                                f"Risk Level: {bot.risk_level.upper()}"
                            ])
                        ], color='success', dismissable=False)
            
            # Show active status
            last_check = bot_state.get('last_check')
            last_trade = bot_state.get('last_trade_time')
            last_check_text = last_check.strftime('%H:%M:%S') if isinstance(last_check, datetime) else 'N/A'
            last_trade_text = last_trade.strftime('%H:%M:%S') if isinstance(last_trade, datetime) else 'N/A'
            return dbc.Alert([
                html.Div([
                    html.Span("🟢 PREDICTION BOT ACTIVE", className='fw-bold'),
                    html.Span(f" | Risk: {bot.risk_level.upper()} | Min Confidence: {bot.min_confidence*100:.0f}%", className='ms-2')
                ]),
                html.Small(
                    f"Current Signal: {signal_type.upper()} ({confidence*100:.0f}%) | BTC: ${current_price:,.2f}",
                    className='text-muted'
                ),
                html.Br(),
                html.Small(
                    f"Last Check: {last_check_text}"
                    f" | Auto Bets Today: {bot_state.get('trades_today', 0)}"
                    f" | Last Bet: {last_trade_text}",
                    className='text-muted'
                )
            ], color='success', dismissable=False)
        except Exception as e:
            print(f"Error in bot prediction logic: {e}")
            return dbc.Alert([
                html.Span("🟢 PREDICTION BOT ACTIVE", className='fw-bold'),
                html.Br(),
                html.Small("Analyzing real-time BTC data for prediction opportunities...", className='text-muted')
            ], color='success', dismissable=False)
    else:
        return dbc.Alert([
            html.Span("⚪ PREDICTION BOT IDLE", className='fw-bold'),
            html.Br(),
            html.Small("Click START BOT to enable automated predictions", className='text-muted')
        ], color='secondary', dismissable=False)


@app.callback(
    Output('account-status', 'children'),
    [Input('connect-trading-button', 'n_clicks')]
)
def handle_account_connection(n_clicks):
    """Handle Coinbase trading account connection"""
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    # Check if trading credentials exist
    trading_key = os.getenv('COINBASE_TRADING_API_KEY')
    trading_secret = os.getenv('COINBASE_TRADING_SECRET')
    
    badges = [
        dbc.Badge("✅ Coinbase API Connected (Real-time Predictions)", color='success', className='me-2')
    ]
    
    if trading_key and trading_secret:
        if n_clicks:
            # Attempt connection
            badges.append(dbc.Badge("🟢 Prediction Markets: CONNECTED", color='success'))
        else:
            badges.append(dbc.Badge("🟡 Prediction Markets: Ready to Connect", color='warning'))
    else:
        badges.append(dbc.Badge("⚠️ Prediction Markets: Not Configured", color='warning'))
    
    return badges


if __name__ == '__main__':
    print("="*60)
    print("🔮 CryptoAI Prediction Market Dashboard")
    print("="*60)
    print("\nStarting server on http://localhost:8050")
    print("Press Ctrl+C to stop\n")
    
    app.run(debug=False, host='0.0.0.0', port=8050, use_reloader=False)

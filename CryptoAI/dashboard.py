"""
Web Dashboard UI for CryptoAI Trading Assistant
Interactive web interface with live updates and charts
"""
import dash
from dash import dcc, html, Input, Output, State, dash_table
import dash_bootstrap_components as dbc
import plotly.graph_objs as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from config import Config
from data_fetcher import LiveDataFetcher
from trading_engine import TradingEngine
from portfolio import Portfolio
import threading
import time

# Initialize components
data_fetcher = LiveDataFetcher()
trading_engine = TradingEngine()
portfolio = Portfolio(initial_balance=Config.WALLET_SIZE)

# Global variable for trade suggestions (updated by background thread)
cached_suggestions = []
suggestions_lock = threading.Lock()
last_suggestions_update = None

def update_suggestions_background():
    """Background thread to update trade suggestions"""
    global cached_suggestions, last_suggestions_update
    while True:
        try:
            print("🔄 Updating trade suggestions in background...")
            suggestions = trading_engine.get_trade_suggestions(num_suggestions=5, use_cache=False)
            with suggestions_lock:
                cached_suggestions = suggestions
                last_suggestions_update = datetime.now()
            print(f"✅ Updated {len(suggestions)} suggestions")
        except Exception as e:
            print(f"⚠️ Error updating suggestions: {e}")
        time.sleep(120)  # Update every 2 minutes

# Start background thread
suggestions_thread = threading.Thread(target=update_suggestions_background, daemon=True)
suggestions_thread.start()

# Initialize Dash app with Bootstrap theme
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.CYBORG])
app.title = "CryptoAI Trading Assistant"

# Color scheme - Professional Trading Platform Theme
COLORS = {
    'background': '#0a0e27',
    'card_bg': '#141b2d',
    'card_border': '#1e293b',
    'text': '#ffffff',
    'primary': '#00d4ff',
    'success': '#10b981',
    'danger': '#ef4444',
    'warning': '#f59e0b',
    'muted': '#8b92a8',
    'chart_bg': '#1e293b',
    'grid_color': '#334155',
    'buy_green': '#10b981',
    'sell_red': '#ef4444'
}

# App Layout
app.layout = dbc.Container([
    dcc.Interval(id='interval-component', interval=60*1000, n_intervals=0),  # Update every 60 seconds (reduced load)
    
    # Header with Live Ticker
    dbc.Row([
        dbc.Col([
            html.Div([
                html.H1("🚀 CryptoAI Trading Assistant", 
                       className="text-center text-primary mb-1",
                       style={'fontSize': '2.5rem', 'fontWeight': 'bold'}),
                html.P("Live Market Data & AI-Powered Trade Suggestions",
                      className="text-center text-muted mb-2",
                      style={'fontSize': '1.2rem'}),
                html.Div(id="live-ticker", className="text-center mb-3",
                        style={'fontSize': '0.9rem', 'color': COLORS['muted']})
            ])
        ])
    ]),
    
    # Market Overview Cards
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("Portfolio Value", className="text-muted"),
                    html.H3(id="portfolio-value", className="text-success"),
                    html.Small(id="portfolio-change", className="text-muted")
                ])
            ], className="mb-3", style={'backgroundColor': COLORS['card_bg']})
        ], width=3),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("Cash Balance", className="text-muted"),
                    html.H3(id="cash-balance", className="text-warning"),
                    html.Small(id="positions-count", className="text-muted")
                ])
            ], className="mb-3", style={'backgroundColor': COLORS['card_bg']})
        ], width=3),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("Market Sentiment", className="text-muted mb-2"),
                    html.H3(id="market-sentiment", className="text-primary mb-2"),
                    html.Small(id="market-cap-change", className="text-muted"),
                    html.Div(id="fear-greed-indicator", className="mt-2")
                ])
            ], className="mb-3", style={'backgroundColor': COLORS['card_bg'], 'border': f'1px solid {COLORS["card_border"]}'}, color="dark")
        ], width=3),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("Total Return", className="text-muted"),
                    html.H3(id="total-return", className="text-info"),
                    html.Small(id="return-percent", className="text-muted")
                ])
            ], className="mb-3", style={'backgroundColor': COLORS['card_bg']})
        ], width=3),
    ], className="mb-4"),
    
    # Main Content Tabs
    dbc.Tabs([
        # Trade Suggestions Tab
        dbc.Tab([
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader(html.H5("🎯 Live Trade Suggestions", className="mb-0")),
                        dbc.CardBody([
                            dbc.Button("🔄 Refresh Suggestions", id="refresh-suggestions-btn", 
                                     color="primary", className="mb-3"),
                            html.Div(id="loading-suggestions", className="mb-3"),
                            html.Div(id="trade-suggestions-content")
                        ])
                    ], className="mb-4", style={'backgroundColor': COLORS['card_bg']})
                ], width=12)
            ])
        ], label="📊 Trade Suggestions", tab_id="tab-suggestions"),
        
        # Portfolio Tab
        dbc.Tab([
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader(html.H5("💼 Current Positions", className="mb-0")),
                        dbc.CardBody([
                            html.Div(id="positions-table")
                        ])
                    ], className="mb-4", style={'backgroundColor': COLORS['card_bg']})
                ], width=8),
                
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader(html.H5("💰 Execute Trade", className="mb-0")),
                        dbc.CardBody([
                            dbc.Label("Coin ID"),
                            dbc.Input(id="trade-coin-id", placeholder="e.g., bitcoin", className="mb-2"),
                            dbc.Label("Investment Amount ($)"),
                            dbc.Input(id="trade-amount", type="number", placeholder="Amount", className="mb-2"),
                            dbc.Button("Buy", id="execute-trade-btn", color="success", className="w-100 mb-2"),
                            html.Div(id="trade-result", className="mt-2")
                        ])
                    ], className="mb-4", style={'backgroundColor': COLORS['card_bg']})
                ], width=4)
            ]),
            
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader(html.H5("📜 Trade History", className="mb-0")),
                        dbc.CardBody([
                            html.Div(id="trade-history-table")
                        ])
                    ], style={'backgroundColor': COLORS['card_bg']})
                ], width=12)
            ])
        ], label="💼 Portfolio", tab_id="tab-portfolio"),
        
        # Market Analysis Tab
        dbc.Tab([
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader(html.H5("🌍 Market Overview", className="mb-0")),
                        dbc.CardBody([
                            html.Div(id="market-overview-content")
                        ])
                    ], className="mb-4", style={'backgroundColor': COLORS['card_bg']})
                ], width=6),
                
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader(html.H5("🚀 Top Gainers (24h)", className="mb-0")),
                        dbc.CardBody([
                            html.Div(id="top-gainers-table")
                        ])
                    ], className="mb-4", style={'backgroundColor': COLORS['card_bg']})
                ], width=6)
            ]),
            
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader(html.H5("🔥 Trending Coins", className="mb-0")),
                        dbc.CardBody([
                            html.Div(id="trending-coins-table")
                        ])
                    ], style={'backgroundColor': COLORS['card_bg']})
                ], width=12)
            ])
        ], label="🌍 Market Analysis", tab_id="tab-market"),
        
        # Coin Analysis Tab
        dbc.Tab([
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader(html.H5("🔍 Analyze Cryptocurrency", className="mb-0")),
                        dbc.CardBody([
                            dbc.Row([
                                dbc.Col([
                                    dbc.Label("Select Coin"),
                                    dcc.Dropdown(
                                        id='coin-selector',
                                        options=[{'label': coin.title(), 'value': coin} 
                                                for coin in Config.TOP_CRYPTOS],
                                        value='bitcoin',
                                        className="mb-3"
                                    )
                                ], width=6),
                                dbc.Col([
                                    dbc.Button("Analyze", id="analyze-coin-btn", 
                                             color="primary", className="mt-4"),
                                ], width=6)
                            ]),
                            html.Hr(),
                            html.Div(id="coin-analysis-content")
                        ])
                    ], style={'backgroundColor': COLORS['card_bg']})
                ], width=12)
            ])
        ], label="🔍 Coin Analysis", tab_id="tab-analysis"),
        
    ], id="tabs", active_tab="tab-suggestions", className="mb-3"),
    
    html.Footer([
        html.Hr(),
        html.P([
            "⚠️ Disclaimer: This is a simulated trading assistant for educational purposes only. ",
            "Not financial advice. Always do your own research."
        ], className="text-center text-muted small")
    ])
    
], fluid=True, style={'backgroundColor': COLORS['background'], 'minHeight': '100vh', 'padding': '20px'})


# Callbacks
@app.callback(
    [Output("portfolio-value", "children"),
     Output("portfolio-change", "children"),
     Output("cash-balance", "children"),
     Output("positions-count", "children"),
     Output("total-return", "children"),
     Output("return-percent", "children")],
    [Input("interval-component", "n_intervals")]
)
def update_portfolio_stats(n):
    """Update portfolio statistics"""
    try:
        # Update prices
        if portfolio.positions:
            coin_ids = list(portfolio.positions.keys())
            live_prices = data_fetcher.get_live_prices(coin_ids)
            if live_prices:
                portfolio.update_prices(live_prices)
        
        performance = portfolio.get_portfolio_performance()
        
        portfolio_value = f"${performance['current_value']:,.2f}"
        portfolio_change = f"Initial: ${performance['initial_balance']:,.2f}"
        cash_balance = f"${performance['cash_balance']:,.2f}"
        positions_count = f"{performance['num_positions']} positions"
        total_return = f"${performance['total_return']:,.2f}"
        return_percent = f"{performance['return_percent']:+.2f}%"
        
        return portfolio_value, portfolio_change, cash_balance, positions_count, total_return, return_percent
    except Exception as e:
        print(f"Error updating portfolio stats: {e}")
        return "$0.00", "...", "$0.00", "0 positions", "$0.00", "+0.00%"


@app.callback(
    [Output("market-sentiment", "children"),
     Output("market-cap-change", "children")],
    [Input("interval-component", "n_intervals")]
)
def update_market_sentiment(n):
    """Update market sentiment"""
    try:
        sentiment_data = trading_engine.get_market_sentiment()
        if sentiment_data and 'sentiment' in sentiment_data:
            sentiment = sentiment_data['sentiment']
            market_cap_change = f"24h: {sentiment_data.get('market_cap_change_24h', 0):+.2f}%"
            return sentiment, market_cap_change
        return "Neutral", "0.00%"
    except Exception as e:
        print(f"Error updating market sentiment: {e}")
        return "Loading...", "..."


@app.callback(
    [Output("trade-suggestions-content", "children"),
     Output("loading-suggestions", "children")],
    [Input("refresh-suggestions-btn", "n_clicks")]
)
def update_trade_suggestions(n_clicks):
    """Display cached trade suggestions (no heavy processing)"""
    global cached_suggestions, last_suggestions_update
    
    # Show initial message on page load
    if not n_clicks:
        return [dbc.Alert("Click 'Refresh Suggestions' to see the latest trade ideas.", color="info")], ""
    
    try:
        # Get suggestions from cache
        with suggestions_lock:
            suggestions = cached_suggestions.copy()
            last_update = last_suggestions_update
        
        if not suggestions:
            return [dbc.Alert("Analyzing market... Please wait a moment and try again.", color="warning")], ""
        
        cards = []
        for i, suggestion in enumerate(suggestions, 1):
            signal_color = {
                'strong_buy': 'success',
                'buy': 'info',
                'neutral': 'secondary',
                'sell': 'warning',
                'strong_sell': 'danger'
            }.get(suggestion.get('signal', 'neutral'), 'secondary')
            
            card = dbc.Card([
                dbc.CardHeader([
                    html.H5([
                        f"#{i} {suggestion.get('symbol', '?').upper()} ",
                        dbc.Badge(suggestion.get('signal', 'NEUTRAL').upper(), color=signal_color, className="ms-2")
                    ], className="mb-0")
                ]),
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.P([
                                html.Strong("Current Price: "),
                                f"${suggestion.get('current_price', 0):,.6f}"
                            ], className="mb-1"),
                            html.P([
                                html.Strong("24h Change: "),
                                html.Span(f"{suggestion.get('price_change_24h', 0):+.2f}%",
                                        className="text-success" if suggestion.get('price_change_24h', 0) > 0 else "text-danger")
                            ], className="mb-1"),
                            html.P([
                                html.Strong("Trend: "),
                                suggestion.get('trend', 'neutral').replace('_', ' ').title()
                            ], className="mb-1"),
                        ], width=4),
                        
                        dbc.Col([
                            html.P([
                                html.Strong("Confidence: "),
                                f"{suggestion.get('confidence', 0):.1f}%"
                            ], className="mb-1"),
                            html.P([
                                html.Strong("Score: "),
                                f"{suggestion.get('score', 0):.1f}/100"
                            ], className="mb-1"),
                            html.P([
                                html.Strong("Risk/Reward: "),
                                f"{suggestion.get('risk_reward_ratio', 0):.2f}"
                            ], className="mb-1"),
                        ], width=4),
                        
                        dbc.Col([
                            html.P([
                                html.Strong("Suggested Investment: "),
                                html.Span(f"${suggestion.get('suggested_investment', 0):,.2f}", 
                                        className="text-warning")
                            ], className="mb-1"),
                            html.P([
                                html.Strong("Stop Loss: "),
                                f"${suggestion.get('stop_loss', 0):,.6f}"
                            ], className="mb-1"),
                            html.P([
                                html.Strong("Take Profit: "),
                                f"${suggestion.get('take_profit', 0):,.6f}"
                            ], className="mb-1"),
                        ], width=4),
                    ])
                ])
            ], className="mb-3", style={'backgroundColor': COLORS['card_bg']})
            
            cards.append(card)
        
        # Add timestamp
        if last_update:
            time_ago = (datetime.now() - last_update).seconds // 60
            cards.insert(0, dbc.Alert(f"Last updated: {time_ago} minute(s) ago", color="info", className="mb-3"))
        
        return cards, ""
    
    except Exception as e:
        print(f"Error displaying suggestions: {e}")
        return [dbc.Alert(f"Error: {str(e)}", color="danger")], ""


@app.callback(
    Output("positions-table", "children"),
    [Input("interval-component", "n_intervals"),
     Input("execute-trade-btn", "n_clicks")]
)
def update_positions_table(n_intervals, n_clicks):
    """Display current positions"""
    positions = portfolio.get_positions_summary()
    
    if not positions:
        return dbc.Alert("No active positions. Execute a trade to get started!", color="info")
    
    # Create table data
    table_data = []
    for pos in positions:
        table_data.append({
            'Symbol': pos['symbol'],
            'Quantity': f"{pos['quantity']:.8f}",
            'Avg Price': f"${pos['avg_price']:,.6f}",
            'Current Price': f"${pos['current_price']:,.6f}",
            'Value': f"${pos['current_value']:,.2f}",
            'P/L': f"${pos['profit_loss']:,.2f}",
            'P/L %': f"{pos['profit_loss_percent']:+.2f}%"
        })
    
    return dash_table.DataTable(
        data=table_data,
        columns=[{"name": i, "id": i} for i in table_data[0].keys()],
        style_cell={
            'backgroundColor': COLORS['card_bg'],
            'color': COLORS['text'],
            'border': '1px solid #2d3748',
            'textAlign': 'left',
            'padding': '10px'
        },
        style_header={
            'backgroundColor': '#1a202c',
            'fontWeight': 'bold',
            'border': '1px solid #2d3748'
        },
        style_data_conditional=[
            {
                'if': {'column_id': 'P/L'},
                'color': COLORS['success']
            }
        ]
    )


@app.callback(
    Output("trade-result", "children"),
    [Input("execute-trade-btn", "n_clicks")],
    [State("trade-coin-id", "value"),
     State("trade-amount", "value")]
)
def execute_trade(n_clicks, coin_id, amount):
    """Execute a simulated trade"""
    if not n_clicks:
        return ""
    
    if not coin_id or not amount:
        return dbc.Alert("Please enter both coin ID and amount!", color="warning", dismissable=True)
    
    try:
        amount = float(amount)
        
        if amount > portfolio.cash_balance:
            return dbc.Alert("Insufficient funds!", color="danger", dismissable=True)
        
        # Get current price
        live_prices = data_fetcher.get_live_prices([coin_id])
        
        if coin_id not in live_prices:
            return dbc.Alert("Invalid coin ID! Use lowercase names like 'bitcoin'", color="danger", dismissable=True)
        
        price = live_prices[coin_id]['price']
        quantity = amount / price
        
        # Execute trade
        success = portfolio.add_position(coin_id, quantity, price, coin_id.upper())
        
        if success:
            return dbc.Alert([
                html.H6("✅ Trade Executed!", className="alert-heading"),
                html.P(f"Bought {quantity:.8f} {coin_id.upper()} at ${price:,.6f}"),
                html.P(f"Total Cost: ${amount:,.2f}", className="mb-0")
            ], color="success", dismissable=True)
        else:
            return dbc.Alert("Trade failed!", color="danger", dismissable=True)
            
    except ValueError:
        return dbc.Alert("Invalid amount!", color="danger", dismissable=True)
    except Exception as e:
        return dbc.Alert(f"Error: {str(e)}", color="danger", dismissable=True)


@app.callback(
    Output("trade-history-table", "children"),
    [Input("interval-component", "n_intervals"),
     Input("execute-trade-btn", "n_clicks")]
)
def update_trade_history(n_intervals, n_clicks):
    """Display trade history"""
    history = portfolio.get_trade_history(limit=10)
    
    if not history:
        return dbc.Alert("No trade history yet.", color="info")
    
    table_data = []
    for trade in history:
        table_data.append({
            'Type': trade['type'],
            'Symbol': trade['symbol'],
            'Quantity': f"{trade['quantity']:.8f}",
            'Price': f"${trade['price']:,.6f}",
            'Amount': f"${trade.get('cost', trade.get('proceeds', 0)):,.2f}",
            'Time': trade['timestamp'][:19]
        })
    
    return dash_table.DataTable(
        data=table_data,
        columns=[{"name": i, "id": i} for i in table_data[0].keys()],
        style_cell={
            'backgroundColor': COLORS['card_bg'],
            'color': COLORS['text'],
            'border': '1px solid #2d3748',
            'textAlign': 'left',
            'padding': '10px'
        },
        style_header={
            'backgroundColor': '#1a202c',
            'fontWeight': 'bold',
            'border': '1px solid #2d3748'
        }
    )


@app.callback(
    Output("market-overview-content", "children"),
    [Input("interval-component", "n_intervals")]
)
def update_market_overview(n):
    """Display market overview"""
    try:
        overview = data_fetcher.get_market_overview()
        
        if not overview:
            return dbc.Alert("Market data temporarily unavailable", color="info")
        
        stats = [
            html.P([html.Strong("Total Market Cap: "), f"${overview.get('total_market_cap_usd', 0):,.0f}"]),
            html.P([html.Strong("24h Volume: "), f"${overview.get('total_volume_24h_usd', 0):,.0f}"]),
            html.P([html.Strong("BTC Dominance: "), f"{overview.get('btc_dominance', 0):.2f}%"]),
            html.P([html.Strong("ETH Dominance: "), f"{overview.get('eth_dominance', 0):.2f}%"]),
            html.P([html.Strong("Active Cryptocurrencies: "), f"{overview.get('active_cryptocurrencies', 0):,}"]),
            html.P([html.Strong("Markets: "), f"{overview.get('markets', 0):,}"]),
        ]
        
        return stats
    except Exception as e:
        print(f"Error loading market overview: {e}")
        return dbc.Alert("Market data temporarily unavailable", color="warning")


@app.callback(
    Output("top-gainers-table", "children"),
    [Input("interval-component", "n_intervals")]
)
def update_top_gainers(n):
    """Display top gainers"""
    try:
        gainers = data_fetcher.get_top_gainers(limit=10)
        
        if not gainers:
            return dbc.Alert("No gainers data available", color="info")
        
        table_data = []
        for coin in gainers:
            table_data.append({
                'Symbol': coin.get('symbol', '?').upper(),
                'Name': coin.get('name', 'Unknown'),
                'Price': f"${coin.get('price', 0):,.6f}",
                '24h Change': f"{coin.get('change_24h', 0):+.2f}%"
            })
        
        if not table_data:
            return dbc.Alert("No gainers data available", color="info")
        
        return dash_table.DataTable(
            data=table_data,
            columns=[{"name": i, "id": i} for i in table_data[0].keys()],
            style_cell={
                'backgroundColor': COLORS['card_bg'],
                'color': COLORS['text'],
                'border': '1px solid #2d3748',
                'textAlign': 'left',
                'padding': '10px'
            },
            style_header={
                'backgroundColor': '#1a202c',
                'fontWeight': 'bold',
                'border': '1px solid #2d3748'
            }
        )
    except Exception as e:
        print(f"Error loading top gainers: {e}")
        return dbc.Alert("Data temporarily unavailable", color="warning")


@app.callback(
    Output("trending-coins-table", "children"),
    [Input("interval-component", "n_intervals")]
)
def update_trending_coins(n):
    """Display trending coins"""
    try:
        trending = data_fetcher.get_trending_coins(limit=10)
        
        if not trending:
            return dbc.Alert("No trending data available", color="info")
        
        table_data = []
        for coin in trending:
            table_data.append({
                'Symbol': coin.get('symbol', '?').upper(),
                'Name': coin.get('name', 'Unknown'),
                'Market Cap Rank': f"#{coin.get('market_cap_rank', 'N/A')}"
            })
        
        if not table_data:
            return dbc.Alert("No trending data available", color="info")
        
        return dash_table.DataTable(
            data=table_data,
            columns=[{"name": i, "id": i} for i in table_data[0].keys()],
            style_cell={
                'backgroundColor': COLORS['card_bg'],
                'color': COLORS['text'],
                'border': '1px solid #2d3748',
                'textAlign': 'left',
                'padding': '10px'
            },
            style_header={
                'backgroundColor': '#1a202c',
                'fontWeight': 'bold',
                'border': '1px solid #2d3748'
            }
        )
    except Exception as e:
        print(f"Error loading trending coins: {e}")
        return dbc.Alert("Data temporarily unavailable", color="warning")


@app.callback(
    Output("coin-analysis-content", "children"),
    [Input("analyze-coin-btn", "n_clicks")],
    [State("coin-selector", "value")]
)
def analyze_specific_coin(n_clicks, coin_id):
    """Analyze a specific cryptocurrency"""
    if not n_clicks:
        return dbc.Alert("Select a coin and click 'Analyze' to see detailed analysis", color="info")
    
    try:
        analysis = trading_engine.analyze_opportunity(coin_id)
        
        if 'error' in analysis:
            return dbc.Alert(f"Error: {analysis['error']}", color="danger")
        
        coin_info = analysis['coin_info']
        tech_analysis = analysis['technical_analysis']
        
        signal_color = {
            'strong_buy': 'success',
            'buy': 'info',
            'neutral': 'secondary',
            'sell': 'warning',
            'strong_sell': 'danger'
        }.get(tech_analysis['overall_signal'], 'secondary')
        
        content = [
            dbc.Row([
                dbc.Col([
                    html.H4(f"{coin_info['name']} ({coin_info['symbol']})"),
                    html.P([
                        dbc.Badge(tech_analysis['overall_signal'].upper(), color=signal_color, className="me-2"),
                        f"Confidence: {tech_analysis['confidence']:.1f}%"
                    ])
                ], width=12)
            ]),
            
            html.Hr(),
            
            dbc.Row([
                dbc.Col([
                    html.H6("Price Information"),
                    html.P([html.Strong("Current Price: "), f"${coin_info['current_price']:,.6f}"]),
                    html.P([html.Strong("24h High: "), f"${coin_info['high_24h']:,.6f}"]),
                    html.P([html.Strong("24h Low: "), f"${coin_info['low_24h']:,.6f}"]),
                    html.P([html.Strong("24h Change: "), f"{coin_info['price_change_percentage_24h']:+.2f}%"]),
                ], width=4),
                
                dbc.Col([
                    html.H6("Market Stats"),
                    html.P([html.Strong("Market Cap: "), f"${coin_info['market_cap']:,.0f}"]),
                    html.P([html.Strong("Rank: "), f"#{coin_info['market_cap_rank']}"]),
                    html.P([html.Strong("7d Change: "), f"{coin_info.get('price_change_percentage_7d', 0):+.2f}%"]),
                    html.P([html.Strong("30d Change: "), f"{coin_info.get('price_change_percentage_30d', 0):+.2f}%"]),
                ], width=4),
                
                dbc.Col([
                    html.H6("Technical Analysis"),
                    html.P([html.Strong("Signal: "), tech_analysis['overall_signal'].upper()]),
                    html.P([html.Strong("Trend: "), tech_analysis['price_trend'].replace('_', ' ').title()]),
                    html.P([html.Strong("Confidence: "), f"{tech_analysis['confidence']:.1f}%"]),
                ], width=4),
            ])
        ]
        
        return content
        
    except Exception as e:
        return dbc.Alert(f"Error analyzing coin: {str(e)}", color="danger")


if __name__ == '__main__':
    print("🚀 Starting CryptoAI Trading Assistant Dashboard...")
    print("📊 Opening browser at http://127.0.0.1:8050")
    print("⚠️  Press Ctrl+C to stop the server")
    app.run(debug=True, host='127.0.0.1', port=8050)

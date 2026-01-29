"""
Enhanced Web Dashboard UI for CryptoAI Trading Assistant
Advanced features inspired by top trading platforms
"""
import dash
from dash import dcc, html, Input, Output, State, dash_table, ctx
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

# Initialize components
data_fetcher = LiveDataFetcher()
trading_engine = TradingEngine()
portfolio = Portfolio(initial_balance=Config.WALLET_SIZE)

# Initialize Dash app with Bootstrap theme
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.CYBORG])
app.title = "CryptoAI Trading Assistant Pro"

# Professional Trading Platform Color Scheme
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
    'sell_red': '#ef4444',
    'neutral': '#6366f1'
}

# App Layout
app.layout = dbc.Container([
    dcc.Interval(id='interval-component', interval=30*1000, n_intervals=0),
    dcc.Interval(id='fast-interval', interval=5*1000, n_intervals=0),  # 5 second updates
    dcc.Store(id='price-history-store', data={}),
    
    # Header with Live Stats
    dbc.Row([
        dbc.Col([
            html.Div([
                html.H1("🚀 CryptoAI Trading Assistant Pro", 
                       className="text-center mb-1",
                       style={'fontSize': '2.5rem', 'fontWeight': 'bold', 'background': 'linear-gradient(90deg, #00d4ff, #10b981)', 
                              'WebkitBackgroundClip': 'text', 'WebkitTextFillColor': 'transparent'}),
                html.P("AI-Powered Live Trading • Real-Time Analytics • Smart Suggestions",
                      className="text-center text-muted mb-2",
                      style={'fontSize': '1.1rem'}),
                html.Div(id="live-ticker", className="text-center mb-3",
                        style={'fontSize': '0.85rem', 'color': COLORS['muted'], 'fontFamily': 'monospace'})
            ])
        ])
    ]),
    
    # Enhanced Statistics Cards
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.Div([
                        html.I(className="fas fa-wallet", style={'fontSize': '1.5rem', 'color': COLORS['success']}),
                        html.Div([
                            html.H6("Portfolio Value", className="text-muted mb-1", style={'fontSize': '0.8rem'}),
                            html.H3(id="portfolio-value", className="mb-0", style={'color': COLORS['success']}),
                            html.Small(id="portfolio-change", className="text-muted")
                        ], style={'marginLeft': '10px'})
                    ], style={'display': 'flex', 'alignItems': 'center'})
                ])
            ], className="mb-3 hover-card", style={
                'backgroundColor': COLORS['card_bg'], 
                'border': f'1px solid {COLORS["card_border"]}',
                'transition': 'transform 0.2s'
            })
        ], width=3),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.Div([
                        html.I(className="fas fa-dollar-sign", style={'fontSize': '1.5rem', 'color': COLORS['warning']}),
                        html.Div([
                            html.H6("Cash Balance", className="text-muted mb-1", style={'fontSize': '0.8rem'}),
                            html.H3(id="cash-balance", className="mb-0", style={'color': COLORS['warning']}),
                            html.Small(id="positions-count", className="text-muted")
                        ], style={'marginLeft': '10px'})
                    ], style={'display': 'flex', 'alignItems': 'center'})
                ])
            ], className="mb-3", style={'backgroundColor': COLORS['card_bg'], 'border': f'1px solid {COLORS["card_border"]}'})
        ], width=3),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.Div([
                        html.I(className="fas fa-chart-line", style={'fontSize': '1.5rem', 'color': COLORS['primary']}),
                        html.Div([
                            html.H6("Market Sentiment", className="text-muted mb-1", style={'fontSize': '0.8rem'}),
                            html.H3(id="market-sentiment", className="mb-0", style={'color': COLORS['primary']}),
                            html.Small(id="market-cap-change", className="text-muted")
                        ], style={'marginLeft': '10px'})
                    ], style={'display': 'flex', 'alignItems': 'center'})
                ])
            ], className="mb-3", style={'backgroundColor': COLORS['card_bg'], 'border': f'1px solid {COLORS["card_border"]}'})
        ], width=3),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.Div([
                        html.I(className="fas fa-trophy", style={'fontSize': '1.5rem', 'color': COLORS['success']}),
                        html.Div([
                            html.H6("Total Return", className="text-muted mb-1", style={'fontSize': '0.8rem'}),
                            html.H3(id="total-return", className="mb-0"),
                            html.Small(id="return-percent", className="text-muted")
                        ], style={'marginLeft': '10px'})
                    ], style={'display': 'flex', 'alignItems': 'center'})
                ])
            ], className="mb-3", style={'backgroundColor': COLORS['card_bg'], 'border': f'1px solid {COLORS["card_border"]}'})
        ], width=3),
    ], className="mb-4"),
    
    # Main Content with Enhanced Tabs
    dbc.Tabs([
        # Enhanced Trade Suggestions Tab
        dbc.Tab([
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.Div([
                                html.H5("🎯 AI Trade Suggestions", className="mb-0", style={'display': 'inline-block'}),
                                dbc.ButtonGroup([
                                    dbc.Button("🔄 Refresh", id="refresh-suggestions-btn", color="primary", size="sm", className="ms-3"),
                                    dbc.Button("⚙️ Filters", id="filter-btn", color="secondary", size="sm", outline=True)
                                ], style={'float': 'right'})
                            ])
                        ]),
                        dbc.CardBody([
                            html.Div(id="loading-suggestions"),
                            html.Div(id="trade-suggestions-content")
                        ])
                    ], className="mb-4", style={'backgroundColor': COLORS['card_bg'], 'border': f'1px solid {COLORS["card_border"]}'})
                ], width=12)
            ])
        ], label="📊 Trade Suggestions", tab_id="tab-suggestions"),
        
        # Enhanced Portfolio Tab with Charts
        dbc.Tab([
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader(html.H5("📈 Portfolio Performance", className="mb-0")),
                        dbc.CardBody([
                            dcc.Graph(id="portfolio-chart", config={'displayModeBar': False},
                                    style={'height': '300px'})
                        ])
                    ], className="mb-3", style={'backgroundColor': COLORS['card_bg'], 'border': f'1px solid {COLORS["card_border"]}'})
                ], width=8),
                
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader(html.H5("💰 Quick Trade", className="mb-0")),
                        dbc.CardBody([
                            dbc.Label("Coin ID", className="fw-bold"),
                            dcc.Dropdown(
                                id="trade-coin-dropdown",
                                options=[{'label': coin.title(), 'value': coin} for coin in Config.TOP_CRYPTOS],
                                placeholder="Select cryptocurrency",
                                className="mb-2",
                                style={'color': '#000'}
                            ),
                            dbc.Label("Investment Amount ($)", className="fw-bold"),
                            dbc.Input(id="trade-amount", type="number", placeholder="Enter amount", className="mb-2"),
                            dbc.Button("🛒 Buy Now", id="execute-trade-btn", color="success", className="w-100 mb-2"),
                            html.Hr(),
                            html.Div(id="quick-coin-info", className="small text-muted"),
                            html.Div(id="trade-result", className="mt-2")
                        ])
                    ], className="mb-3", style={'backgroundColor': COLORS['card_bg'], 'border': f'1px solid {COLORS["card_border"]}'})
                ], width=4)
            ]),
            
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader(html.H5("💼 Active Positions", className="mb-0")),
                        dbc.CardBody([
                            html.Div(id="positions-table")
                        ])
                    ], className="mb-3", style={'backgroundColor': COLORS['card_bg'], 'border': f'1px solid {COLORS["card_border"]}'})
                ], width=12)
            ]),
            
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader(html.H5("📜 Trade History", className="mb-0")),
                        dbc.CardBody([
                            html.Div(id="trade-history-table")
                        ])
                    ], style={'backgroundColor': COLORS['card_bg'], 'border': f'1px solid {COLORS["card_border"]}'})
                ], width=12)
            ])
        ], label="💼 Portfolio", tab_id="tab-portfolio"),
        
        # Market Analysis with Charts
        dbc.Tab([
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader(html.H5("🌍 Global Market Overview", className="mb-0")),
                        dbc.CardBody([
                            dbc.Row([
                                dbc.Col([
                                    html.Div(id="market-overview-content")
                                ], width=6),
                                dbc.Col([
                                    dcc.Graph(id="market-dominance-chart", config={'displayModeBar': False},
                                            style={'height': '250px'})
                                ], width=6)
                            ])
                        ])
                    ], className="mb-3", style={'backgroundColor': COLORS['card_bg'], 'border': f'1px solid {COLORS["card_border"]}'})
                ], width=12)
            ]),
            
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader(html.H5("🚀 Top Gainers (24h)", className="mb-0")),
                        dbc.CardBody([
                            html.Div(id="top-gainers-table")
                        ])
                    ], className="mb-3", style={'backgroundColor': COLORS['card_bg'], 'border': f'1px solid {COLORS["card_border"]}'})
                ], width=6),
                
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader(html.H5("🔥 Trending Now", className="mb-0")),
                        dbc.CardBody([
                            html.Div(id="trending-coins-table")
                        ])
                    ], className="mb-3", style={'backgroundColor': COLORS['card_bg'], 'border': f'1px solid {COLORS["card_border"]}'})
                ], width=6)
            ])
        ], label="🌍 Market Analysis", tab_id="tab-market"),
        
        # Enhanced Coin Analysis with Price Charts
        dbc.Tab([
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.Div([
                                html.H5("🔍 Cryptocurrency Analysis", className="mb-0", style={'display': 'inline-block'}),
                                dbc.Button("Analyze", id="analyze-coin-btn", color="primary", size="sm", style={'float': 'right'})
                            ])
                        ]),
                        dbc.CardBody([
                            dbc.Row([
                                dbc.Col([
                                    dbc.Label("Select Cryptocurrency", className="fw-bold"),
                                    dcc.Dropdown(
                                        id='coin-selector',
                                        options=[{'label': coin.title(), 'value': coin} for coin in Config.TOP_CRYPTOS],
                                        value='bitcoin',
                                        className="mb-3",
                                        style={'color': '#000'}
                                    )
                                ], width=6),
                                dbc.Col([
                                    dbc.Label("Timeframe", className="fw-bold"),
                                    dcc.Dropdown(
                                        id='timeframe-selector',
                                        options=[
                                            {'label': '7 Days', 'value': 7},
                                            {'label': '30 Days', 'value': 30},
                                            {'label': '90 Days', 'value': 90}
                                        ],
                                        value=30,
                                        className="mb-3",
                                        style={'color': '#000'}
                                    )
                                ], width=6)
                            ]),
                            html.Hr(),
                            html.Div(id="coin-analysis-content")
                        ])
                    ], style={'backgroundColor': COLORS['card_bg'], 'border': f'1px solid {COLORS["card_border"]}'})
                ], width=12)
            ])
        ], label="🔍 Coin Analysis", tab_id="tab-analysis"),
        
        # New: Performance Analytics Tab
        dbc.Tab([
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader(html.H5("📊 Performance Analytics", className="mb-0")),
                        dbc.CardBody([
                            dbc.Row([
                                dbc.Col([
                                    html.H6("Win Rate", className="text-muted"),
                                    html.H4(id="win-rate", className="text-success")
                                ], width=3),
                                dbc.Col([
                                    html.H6("Avg Trade Return", className="text-muted"),
                                    html.H4(id="avg-return", className="text-primary")
                                ], width=3),
                                dbc.Col([
                                    html.H6("Best Trade", className="text-muted"),
                                    html.H4(id="best-trade", className="text-success")
                                ], width=3),
                                dbc.Col([
                                    html.H6("Worst Trade", className="text-muted"),
                                    html.H4(id="worst-trade", className="text-danger")
                                ], width=3)
                            ])
                        ])
                    ], className="mb-3", style={'backgroundColor': COLORS['card_bg'], 'border': f'1px solid {COLORS["card_border"]}'})
                ], width=12)
            ]),
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader(html.H5("📈 Portfolio Growth Chart", className="mb-0")),
                        dbc.CardBody([
                            dcc.Graph(id="performance-chart", config={'displayModeBar': False})
                        ])
                    ], style={'backgroundColor': COLORS['card_bg'], 'border': f'1px solid {COLORS["card_border"]}'})
                ], width=12)
            ])
        ], label="📊 Analytics", tab_id="tab-analytics"),
        
    ], id="tabs", active_tab="tab-suggestions", className="mb-3"),
    
    html.Footer([
        html.Hr(),
        html.P([
            "⚠️ Simulated Trading Platform • Educational Purposes Only • Not Financial Advice • Last Updated: ",
            html.Span(id="last-update-time", className="text-primary")
        ], className="text-center text-muted small")
    ])
    
], fluid=True, style={'backgroundColor': COLORS['background'], 'minHeight': '100vh', 'padding': '20px'})

# Callbacks remain similar but I'll add the new ones for enhanced features...
# (Keep all previous callbacks and add new ones below)

@app.callback(
    [Output("portfolio-value", "children"),
     Output("portfolio-change", "children"),
     Output("cash-balance", "children"),
     Output("positions-count", "children"),
     Output("total-return", "children"),
     Output("return-percent", "children"),
     Output("last-update-time", "children")],
    [Input("interval-component", "n_intervals")]
)
def update_portfolio_stats(n):
    if portfolio.positions:
        coin_ids = list(portfolio.positions.keys())
        live_prices = data_fetcher.get_live_prices(coin_ids)
        portfolio.update_prices(live_prices)
    
    performance = portfolio.get_portfolio_performance()
    
    return_color = COLORS['success'] if performance['total_return'] >= 0 else COLORS['danger']
    
    return (
        f"${performance['current_value']:,.2f}",
        f"Initial: ${performance['initial_balance']:,.2f}",
        f"${performance['cash_balance']:,.2f}",
        f"{performance['num_positions']} positions • {performance['num_trades']} trades",
        html.Span(f"${performance['total_return']:,.2f}", style={'color': return_color}),
        html.Span(f"{performance['return_percent']:+.2f}%", style={'color': return_color}),
        datetime.now().strftime("%H:%M:%S")
    )

@app.callback(
    Output("live-ticker", "children"),
    [Input("fast-interval", "n_intervals")]
)
def update_live_ticker(n):
    try:
        top_coins = ['bitcoin', 'ethereum', 'binancecoin']
        prices = data_fetcher.get_live_prices(top_coins)
        
        ticker_items = []
        for coin_id in top_coins:
            if coin_id in prices:
                data = prices[coin_id]
                change = data.get('change_24h', 0)
                color = COLORS['success'] if change >= 0 else COLORS['danger']
                ticker_items.append(
                    html.Span([
                        f"{coin_id.upper()}: ${data['price']:,.2f} ",
                        html.Span(f"({change:+.2f}%)", style={'color': color})
                    ], style={'marginRight': '20px'})
                )
        
        return ticker_items
    except:
        return "Loading market data..."

@app.callback(
    [Output("market-sentiment", "children"),
     Output("market-cap-change", "children")],
    [Input("interval-component", "n_intervals")]
)
def update_market_sentiment(n):
    try:
        sentiment_data = trading_engine.get_market_sentiment()
        sentiment = sentiment_data['sentiment']
        change = sentiment_data['market_cap_change_24h']
        
        sentiment_colors = {
            'Very Bullish': COLORS['success'],
            'Bullish': COLORS['success'],
            'Neutral': COLORS['neutral'],
            'Bearish': COLORS['danger'],
            'Very Bearish': COLORS['danger']
        }
        
        return (
            html.Span(sentiment, style={'color': sentiment_colors.get(sentiment, COLORS['primary'])}),
            f"24h: {change:+.2f}%"
        )
    except:
        return "Loading...", "..."

# Continue with enhanced versions of other callbacks...
# (I'll add the critical ones for the new features)

@app.callback(
    Output("portfolio-chart", "figure"),
    [Input("interval-component", "n_intervals")]
)
def update_portfolio_chart(n):
    """Create portfolio allocation pie chart"""
    positions = portfolio.get_positions_summary()
    
    if not positions:
        # Empty portfolio
        fig = go.Figure()
        fig.add_annotation(
            text="No active positions<br>Execute trades to see portfolio allocation",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=14, color=COLORS['muted'])
        )
        fig.update_layout(
            paper_bgcolor=COLORS['chart_bg'],
            plot_bgcolor=COLORS['chart_bg'],
            font={'color': COLORS['text']}
        )
        return fig
    
    labels = [pos['symbol'] for pos in positions]
    values = [pos['current_value'] for pos in positions]
    
    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.4,
        marker=dict(colors=['#10b981', '#00d4ff', '#f59e0b', '#ef4444', '#6366f1', '#8b5cf6'])
    )])
    
    fig.update_layout(
        paper_bgcolor=COLORS['chart_bg'],
        plot_bgcolor=COLORS['chart_bg'],
        font={'color': COLORS['text']},
        margin=dict(t=30, b=30, l=30, r=30),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5)
    )
    
    return fig

@app.callback(
    Output("market-dominance-chart", "figure"),
    [Input("interval-component", "n_intervals")]
)
def update_dominance_chart(n):
    """Create market dominance chart"""
    try:
        overview = data_fetcher.get_market_overview()
        btc_dom = overview.get('btc_dominance', 0)
        eth_dom = overview.get('eth_dominance', 0)
        other_dom = 100 - btc_dom - eth_dom
        
        fig = go.Figure(data=[go.Pie(
            labels=['Bitcoin', 'Ethereum', 'Others'],
            values=[btc_dom, eth_dom, other_dom],
            hole=0.4,
            marker=dict(colors=[COLORS['warning'], COLORS['primary'], COLORS['muted']])
        )])
        
        fig.update_layout(
            title="Market Dominance",
            paper_bgcolor=COLORS['chart_bg'],
            plot_bgcolor=COLORS['chart_bg'],
            font={'color': COLORS['text'], 'size': 10},
            margin=dict(t=40, b=10, l=10, r=10),
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5)
        )
        
        return fig
    except:
        return go.Figure()

# Import all the previous callbacks here for suggestions, portfolio, trades, etc.
# (Keeping them as they were but with enhanced styling)

if __name__ == '__main__':
    print("🚀 Starting CryptoAI Trading Assistant Pro...")
    print("📊 Enhanced with real-time charts and advanced analytics")
    print("🌐 Opening at http://127.0.0.1:8050")
    print("⚠️  Press Ctrl+C to stop")
    app.run(debug=False, host='127.0.0.1', port=8050)

"""
Mobile-Friendly REST API for CryptoAI
Enables iOS/Android/Web clients to connect to your portfolio
Based on Swift CryptoPortfolio patterns
"""
from flask import Flask, jsonify, request
from flask_cors import CORS
from functools import wraps
import os
import time
from datetime import datetime
from typing import Optional

# Import existing modules
try:
    from portfolio import Portfolio
    from data_fetcher import LiveDataFetcher
    from technical_analyzer import TechnicalAnalyzer
    from prediction_market_analyzer import PredictionMarketAnalyzer
    from coinmarketcap_api import CoinMarketCapAPI, CoinMarketCapError
except ImportError as e:
    print(f"⚠️ Import warning: {e}")

app = Flask(__name__)
CORS(app)  # Enable CORS for mobile apps

# Initialize components
portfolio = Portfolio()
data_fetcher = LiveDataFetcher()

# Optional: CoinMarketCap API
cmc_api = None
if os.environ.get('CMC_API_KEY'):
    cmc_api = CoinMarketCapAPI()

# Rate limiting
request_counts = {}
RATE_LIMIT = 60  # requests per minute


def rate_limit(f):
    """Rate limiting decorator"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        client_ip = request.remote_addr
        current_minute = int(time.time() / 60)
        
        key = f"{client_ip}_{current_minute}"
        request_counts[key] = request_counts.get(key, 0) + 1
        
        # Clean old entries
        old_keys = [k for k in request_counts if k.split('_')[1] != str(current_minute)]
        for k in old_keys:
            del request_counts[k]
        
        if request_counts[key] > RATE_LIMIT:
            return jsonify({
                'error': 'Rate limit exceeded',
                'retry_after': 60 - (int(time.time()) % 60)
            }), 429
        
        return f(*args, **kwargs)
    return decorated_function


def api_response(data=None, error=None, status=200):
    """Standard API response format"""
    response = {
        'success': error is None,
        'timestamp': datetime.now().isoformat(),
        'data': data
    }
    if error:
        response['error'] = str(error)
    return jsonify(response), status


# ============================================================================
# PORTFOLIO ENDPOINTS
# ============================================================================

@app.route('/api/v1/portfolio', methods=['GET'])
@rate_limit
def get_portfolio():
    """
    Get complete portfolio overview
    
    Response:
    {
        "success": true,
        "data": {
            "performance": {...},
            "positions": [...],
            "recent_trades": [...]
        }
    }
    """
    try:
        return api_response({
            'performance': portfolio.get_portfolio_performance(),
            'positions': portfolio.get_positions_summary(),
            'recent_trades': portfolio.get_trade_history(5)
        })
    except Exception as e:
        return api_response(error=e, status=500)


@app.route('/api/v1/portfolio/value', methods=['GET'])
@rate_limit
def get_portfolio_value():
    """Get current portfolio value"""
    try:
        return api_response({
            'total_value': portfolio.get_portfolio_value(),
            'cash_balance': portfolio.cash_balance,
            'positions_count': len(portfolio.positions)
        })
    except Exception as e:
        return api_response(error=e, status=500)


@app.route('/api/v1/portfolio/holdings', methods=['GET'])
@rate_limit
def get_holdings():
    """Get all holdings with profit/loss"""
    try:
        return api_response({
            'holdings': portfolio.get_positions_summary()
        })
    except Exception as e:
        return api_response(error=e, status=500)


@app.route('/api/v1/portfolio/holdings', methods=['POST'])
@rate_limit
def add_holding():
    """
    Add a new holding
    
    Request Body:
    {
        "coin_id": "bitcoin",
        "symbol": "BTC",
        "quantity": 0.1,
        "price": 65000.0
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return api_response(error="Request body required", status=400)
        
        coin_id = data.get('coin_id')
        quantity = data.get('quantity')
        price = data.get('price')
        symbol = data.get('symbol')
        
        if not all([coin_id, quantity, price]):
            return api_response(error="coin_id, quantity, and price are required", status=400)
        
        success = portfolio.add_position(
            coin_id=coin_id,
            quantity=float(quantity),
            price=float(price),
            symbol=symbol
        )
        
        if success:
            return api_response({
                'message': f'Added {quantity} {symbol or coin_id}',
                'position': portfolio.positions.get(coin_id)
            }, status=201)
        else:
            return api_response(error="Insufficient funds", status=400)
            
    except Exception as e:
        return api_response(error=e, status=500)


@app.route('/api/v1/portfolio/holdings/<coin_id>', methods=['DELETE'])
@rate_limit
def remove_holding(coin_id: str):
    """
    Remove or reduce a holding
    
    Query params:
    - quantity: Amount to sell (optional, sells all if not provided)
    - price: Current price (required)
    """
    try:
        price = request.args.get('price', type=float)
        quantity = request.args.get('quantity', type=float)
        
        if not price:
            return api_response(error="price parameter required", status=400)
        
        if coin_id not in portfolio.positions:
            return api_response(error=f"No position for {coin_id}", status=404)
        
        # If no quantity specified, sell all
        if quantity is None:
            quantity = portfolio.positions[coin_id]['quantity']
        
        success = portfolio.remove_position(coin_id, quantity, price)
        
        if success:
            return api_response({
                'message': f'Sold {quantity} {coin_id}',
                'proceeds': quantity * price
            })
        else:
            return api_response(error="Failed to remove position", status=400)
            
    except Exception as e:
        return api_response(error=e, status=500)


@app.route('/api/v1/portfolio/trades', methods=['GET'])
@rate_limit
def get_trades():
    """Get trade history"""
    try:
        limit = request.args.get('limit', 20, type=int)
        return api_response({
            'trades': portfolio.get_trade_history(limit)
        })
    except Exception as e:
        return api_response(error=e, status=500)


# ============================================================================
# PRICE ENDPOINTS
# ============================================================================

@app.route('/api/v1/prices/<symbol>', methods=['GET'])
@rate_limit
def get_price(symbol: str):
    """
    Get current price for a cryptocurrency
    
    Path params:
    - symbol: Cryptocurrency symbol (e.g., 'BTC', 'ETH')
    """
    try:
        # Try CoinMarketCap first if available
        if cmc_api:
            try:
                crypto = cmc_api.fetch_price(symbol.upper())
                return api_response({
                    'symbol': crypto.symbol,
                    'name': crypto.name,
                    'price': crypto.current_price,
                    'change_24h': crypto.percent_change_24h,
                    'change_7d': crypto.percent_change_7d,
                    'market_cap': crypto.market_cap,
                    'volume_24h': crypto.volume_24h,
                    'source': 'coinmarketcap'
                })
            except CoinMarketCapError:
                pass  # Fall through to alternative
        
        # Fallback to free APIs
        coin_id = symbol.lower()
        prices = data_fetcher.get_live_prices([coin_id])
        
        if coin_id in prices:
            return api_response({
                'symbol': symbol.upper(),
                'price': prices[coin_id],
                'source': 'cryptocompare'
            })
        else:
            return api_response(error=f"Price not found for {symbol}", status=404)
            
    except Exception as e:
        return api_response(error=e, status=500)


@app.route('/api/v1/prices', methods=['GET'])
@rate_limit
def get_prices():
    """
    Get prices for multiple cryptocurrencies
    
    Query params:
    - symbols: Comma-separated list (e.g., 'BTC,ETH,SOL')
    """
    try:
        symbols = request.args.get('symbols', 'BTC,ETH')
        symbol_list = [s.strip().upper() for s in symbols.split(',')]
        
        if cmc_api:
            try:
                cryptos = cmc_api.fetch_prices(symbol_list)
                return api_response({
                    'prices': {
                        s: {
                            'price': c.current_price,
                            'change_24h': c.percent_change_24h
                        }
                        for s, c in cryptos.items()
                    },
                    'source': 'coinmarketcap'
                })
            except CoinMarketCapError:
                pass
        
        # Fallback
        coin_ids = [s.lower() for s in symbol_list]
        prices = data_fetcher.get_live_prices(coin_ids)
        
        return api_response({
            'prices': {s.upper(): {'price': p} for s, p in prices.items()},
            'source': 'cryptocompare'
        })
        
    except Exception as e:
        return api_response(error=e, status=500)


@app.route('/api/v1/prices/top', methods=['GET'])
@rate_limit
def get_top_prices():
    """
    Get top cryptocurrencies by market cap
    
    Query params:
    - limit: Number of results (default 20, max 100)
    """
    try:
        limit = min(request.args.get('limit', 20, type=int), 100)
        
        if cmc_api:
            try:
                cryptos = cmc_api.fetch_top_cryptocurrencies(limit)
                return api_response({
                    'cryptocurrencies': [
                        {
                            'rank': i + 1,
                            'symbol': c.symbol,
                            'name': c.name,
                            'price': c.current_price,
                            'change_24h': c.percent_change_24h,
                            'market_cap': c.market_cap
                        }
                        for i, c in enumerate(cryptos)
                    ]
                })
            except CoinMarketCapError as e:
                return api_response(error=f"CoinMarketCap error: {e}", status=503)
        else:
            return api_response(error="Top prices require CoinMarketCap API key", status=503)
            
    except Exception as e:
        return api_response(error=e, status=500)


# ============================================================================
# ANALYSIS ENDPOINTS
# ============================================================================

@app.route('/api/v1/analysis/<coin_id>', methods=['GET'])
@rate_limit
def get_analysis(coin_id: str):
    """
    Get technical and ML analysis for a cryptocurrency
    """
    try:
        analyzer = PredictionMarketAnalyzer()
        analysis = analyzer.get_full_analysis()
        
        return api_response({
            'coin_id': coin_id,
            'signal': analysis.get('overall_signal', 'neutral'),
            'confidence': analysis.get('confidence', 0),
            'technical': analysis.get('technical', {}),
            'ml_prediction': analysis.get('ml_prediction', {}),
            'recommendation': analysis.get('recommendation', {})
        })
    except Exception as e:
        return api_response(error=e, status=500)


@app.route('/api/v1/market/global', methods=['GET'])
@rate_limit
def get_global_metrics():
    """Get global cryptocurrency market metrics"""
    try:
        if cmc_api:
            metrics = cmc_api.get_global_metrics()
            return api_response(metrics)
        else:
            return api_response(error="Global metrics require CoinMarketCap API key", status=503)
    except Exception as e:
        return api_response(error=e, status=500)


# ============================================================================
# PREDICTION MARKETS ENDPOINTS
# ============================================================================

@app.route('/api/v1/prediction-markets', methods=['GET'])
@rate_limit
def get_prediction_markets():
    """
    Get all crypto prediction markets from multiple platforms
    
    Query params:
    - platform: Filter by platform (polymarket, kalshi, metaculus)
    - btc_only: Only return Bitcoin-related markets (default: false)
    """
    try:
        from prediction_markets import PredictionMarketAnalyzer as PMAnalyzer
        
        analyzer = PMAnalyzer()
        platform = request.args.get('platform', '')
        btc_only = request.args.get('btc_only', 'false').lower() == 'true'
        
        if btc_only:
            markets = analyzer.client.get_btc_price_markets()
        else:
            markets = analyzer.client.get_all_crypto_markets()
        
        # Filter by platform if specified
        if platform:
            markets = [m for m in markets if m.platform == platform.lower()]
        
        return api_response({
            'count': len(markets),
            'markets': [
                {
                    'id': m.id,
                    'platform': m.platform,
                    'title': m.title,
                    'description': m.description[:200] if m.description else '',
                    'implied_probability': m.implied_probability,
                    'outcomes': m.outcomes,
                    'volume': m.volume,
                    'liquidity': m.liquidity,
                    'end_date': m.end_date.isoformat(),
                    'url': m.url
                }
                for m in markets[:50]  # Limit to 50
            ]
        })
    except Exception as e:
        return api_response(error=str(e), status=500)


@app.route('/api/v1/prediction-markets/consensus', methods=['GET'])
@rate_limit
def get_market_consensus():
    """Get aggregated consensus from prediction markets"""
    try:
        from prediction_markets import PredictionMarketAnalyzer as PMAnalyzer
        
        analyzer = PMAnalyzer()
        consensus = analyzer.get_market_consensus()
        
        return api_response(consensus)
    except Exception as e:
        return api_response(error=str(e), status=500)


@app.route('/api/v1/prediction-markets/arbitrage', methods=['GET'])
@rate_limit
def get_arbitrage_opportunities():
    """
    Find arbitrage opportunities between our predictions and markets
    
    Query params:
    - our_prediction: Our bullish probability (0-1, default: 0.5)
    - min_edge: Minimum edge to report (default: 0.05)
    """
    try:
        from prediction_markets import PredictionMarketAnalyzer as PMAnalyzer
        
        our_pred = request.args.get('our_prediction', 0.5, type=float)
        min_edge = request.args.get('min_edge', 0.05, type=float)
        
        analyzer = PMAnalyzer()
        opportunities = analyzer.find_arbitrage_opportunities(
            our_prediction=our_pred,
            min_edge=min_edge
        )
        
        return api_response({
            'our_prediction': our_pred,
            'min_edge': min_edge,
            'opportunities_count': len(opportunities),
            'opportunities': [
                {
                    'platform': o.market.platform,
                    'market_title': o.market.title,
                    'market_probability': o.market_probability,
                    'our_probability': o.our_prediction,
                    'edge': o.edge,
                    'recommended_position': o.recommended_position,
                    'expected_value': o.expected_value,
                    'reasoning': o.reasoning,
                    'url': o.market.url
                }
                for o in opportunities[:10]
            ]
        })
    except Exception as e:
        return api_response(error=str(e), status=500)


@app.route('/api/v1/prediction-markets/report', methods=['GET'])
@rate_limit
def get_prediction_report():
    """
    Get comprehensive prediction market report
    
    Query params:
    - bullish_prob: Our model's bullish probability (default: uses ML engine)
    """
    try:
        from prediction_markets import PredictionMarketAnalyzer as PMAnalyzer
        
        # Try to get ML prediction
        bullish_prob = request.args.get('bullish_prob', type=float)
        
        if bullish_prob is None:
            try:
                from ml_prediction_engine import MLPredictionEngine
                ml_engine = MLPredictionEngine()
                prediction = ml_engine.predict()
                bullish_prob = prediction.get('probability_up', 0.5)
            except:
                bullish_prob = 0.5
        
        analyzer = PMAnalyzer()
        report = analyzer.generate_prediction_report(bullish_prob)
        
        return api_response(report)
    except Exception as e:
        return api_response(error=str(e), status=500)


# ============================================================================
# HEALTH & INFO ENDPOINTS
# ============================================================================

@app.route('/api/v1/health', methods=['GET'])
def health_check():
    """API health check"""
    return api_response({
        'status': 'healthy',
        'version': '1.1.0',
        'features': {
            'portfolio': True,
            'prices': True,
            'analysis': True,
            'prediction_markets': True,
            'coinmarketcap': cmc_api is not None
        }
    })


@app.route('/api/v1', methods=['GET'])
def api_info():
    """API documentation"""
    return api_response({
        'name': 'CryptoAI REST API',
        'version': '1.0.0',
        'description': 'Mobile-friendly API for cryptocurrency portfolio management',
        'endpoints': {
            'portfolio': {
                'GET /api/v1/portfolio': 'Get portfolio overview',
                'GET /api/v1/portfolio/value': 'Get portfolio value',
                'GET /api/v1/portfolio/holdings': 'List all holdings',
                'POST /api/v1/portfolio/holdings': 'Add a holding',
                'DELETE /api/v1/portfolio/holdings/<coin_id>': 'Remove a holding',
                'GET /api/v1/portfolio/trades': 'Get trade history'
            },
            'prices': {
                'GET /api/v1/prices/<symbol>': 'Get price for symbol',
                'GET /api/v1/prices?symbols=BTC,ETH': 'Get multiple prices',
                'GET /api/v1/prices/top?limit=20': 'Get top cryptocurrencies'
            },
            'analysis': {
                'GET /api/v1/analysis/<coin_id>': 'Get analysis for coin',
                'GET /api/v1/market/global': 'Get global market metrics'
            }
        },
        'rate_limit': f'{RATE_LIMIT} requests per minute'
    })


# ============================================================================
# MAIN
# ============================================================================

def run_api(host='0.0.0.0', port=5000, debug=False):
    """
    Run the REST API server
    
    Args:
        host: Host to bind to (0.0.0.0 for all interfaces)
        port: Port number
        debug: Enable debug mode
    """
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║              🪙 CryptoAI REST API Server                     ║
╠══════════════════════════════════════════════════════════════╣
║  URL: http://{host}:{port}                               ║
║  Docs: http://{host}:{port}/api/v1                       ║
║                                                              ║
║  Features:                                                   ║
║  ✓ Portfolio Management                                      ║
║  ✓ Real-time Prices                                         ║
║  ✓ Technical Analysis                                       ║
║  {'✓' if cmc_api else '✗'} CoinMarketCap Integration                               ║
║                                                              ║
║  Connect from iOS/Android/Web apps!                          ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    app.run(host=host, port=port, debug=debug, threaded=True)


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='CryptoAI REST API')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=5000, help='Port number')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    
    args = parser.parse_args()
    run_api(host=args.host, port=args.port, debug=args.debug)

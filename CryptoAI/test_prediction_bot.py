"""
Test script for Prediction Market Bot
Validates all components are working correctly
"""
import sys
from colorama import Fore, Style, init

init(autoreset=True)

print(f"{Fore.CYAN}{'='*60}")
print(f"{Fore.CYAN}🔮 CryptoAI Prediction Bot - Component Test")
print(f"{Fore.CYAN}{'='*60}\n")

# Track results
results = []

def test_component(name, test_func):
    """Test a component and track results"""
    try:
        print(f"{Fore.YELLOW}Testing {name}...", end=" ")
        result = test_func()
        print(f"{Fore.GREEN}✓ PASS")
        results.append((name, True, result))
        return True
    except Exception as e:
        print(f"{Fore.RED}✗ FAIL")
        print(f"{Fore.RED}  Error: {str(e)[:100]}")
        results.append((name, False, str(e)))
        return False

# Test 1: Core Dependencies
def test_dependencies():
    """Test if all required libraries are installed"""
    deps = {
        'requests': 'HTTP requests',
        'pandas': 'Data processing',
        'numpy': 'Numerical operations',
        'ta': 'Technical analysis',
        'plotly': 'Visualization',
        'dash': 'Dashboard',
    }
    
    missing = []
    for module, desc in deps.items():
        try:
            __import__(module)
        except ImportError:
            missing.append(f"{module} ({desc})")
    
    if missing:
        raise ImportError(f"Missing: {', '.join(missing)}")
    
    return f"{len(deps)} core dependencies"

# Test 2: ML Libraries
def test_ml_libraries():
    """Test if ML libraries are installed"""
    ml_libs = []
    
    try:
        import sklearn
        ml_libs.append('scikit-learn')
    except ImportError:
        pass
    
    try:
        import xgboost
        ml_libs.append('XGBoost')
    except ImportError:
        pass
    
    try:
        import tensorflow
        ml_libs.append('TensorFlow')
    except ImportError:
        pass
    
    if not ml_libs:
        raise ImportError("No ML libraries found. Install: pip install scikit-learn xgboost tensorflow")
    
    return f"Available: {', '.join(ml_libs)}"

# Test 3: Prediction Market Fetcher
def test_market_fetcher():
    """Test market data fetcher"""
    from prediction_market_fetcher import PredictionMarketFetcher
    
    fetcher = PredictionMarketFetcher(cache_timeout=30)
    
    # Test order book fetch
    orderbook = fetcher.get_btc_orderbook(level=2)
    if not orderbook or 'mid_price' not in orderbook:
        raise ValueError("Failed to fetch order book")
    
    mid_price = orderbook['mid_price']
    if mid_price == 0:
        raise ValueError("Invalid price data")
    
    return f"BTC Price: ${mid_price:,.2f}"

# Test 4: ML Prediction Engine
def test_ml_engine():
    """Test ML prediction engine"""
    from ml_prediction_engine import MLPredictionEngine
    import pandas as pd
    from datetime import datetime, timedelta
    
    engine = MLPredictionEngine(lookback_period=60, prediction_horizon=24)
    
    # Create sample data
    dates = pd.date_range(end=datetime.now(), periods=200, freq='1h')
    sample_df = pd.DataFrame({
        'timestamp': dates,
        'price': 50000 + pd.Series(range(200)).cumsum() * 10,
        'volume': pd.Series([1000] * 200),
        'market_cap': pd.Series([1e9] * 200)
    })
    
    # Test feature preparation
    df_prepared = engine.prepare_features(sample_df)
    if df_prepared.empty:
        raise ValueError("Feature preparation failed")
    
    feature_count = len(df_prepared.columns)
    
    return f"{feature_count} features engineered"

# Test 5: Prediction Analyzer
def test_analyzer():
    """Test prediction market analyzer"""
    from prediction_market_analyzer import PredictionMarketAnalyzer
    
    analyzer = PredictionMarketAnalyzer(auto_train=False)
    
    # Test market analysis
    analysis = analyzer.analyze_market()
    
    if 'error' in analysis:
        raise ValueError(f"Analysis failed: {analysis['error']}")
    
    if 'current_price' not in analysis:
        raise ValueError("Missing current price in analysis")
    
    current_price = analysis['current_price']
    signal = analysis.get('overall_signal', {}).get('signal', 'unknown')
    
    return f"Signal: {signal.upper()}, Price: ${current_price:,.2f}"

# Test 6: Trading Bot
def test_trading_bot():
    """Test trading bot initialization"""
    from prediction_trading_bot import PredictionTradingBot
    from portfolio import Portfolio
    
    portfolio = Portfolio()
    bot = PredictionTradingBot(
        portfolio=portfolio,
        risk_level='medium',
        auto_trade=False,
        min_confidence=0.65
    )
    
    status = bot.get_status()
    
    if not status:
        raise ValueError("Failed to get bot status")
    
    portfolio_value = status.get('portfolio_value', 0)
    
    return f"Portfolio: ${portfolio_value:,.2f}"

# Test 7: Dashboard Components
def test_dashboard():
    """Test dashboard components"""
    import dash
    from dash import dcc, html
    import dash_bootstrap_components as dbc
    
    # Test if dashboard can be created
    app = dash.Dash(__name__, external_stylesheets=[dbc.themes.CYBORG])
    
    if not app:
        raise ValueError("Failed to create dashboard app")
    
    return "Dashboard components loaded"

# Test 8: API Connectivity
def test_api_connectivity():
    """Test API connections"""
    import requests
    
    apis = []
    
    # Test CoinGecko
    try:
        response = requests.get('https://api.coingecko.com/api/v3/ping', timeout=5)
        if response.status_code == 200:
            apis.append('CoinGecko')
    except:
        pass
    
    # Test Coinbase
    try:
        response = requests.get('https://api.pro.coinbase.com/products/BTC-USD', timeout=5)
        if response.status_code == 200:
            apis.append('Coinbase')
    except:
        pass
    
    # Test Fear & Greed
    try:
        response = requests.get('https://api.alternative.me/fng/', timeout=5)
        if response.status_code == 200:
            apis.append('Fear&Greed')
    except:
        pass
    
    if not apis:
        raise ConnectionError("No APIs accessible")
    
    return f"Connected: {', '.join(apis)}"

# Run all tests
print(f"{Fore.CYAN}Running component tests...\n")

test_component("1. Core Dependencies", test_dependencies)
test_component("2. ML Libraries", test_ml_libraries)
test_component("3. Market Data Fetcher", test_market_fetcher)
test_component("4. ML Prediction Engine", test_ml_engine)
test_component("5. Prediction Analyzer", test_analyzer)
test_component("6. Trading Bot", test_trading_bot)
test_component("7. Dashboard Components", test_dashboard)
test_component("8. API Connectivity", test_api_connectivity)

# Print summary
print(f"\n{Fore.CYAN}{'='*60}")
print(f"{Fore.CYAN}Test Summary")
print(f"{Fore.CYAN}{'='*60}\n")

passed = sum(1 for _, success, _ in results if success)
failed = len(results) - passed

for name, success, result in results:
    status = f"{Fore.GREEN}✓" if success else f"{Fore.RED}✗"
    print(f"{status} {name}")
    if success:
        print(f"  {Fore.WHITE}{result}")

print(f"\n{Fore.CYAN}{'='*60}")
print(f"{Fore.GREEN}Passed: {passed}/{len(results)}")
print(f"{Fore.RED}Failed: {failed}/{len(results)}")
print(f"{Fore.CYAN}{'='*60}\n")

if failed == 0:
    print(f"{Fore.GREEN}🎉 All tests passed! You're ready to start trading.")
    print(f"\n{Fore.YELLOW}Next steps:")
    print(f"  1. Run: {Fore.CYAN}.\\start_prediction_dashboard.ps1")
    print(f"  2. Click 'Train ML Models' button")
    print(f"  3. Review predictions and start trading!")
    sys.exit(0)
else:
    print(f"{Fore.RED}⚠️  Some tests failed. Please fix the issues above.")
    print(f"\n{Fore.YELLOW}Common fixes:")
    print(f"  • Install missing packages: {Fore.CYAN}pip install -r requirements.txt")
    print(f"  • Check internet connection for API tests")
    print(f"  • Update packages: {Fore.CYAN}pip install --upgrade -r requirements.txt")
    sys.exit(1)

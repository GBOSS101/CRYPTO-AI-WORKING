"""
Complete Bot Testing Script
Tests all components: Data fetching, predictions, analysis, and trading bot
"""
import sys
from datetime import datetime
from prediction_market_fetcher import PredictionMarketFetcher
from prediction_market_analyzer import PredictionMarketAnalyzer
from multitimeframe_predictor import MultiTimeframePredictor
from prediction_trading_bot import PredictionTradingBot

def test_data_fetching():
    """Test 1: Data fetching from Coinbase"""
    print("\n" + "="*60)
    print("TEST 1: Data Fetching (Coinbase Authenticated API)")
    print("="*60)
    
    try:
        fetcher = PredictionMarketFetcher()
        
        # Test live price
        print("\n📊 Testing live BTC price...")
        price = fetcher.get_live_btc_price()
        print(f"✅ Live BTC Price: ${price:,.2f}")
        
        # Test historical data
        print("\n📊 Testing historical data (30 days)...")
        df = fetcher.get_btc_historical_data(days=30)
        print(f"✅ Fetched {len(df)} candles")
        print(f"   Latest close: ${df.iloc[-1]['close']:,.2f}")
        print(f"   Date range: {df.index[0]} to {df.index[-1]}")
        
        return True, price, df
    except Exception as e:
        print(f"❌ Data fetching failed: {e}")
        return False, None, None

def test_multitimeframe_predictions(historical_df, current_price):
    """Test 2: Multi-timeframe predictions"""
    print("\n" + "="*60)
    print("TEST 2: Multi-Timeframe Predictions (5 Timeframes)")
    print("="*60)
    
    try:
        predictor = MultiTimeframePredictor()
        
        print(f"\n📊 Generating predictions for {len(historical_df)} candles...")
        print(f"   Current BTC: ${current_price:,.2f}")
        
        predictions = predictor.predict_all_timeframes(historical_df, current_price)
        
        print("\n✅ PREDICTIONS GENERATED:")
        print("-" * 60)
        for tf_name, pred in predictions['timeframes'].items():
            direction = pred['direction']
            emoji = "🚀" if direction == "STRONG_BULLISH" else "📈" if direction == "BULLISH" else "➡️" if direction == "NEUTRAL" else "📉"
            
            print(f"{emoji} {tf_name.upper()}")
            print(f"   Predicted: ${pred['predicted_price']:,.2f} ({pred['change_pct']:+.2f}%)")
            print(f"   Direction: {direction}")
            print(f"   Confidence: {pred['confidence']:.1%}")
            print(f"   Horizon: {pred['horizon']}")
        
        print("\n✅ Coinbase-Style Prediction Markets:")
        print("-" * 60)
        markets = predictions.get('markets', [])
        for i, market in enumerate(markets[:5], 1):  # Show top 5
            print(f"\n{i}. {market['title']}")
            print(f"   YES: {market['yes_prob']:.1%} | NO: {market['no_prob']:.1%}")
            print(f"   Edge: {market['edge']:+.1%}")
            print(f"   Signal: {market['signal']}")
            print(f"   Recommended Action: {market['action']}")
        
        return True, predictions
    except Exception as e:
        print(f"❌ Prediction generation failed: {e}")
        import traceback
        traceback.print_exc()
        return False, None

def test_market_analysis():
    """Test 3: Complete market analysis"""
    print("\n" + "="*60)
    print("TEST 3: Market Analysis (ML + Technical + Sentiment)")
    print("="*60)
    
    try:
        analyzer = PredictionMarketAnalyzer(auto_train=False)
        
        print("\n📊 Running complete market analysis...")
        analysis = analyzer.analyze_market()
        
        if 'error' in analysis:
            print(f"❌ Analysis failed: {analysis['error']}")
            return False, None
        
        # Current price
        print(f"\n✅ Current BTC: ${analysis['current_price']:,.2f}")
        
        # Overall signal
        signal = analysis['overall_signal']
        print(f"\n📊 OVERALL SIGNAL:")
        print(f"   Signal: {signal['signal']}")
        print(f"   Confidence: {signal['confidence']:.1%}")
        print(f"   Score: {signal['score']}/100")
        
        # ML Predictions
        ml = analysis.get('ml_prediction', {})
        if ml and ml.get('predicted_price'):
            print(f"\n🤖 ML PREDICTIONS:")
            print(f"   Predicted: ${ml['predicted_price']:,.2f}")
            print(f"   Direction: {ml['direction']}")
            print(f"   Confidence: {ml['confidence']:.1%}")
            print(f"   Models: {', '.join(ml.get('models_used', []))}")
        
        # Technical Analysis
        tech = analysis.get('technical_analysis', {})
        if tech and tech.get('overall_signal'):
            print(f"\n📈 TECHNICAL ANALYSIS:")
            print(f"   Signal: {tech['overall_signal']}")
            indicators = tech.get('indicators', {})
            print(f"   RSI: {indicators.get('rsi', 0):.1f}")
            print(f"   MACD: {indicators.get('macd', 0):.2f}")
            print(f"   Trend: {tech.get('trend', 'N/A')}")
        
        # Sentiment
        sentiment = analysis.get('sentiment', {})
        if sentiment and sentiment.get('fear_greed_index'):
            print(f"\n😱 SENTIMENT:")
            print(f"   Fear & Greed: {sentiment['fear_greed_index']}/100")
            print(f"   Trend: {sentiment.get('trend', 'N/A')}")
        
        return True, analysis
    except Exception as e:
        print(f"❌ Market analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return False, None

def test_trading_bot():
    """Test 4: Trading bot (simulation mode)"""
    print("\n" + "="*60)
    print("TEST 4: Trading Bot (Simulation Mode)")
    print("="*60)
    
    try:
        bot = PredictionTradingBot(
            risk_level='medium',
            auto_trade=False,  # SIMULATION ONLY
            min_confidence=0.6
        )
        
        print("\n✅ Bot initialized successfully")
        
        # Get current status
        status = bot.get_status()
        print(f"\n📊 BOT STATUS:")
        print(f"   Portfolio Value: ${status['portfolio_value']:,.2f}")
        print(f"   Cash Available: ${status['cash']:,.2f}")
        print(f"   Open Positions: {status['positions']}")
        print(f"   Total Trades: {status['stats']['total_trades']}")
        
        # Run one trading cycle
        print("\n🔄 Running one trading cycle...")
        bot._trading_cycle()
        
        print("\n✅ Trading cycle completed successfully")
        
        return True, bot
    except Exception as e:
        print(f"❌ Trading bot test failed: {e}")
        import traceback
        traceback.print_exc()
        return False, None

def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("🧪 CRYPTOAI COMPLETE SYSTEM TEST")
    print("="*70)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = {}
    
    # Test 1: Data Fetching
    success, price, df = test_data_fetching()
    results['data_fetching'] = success
    
    if not success:
        print("\n❌ Data fetching failed - aborting further tests")
        return
    
    # Test 2: Multi-timeframe Predictions
    success, predictions = test_multitimeframe_predictions(df, price)
    results['predictions'] = success
    
    # Test 3: Market Analysis
    success, analysis = test_market_analysis()
    results['analysis'] = success
    
    # Test 4: Trading Bot
    success, bot = test_trading_bot()
    results['trading_bot'] = success
    
    # Final Summary
    print("\n" + "="*70)
    print("📊 TEST SUMMARY")
    print("="*70)
    
    all_passed = True
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status} - {test_name.replace('_', ' ').title()}")
        if not passed:
            all_passed = False
    
    print("\n" + "="*70)
    if all_passed:
        print("🎉 ALL TESTS PASSED - BOT IS FULLY FUNCTIONAL!")
        print("\nYou can now:")
        print("  1. Run dashboard: python dashboard_predictions.py")
        print("  2. Run trading bot: python prediction_trading_bot.py")
        print("  3. Enable live trading: python prediction_trading_bot.py --live")
    else:
        print("⚠️  SOME TESTS FAILED - Please review errors above")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()

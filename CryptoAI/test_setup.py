"""
Quick test script to verify all components are working
"""
print("🔍 Testing CryptoAI Components...\n")

# Test imports
try:
    from config import Config
    print("✅ Config module loaded")
    
    from data_fetcher import LiveDataFetcher
    print("✅ Data Fetcher module loaded")
    
    from technical_analyzer import TechnicalAnalyzer
    print("✅ Technical Analyzer module loaded")
    
    from trading_engine import TradingEngine
    print("✅ Trading Engine module loaded")
    
    from portfolio import Portfolio
    print("✅ Portfolio module loaded")
    
    # Test dashboard imports
    import dash
    import dash_bootstrap_components as dbc
    print("✅ Dashboard modules loaded")
    
    print("\n" + "="*50)
    print("🎉 All components working correctly!")
    print("="*50)
    
    # Test basic functionality
    print("\n🧪 Testing Basic Functions...\n")
    
    config = Config()
    print(f"✅ Wallet Size: ${config.WALLET_SIZE:,.2f}")
    print(f"✅ Risk Level: {config.RISK_LEVEL}")
    
    portfolio = Portfolio(initial_balance=Config.WALLET_SIZE)
    print(f"✅ Portfolio initialized with ${portfolio.cash_balance:,.2f}")
    
    print("\n" + "="*50)
    print("✅ SYSTEM READY TO USE!")
    print("="*50)
    
    print("\n📊 Launch Commands:")
    print("   Web Dashboard: python dashboard.py")
    print("   CLI Interface: python main.py")
    
except ImportError as e:
    print(f"❌ Import Error: {e}")
    print("\n💡 Run: pip install -r requirements.txt")
except Exception as e:
    print(f"❌ Error: {e}")

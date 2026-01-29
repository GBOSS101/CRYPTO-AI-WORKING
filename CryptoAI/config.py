"""
Configuration management for CryptoAI Trading Assistant
"""
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # API Configuration
    BINANCE_API_KEY = os.getenv('BINANCE_API_KEY', '')
    BINANCE_SECRET_KEY = os.getenv('BINANCE_SECRET_KEY', '')
    COINGECKO_API_KEY = os.getenv('COINGECKO_API_KEY', '')
    
    # Portfolio Settings
    WALLET_SIZE = float(os.getenv('WALLET_SIZE', 1000))
    CURRENCY = os.getenv('CURRENCY', 'USD')
    RISK_LEVEL = os.getenv('RISK_LEVEL', 'medium')
    
    # Trading Parameters
    MAX_POSITION_SIZE = float(os.getenv('MAX_POSITION_SIZE', 0.15))
    MIN_POSITION_SIZE = float(os.getenv('MIN_POSITION_SIZE', 0.03))
    STOP_LOSS_PERCENT = float(os.getenv('STOP_LOSS_PERCENT', 5))
    TAKE_PROFIT_PERCENT = float(os.getenv('TAKE_PROFIT_PERCENT', 15))
    
    # Update Intervals
    PRICE_UPDATE_INTERVAL = int(os.getenv('PRICE_UPDATE_INTERVAL', 30))
    ANALYSIS_UPDATE_INTERVAL = int(os.getenv('ANALYSIS_UPDATE_INTERVAL', 300))
    
    # Top cryptocurrencies to track
    TOP_CRYPTOS = [
        'bitcoin', 'ethereum', 'dogecoin', 'solana', 'ripple',
        'binancecoin', 'cardano', 'polkadot', 'avalanche-2', 'chainlink',
        'polygon', 'uniswap', 'litecoin', 'near', 'cosmos', 'algorand'
    ]
    
    # Fast analysis subset (for quick callbacks)
    FAST_ANALYSIS_CRYPTOS = [
        'bitcoin', 'ethereum', 'dogecoin', 'solana', 'ripple'
    ]
    
    # Risk profiles
    RISK_PROFILES = {
        'low': {
            'max_position': 0.10,
            'min_volatility': 0,
            'max_volatility': 30,
            'preferred_assets': ['bitcoin', 'ethereum', 'binancecoin']
        },
        'medium': {
            'max_position': 0.15,
            'min_volatility': 0,
            'max_volatility': 50,
            'preferred_assets': ['bitcoin', 'ethereum', 'dogecoin', 'solana', 'ripple']
        },
        'high': {
            'max_position': 0.20,
            'min_volatility': 0,
            'max_volatility': 100,
            'preferred_assets': []  # All assets allowed
        }
    }
    
    @classmethod
    def get_risk_profile(cls):
        return cls.RISK_PROFILES.get(cls.RISK_LEVEL, cls.RISK_PROFILES['medium'])

"""
Technical Analysis Module
Analyzes cryptocurrency data using technical indicators
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from ta.trend import SMAIndicator, EMAIndicator, MACD
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.volatility import BollingerBands, AverageTrueRange

class TechnicalAnalyzer:
    def __init__(self):
        self.signals = {
            'strong_buy': 5,
            'buy': 4,
            'neutral': 3,
            'sell': 2,
            'strong_sell': 1
        }
    
    def analyze_coin(self, df: pd.DataFrame) -> Dict:
        """
        Perform comprehensive technical analysis on price data
        """
        if df.empty or len(df) < 50:
            return {'error': 'Insufficient data for analysis'}
        
        df = df.copy()
        
        # Calculate indicators
        indicators = self._calculate_indicators(df)
        
        # Generate signals
        signals = self._generate_signals(indicators, df)
        
        # Calculate overall score
        overall_signal, confidence = self._calculate_overall_signal(signals)
        
        return {
            'indicators': indicators,
            'signals': signals,
            'overall_signal': overall_signal,
            'confidence': confidence,
            'current_price': df['price'].iloc[-1],
            'price_trend': self._get_price_trend(df)
        }
    
    def _calculate_indicators(self, df: pd.DataFrame) -> Dict:
        """
        Calculate technical indicators
        """
        indicators = {}
        
        # Moving Averages
        sma_20 = SMAIndicator(close=df['price'], window=20)
        sma_50 = SMAIndicator(close=df['price'], window=50)
        ema_12 = EMAIndicator(close=df['price'], window=12)
        ema_26 = EMAIndicator(close=df['price'], window=26)
        
        indicators['sma_20'] = sma_20.sma_indicator().iloc[-1]
        indicators['sma_50'] = sma_50.sma_indicator().iloc[-1]
        indicators['ema_12'] = ema_12.ema_indicator().iloc[-1]
        indicators['ema_26'] = ema_26.ema_indicator().iloc[-1]
        
        # RSI
        rsi = RSIIndicator(close=df['price'], window=14)
        indicators['rsi'] = rsi.rsi().iloc[-1]
        
        # MACD
        macd = MACD(close=df['price'])
        indicators['macd'] = macd.macd().iloc[-1]
        indicators['macd_signal'] = macd.macd_signal().iloc[-1]
        indicators['macd_diff'] = macd.macd_diff().iloc[-1]
        
        # Bollinger Bands
        bb = BollingerBands(close=df['price'], window=20, window_dev=2)
        indicators['bb_upper'] = bb.bollinger_hband().iloc[-1]
        indicators['bb_middle'] = bb.bollinger_mavg().iloc[-1]
        indicators['bb_lower'] = bb.bollinger_lband().iloc[-1]
        
        # Volatility
        if 'volume' in df.columns and not df['volume'].isna().all():
            indicators['volume_avg'] = df['volume'].tail(20).mean()
            indicators['volume_current'] = df['volume'].iloc[-1]
        
        return indicators
    
    def _generate_signals(self, indicators: Dict, df: pd.DataFrame) -> Dict:
        """
        Generate trading signals from indicators
        """
        signals = {}
        current_price = df['price'].iloc[-1]
        
        # RSI Signal
        rsi = indicators.get('rsi', 50)
        if rsi < 30:
            signals['rsi'] = 'strong_buy'
        elif rsi < 45:
            signals['rsi'] = 'buy'
        elif rsi > 70:
            signals['rsi'] = 'strong_sell'
        elif rsi > 55:
            signals['rsi'] = 'sell'
        else:
            signals['rsi'] = 'neutral'
        
        # Moving Average Signal
        sma_20 = indicators.get('sma_20', current_price)
        sma_50 = indicators.get('sma_50', current_price)
        
        if current_price > sma_20 > sma_50:
            signals['ma'] = 'strong_buy'
        elif current_price > sma_20:
            signals['ma'] = 'buy'
        elif current_price < sma_20 < sma_50:
            signals['ma'] = 'strong_sell'
        elif current_price < sma_20:
            signals['ma'] = 'sell'
        else:
            signals['ma'] = 'neutral'
        
        # MACD Signal
        macd_diff = indicators.get('macd_diff', 0)
        if macd_diff > 0:
            signals['macd'] = 'buy' if macd_diff > 5 else 'buy'
        elif macd_diff < 0:
            signals['macd'] = 'sell' if macd_diff < -5 else 'sell'
        else:
            signals['macd'] = 'neutral'
        
        # Bollinger Bands Signal
        bb_upper = indicators.get('bb_upper', current_price * 1.1)
        bb_lower = indicators.get('bb_lower', current_price * 0.9)
        
        if current_price <= bb_lower:
            signals['bb'] = 'strong_buy'
        elif current_price >= bb_upper:
            signals['bb'] = 'strong_sell'
        else:
            signals['bb'] = 'neutral'
        
        # Volume Signal
        if 'volume_avg' in indicators and 'volume_current' in indicators:
            volume_ratio = indicators['volume_current'] / indicators['volume_avg']
            if volume_ratio > 1.5:
                signals['volume'] = 'strong'  # High volume confirms trend
            else:
                signals['volume'] = 'weak'
        
        return signals
    
    def _calculate_overall_signal(self, signals: Dict) -> Tuple[str, float]:
        """
        Calculate overall trading signal from individual signals
        """
        signal_scores = []
        
        for key, value in signals.items():
            if key != 'volume' and value in self.signals:
                signal_scores.append(self.signals[value])
        
        if not signal_scores:
            return 'neutral', 0.0
        
        avg_score = np.mean(signal_scores)
        confidence = (1 - np.std(signal_scores) / 2) * 100  # Lower std = higher confidence
        
        if avg_score >= 4.5:
            return 'strong_buy', min(confidence, 100)
        elif avg_score >= 3.5:
            return 'buy', min(confidence, 100)
        elif avg_score <= 1.5:
            return 'strong_sell', min(confidence, 100)
        elif avg_score <= 2.5:
            return 'sell', min(confidence, 100)
        else:
            return 'neutral', min(confidence, 100)
    
    def _get_price_trend(self, df: pd.DataFrame) -> str:
        """
        Determine the overall price trend
        """
        if len(df) < 20:
            return 'insufficient_data'
        
        recent_prices = df['price'].tail(20)
        old_avg = recent_prices.head(10).mean()
        new_avg = recent_prices.tail(10).mean()
        
        change_percent = ((new_avg - old_avg) / old_avg) * 100
        
        if change_percent > 5:
            return 'strong_uptrend'
        elif change_percent > 2:
            return 'uptrend'
        elif change_percent < -5:
            return 'strong_downtrend'
        elif change_percent < -2:
            return 'downtrend'
        else:
            return 'sideways'
    
    def calculate_support_resistance(self, df: pd.DataFrame, num_levels: int = 3) -> Dict:
        """
        Calculate support and resistance levels
        """
        if len(df) < 50:
            return {'support': [], 'resistance': []}
        
        prices = df['price'].values
        
        # Find local minima and maxima
        from scipy.signal import argrelextrema
        
        local_min = argrelextrema(prices, np.less, order=5)[0]
        local_max = argrelextrema(prices, np.greater, order=5)[0]
        
        support_levels = sorted([prices[i] for i in local_min])[-num_levels:]
        resistance_levels = sorted([prices[i] for i in local_max])[-num_levels:]
        
        return {
            'support': support_levels,
            'resistance': resistance_levels
        }

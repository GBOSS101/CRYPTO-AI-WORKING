"""
Multi-Timeframe Prediction Engine
Generates predictions for 15min, 1hr, 4hr, 24hr, and 7d horizons
Matches Coinbase Prediction Markets format with YES/NO probabilities
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
from datetime import datetime, timedelta
import math
from scipy.stats import norm
import warnings
warnings.filterwarnings('ignore')

from ml_prediction_engine import MLPredictionEngine
from technical_analyzer import TechnicalAnalyzer


class MultiTimeframePredictor:
    """Generates predictions across multiple timeframes"""
    
    # Timeframe configurations (hours, model weights)
    TIMEFRAMES = {
        '15min': {
            'hours': 0.25,
            'weights': {'lstm': 0.20, 'xgboost': 0.30, 'technical': 0.50},
            'confidence_decay': 0.95  # High decay for ultra-short term
        },
        '1hr': {
            'hours': 1.0,
            'weights': {'lstm': 0.30, 'xgboost': 0.35, 'technical': 0.35},
            'confidence_decay': 0.90
        },
        '4hr': {
            'hours': 4.0,
            'weights': {'lstm': 0.35, 'xgboost': 0.35, 'technical': 0.30},
            'confidence_decay': 0.80
        },
        '24hr': {
            'hours': 24.0,
            'weights': {'lstm': 0.45, 'xgboost': 0.35, 'technical': 0.20},
            'confidence_decay': 0.70
        },
        '7d': {
            'hours': 168.0,
            'weights': {'lstm': 0.50, 'xgboost': 0.30, 'technical': 0.20},
            'confidence_decay': 0.50  # Low confidence for long-term
        }
    }
    
    def __init__(self):
        """Initialize multi-timeframe predictor"""
        self.technical_analyzer = TechnicalAnalyzer()
        
        # Create ML engines for each timeframe
        self.engines = {}
        for timeframe, config in self.TIMEFRAMES.items():
            hours = config['hours']
            lookback = max(5, min(60, int(hours * 5)))  # Adaptive lookback
            horizon = max(1, int(math.ceil(hours)))
            self.engines[timeframe] = MLPredictionEngine(
                lookback_period=lookback,
                prediction_horizon=horizon
            )
    
    def predict_all_timeframes(self, historical_df: pd.DataFrame, current_price: float) -> Dict:
        """
        Generate predictions for all timeframes
        
        Args:
            historical_df: Historical OHLCV data
            current_price: Current BTC price
        
        Returns:
            Dict with predictions for each timeframe
        """
        all_predictions = {
            'timestamp': datetime.now().isoformat(),
            'current_price': current_price,
            'timeframes': {}
        }
        
        for timeframe, config in self.TIMEFRAMES.items():
            try:
                prediction = self._predict_single_timeframe(
                    timeframe, config, historical_df, current_price
                )
                all_predictions['timeframes'][timeframe] = prediction
            except Exception as e:
                print(f"Error predicting {timeframe}: {e}")
                all_predictions['timeframes'][timeframe] = {
                    'error': str(e),
                    'predicted_price': current_price,
                    'confidence': 0.0
                }
        
        return all_predictions
    
    def _predict_single_timeframe(self, timeframe: str, config: Dict, 
                                  historical_df: pd.DataFrame, 
                                  current_price: float) -> Dict:
        """Predict for a single timeframe"""
        engine = self.engines[timeframe]
        weights = config['weights']
        hours = config['hours']
        confidence_decay = config['confidence_decay']
        
        # Get ML prediction
        ml_pred = engine.predict(historical_df, use_ensemble=True)
        
        # Get technical analysis (short-term focus for < 1hr)
        tech_signals = {}
        if not historical_df.empty:
            tech_signals = self.technical_analyzer.analyze_coin(historical_df)
        
        # Combine predictions using timeframe-specific weights
        predicted_price = current_price
        base_confidence = 0.5
        
        if ml_pred.get('predicted_price', 0) > 0:
            ml_price = ml_pred['predicted_price']
            ml_confidence = ml_pred.get('confidence', 0.5)
            
            # Weighted average
            weight_sum = weights['lstm'] + weights['xgboost'] + weights['technical']
            predicted_price = (
                (ml_price * (weights['lstm'] + weights['xgboost'])) +
                (current_price * weights['technical'])
            ) / weight_sum
            
            base_confidence = ml_confidence * confidence_decay
        
        # Calculate direction and change
        predicted_change_pct = ((predicted_price - current_price) / current_price) * 100
        
        if predicted_change_pct > 1.0:
            direction = 'strong_bullish'
        elif predicted_change_pct > 0.2:
            direction = 'bullish'
        elif predicted_change_pct < -1.0:
            direction = 'strong_bearish'
        elif predicted_change_pct < -0.2:
            direction = 'bearish'
        else:
            direction = 'neutral'
        
        # Calculate expiry time
        expiry_time = datetime.now() + timedelta(hours=hours)
        
        return {
            'timeframe': timeframe,
            'hours': hours,
            'predicted_price': round(predicted_price, 2),
            'predicted_change_pct': round(predicted_change_pct, 2),
            'direction': direction,
            'confidence': round(base_confidence, 3),
            'expiry_time': expiry_time.isoformat(),
            'model_weights': weights
        }
    
    def calculate_threshold_probabilities(self, 
                                         current_price: float,
                                         predicted_price: float,
                                         confidence: float,
                                         thresholds: List[float]) -> Dict:
        """
        Calculate YES/NO probabilities for specific price thresholds
        Uses normal distribution centered on predicted price
        
        Args:
            current_price: Current BTC price
            predicted_price: Predicted BTC price
            confidence: Model confidence (0-1)
            thresholds: List of price thresholds to evaluate
        
        Returns:
            Dict with YES% and NO% for each threshold
        """
        # Calculate standard deviation based on confidence
        # Low confidence = wide distribution (high sigma)
        # High confidence = narrow distribution (low sigma)
        base_volatility = current_price * 0.02  # 2% base volatility
        sigma = base_volatility * (1.5 - confidence)  # Inverse relationship
        
        probabilities = {}
        
        for threshold in thresholds:
            # Calculate z-score
            z_score = (threshold - predicted_price) / sigma if sigma > 0 else 0
            
            # Cumulative distribution function
            # P(X > threshold) = 1 - P(X <= threshold)
            yes_prob = float(1 - norm.cdf(z_score))
            no_prob = float(norm.cdf(z_score))
            
            # Ensure probabilities sum to ~100% (accounting for rounding)
            yes_pct = round(yes_prob * 100, 1)
            no_pct = round(no_prob * 100, 1)
            
            # Determine recommendation
            if yes_pct > 65:
                recommendation = "BUY YES"
                strength = "STRONG" if yes_pct > 75 else "GOOD"
            elif no_pct > 65:
                recommendation = "BUY NO"
                strength = "STRONG" if no_pct > 75 else "GOOD"
            else:
                recommendation = "SKIP"
                strength = "WEAK"
            
            # Calculate edge (expected value vs. 50/50 market)
            edge = max(yes_pct, no_pct) - 50
            
            probabilities[threshold] = {
                'threshold_price': threshold,
                'yes_probability': yes_pct,
                'no_probability': no_pct,
                'recommendation': recommendation,
                'strength': strength,
                'edge': round(edge, 1),
                'above_current': threshold > current_price
            }
        
        return probabilities
    
    def generate_coinbase_style_markets(self, 
                                       current_price: float,
                                       timeframe_predictions: Dict) -> List[Dict]:
        """
        Generate Coinbase-style prediction market questions
        
        Args:
            current_price: Current BTC price
            timeframe_predictions: Predictions from predict_all_timeframes()
        
        Returns:
            List of market dicts matching Coinbase format
        """
        markets = []
        
        # Common threshold multipliers based on Coinbase patterns
        threshold_configs = [
            {'multiplier': 0.98, 'label': '-2%'},
            {'multiplier': 0.99, 'label': '-1%'},
            {'multiplier': 1.00, 'label': 'Current'},
            {'multiplier': 1.01, 'label': '+1%'},
            {'multiplier': 1.02, 'label': '+2%'},
            {'multiplier': 1.03, 'label': '+3%'},
            {'multiplier': 1.05, 'label': '+5%'},
            {'multiplier': 1.10, 'label': '+10%'},
        ]
        
        # Also add specific round numbers
        round_numbers = self._get_round_numbers(current_price)
        
        for timeframe_name, pred_data in timeframe_predictions.get('timeframes', {}).items():
            if 'error' in pred_data:
                continue
            
            predicted_price = pred_data['predicted_price']
            confidence = pred_data['confidence']
            expiry_time = pred_data['expiry_time']
            hours = pred_data['hours']
            
            # Generate thresholds for this timeframe
            thresholds = [current_price * cfg['multiplier'] for cfg in threshold_configs]
            thresholds.extend(round_numbers)
            thresholds = sorted(list(set([round(t, 2) for t in thresholds])))
            
            # Calculate probabilities
            probabilities = self.calculate_threshold_probabilities(
                current_price, predicted_price, confidence, thresholds
            )
            
            # Create market entries
            for threshold, prob_data in probabilities.items():
                # Only include markets with strong edge (>10%)
                if prob_data['edge'] < 10:
                    continue
                
                market = {
                    'question': f"Will Bitcoin be above ${threshold:,.0f} in {timeframe_name}?",
                    'timeframe': timeframe_name,
                    'hours_until_expiry': hours,
                    'expiry_time': expiry_time,
                    'current_price': current_price,
                    'threshold_price': threshold,
                    'yes_probability': prob_data['yes_probability'],
                    'no_probability': prob_data['no_probability'],
                    'recommendation': prob_data['recommendation'],
                    'strength': prob_data['strength'],
                    'edge': prob_data['edge'],
                    'model_confidence': round(confidence * 100, 1)
                }
                
                markets.append(market)
        
        # Sort by edge (highest first)
        markets.sort(key=lambda x: x['edge'], reverse=True)
        
        return markets
    
    def _get_round_numbers(self, current_price: float) -> List[float]:
        """Get psychologically important round numbers near current price"""
        round_numbers = []
        
        # Determine rounding based on price magnitude
        if current_price > 100000:
            step = 5000  # $5k increments
        elif current_price > 50000:
            step = 2500  # $2.5k increments
        elif current_price > 10000:
            step = 1000  # $1k increments
        else:
            step = 500   # $500 increments
        
        # Generate round numbers within ±10% of current price
        lower = current_price * 0.90
        upper = current_price * 1.10
        
        # Find nearest round number below current price
        start = int(lower / step) * step
        
        price = start
        while price <= upper:
            if abs(price - current_price) > (current_price * 0.005):  # Skip if too close to current
                round_numbers.append(float(price))
            price += step
        
        return round_numbers[:10]  # Limit to 10 round numbers


if __name__ == "__main__":
    # Test the multi-timeframe predictor
    print("🎯 Testing Multi-Timeframe Predictor...\n")
    
    from prediction_market_fetcher import PredictionMarketFetcher
    
    # Initialize
    predictor = MultiTimeframePredictor()
    fetcher = PredictionMarketFetcher()
    
    # Get current data
    print("📊 Fetching market data...")
    current_price = fetcher.get_live_btc_price()
    historical_df = fetcher.get_btc_historical_data(days=7)
    
    print(f"✅ Current BTC Price: ${current_price:,.2f}\n")
    
    # Generate all timeframe predictions
    print("🔮 Generating predictions for all timeframes...\n")
    all_predictions = predictor.predict_all_timeframes(historical_df, current_price)
    
    # Display results
    print("=" * 80)
    print("MULTI-TIMEFRAME PREDICTIONS")
    print("=" * 80)
    
    for timeframe, pred in all_predictions['timeframes'].items():
        if 'error' in pred:
            print(f"\n⚠️ {timeframe.upper()}: Error - {pred['error']}")
            continue
        
        print(f"\n📈 {timeframe.upper()} Prediction:")
        print(f"   Predicted Price: ${pred['predicted_price']:,.2f}")
        print(f"   Change: {pred['predicted_change_pct']:+.2f}%")
        print(f"   Direction: {pred['direction']}")
        print(f"   Confidence: {pred['confidence']*100:.1f}%")
        print(f"   Expiry: {pred['expiry_time']}")
    
    # Generate Coinbase-style markets
    print("\n" + "=" * 80)
    print("COINBASE-STYLE PREDICTION MARKETS (Top 10 by Edge)")
    print("=" * 80 + "\n")
    
    markets = predictor.generate_coinbase_style_markets(current_price, all_predictions)
    
    for i, market in enumerate(markets[:10], 1):
        print(f"{i}. {market['question']}")
        print(f"   ⏰ Timeframe: {market['timeframe']} ({market['hours_until_expiry']:.1f}h)")
        print(f"   📊 YES: {market['yes_probability']:.1f}% | NO: {market['no_probability']:.1f}%")
        print(f"   💡 Recommendation: {market['recommendation']} ({market['strength']})")
        print(f"   💰 Edge: {market['edge']:.1f}% | Confidence: {market['model_confidence']:.1f}%")
        print()
    
    if not markets:
        print("⚠️ No markets with strong edge (>10%) found at this time.\n")
    
    print("✅ Testing complete!")

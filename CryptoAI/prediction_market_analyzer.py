"""
Prediction Market Analyzer
Combines market data, ML predictions, and technical analysis for trading signals
Now with Advanced ML Engine for aggressive real-time training
"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

from prediction_market_fetcher import PredictionMarketFetcher
from ml_prediction_engine import MLPredictionEngine
from technical_analyzer import TechnicalAnalyzer

# Import advanced ML engine
try:
    from advanced_ml_engine import AdvancedMLEngine
    ADVANCED_ML_AVAILABLE = True
except ImportError:
    ADVANCED_ML_AVAILABLE = False
    print("⚠️  Advanced ML Engine not available, using standard models")


class PredictionMarketAnalyzer:
    """Analyzes prediction markets and generates trading signals"""
    
    def __init__(self, auto_train: bool = True):
        """
        Initialize the prediction market analyzer
        
        Args:
            auto_train: Whether to auto-train ML models on initialization
        """
        self.fetcher = PredictionMarketFetcher(cache_timeout=15)
        self.ml_engine = MLPredictionEngine(lookback_period=60, prediction_horizon=24)
        self.technical_analyzer = TechnicalAnalyzer()
        
        # Initialize Advanced ML Engine
        if ADVANCED_ML_AVAILABLE:
            self.advanced_ml = AdvancedMLEngine(lookback=60, prediction_horizon=24)
            print("✅ Advanced ML Engine: ACTIVE (Seq2Seq-VAE + BiGRU + Attention)")
        else:
            self.advanced_ml = None
            print("⚠️  Advanced ML Engine: Not available, using standard models")
        
        self.models_trained = False
        self.last_training = None
        self.use_advanced_ml = ADVANCED_ML_AVAILABLE
        
        if auto_train:
            self.train_models()
    
    def train_models(self, days: int = 30, aggressive: bool = False) -> Dict:
        """
        Train ML models with historical data
        Uses Advanced ML Engine if available
        
        Args:
            days: Days of historical data for training
        
        Returns:
            Dict with training results
        """
        print(f"\nTraining models with {days} days of data...")
        
        try:
            # Fetch historical data
            historical_df = self.fetcher.get_btc_historical_data(days=days)
            
            if historical_df.empty:
                return {
                    'success': False,
                    'error': 'Failed to fetch historical data'
                }
            
            # Train Advanced ML if available
            if self.use_advanced_ml and self.advanced_ml:
                mode_label = "AGGRESSIVE" if aggressive else "STABLE"
                print(f"🚀 Using Advanced ML Engine ({mode_label} TRAINING)")
                advanced_results = self.advanced_ml.train_models(historical_df, aggressive=aggressive)
                
                if advanced_results.get('success'):
                    self.models_trained = True
                    self.last_training = datetime.now()
                    
                    return {
                        'success': True,
                        'timestamp': self.last_training.isoformat(),
                        'engine': 'Advanced ML (Seq2Seq-VAE + BiGRU + Attention)',
                        'models_trained': advanced_results.get('models_trained', 3),
                        'training_samples': advanced_results.get('training_samples', len(historical_df)),
                        'training_mode': mode_label,
                        'online_learning': True
                    }
            
            # Fallback to standard training
            print("📊 Using Standard ML Engine")
            # Train XGBoost
            xgb_results = self.ml_engine.train_xgboost_model(historical_df)
            
            # Train LSTM
            lstm_results = self.ml_engine.train_lstm_model(historical_df)
            
            self.models_trained = True
            self.last_training = datetime.now()
            
            return {
                'success': True,
                'timestamp': self.last_training.isoformat(),
                'engine': 'Standard ML (XGBoost + LSTM)',
                'xgboost': xgb_results,
                'lstm': lstm_results,
                'training_samples': len(historical_df)
            }
            
        except Exception as e:
            print(f"Error training models: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def analyze_market(self) -> Dict:
        """
        Perform comprehensive market analysis
        
        Returns:
            Dict with all analysis results
        """
        try:
            # Fetch all market data
            # FIXED: Use authenticated live price instead of deprecated orderbook
            current_price = self.fetcher.get_live_btc_price()
            historical = self.fetcher.get_btc_historical_data(days=30)
            sentiment = self.fetcher.get_market_sentiment()
            funding = self.fetcher.get_funding_rates()
            prediction_odds = self.fetcher.get_prediction_market_odds()
            
            # Get orderbook for depth analysis (optional, not for price)
            orderbook = self.fetcher.get_btc_orderbook(level=2)
            
            # Fallback: If live price fails, use latest from historical data
            if current_price == 0 and not historical.empty:
                current_price = float(historical.iloc[-1]['close'])
                print(f"⚠️ Using historical price as fallback: ${current_price:,.2f}")
            
            # Technical analysis
            technical_signals = {}
            if not historical.empty:
                technical_signals = self.technical_analyzer.analyze_coin(historical)
            
            # ML prediction
            ml_prediction = {}
            if self.models_trained and not historical.empty:
                if self.use_advanced_ml and self.advanced_ml:
                    adv_pred = self.advanced_ml.predict(historical)
                    if adv_pred and not adv_pred.get('error'):
                        predicted_prices = adv_pred.get('predicted_prices', [])
                        predicted_price = predicted_prices[-1] if predicted_prices else 0
                        predicted_change_pct = ((predicted_price - current_price) / current_price) * 100 if current_price else 0
                        ml_prediction = {
                            'timestamp': datetime.now().isoformat(),
                            'current_price': current_price,
                            'predicted_price': float(predicted_price),
                            'predicted_change_pct': float(predicted_change_pct),
                            'direction': 'up' if predicted_price > current_price else 'down' if predicted_price < current_price else 'neutral',
                            'confidence': float(adv_pred.get('confidence', 0.5)),
                            'models_used': ['seq2seq_vae', 'bigru', 'attention'],
                            'advanced': True,
                            'predicted_prices': predicted_prices
                        }
                    else:
                        ml_prediction = self.ml_engine.predict(historical, use_ensemble=True)
                else:
                    ml_prediction = self.ml_engine.predict(historical, use_ensemble=True)
            
            # Combine signals for overall recommendation
            overall_signal = self._calculate_overall_signal(
                technical_signals,
                ml_prediction,
                sentiment,
                orderbook
            )
            
            # Convert historical DataFrame to list of dicts for JSON serialization
            historical_data = []
            if not historical.empty:
                # Reset index to make timestamp a column
                hist_df = historical.reset_index()
                cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'price']
                available_cols = [col for col in cols if col in hist_df.columns]
                historical_data = hist_df[available_cols].tail(100).to_dict('records')
            
            return {
                'timestamp': datetime.now().isoformat(),
                'current_price': current_price,
                'orderbook': {
                    'spread': orderbook.get('spread', 0),
                    'bid_volume': orderbook.get('total_bid_volume', 0),
                    'ask_volume': orderbook.get('total_ask_volume', 0)
                },
                'technical_analysis': technical_signals,
                'ml_prediction': ml_prediction,
                'sentiment': sentiment,
                'funding_rates': funding,
                'prediction_odds': prediction_odds,
                'overall_signal': overall_signal,
                'models_trained': self.models_trained,
                'historical': historical_data,
                'last_training': self.last_training.isoformat() if self.last_training else None
            }
            
        except Exception as e:
            print(f"Error analyzing market: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'error': str(e),
                'current_price': 0,
                'overall_signal': {
                    'signal': 'neutral',
                    'confidence': 0.0,
                    'score': 50
                }
            }
    
    def _calculate_overall_signal(self, 
                                  technical: Dict,
                                  ml_pred: Dict,
                                  sentiment: Dict,
                                  orderbook: Dict) -> Dict:
        """
        Calculate overall trading signal from all inputs
        
        Returns:
            Dict with signal, confidence, and score
        """
        signals = []
        weights = []
        
        # Technical analysis signal (40% weight)
        if technical and 'overall_signal' in technical:
            tech_signal = technical['overall_signal']
            signal_value = self._signal_to_value(tech_signal)
            signals.append(signal_value)
            weights.append(0.40)
        
        # ML prediction signal (35% weight)
        if ml_pred and 'direction' in ml_pred:
            ml_signal = ml_pred['direction']
            signal_value = self._signal_to_value(ml_signal)
            ml_confidence = ml_pred.get('confidence', 0.5)
            signals.append(signal_value)
            weights.append(0.35 * ml_confidence)  # Weight by ML confidence
        
        # Sentiment signal (15% weight)
        if sentiment:
            fear_greed = sentiment.get('fear_greed_index', 50)
            # Convert 0-100 to -1 to +1
            sentiment_value = (fear_greed - 50) / 50
            signals.append(sentiment_value)
            weights.append(0.15)
        
        # Order book imbalance (10% weight)
        if orderbook:
            bid_vol = orderbook.get('total_bid_volume', 0)
            ask_vol = orderbook.get('total_ask_volume', 0)
            total_vol = bid_vol + ask_vol
            
            if total_vol > 0:
                imbalance = (bid_vol - ask_vol) / total_vol
                signals.append(imbalance)
                weights.append(0.10)
        
        # Calculate weighted average
        if signals and weights:
            total_weight = sum(weights)
            weighted_signal = sum(s * w for s, w in zip(signals, weights)) / total_weight
            
            # Calculate confidence (based on signal agreement)
            if len(signals) > 1:
                signal_std = np.std(signals)
                confidence = max(0.0, min(1.0, 1.0 - signal_std))
            else:
                confidence = 0.5
            
            # Convert to score (0-100)
            score = int((weighted_signal + 1) * 50)  # -1 to +1 → 0 to 100
            
            # Determine signal direction
            if weighted_signal > 0.3:
                signal = 'strong_buy'
            elif weighted_signal > 0.1:
                signal = 'buy'
            elif weighted_signal < -0.3:
                signal = 'strong_sell'
            elif weighted_signal < -0.1:
                signal = 'sell'
            else:
                signal = 'neutral'
            
            return {
                'signal': signal,
                'confidence': round(confidence, 2),
                'score': score,
                'weighted_value': round(weighted_signal, 3),
                'components': {
                    'technical': signals[0] if len(signals) > 0 else 0,
                    'ml_prediction': signals[1] if len(signals) > 1 else 0,
                    'sentiment': signals[2] if len(signals) > 2 else 0,
                    'orderbook': signals[3] if len(signals) > 3 else 0
                }
            }
        
        return {
            'signal': 'neutral',
            'confidence': 0.0,
            'score': 50,
            'weighted_value': 0.0,
            'components': {}
        }
    
    def _signal_to_value(self, signal: str) -> float:
        """Convert signal string to numeric value (-1 to +1)"""
        signal_map = {
            'strong_sell': -1.0,
            'sell': -0.5,
            'neutral': 0.0,
            'buy': 0.5,
            'strong_buy': 1.0
        }
        return signal_map.get(signal, 0.0)
    
    def get_trade_recommendations(self, 
                                 portfolio_value: float = 1000,
                                 risk_level: str = 'medium') -> List[Dict]:
        """
        Get specific trade recommendations
        
        Args:
            portfolio_value: Total portfolio value in USD
            risk_level: Risk level (low, medium, high)
        
        Returns:
            List of trade recommendations
        """
        analysis = self.analyze_market()
        
        if 'error' in analysis:
            return []
        
        current_price = analysis['current_price']
        overall_signal = analysis['overall_signal']
        
        if current_price == 0:
            return []
        
        recommendations = []
        
        # Position sizing based on risk level
        risk_multipliers = {
            'low': 0.10,      # 10% of portfolio
            'medium': 0.15,   # 15% of portfolio
            'high': 0.20      # 20% of portfolio
        }
        
        position_size_usd = portfolio_value * risk_multipliers.get(risk_level, 0.15)
        
        # Only recommend trades if signal is strong enough
        signal = overall_signal['signal']
        confidence = overall_signal['confidence']
        
        if signal in ['buy', 'strong_buy'] and confidence > 0.5:
            # Calculate position size
            btc_amount = position_size_usd / current_price
            
            # Get ML prediction for target
            ml_pred = analysis.get('ml_prediction', {})
            predicted_price = ml_pred.get('predicted_price', current_price * 1.05)
            
            # Calculate stop loss and take profit
            stop_loss = current_price * 0.95  # 5% stop loss
            take_profit = predicted_price * 1.02  # 2% above prediction
            
            recommendations.append({
                'action': 'BUY',
                'asset': 'BTC',
                'signal': signal,
                'confidence': confidence,
                'score': overall_signal['score'],
                'entry_price': current_price,
                'amount_btc': round(btc_amount, 8),
                'amount_usd': position_size_usd,
                'stop_loss': round(stop_loss, 2),
                'take_profit': round(take_profit, 2),
                'predicted_price': round(predicted_price, 2),
                'expected_return_pct': round(((take_profit - current_price) / current_price) * 100, 2),
                'risk_reward_ratio': round((take_profit - current_price) / (current_price - stop_loss), 2),
                'reasons': self._get_trade_reasons(analysis),
                'timestamp': datetime.now().isoformat()
            })
        
        elif signal in ['sell', 'strong_sell'] and confidence > 0.5:
            # Sell recommendation (for existing positions)
            recommendations.append({
                'action': 'SELL',
                'asset': 'BTC',
                'signal': signal,
                'confidence': confidence,
                'score': overall_signal['score'],
                'exit_price': current_price,
                'reasons': self._get_trade_reasons(analysis),
                'timestamp': datetime.now().isoformat()
            })
        
        return recommendations
    
    def _get_trade_reasons(self, analysis: Dict) -> List[str]:
        """Extract key reasons for trade recommendation"""
        reasons = []
        
        # Technical reasons
        tech = analysis.get('technical_analysis', {})
        if tech:
            tech_signal = tech.get('overall_signal', 'neutral')
            if tech_signal in ['buy', 'strong_buy']:
                reasons.append(f"Technical analysis: {tech_signal}")
            
            indicators = tech.get('indicators', {})
            if indicators.get('rsi', 50) < 30:
                reasons.append("RSI oversold (<30)")
            elif indicators.get('rsi', 50) > 70:
                reasons.append("RSI overbought (>70)")
        
        # ML reasons
        ml = analysis.get('ml_prediction', {})
        if ml and ml.get('direction') in ['buy', 'strong_buy']:
            change_pct = ml.get('predicted_change_pct', 0)
            reasons.append(f"ML predicts +{change_pct:.1f}% move")
        
        # Sentiment reasons
        sentiment = analysis.get('sentiment', {})
        if sentiment:
            fg_index = sentiment.get('fear_greed_index', 50)
            if fg_index < 25:
                reasons.append(f"Extreme fear ({fg_index}/100) - contrarian buy")
            elif fg_index > 75:
                reasons.append(f"Extreme greed ({fg_index}/100) - potential correction")
        
        # Order book reasons
        orderbook = analysis.get('orderbook', {})
        if orderbook:
            bid_vol = orderbook.get('bid_volume', 0)
            ask_vol = orderbook.get('ask_volume', 0)
            if bid_vol > ask_vol * 1.5:
                reasons.append("Strong bid support (1.5x asks)")
            elif ask_vol > bid_vol * 1.5:
                reasons.append("Heavy sell pressure (1.5x bids)")
        
        return reasons[:5]  # Limit to top 5 reasons
    
    def get_prediction_summary(self) -> Dict:
        """Get quick summary of current predictions"""
        analysis = self.analyze_market()
        
        return {
            'current_price': analysis.get('current_price', 0),
            'signal': analysis.get('overall_signal', {}).get('signal', 'neutral'),
            'confidence': analysis.get('overall_signal', {}).get('confidence', 0),
            'score': analysis.get('overall_signal', {}).get('score', 50),
            'ml_predicted_price': analysis.get('ml_prediction', {}).get('predicted_price', 0),
            'ml_predicted_change': analysis.get('ml_prediction', {}).get('predicted_change_pct', 0),
            'fear_greed': analysis.get('sentiment', {}).get('fear_greed_index', 50),
            'models_trained': self.models_trained,
            'timestamp': datetime.now().isoformat()
        }


if __name__ == "__main__":
    # Test the analyzer
    print("Testing Prediction Market Analyzer...")
    
    analyzer = PredictionMarketAnalyzer(auto_train=False)
    
    print("\n1. Market Analysis:")
    analysis = analyzer.analyze_market()
    print(f"   Current Price: ${analysis['current_price']:,.2f}")
    print(f"   Overall Signal: {analysis['overall_signal']['signal']}")
    print(f"   Confidence: {analysis['overall_signal']['confidence']:.1%}")
    print(f"   Score: {analysis['overall_signal']['score']}/100")
    
    print("\n2. Trade Recommendations:")
    recommendations = analyzer.get_trade_recommendations(portfolio_value=1000, risk_level='medium')
    
    if recommendations:
        for rec in recommendations:
            print(f"   {rec['action']} {rec['amount_btc']:.8f} BTC @ ${rec['entry_price']:,.2f}")
            print(f"   Confidence: {rec['confidence']:.1%}")
            print(f"   Stop Loss: ${rec['stop_loss']:,.2f}")
            print(f"   Take Profit: ${rec['take_profit']:,.2f}")
            print(f"   Reasons: {', '.join(rec['reasons'][:3])}")
    else:
        print("   No strong recommendations at this time")
    
    print("\n3. Prediction Summary:")
    summary = analyzer.get_prediction_summary()
    print(f"   Signal: {summary['signal']}")
    print(f"   Fear/Greed: {summary['fear_greed']}/100")
    print(f"   Models Trained: {summary['models_trained']}")

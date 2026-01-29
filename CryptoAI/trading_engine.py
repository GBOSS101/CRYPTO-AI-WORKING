"""
Trading Strategy and Suggestion Engine
Generates intelligent trade suggestions based on analysis and portfolio constraints
"""
from typing import Dict, List, Tuple
from datetime import datetime
import numpy as np
from config import Config
from data_fetcher import LiveDataFetcher
from technical_analyzer import TechnicalAnalyzer

class TradingEngine:
    def __init__(self, wallet_size: float = None):
        self.wallet_size = wallet_size or Config.WALLET_SIZE
        self.data_fetcher = LiveDataFetcher()
        self.analyzer = TechnicalAnalyzer()
        self.risk_profile = Config.get_risk_profile()
        self.suggestions_cache = None
        self.cache_timestamp = None
        self.cache_timeout = 60  # Cache suggestions for 60 seconds
        
    def get_trade_suggestions(self, num_suggestions: int = 5, use_cache: bool = True) -> List[Dict]:
        """
        Generate intelligent trade suggestions for the current market
        """
        # Check cache first
        if use_cache and self.suggestions_cache and self.cache_timestamp:
            from datetime import datetime, timedelta
            if datetime.now() - self.cache_timestamp < timedelta(seconds=self.cache_timeout):
                return self.suggestions_cache[:num_suggestions]
        
        print("🔍 Analyzing market conditions...")
        
        # Use faster analysis subset to prevent timeouts
        coins_to_analyze = Config.FAST_ANALYSIS_CRYPTOS
        
        # Get live prices
        live_prices = self.data_fetcher.get_live_prices(coins_to_analyze)
        
        suggestions = []
        
        for coin_id in coins_to_analyze:
            if coin_id not in live_prices:
                continue
            
            print(f"📊 Analyzing {coin_id}...")
            
            try:
                # Get historical data for analysis (reduced to 14 days for speed)
                market_data = self.data_fetcher.get_market_data(coin_id, days=14)
                
                if market_data.empty:
                    continue
                
                # Perform technical analysis
                analysis = self.analyzer.analyze_coin(market_data)
                
                if 'error' in analysis:
                    continue
            except Exception as e:
                print(f"⚠️ Error analyzing {coin_id}: {e}")
                continue
            
            # Get detailed coin info
            coin_details = live_prices[coin_id]
            
            # Calculate trade suggestion
            suggestion = self._create_trade_suggestion(
                coin_id,
                coin_details,
                analysis
            )
            
            if suggestion:
                suggestions.append(suggestion)
        
        # Sort by score and confidence
        suggestions.sort(key=lambda x: x['score'] * (x['confidence'] / 100), reverse=True)
        
        # Cache the results
        from datetime import datetime
        self.suggestions_cache = suggestions
        self.cache_timestamp = datetime.now()
        
        return suggestions[:num_suggestions]
    
    def _create_trade_suggestion(
        self,
        coin_id: str,
        coin_details: Dict,
        analysis: Dict
    ) -> Dict:
        """
        Create a trade suggestion based on analysis
        """
        current_price = coin_details['price']
        signal = analysis['overall_signal']
        confidence = analysis['confidence']
        
        # Only suggest buys for now (sell suggestions would require portfolio)
        if signal not in ['buy', 'strong_buy']:
            return None
        
        # Calculate position size based on risk profile and confidence
        base_position = self.wallet_size * Config.MIN_POSITION_SIZE
        max_position = self.wallet_size * self.risk_profile['max_position']
        
        # Adjust position size based on confidence
        confidence_factor = confidence / 100
        position_size = base_position + (max_position - base_position) * confidence_factor
        
        # Calculate quantity
        quantity = position_size / current_price
        
        # Calculate stop loss and take profit
        stop_loss = current_price * (1 - Config.STOP_LOSS_PERCENT / 100)
        take_profit = current_price * (1 + Config.TAKE_PROFIT_PERCENT / 100)
        
        # Calculate risk/reward ratio
        risk = current_price - stop_loss
        reward = take_profit - current_price
        risk_reward_ratio = reward / risk if risk > 0 else 0
        
        # Calculate score based on multiple factors
        score = self._calculate_trade_score(
            signal,
            confidence,
            coin_details,
            analysis
        )
        
        return {
            'coin_id': coin_id,
            'symbol': coin_id.upper(),
            'action': 'BUY',
            'signal': signal,
            'confidence': round(confidence, 2),
            'score': round(score, 2),
            'current_price': round(current_price, 6),
            'suggested_investment': round(position_size, 2),
            'quantity': round(quantity, 8),
            'stop_loss': round(stop_loss, 6),
            'take_profit': round(take_profit, 6),
            'risk_reward_ratio': round(risk_reward_ratio, 2),
            'price_change_24h': round(coin_details.get('change_24h', 0), 2),
            'trend': analysis.get('price_trend', 'unknown'),
            'indicators': analysis.get('signals', {}),
            'timestamp': datetime.now().isoformat()
        }
    
    def _calculate_trade_score(
        self,
        signal: str,
        confidence: float,
        coin_details: Dict,
        analysis: Dict
    ) -> float:
        """
        Calculate an overall trade score (0-100)
        """
        score = 0
        
        # Signal strength (0-30 points)
        if signal == 'strong_buy':
            score += 30
        elif signal == 'buy':
            score += 20
        
        # Confidence (0-30 points)
        score += (confidence / 100) * 30
        
        # Trend alignment (0-20 points)
        trend = analysis.get('price_trend', '')
        if trend in ['strong_uptrend', 'uptrend']:
            score += 20
        elif trend == 'sideways':
            score += 10
        
        # Volume (0-10 points)
        volume_24h = coin_details.get('volume_24h', 0)
        market_cap = coin_details.get('market_cap', 1)
        volume_ratio = volume_24h / market_cap if market_cap > 0 else 0
        
        if volume_ratio > 0.1:  # High volume relative to market cap
            score += 10
        elif volume_ratio > 0.05:
            score += 5
        
        # Recent performance (0-10 points)
        change_24h = coin_details.get('change_24h', 0)
        if 0 < change_24h < 10:  # Positive but not overheated
            score += 10
        elif change_24h > 0:
            score += 5
        
        return min(score, 100)
    
    def analyze_opportunity(self, coin_id: str) -> Dict:
        """
        Deep dive analysis of a specific trading opportunity
        """
        # Get live data
        live_prices = self.data_fetcher.get_live_prices([coin_id])
        if coin_id not in live_prices:
            return {'error': 'Could not fetch price data'}
        
        # Get historical data
        market_data = self.data_fetcher.get_market_data(coin_id, days=90)
        if market_data.empty:
            return {'error': 'Could not fetch historical data'}
        
        # Perform analysis
        analysis = self.analyzer.analyze_coin(market_data)
        
        # Get support/resistance levels
        levels = self.analyzer.calculate_support_resistance(market_data)
        
        # Get detailed coin info
        coin_info = self.data_fetcher.get_coin_details(coin_id)
        
        return {
            'coin_info': coin_info,
            'live_data': live_prices[coin_id],
            'technical_analysis': analysis,
            'support_resistance': levels,
            'timestamp': datetime.now().isoformat()
        }
    
    def get_market_sentiment(self) -> Dict:
        """
        Analyze overall market sentiment
        """
        # Get market overview
        overview = self.data_fetcher.get_market_overview()
        
        # Get trending coins
        trending = self.data_fetcher.get_trending_coins(limit=10)
        
        # Get top gainers
        gainers = self.data_fetcher.get_top_gainers(limit=10)
        
        # Analyze sentiment
        market_cap_change = overview.get('market_cap_change_24h', 0)
        
        if market_cap_change > 5:
            sentiment = 'Very Bullish'
        elif market_cap_change > 2:
            sentiment = 'Bullish'
        elif market_cap_change < -5:
            sentiment = 'Very Bearish'
        elif market_cap_change < -2:
            sentiment = 'Bearish'
        else:
            sentiment = 'Neutral'
        
        return {
            'sentiment': sentiment,
            'market_cap_change_24h': round(market_cap_change, 2),
            'overview': overview,
            'trending_coins': trending,
            'top_gainers': gainers,
            'timestamp': datetime.now().isoformat()
        }

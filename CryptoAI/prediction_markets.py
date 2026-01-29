"""
Prediction Markets Integration Module
Fetches odds and data from major crypto prediction markets
Identifies arbitrage opportunities and integrates with ML predictions
"""
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import time
import json
import os


class MarketOutcome(Enum):
    """Possible market outcomes"""
    YES = "yes"
    NO = "no"
    HIGHER = "higher"
    LOWER = "lower"
    BULLISH = "bullish"
    BEARISH = "bearish"


@dataclass
class PredictionMarket:
    """Represents a prediction market"""
    id: str
    platform: str
    title: str
    description: str
    category: str
    outcomes: List[Dict[str, Any]]
    volume: float
    liquidity: float
    end_date: datetime
    created_at: datetime
    url: str
    
    @property
    def best_yes_price(self) -> float:
        """Get the best YES price (implied probability)"""
        for outcome in self.outcomes:
            if outcome.get('name', '').lower() in ['yes', 'higher', 'bullish']:
                return outcome.get('price', 0.5)
        return 0.5
    
    @property
    def best_no_price(self) -> float:
        """Get the best NO price"""
        for outcome in self.outcomes:
            if outcome.get('name', '').lower() in ['no', 'lower', 'bearish']:
                return outcome.get('price', 0.5)
        return 1 - self.best_yes_price
    
    @property
    def implied_probability(self) -> float:
        """Get implied probability of YES outcome"""
        return self.best_yes_price


@dataclass
class ArbitrageOpportunity:
    """Represents an arbitrage opportunity between markets or predictions"""
    market: PredictionMarket
    our_prediction: float  # Our ML model's probability
    market_probability: float  # Market's implied probability
    edge: float  # Difference (positive = we think YES is underpriced)
    confidence: float
    recommended_position: str  # "YES" or "NO"
    expected_value: float
    reasoning: str


class PredictionMarketsClient:
    """
    Client for fetching data from prediction market platforms
    Supports: Polymarket, Kalshi, Metaculus, PredictIt
    """
    
    def __init__(self):
        self.session = self._build_session()
        self.cache: Dict[str, Tuple[Any, float]] = {}
        self.cache_timeout = 60  # 1 minute
        
        # API endpoints
        self.endpoints = {
            'polymarket': 'https://clob.polymarket.com',
            'polymarket_gamma': 'https://gamma-api.polymarket.com',
            'kalshi': 'https://trading-api.kalshi.com/trade-api/v2',
            'metaculus': 'https://www.metaculus.com/api2',
        }
        
    def _build_session(self) -> requests.Session:
        """Build requests session with retry logic"""
        session = requests.Session()
        retries = Retry(
            total=3,
            backoff_factor=1.0,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retries)
        session.mount("https://", adapter)
        return session
    
    def _get_cached(self, key: str) -> Optional[Any]:
        """Get cached data if not expired"""
        if key in self.cache:
            data, timestamp = self.cache[key]
            if time.time() - timestamp < self.cache_timeout:
                return data
        return None
    
    def _set_cache(self, key: str, data: Any):
        """Set cache data"""
        self.cache[key] = (data, time.time())
    
    # =========================================================================
    # POLYMARKET
    # =========================================================================
    
    def get_polymarket_markets(self, category: str = "crypto") -> List[PredictionMarket]:
        """
        Fetch markets from Polymarket
        
        Args:
            category: Market category filter
            
        Returns:
            List of PredictionMarket objects
        """
        cache_key = f"polymarket_{category}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        try:
            # Fetch from Polymarket Gamma API
            response = self.session.get(
                f"{self.endpoints['polymarket_gamma']}/markets",
                params={
                    'active': 'true',
                    'closed': 'false',
                    'limit': 100
                },
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            markets = []
            for item in data:
                # Filter for crypto-related markets
                title = item.get('question', '').lower()
                tags = [t.lower() for t in item.get('tags', [])]
                
                is_crypto = any(kw in title for kw in ['bitcoin', 'btc', 'ethereum', 'eth', 'crypto', 'solana', 'sol'])
                is_crypto = is_crypto or 'crypto' in tags or 'cryptocurrency' in tags
                
                if category == "crypto" and not is_crypto:
                    continue
                
                try:
                    outcomes = []
                    for token in item.get('tokens', []):
                        outcomes.append({
                            'name': token.get('outcome', 'Unknown'),
                            'price': float(token.get('price', 0.5)),
                            'token_id': token.get('token_id', '')
                        })
                    
                    market = PredictionMarket(
                        id=item.get('condition_id', ''),
                        platform='polymarket',
                        title=item.get('question', ''),
                        description=item.get('description', ''),
                        category='crypto' if is_crypto else 'other',
                        outcomes=outcomes,
                        volume=float(item.get('volume', 0)),
                        liquidity=float(item.get('liquidity', 0)),
                        end_date=datetime.fromisoformat(item.get('end_date_iso', datetime.now().isoformat()).replace('Z', '+00:00')),
                        created_at=datetime.fromisoformat(item.get('created_at', datetime.now().isoformat()).replace('Z', '+00:00')),
                        url=f"https://polymarket.com/event/{item.get('slug', '')}"
                    )
                    markets.append(market)
                except Exception as e:
                    continue
            
            self._set_cache(cache_key, markets)
            return markets
            
        except Exception as e:
            print(f"⚠️ Polymarket fetch error: {e}")
            return []
    
    def get_polymarket_btc_markets(self) -> List[PredictionMarket]:
        """Get Bitcoin-specific prediction markets"""
        all_markets = self.get_polymarket_markets("crypto")
        btc_markets = [
            m for m in all_markets 
            if any(kw in m.title.lower() for kw in ['bitcoin', 'btc'])
        ]
        return btc_markets
    
    # =========================================================================
    # KALSHI
    # =========================================================================
    
    def get_kalshi_markets(self, series: str = "KXBTC") -> List[PredictionMarket]:
        """
        Fetch markets from Kalshi
        
        Args:
            series: Market series ticker (KXBTC for Bitcoin)
            
        Returns:
            List of PredictionMarket objects
        """
        cache_key = f"kalshi_{series}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        try:
            response = self.session.get(
                f"{self.endpoints['kalshi']}/markets",
                params={
                    'series_ticker': series,
                    'status': 'open'
                },
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            markets = []
            for item in data.get('markets', []):
                try:
                    yes_price = item.get('yes_bid', 50) / 100
                    no_price = item.get('no_bid', 50) / 100
                    
                    market = PredictionMarket(
                        id=item.get('ticker', ''),
                        platform='kalshi',
                        title=item.get('title', ''),
                        description=item.get('subtitle', ''),
                        category='crypto',
                        outcomes=[
                            {'name': 'Yes', 'price': yes_price},
                            {'name': 'No', 'price': no_price}
                        ],
                        volume=float(item.get('volume', 0)),
                        liquidity=float(item.get('open_interest', 0)),
                        end_date=datetime.fromisoformat(item.get('close_time', datetime.now().isoformat()).replace('Z', '+00:00')),
                        created_at=datetime.now(),
                        url=f"https://kalshi.com/markets/{item.get('ticker', '')}"
                    )
                    markets.append(market)
                except Exception:
                    continue
            
            self._set_cache(cache_key, markets)
            return markets
            
        except Exception as e:
            print(f"⚠️ Kalshi fetch error: {e}")
            return []
    
    # =========================================================================
    # METACULUS (Free, community predictions)
    # =========================================================================
    
    def get_metaculus_questions(self, topic: str = "crypto") -> List[PredictionMarket]:
        """
        Fetch questions from Metaculus
        
        Args:
            topic: Topic to search for
            
        Returns:
            List of PredictionMarket objects
        """
        cache_key = f"metaculus_{topic}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        try:
            response = self.session.get(
                f"{self.endpoints['metaculus']}/questions/",
                params={
                    'search': topic,
                    'status': 'open',
                    'type': 'forecast',
                    'limit': 50
                },
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            markets = []
            for item in data.get('results', []):
                try:
                    # Get community prediction
                    prediction = item.get('community_prediction', {})
                    prob = prediction.get('full', {}).get('q2', 0.5) if prediction else 0.5
                    
                    market = PredictionMarket(
                        id=str(item.get('id', '')),
                        platform='metaculus',
                        title=item.get('title', ''),
                        description=item.get('description', '')[:500],
                        category='crypto',
                        outcomes=[
                            {'name': 'Yes', 'price': prob},
                            {'name': 'No', 'price': 1 - prob}
                        ],
                        volume=item.get('number_of_predictions', 0),
                        liquidity=0,
                        end_date=datetime.fromisoformat(item.get('resolve_time', datetime.now().isoformat()).replace('Z', '+00:00')) if item.get('resolve_time') else datetime.now() + timedelta(days=30),
                        created_at=datetime.fromisoformat(item.get('created_time', datetime.now().isoformat()).replace('Z', '+00:00')),
                        url=f"https://www.metaculus.com/questions/{item.get('id')}/"
                    )
                    markets.append(market)
                except Exception:
                    continue
            
            self._set_cache(cache_key, markets)
            return markets
            
        except Exception as e:
            print(f"⚠️ Metaculus fetch error: {e}")
            return []
    
    # =========================================================================
    # AGGREGATED DATA
    # =========================================================================
    
    def get_all_crypto_markets(self) -> List[PredictionMarket]:
        """Get all crypto prediction markets from all platforms"""
        all_markets = []
        
        # Polymarket
        all_markets.extend(self.get_polymarket_markets("crypto"))
        
        # Kalshi Bitcoin markets
        all_markets.extend(self.get_kalshi_markets("KXBTC"))
        
        # Metaculus crypto questions
        all_markets.extend(self.get_metaculus_questions("bitcoin"))
        all_markets.extend(self.get_metaculus_questions("cryptocurrency"))
        
        # Sort by volume/liquidity
        all_markets.sort(key=lambda m: m.volume + m.liquidity, reverse=True)
        
        return all_markets
    
    def get_btc_price_markets(self) -> List[PredictionMarket]:
        """Get markets specifically about Bitcoin price"""
        all_markets = self.get_all_crypto_markets()
        
        price_keywords = ['price', '$', 'above', 'below', 'reach', 'hit', 'exceed']
        btc_keywords = ['bitcoin', 'btc']
        
        price_markets = []
        for market in all_markets:
            title_lower = market.title.lower()
            has_btc = any(kw in title_lower for kw in btc_keywords)
            has_price = any(kw in title_lower for kw in price_keywords)
            
            if has_btc and has_price:
                price_markets.append(market)
        
        return price_markets


class PredictionMarketAnalyzer:
    """
    Analyzes prediction markets and finds opportunities
    Integrates with ML predictions
    """
    
    def __init__(self, ml_engine=None):
        self.client = PredictionMarketsClient()
        self.ml_engine = ml_engine
        
    def find_arbitrage_opportunities(
        self,
        our_prediction: float,
        our_confidence: float = 0.7,
        min_edge: float = 0.10
    ) -> List[ArbitrageOpportunity]:
        """
        Find arbitrage opportunities between our predictions and markets
        
        Args:
            our_prediction: Our model's probability (0-1) for bullish outcome
            our_confidence: Confidence in our prediction (0-1)
            min_edge: Minimum edge required to flag opportunity
            
        Returns:
            List of arbitrage opportunities
        """
        opportunities = []
        markets = self.client.get_btc_price_markets()
        
        for market in markets:
            market_prob = market.implied_probability
            edge = our_prediction - market_prob
            
            # Only flag if edge exceeds minimum
            if abs(edge) >= min_edge:
                if edge > 0:
                    # We think YES is underpriced
                    recommended = "YES"
                    expected_value = edge * our_confidence
                    reasoning = f"Market prices YES at {market_prob:.1%}, we predict {our_prediction:.1%}"
                else:
                    # We think NO is underpriced
                    recommended = "NO"
                    expected_value = abs(edge) * our_confidence
                    reasoning = f"Market prices NO at {1-market_prob:.1%}, we predict {1-our_prediction:.1%}"
                
                opportunity = ArbitrageOpportunity(
                    market=market,
                    our_prediction=our_prediction,
                    market_probability=market_prob,
                    edge=edge,
                    confidence=our_confidence,
                    recommended_position=recommended,
                    expected_value=expected_value,
                    reasoning=reasoning
                )
                opportunities.append(opportunity)
        
        # Sort by expected value
        opportunities.sort(key=lambda o: o.expected_value, reverse=True)
        
        return opportunities
    
    def get_market_consensus(self) -> Dict[str, Any]:
        """
        Get the consensus view from prediction markets
        
        Returns:
            Dict with consensus data
        """
        btc_markets = self.client.get_btc_price_markets()
        
        if not btc_markets:
            return {
                'consensus': 'neutral',
                'average_bullish_probability': 0.5,
                'num_markets': 0,
                'markets': []
            }
        
        # Calculate weighted average by volume
        total_volume = sum(m.volume for m in btc_markets) or 1
        weighted_prob = sum(
            m.implied_probability * (m.volume / total_volume)
            for m in btc_markets
        )
        
        # Determine consensus
        if weighted_prob > 0.65:
            consensus = 'strongly_bullish'
        elif weighted_prob > 0.55:
            consensus = 'bullish'
        elif weighted_prob < 0.35:
            consensus = 'strongly_bearish'
        elif weighted_prob < 0.45:
            consensus = 'bearish'
        else:
            consensus = 'neutral'
        
        return {
            'consensus': consensus,
            'average_bullish_probability': weighted_prob,
            'num_markets': len(btc_markets),
            'total_volume': total_volume,
            'markets': [
                {
                    'platform': m.platform,
                    'title': m.title,
                    'probability': m.implied_probability,
                    'volume': m.volume,
                    'url': m.url
                }
                for m in btc_markets[:10]  # Top 10 by volume
            ]
        }
    
    def generate_prediction_report(self, our_bullish_prob: float = 0.5) -> Dict[str, Any]:
        """
        Generate a comprehensive prediction market report
        
        Args:
            our_bullish_prob: Our ML model's bullish probability
            
        Returns:
            Comprehensive report dict
        """
        consensus = self.get_market_consensus()
        opportunities = self.find_arbitrage_opportunities(our_bullish_prob)
        
        # All markets summary
        all_markets = self.client.get_all_crypto_markets()
        
        return {
            'timestamp': datetime.now().isoformat(),
            'our_prediction': {
                'bullish_probability': our_bullish_prob,
                'bearish_probability': 1 - our_bullish_prob,
                'signal': 'bullish' if our_bullish_prob > 0.55 else ('bearish' if our_bullish_prob < 0.45 else 'neutral')
            },
            'market_consensus': consensus,
            'agreement': abs(our_bullish_prob - consensus['average_bullish_probability']) < 0.1,
            'arbitrage_opportunities': [
                {
                    'platform': o.market.platform,
                    'market': o.market.title,
                    'edge': f"{o.edge:+.1%}",
                    'recommended': o.recommended_position,
                    'expected_value': f"{o.expected_value:.1%}",
                    'reasoning': o.reasoning,
                    'url': o.market.url
                }
                for o in opportunities[:5]  # Top 5 opportunities
            ],
            'all_markets_count': len(all_markets),
            'platforms': {
                'polymarket': len([m for m in all_markets if m.platform == 'polymarket']),
                'kalshi': len([m for m in all_markets if m.platform == 'kalshi']),
                'metaculus': len([m for m in all_markets if m.platform == 'metaculus'])
            }
        }


# Integration with existing prediction system
def integrate_with_ml_engine():
    """
    Example integration with existing ML prediction engine
    """
    try:
        from ml_prediction_engine import MLPredictionEngine
        
        # Initialize
        ml_engine = MLPredictionEngine()
        market_analyzer = PredictionMarketAnalyzer(ml_engine=ml_engine)
        
        # Get ML prediction
        ml_prediction = ml_engine.predict()
        bullish_prob = ml_prediction.get('probability_up', 0.5)
        
        # Generate combined report
        report = market_analyzer.generate_prediction_report(bullish_prob)
        
        return report
        
    except ImportError:
        print("⚠️ ML engine not available, using market data only")
        analyzer = PredictionMarketAnalyzer()
        return analyzer.generate_prediction_report(0.5)


if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════╗
║           🎯 Crypto Prediction Markets Analyzer              ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    analyzer = PredictionMarketAnalyzer()
    
    # Get market consensus
    print("📊 Fetching prediction market data...")
    consensus = analyzer.get_market_consensus()
    
    print(f"\n🎯 Market Consensus: {consensus['consensus'].upper()}")
    print(f"   Bullish Probability: {consensus['average_bullish_probability']:.1%}")
    print(f"   Markets Analyzed: {consensus['num_markets']}")
    
    if consensus['markets']:
        print("\n📈 Top Markets:")
        for i, m in enumerate(consensus['markets'][:5], 1):
            print(f"   {i}. [{m['platform']}] {m['title'][:60]}...")
            print(f"      Probability: {m['probability']:.1%} | Volume: ${m['volume']:,.0f}")
    
    # Find arbitrage opportunities (assuming 60% bullish prediction)
    print("\n🔍 Checking for arbitrage opportunities...")
    opportunities = analyzer.find_arbitrage_opportunities(0.60, 0.75, 0.05)
    
    if opportunities:
        print(f"\n💰 Found {len(opportunities)} opportunities:")
        for i, opp in enumerate(opportunities[:3], 1):
            print(f"\n   {i}. {opp.market.title[:50]}...")
            print(f"      Platform: {opp.market.platform}")
            print(f"      Market: {opp.market_probability:.1%} | Ours: {opp.our_prediction:.1%}")
            print(f"      Edge: {opp.edge:+.1%} → {opp.recommended_position}")
            print(f"      EV: {opp.expected_value:.1%}")
    else:
        print("   No significant arbitrage opportunities found")
    
    print("\n" + "="*60)

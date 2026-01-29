"""
Prediction Market Data Fetcher for Coinbase
Fetches market data, order book, and prediction signals for BTC
"""
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
import time
import json
import hmac
import hashlib
import base64
from functools import lru_cache
import os
from dotenv import load_dotenv

# Coinbase Advanced Trade SDK
try:
    from coinbase.rest import RESTClient
    COINBASE_SDK_AVAILABLE = True
except ImportError:
    COINBASE_SDK_AVAILABLE = False
    print("⚠️ coinbase-advanced-py not installed. Install with: pip install coinbase-advanced-py")

load_dotenv()


class PredictionMarketFetcher:
    """Fetches and processes data for BTC prediction markets"""
    
    def __init__(self, cache_timeout: int = 30):
        """
        Initialize the prediction market fetcher
        
        Args:
            cache_timeout: Cache timeout in seconds (default 30s)
        """
        self.cache_timeout = cache_timeout
        self.cache = {}
        self.request_timeout = 10
        self.session = self._build_session()
        
        # Coinbase API Authentication
        self.coinbase_api_key = os.getenv('COINBASE_API_KEY', '')
        self.coinbase_private_key = os.getenv('COINBASE_PRIVATE_KEY', '')
        
        # Initialize Coinbase Advanced Trade SDK
        self.coinbase_client = None
        if COINBASE_SDK_AVAILABLE and self.coinbase_api_key and self.coinbase_private_key:
            try:
                self.coinbase_client = RESTClient(
                    api_key=self.coinbase_api_key,
                    api_secret=self.coinbase_private_key
                )
                print(f"✅ Coinbase Advanced Trade: AUTHENTICATED")
            except Exception as e:
                print(f"⚠️ Coinbase authentication failed: {e}")
        
        # FREE Open-Source API Endpoints (No Auth Required)
        self.coinbase_api_base = "https://api.exchange.coinbase.com"
        self.coinbase_pro_base = "https://api.pro.coinbase.com"
        self.coinbase_advanced = "https://api.coinbase.com/api/v3/brokerage"  # Advanced Trade
        
        # Alternative FREE data sources
        self.cryptocompare_base = "https://min-api.cryptocompare.com/data"
        self.livecoinwatch_base = "https://api.livecoinwatch.com"
        self.coinmarketcap_base = "https://pro-api.coinmarketcap.com/v1"  # Free tier: 10k calls/month
        self.coincodex_base = "https://coincodex.com/api"
        
        auth_status = "Authenticated (Advanced Trade SDK)" if self.coinbase_client else "Public (Free APIs)"
        print(f"📡 Initialized Coinbase API: {auth_status}")
        print("  ✓ Coinbase Advanced Trade (Primary)")
        print("  ✓ CryptoCompare (Backup #1)")
        print("  ✓ CoinMarketCap Free Tier (Backup #2)")
        print("  ✓ LiveCoinWatch (Backup #3)")

    def _build_session(self) -> requests.Session:
        session = requests.Session()
        retries = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"]
        )
        adapter = HTTPAdapter(max_retries=retries)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session
        
    def _get_cached_data(self, cache_key: str) -> Optional[Any]:
        """Get data from cache if valid"""
        if cache_key in self.cache:
            data, timestamp = self.cache[cache_key]
            if time.time() - timestamp < self.cache_timeout:
                return data
        return None
    
    def _set_cache(self, cache_key: str, data: Any):
        """Set data in cache with timestamp"""
        self.cache[cache_key] = (data, time.time())

    def _safe_float(self, value: Any) -> Optional[float]:
        """Safely convert values to float."""
        try:
            if value is None:
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

    def _safe_int(self, value: Any) -> Optional[int]:
        """Safely convert values to int."""
        try:
            if value is None:
                return None
            return int(value)
        except (TypeError, ValueError):
            return None
    
    def get_live_btc_price(self) -> float:
        """
        Get current BTC price with MAXIMUM accuracy using authenticated API
        
        Returns:
            Current BTC price in USD (live, sub-second accuracy)
        """
        # Try multiple sources simultaneously and average for accuracy
        prices = []
        
        # Source 1: Coinbase Advanced Trade SDK (AUTHENTICATED - NO 503 ERRORS!)
        if self.coinbase_client:
            try:
                ticker = self.coinbase_client.get_product(product_id="BTC-USD")
                if hasattr(ticker, 'price'):
                    price = float(ticker.price)
                elif isinstance(ticker, dict):
                    price = float(ticker.get('price', 0))
                else:
                    # Fallback: get from candles
                    candles_response = self.coinbase_client.get_candles(
                        product_id="BTC-USD",
                        start=str(int(time.time()) - 300),
                        end=str(int(time.time())),
                        granularity='ONE_MINUTE'
                    )
                    if hasattr(candles_response, 'candles') and candles_response.candles:
                        close_price = self._safe_float(candles_response.candles[-1].close)
                        price = close_price if close_price is not None else 0
                    else:
                        price = 0
                
                if price > 0:
                    prices.append(price)
            except Exception as e:
                print(f"⚠️ Coinbase SDK price error: {e}")
        
        # Source 2: Coinbase Public API (backup)
        try:
            url = f"{self.coinbase_api_base}/products/BTC-USD/ticker"
            response = self.session.get(url, timeout=self.request_timeout)
            response.raise_for_status()
            data = response.json()
            price = float(data.get('price', 0))
            if price > 0:
                prices.append(price)
        except:
            pass
        
        # Source 3: CryptoCompare (backup)
        try:
            url = f"{self.cryptocompare_base}/price"
            params = {'fsym': 'BTC', 'tsyms': 'USD'}
            response = self.session.get(url, params=params, timeout=self.request_timeout)
            response.raise_for_status()
            data = response.json()
            price = float(data.get('USD', 0))
            if price > 0:
                prices.append(price)
        except:
            pass
        
        # Return median price for accuracy (resistant to outliers)
        if prices:
            prices.sort()
            if len(prices) == 1:
                return prices[0]
            elif len(prices) == 2:
                return (prices[0] + prices[1]) / 2
            else:
                # Return median
                mid = len(prices) // 2
                return prices[mid]
        
        # Fallback only if all sources fail
        return 0.0
    
    def get_btc_orderbook(self, level: int = 2) -> Dict:
        """
        Get BTC order book data from Coinbase
        
        Args:
            level: Order book level (1=best bid/ask, 2=top 50, 3=full)
        
        Returns:
            Dict with bids, asks, and market depth
        """
        cache_key = f'orderbook_{level}'
        cached = self._get_cached_data(cache_key)
        if cached:
            return cached
        
        try:
            url = f"{self.coinbase_pro_base}/products/BTC-USD/book?level={level}"
            response = self.session.get(url, timeout=self.request_timeout)
            response.raise_for_status()
            
            data = response.json()
            
            # Parse order book
            orderbook = {
                'bids': [[float(price), float(size)] for price, size, _ in data.get('bids', [])],
                'asks': [[float(price), float(size)] for price, size, _ in data.get('asks', [])],
                'timestamp': datetime.now().isoformat(),
                'spread': 0.0,
                'mid_price': 0.0,
                'total_bid_volume': 0.0,
                'total_ask_volume': 0.0
            }
            
            if orderbook['bids'] and orderbook['asks']:
                best_bid = orderbook['bids'][0][0]
                best_ask = orderbook['asks'][0][0]
                orderbook['spread'] = best_ask - best_bid
                orderbook['mid_price'] = (best_bid + best_ask) / 2
                orderbook['total_bid_volume'] = sum(size for _, size in orderbook['bids'])
                orderbook['total_ask_volume'] = sum(size for _, size in orderbook['asks'])
            
            self._set_cache(cache_key, orderbook)
            return orderbook
            
        except Exception as e:
            print(f"Error fetching order book: {e}")
            return {
                'bids': [], 'asks': [], 'spread': 0.0, 'mid_price': 0.0,
                'total_bid_volume': 0.0, 'total_ask_volume': 0.0,
                'timestamp': datetime.now().isoformat()
            }
    
    def get_btc_historical_data(self, days: int = 30, interval: str = '1h') -> pd.DataFrame:
        """
        Get historical BTC price data using Authenticated Coinbase Advanced Trade SDK
        
        Strategy: Coinbase Advanced Trade SDK → CryptoCompare → CoinMarketCap → Mock
        
        Args:
            days: Number of days of historical data
            interval: Data interval ('1h', '4h', '1d')
        
        Returns:
            DataFrame with OHLCV data
        """
        cache_key = f'historical_{days}_{interval}'
        cached = self._get_cached_data(cache_key)
        if cached:
            return pd.DataFrame(cached)
        
        # PRIMARY: Coinbase Advanced Trade SDK (AUTHENTICATED - No rate limits!)
        if self.coinbase_client:
            try:
                # Coinbase SDK uses granularity strings
                granularity_map = {
                    '1h': 'ONE_HOUR',
                    '4h': 'FOUR_HOUR', 
                    '1d': 'ONE_DAY'
                }
                granularity = granularity_map.get(interval, 'ONE_HOUR')
                
                # Calculate time range (Coinbase accepts Unix timestamps)
                end_time = int(datetime.now().timestamp())
                start_time = int((datetime.now() - timedelta(days=days)).timestamp())
                
                # Coinbase API limit: 350 candles per request
                # Calculate expected candles
                hours_per_candle = {'ONE_HOUR': 1, 'FOUR_HOUR': 4, 'ONE_DAY': 24}
                hours_requested = days * 24
                expected_candles = hours_requested / hours_per_candle.get(granularity, 1)
                
                # If over limit, use larger granularity or reduce days
                if expected_candles > 350:
                    if granularity == 'ONE_HOUR':
                        # Switch to 4-hour candles for large requests
                        granularity = 'FOUR_HOUR'
                        print(f"📊 Switching to 4H candles (requested {days}d = {expected_candles:.0f} candles > 350 limit)")
                    elif granularity == 'FOUR_HOUR':
                        # Switch to daily for very large requests
                        granularity = 'ONE_DAY'
                        print(f"📊 Switching to 1D candles (requested {days}d = {expected_candles:.0f} candles > 350 limit)")
                    else:
                        # Reduce days to fit within limit
                        max_days = int(350 * hours_per_candle.get(granularity, 1) / 24)
                        start_time = int((datetime.now() - timedelta(days=max_days)).timestamp())
                        print(f"📊 Reducing to {max_days} days to fit 350 candle limit")
                
                # Use authenticated SDK to get candles (NO 503 ERRORS!)
                candles_response = self.coinbase_client.get_candles(
                    product_id="BTC-USD",
                    start=str(start_time),
                    end=str(end_time),
                    granularity=granularity
                )
                
                # Parse response - SDK returns object, not dict
                candles = []
                if hasattr(candles_response, 'candles'):
                    candles = candles_response.candles
                elif isinstance(candles_response, dict):
                    candles = candles_response.get('candles', [])
                
                if candles:
                    # Convert to DataFrame
                    df_data = []
                    for candle in candles:
                        # Handle both dict and object attribute access
                        if hasattr(candle, 'start'):
                            start_ts = self._safe_int(candle.start)
                            open_price = self._safe_float(candle.open)
                            high_price = self._safe_float(candle.high)
                            low_price = self._safe_float(candle.low)
                            close_price = self._safe_float(candle.close)
                            volume = self._safe_float(candle.volume)

                            if start_ts is None or close_price is None:
                                continue

                            df_data.append({
                                'timestamp': pd.to_datetime(start_ts, unit='s'),
                                'open': open_price if open_price is not None else close_price,
                                'high': high_price if high_price is not None else close_price,
                                'low': low_price if low_price is not None else close_price,
                                'close': close_price,
                                'volume': volume if volume is not None else 0.0,
                                'price': close_price
                            })
                        elif isinstance(candle, dict):
                            start_ts = self._safe_int(candle.get('start'))
                            close_price = self._safe_float(candle.get('close'))
                            if start_ts is None or close_price is None:
                                continue

                            open_price = self._safe_float(candle.get('open'))
                            high_price = self._safe_float(candle.get('high'))
                            low_price = self._safe_float(candle.get('low'))
                            volume = self._safe_float(candle.get('volume'))

                            df_data.append({
                                'timestamp': pd.to_datetime(start_ts, unit='s'),
                                'open': open_price if open_price is not None else close_price,
                                'high': high_price if high_price is not None else close_price,
                                'low': low_price if low_price is not None else close_price,
                                'close': close_price,
                                'volume': volume if volume is not None else 0.0,
                                'price': close_price
                            })
                    
                    df = pd.DataFrame(df_data)
                    df = df.sort_values('timestamp').set_index('timestamp')
                    
                    print(f"✅ Fetched {len(df)} candles from Coinbase Advanced Trade SDK (AUTHENTICATED)")
                    
                    # Cache for next request
                    self._set_cache(cache_key, df.reset_index().to_dict('records'))
                    return df
                
            except Exception as e:
                print(f"⚠️ Coinbase SDK error: {e}")
        
        # FALLBACK: Try public API if SDK fails
        try:
            # Coinbase uses granularity in seconds
            granularity_map = {'1h': 3600, '4h': 14400, '1d': 86400}
            granularity = granularity_map.get(interval, 3600)
            
            # Calculate time range
            end_time = datetime.now()
            start_time = end_time - timedelta(days=days)
            
            # Try public endpoint
            url = f"{self.coinbase_pro_base}/products/BTC-USD/candles"
            params = {
                'start': start_time.isoformat(),
                'end': end_time.isoformat(),
                'granularity': granularity
            }
            
            response = self.session.get(url, params=params, timeout=self.request_timeout)
            response.raise_for_status()
            data = response.json()
            
            # Coinbase returns: [time, low, high, open, close, volume]
            df = pd.DataFrame(data, columns=['timestamp', 'low', 'high', 'open', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
            df['price'] = df['close']
            df = df[['timestamp', 'open', 'high', 'low', 'close', 'price', 'volume']]
            df = df.sort_values('timestamp').set_index('timestamp')
            
            print(f"✅ Fetched {len(df)} candles from Coinbase Public API")
            
            # Cache for next request
            self._set_cache(cache_key, df.reset_index().to_dict('records'))
            return df
            
        except Exception as e:
            print(f"⚠️ Coinbase Public API error: {e}")
            
            # FALLBACK 1: CryptoCompare (FREE, reliable)
            try:
                print("🔄 Trying CryptoCompare (FREE)...")
                
                # Determine endpoint based on interval
                if '1h' in interval:
                    endpoint = 'histohour'
                    limit = min(days * 24, 2000)
                elif '4h' in interval:
                    endpoint = 'histohour'
                    limit = min(days * 6, 2000)
                else:
                    endpoint = 'histoday'
                    limit = min(days, 2000)
                
                url = f"{self.cryptocompare_base}/v2/{endpoint}"
                params = {'fsym': 'BTC', 'tsym': 'USD', 'limit': limit}
                
                response = self.session.get(url, params=params, timeout=self.request_timeout)
                response.raise_for_status()
                result = response.json()
                
                if result.get('Response') == 'Success':
                    candles = result['Data']['Data']
                    df = pd.DataFrame(candles)
                    df['timestamp'] = pd.to_datetime(df['time'], unit='s')
                    df = df.rename(columns={'volumeto': 'volume'})
                    df['price'] = df['close']
                    df = df[['timestamp', 'open', 'high', 'low', 'close', 'price', 'volume']]
                    df = df.set_index('timestamp')
                    
                    print(f"✅ Fetched {len(df)} candles from CryptoCompare (FREE)")
                    self._set_cache(cache_key, df.reset_index().to_dict('records'))
                    return df

            except Exception as e2:
                print(f"⚠️ CryptoCompare error: {e2}")
            
            # FALLBACK 2: CoinMarketCap (FREE tier: 10k calls/month)
            try:
                print("🔄 Trying CoinMarketCap (FREE tier)...")
                
                # CoinMarketCap historical endpoint (may need API key for high volume)
                # Using quotes endpoint for recent data
                url = "https://api.coinmarketcap.com/data-api/v3/cryptocurrency/historical"
                params = {
                    'id': 1,  # BTC ID
                    'convertId': 2781,  # USD
                    'timeStart': int((datetime.now() - timedelta(days=days)).timestamp()),
                    'timeEnd': int(datetime.now().timestamp())
                }
                
                response = self.session.get(url, params=params, timeout=self.request_timeout)
                response.raise_for_status()
                result = response.json()
                
                if result.get('data', {}).get('quotes'):
                    quotes = result['data']['quotes']
                    df = pd.DataFrame(quotes)
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                    
                    # Extract price data
                    df['open'] = df['quote'].apply(lambda x: x.get('open', 0))
                    df['high'] = df['quote'].apply(lambda x: x.get('high', 0))
                    df['low'] = df['quote'].apply(lambda x: x.get('low', 0))
                    df['close'] = df['quote'].apply(lambda x: x.get('close', 0))
                    df['volume'] = df['quote'].apply(lambda x: x.get('volume', 0))
                    df['price'] = df['close']
                    
                    df = df[['timestamp', 'open', 'high', 'low', 'close', 'price', 'volume']]
                    df = df.set_index('timestamp')
                    
                    print(f"✅ Fetched {len(df)} candles from CoinMarketCap (FREE)")
                    self._set_cache(cache_key, df.reset_index().to_dict('records'))
                    return df
                    
            except Exception as e3:
                print(f"⚠️ CoinMarketCap error: {e3}")
            
            # FALLBACK 3: LiveCoinWatch (FREE: 5000 req/day)
            try:
                print("🔄 Trying LiveCoinWatch (FREE)...")
                
                url = f"{self.livecoinwatch_base}/coins/single/history"
                payload = {
                    'currency': 'USD',
                    'code': 'BTC',
                    'start': int((datetime.now() - timedelta(days=days)).timestamp() * 1000),
                    'end': int(datetime.now().timestamp() * 1000),
                    'meta': True
                }
                headers = {'content-type': 'application/json'}
                
                response = self.session.post(url, json=payload, headers=headers, timeout=self.request_timeout)
                response.raise_for_status()
                result = response.json()
                
                if result.get('history'):
                    history = result['history']
                    df = pd.DataFrame(history)
                    df['timestamp'] = pd.to_datetime(df['date'], unit='ms')
                    df['open'] = df['rate']
                    df['high'] = df['rate'] * 1.01  # Approximation
                    df['low'] = df['rate'] * 0.99   # Approximation
                    df['close'] = df['rate']
                    df['price'] = df['rate']
                    df['volume'] = df.get('volume', 0)
                    
                    df = df[['timestamp', 'open', 'high', 'low', 'close', 'price', 'volume']]
                    df = df.set_index('timestamp')
                    
                    print(f"✅ Fetched {len(df)} candles from LiveCoinWatch (FREE)")
                    self._set_cache(cache_key, df.reset_index().to_dict('records'))
                    return df
                    
            except Exception as e4:
                print(f"⚠️ LiveCoinWatch error: {e4}")
            
            # LAST RESORT: Generate realistic mock data
            print("🎲 All FREE APIs failed - using mock data for testing")
            return self._generate_mock_data(days)
    
    def _generate_mock_data(self, days: int = 30) -> pd.DataFrame:
        """
        Generate mock BTC price data for testing when APIs are unavailable
        
        Args:
            days: Number of days to generate
        
        Returns:
            DataFrame with synthetic OHLCV data
        """
        # Generate timestamps
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        timestamps = pd.date_range(start=start_date, end=end_date, freq='1h')
        
        # Generate realistic price movement (random walk around $104,000)
        np.random.seed(42)  # Reproducible
        base_price = 104000
        returns = np.random.normal(0.0002, 0.01, len(timestamps))  # Small mean, realistic volatility
        prices = base_price * np.exp(np.cumsum(returns))
        
        # Create OHLCV data
        df = pd.DataFrame({
            'timestamp': timestamps,
            'open': prices * (1 + np.random.uniform(-0.002, 0.002, len(timestamps))),
            'high': prices * (1 + np.random.uniform(0.001, 0.01, len(timestamps))),
            'low': prices * (1 - np.random.uniform(0.001, 0.01, len(timestamps))),
            'close': prices,
            'price': prices,
            'volume': np.random.uniform(100, 1000, len(timestamps))
        })
        
        df = df.set_index('timestamp')
        print(f"✓ Generated {len(df)} mock candles for testing")
        
        return df

    def get_btc_price_at(self, target_time: datetime) -> float:
        """
        Get BTC price closest to a specific timestamp.

        Args:
            target_time: datetime to query

        Returns:
            Closest candle close price (0.0 if unavailable)
        """
        try:
            now = datetime.now()
            if target_time > now:
                return 0.0

            days_back = max(1, min(30, (now - target_time).days + 1))
            interval = '1h' if days_back <= 7 else '4h'

            df = self.get_btc_historical_data(days=days_back, interval=interval)
            if df.empty:
                return 0.0

            if isinstance(df.index, pd.DatetimeIndex):
                time_index = df.index
            else:
                df = df.reset_index()
                time_index = pd.to_datetime(df['timestamp'])

            idx = int(np.abs(time_index - target_time).argmin())
            row = df.iloc[idx]

            if 'close' in row:
                return float(row['close'])
            if 'price' in row:
                return float(row['price'])

            return 0.0
        except Exception as e:
            print(f"⚠️ Error fetching price at time: {e}")
            return 0.0
    
    def get_market_sentiment(self) -> Dict:
        """
        Get market sentiment indicators
        
        Returns:
            Dict with fear/greed index, social sentiment, etc.
        """
        cache_key = 'market_sentiment'
        cached = self._get_cached_data(cache_key)
        if cached:
            return cached
        
        sentiment = {
            'fear_greed_index': 50,  # Neutral default
            'trend': 'neutral',
            'social_volume': 0,
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            # Try to get Fear & Greed Index from Alternative.me
            url = "https://api.alternative.me/fng/"
            response = self.session.get(url, timeout=self.request_timeout)
            response.raise_for_status()
            data = response.json()
            
            if data.get('data'):
                latest = data['data'][0]
                sentiment['fear_greed_index'] = int(latest.get('value', 50))
                sentiment['trend'] = latest.get('value_classification', 'neutral').lower()
                
        except Exception as e:
            print(f"Error fetching sentiment: {e}")
        
        self._set_cache(cache_key, sentiment)
        return sentiment
    
    def get_funding_rates(self) -> Dict:
        """
        Get BTC perpetual funding rates (from multiple exchanges)
        
        Returns:
            Dict with funding rates and predicted direction
        """
        cache_key = 'funding_rates'
        cached = self._get_cached_data(cache_key)
        if cached:
            return cached
        
        funding = {
            'binance': 0.0,
            'bybit': 0.0,
            'average': 0.0,
            'trend': 'neutral',
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            # Note: This would require exchange API keys for real data
            # For now, returning placeholder structure
            # In production, use ccxt library to fetch real funding rates
            pass
            
        except Exception as e:
            print(f"Error fetching funding rates: {e}")
        
        self._set_cache(cache_key, funding)
        return funding
    
    def get_current_market_data(self) -> Dict:
        """
        Get comprehensive current BTC market data from FREE APIs
        
        Returns:
            Dict with price, volume, market cap, 24h change, etc.
        """
        cache_key = 'current_market_data'
        cached = self._get_cached_data(cache_key)
        if cached:
            return cached
        
        market_data = {
            'price': 0,
            'volume_24h': 0,
            'market_cap': 0,
            'change_24h': 0,
            'change_1h': 0,
            'high_24h': 0,
            'low_24h': 0,
            'timestamp': datetime.now().isoformat()
        }
        
        # Try Coinbase Advanced Trade first
        try:
            # Get current ticker
            ticker_url = f"{self.coinbase_pro_base}/products/BTC-USD/ticker"
            ticker_resp = self.session.get(ticker_url, timeout=self.request_timeout)
            ticker_resp.raise_for_status()
            ticker = ticker_resp.json()
            
            # Get 24h stats
            stats_url = f"{self.coinbase_pro_base}/products/BTC-USD/stats"
            stats_resp = self.session.get(stats_url, timeout=self.request_timeout)
            stats_resp.raise_for_status()
            stats = stats_resp.json()
            
            market_data['price'] = float(ticker.get('price', 0))
            market_data['volume_24h'] = float(stats.get('volume', 0))
            market_data['high_24h'] = float(stats.get('high', 0))
            market_data['low_24h'] = float(stats.get('low', 0))
            
            # Calculate 24h change
            open_price = float(stats.get('open', market_data['price']))
            if open_price > 0:
                market_data['change_24h'] = ((market_data['price'] - open_price) / open_price) * 100
            
            print(f"✅ Got market data from Coinbase: ${market_data['price']:,.2f} ({market_data['change_24h']:+.2f}%)")
            
            self._set_cache(cache_key, market_data)
            return market_data
            
        except Exception as e:
            print(f"⚠️ Coinbase market data error: {e}")
        
        # Fallback to CryptoCompare
        try:
            # Get current price and market data
            url = f"{self.cryptocompare_base}/pricemultifull"
            params = {'fsyms': 'BTC', 'tsyms': 'USD'}
            
            response = self.session.get(url, params=params, timeout=self.request_timeout)
            response.raise_for_status()
            data = response.json()
            
            if 'RAW' in data and 'BTC' in data['RAW']:
                btc_data = data['RAW']['BTC']['USD']
                
                market_data['price'] = float(btc_data.get('PRICE', 0))
                market_data['volume_24h'] = float(btc_data.get('VOLUME24HOUR', 0))
                market_data['market_cap'] = float(btc_data.get('MKTCAP', 0))
                market_data['change_24h'] = float(btc_data.get('CHANGEPCT24HOUR', 0))
                market_data['change_1h'] = float(btc_data.get('CHANGEPCTHOUR', 0))
                market_data['high_24h'] = float(btc_data.get('HIGH24HOUR', 0))
                market_data['low_24h'] = float(btc_data.get('LOW24HOUR', 0))
                
                print(f"✅ Got market data from CryptoCompare: ${market_data['price']:,.2f}")
                
                self._set_cache(cache_key, market_data)
                return market_data
                
        except Exception as e2:
            print(f"⚠️ CryptoCompare error: {e2}")
        
        # Final fallback: Use live price method
        market_data['price'] = self.get_live_btc_price()
        self._set_cache(cache_key, market_data)
        return market_data
    
    def get_prediction_market_odds(self) -> Dict:
        """
        Get prediction market odds for BTC price movements
        
        Returns:
            Dict with market-implied probabilities
        """
        cache_key = 'prediction_odds'
        cached = self._get_cached_data(cache_key)
        if cached:
            return cached
        
        try:
            orderbook = self.get_btc_orderbook(level=2)
            current_price = orderbook.get('mid_price', 0)
            
            if current_price == 0:
                return {
                    'current_price': 0,
                    'up_probability': 0.5,
                    'down_probability': 0.5,
                    'targets': {},
                    'timestamp': datetime.now().isoformat()
                }
            
            # Calculate implied probabilities from order book imbalance
            total_bids = orderbook.get('total_bid_volume', 0)
            total_asks = orderbook.get('total_ask_volume', 0)
            total_volume = total_bids + total_asks
            
            if total_volume > 0:
                up_prob = total_bids / total_volume
                down_prob = total_asks / total_volume
            else:
                up_prob = down_prob = 0.5
            
            # Create price targets
            targets = {
                '1h': {
                    'up_1%': current_price * 1.01,
                    'down_1%': current_price * 0.99,
                    'up_prob': up_prob,
                    'down_prob': down_prob
                },
                '24h': {
                    'up_5%': current_price * 1.05,
                    'down_5%': current_price * 0.95,
                    'up_prob': up_prob * 0.9,  # Reduce confidence over time
                    'down_prob': down_prob * 0.9
                },
                '7d': {
                    'up_10%': current_price * 1.10,
                    'down_10%': current_price * 0.90,
                    'up_prob': up_prob * 0.7,
                    'down_prob': down_prob * 0.7
                }
            }
            
            odds = {
                'current_price': current_price,
                'up_probability': up_prob,
                'down_probability': down_prob,
                'targets': targets,
                'timestamp': datetime.now().isoformat()
            }
            
            self._set_cache(cache_key, odds)
            return odds
            
        except Exception as e:
            print(f"Error calculating prediction odds: {e}")
            return {
                'current_price': 0,
                'up_probability': 0.5,
                'down_probability': 0.5,
                'targets': {},
                'timestamp': datetime.now().isoformat()
            }
    
    def get_comprehensive_market_data(self) -> Dict:
        """
        Get all market data needed for prediction model
        
        Returns:
            Comprehensive dict with all market indicators
        """
        return {
            'orderbook': self.get_btc_orderbook(),
            'historical': self.get_btc_historical_data(days=30).to_dict('records'),
            'sentiment': self.get_market_sentiment(),
            'funding': self.get_funding_rates(),
            'predictions': self.get_prediction_market_odds(),
            'timestamp': datetime.now().isoformat()
        }


if __name__ == "__main__":
    # Test the fetcher
    fetcher = PredictionMarketFetcher()
    
    print("Testing Prediction Market Fetcher...")
    print("\n1. Order Book:")
    orderbook = fetcher.get_btc_orderbook()
    print(f"   Mid Price: ${orderbook['mid_price']:,.2f}")
    print(f"   Spread: ${orderbook['spread']:.2f}")
    
    print("\n2. Market Sentiment:")
    sentiment = fetcher.get_market_sentiment()
    print(f"   Fear/Greed: {sentiment['fear_greed_index']}/100 ({sentiment['trend']})")
    
    print("\n3. Prediction Odds:")
    odds = fetcher.get_prediction_market_odds()
    print(f"   Current Price: ${odds['current_price']:,.2f}")
    print(f"   Up Probability: {odds['up_probability']:.1%}")
    print(f"   Down Probability: {odds['down_probability']:.1%}")
    
    print("\n4. Historical Data:")
    historical = fetcher.get_btc_historical_data(days=7)
    if not historical.empty:
        print(f"   Records: {len(historical)}")
        print(f"   Latest Price: ${historical['price'].iloc[-1]:,.2f}")

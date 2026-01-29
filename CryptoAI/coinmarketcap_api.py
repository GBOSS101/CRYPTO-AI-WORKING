"""
CoinMarketCap API Client
Based on Swift CryptoPortfolio patterns - comprehensive error handling and rate limiting
"""
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import time
import os


class CoinMarketCapError(Exception):
    """Base exception for CoinMarketCap API errors"""
    pass


class RateLimitExceeded(CoinMarketCapError):
    """Raised when API rate limit is exceeded"""
    def __init__(self, retry_after: int = 60):
        self.retry_after = retry_after
        super().__init__(f"Rate limit exceeded. Retry after {retry_after} seconds")


class InvalidResponse(CoinMarketCapError):
    """Raised when API returns invalid response"""
    pass


class AuthenticationError(CoinMarketCapError):
    """Raised when API key is invalid or missing"""
    pass


class NotFoundError(CoinMarketCapError):
    """Raised when requested resource is not found"""
    pass


@dataclass
class Cryptocurrency:
    """Represents a cryptocurrency with market data (matching Swift model)"""
    id: int
    symbol: str
    name: str
    current_price: float
    market_cap: float
    volume_24h: float
    percent_change_1h: float
    percent_change_24h: float
    percent_change_7d: float
    last_updated: datetime
    
    @classmethod
    def from_cmc_response(cls, data: Dict[str, Any]) -> 'Cryptocurrency':
        """Create from CoinMarketCap API response"""
        quote = data.get('quote', {}).get('USD', {})
        return cls(
            id=data.get('id', 0),
            symbol=data.get('symbol', ''),
            name=data.get('name', ''),
            current_price=quote.get('price', 0.0),
            market_cap=quote.get('market_cap', 0.0),
            volume_24h=quote.get('volume_24h', 0.0),
            percent_change_1h=quote.get('percent_change_1h', 0.0),
            percent_change_24h=quote.get('percent_change_24h', 0.0),
            percent_change_7d=quote.get('percent_change_7d', 0.0),
            last_updated=datetime.fromisoformat(
                data.get('last_updated', datetime.now().isoformat()).replace('Z', '+00:00')
            )
        )


class CoinMarketCapAPI:
    """
    CoinMarketCap API Client with comprehensive error handling
    Based on Swift CryptoPortfolio patterns
    """
    
    BASE_URL = "https://pro-api.coinmarketcap.com/v1"
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize API client
        
        Args:
            api_key: CoinMarketCap API key. If not provided, reads from
                    CMC_API_KEY environment variable
        """
        self.api_key = api_key or os.environ.get('CMC_API_KEY', '')
        if not self.api_key:
            print("⚠️ No CoinMarketCap API key provided. Set CMC_API_KEY env var or pass api_key")
        
        self.session = self._build_session()
        self.cache: Dict[str, tuple] = {}
        self.cache_timeout = 60  # 1 minute cache
        
        # Rate limiting
        self.request_count = 0
        self.request_reset_time = datetime.now()
        self.max_requests_per_minute = 30  # Free tier limit
        
    def _build_session(self) -> requests.Session:
        """Build requests session with retry logic"""
        session = requests.Session()
        retries = Retry(
            total=3,
            backoff_factor=1.0,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"]
        )
        adapter = HTTPAdapter(max_retries=retries)
        session.mount("https://", adapter)
        return session
    
    def _check_rate_limit(self):
        """Check and enforce rate limiting"""
        now = datetime.now()
        
        # Reset counter every minute
        if (now - self.request_reset_time).total_seconds() > 60:
            self.request_count = 0
            self.request_reset_time = now
        
        if self.request_count >= self.max_requests_per_minute:
            wait_time = 60 - (now - self.request_reset_time).total_seconds()
            raise RateLimitExceeded(retry_after=int(max(wait_time, 1)))
        
        self.request_count += 1
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with API key"""
        return {
            'X-CMC_PRO_API_KEY': self.api_key,
            'Accept': 'application/json'
        }
    
    def _make_request(self, endpoint: str, params: Dict = None) -> Dict:
        """
        Make API request with error handling
        
        Args:
            endpoint: API endpoint path
            params: Query parameters
            
        Returns:
            JSON response data
            
        Raises:
            CoinMarketCapError: On API errors
        """
        self._check_rate_limit()
        
        url = f"{self.BASE_URL}{endpoint}"
        
        try:
            response = self.session.get(
                url,
                headers=self._get_headers(),
                params=params,
                timeout=10
            )
            
            # Handle HTTP errors
            if response.status_code == 401:
                raise AuthenticationError("Invalid API key")
            elif response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 60))
                raise RateLimitExceeded(retry_after=retry_after)
            elif response.status_code == 404:
                raise NotFoundError(f"Resource not found: {endpoint}")
            elif response.status_code != 200:
                raise InvalidResponse(f"HTTP {response.status_code}: {response.text}")
            
            data = response.json()
            
            # Check for API-level errors
            status = data.get('status', {})
            if status.get('error_code', 0) != 0:
                error_msg = status.get('error_message', 'Unknown error')
                raise InvalidResponse(error_msg)
            
            return data.get('data', {})
            
        except requests.exceptions.Timeout:
            raise CoinMarketCapError("Request timed out")
        except requests.exceptions.ConnectionError:
            raise CoinMarketCapError("Connection error")
        except requests.exceptions.JSONDecodeError:
            raise InvalidResponse("Invalid JSON response")
    
    def fetch_price(self, symbol: str) -> Cryptocurrency:
        """
        Fetch price for a single cryptocurrency
        
        Args:
            symbol: Cryptocurrency symbol (e.g., 'BTC', 'ETH')
            
        Returns:
            Cryptocurrency object with current data
        """
        cache_key = f"price_{symbol}"
        
        # Check cache
        if cache_key in self.cache:
            cached_data, cached_time = self.cache[cache_key]
            if time.time() - cached_time < self.cache_timeout:
                return cached_data
        
        data = self._make_request(
            '/cryptocurrency/quotes/latest',
            params={'symbol': symbol.upper(), 'convert': 'USD'}
        )
        
        if symbol.upper() not in data:
            raise NotFoundError(f"Cryptocurrency {symbol} not found")
        
        crypto = Cryptocurrency.from_cmc_response(data[symbol.upper()])
        self.cache[cache_key] = (crypto, time.time())
        
        return crypto
    
    def fetch_prices(self, symbols: List[str]) -> Dict[str, Cryptocurrency]:
        """
        Fetch prices for multiple cryptocurrencies
        
        Args:
            symbols: List of cryptocurrency symbols
            
        Returns:
            Dict mapping symbol to Cryptocurrency object
        """
        cache_key = f"prices_{'_'.join(sorted(symbols))}"
        
        # Check cache
        if cache_key in self.cache:
            cached_data, cached_time = self.cache[cache_key]
            if time.time() - cached_time < self.cache_timeout:
                return cached_data
        
        symbols_str = ','.join(s.upper() for s in symbols)
        data = self._make_request(
            '/cryptocurrency/quotes/latest',
            params={'symbol': symbols_str, 'convert': 'USD'}
        )
        
        result = {}
        for symbol in symbols:
            upper_symbol = symbol.upper()
            if upper_symbol in data:
                result[upper_symbol] = Cryptocurrency.from_cmc_response(data[upper_symbol])
        
        self.cache[cache_key] = (result, time.time())
        return result
    
    def fetch_top_cryptocurrencies(self, limit: int = 20) -> List[Cryptocurrency]:
        """
        Fetch top cryptocurrencies by market cap
        
        Args:
            limit: Number of cryptocurrencies to fetch (max 100)
            
        Returns:
            List of Cryptocurrency objects
        """
        cache_key = f"top_{limit}"
        
        # Check cache
        if cache_key in self.cache:
            cached_data, cached_time = self.cache[cache_key]
            if time.time() - cached_time < self.cache_timeout:
                return cached_data
        
        data = self._make_request(
            '/cryptocurrency/listings/latest',
            params={'limit': min(limit, 100), 'convert': 'USD'}
        )
        
        cryptos = [Cryptocurrency.from_cmc_response(item) for item in data]
        self.cache[cache_key] = (cryptos, time.time())
        
        return cryptos
    
    def get_global_metrics(self) -> Dict[str, Any]:
        """
        Get global cryptocurrency market metrics
        
        Returns:
            Dict with total market cap, volume, BTC dominance, etc.
        """
        cache_key = "global_metrics"
        
        if cache_key in self.cache:
            cached_data, cached_time = self.cache[cache_key]
            if time.time() - cached_time < self.cache_timeout:
                return cached_data
        
        data = self._make_request('/global-metrics/quotes/latest')
        
        quote = data.get('quote', {}).get('USD', {})
        metrics = {
            'total_market_cap': quote.get('total_market_cap', 0),
            'total_volume_24h': quote.get('total_volume_24h', 0),
            'btc_dominance': data.get('btc_dominance', 0),
            'eth_dominance': data.get('eth_dominance', 0),
            'active_cryptocurrencies': data.get('active_cryptocurrencies', 0),
            'total_cryptocurrencies': data.get('total_cryptocurrencies', 0),
            'active_exchanges': data.get('active_exchanges', 0),
            'last_updated': data.get('last_updated', '')
        }
        
        self.cache[cache_key] = (metrics, time.time())
        return metrics


# Integration with existing data fetcher
def integrate_with_live_data_fetcher():
    """
    Example of integrating CoinMarketCap with existing LiveDataFetcher
    """
    from data_fetcher import LiveDataFetcher
    
    class EnhancedDataFetcher(LiveDataFetcher):
        def __init__(self, cmc_api_key: str = None):
            super().__init__()
            self.cmc_api = CoinMarketCapAPI(api_key=cmc_api_key)
            self.use_cmc = bool(cmc_api_key or os.environ.get('CMC_API_KEY'))
        
        def get_live_prices_enhanced(self, coin_ids: List[str]) -> Dict[str, float]:
            """Get prices with CoinMarketCap fallback"""
            try:
                # Try existing sources first (free, no key needed)
                return self.get_live_prices(coin_ids)
            except Exception as e:
                if self.use_cmc:
                    print(f"⚠️ Primary sources failed, using CoinMarketCap: {e}")
                    # Convert coin IDs to symbols
                    symbols = [self.coin_symbol_map.get(cid, cid.upper()) for cid in coin_ids]
                    try:
                        cryptos = self.cmc_api.fetch_prices(symbols)
                        return {
                            cid: cryptos[self.coin_symbol_map.get(cid, cid.upper())].current_price
                            for cid in coin_ids
                            if self.coin_symbol_map.get(cid, cid.upper()) in cryptos
                        }
                    except CoinMarketCapError as cmc_e:
                        print(f"❌ CoinMarketCap also failed: {cmc_e}")
                raise
    
    return EnhancedDataFetcher


if __name__ == "__main__":
    # Demo usage
    print("🪙 CoinMarketCap API Client Demo")
    print("=" * 50)
    
    api = CoinMarketCapAPI()
    
    if not api.api_key:
        print("\n⚠️ No API key set. Get one at https://coinmarketcap.com/api/")
        print("Set it with: $env:CMC_API_KEY = 'your-key'")
        print("\nRunning in demo mode with mock data...")
    else:
        try:
            # Fetch Bitcoin price
            btc = api.fetch_price('BTC')
            print(f"\n₿ Bitcoin: ${btc.current_price:,.2f}")
            print(f"   24h Change: {btc.percent_change_24h:+.2f}%")
            print(f"   Market Cap: ${btc.market_cap/1e9:.2f}B")
            
            # Fetch top 5 cryptos
            print("\n📊 Top 5 Cryptocurrencies:")
            top5 = api.fetch_top_cryptocurrencies(5)
            for i, crypto in enumerate(top5, 1):
                print(f"   {i}. {crypto.symbol}: ${crypto.current_price:,.2f} ({crypto.percent_change_24h:+.2f}%)")
            
            # Global metrics
            metrics = api.get_global_metrics()
            print(f"\n🌍 Global Market:")
            print(f"   Total Market Cap: ${metrics['total_market_cap']/1e12:.2f}T")
            print(f"   BTC Dominance: {metrics['btc_dominance']:.1f}%")
            
        except CoinMarketCapError as e:
            print(f"\n❌ Error: {e}")

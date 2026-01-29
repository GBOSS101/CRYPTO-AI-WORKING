"""
Live Data Fetching Module
Fetches real-time cryptocurrency data from FREE APIs (No CoinGecko Pro!)
"""
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import ccxt
from datetime import datetime, timedelta
import pandas as pd
from typing import Dict, List, Optional
import time

class LiveDataFetcher:
    def __init__(self):
        # FREE API endpoints (no authentication needed!)
        self.cryptocompare_base = "https://min-api.cryptocompare.com/data"
        self.coinbase_base = "https://api.pro.coinbase.com"
        self.cache = {}
        self.cache_timeout = 15  # seconds
        self.request_timeout = 10
        self.session = self._build_session()
        
        print("📡 Initialized FREE data sources (CryptoCompare + Coinbase)")
        
        # Map common coin IDs to symbols
        self.coin_symbol_map = {
            'bitcoin': 'BTC',
            'ethereum': 'ETH',
            'dogecoin': 'DOGE',
            'binancecoin': 'BNB',
            'cardano': 'ADA',
            'solana': 'SOL',
            'ripple': 'XRP',
            'polkadot': 'DOT',
            'avalanche-2': 'AVAX',
            'chainlink': 'LINK',
            'polygon': 'MATIC',
            'uniswap': 'UNI',
            'litecoin': 'LTC',
            'near': 'NEAR',
            'cosmos': 'ATOM',
            'algorand': 'ALGO'
        }

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
        
    def get_live_prices(self, coin_ids: List[str]) -> Dict[str, float]:
        """
        Get live prices for multiple cryptocurrencies from FREE APIs
        """
        cache_key = 'prices_' + '_'.join(coin_ids)
        
        # Check cache
        if cache_key in self.cache:
            cached_data, cached_time = self.cache[cache_key]
            if time.time() - cached_time < self.cache_timeout:
                return cached_data
        
        try:
            def parse_response(resp_json, batch_coin_ids, batch_symbols):
                batch_result = {}
                raw = resp_json.get('RAW', {})
                display = resp_json.get('DISPLAY', {})
                for idx, coin_id in enumerate(batch_coin_ids):
                    symbol = batch_symbols[idx]
                    coin_data = None
                    if symbol in raw and 'USD' in raw[symbol]:
                        coin_data = raw[symbol]['USD']
                        batch_result[coin_id] = {
                            'price': float(coin_data.get('PRICE', 0)),
                            'change_24h': float(coin_data.get('CHANGEPCT24HOUR', 0)),
                            'volume_24h': float(coin_data.get('VOLUME24HOURTO', 0)),
                            'market_cap': float(coin_data.get('MKTCAP', 0)),
                            'timestamp': datetime.now().isoformat()
                        }
                    elif symbol in display and 'USD' in display[symbol]:
                        disp = display[symbol]['USD']
                        price_str = str(disp.get('PRICE', '0')).replace('$', '').replace(',', '')
                        change_str = str(disp.get('CHANGEPCT24HOUR', '0')).replace('%', '')
                        batch_result[coin_id] = {
                            'price': float(price_str or 0),
                            'change_24h': float(change_str or 0),
                            'volume_24h': 0.0,
                            'market_cap': 0.0,
                            'timestamp': datetime.now().isoformat()
                        }
                return batch_result

            # Convert coin IDs to symbols
            symbols = [self.coin_symbol_map.get(coin_id, coin_id.upper()) for coin_id in coin_ids]

            # Chunk requests to avoid API limits
            result = {}
            batch_size = 8
            for i in range(0, len(symbols), batch_size):
                batch_symbols = symbols[i:i + batch_size]
                batch_coin_ids = coin_ids[i:i + batch_size]
                fsyms = ','.join(batch_symbols)
                url = f"{self.cryptocompare_base}/pricemultifull"
                params = {'fsyms': fsyms, 'tsyms': 'USD'}
                response = self.session.get(url, params=params, timeout=self.request_timeout)
                response.raise_for_status()
                data = response.json()
                result.update(parse_response(data, batch_coin_ids, batch_symbols))

            self.cache[cache_key] = (result, time.time())
            return result

        except Exception as e:
            print(f"Error fetching live prices: {e}")
            return {}
    
    def get_market_data(self, coin_id: str, days: int = 7) -> pd.DataFrame:
        """
        Get historical market data for technical analysis using FREE APIs
        """
        try:
            # Convert coin ID to symbol
            symbol = self.coin_symbol_map.get(coin_id, coin_id.upper())
            
            # Determine endpoint based on days
            if days <= 7:
                endpoint = 'histohour'
                limit = days * 24
            else:
                endpoint = 'histoday'
                limit = min(days, 365)
            
            url = f"{self.cryptocompare_base}/v2/{endpoint}"
            params = {'fsym': symbol, 'tsym': 'USD', 'limit': limit}
            
            response = self.session.get(url, params=params, timeout=self.request_timeout)
            response.raise_for_status()
            result = response.json()
            
            if result.get('Response') == 'Success':
                data = result['Data']['Data']
                df = pd.DataFrame(data)
                df['timestamp'] = pd.to_datetime(df['time'], unit='s')
                df['price'] = df['close']
                df = df.rename(columns={'volumeto': 'volume'})
                df = df[['timestamp', 'price', 'volume', 'high', 'low', 'open', 'close']]
                return df
            
            return pd.DataFrame()
            
        except Exception as e:
            print(f"Error fetching market data for {coin_id}: {e}")
            return pd.DataFrame()
    
    def get_trending_coins(self, limit: int = 10) -> List[Dict]:
        """
        Get top cryptocurrencies by market cap (FREE API)
        """
        try:
            # Get top coins by market cap from CryptoCompare
            url = f"{self.cryptocompare_base}/top/mktcapfull"
            params = {'limit': limit, 'tsym': 'USD'}
            
            response = self.session.get(url, params=params, timeout=self.request_timeout)
            response.raise_for_status()
            result = response.json()
            
            coins = []
            if 'Data' in result:
                for item in result['Data']:
                    coin_info = item['CoinInfo']
                    raw_data = item.get('RAW', {}).get('USD', {})
                    
                    # Reverse lookup symbol to coin_id
                    coin_id = coin_info['Name'].lower()
                    for cid, sym in self.coin_symbol_map.items():
                        if sym == coin_info['Name']:
                            coin_id = cid
                            break
                    
                    coins.append({
                        'id': coin_id,
                        'symbol': coin_info['Name'],
                        'name': coin_info['FullName'],
                        'market_cap_rank': len(coins) + 1,
                        'price_btc': raw_data.get('PRICE', 0) / 100000 if raw_data else 0
                    })
            
            return coins
            
        except Exception as e:
            print(f"Error fetching trending coins: {e}")
            return []
    
    def get_top_gainers(self, limit: int = 10) -> List[Dict]:
        """
        Get top gaining cryptocurrencies in the last 24h (FREE API)
        """
        try:
            # Get top volume coins from CryptoCompare
            url = f"{self.cryptocompare_base}/top/totalvolfull"
            params = {'limit': limit * 2, 'tsym': 'USD'}
            
            response = self.session.get(url, params=params, timeout=self.request_timeout)
            response.raise_for_status()
            result = response.json()
            
            gainers = []
            if 'Data' in result:
                for item in result['Data']:
                    coin_info = item['CoinInfo']
                    raw_data = item.get('RAW', {}).get('USD', {})
                    
                    if raw_data:
                        change_24h = raw_data.get('CHANGEPCT24HOUR', 0)
                        if change_24h > 0:  # Only gainers
                            # Reverse lookup symbol to coin_id
                            coin_id = coin_info['Name'].lower()
                            for cid, sym in self.coin_symbol_map.items():
                                if sym == coin_info['Name']:
                                    coin_id = cid
                                    break
                            
                            gainers.append({
                                'id': coin_id,
                                'symbol': coin_info['Name'],
                                'name': coin_info['FullName'],
                                'price': raw_data.get('PRICE', 0),
                                'change_24h': change_24h,
                                'volume_24h': raw_data.get('VOLUME24HOURTO', 0),
                                'market_cap': raw_data.get('MKTCAP', 0),
                                'market_cap_rank': len(gainers) + 1
                            })
            
            # Sort by change and return top gainers
            gainers.sort(key=lambda x: x['change_24h'], reverse=True)
            return gainers[:limit]
            
        except Exception as e:
            print(f"Error fetching top gainers: {e}")
            return []
    
    def get_market_overview(self) -> Dict:
        """
        Get overall market overview and statistics (using FREE API approximation)
        """
        try:
            # Use top coins to estimate market overview
            url = f"{self.cryptocompare_base}/top/mktcapfull"
            params = {'limit': 100, 'tsym': 'USD'}
            
            response = self.session.get(url, params=params, timeout=self.request_timeout)
            response.raise_for_status()
            result = response.json()
            
            total_market_cap = 0
            total_volume = 0
            btc_market_cap = 0
            eth_market_cap = 0
            
            if 'Data' in result:
                for item in result['Data']:
                    raw_data = item.get('RAW', {}).get('USD', {})
                    if raw_data:
                        mktcap = raw_data.get('MKTCAP', 0)
                        volume = raw_data.get('VOLUME24HOURTO', 0)
                        total_market_cap += mktcap
                        total_volume += volume
                        
                        symbol = item['CoinInfo']['Name']
                        if symbol == 'BTC':
                            btc_market_cap = mktcap
                        elif symbol == 'ETH':
                            eth_market_cap = mktcap
            
            return {
                'total_market_cap_usd': total_market_cap,
                'total_volume_24h_usd': total_volume,
                'btc_dominance': (btc_market_cap / total_market_cap * 100) if total_market_cap > 0 else 0,
                'eth_dominance': (eth_market_cap / total_market_cap * 100) if total_market_cap > 0 else 0,
                'active_cryptocurrencies': 100,
                'markets': 500,
                'market_cap_change_24h': 0,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"Error fetching market overview: {e}")
            return {}
    
    def get_coin_details(self, coin_id: str) -> Dict:
        """
        Get detailed information about a specific cryptocurrency (FREE API)
        """
        try:
            # Get symbol from coin_id
            symbol = self.coin_symbol_map.get(coin_id, coin_id.upper())
            
            # Get current price data
            url = f"{self.cryptocompare_base}/pricemultifull"
            params = {'fsyms': symbol, 'tsyms': 'USD'}
            
            response = self.session.get(url, params=params, timeout=self.request_timeout)
            response.raise_for_status()
            result = response.json()
            
            raw_data = result.get('RAW', {}).get(symbol, {}).get('USD', {})
            
            if not raw_data:
                return {}
            
            return {
                'id': coin_id,
                'symbol': symbol,
                'name': raw_data.get('FROMSYMBOL', symbol),
                'current_price': raw_data.get('PRICE', 0),
                'market_cap': raw_data.get('MKTCAP', 0),
                'market_cap_rank': 999,  # Not available from free API
                'total_volume': raw_data.get('VOLUME24HOURTO', 0),
                'high_24h': raw_data.get('HIGH24HOUR', 0),
                'low_24h': raw_data.get('LOW24HOUR', 0),
                'price_change_24h': raw_data.get('CHANGE24HOUR', 0),
                'price_change_percentage_24h': raw_data.get('CHANGEPCT24HOUR', 0),
                'price_change_percentage_7d': 0,  # Not available in free tier
                'price_change_percentage_30d': 0,  # Not available in free tier
                'circulating_supply': raw_data.get('CIRCULATINGSUPPLY', 0),
                'total_supply': raw_data.get('SUPPLY', 0),
                'ath': 0,  # Not available from free API
                'atl': 0,  # Not available from free API
            }
            
        except Exception as e:
            print(f"Error fetching coin details for {coin_id}: {e}")
            return {}

"""
CryptoAI - Simple Windows Cryptocurrency Tracker
Uses CoinMarketCap and Coinbase for live data
"""
import tkinter as tk
from tkinter import ttk, messagebox
import requests
import threading
import time
import os
import json
from datetime import datetime

class CryptoTracker:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("CryptoAI - Live Crypto Tracker")
        self.root.geometry("800x600")
        self.root.configure(bg='#1a1a2e')
        
        # API endpoints
        self.coinbase_url = "https://api.coinbase.com/v2/prices"
        self.coingecko_url = "https://api.coingecko.com/api/v3"
        
        # CoinMarketCap API (free tier)
        self.cmc_api_key = os.environ.get('CMC_API_KEY', '')
        self.cmc_url = "https://pro-api.coinmarketcap.com/v1"
        
        # Tracked coins
        self.coins = ['BTC', 'ETH', 'SOL', 'XRP', 'ADA', 'DOGE', 'AVAX', 'DOT', 'LINK', 'MATIC']
        self.prices = {}
        self.running = True
        
        self.setup_ui()
        self.start_price_updates()
        
    def setup_ui(self):
        """Setup the user interface"""
        # Title
        title = tk.Label(
            self.root, 
            text="🪙 CryptoAI Live Tracker", 
            font=('Segoe UI', 24, 'bold'),
            bg='#1a1a2e', 
            fg='#eee'
        )
        title.pack(pady=20)
        
        # Status bar
        self.status_var = tk.StringVar(value="Connecting to exchanges...")
        status = tk.Label(
            self.root,
            textvariable=self.status_var,
            font=('Segoe UI', 10),
            bg='#1a1a2e',
            fg='#888'
        )
        status.pack()
        
        # Create treeview for prices
        style = ttk.Style()
        style.theme_use('clam')
        style.configure(
            "Treeview",
            background="#16213e",
            foreground="white",
            rowheight=40,
            fieldbackground="#16213e",
            font=('Segoe UI', 12)
        )
        style.configure(
            "Treeview.Heading",
            background="#0f3460",
            foreground="white",
            font=('Segoe UI', 12, 'bold')
        )
        style.map('Treeview', background=[('selected', '#e94560')])
        
        # Frame for treeview
        frame = tk.Frame(self.root, bg='#1a1a2e')
        frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Treeview
        self.tree = ttk.Treeview(
            frame,
            columns=('Symbol', 'Price', 'Change 24h', 'Source', 'Updated'),
            show='headings',
            yscrollcommand=scrollbar.set
        )
        
        self.tree.heading('Symbol', text='Coin')
        self.tree.heading('Price', text='Price (USD)')
        self.tree.heading('Change 24h', text='24h Change')
        self.tree.heading('Source', text='Source')
        self.tree.heading('Updated', text='Updated')
        
        self.tree.column('Symbol', width=100, anchor='center')
        self.tree.column('Price', width=150, anchor='e')
        self.tree.column('Change 24h', width=120, anchor='center')
        self.tree.column('Source', width=120, anchor='center')
        self.tree.column('Updated', width=150, anchor='center')
        
        self.tree.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.tree.yview)
        
        # Buttons frame
        btn_frame = tk.Frame(self.root, bg='#1a1a2e')
        btn_frame.pack(pady=10)
        
        refresh_btn = tk.Button(
            btn_frame,
            text="🔄 Refresh Now",
            command=self.refresh_prices,
            font=('Segoe UI', 11),
            bg='#e94560',
            fg='white',
            padx=20,
            pady=5
        )
        refresh_btn.pack(side=tk.LEFT, padx=5)
        
        # Last update label
        self.last_update_var = tk.StringVar(value="")
        last_update = tk.Label(
            self.root,
            textvariable=self.last_update_var,
            font=('Segoe UI', 9),
            bg='#1a1a2e',
            fg='#666'
        )
        last_update.pack(pady=5)
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
    def fetch_coinbase_price(self, symbol):
        """Fetch price from Coinbase"""
        try:
            url = f"{self.coinbase_url}/{symbol}-USD/spot"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                return {
                    'price': float(data['data']['amount']),
                    'source': 'Coinbase',
                    'change_24h': None
                }
        except Exception as e:
            pass
        return None
    
    def fetch_coingecko_prices(self):
        """Fetch prices from CoinGecko (includes 24h change)"""
        try:
            # Map symbols to CoinGecko IDs
            id_map = {
                'BTC': 'bitcoin', 'ETH': 'ethereum', 'SOL': 'solana',
                'XRP': 'ripple', 'ADA': 'cardano', 'DOGE': 'dogecoin',
                'AVAX': 'avalanche-2', 'DOT': 'polkadot', 'LINK': 'chainlink',
                'MATIC': 'matic-network', 'LTC': 'litecoin', 'UNI': 'uniswap'
            }
            
            ids = [id_map.get(s, s.lower()) for s in self.coins if s in id_map]
            url = f"{self.coingecko_url}/simple/price"
            params = {
                'ids': ','.join(ids),
                'vs_currencies': 'usd',
                'include_24hr_change': 'true'
            }
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                result = {}
                for symbol, cg_id in id_map.items():
                    if cg_id in data:
                        result[symbol] = {
                            'price': data[cg_id].get('usd', 0),
                            'change_24h': data[cg_id].get('usd_24h_change', 0),
                            'source': 'CoinGecko'
                        }
                return result
        except Exception as e:
            print(f"CoinGecko error: {e}")
        return {}
    
    def fetch_coinmarketcap_prices(self):
        """Fetch prices from CoinMarketCap (if API key available)"""
        if not self.cmc_api_key:
            return {}
            
        try:
            url = f"{self.cmc_url}/cryptocurrency/quotes/latest"
            headers = {
                'X-CMC_PRO_API_KEY': self.cmc_api_key,
                'Accept': 'application/json'
            }
            params = {
                'symbol': ','.join(self.coins),
                'convert': 'USD'
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                result = {}
                for symbol in self.coins:
                    if symbol in data.get('data', {}):
                        coin_data = data['data'][symbol]
                        quote = coin_data.get('quote', {}).get('USD', {})
                        result[symbol] = {
                            'price': quote.get('price', 0),
                            'change_24h': quote.get('percent_change_24h', 0),
                            'source': 'CoinMarketCap'
                        }
                return result
        except Exception as e:
            print(f"CoinMarketCap error: {e}")
        return {}
    
    def fetch_all_prices(self):
        """Fetch prices from all sources with fallback"""
        prices = {}
        
        # Try CoinMarketCap first (most reliable if API key exists)
        cmc_prices = self.fetch_coinmarketcap_prices()
        if cmc_prices:
            prices.update(cmc_prices)
            self.status_var.set("✅ Connected to CoinMarketCap")
        
        # Try CoinGecko for any missing coins
        cg_prices = self.fetch_coingecko_prices()
        for symbol, data in cg_prices.items():
            if symbol not in prices:
                prices[symbol] = data
        
        if cg_prices and not cmc_prices:
            self.status_var.set("✅ Connected to CoinGecko")
        
        # Try Coinbase for any still missing
        for symbol in self.coins:
            if symbol not in prices:
                cb_price = self.fetch_coinbase_price(symbol)
                if cb_price:
                    prices[symbol] = cb_price
        
        if not prices:
            self.status_var.set("⚠️ Unable to fetch prices - retrying...")
        
        return prices
    
    def update_display(self):
        """Update the treeview with current prices"""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Add updated prices
        for symbol in self.coins:
            if symbol in self.prices:
                data = self.prices[symbol]
                price = data.get('price', 0)
                change = data.get('change_24h')
                source = data.get('source', 'N/A')
                
                # Format price
                if price >= 1000:
                    price_str = f"${price:,.2f}"
                elif price >= 1:
                    price_str = f"${price:.2f}"
                else:
                    price_str = f"${price:.6f}"
                
                # Format change
                if change is not None:
                    change_str = f"{change:+.2f}%"
                    if change > 0:
                        change_str = f"🟢 {change_str}"
                    elif change < 0:
                        change_str = f"🔴 {change_str}"
                else:
                    change_str = "N/A"
                
                # Insert row
                self.tree.insert('', 'end', values=(
                    symbol,
                    price_str,
                    change_str,
                    source,
                    datetime.now().strftime('%H:%M:%S')
                ))
        
        self.last_update_var.set(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    def refresh_prices(self):
        """Manual refresh"""
        self.status_var.set("Refreshing prices...")
        threading.Thread(target=self._fetch_and_update, daemon=True).start()
    
    def _fetch_and_update(self):
        """Fetch prices and update display (runs in thread)"""
        self.prices = self.fetch_all_prices()
        self.root.after(0, self.update_display)
    
    def price_update_loop(self):
        """Background loop to update prices"""
        while self.running:
            try:
                self.prices = self.fetch_all_prices()
                self.root.after(0, self.update_display)
            except Exception as e:
                print(f"Update error: {e}")
            
            # Wait 30 seconds between updates
            for _ in range(30):
                if not self.running:
                    break
                time.sleep(1)
    
    def start_price_updates(self):
        """Start the background price update thread"""
        thread = threading.Thread(target=self.price_update_loop, daemon=True)
        thread.start()
    
    def on_close(self):
        """Handle window close"""
        self.running = False
        self.root.destroy()
    
    def run(self):
        """Start the application"""
        self.root.mainloop()


def main():
    """Main entry point"""
    app = CryptoTracker()
    app.run()


if __name__ == '__main__':
    main()

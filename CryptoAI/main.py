"""
CryptoAI Trading Assistant - Main Application
Live crypto trading suggestions and portfolio management
"""
import os
from datetime import datetime
from colorama import init, Fore, Style
from tabulate import tabulate
from config import Config
from data_fetcher import LiveDataFetcher
from trading_engine import TradingEngine
from portfolio import Portfolio
import time

# Initialize colorama for colored terminal output
init(autoreset=True)

class CryptoAI:
    def __init__(self):
        self.config = Config()
        self.data_fetcher = LiveDataFetcher()
        self.trading_engine = TradingEngine()
        self.portfolio = Portfolio(initial_balance=Config.WALLET_SIZE)
        
    def clear_screen(self):
        """Clear terminal screen"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def print_header(self):
        """Print application header"""
        print(Fore.CYAN + "=" * 80)
        print(Fore.CYAN + "                    🚀 CryptoAI Trading Assistant 🚀")
        print(Fore.CYAN + "              Live Market Data & Intelligent Trade Suggestions")
        print(Fore.CYAN + f"                    Wallet Size: ${Config.WALLET_SIZE:,.2f}")
        print(Fore.CYAN + "=" * 80)
        print()
    
    def show_main_menu(self):
        """Display main menu"""
        print(Fore.YELLOW + "\n📋 MAIN MENU")
        print("-" * 50)
        print("1. 📊 Get Live Trade Suggestions")
        print("2. 🌍 Market Overview & Sentiment")
        print("3. 💼 View Portfolio")
        print("4. 🔍 Analyze Specific Coin")
        print("5. 📈 Top Gainers")
        print("6. 🔥 Trending Coins")
        print("7. 💰 Simulate Trade")
        print("8. 📜 Trade History")
        print("9. ⚙️  Settings")
        print("0. ❌ Exit")
        print("-" * 50)
    
    def get_trade_suggestions(self):
        """Display live trade suggestions"""
        self.clear_screen()
        self.print_header()
        
        print(Fore.YELLOW + "🤖 Generating Live Trade Suggestions...\n")
        
        suggestions = self.trading_engine.get_trade_suggestions(num_suggestions=5)
        
        if not suggestions:
            print(Fore.RED + "No trade suggestions available at the moment.")
            return
        
        print(Fore.GREEN + f"✅ Found {len(suggestions)} Trading Opportunities:\n")

        summary_rows = []
        for i, s in enumerate(suggestions, 1):
            summary_rows.append([
                f"#{i}",
                s['symbol'].upper(),
                s['signal'].upper(),
                f"{s['confidence']:.1f}%",
                f"{s['score']:.1f}",
                f"${s['current_price']:,.6f}",
                self._format_percent_change(s['price_change_24h']),
                s['trend'].replace('_', ' ').title(),
                f"${s['suggested_investment']:,.2f}"
            ])

        print(Fore.CYAN + "📌 QUICK DECISION SUMMARY")
        print(tabulate(
            summary_rows,
            headers=["Rank", "Coin", "Signal", "Conf", "Score", "Price", "24h", "Trend", "Suggested $"],
            tablefmt="grid"
        ))
        print(Fore.YELLOW + "Tip: Focus on highest score + confidence with positive 24h change.")

        for i, suggestion in enumerate(suggestions, 1):
            self._print_trade_suggestion(i, suggestion)
        
        print(Fore.CYAN + "\n" + "=" * 80)
    
    def _print_trade_suggestion(self, index: int, suggestion: Dict):
        """Print a formatted trade suggestion"""
        signal_color = {
            'strong_buy': Fore.GREEN,
            'buy': Fore.LIGHTGREEN_EX,
            'neutral': Fore.YELLOW,
            'sell': Fore.LIGHTRED_EX,
            'strong_sell': Fore.RED
        }.get(suggestion['signal'], Fore.WHITE)
        
        print(Fore.CYAN + f"\n{'─' * 80}")
        print(Fore.YELLOW + f"#{index} - {suggestion['symbol'].upper()}")
        print(Fore.CYAN + f"{'─' * 80}")
        
        data = [
            ["Signal", signal_color + suggestion['signal'].upper()],
            ["Confidence", f"{suggestion['confidence']:.1f}%"],
            ["Score", f"{suggestion['score']:.1f}/100"],
            ["Current Price", f"${suggestion['current_price']:,.6f}"],
            ["24h Change", self._format_percent_change(suggestion['price_change_24h'])],
            ["Trend", suggestion['trend'].replace('_', ' ').title()],
            ["", ""],
            ["💰 Investment", f"${suggestion['suggested_investment']:,.2f}"],
            ["📊 Quantity", f"{suggestion['quantity']:.8f}"],
            ["🛡️ Stop Loss", f"${suggestion['stop_loss']:,.6f}"],
            ["🎯 Take Profit", f"${suggestion['take_profit']:,.6f}"],
            ["⚖️ Risk/Reward", f"{suggestion['risk_reward_ratio']:.2f}"],
        ]
        
        print(tabulate(data, tablefmt="simple"))
    
    def _format_percent_change(self, change: float) -> str:
        """Format percentage change with color"""
        if change > 0:
            return Fore.GREEN + f"+{change:.2f}%"
        elif change < 0:
            return Fore.RED + f"{change:.2f}%"
        else:
            return Fore.YELLOW + "0.00%"
    
    def show_market_overview(self):
        """Display market overview and sentiment"""
        self.clear_screen()
        self.print_header()
        
        print(Fore.YELLOW + "🌍 Fetching Market Overview...\n")
        
        sentiment_data = self.trading_engine.get_market_sentiment()
        overview = sentiment_data['overview']
        
        print(Fore.CYAN + "📊 GLOBAL MARKET OVERVIEW")
        print("=" * 80)
        
        sentiment_color = {
            'Very Bullish': Fore.GREEN,
            'Bullish': Fore.LIGHTGREEN_EX,
            'Neutral': Fore.YELLOW,
            'Bearish': Fore.LIGHTRED_EX,
            'Very Bearish': Fore.RED
        }.get(sentiment_data['sentiment'], Fore.WHITE)
        
        market_data = [
            ["Market Sentiment", sentiment_color + sentiment_data['sentiment']],
            ["24h Market Cap Change", self._format_percent_change(sentiment_data['market_cap_change_24h'])],
            ["Total Market Cap", f"${overview.get('total_market_cap_usd', 0):,.0f}"],
            ["24h Volume", f"${overview.get('total_volume_24h_usd', 0):,.0f}"],
            ["BTC Dominance", f"{overview.get('btc_dominance', 0):.2f}%"],
            ["ETH Dominance", f"{overview.get('eth_dominance', 0):.2f}%"],
            ["Active Cryptocurrencies", f"{overview.get('active_cryptocurrencies', 0):,}"],
        ]
        
        print(tabulate(market_data, tablefmt="grid"))
        
        # Show top gainers
        print(Fore.CYAN + "\n🚀 TOP GAINERS (24h)")
        print("=" * 80)
        
        gainers = sentiment_data['top_gainers'][:5]
        if gainers:
            gainer_data = []
            for coin in gainers:
                gainer_data.append([
                    coin['symbol'].upper(),
                    coin['name'],
                    f"${coin['price']:,.6f}",
                    self._format_percent_change(coin['change_24h'])
                ])
            
            print(tabulate(gainer_data, 
                          headers=["Symbol", "Name", "Price", "24h Change"],
                          tablefmt="grid"))
    
    def view_portfolio(self):
        """Display portfolio summary"""
        self.clear_screen()
        self.print_header()
        
        print(Fore.YELLOW + "💼 Updating Portfolio Prices...\n")
        
        # Update prices if there are positions
        if self.portfolio.positions:
            coin_ids = list(self.portfolio.positions.keys())
            live_prices = self.data_fetcher.get_live_prices(coin_ids)
            self.portfolio.update_prices(live_prices)
        
        performance = self.portfolio.get_portfolio_performance()
        
        print(Fore.CYAN + "📊 PORTFOLIO PERFORMANCE")
        print("=" * 80)
        
        perf_data = [
            ["Initial Balance", f"${performance['initial_balance']:,.2f}"],
            ["Current Value", f"${performance['current_value']:,.2f}"],
            ["Cash Balance", f"${performance['cash_balance']:,.2f}"],
            ["Invested Value", f"${performance['invested_value']:,.2f}"],
            ["Total Return", self._format_profit_loss(performance['total_return'])],
            ["Return %", self._format_percent_change(performance['return_percent'])],
            ["Active Positions", str(performance['num_positions'])],
            ["Total Trades", str(performance['num_trades'])],
        ]
        
        print(tabulate(perf_data, tablefmt="grid"))
        
        # Show positions
        positions = self.portfolio.get_positions_summary()
        if positions:
            print(Fore.CYAN + "\n💰 CURRENT POSITIONS")
            print("=" * 80)
            
            pos_data = []
            for pos in positions:
                pos_data.append([
                    pos['symbol'],
                    f"{pos['quantity']:.8f}",
                    f"${pos['avg_price']:,.6f}",
                    f"${pos['current_price']:,.6f}",
                    f"${pos['current_value']:,.2f}",
                    self._format_profit_loss(pos['profit_loss']),
                    self._format_percent_change(pos['profit_loss_percent'])
                ])
            
            headers = ["Symbol", "Quantity", "Avg Price", "Current", "Value", "P/L", "P/L %"]
            print(tabulate(pos_data, headers=headers, tablefmt="grid"))
        else:
            print(Fore.YELLOW + "\nNo active positions.")
    
    def _format_profit_loss(self, value: float) -> str:
        """Format profit/loss with color"""
        if value > 0:
            return Fore.GREEN + f"+${value:,.2f}"
        elif value < 0:
            return Fore.RED + f"-${abs(value):,.2f}"
        else:
            return Fore.YELLOW + "$0.00"
    
    def analyze_coin(self):
        """Analyze a specific cryptocurrency"""
        self.clear_screen()
        self.print_header()
        
        print(Fore.YELLOW + "🔍 Analyze Specific Cryptocurrency\n")
        print("Available coins:")
        for i, coin in enumerate(Config.TOP_CRYPTOS[:10], 1):
            print(f"  {i}. {coin}")
        
        coin_input = input(Fore.CYAN + "\nEnter coin name or number: " + Style.RESET_ALL).strip().lower()
        
        # Parse input
        try:
            coin_num = int(coin_input)
            if 1 <= coin_num <= len(Config.TOP_CRYPTOS):
                coin_id = Config.TOP_CRYPTOS[coin_num - 1]
            else:
                print(Fore.RED + "Invalid selection.")
                return
        except ValueError:
            coin_id = coin_input
        
        print(Fore.YELLOW + f"\n📊 Analyzing {coin_id}...\n")
        
        analysis = self.trading_engine.analyze_opportunity(coin_id)
        
        if 'error' in analysis:
            print(Fore.RED + f"Error: {analysis['error']}")
            return
        
        coin_info = analysis['coin_info']
        live_data = analysis['live_data']
        tech_analysis = analysis['technical_analysis']
        
        print(Fore.CYAN + f"💎 {coin_info['name']} ({coin_info['symbol']})")
        print("=" * 80)
        
        info_data = [
            ["Current Price", f"${coin_info['current_price']:,.6f}"],
            ["Market Cap", f"${coin_info['market_cap']:,.0f}"],
            ["Market Cap Rank", f"#{coin_info['market_cap_rank']}"],
            ["24h High", f"${coin_info['high_24h']:,.6f}"],
            ["24h Low", f"${coin_info['low_24h']:,.6f}"],
            ["24h Change", self._format_percent_change(coin_info['price_change_percentage_24h'])],
            ["7d Change", self._format_percent_change(coin_info.get('price_change_percentage_7d', 0))],
            ["30d Change", self._format_percent_change(coin_info.get('price_change_percentage_30d', 0))],
        ]
        
        print(tabulate(info_data, tablefmt="grid"))
        
        print(Fore.CYAN + "\n📈 TECHNICAL ANALYSIS")
        print("=" * 80)
        
        signal_color = {
            'strong_buy': Fore.GREEN,
            'buy': Fore.LIGHTGREEN_EX,
            'neutral': Fore.YELLOW,
            'sell': Fore.LIGHTRED_EX,
            'strong_sell': Fore.RED
        }.get(tech_analysis['overall_signal'], Fore.WHITE)
        
        tech_data = [
            ["Signal", signal_color + tech_analysis['overall_signal'].upper()],
            ["Confidence", f"{tech_analysis['confidence']:.1f}%"],
            ["Trend", tech_analysis['price_trend'].replace('_', ' ').title()],
        ]
        
        print(tabulate(tech_data, tablefmt="grid"))
    
    def show_top_gainers(self):
        """Show top gaining cryptocurrencies"""
        self.clear_screen()
        self.print_header()
        
        print(Fore.YELLOW + "🚀 Fetching Top Gainers...\n")
        
        gainers = self.data_fetcher.get_top_gainers(limit=15)
        
        print(Fore.CYAN + "📊 TOP GAINERS (24h)")
        print("=" * 80)
        
        if gainers:
            gainer_data = []
            for i, coin in enumerate(gainers, 1):
                gainer_data.append([
                    i,
                    coin['symbol'].upper(),
                    coin['name'],
                    f"${coin['price']:,.6f}",
                    self._format_percent_change(coin['change_24h']),
                    f"${coin['volume_24h']:,.0f}"
                ])
            
            headers = ["#", "Symbol", "Name", "Price", "24h Change", "Volume"]
            print(tabulate(gainer_data, headers=headers, tablefmt="grid"))
        else:
            print(Fore.RED + "Unable to fetch data.")
    
    def show_trending(self):
        """Show trending cryptocurrencies"""
        self.clear_screen()
        self.print_header()
        
        print(Fore.YELLOW + "🔥 Fetching Trending Coins...\n")
        
        trending = self.data_fetcher.get_trending_coins(limit=10)
        
        print(Fore.CYAN + "📊 TRENDING CRYPTOCURRENCIES")
        print("=" * 80)
        
        if trending:
            trending_data = []
            for i, coin in enumerate(trending, 1):
                trending_data.append([
                    i,
                    coin['symbol'].upper(),
                    coin['name'],
                    f"#{coin.get('market_cap_rank', 'N/A')}"
                ])
            
            headers = ["#", "Symbol", "Name", "Market Cap Rank"]
            print(tabulate(trending_data, headers=headers, tablefmt="grid"))
        else:
            print(Fore.RED + "Unable to fetch data.")
    
    def simulate_trade(self):
        """Simulate executing a trade"""
        self.clear_screen()
        self.print_header()
        
        print(Fore.YELLOW + "💰 Simulate Trade\n")
        print(f"Available Cash: ${self.portfolio.cash_balance:,.2f}\n")
        
        coin_id = input(Fore.CYAN + "Enter coin ID (e.g., bitcoin): " + Style.RESET_ALL).strip().lower()
        amount = input(Fore.CYAN + "Enter investment amount ($): " + Style.RESET_ALL).strip()
        
        try:
            amount = float(amount)
            
            if amount > self.portfolio.cash_balance:
                print(Fore.RED + "Insufficient funds!")
                return
            
            # Get current price
            live_prices = self.data_fetcher.get_live_prices([coin_id])
            
            if coin_id not in live_prices:
                print(Fore.RED + "Invalid coin ID!")
                return
            
            price = live_prices[coin_id]['price']
            quantity = amount / price
            
            # Execute trade
            success = self.portfolio.add_position(coin_id, quantity, price, coin_id.upper())
            
            if success:
                print(Fore.GREEN + f"\n✅ Trade Executed Successfully!")
                print(f"Bought {quantity:.8f} {coin_id.upper()} at ${price:,.6f}")
                print(f"Total Cost: ${amount:,.2f}")
                print(f"Remaining Cash: ${self.portfolio.cash_balance:,.2f}")
            else:
                print(Fore.RED + "Trade failed!")
                
        except ValueError:
            print(Fore.RED + "Invalid amount!")
    
    def show_trade_history(self):
        """Show trade history"""
        self.clear_screen()
        self.print_header()
        
        print(Fore.CYAN + "📜 TRADE HISTORY")
        print("=" * 80)
        
        history = self.portfolio.get_trade_history(limit=20)
        
        if history:
            history_data = []
            for trade in history:
                pl = trade.get('profit_loss', 0)
                history_data.append([
                    trade['type'],
                    trade['symbol'],
                    f"{trade['quantity']:.8f}",
                    f"${trade['price']:,.6f}",
                    f"${trade.get('cost', trade.get('proceeds', 0)):,.2f}",
                    self._format_profit_loss(pl) if pl else "N/A",
                    trade['timestamp'][:19]
                ])
            
            headers = ["Type", "Symbol", "Quantity", "Price", "Amount", "P/L", "Timestamp"]
            print(tabulate(history_data, headers=headers, tablefmt="grid"))
        else:
            print(Fore.YELLOW + "No trade history available.")
    
    def run(self):
        """Main application loop"""
        while True:
            self.clear_screen()
            self.print_header()
            self.show_main_menu()
            
            choice = input(Fore.CYAN + "\nSelect option: " + Style.RESET_ALL).strip()
            
            if choice == '1':
                self.get_trade_suggestions()
            elif choice == '2':
                self.show_market_overview()
            elif choice == '3':
                self.view_portfolio()
            elif choice == '4':
                self.analyze_coin()
            elif choice == '5':
                self.show_top_gainers()
            elif choice == '6':
                self.show_trending()
            elif choice == '7':
                self.simulate_trade()
            elif choice == '8':
                self.show_trade_history()
            elif choice == '9':
                print(Fore.YELLOW + f"\n⚙️  Current Settings:")
                print(f"  Wallet Size: ${Config.WALLET_SIZE:,.2f}")
                print(f"  Risk Level: {Config.RISK_LEVEL}")
                print(f"  Max Position Size: {Config.MAX_POSITION_SIZE * 100}%")
                print(f"  Stop Loss: {Config.STOP_LOSS_PERCENT}%")
                print(f"  Take Profit: {Config.TAKE_PROFIT_PERCENT}%")
            elif choice == '0':
                print(Fore.YELLOW + "\n👋 Thank you for using CryptoAI! Goodbye!")
                break
            else:
                print(Fore.RED + "\n❌ Invalid option. Please try again.")
            
            if choice != '0':
                input(Fore.CYAN + "\nPress Enter to continue..." + Style.RESET_ALL)

if __name__ == "__main__":
    try:
        app = CryptoAI()
        app.run()
    except KeyboardInterrupt:
        print(Fore.YELLOW + "\n\n👋 Application terminated by user. Goodbye!")
    except Exception as e:
        print(Fore.RED + f"\n❌ An error occurred: {e}")
        import traceback
        traceback.print_exc()

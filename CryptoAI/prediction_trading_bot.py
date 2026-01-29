"""
Coinbase BTC Prediction Market Trading Bot
Automated bot that executes trades based on prediction market signals
"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import time
import json
from pathlib import Path

from prediction_market_analyzer import PredictionMarketAnalyzer
from portfolio import Portfolio
from config import Config


class PredictionTradingBot:
    """Automated trading bot for BTC prediction markets"""
    
    def __init__(self, 
                 portfolio: Optional[Portfolio] = None,
                 risk_level: str = 'medium',
                 auto_trade: bool = False,
                 min_confidence: float = 0.6):
        """
        Initialize the prediction trading bot
        
        Args:
            portfolio: Portfolio instance (creates new if None)
            risk_level: Risk level for position sizing (low, medium, high)
            auto_trade: Whether to automatically execute trades
            min_confidence: Minimum confidence threshold for trades (0.0-1.0)
        """
        self.analyzer = PredictionMarketAnalyzer(auto_train=True)
        self.portfolio = portfolio or Portfolio()
        self.risk_level = risk_level
        self.auto_trade = auto_trade
        self.min_confidence = min_confidence
        
        # Bot state
        self.is_running = False
        self.trade_history = []
        self.last_signal = None
        self.last_trade_time = None
        
        # Trading parameters
        self.cooldown_period = timedelta(hours=1)  # Min time between trades
        self.max_open_positions = 3
        
        # Performance tracking
        self.stats = {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'total_profit_usd': 0.0,
            'best_trade_pct': 0.0,
            'worst_trade_pct': 0.0,
            'win_rate': 0.0
        }
        
        print(f"Prediction Trading Bot initialized")
        print(f"  Risk Level: {risk_level}")
        print(f"  Auto-Trade: {auto_trade}")
        print(f"  Min Confidence: {min_confidence:.0%}")
    
    def start(self, interval_seconds: int = 60):
        """
        Start the trading bot
        
        Args:
            interval_seconds: Analysis interval in seconds
        """
        self.is_running = True
        print(f"\n🤖 Bot started - analyzing every {interval_seconds}s")
        print(f"Portfolio Value: ${self.portfolio.get_total_value():,.2f}")
        print(f"Available Cash: ${self.portfolio.cash:,.2f}\n")
        
        try:
            while self.is_running:
                self._trading_cycle()
                time.sleep(interval_seconds)
        except KeyboardInterrupt:
            print("\n⏸️  Bot stopped by user")
            self.stop()
    
    def stop(self):
        """Stop the trading bot"""
        self.is_running = False
        self._print_performance_summary()
    
    def _trading_cycle(self):
        """Execute one trading cycle"""
        try:
            # Get current analysis
            analysis = self.analyzer.analyze_market()
            
            if 'error' in analysis:
                print(f"⚠️  Analysis error: {analysis['error']}")
                return
            
            current_price = analysis['current_price']
            overall_signal = analysis['overall_signal']
            
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] BTC: ${current_price:,.2f}")
            print(f"Signal: {overall_signal['signal']} | "
                  f"Confidence: {overall_signal['confidence']:.1%} | "
                  f"Score: {overall_signal['score']}/100")
            
            # Check if we should trade
            if self._should_trade(overall_signal):
                # Get trade recommendations
                portfolio_value = self.portfolio.get_total_value()
                recommendations = self.analyzer.get_trade_recommendations(
                    portfolio_value=portfolio_value,
                    risk_level=self.risk_level
                )
                
                if recommendations:
                    for rec in recommendations:
                        self._execute_recommendation(rec, analysis)
            
            # Check existing positions for exits
            self._manage_positions(current_price, overall_signal)
            
            self.last_signal = overall_signal
            
        except Exception as e:
            print(f"❌ Error in trading cycle: {e}")
    
    def _should_trade(self, signal: Dict) -> bool:
        """Determine if we should consider trading"""
        # Check confidence threshold
        if signal['confidence'] < self.min_confidence:
            return False
        
        # Check cooldown period
        if self.last_trade_time:
            time_since_last = datetime.now() - self.last_trade_time
            if time_since_last < self.cooldown_period:
                return False
        
        # Check max positions
        if len(self.portfolio.positions) >= self.max_open_positions:
            return False
        
        # Only trade on strong signals
        if signal['signal'] in ['neutral']:
            return False
        
        return True
    
    def _execute_recommendation(self, rec: Dict, analysis: Dict):
        """Execute a trade recommendation"""
        action = rec['action']
        
        if action == 'BUY':
            self._execute_buy(rec, analysis)
        elif action == 'SELL':
            self._execute_sell(rec, analysis)
    
    def _execute_buy(self, rec: Dict, analysis: Dict):
        """Execute a buy trade"""
        amount_usd = rec['amount_usd']
        entry_price = rec['entry_price']
        amount_btc = rec['amount_btc']
        
        # Check if we have enough cash
        if self.portfolio.cash < amount_usd:
            print(f"⚠️  Insufficient funds: ${self.portfolio.cash:,.2f} < ${amount_usd:,.2f}")
            return
        
        print(f"\n{'🔴 SIMULATION' if not self.auto_trade else '🟢 LIVE'} BUY SIGNAL")
        print(f"  Amount: {amount_btc:.8f} BTC (${amount_usd:,.2f})")
        print(f"  Entry: ${entry_price:,.2f}")
        print(f"  Stop Loss: ${rec['stop_loss']:,.2f}")
        print(f"  Take Profit: ${rec['take_profit']:,.2f}")
        print(f"  Confidence: {rec['confidence']:.1%}")
        print(f"  Reasons: {', '.join(rec['reasons'][:3])}")
        
        if self.auto_trade:
            # Execute trade
            success = self.portfolio.add_position(
                coin_id='bitcoin',
                quantity=amount_btc,
                price=entry_price
            )
            
            if success:
                # Record trade
                trade_record = {
                    'timestamp': datetime.now().isoformat(),
                    'action': 'BUY',
                    'asset': 'BTC',
                    'amount': amount_btc,
                    'price': entry_price,
                    'total_usd': amount_usd,
                    'stop_loss': rec['stop_loss'],
                    'take_profit': rec['take_profit'],
                    'signal': rec['signal'],
                    'confidence': rec['confidence'],
                    'analysis': {
                        'technical_signal': analysis.get('technical_analysis', {}).get('overall_signal'),
                        'ml_prediction': analysis.get('ml_prediction', {}).get('direction'),
                        'fear_greed': analysis.get('sentiment', {}).get('fear_greed_index')
                    }
                }
                
                self.trade_history.append(trade_record)
                self.stats['total_trades'] += 1
                self.last_trade_time = datetime.now()
                
                print(f"✅ Trade executed successfully")
                print(f"Portfolio Value: ${self.portfolio.get_total_value():,.2f}")
        else:
            print(f"💡 SIMULATION MODE - Trade not executed")
    
    def _execute_sell(self, rec: Dict, analysis: Dict):
        """Execute a sell trade"""
        # Check if we have BTC position
        if 'bitcoin' not in self.portfolio.positions:
            print(f"⚠️  No BTC position to sell")
            return
        
        position = self.portfolio.positions['bitcoin']
        exit_price = rec['exit_price']
        
        # Calculate P&L
        entry_price = position.get('avg_price', 0)
        quantity = position.get('quantity', 0)
        pnl_pct = ((exit_price - entry_price) / entry_price) * 100 if entry_price else 0
        pnl_usd = (exit_price - entry_price) * quantity
        
        print(f"\n{'🔴 SIMULATION' if not self.auto_trade else '🟢 LIVE'} SELL SIGNAL")
        print(f"  Amount: {quantity:.8f} BTC")
        print(f"  Entry: ${entry_price:,.2f}")
        print(f"  Exit: ${exit_price:,.2f}")
        print(f"  P&L: ${pnl_usd:,.2f} ({pnl_pct:+.2f}%)")
        print(f"  Confidence: {rec['confidence']:.1%}")
        
        if self.auto_trade:
            # Execute trade
            success = self.portfolio.close_position(
                coin_id='bitcoin',
                current_price=exit_price
            )
            
            if success:
                # Record trade
                trade_record = {
                    'timestamp': datetime.now().isoformat(),
                    'action': 'SELL',
                    'asset': 'BTC',
                    'amount': quantity,
                    'price': exit_price,
                    'pnl_usd': pnl_usd,
                    'pnl_pct': pnl_pct,
                    'signal': rec['signal'],
                    'confidence': rec['confidence']
                }
                
                self.trade_history.append(trade_record)
                self.stats['total_trades'] += 1
                
                if pnl_usd > 0:
                    self.stats['winning_trades'] += 1
                else:
                    self.stats['losing_trades'] += 1
                
                self.stats['total_profit_usd'] += pnl_usd
                self.stats['best_trade_pct'] = max(self.stats['best_trade_pct'], pnl_pct)
                self.stats['worst_trade_pct'] = min(self.stats['worst_trade_pct'], pnl_pct)
                
                if self.stats['total_trades'] > 0:
                    self.stats['win_rate'] = self.stats['winning_trades'] / self.stats['total_trades']
                
                self.last_trade_time = datetime.now()
                
                print(f"✅ Position closed")
                print(f"Portfolio Value: ${self.portfolio.get_total_value():,.2f}")
        else:
            print(f"💡 SIMULATION MODE - Trade not executed")
    
    def _manage_positions(self, current_price: float, signal: Dict):
        """Manage existing positions (stop loss, take profit)"""
        if 'bitcoin' not in self.portfolio.positions:
            return
        
        position = self.portfolio.positions['bitcoin']
        entry_price = position.get('avg_price', 0)
        
        # Calculate current P&L
        pnl_pct = ((current_price - entry_price) / entry_price) * 100 if entry_price else 0
        
        # Check stop loss (5% default)
        if pnl_pct <= -5.0:
            print(f"\n🛑 STOP LOSS TRIGGERED at ${current_price:,.2f} ({pnl_pct:.2f}%)")
            self._execute_sell({
                'action': 'SELL',
                'exit_price': current_price,
                'confidence': 1.0
            }, {})
        
        # Check take profit (10% default)
        elif pnl_pct >= 10.0:
            print(f"\n🎯 TAKE PROFIT TRIGGERED at ${current_price:,.2f} (+{pnl_pct:.2f}%)")
            self._execute_sell({
                'action': 'SELL',
                'exit_price': current_price,
                'confidence': 1.0
            }, {})
        
        # Check if signal reversed strongly
        elif signal['signal'] in ['strong_sell', 'sell'] and signal['confidence'] > 0.7:
            print(f"\n⚠️  Signal reversal detected - consider exit")
    
    def _print_performance_summary(self):
        """Print bot performance summary"""
        print("\n" + "="*60)
        print("📊 BOT PERFORMANCE SUMMARY")
        print("="*60)
        print(f"Total Trades: {self.stats['total_trades']}")
        print(f"Winning Trades: {self.stats['winning_trades']}")
        print(f"Losing Trades: {self.stats['losing_trades']}")
        print(f"Win Rate: {self.stats['win_rate']:.1%}")
        print(f"Total Profit: ${self.stats['total_profit_usd']:+,.2f}")
        print(f"Best Trade: {self.stats['best_trade_pct']:+.2f}%")
        print(f"Worst Trade: {self.stats['worst_trade_pct']:+.2f}%")
        print(f"\nFinal Portfolio Value: ${self.portfolio.get_total_value():,.2f}")
        print(f"Starting Value: $1000.00")
        print(f"Return: {((self.portfolio.get_total_value() - 1000) / 1000) * 100:+.2f}%")
        print("="*60)
    
    def get_status(self) -> Dict:
        """Get current bot status"""
        return {
            'is_running': self.is_running,
            'portfolio_value': self.portfolio.get_total_value(),
            'cash': self.portfolio.cash,
            'positions': len(self.portfolio.positions),
            'last_signal': self.last_signal,
            'stats': self.stats,
            'timestamp': datetime.now().isoformat()
        }
    
    def save_trade_history(self, filepath: str = 'trade_history.json'):
        """Save trade history to file"""
        with open(filepath, 'w') as f:
            json.dump({
                'trades': self.trade_history,
                'stats': self.stats,
                'timestamp': datetime.now().isoformat()
            }, f, indent=2)
        print(f"Trade history saved to {filepath}")


if __name__ == "__main__":
    import sys
    
    print("="*60)
    print("🤖 COINBASE BTC PREDICTION MARKET BOT")
    print("="*60)
    
    # Parse arguments
    auto_trade = '--live' in sys.argv
    risk_level = 'high' if '--high-risk' in sys.argv else 'low' if '--low-risk' in sys.argv else 'medium'
    
    if auto_trade:
        print("\n⚠️  WARNING: LIVE TRADING MODE ENABLED")
        print("This will execute real trades with your portfolio!")
        response = input("Type 'CONFIRM' to continue: ")
        if response != 'CONFIRM':
            print("Exiting...")
            sys.exit(0)
    
    # Create bot
    bot = PredictionTradingBot(
        risk_level=risk_level,
        auto_trade=auto_trade,
        min_confidence=0.65
    )
    
    print(f"\nStarting bot in {'LIVE' if auto_trade else 'SIMULATION'} mode...")
    print("Press Ctrl+C to stop\n")
    
    try:
        bot.start(interval_seconds=60)
    except KeyboardInterrupt:
        print("\nStopping bot...")
        bot.stop()
        bot.save_trade_history()

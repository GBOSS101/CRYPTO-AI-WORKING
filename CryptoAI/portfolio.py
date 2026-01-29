"""
Portfolio Management System
Tracks portfolio, positions, and performance
"""
from typing import Dict, List, Optional
from datetime import datetime
import json
import os

class Portfolio:
    def __init__(self, initial_balance: float = 1000):
        self.initial_balance = initial_balance
        self.cash_balance = initial_balance
        self.positions = {}  # {coin_id: {quantity, avg_price, current_price}}
        self.trade_history = []
        self.portfolio_file = 'portfolio_data.json'
        
        self._load_portfolio()
    
    def _load_portfolio(self):
        """Load portfolio from file if exists"""
        if os.path.exists(self.portfolio_file):
            try:
                with open(self.portfolio_file, 'r') as f:
                    data = json.load(f)
                    self.cash_balance = data.get('cash_balance', self.initial_balance)
                    self.positions = data.get('positions', {})
                    self.trade_history = data.get('trade_history', [])
            except Exception as e:
                print(f"Error loading portfolio: {e}")
    
    def _save_portfolio(self):
        """Save portfolio to file"""
        try:
            data = {
                'initial_balance': self.initial_balance,
                'cash_balance': self.cash_balance,
                'positions': self.positions,
                'trade_history': self.trade_history,
                'last_updated': datetime.now().isoformat()
            }
            with open(self.portfolio_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving portfolio: {e}")
    
    def add_position(
        self,
        coin_id: str,
        quantity: float,
        price: float,
        symbol: str = None
    ) -> bool:
        """
        Add or update a position (simulated buy)
        """
        cost = quantity * price
        
        if cost > self.cash_balance:
            return False
        
        if coin_id in self.positions:
            # Update existing position (average price)
            pos = self.positions[coin_id]
            total_quantity = pos['quantity'] + quantity
            total_cost = (pos['quantity'] * pos['avg_price']) + cost
            avg_price = total_cost / total_quantity
            
            self.positions[coin_id] = {
                'symbol': symbol or coin_id.upper(),
                'quantity': total_quantity,
                'avg_price': avg_price,
                'current_price': price,
                'last_updated': datetime.now().isoformat()
            }
        else:
            # New position
            self.positions[coin_id] = {
                'symbol': symbol or coin_id.upper(),
                'quantity': quantity,
                'avg_price': price,
                'current_price': price,
                'last_updated': datetime.now().isoformat()
            }
        
        self.cash_balance -= cost
        
        # Record trade
        self.trade_history.append({
            'type': 'BUY',
            'coin_id': coin_id,
            'symbol': symbol or coin_id.upper(),
            'quantity': quantity,
            'price': price,
            'cost': cost,
            'timestamp': datetime.now().isoformat()
        })
        
        self._save_portfolio()
        return True
    
    def remove_position(
        self,
        coin_id: str,
        quantity: float,
        price: float
    ) -> bool:
        """
        Remove or reduce a position (simulated sell)
        """
        if coin_id not in self.positions:
            return False
        
        pos = self.positions[coin_id]
        
        if quantity > pos['quantity']:
            return False
        
        proceeds = quantity * price
        self.cash_balance += proceeds
        
        # Record trade
        profit_loss = (price - pos['avg_price']) * quantity
        
        self.trade_history.append({
            'type': 'SELL',
            'coin_id': coin_id,
            'symbol': pos['symbol'],
            'quantity': quantity,
            'price': price,
            'proceeds': proceeds,
            'profit_loss': profit_loss,
            'timestamp': datetime.now().isoformat()
        })
        
        if quantity == pos['quantity']:
            # Close position
            del self.positions[coin_id]
        else:
            # Reduce position
            self.positions[coin_id]['quantity'] -= quantity
        
        self._save_portfolio()
        return True
    
    def update_prices(self, live_prices: Dict[str, Dict]):
        """
        Update current prices for all positions
        """
        for coin_id in self.positions:
            if coin_id in live_prices:
                self.positions[coin_id]['current_price'] = live_prices[coin_id]['price']
                self.positions[coin_id]['last_updated'] = datetime.now().isoformat()
        
        self._save_portfolio()
    
    def get_portfolio_value(self) -> float:
        """
        Calculate total portfolio value
        """
        total = self.cash_balance
        
        for coin_id, pos in self.positions.items():
            total += pos['quantity'] * pos['current_price']
        
        return total

    # Backwards-compatible helpers
    def get_total_value(self) -> float:
        """Alias for get_portfolio_value() used by other modules."""
        return self.get_portfolio_value()

    @property
    def cash(self) -> float:
        """Alias for cash_balance used by other modules."""
        return self.cash_balance

    def close_position(self, coin_id: str, current_price: float) -> bool:
        """Close a full position (compatibility shim)."""
        if coin_id not in self.positions:
            return False
        quantity = self.positions[coin_id]['quantity']
        return self.remove_position(coin_id, quantity, current_price)
    
    def get_portfolio_performance(self) -> Dict:
        """
        Get portfolio performance metrics
        """
        current_value = self.get_portfolio_value()
        total_return = current_value - self.initial_balance
        return_percent = (total_return / self.initial_balance) * 100
        
        return {
            'initial_balance': self.initial_balance,
            'current_value': round(current_value, 2),
            'cash_balance': round(self.cash_balance, 2),
            'invested_value': round(current_value - self.cash_balance, 2),
            'total_return': round(total_return, 2),
            'return_percent': round(return_percent, 2),
            'num_positions': len(self.positions),
            'num_trades': len(self.trade_history)
        }
    
    def get_positions_summary(self) -> List[Dict]:
        """
        Get summary of all positions
        """
        summary = []
        
        for coin_id, pos in self.positions.items():
            current_value = pos['quantity'] * pos['current_price']
            cost_basis = pos['quantity'] * pos['avg_price']
            profit_loss = current_value - cost_basis
            profit_loss_percent = (profit_loss / cost_basis) * 100 if cost_basis > 0 else 0
            
            summary.append({
                'coin_id': coin_id,
                'symbol': pos['symbol'],
                'quantity': round(pos['quantity'], 8),
                'avg_price': round(pos['avg_price'], 6),
                'current_price': round(pos['current_price'], 6),
                'cost_basis': round(cost_basis, 2),
                'current_value': round(current_value, 2),
                'profit_loss': round(profit_loss, 2),
                'profit_loss_percent': round(profit_loss_percent, 2),
                'last_updated': pos['last_updated']
            })
        
        return summary
    
    def get_trade_history(self, limit: int = 10) -> List[Dict]:
        """
        Get recent trade history
        """
        return self.trade_history[-limit:][::-1]  # Most recent first
    
    def reset_portfolio(self):
        """
        Reset portfolio to initial state
        """
        self.cash_balance = self.initial_balance
        self.positions = {}
        self.trade_history = []
        self._save_portfolio()

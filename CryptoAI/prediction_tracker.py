"""
Prediction Accuracy Tracker
Tracks all predictions and their outcomes for performance analysis
"""
import json
import os
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import pandas as pd
import numpy as np


class PredictionTracker:
    """Track prediction accuracy and calculate performance metrics"""
    
    def __init__(self, filename: str = 'prediction_history.json'):
        """
        Initialize prediction tracker
        
        Args:
            filename: JSON file to store prediction history
        """
        self.filename = filename
        self.history = []
        self.load_history()
    
    def load_history(self):
        """Load prediction history from JSON file"""
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r') as f:
                    self.history = json.load(f)
                print(f"✅ Loaded {len(self.history)} historical predictions")
            except Exception as e:
                print(f"⚠️ Error loading history: {e}")
                self.history = []
        else:
            print("📝 Creating new prediction history file")
            self.history = []
    
    def save_history(self):
        """Save prediction history to JSON file"""
        try:
            with open(self.filename, 'w') as f:
                json.dump(self.history, f, indent=2)
        except Exception as e:
            print(f"❌ Error saving history: {e}")
    
    def record_prediction(self, 
                         current_price: float,
                         predicted_price: float,
                         timeframe: str,
                         confidence: float,
                         hours_ahead: float,
                         model_type: str = 'ensemble',
                         metadata: Optional[Dict] = None) -> str:
        """
        Record a new prediction
        
        Args:
            current_price: Current BTC price when prediction made
            predicted_price: Predicted BTC price
            timeframe: Prediction timeframe (15min, 1hr, etc.)
            confidence: Model confidence (0-1)
            hours_ahead: Hours until prediction expires
            model_type: Type of model used
            metadata: Additional prediction metadata
        
        Returns:
            Prediction ID
        """
        prediction_time = datetime.now()
        expiry_time = prediction_time + timedelta(hours=hours_ahead)
        
        prediction = {
            'id': f"{prediction_time.strftime('%Y%m%d_%H%M%S')}_{timeframe}",
            'timestamp': prediction_time.isoformat(),
            'expiry_time': expiry_time.isoformat(),
            'timeframe': timeframe,
            'hours_ahead': hours_ahead,
            'current_price': round(current_price, 2),
            'predicted_price': round(predicted_price, 2),
            'predicted_change_pct': round(((predicted_price - current_price) / current_price) * 100, 2),
            'confidence': round(confidence, 3),
            'model_type': model_type,
            'metadata': metadata or {},
            # Outcome fields (filled later)
            'actual_price': None,
            'actual_change_pct': None,
            'error': None,
            'error_pct': None,
            'outcome': None,  # 'correct' or 'incorrect'
            'checked_at': None
        }
        
        self.history.append(prediction)
        self.save_history()
        
        return prediction['id']
    
    def check_expired_predictions(self, price_fetcher_func) -> int:
        """
        Check outcomes for expired predictions
        
        Args:
            price_fetcher_func: Function to fetch historical price at specific time
        
        Returns:
            Number of predictions checked
        """
        now = datetime.now()
        checked_count = 0
        
        for pred in self.history:
            # Skip if already checked
            if pred.get('outcome') is not None:
                continue
            
            # Check if prediction has expired
            expiry = datetime.fromisoformat(pred['expiry_time'])
            
            if now >= expiry:
                try:
                    # Fetch actual price at expiry time
                    actual_price = price_fetcher_func(expiry)
                    
                    if actual_price > 0:
                        # Calculate metrics
                        pred['actual_price'] = round(actual_price, 2)
                        pred['actual_change_pct'] = round(
                            ((actual_price - pred['current_price']) / pred['current_price']) * 100, 2
                        )
                        pred['error'] = round(abs(actual_price - pred['predicted_price']), 2)
                        pred['error_pct'] = round(
                            (abs(actual_price - pred['predicted_price']) / pred['current_price']) * 100, 2
                        )
                        
                        # Determine outcome (within 2% tolerance for 'correct')
                        if pred['error_pct'] <= 2.0:
                            pred['outcome'] = 'correct'
                        else:
                            pred['outcome'] = 'incorrect'
                        
                        pred['checked_at'] = now.isoformat()
                        checked_count += 1
                
                except Exception as e:
                    print(f"Error checking prediction {pred['id']}: {e}")
        
        if checked_count > 0:
            self.save_history()
            print(f"✅ Checked {checked_count} expired predictions")
        
        return checked_count
    
    def get_statistics(self, timeframe: Optional[str] = None, 
                      last_n_days: Optional[int] = None) -> Dict:
        """
        Calculate performance statistics
        
        Args:
            timeframe: Filter by specific timeframe (optional)
            last_n_days: Only include predictions from last N days (optional)
        
        Returns:
            Dict with performance metrics
        """
        # Filter predictions
        filtered = [p for p in self.history if p.get('outcome') is not None]
        
        if timeframe:
            filtered = [p for p in filtered if p['timeframe'] == timeframe]
        
        if last_n_days:
            cutoff = (datetime.now() - timedelta(days=last_n_days)).isoformat()
            filtered = [p for p in filtered if p['timestamp'] >= cutoff]
        
        if not filtered:
            return {
                'total_predictions': 0,
                'error': 'No completed predictions found'
            }
        
        # Calculate statistics
        total = len(filtered)
        correct = len([p for p in filtered if p['outcome'] == 'correct'])
        incorrect = total - correct
        
        errors = [p['error'] for p in filtered if p['error'] is not None]
        error_pcts = [p['error_pct'] for p in filtered if p['error_pct'] is not None]
        
        # Calculate Brier score (for probability calibration)
        brier_score = self._calculate_brier_score(filtered)
        
        # Calculate profit/loss (assuming equal position sizes)
        total_pnl_pct = sum([
            p['actual_change_pct'] if p['predicted_change_pct'] > 0 else -p['actual_change_pct']
            for p in filtered
        ])
        
        stats = {
            'total_predictions': total,
            'correct': correct,
            'incorrect': incorrect,
            'win_rate': round(correct / total * 100, 2) if total > 0 else 0,
            'avg_error': round(np.mean(errors), 2) if errors else 0,
            'median_error': round(np.median(errors), 2) if errors else 0,
            'avg_error_pct': round(np.mean(error_pcts), 2) if error_pcts else 0,
            'median_error_pct': round(np.median(error_pcts), 2) if error_pcts else 0,
            'brier_score': round(brier_score, 4),
            'total_pnl_pct': round(total_pnl_pct, 2),
            'avg_pnl_per_trade': round(total_pnl_pct / total, 2) if total > 0 else 0,
            'timeframe': timeframe or 'all',
            'last_n_days': last_n_days or 'all_time'
        }
        
        # Add confidence distribution
        confidences = [p['confidence'] for p in filtered]
        stats['avg_confidence'] = round(np.mean(confidences), 3) if confidences else 0
        stats['confidence_std'] = round(np.std(confidences), 3) if confidences else 0
        
        return stats
    
    def _calculate_brier_score(self, predictions: List[Dict]) -> float:
        """
        Calculate Brier score for probability calibration
        Lower is better (0 = perfect calibration)
        
        Brier Score = (1/N) * Σ(probability - outcome)²
        """
        if not predictions:
            return 0.0
        
        scores = []
        for pred in predictions:
            confidence = pred.get('confidence', 0.5)
            outcome = 1.0 if pred['outcome'] == 'correct' else 0.0
            scores.append((confidence - outcome) ** 2)
        
        return float(np.mean(scores)) if scores else 0.0
    
    def get_recent_predictions(self, n: int = 10) -> List[Dict]:
        """Get N most recent predictions"""
        return sorted(self.history, key=lambda x: x['timestamp'], reverse=True)[:n]
    
    def get_predictions_by_timeframe(self) -> Dict:
        """Get statistics grouped by timeframe"""
        timeframes = set([p['timeframe'] for p in self.history if 'outcome' in p])
        
        stats_by_timeframe = {}
        for tf in timeframes:
            stats_by_timeframe[tf] = self.get_statistics(timeframe=tf)
        
        return stats_by_timeframe
    
    def export_to_csv(self, filename: str = 'predictions_export.csv'):
        """Export prediction history to CSV for analysis"""
        if not self.history:
            print("⚠️ No predictions to export")
            return
        
        df = pd.DataFrame(self.history)
        df.to_csv(filename, index=False)
        print(f"✅ Exported {len(df)} predictions to {filename}")
    
    def print_summary(self):
        """Print a formatted summary of prediction performance"""
        print("\n" + "=" * 80)
        print("PREDICTION PERFORMANCE SUMMARY")
        print("=" * 80)
        
        # Overall stats
        overall = self.get_statistics()
        
        if 'error' in overall:
            print(f"\n⚠️ {overall['error']}")
            return
        
        print(f"\n📊 Overall Performance:")
        print(f"   Total Predictions: {overall['total_predictions']}")
        print(f"   Correct: {overall['correct']} | Incorrect: {overall['incorrect']}")
        print(f"   Win Rate: {overall['win_rate']:.2f}%")
        print(f"   Average Error: ${overall['avg_error']:.2f} ({overall['avg_error_pct']:.2f}%)")
        print(f"   Brier Score: {overall['brier_score']:.4f} (lower is better)")
        print(f"   Total P&L: {overall['total_pnl_pct']:+.2f}%")
        print(f"   Avg P&L per Trade: {overall['avg_pnl_per_trade']:+.2f}%")
        
        # Stats by timeframe
        print(f"\n📈 Performance by Timeframe:")
        timeframe_stats = self.get_predictions_by_timeframe()
        
        for tf, stats in sorted(timeframe_stats.items()):
            if 'error' not in stats and stats['total_predictions'] > 0:
                print(f"\n   {tf.upper()}:")
                print(f"      Predictions: {stats['total_predictions']}")
                print(f"      Win Rate: {stats['win_rate']:.2f}%")
                print(f"      Avg Error: ${stats['avg_error']:.2f} ({stats['avg_error_pct']:.2f}%)")
                print(f"      Avg P&L: {stats['avg_pnl_per_trade']:+.2f}%")
        
        # Recent predictions
        print(f"\n🕐 Last 5 Predictions:")
        recent = self.get_recent_predictions(5)
        
        for i, pred in enumerate(recent, 1):
            outcome_emoji = "✅" if pred.get('outcome') == 'correct' else "❌" if pred.get('outcome') == 'incorrect' else "⏳"
            print(f"\n   {i}. {outcome_emoji} {pred['timeframe'].upper()} - {pred['timestamp'][:10]}")
            print(f"      Predicted: ${pred['predicted_price']:,.2f} ({pred['predicted_change_pct']:+.2f}%)")
            
            if pred.get('actual_price'):
                print(f"      Actual: ${pred['actual_price']:,.2f} ({pred['actual_change_pct']:+.2f}%)")
                print(f"      Error: ${pred['error']:.2f} ({pred['error_pct']:.2f}%)")
        
        print("\n" + "=" * 80 + "\n")


if __name__ == "__main__":
    # Test the prediction tracker
    print("🧪 Testing Prediction Tracker...\n")
    
    tracker = PredictionTracker(filename='test_prediction_history.json')
    
    # Record some test predictions
    print("📝 Recording test predictions...")
    
    tracker.record_prediction(
        current_price=90000,
        predicted_price=91500,
        timeframe='1hr',
        confidence=0.75,
        hours_ahead=1.0,
        metadata={'signal': 'buy', 'technical_score': 65}
    )
    
    tracker.record_prediction(
        current_price=90000,
        predicted_price=92000,
        timeframe='24hr',
        confidence=0.68,
        hours_ahead=24.0,
        metadata={'signal': 'strong_buy', 'technical_score': 72}
    )
    
    print(f"✅ Recorded {len(tracker.history)} predictions\n")
    
    # Display summary
    tracker.print_summary()
    
    print("✅ Test complete!")

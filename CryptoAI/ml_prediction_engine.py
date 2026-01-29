"""
Machine Learning Prediction Engine for BTC
Combines LSTM, XGBoost, and technical analysis for price predictions
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, TYPE_CHECKING
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    print("Warning: XGBoost not installed. Install with: pip install xgboost")

try:
    from sklearn.preprocessing import MinMaxScaler
    from sklearn.ensemble import RandomForestRegressor
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    print("Warning: scikit-learn not installed. Install with: pip install scikit-learn")

try:
    import tensorflow as tf  # type: ignore[import-not-found]
    from tensorflow import keras  # type: ignore[import-not-found]
    from tensorflow.keras.models import Sequential  # type: ignore[import-not-found]
    from tensorflow.keras.layers import LSTM, Dense, Dropout  # type: ignore[import-not-found]
    TENSORFLOW_AVAILABLE = True
except ImportError:
    TENSORFLOW_AVAILABLE = False
    print("Warning: TensorFlow not installed. Install with: pip install tensorflow")


class MLPredictionEngine:
    """Hybrid ML prediction engine using LSTM + XGBoost"""
    
    def __init__(self, lookback_period: int = 60, prediction_horizon: int = 24):
        """
        Initialize the ML prediction engine
        
        Args:
            lookback_period: Number of hours to look back for patterns
            prediction_horizon: Hours ahead to predict (1h, 4h, 24h)
        """
        self.lookback_period = lookback_period
        self.prediction_horizon = prediction_horizon
        self.scaler = MinMaxScaler() if SKLEARN_AVAILABLE else None
        
        # Model weights for ensemble
        self.model_weights = {
            'lstm': 0.4,
            'xgboost': 0.3,
            'technical': 0.3
        }
        
        # Pre-trained models (will be None until trained)
        self.lstm_model = None
        self.xgb_model = None
        
    def prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Prepare features from historical data
        
        Args:
            df: DataFrame with OHLCV data
        
        Returns:
            DataFrame with engineered features
        """
        if df.empty:
            return df
        
        df = df.copy()
        
        # Price features
        df['returns'] = df['price'].pct_change()
        df['log_returns'] = np.log(df['price'] / df['price'].shift(1))
        
        # Moving averages
        for window in [7, 14, 21, 50]:
            df[f'sma_{window}'] = df['price'].rolling(window=window).mean()
            df[f'ema_{window}'] = df['price'].ewm(span=window).mean()
        
        # Volatility
        df['volatility_7'] = df['returns'].rolling(window=7).std()
        df['volatility_21'] = df['returns'].rolling(window=21).std()
        
        # Momentum indicators
        df['rsi'] = self._calculate_rsi(df['price'], period=14)
        df['macd'], df['macd_signal'] = self._calculate_macd(df['price'])
        
        # Volume features
        if 'volume' in df.columns:
            df['volume_sma_7'] = df['volume'].rolling(window=7).mean()
            df['volume_ratio'] = df['volume'] / df['volume_sma_7']
        
        # Price position relative to range
        df['high_14'] = df['price'].rolling(window=14).max()
        df['low_14'] = df['price'].rolling(window=14).min()
        df['price_position'] = (df['price'] - df['low_14']) / (df['high_14'] - df['low_14'])
        
        # Lag features
        for lag in [1, 2, 3, 6, 12, 24]:
            df[f'price_lag_{lag}'] = df['price'].shift(lag)
            df[f'returns_lag_{lag}'] = df['returns'].shift(lag)
        
        # Target variable (future price)
        df['target'] = df['price'].shift(-self.prediction_horizon)
        df['target_direction'] = (df['target'] > df['price']).astype(int)
        
        # Drop NaN values
        df = df.dropna()
        
        return df
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Relative Strength Index"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _calculate_macd(self, prices: pd.Series, 
                       fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series]:
        """Calculate MACD and signal line"""
        ema_fast = prices.ewm(span=fast).mean()
        ema_slow = prices.ewm(span=slow).mean()
        macd = ema_fast - ema_slow
        macd_signal = macd.ewm(span=signal).mean()
        return macd, macd_signal
    
    def train_xgboost_model(self, df: pd.DataFrame) -> Dict:
        """
        Train XGBoost regression model
        
        Args:
            df: Prepared DataFrame with features
        
        Returns:
            Dict with model performance metrics
        """
        if not XGBOOST_AVAILABLE:
            return {'error': 'XGBoost not available'}
        
        if df.empty or 'target' not in df.columns:
            return {'error': 'Invalid training data'}
        
        # Select features (exclude target and timestamp)
        feature_cols = [col for col in df.columns 
                       if col not in ['target', 'target_direction', 'timestamp']]
        
        X = df[feature_cols].values
        y = np.asarray(df['target'].values)
        
        # Train/test split (80/20)
        split_idx = int(len(X) * 0.8)
        X_train, X_test = X[:split_idx], X[split_idx:]
        y_train, y_test = y[:split_idx], y[split_idx:]
        
        # Train XGBoost
        self.xgb_model = xgb.XGBRegressor(
            n_estimators=100,
            learning_rate=0.05,
            max_depth=7,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42
        )
        
        self.xgb_model.fit(X_train, y_train)
        
        # Evaluate
        train_score = self.xgb_model.score(X_train, y_train)
        test_score = self.xgb_model.score(X_test, y_test)
        
        predictions = self.xgb_model.predict(X_test)
        mape = np.mean(np.abs((y_test - predictions) / y_test)) * 100
        
        return {
            'model': 'xgboost',
            'train_r2': train_score,
            'test_r2': test_score,
            'mape': mape,
            'feature_importance': dict(zip(feature_cols, 
                                          self.xgb_model.feature_importances_))
        }
    
    def train_lstm_model(self, df: pd.DataFrame) -> Dict:
        """
        Train LSTM neural network model
        
        Args:
            df: Prepared DataFrame with features
        
        Returns:
            Dict with model performance metrics
        """
        if not TENSORFLOW_AVAILABLE or not SKLEARN_AVAILABLE:
            return {'error': 'TensorFlow or sklearn not available'}

        if self.scaler is None:
            return {'error': 'Scaler not available'}
        
        if df.empty or 'target' not in df.columns:
            return {'error': 'Invalid training data'}
        
        # Use price and key features for LSTM
        feature_cols = ['price', 'volume', 'sma_7', 'ema_14', 'rsi', 'volatility_7']
        available_cols = [col for col in feature_cols if col in df.columns]
        
        if len(available_cols) < 2:
            return {'error': 'Insufficient features for LSTM'}
        
        data = df[available_cols].values
        
        # Scale data
        data_scaled = self.scaler.fit_transform(data)
        
        # Create sequences
        X, y = [], []
        for i in range(self.lookback_period, len(data_scaled) - self.prediction_horizon):
            X.append(data_scaled[i-self.lookback_period:i])
            y.append(data_scaled[i + self.prediction_horizon, 0])  # Predict price
        
        X, y = np.array(X), np.array(y)
        
        # Train/test split
        split_idx = int(len(X) * 0.8)
        X_train, X_test = X[:split_idx], X[split_idx:]
        y_train, y_test = y[:split_idx], y[split_idx:]
        
        # Build LSTM model
        self.lstm_model = Sequential([
            LSTM(50, return_sequences=True, input_shape=(X_train.shape[1], X_train.shape[2])),
            Dropout(0.2),
            LSTM(50, return_sequences=False),
            Dropout(0.2),
            Dense(25),
            Dense(1)
        ])
        
        self.lstm_model.compile(optimizer='adam', loss='mse', metrics=['mae'])
        
        # Train
        history = self.lstm_model.fit(
            X_train, y_train,
            validation_data=(X_test, y_test),
            epochs=50,
            batch_size=32,
            verbose=0
        )
        
        # Evaluate
        train_loss = history.history['loss'][-1]
        test_loss = history.history['val_loss'][-1]
        
        return {
            'model': 'lstm',
            'train_loss': train_loss,
            'test_loss': test_loss,
            'epochs': 50
        }
    
    def predict(self, df: pd.DataFrame, use_ensemble: bool = True) -> Dict:
        """
        Make price predictions using trained models
        
        Args:
            df: Current market data DataFrame
            use_ensemble: Whether to use ensemble of models
        
        Returns:
            Dict with predictions and confidence
        """
        predictions = {
            'timestamp': datetime.now().isoformat(),
            'current_price': 0.0,
            'predicted_price': 0.0,
            'predicted_change_pct': 0.0,
            'direction': 'neutral',
            'confidence': 0.0,
            'models_used': []
        }
        
        if df.empty:
            return predictions
        
        # Prepare features
        df_prepared = self.prepare_features(df)
        
        if df_prepared.empty:
            return predictions
        
        current_price = df_prepared['price'].iloc[-1]
        predictions['current_price'] = current_price
        
        # Get latest features
        feature_cols = [col for col in df_prepared.columns 
                       if col not in ['target', 'target_direction', 'timestamp']]
        latest_features = df_prepared[feature_cols].iloc[-1:].values
        
        ensemble_predictions = []
        weights = []
        
        # XGBoost prediction
        if self.xgb_model is not None and XGBOOST_AVAILABLE:
            try:
                xgb_pred = self.xgb_model.predict(latest_features)[0]
                ensemble_predictions.append(xgb_pred)
                weights.append(self.model_weights['xgboost'])
                predictions['models_used'].append('xgboost')
            except Exception as e:
                print(f"XGBoost prediction error: {e}")
        
        # LSTM prediction
        if self.lstm_model is not None and TENSORFLOW_AVAILABLE and SKLEARN_AVAILABLE:
            try:
                # Prepare LSTM input
                feature_cols_lstm = ['price', 'volume', 'sma_7', 'ema_14', 'rsi', 'volatility_7']
                available_cols = [col for col in feature_cols_lstm if col in df_prepared.columns]
                
                if self.scaler is None:
                    return predictions

                if len(df_prepared) >= self.lookback_period and len(available_cols) >= 2:
                    lstm_data = df_prepared[available_cols].iloc[-self.lookback_period:].values
                    lstm_data_scaled = self.scaler.transform(lstm_data)
                    lstm_input = lstm_data_scaled.reshape(1, self.lookback_period, -1)
                    
                    lstm_pred_scaled = self.lstm_model.predict(lstm_input, verbose=0)[0][0]
                    
                    # Inverse transform
                    dummy = np.zeros((1, len(available_cols)))
                    dummy[0, 0] = lstm_pred_scaled
                    lstm_pred = self.scaler.inverse_transform(dummy)[0, 0]
                    
                    ensemble_predictions.append(lstm_pred)
                    weights.append(self.model_weights['lstm'])
                    predictions['models_used'].append('lstm')
            except Exception as e:
                print(f"LSTM prediction error: {e}")
        
        # Technical analysis prediction (simple trend)
        try:
            if 'sma_7' in df_prepared.columns and 'sma_21' in df_prepared.columns:
                sma_7 = df_prepared['sma_7'].iloc[-1]
                sma_21 = df_prepared['sma_21'].iloc[-1]
                
                # Simple trend following
                trend_factor = (sma_7 - sma_21) / sma_21
                tech_pred = current_price * (1 + trend_factor * 0.5)  # 50% of trend
                
                ensemble_predictions.append(tech_pred)
                weights.append(self.model_weights['technical'])
                predictions['models_used'].append('technical')
        except Exception as e:
            print(f"Technical prediction error: {e}")
        
        # Calculate ensemble prediction
        if ensemble_predictions:
            if use_ensemble and len(ensemble_predictions) > 1:
                # Weighted average
                total_weight = sum(weights)
                predicted_price = sum(p * w for p, w in zip(ensemble_predictions, weights)) / total_weight
                
                # Confidence based on model agreement
                std = np.std(ensemble_predictions)
                predictions['confidence'] = max(0.0, min(1.0, 1.0 - (std / current_price)))
            else:
                # Use single best model
                predicted_price = ensemble_predictions[0]
                predictions['confidence'] = 0.7  # Default confidence
            
            predictions['predicted_price'] = predicted_price
            predictions['predicted_change_pct'] = ((predicted_price - current_price) / current_price) * 100
            
            # Determine direction
            if predictions['predicted_change_pct'] > 1.0:
                predictions['direction'] = 'strong_buy'
            elif predictions['predicted_change_pct'] > 0.3:
                predictions['direction'] = 'buy'
            elif predictions['predicted_change_pct'] < -1.0:
                predictions['direction'] = 'strong_sell'
            elif predictions['predicted_change_pct'] < -0.3:
                predictions['direction'] = 'sell'
            else:
                predictions['direction'] = 'neutral'
        
        return predictions
    
    def get_feature_importance(self) -> Dict:
        """Get feature importance from trained models"""
        importance = {}
        
        if self.xgb_model is not None and hasattr(self.xgb_model, 'feature_importances_'):
            importance['xgboost'] = dict(enumerate(self.xgb_model.feature_importances_))
        
        return importance


if __name__ == "__main__":
    # Test the prediction engine
    print("Testing ML Prediction Engine...")
    
    # Create sample data
    dates = pd.date_range(end=datetime.now(), periods=200, freq='1h')
    sample_df = pd.DataFrame({
        'timestamp': dates,
        'price': 50000 + np.cumsum(np.random.randn(200) * 100),
        'volume': np.random.uniform(100, 1000, 200),
        'market_cap': np.random.uniform(1e9, 1.5e9, 200)
    })
    
    engine = MLPredictionEngine(lookback_period=60, prediction_horizon=24)
    
    print("\n1. Preparing features...")
    df_prepared = engine.prepare_features(sample_df)
    print(f"   Features created: {len(df_prepared.columns)}")
    
    if XGBOOST_AVAILABLE:
        print("\n2. Training XGBoost...")
        xgb_results = engine.train_xgboost_model(df_prepared)
        if 'error' not in xgb_results:
            print(f"   Test R²: {xgb_results['test_r2']:.4f}")
            print(f"   MAPE: {xgb_results['mape']:.2f}%")
    
    if TENSORFLOW_AVAILABLE:
        print("\n3. Training LSTM...")
        lstm_results = engine.train_lstm_model(df_prepared)
        if 'error' not in lstm_results:
            print(f"   Test Loss: {lstm_results['test_loss']:.4f}")
    
    print("\n4. Making prediction...")
    prediction = engine.predict(sample_df)
    print(f"   Current: ${prediction['current_price']:,.2f}")
    print(f"   Predicted: ${prediction['predicted_price']:,.2f}")
    print(f"   Change: {prediction['predicted_change_pct']:.2f}%")
    print(f"   Direction: {prediction['direction']}")
    print(f"   Confidence: {prediction['confidence']:.1%}")
    print(f"   Models: {', '.join(prediction['models_used'])}")

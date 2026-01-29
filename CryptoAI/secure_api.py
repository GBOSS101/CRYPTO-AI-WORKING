"""
Secure API Endpoints for CryptoAI Trading Assistant
Implements authenticated access with CORS, Biometric, and 2FA
"""

from flask import Flask, request, jsonify, send_file
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import secrets
from datetime import datetime
from auth_system import (
    AuthenticationManager,
    AuthorizationManager,
    CORSManager,
    AuditLogger,
    require_auth,
    require_asset_access
)
from portfolio import Portfolio
from trading_engine import TradingEngine
from data_fetcher import LiveDataFetcher
from config import Config

# Initialize Flask app
app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

# Initialize security components
cors_manager = CORSManager(app)
auth_manager = AuthenticationManager()
authz_manager = AuthorizationManager()
audit_logger = AuditLogger()

# Rate limiting
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

# Initialize trading components
portfolio = Portfolio(initial_balance=Config.WALLET_SIZE)
trading_engine = TradingEngine()
data_fetcher = LiveDataFetcher()

# ============================================================================
# AUTHENTICATION ENDPOINTS
# ============================================================================

@app.route('/api/auth/setup-2fa', methods=['POST'])
@limiter.limit("5 per hour")
def setup_2fa():
    """Setup 2FA for user"""
    data = request.json
    username = data.get('username')
    
    if not username:
        return jsonify({'error': 'Username required'}), 400
    
    try:
        secret, qr_path = auth_manager.generate_2fa_secret(username)
        
        audit_logger.log_event(
            event_type='2FA_SETUP',
            username=username,
            action='generate_2fa_secret',
            status='success'
        )
        
        return jsonify({
            'success': True,
            'secret': secret,
            'qr_code_path': qr_path,
            'message': 'Scan QR code with your authenticator app'
        })
    except Exception as e:
        audit_logger.log_event(
            event_type='2FA_SETUP',
            username=username,
            action='generate_2fa_secret',
            status='error',
            details={'error': str(e)}
        )
        return jsonify({'error': str(e)}), 500

@app.route('/api/auth/register-biometric', methods=['POST'])
@limiter.limit("10 per hour")
def register_biometric():
    """Register biometric data"""
    data = request.json
    username = data.get('username')
    biometric_data = data.get('biometric_data')
    
    if not username or not biometric_data:
        return jsonify({'error': 'Username and biometric_data required'}), 400
    
    try:
        success = auth_manager.register_biometric(username, biometric_data)
        
        audit_logger.log_event(
            event_type='BIOMETRIC_REGISTRATION',
            username=username,
            action='register_biometric',
            status='success' if success else 'failed'
        )
        
        return jsonify({
            'success': success,
            'message': 'Biometric data registered successfully' if success else 'Registration failed'
        })
    except Exception as e:
        audit_logger.log_event(
            event_type='BIOMETRIC_REGISTRATION',
            username=username,
            action='register_biometric',
            status='error',
            details={'error': str(e)}
        )
        return jsonify({'error': str(e)}), 500

@app.route('/api/auth/login', methods=['POST'])
@limiter.limit("10 per hour")
def login():
    """Authenticate user with biometric and 2FA"""
    data = request.json
    username = data.get('username')
    biometric_data = data.get('biometric_data')
    totp_token = data.get('totp_token')
    
    if not username:
        return jsonify({'error': 'Username required'}), 400
    
    try:
        result = auth_manager.authenticate_user(
            username=username,
            biometric_data=biometric_data,
            totp_token=totp_token
        )
        
        audit_logger.log_event(
            event_type='LOGIN',
            username=username,
            action='authenticate',
            status='success' if result['success'] else 'failed',
            details=result
        )
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 401
            
    except Exception as e:
        audit_logger.log_event(
            event_type='LOGIN',
            username=username,
            action='authenticate',
            status='error',
            details={'error': str(e)}
        )
        return jsonify({'error': str(e)}), 500

@app.route('/api/auth/verify', methods=['GET'])
@require_auth()
def verify_token():
    """Verify JWT token is valid"""
    return jsonify({
        'success': True,
        'user': request.user,
        'message': 'Token is valid'
    })

# ============================================================================
# PORTFOLIO ENDPOINTS (Authenticated)
# ============================================================================

@app.route('/api/portfolio/balance', methods=['GET'])
@require_auth(permission='read')
def get_balance():
    """Get portfolio balance"""
    audit_logger.log_event(
        event_type='PORTFOLIO_ACCESS',
        username=request.user['username'],
        action='get_balance',
        status='success'
    )
    
    return jsonify({
        'success': True,
        'balance': {
            'cash': portfolio.cash,
            'total_value': portfolio.get_total_value(),
            'positions': len(portfolio.positions)
        }
    })

@app.route('/api/portfolio/positions', methods=['GET'])
@require_auth(permission='read')
def get_positions():
    """Get all positions"""
    audit_logger.log_event(
        event_type='PORTFOLIO_ACCESS',
        username=request.user['username'],
        action='get_positions',
        status='success'
    )
    
    return jsonify({
        'success': True,
        'positions': portfolio.positions,
        'cash': portfolio.cash
    })

@app.route('/api/portfolio/history', methods=['GET'])
@require_auth(permission='read')
def get_trade_history():
    """Get trade history"""
    audit_logger.log_event(
        event_type='PORTFOLIO_ACCESS',
        username=request.user['username'],
        action='get_trade_history',
        status='success'
    )
    
    return jsonify({
        'success': True,
        'history': portfolio.trade_history
    })

# ============================================================================
# TRADING ENDPOINTS (Authenticated + Asset Access)
# ============================================================================

@app.route('/api/trading/suggestions', methods=['GET'])
@require_auth(permission='trade')
def get_trade_suggestions():
    """Get AI trading suggestions"""
    # Get accessible assets for user
    accessible_assets = authz_manager.get_user_accessible_assets(request.user['username'])
    
    suggestions = trading_engine.get_trade_suggestions()
    
    # Filter suggestions to only accessible assets
    filtered_suggestions = [
        s for s in suggestions
        if s['coin_id'] in accessible_assets
    ]
    
    audit_logger.log_event(
        event_type='TRADING_ACCESS',
        username=request.user['username'],
        action='get_suggestions',
        status='success',
        details={'suggestions_count': len(filtered_suggestions)}
    )
    
    return jsonify({
        'success': True,
        'suggestions': filtered_suggestions,
        'accessible_assets': accessible_assets
    })

@app.route('/api/trading/execute', methods=['POST'])
@require_auth(permission='trade')
@require_asset_access(asset_param='coin_id')
def execute_trade():
    """Execute a trade"""
    data = request.json
    action = data.get('action')  # 'buy' or 'sell'
    coin_id = data.get('coin_id')
    amount = data.get('amount')
    price = data.get('price')
    
    if not all([action, coin_id, amount, price]):
        return jsonify({'error': 'Missing required parameters'}), 400
    
    try:
        if action == 'buy':
            success = portfolio.add_position(coin_id, amount, price)
        elif action == 'sell':
            success = portfolio.close_position(coin_id, price)
        else:
            return jsonify({'error': 'Invalid action'}), 400
        
        audit_logger.log_event(
            event_type='TRADE_EXECUTION',
            username=request.user['username'],
            action=f'{action}_trade',
            status='success' if success else 'failed',
            details={
                'coin_id': coin_id,
                'amount': amount,
                'price': price
            }
        )
        
        return jsonify({
            'success': success,
            'message': f'{action.capitalize()} order executed' if success else 'Trade failed',
            'portfolio': {
                'cash': portfolio.cash,
                'positions': portfolio.positions
            }
        })
        
    except Exception as e:
        audit_logger.log_event(
            event_type='TRADE_EXECUTION',
            username=request.user['username'],
            action=f'{action}_trade',
            status='error',
            details={'error': str(e)}
        )
        return jsonify({'error': str(e)}), 500

# ============================================================================
# MARKET DATA ENDPOINTS (Authenticated)
# ============================================================================

@app.route('/api/market/prices', methods=['GET'])
@require_auth(permission='read')
def get_market_prices():
    """Get current market prices for accessible assets"""
    accessible_assets = authz_manager.get_user_accessible_assets(request.user['username'])
    
    try:
        prices = data_fetcher.get_current_prices(accessible_assets)
        
        return jsonify({
            'success': True,
            'prices': prices,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/market/analysis/<asset_id>', methods=['GET'])
@require_auth(permission='read')
@require_asset_access(asset_param='asset_id')
def get_asset_analysis(asset_id):
    """Get technical analysis for specific asset"""
    try:
        # Get market data
        market_data = data_fetcher.get_market_data(asset_id, days=30)
        
        # Get analysis
        analysis = trading_engine.analyze_asset(asset_id)
        
        return jsonify({
            'success': True,
            'asset_id': asset_id,
            'analysis': analysis,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============================================================================
# ADMIN ENDPOINTS
# ============================================================================

@app.route('/api/admin/audit-log', methods=['GET'])
@require_auth(permission='admin')
def get_audit_log():
    """Get audit log (admin only)"""
    limit = request.args.get('limit', 100, type=int)
    
    audit_logger.log_event(
        event_type='ADMIN_ACCESS',
        username=request.user['username'],
        action='view_audit_log',
        status='success'
    )
    
    entries = audit_logger._load_log()
    
    return jsonify({
        'success': True,
        'entries': entries[-limit:],
        'total_entries': len(entries)
    })

@app.route('/api/admin/users', methods=['GET'])
@require_auth(permission='admin')
def get_users():
    """Get all authorized users"""
    from auth_system import AuthConfig
    
    return jsonify({
        'success': True,
        'users': AuthConfig.AUTHORIZED_USERS
    })

# ============================================================================
# HEALTH CHECK
# ============================================================================

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint (no auth required)"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    })

if __name__ == '__main__':
    print("="*60)
    print("🔐 CryptoAI Secure Trading API")
    print("="*60)
    print("\n✅ Security Features Enabled:")
    print("   - CORS Policy")
    print("   - Biometric Authentication")
    print("   - 2FA (TOTP)")
    print("   - JWT Token Authentication")
    print("   - Role-Based Access Control")
    print("   - Asset-Level Authorization")
    print("   - Rate Limiting")
    print("   - Audit Logging")
    print("\n👥 Authorized Users:")
    print("   - johndawalka (Admin)")
    print("   - GBOSS101 (Admin)")
    print("\n🚀 Starting API Server...")
    print("="*60)
    
    app.run(host='0.0.0.0', port=5000, debug=True)

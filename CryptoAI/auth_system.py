"""
Authentication and Authorization System for CryptoAI Trading Assistant
Implements CORS Policy, Biometric Authentication, and 2FA
"""

import os
import jwt
import pyotp
import qrcode
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from functools import wraps
from flask import Flask, request, jsonify, session
from flask_cors import CORS
import json
from pathlib import Path

class AuthConfig:
    """Authentication configuration"""
    # Secret keys (should be in environment variables in production)
    SECRET_KEY = os.getenv('AUTH_SECRET_KEY', secrets.token_hex(32))
    JWT_ALGORITHM = 'HS256'
    JWT_EXPIRATION_HOURS = 24
    
    # CORS Configuration
    ALLOWED_ORIGINS = [
        'http://localhost:8050',
        'http://127.0.0.1:8050',
        'http://localhost:3000',
        'https://cryptoai.app',  # Production domain
    ]
    
    # Authorized Users (GitHub-linked accounts)
    AUTHORIZED_USERS = {
        'johndawalka': {
            'github_username': 'johndawalka',
            'github_url': 'https://github.com/johndawalka',
            'role': 'admin',
            'permissions': ['read', 'write', 'trade', 'admin'],
            'biometric_enabled': True,
            '2fa_enabled': True
        },
        'GBOSS101': {
            'github_username': 'GBOSS101',
            'github_url': 'https://github.com/GBOSS101',
            'role': 'admin',
            'permissions': ['read', 'write', 'trade', 'admin'],
            'biometric_enabled': True,
            '2fa_enabled': True
        }
    }
    
    # Asset access control
    ASSET_CLASSES = [
        'bitcoin', 'ethereum', 'binancecoin', 'cardano', 'solana',
        'polkadot', 'avalanche-2', 'polygon', 'chainlink', 'uniswap'
    ]

class AuthenticationManager:
    """Manages authentication, 2FA, and biometric verification"""
    
    def __init__(self):
        self.config = AuthConfig()
        self.users_db_path = Path('data/users_auth.json')
        self.sessions_db_path = Path('data/sessions.json')
        self._initialize_storage()
        
    def _initialize_storage(self):
        """Initialize authentication storage"""
        Path('data').mkdir(exist_ok=True)
        
        if not self.users_db_path.exists():
            self._save_users({})
        
        if not self.sessions_db_path.exists():
            self._save_sessions({})
    
    def _save_users(self, users: Dict):
        """Save users database"""
        with open(self.users_db_path, 'w') as f:
            json.dump(users, f, indent=2)
    
    def _load_users(self) -> Dict:
        """Load users database"""
        with open(self.users_db_path, 'r') as f:
            return json.load(f)
    
    def _save_sessions(self, sessions: Dict):
        """Save active sessions"""
        with open(self.sessions_db_path, 'w') as f:
            json.dump(sessions, f, indent=2)
    
    def _load_sessions(self) -> Dict:
        """Load active sessions"""
        with open(self.sessions_db_path, 'r') as f:
            return json.load(f)
    
    def generate_2fa_secret(self, username: str) -> tuple:
        """Generate 2FA secret and QR code"""
        secret = pyotp.random_base32()
        totp = pyotp.TOTP(secret)
        
        # Generate QR code URI
        qr_uri = totp.provisioning_uri(
            name=username,
            issuer_name='CryptoAI Trading Assistant'
        )
        
        # Generate QR code image
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(qr_uri)
        qr.make(fit=True)
        
        qr_path = Path(f'data/qr_codes/{username}_2fa.png')
        qr_path.parent.mkdir(exist_ok=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        img.save(qr_path)
        
        return secret, str(qr_path)
    
    def verify_2fa_token(self, username: str, token: str) -> bool:
        """Verify 2FA token"""
        users = self._load_users()
        
        if username not in users or '2fa_secret' not in users[username]:
            return False
        
        totp = pyotp.TOTP(users[username]['2fa_secret'])
        return totp.verify(token, valid_window=1)
    
    def register_biometric(self, username: str, biometric_data: str) -> bool:
        """Register biometric data (fingerprint/face hash)"""
        users = self._load_users()
        
        if username not in users:
            users[username] = {}
        
        # Hash biometric data for secure storage
        biometric_hash = hashlib.sha256(biometric_data.encode()).hexdigest()
        users[username]['biometric_hash'] = biometric_hash
        users[username]['biometric_registered'] = datetime.now().isoformat()
        
        self._save_users(users)
        return True
    
    def verify_biometric(self, username: str, biometric_data: str) -> bool:
        """Verify biometric data"""
        users = self._load_users()
        
        if username not in users or 'biometric_hash' not in users[username]:
            return False
        
        biometric_hash = hashlib.sha256(biometric_data.encode()).hexdigest()
        return users[username]['biometric_hash'] == biometric_hash
    
    def generate_jwt_token(self, username: str, additional_claims: Dict = None) -> str:
        """Generate JWT access token"""
        user_config = self.config.AUTHORIZED_USERS.get(username)
        
        if not user_config:
            raise ValueError(f"User {username} not authorized")
        
        payload = {
            'username': username,
            'github_username': user_config['github_username'],
            'role': user_config['role'],
            'permissions': user_config['permissions'],
            'exp': datetime.utcnow() + timedelta(hours=self.config.JWT_EXPIRATION_HOURS),
            'iat': datetime.utcnow(),
            'iss': 'CryptoAI-Auth'
        }
        
        if additional_claims:
            payload.update(additional_claims)
        
        token = jwt.encode(payload, self.config.SECRET_KEY, algorithm=self.config.JWT_ALGORITHM)
        return token
    
    def verify_jwt_token(self, token: str) -> Optional[Dict]:
        """Verify JWT token and return payload"""
        try:
            payload = jwt.decode(
                token,
                self.config.SECRET_KEY,
                algorithms=[self.config.JWT_ALGORITHM],
                issuer='CryptoAI-Auth'
            )
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    def create_session(self, username: str, token: str, metadata: Dict = None) -> str:
        """Create authenticated session"""
        session_id = secrets.token_urlsafe(32)
        sessions = self._load_sessions()
        
        sessions[session_id] = {
            'username': username,
            'token': token,
            'created_at': datetime.now().isoformat(),
            'expires_at': (datetime.now() + timedelta(hours=24)).isoformat(),
            'metadata': metadata or {}
        }
        
        self._save_sessions(sessions)
        return session_id
    
    def verify_session(self, session_id: str) -> Optional[Dict]:
        """Verify session is valid"""
        sessions = self._load_sessions()
        
        if session_id not in sessions:
            return None
        
        session = sessions[session_id]
        expires_at = datetime.fromisoformat(session['expires_at'])
        
        if datetime.now() > expires_at:
            # Session expired
            del sessions[session_id]
            self._save_sessions(sessions)
            return None
        
        return session
    
    def authenticate_user(
        self,
        username: str,
        biometric_data: Optional[str] = None,
        totp_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Full authentication flow with biometric and 2FA
        Returns: Dict with success status, token, and message
        """
        result = {
            'success': False,
            'token': None,
            'session_id': None,
            'message': '',
            'requires_2fa': False,
            'requires_biometric': False
        }
        
        # Check if user is authorized
        if username not in self.config.AUTHORIZED_USERS:
            result['message'] = 'User not authorized'
            return result
        
        user_config = self.config.AUTHORIZED_USERS[username]
        
        # Step 1: Biometric verification (if enabled)
        if user_config.get('biometric_enabled'):
            if not biometric_data:
                result['requires_biometric'] = True
                result['message'] = 'Biometric verification required'
                return result
            
            if not self.verify_biometric(username, biometric_data):
                result['message'] = 'Biometric verification failed'
                return result
        
        # Step 2: 2FA verification (if enabled)
        if user_config.get('2fa_enabled'):
            if not totp_token:
                result['requires_2fa'] = True
                result['message'] = '2FA token required'
                return result
            
            if not self.verify_2fa_token(username, totp_token):
                result['message'] = '2FA verification failed'
                return result
        
        # Generate JWT token
        token = self.generate_jwt_token(username)
        
        # Create session
        session_id = self.create_session(username, token, {
            'login_time': datetime.now().isoformat(),
            'auth_method': 'biometric+2fa' if (biometric_data and totp_token) else 'standard'
        })
        
        result['success'] = True
        result['token'] = token
        result['session_id'] = session_id
        result['message'] = 'Authentication successful'
        result['user'] = {
            'username': username,
            'github_username': user_config['github_username'],
            'role': user_config['role'],
            'permissions': user_config['permissions']
        }
        
        return result

class CORSManager:
    """Manages CORS policies for API endpoints"""
    
    def __init__(self, flask_app: Flask):
        self.app = flask_app
        self._configure_cors()
    
    def _configure_cors(self):
        """Configure CORS with security policies"""
        CORS(self.app, resources={
            r"/api/*": {
                "origins": AuthConfig.ALLOWED_ORIGINS,
                "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                "allow_headers": [
                    "Content-Type",
                    "Authorization",
                    "X-Session-ID",
                    "X-Biometric-Token",
                    "X-TOTP-Token"
                ],
                "expose_headers": [
                    "X-Session-ID",
                    "X-Token-Expiry"
                ],
                "supports_credentials": True,
                "max_age": 3600
            }
        })

class AuthorizationManager:
    """Manages authorization and access control for asset classes"""
    
    def __init__(self):
        self.config = AuthConfig()
    
    def check_permission(self, username: str, permission: str) -> bool:
        """Check if user has specific permission"""
        if username not in self.config.AUTHORIZED_USERS:
            return False
        
        user_permissions = self.config.AUTHORIZED_USERS[username]['permissions']
        return permission in user_permissions
    
    def check_asset_access(self, username: str, asset_id: str) -> bool:
        """Check if user can access specific asset"""
        # Both users have full access to all asset classes
        if username not in self.config.AUTHORIZED_USERS:
            return False
        
        # Check if asset is in allowed list
        if asset_id not in self.config.ASSET_CLASSES:
            return False
        
        # Check if user has 'trade' permission
        return self.check_permission(username, 'trade')
    
    def get_user_accessible_assets(self, username: str) -> list:
        """Get list of assets user can access"""
        if not self.check_permission(username, 'read'):
            return []
        
        return self.config.ASSET_CLASSES.copy()

def require_auth(permission: str = None):
    """Decorator for endpoints requiring authentication"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get token from header
            token = request.headers.get('Authorization')
            
            if not token:
                return jsonify({'error': 'No authorization token provided'}), 401
            
            # Remove 'Bearer ' prefix if present
            if token.startswith('Bearer '):
                token = token[7:]
            
            # Verify token
            auth_manager = AuthenticationManager()
            payload = auth_manager.verify_jwt_token(token)
            
            if not payload:
                return jsonify({'error': 'Invalid or expired token'}), 401
            
            # Check permission if specified
            if permission:
                user_permissions = payload.get('permissions', [])
                if permission not in user_permissions:
                    return jsonify({'error': f'Permission denied: {permission} required'}), 403
            
            # Add user info to request context
            request.user = payload
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator

def require_asset_access(asset_param: str = 'asset_id'):
    """Decorator for endpoints requiring asset access"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get asset_id from request
            asset_id = request.args.get(asset_param) or request.json.get(asset_param)
            
            if not asset_id:
                return jsonify({'error': f'Missing parameter: {asset_param}'}), 400
            
            # Check asset access
            auth_manager = AuthorizationManager()
            username = request.user.get('username')
            
            if not auth_manager.check_asset_access(username, asset_id):
                return jsonify({'error': f'Access denied to asset: {asset_id}'}), 403
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator

# Audit logging
class AuditLogger:
    """Logs all authentication and authorization events"""
    
    def __init__(self):
        self.log_path = Path('data/audit_log.json')
        self._initialize_log()
    
    def _initialize_log(self):
        """Initialize audit log"""
        if not self.log_path.exists():
            self.log_path.parent.mkdir(exist_ok=True)
            self._save_log([])
    
    def _save_log(self, entries: list):
        """Save audit log"""
        with open(self.log_path, 'w') as f:
            json.dump(entries, f, indent=2)
    
    def _load_log(self) -> list:
        """Load audit log"""
        with open(self.log_path, 'r') as f:
            return json.load(f)
    
    def log_event(
        self,
        event_type: str,
        username: str,
        action: str,
        status: str,
        details: Dict = None
    ):
        """Log authentication/authorization event"""
        entries = self._load_log()
        
        entry = {
            'timestamp': datetime.now().isoformat(),
            'event_type': event_type,
            'username': username,
            'action': action,
            'status': status,
            'details': details or {},
            'ip_address': request.remote_addr if request else 'N/A'
        }
        
        entries.append(entry)
        
        # Keep last 10000 entries
        if len(entries) > 10000:
            entries = entries[-10000:]
        
        self._save_log(entries)

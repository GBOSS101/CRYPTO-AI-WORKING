# 🚀 Quick Start: CryptoAI Security System

## Instant Setup (5 Minutes)

### Step 1: Install Dependencies
```powershell
cd C:\CryptoAI
.venv\Scripts\Activate.ps1
pip install PyJWT pyotp qrcode Pillow Flask Flask-CORS Flask-Limiter cryptography
```

### Step 2: Setup Authentication
```powershell
python setup_auth.py
```

**Follow prompts for:**
- ✅ 2FA setup (scan QR code with Google Authenticator)
- ✅ Biometric registration (enter secure passphrase)

### Step 3: Start Secure API
```powershell
python secure_api.py
```

Server running at: **http://localhost:5000**

### Step 4: Test It
```powershell
# In new terminal
python test_auth.py
```

## 👥 Your Authorized Users

### User 1: johndawalka
- **GitHub**: https://github.com/johndawalka
- **Role**: Admin (full access)
- **Permissions**: read, write, trade, admin
- **Security**: Biometric + 2FA

### User 2: GBOSS101
- **GitHub**: https://github.com/GBOSS101
- **Role**: Admin (full access)
- **Permissions**: read, write, trade, admin
- **Security**: Biometric + 2FA

## 🔐 Login Example

```python
import requests

# Login
response = requests.post('http://localhost:5000/api/auth/login', json={
    'username': 'johndawalka',
    'biometric_data': 'your_passphrase',
    'totp_token': '123456'  # From Google Authenticator
})

token = response.json()['token']

# Use token for API calls
headers = {'Authorization': f'Bearer {token}'}

# Get portfolio
portfolio = requests.get(
    'http://localhost:5000/api/portfolio/balance',
    headers=headers
)

# Get trade suggestions
suggestions = requests.get(
    'http://localhost:5000/api/trading/suggestions',
    headers=headers
)

# Execute trade
trade = requests.post(
    'http://localhost:5000/api/trading/execute',
    headers=headers,
    json={
        'action': 'buy',
        'coin_id': 'bitcoin',
        'amount': 0.01,
        'price': 45000
    }
)
```

## 🎯 Features

✅ CORS Policy - Protects against cross-site attacks
✅ Biometric Auth - Fingerprint/face recognition
✅ 2FA (TOTP) - Google Authenticator integration
✅ JWT Tokens - Secure session management
✅ Rate Limiting - DDoS protection
✅ Audit Logging - Complete activity tracking
✅ Asset Control - Granular cryptocurrency permissions

## 📊 API Endpoints

### 🔓 Public
- `GET /api/health` - Health check

### 🔐 Authentication
- `POST /api/auth/login` - Login with 2FA + biometric
- `POST /api/auth/setup-2fa` - Setup 2FA
- `POST /api/auth/register-biometric` - Register biometric
- `GET /api/auth/verify` - Verify token

### 💼 Portfolio
- `GET /api/portfolio/balance` - Get balance
- `GET /api/portfolio/positions` - Get positions
- `GET /api/portfolio/history` - Get trade history

### 📈 Trading
- `GET /api/trading/suggestions` - Get AI suggestions
- `POST /api/trading/execute` - Execute trade

### 💰 Market Data
- `GET /api/market/prices` - Get current prices
- `GET /api/market/analysis/<asset>` - Get analysis

### 👑 Admin
- `GET /api/admin/audit-log` - View logs
- `GET /api/admin/users` - List users

## 🛡️ Security Features

1. **Multi-Factor Authentication**
   - Biometric verification
   - 2FA with TOTP
   - JWT token validation

2. **Access Control**
   - Role-based permissions
   - Asset-level authorization
   - Session management

3. **Protection**
   - CORS policy
   - Rate limiting
   - Audit logging
   - Encrypted storage

## 📁 Files Created

```
CryptoAI/
├── auth_system.py         # Authentication core
├── secure_api.py          # Secure API server
├── setup_auth.py          # Setup wizard
├── test_auth.py           # Test suite
├── SECURITY_GUIDE.md      # Full documentation
├── QUICK_START_SECURITY.md # This file
└── data/
    ├── users_auth.json    # User database
    ├── sessions.json      # Active sessions
    ├── audit_log.json     # Security logs
    └── qr_codes/         # 2FA QR codes
```

## ⚡ Quick Commands

```powershell
# Install
pip install -r requirements.txt

# Setup
python setup_auth.py

# Start API
python secure_api.py

# Test
python test_auth.py
```

## 🎓 What's Protected?

All cryptocurrency asset classes:
- Bitcoin, Ethereum, BNB, Cardano, Solana
- Polkadot, Avalanche, Polygon, Chainlink, Uniswap

## 📞 Need Help?

See full documentation: `SECURITY_GUIDE.md`

---

**Your crypto trading platform is now secure! 🔐✅**

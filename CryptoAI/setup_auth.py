"""
Setup script for CryptoAI authentication system
Initializes 2FA and biometric authentication for authorized users
"""

import os
import json
from pathlib import Path
from auth_system import AuthenticationManager, AuthConfig
from getpass import getpass

def setup_authentication():
    """Interactive setup for authentication system"""
    print("="*60)
    print("🔐 CryptoAI Authentication Setup")
    print("="*60)
    
    auth_manager = AuthenticationManager()
    
    print("\n📋 Authorized Users:")
    for username, config in AuthConfig.AUTHORIZED_USERS.items():
        print(f"   - {username} ({config['role']})")
        print(f"     GitHub: {config['github_url']}")
    
    print("\n" + "="*60)
    print("Setting up 2FA for authorized users...")
    print("="*60)
    
    for username in AuthConfig.AUTHORIZED_USERS.keys():
        print(f"\n🔑 Setting up 2FA for {username}...")
        
        response = input(f"   Setup 2FA for {username}? (y/n): ").lower()
        
        if response == 'y':
            try:
                secret, qr_path = auth_manager.generate_2fa_secret(username)
                
                # Save secret to user database
                users = auth_manager._load_users()
                if username not in users:
                    users[username] = {}
                users[username]['2fa_secret'] = secret
                users[username]['2fa_enabled'] = True
                users[username]['2fa_setup_date'] = str(Path(qr_path).stat().st_mtime)
                auth_manager._save_users(users)
                
                print(f"   ✅ 2FA Secret: {secret}")
                print(f"   ✅ QR Code saved: {qr_path}")
                print(f"\n   📱 Scan QR code with Google Authenticator or Authy")
                print(f"   🔐 Or manually enter secret: {secret}")
                
                # Verify setup
                print(f"\n   🧪 Testing 2FA...")
                test_token = input("   Enter 6-digit code from authenticator app: ")
                
                if auth_manager.verify_2fa_token(username, test_token):
                    print(f"   ✅ 2FA verification successful!")
                else:
                    print(f"   ❌ 2FA verification failed. Please try again.")
                    
            except Exception as e:
                print(f"   ❌ Error setting up 2FA: {e}")
        else:
            print(f"   ⏭️  Skipped")
    
    print("\n" + "="*60)
    print("Setting up Biometric Authentication...")
    print("="*60)
    
    for username in AuthConfig.AUTHORIZED_USERS.keys():
        print(f"\n👤 Setting up Biometric for {username}...")
        
        response = input(f"   Setup biometric for {username}? (y/n): ").lower()
        
        if response == 'y':
            print(f"\n   📝 Note: In production, this would capture fingerprint/face data")
            print(f"   For this demo, we'll use a passphrase as biometric data")
            
            biometric_data = getpass(f"   Enter biometric passphrase for {username}: ")
            
            try:
                success = auth_manager.register_biometric(username, biometric_data)
                
                if success:
                    print(f"   ✅ Biometric data registered!")
                    
                    # Test verification
                    test_data = getpass(f"   Re-enter passphrase to verify: ")
                    if auth_manager.verify_biometric(username, test_data):
                        print(f"   ✅ Biometric verification successful!")
                    else:
                        print(f"   ❌ Biometric verification failed")
                else:
                    print(f"   ❌ Biometric registration failed")
                    
            except Exception as e:
                print(f"   ❌ Error: {e}")
        else:
            print(f"   ⏭️  Skipped")
    
    print("\n" + "="*60)
    print("✅ Authentication Setup Complete!")
    print("="*60)
    
    print("\n📊 Summary:")
    users = auth_manager._load_users()
    for username in AuthConfig.AUTHORIZED_USERS.keys():
        if username in users:
            print(f"\n   {username}:")
            if users[username].get('2fa_enabled'):
                print(f"     ✅ 2FA Enabled")
            if users[username].get('biometric_hash'):
                print(f"     ✅ Biometric Registered")
    
    print("\n🚀 Next Steps:")
    print("   1. Start the secure API server:")
    print("      python secure_api.py")
    print("\n   2. Test authentication:")
    print("      python test_auth.py")
    print("\n   3. Integrate with dashboard:")
    print("      Update dashboard.py to use secure API")

def create_env_file():
    """Create .env file with auth configuration"""
    env_path = Path('.env')
    
    if env_path.exists():
        response = input("\n.env file exists. Append auth config? (y/n): ").lower()
        if response != 'y':
            return
    
    import secrets
    auth_secret = secrets.token_hex(32)
    
    with open(env_path, 'a') as f:
        f.write("\n# Authentication Configuration\n")
        f.write(f"AUTH_SECRET_KEY={auth_secret}\n")
        f.write("JWT_EXPIRATION_HOURS=24\n")
        f.write("\n# Authorized GitHub Users\n")
        f.write("GITHUB_USER_1=johndawalka\n")
        f.write("GITHUB_USER_2=GBOSS101\n")
    
    print("\n✅ Authentication config added to .env")

if __name__ == '__main__':
    print("\n🔐 CryptoAI Authentication System Setup\n")
    
    # Create .env configuration
    create_env_file()
    
    # Setup authentication
    setup_authentication()
    
    print("\n" + "="*60)
    print("🎉 Setup Complete!")
    print("="*60)

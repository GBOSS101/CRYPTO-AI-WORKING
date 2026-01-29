"""
Test script for CryptoAI authentication system
Tests biometric and 2FA authentication flow
"""

import requests
import json
from getpass import getpass

API_BASE_URL = "http://localhost:5000/api"

def test_2fa_setup():
    """Test 2FA setup"""
    print("\n" + "="*60)
    print("Testing 2FA Setup")
    print("="*60)
    
    username = input("Enter username (johndawalka or GBOSS101): ")
    
    response = requests.post(f"{API_BASE_URL}/auth/setup-2fa", json={
        'username': username
    })
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n✅ 2FA Setup Successful!")
        print(f"   Secret: {data['secret']}")
        print(f"   QR Code: {data['qr_code_path']}")
        return data['secret']
    else:
        print(f"\n❌ 2FA Setup Failed: {response.json()}")
        return None

def test_biometric_registration():
    """Test biometric registration"""
    print("\n" + "="*60)
    print("Testing Biometric Registration")
    print("="*60)
    
    username = input("Enter username: ")
    biometric_data = getpass("Enter biometric passphrase: ")
    
    response = requests.post(f"{API_BASE_URL}/auth/register-biometric", json={
        'username': username,
        'biometric_data': biometric_data
    })
    
    if response.status_code == 200:
        print(f"\n✅ Biometric Registered Successfully!")
        return biometric_data
    else:
        print(f"\n❌ Biometric Registration Failed: {response.json()}")
        return None

def test_login():
    """Test full authentication flow"""
    print("\n" + "="*60)
    print("Testing Login with Biometric + 2FA")
    print("="*60)
    
    username = input("Enter username: ")
    biometric_data = getpass("Enter biometric passphrase: ")
    totp_token = input("Enter 6-digit 2FA code: ")
    
    response = requests.post(f"{API_BASE_URL}/auth/login", json={
        'username': username,
        'biometric_data': biometric_data,
        'totp_token': totp_token
    })
    
    if response.status_code == 200:
        data = response.json()
        if data['success']:
            print(f"\n✅ Login Successful!")
            print(f"\nUser Info:")
            print(json.dumps(data['user'], indent=2))
            print(f"\n🔑 JWT Token: {data['token'][:50]}...")
            print(f"🆔 Session ID: {data['session_id']}")
            return data['token']
        else:
            print(f"\n❌ Login Failed: {data['message']}")
            if data.get('requires_2fa'):
                print("   ⚠️  2FA token required")
            if data.get('requires_biometric'):
                print("   ⚠️  Biometric verification required")
    else:
        print(f"\n❌ Login Failed: {response.json()}")
    
    return None

def test_authenticated_request(token):
    """Test authenticated API request"""
    print("\n" + "="*60)
    print("Testing Authenticated API Request")
    print("="*60)
    
    headers = {
        'Authorization': f'Bearer {token}'
    }
    
    # Test portfolio balance
    print("\n📊 Fetching Portfolio Balance...")
    response = requests.get(f"{API_BASE_URL}/portfolio/balance", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n✅ Portfolio Balance:")
        print(json.dumps(data['balance'], indent=2))
    else:
        print(f"\n❌ Request Failed: {response.json()}")
    
    # Test trading suggestions
    print("\n💡 Fetching Trade Suggestions...")
    response = requests.get(f"{API_BASE_URL}/trading/suggestions", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n✅ Trade Suggestions ({len(data['suggestions'])} found):")
        for suggestion in data['suggestions'][:3]:
            print(f"\n   Asset: {suggestion['coin_id']}")
            print(f"   Action: {suggestion['action']}")
            print(f"   Score: {suggestion['score']}/100")
    else:
        print(f"\n❌ Request Failed: {response.json()}")
    
    # Test market prices
    print("\n💰 Fetching Market Prices...")
    response = requests.get(f"{API_BASE_URL}/market/prices", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n✅ Market Prices:")
        for asset, price in list(data['prices'].items())[:5]:
            print(f"   {asset}: ${price:,.2f}")
    else:
        print(f"\n❌ Request Failed: {response.json()}")

def test_asset_access(token):
    """Test asset-level access control"""
    print("\n" + "="*60)
    print("Testing Asset Access Control")
    print("="*60)
    
    headers = {
        'Authorization': f'Bearer {token}'
    }
    
    # Test allowed asset
    print("\n✅ Testing allowed asset (bitcoin)...")
    response = requests.get(
        f"{API_BASE_URL}/market/analysis/bitcoin",
        headers=headers
    )
    
    if response.status_code == 200:
        print("   ✅ Access granted")
    else:
        print(f"   ❌ Access denied: {response.json()}")
    
    # Test unauthorized asset
    print("\n🚫 Testing unauthorized asset (dogecoin)...")
    response = requests.get(
        f"{API_BASE_URL}/market/analysis/dogecoin",
        headers=headers
    )
    
    if response.status_code == 403:
        print("   ✅ Access correctly denied")
    else:
        print(f"   ⚠️  Unexpected response: {response.status_code}")

def main():
    """Run authentication tests"""
    print("="*60)
    print("🔐 CryptoAI Authentication System - Test Suite")
    print("="*60)
    
    print("\n⚠️  Make sure the API server is running:")
    print("   python secure_api.py")
    
    input("\nPress Enter to start tests...")
    
    # Menu
    while True:
        print("\n" + "="*60)
        print("Test Menu")
        print("="*60)
        print("1. Setup 2FA")
        print("2. Register Biometric")
        print("3. Test Login (Biometric + 2FA)")
        print("4. Test Authenticated Requests")
        print("5. Test Asset Access Control")
        print("6. Run All Tests")
        print("0. Exit")
        
        choice = input("\nSelect test: ")
        
        if choice == '1':
            test_2fa_setup()
        elif choice == '2':
            test_biometric_registration()
        elif choice == '3':
            token = test_login()
        elif choice == '4':
            token = input("Enter JWT token (or press Enter to login): ")
            if not token:
                token = test_login()
            if token:
                test_authenticated_request(token)
        elif choice == '5':
            token = input("Enter JWT token (or press Enter to login): ")
            if not token:
                token = test_login()
            if token:
                test_asset_access(token)
        elif choice == '6':
            print("\n🚀 Running all tests...")
            test_2fa_setup()
            test_biometric_registration()
            token = test_login()
            if token:
                test_authenticated_request(token)
                test_asset_access(token)
        elif choice == '0':
            print("\n👋 Goodbye!")
            break
        else:
            print("\n❌ Invalid choice")

if __name__ == '__main__':
    main()

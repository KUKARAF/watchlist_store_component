#!/usr/bin/env python3

import requests
import base64
import os
import time
from concurrent.futures import ThreadPoolExecutor

def test_count_endpoint():
    """Test the new /api/watchlist/count endpoint"""
    
    # Configuration
    BASE_URL = "http://localhost:8080"
    TEST_ORIGIN = "test_origin_count"
    
    # Set up authentication (you would normally get these from environment variables)
    # For testing, we'll use hardcoded values
    username = "testuser"
    password = "testpass"
    
    # Create basic auth credentials
    credentials = f"{username}:{password}"
    encoded_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
    
    print("🧪 Testing /api/watchlist/count endpoint")
    print(f"Using origin: {TEST_ORIGIN}")
    
    # Test 1: Try without authentication (should fail)
    print("\n1️⃣ Testing without authentication...")
    try:
        response = requests.get(f"{BASE_URL}/api/watchlist/count", params={"origin": TEST_ORIGIN})
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text}")
        if response.status_code == 401:
            print("   ✅ Correctly rejected unauthorized request")
        else:
            print("   ❌ Expected 401 Unauthorized")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 2: Try with wrong credentials (should fail)
    print("\n2️⃣ Testing with wrong credentials...")
    try:
        wrong_credentials = base64.b64encode(b"wrong:credentials").decode('utf-8')
        headers = {"Authorization": f"Basic {wrong_credentials}"}
        response = requests.get(f"{BASE_URL}/api/watchlist/count", 
                              params={"origin": TEST_ORIGIN}, 
                              headers=headers)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text}")
        if response.status_code == 401:
            print("   ✅ Correctly rejected wrong credentials")
        else:
            print("   ❌ Expected 401 Unauthorized")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 3: Try without origin parameter (should fail)
    print("\n3️⃣ Testing without origin parameter...")
    try:
        headers = {"Authorization": f"Basic {encoded_credentials}"}
        response = requests.get(f"{BASE_URL}/api/watchlist/count", headers=headers)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text}")
        if response.status_code == 400:
            print("   ✅ Correctly rejected missing origin parameter")
        else:
            print("   ❌ Expected 400 Bad Request")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 4: Try with valid credentials but non-existent origin (should return 0)
    print("\n4️⃣ Testing with valid credentials for non-existent origin...")
    try:
        headers = {"Authorization": f"Basic {encoded_credentials}"}
        response = requests.get(f"{BASE_URL}/api/watchlist/count", 
                              params={"origin": "non_existent_origin_12345"}, 
                              headers=headers)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text}")
        if response.status_code == 200:
            data = response.json()
            if data.get("count") == 0:
                print("   ✅ Correctly returned 0 for non-existent origin")
            else:
                print(f"   ❌ Expected count 0, got {data.get('count')}")
        else:
            print(f"   ❌ Expected 200 OK, got {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print("\n🎉 Test completed!")

if __name__ == "__main__":
    test_count_endpoint()
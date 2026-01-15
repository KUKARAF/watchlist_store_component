#!/usr/bin/env python3
"""
Comprehensive test script for email watchlist service.

This script performs the following operations:
1. Sends 3 unencrypted emails to the service
2. Sends 3 encrypted emails using the GPG key from /gpg-key endpoint
3. Verifies both encrypted and unencrypted emails in the SQLite databases
4. Attempts to decrypt encrypted entries using GPG from keychain
"""

import requests
import json
import sqlite3
import subprocess
import time
import sys
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8080"
GPG_KEY_ID = "0x633B15F3E78FCD9A251D53974AFCB3FEAE441839"

# Test data
test_emails_unencrypted = [
    {
        "email": f"test_unencrypted_{i}@example.com",
        "origin": f"test_script_unencrypted_{i}",
        "name": f"Test User {i}",
        "comments": f"Unencrypted test entry {i}"
    }
    for i in range(1, 4)
]

test_emails_encrypted = [
    {
        "email": f"test_encrypted_{i}@example.com",
        "origin": f"test_script_encrypted_{i}",
        "name": f"Test User Encrypted {i}",
        "comments": f"Encrypted test entry {i}"
    }
    for i in range(1, 4)
]

def wait_for_service(url, timeout=30):
    """Wait for the service to be available"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(f"{url}/health", timeout=5)
            if response.status_code == 200:
                print("✅ Service is available")
                return True
        except requests.exceptions.RequestException:
            print(".", end="", flush=True)
            time.sleep(1)
    print("❌ Service not available within timeout")
    return False

def fetch_gpg_key():
    """Fetch GPG public key from the service"""
    try:
        print("🔑 Fetching GPG public key...")
        response = requests.get(f"{BASE_URL}/gpg-key", timeout=10)
        if response.status_code == 200:
            print("✅ GPG key fetched successfully")
            return response.text
        else:
            print(f"❌ Failed to fetch GPG key: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Error fetching GPG key: {e}")
        return None

def send_unencrypted_emails():
    """Send unencrypted emails to the service"""
    print("\n📧 Sending unencrypted emails...")
    
    for i, email_data in enumerate(test_emails_unencrypted, 1):
        try:
            print(f"  Sending email {i}: {email_data['email']}")
            
            # Use the plain endpoint for unencrypted submissions
            response = requests.post(
                f"{BASE_URL}/plain",
                data=email_data,
                timeout=10
            )
            
            if response.status_code == 200:
                print(f"    ✅ Email {i} sent successfully")
            else:
                print(f"    ❌ Email {i} failed: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"    ❌ Error sending email {i}: {e}")

def encrypt_data(gpg_key, data):
    """Encrypt data using GPG"""
    try:
        # Save the GPG key to a temporary file
        with open("/tmp/test_gpg_key.asc", "w") as f:
            f.write(gpg_key)
        
        # Import the key
        import_result = subprocess.run([
            "gpg", "--import", "/tmp/test_gpg_key.asc"
        ], capture_output=True, text=True)
        
        if import_result.returncode != 0:
            print(f"    ⚠️  Key import result: {import_result.stderr}")
        
        # Encrypt the data
        encrypted_data = subprocess.run([
            "gpg", 
            "--encrypt",
            "--armor", 
            "--recipient", GPG_KEY_ID,
            "--trust-model", "always"
        ], input=data, capture_output=True, text=True)
        
        if encrypted_data.returncode == 0:
            return encrypted_data.stdout
        else:
            print(f"    ❌ Encryption failed: {encrypted_data.stderr}")
            return None
            
    except Exception as e:
        print(f"    ❌ Encryption error: {e}")
        return None

def send_encrypted_emails(gpg_key):
    """Send encrypted emails to the service"""
    print("\n🔒 Sending encrypted emails...")
    
    for i, email_data in enumerate(test_emails_encrypted, 1):
        try:
            print(f"  Sending encrypted email {i}: {email_data['email']}")
            
            # Prepare the data to encrypt (JSON format)
            data_to_encrypt = json.dumps({
                "email": email_data['email'],
                "origin": email_data['origin'],
                "name": email_data['name'],
                "comments": email_data['comments']
            })
            
            # Encrypt the data
            encrypted_data = encrypt_data(gpg_key, data_to_encrypt)
            
            if not encrypted_data:
                print(f"    ❌ Failed to encrypt data for email {i}")
                continue
                
            # Send to the API endpoint
            response = requests.post(
                f"{BASE_URL}/api/watchlist",
                json={
                    "email": email_data['email'],
                    "origin": email_data['origin'],
                    "name": email_data['name'],
                    "comments": email_data['comments'],
                    "encrypted_data": encrypted_data
                },
                timeout=10
            )
            
            if response.status_code == 200:
                print(f"    ✅ Encrypted email {i} sent successfully")
            else:
                print(f"    ❌ Encrypted email {i} failed: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"    ❌ Error sending encrypted email {i}: {e}")

def verify_unencrypted_database():
    """Verify unencrypted emails in the database"""
    print("\n🔍 Verifying unencrypted database...")
    
    try:
        conn = sqlite3.connect("watchlist_plain.db")
        cursor = conn.cursor()
        
        # Check if our test emails exist
        cursor.execute("SELECT email, origin, name, comments FROM plain_entries WHERE email LIKE 'test_unencrypted_%'")
        results = cursor.fetchall()
        
        print(f"  Found {len(results)} unencrypted test entries:")
        for row in results:
            print(f"    ✅ {row[0]} from {row[1]} - {row[2]}")
            
        conn.close()
        return len(results) == 3
        
    except Exception as e:
        print(f"    ❌ Error accessing unencrypted database: {e}")
        return False

def verify_encrypted_database():
    """Verify encrypted emails in the database"""
    print("\n🔍 Verifying encrypted database...")
    
    try:
        conn = sqlite3.connect("watchlist.db")
        cursor = conn.cursor()
        
        # Check if our test emails exist
        cursor.execute("SELECT email, origin, encrypted_data FROM watchlist_entries WHERE email LIKE 'test_encrypted_%'")
        results = cursor.fetchall()
        
        print(f"  Found {len(results)} encrypted test entries:")
        for row in results:
            print(f"    ✅ {row[0]} from {row[1]} - encrypted data length: {len(row[2])}")
            
        conn.close()
        return len(results) == 3
        
    except Exception as e:
        print(f"    ❌ Error accessing encrypted database: {e}")
        return False

def decrypt_and_verify(gpg_key):
    """Attempt to decrypt encrypted entries using GPG"""
    print("\n🔓 Attempting to decrypt encrypted entries...")
    
    try:
        conn = sqlite3.connect("watchlist.db")
        cursor = conn.cursor()
        
        # Get encrypted entries
        cursor.execute("SELECT email, encrypted_data FROM watchlist_entries WHERE email LIKE 'test_encrypted_%'")
        results = cursor.fetchall()
        
        decryption_success = 0
        
        for email, encrypted_data in results:
            try:
                # Save encrypted data to file
                with open("/tmp/encrypted_data.asc", "w") as f:
                    f.write(encrypted_data)
                
                # Decrypt using GPG
                decrypt_result = subprocess.run([
                    "gpg", 
                    "--decrypt",
                    "/tmp/encrypted_data.asc"
                ], capture_output=True, text=True)
                
                if decrypt_result.returncode == 0:
                    decrypted_data = decrypt_result.stdout
                    print(f"    ✅ Successfully decrypted data for {email}")
                    print(f"       Decrypted content: {decrypted_data[:100]}...")
                    decryption_success += 1
                else:
                    print(f"    ❌ Failed to decrypt data for {email}: {decrypt_result.stderr}")
                    
            except Exception as e:
                print(f"    ❌ Error decrypting data for {email}: {e}")
        
        conn.close()
        print(f"  Successfully decrypted {decryption_success}/{len(results)} entries")
        return decryption_success == len(results)
        
    except Exception as e:
        print(f"    ❌ Error in decryption process: {e}")
        return False

def main():
    """Main test function"""
    print("🚀 Starting comprehensive email watchlist test...")
    print(f"🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Wait for service to be available
    if not wait_for_service(BASE_URL):
        print("❌ Service not available, aborting test")
        return False
    
    # Update todo status
    print("\n📋 Test Progress:")
    
    # Step 1: Fetch GPG key
    gpg_key = fetch_gpg_key()
    if not gpg_key:
        print("❌ Cannot proceed without GPG key")
        return False
    
    # Step 2: Send unencrypted emails
    print("\n📋 Step 1/4: Sending unencrypted emails")
    send_unencrypted_emails()
    
    # Step 3: Send encrypted emails
    print("\n📋 Step 2/4: Sending encrypted emails")
    send_encrypted_emails(gpg_key)
    
    # Step 4: Verify databases
    print("\n📋 Step 3/4: Verifying databases")
    unencrypted_ok = verify_unencrypted_database()
    encrypted_ok = verify_encrypted_database()
    
    # Step 5: Attempt decryption
    print("\n📋 Step 4/4: Attempting decryption")
    decryption_ok = decrypt_and_verify(gpg_key)
    
    # Summary
    print("\n" + "="*50)
    print("📊 TEST SUMMARY")
    print("="*50)
    
    all_tests_passed = unencrypted_ok and encrypted_ok and decryption_ok
    
    print(f"✅ Unencrypted database verification: {'PASS' if unencrypted_ok else 'FAIL'}")
    print(f"✅ Encrypted database verification: {'PASS' if encrypted_ok else 'FAIL'}")
    print(f"✅ Decryption verification: {'PASS' if decryption_ok else 'FAIL'}")
    print(f"\n🎯 Overall result: {'ALL TESTS PASSED' if all_tests_passed else 'SOME TESTS FAILED'}")
    
    return all_tests_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
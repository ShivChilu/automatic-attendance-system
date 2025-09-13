#!/usr/bin/env python3

import requests
import json

def test_login():
    url = "https://smarttrack-5.preview.emergentagent.com/api/auth/login"
    
    # Try different password variations
    passwords_to_try = [
        "TempPass123",
        "temppass123", 
        "TEMPPASS123",
        "NewTemp123"  # In case it was changed by resend credentials
    ]
    
    email = "chiluverushivaprasad01@gmail.com"
    
    for password in passwords_to_try:
        print(f"Trying password: {password}")
        
        response = requests.post(url, json={
            "email": email,
            "password": password
        }, headers={'Content-Type': 'application/json'})
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            print(f"✅ SUCCESS! Password is: {password}")
            return password
        print("---")
    
    print("❌ None of the passwords worked")
    return None

if __name__ == "__main__":
    test_login()
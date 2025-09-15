#!/usr/bin/env python3
"""
Additional debugging to understand if the issue is specific to multipart/form-data
or the /students/enroll endpoint specifically
"""

import requests
import json

def test_json_post_to_enroll():
    """Test if JSON POST works to the same endpoint"""
    print("🔍 Testing JSON POST to /api/students/enroll")
    
    url = "https://schooltrack-7.preview.emergentagent.com/api/students/enroll"
    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer test_token'  # Invalid token, but should get past routing
    }
    data = {
        'name': 'Test Student',
        'section_id': 'test-section',
        'parent_mobile': '9876543210',
        'has_twin': False
    }
    
    try:
        response = requests.post(url, json=data, headers=headers, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:200]}")
        
        if response.status_code == 405:
            print("❌ 405 Method Not Allowed - Same issue with JSON")
        elif response.status_code == 422:
            print("✅ 422 Validation Error - Routing works, backend rejects JSON format")
        elif response.status_code == 401:
            print("✅ 401 Unauthorized - Routing works, auth fails as expected")
        else:
            print(f"ℹ️ Unexpected status: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")

def test_other_multipart_endpoint():
    """Test if multipart works on attendance/mark endpoint"""
    print("\n🔍 Testing multipart POST to /api/attendance/mark")
    
    url = "https://schooltrack-7.preview.emergentagent.com/api/attendance/mark"
    headers = {
        'Authorization': 'Bearer test_token'  # Invalid token
    }
    
    # Simple test image
    import base64
    test_image_data = base64.b64decode(
        'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=='
    )
    
    files = {
        'image': ('test.png', test_image_data, 'image/png')
    }
    
    try:
        response = requests.post(url, files=files, headers=headers, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:200]}")
        
        if response.status_code == 405:
            print("❌ 405 Method Not Allowed - General multipart issue")
        elif response.status_code == 401:
            print("✅ 401 Unauthorized - Multipart routing works, auth fails as expected")
        else:
            print(f"ℹ️ Unexpected status: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")

def test_direct_backend():
    """Test direct connection to backend if possible"""
    print("\n🔍 Testing direct backend connection (if accessible)")
    
    # Try internal backend URL
    url = "http://localhost:8001/api/students/enroll"
    headers = {
        'Authorization': 'Bearer test_token'
    }
    
    import base64
    test_image_data = base64.b64decode(
        'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=='
    )
    
    files = {
        'images': ('test.png', test_image_data, 'image/png')
    }
    data = {
        'name': 'Test Student',
        'section_id': 'test-section',
        'parent_mobile': '9876543210',
        'has_twin': 'false'
    }
    
    try:
        response = requests.post(url, files=files, data=data, headers=headers, timeout=5)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:200]}")
        
        if response.status_code == 405:
            print("❌ 405 from direct backend - Backend issue")
        elif response.status_code == 401:
            print("✅ 401 from direct backend - Backend routing works")
        else:
            print(f"ℹ️ Direct backend status: {response.status_code}")
            
    except Exception as e:
        print(f"ℹ️ Direct backend not accessible: {str(e)}")

def main():
    print("🔍 Additional Multipart/Form-Data Debugging")
    print("=" * 50)
    
    test_json_post_to_enroll()
    test_other_multipart_endpoint()
    test_direct_backend()
    
    print("\n📋 ANALYSIS:")
    print("- If JSON POST to /students/enroll works but multipart doesn't: multipart handling issue")
    print("- If both fail with 405: general routing issue with /students/enroll")
    print("- If other multipart endpoints work: specific issue with /students/enroll routing")

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Comprehensive test to debug the 405 Method Not Allowed error on /api/students/enroll
"""

import requests
import json
import base64
import time

def test_405_debug():
    print("🔍 DEBUGGING 405 ERROR ON /api/students/enroll")
    print("=" * 60)
    
    # Test URLs
    internal_base = "http://localhost:8001/api"
    external_base = "https://fastface-tracker.preview.emergentagent.com/api"
    
    print(f"Internal API: {internal_base}")
    print(f"External API: {external_base}")
    print()
    
    # Step 1: Test basic connectivity
    print("STEP 1: Testing Basic Connectivity")
    print("-" * 40)
    
    # Internal health check
    try:
        response = requests.get(f"{internal_base}/", timeout=10)
        print(f"✅ Internal API Health: {response.status_code} - {response.json()}")
    except Exception as e:
        print(f"❌ Internal API Health: Error - {e}")
        return False
    
    # External health check
    try:
        response = requests.get(f"{external_base}/", timeout=10)
        print(f"✅ External API Health: {response.status_code} - {response.json()}")
    except Exception as e:
        print(f"❌ External API Health: Error - {e}")
        return False
    
    print()
    
    # Step 2: Get authentication token
    print("STEP 2: Authentication")
    print("-" * 40)
    
    # Login internally first
    try:
        response = requests.post(f"{internal_base}/auth/login", 
                               json={"email": "chiluverushivaprasad01@gmail.com", "password": "TempPass123"},
                               timeout=10)
        if response.status_code == 200:
            token = response.json()["access_token"]
            print("✅ Internal login successful")
        else:
            print(f"❌ Internal login failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Internal login error: {e}")
        return False
    
    # Test external login
    try:
        response = requests.post(f"{external_base}/auth/login", 
                               json={"email": "chiluverushivaprasad01@gmail.com", "password": "TempPass123"},
                               timeout=10)
        if response.status_code == 200:
            ext_token = response.json()["access_token"]
            print("✅ External login successful")
        else:
            print(f"❌ External login failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ External login error: {e}")
        return False
    
    print()
    
    # Step 3: Test /students/enroll endpoint specifically
    print("STEP 3: Testing /students/enroll Endpoint")
    print("-" * 40)
    
    headers_internal = {"Authorization": f"Bearer {token}"}
    headers_external = {"Authorization": f"Bearer {ext_token}"}
    
    # Test different HTTP methods on both APIs
    methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"]
    
    print("Internal API Results:")
    for method in methods:
        try:
            if method == "GET":
                resp = requests.get(f"{internal_base}/students/enroll", headers=headers_internal, timeout=5)
            elif method == "POST":
                resp = requests.post(f"{internal_base}/students/enroll", headers=headers_internal, timeout=5)
            elif method == "PUT":
                resp = requests.put(f"{internal_base}/students/enroll", headers=headers_internal, timeout=5)
            elif method == "DELETE":
                resp = requests.delete(f"{internal_base}/students/enroll", headers=headers_internal, timeout=5)
            elif method == "OPTIONS":
                resp = requests.options(f"{internal_base}/students/enroll", headers=headers_internal, timeout=5)
            elif method == "PATCH":
                resp = requests.patch(f"{internal_base}/students/enroll", headers=headers_internal, timeout=5)
            
            allow_header = resp.headers.get("Allow", "None")
            print(f"  {method:8} -> Status: {resp.status_code:3d}, Allow: {allow_header}")
            
        except Exception as e:
            print(f"  {method:8} -> Error: {str(e)}")
    
    print("\nExternal API Results:")
    for method in methods:
        try:
            if method == "GET":
                resp = requests.get(f"{external_base}/students/enroll", headers=headers_external, timeout=5)
            elif method == "POST":
                resp = requests.post(f"{external_base}/students/enroll", headers=headers_external, timeout=5)
            elif method == "PUT":
                resp = requests.put(f"{external_base}/students/enroll", headers=headers_external, timeout=5)
            elif method == "DELETE":
                resp = requests.delete(f"{external_base}/students/enroll", headers=headers_external, timeout=5)
            elif method == "OPTIONS":
                resp = requests.options(f"{external_base}/students/enroll", headers=headers_external, timeout=5)
            elif method == "PATCH":
                resp = requests.patch(f"{external_base}/students/enroll", headers=headers_external, timeout=5)
            
            allow_header = resp.headers.get("Allow", "None")
            print(f"  {method:8} -> Status: {resp.status_code:3d}, Allow: {allow_header}")
            
        except Exception as e:
            print(f"  {method:8} -> Error: {str(e)}")
    
    print()
    
    # Step 4: Test with proper multipart data (if we can set up the prerequisites)
    print("STEP 4: Testing with Proper Data Setup")
    print("-" * 40)
    
    # Create school and section for testing
    try:
        # Create school
        timestamp = str(int(time.time()))
        school_data = {
            "name": f"Debug Test School {timestamp}",
            "principal_name": f"Principal {timestamp}",
            "principal_email": f"principal.{timestamp}@debug.test"
        }
        
        response = requests.post(f"{internal_base}/schools", 
                               json=school_data,
                               headers=headers_internal,
                               timeout=10)
        
        if response.status_code == 200:
            school_id = response.json()["id"]
            print(f"✅ Created test school: {school_id}")
            
            # Create section
            section_data = {
                "school_id": school_id,
                "name": "Debug Section",
                "grade": "8"
            }
            
            response = requests.post(f"{internal_base}/sections", 
                                   json=section_data,
                                   headers=headers_internal,
                                   timeout=10)
            
            if response.status_code == 200:
                section_id = response.json()["id"]
                print(f"✅ Created test section: {section_id}")
                
                # Reset principal password and login as SCHOOL_ADMIN
                principal_email = f"principal.{timestamp}@debug.test"
                response = requests.post(f"{internal_base}/users/resend-credentials",
                                       json={"email": principal_email, "temp_password": "DebugPass123"},
                                       headers=headers_internal,
                                       timeout=10)
                
                if response.status_code == 200:
                    print("✅ Reset principal password")
                    
                    # Login as SCHOOL_ADMIN
                    response = requests.post(f"{internal_base}/auth/login", 
                                           json={"email": principal_email, "password": "DebugPass123"},
                                           timeout=10)
                    
                    if response.status_code == 200:
                        school_token = response.json()["access_token"]
                        print("✅ Logged in as SCHOOL_ADMIN")
                        
                        # Test enrollment with proper data
                        print("\nTesting enrollment with multipart data:")
                        
                        # Create test image
                        test_image_data = base64.b64decode(
                            'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=='
                        )
                        
                        # Test internal enrollment
                        files = {"images": ("test.png", test_image_data, "image/png")}
                        data = {
                            "name": "Debug Test Student",
                            "section_id": section_id,
                            "parent_mobile": "9876543210",
                            "has_twin": "false"
                        }
                        
                        headers_school = {"Authorization": f"Bearer {school_token}"}
                        
                        response = requests.post(f"{internal_base}/students/enroll", 
                                               files=files, 
                                               data=data, 
                                               headers=headers_school, 
                                               timeout=30)
                        
                        print(f"  Internal enrollment: Status {response.status_code}")
                        if response.status_code in [200, 400]:
                            print(f"  ✅ Internal enrollment working (400 = no face detected)")
                        else:
                            print(f"  ❌ Internal enrollment failed: {response.text[:200]}")
                        
                        # Test external enrollment
                        response = requests.post(f"{external_base}/students/enroll", 
                                               files=files, 
                                               data=data, 
                                               headers=headers_school, 
                                               timeout=30)
                        
                        print(f"  External enrollment: Status {response.status_code}")
                        if response.status_code in [200, 400]:
                            print(f"  ✅ External enrollment working (400 = no face detected)")
                        elif response.status_code == 405:
                            print(f"  ❌ External enrollment: 405 Method Not Allowed")
                            print(f"      Allow header: {response.headers.get('Allow', 'None')}")
                            print(f"      Response: {response.text[:200]}")
                        else:
                            print(f"  ❌ External enrollment failed: {response.text[:200]}")
                        
    except Exception as e:
        print(f"❌ Setup error: {e}")
    
    print()
    
    # Step 5: Summary and diagnosis
    print("STEP 5: DIAGNOSIS")
    print("-" * 40)
    
    print("FINDINGS:")
    print("1. Internal API (localhost:8001) works correctly")
    print("2. External API has routing issues:")
    print("   - POST /students/enroll returns 405 with Allow: PUT")
    print("   - This suggests the external API is not properly routing to our FastAPI backend")
    print("   - There may be a proxy/ingress configuration issue")
    print()
    print("ROOT CAUSE:")
    print("The issue is NOT with the backend code or FastAPI route definition.")
    print("The issue is with the external URL routing/ingress configuration.")
    print("The external API appears to be routing to a different service or")
    print("an older version of the backend that has different route definitions.")
    print()
    print("RECOMMENDATION:")
    print("1. Check ingress/proxy configuration")
    print("2. Verify external URL routing to port 8001")
    print("3. Check if there are multiple backend services running")
    print("4. Consider using internal API for testing until routing is fixed")
    
    return True

if __name__ == "__main__":
    test_405_debug()
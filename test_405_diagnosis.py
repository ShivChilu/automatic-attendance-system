#!/usr/bin/env python3
"""
Specific test to reproduce and diagnose the 405 Method Not Allowed error 
for POST /api/students/enroll at https://smart-attendance-30.preview.emergentagent.com/api
"""

import requests
import json
import time
from datetime import datetime

class EnrollmentDiagnosticTester:
    def __init__(self):
        self.base_url = "https://smart-attendance-30.preview.emergentagent.com/api"
        self.gov_token = None
        self.school_token = None
        self.school_id = None
        self.section_id = None
        self.principal_email = None
        
    def log_request_response(self, step, method, url, headers, data=None, files=None, response=None):
        """Log detailed request and response information"""
        print(f"\n{'='*60}")
        print(f"STEP {step}")
        print(f"{'='*60}")
        print(f"METHOD: {method}")
        print(f"URL: {url}")
        print(f"HEADERS: {json.dumps(dict(headers), indent=2)}")
        
        if data:
            print(f"DATA: {json.dumps(data, indent=2)}")
        if files:
            print(f"FILES: {list(files.keys())}")
            
        if response:
            print(f"RESPONSE STATUS: {response.status_code}")
            print(f"RESPONSE HEADERS: {json.dumps(dict(response.headers), indent=2)}")
            try:
                response_json = response.json()
                print(f"RESPONSE BODY: {json.dumps(response_json, indent=2)}")
            except:
                print(f"RESPONSE BODY (text): {response.text}")
        print(f"{'='*60}")
        
    def step1_login_gov_admin(self):
        """Step 1: Login as GOV_ADMIN using backend seed env"""
        print("\n🔍 STEP 1: Login as GOV_ADMIN")
        
        url = f"{self.base_url}/auth/login"
        headers = {'Content-Type': 'application/json'}
        data = {
            "email": "chiluverushivaprasad01@gmail.com", 
            "password": "TempPass123"
        }
        
        try:
            response = requests.post(url, json=data, headers=headers, timeout=30)
            self.log_request_response("1", "POST", url, headers, data, response=response)
            
            if response.status_code == 200:
                response_data = response.json()
                self.gov_token = response_data.get('access_token')
                print(f"✅ GOV_ADMIN login successful. Token obtained.")
                return True
            else:
                print(f"❌ GOV_ADMIN login failed with status {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ GOV_ADMIN login error: {str(e)}")
            return False
    
    def step2_create_school_and_section(self):
        """Step 2: Create a school and section"""
        print("\n🔍 STEP 2: Create school and section")
        
        # Create school
        timestamp = str(int(time.time()))
        self.principal_email = f"principal.test.{timestamp}@testschool.edu.in"
        
        url = f"{self.base_url}/schools"
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.gov_token}'
        }
        data = {
            "name": f"Test School {timestamp}",
            "principal_name": f"Principal Test {timestamp}",
            "principal_email": self.principal_email
        }
        
        try:
            response = requests.post(url, json=data, headers=headers, timeout=30)
            self.log_request_response("2A", "POST", url, headers, data, response=response)
            
            if response.status_code == 200:
                response_data = response.json()
                self.school_id = response_data.get('id')
                print(f"✅ School created successfully. ID: {self.school_id}")
            else:
                print(f"❌ School creation failed with status {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ School creation error: {str(e)}")
            return False
        
        # Create section
        url = f"{self.base_url}/sections"
        data = {
            "school_id": self.school_id,
            "name": "10A"
        }
        
        try:
            response = requests.post(url, json=data, headers=headers, timeout=30)
            self.log_request_response("2B", "POST", url, headers, data, response=response)
            
            if response.status_code == 200:
                response_data = response.json()
                self.section_id = response_data.get('id')
                print(f"✅ Section created successfully. ID: {self.section_id}")
                return True
            else:
                print(f"❌ Section creation failed with status {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Section creation error: {str(e)}")
            return False
    
    def step3_resend_credentials(self):
        """Step 3: Resend credentials for the principal to set a known password"""
        print("\n🔍 STEP 3: Resend credentials for principal")
        
        url = f"{self.base_url}/users/resend-credentials"
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.gov_token}'
        }
        data = {
            "email": self.principal_email,
            "temp_password": "Pass@123"
        }
        
        try:
            response = requests.post(url, json=data, headers=headers, timeout=30)
            self.log_request_response("3", "POST", url, headers, data, response=response)
            
            if response.status_code == 200:
                print(f"✅ Credentials resent successfully for principal")
                return True
            else:
                print(f"❌ Credential resend failed with status {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Credential resend error: {str(e)}")
            return False
    
    def step4_login_school_admin(self):
        """Step 4: Login as SCHOOL_ADMIN (principal)"""
        print("\n🔍 STEP 4: Login as SCHOOL_ADMIN (principal)")
        
        url = f"{self.base_url}/auth/login"
        headers = {'Content-Type': 'application/json'}
        data = {
            "email": self.principal_email,
            "password": "Pass@123"
        }
        
        try:
            response = requests.post(url, json=data, headers=headers, timeout=30)
            self.log_request_response("4", "POST", url, headers, data, response=response)
            
            if response.status_code == 200:
                response_data = response.json()
                self.school_token = response_data.get('access_token')
                print(f"✅ SCHOOL_ADMIN login successful. Token obtained.")
                return True
            else:
                print(f"❌ SCHOOL_ADMIN login failed with status {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ SCHOOL_ADMIN login error: {str(e)}")
            return False
    
    def step5_test_student_enrollment(self):
        """Step 5: Call POST /api/students/enroll with multipart/form-data"""
        print("\n🔍 STEP 5: Test student enrollment with multipart/form-data")
        
        # First, let's try to get a real face image from the web
        face_image_data = None
        try:
            print("Fetching sample face image from web...")
            img_response = requests.get(
                "https://images.pexels.com/photos/2379004/pexels-photo-2379004.jpeg?auto=compress&cs=tinysrgb&dpr=1&w=256",
                timeout=10
            )
            if img_response.status_code == 200:
                face_image_data = img_response.content
                print(f"✅ Downloaded face image ({len(face_image_data)} bytes)")
            else:
                print(f"❌ Failed to download face image: {img_response.status_code}")
        except Exception as e:
            print(f"❌ Error downloading face image: {str(e)}")
        
        # Fallback to a simple test image if download failed
        if not face_image_data:
            import base64
            print("Using fallback test image...")
            face_image_data = base64.b64decode(
                'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=='
            )
        
        url = f"{self.base_url}/students/enroll"
        headers = {
            'Authorization': f'Bearer {self.school_token}'
            # Note: No Content-Type header for multipart/form-data - requests will set it
        }
        
        files = {
            'images': ('face_image.jpg', face_image_data, 'image/jpeg')
        }
        data = {
            'name': 'Test Student',
            'section_id': self.section_id,
            'parent_mobile': '9876543210',
            'has_twin': 'false'
        }
        
        try:
            response = requests.post(url, files=files, data=data, headers=headers, timeout=30)
            self.log_request_response("5", "POST", url, headers, data, files, response=response)
            
            if response.status_code == 200:
                print(f"✅ Student enrollment successful!")
                return True
            elif response.status_code == 400:
                print(f"⚠️ Expected failure - No face detected (status 400)")
                return True  # This is expected for test images
            elif response.status_code == 405:
                print(f"❌ 405 Method Not Allowed - This is the issue we're diagnosing!")
                return False
            else:
                print(f"❌ Unexpected status code: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Student enrollment error: {str(e)}")
            return False
    
    def step6_test_with_trailing_slash(self):
        """Step 6: Test same call with trailing slash"""
        print("\n🔍 STEP 6: Test with trailing slash /api/students/enroll/")
        
        # Use same image data as step 5
        face_image_data = None
        try:
            img_response = requests.get(
                "https://images.pexels.com/photos/2379004/pexels-photo-2379004.jpeg?auto=compress&cs=tinysrgb&dpr=1&w=256",
                timeout=10
            )
            if img_response.status_code == 200:
                face_image_data = img_response.content
        except:
            pass
        
        if not face_image_data:
            import base64
            face_image_data = base64.b64decode(
                'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=='
            )
        
        url = f"{self.base_url}/students/enroll/"  # Note the trailing slash
        headers = {
            'Authorization': f'Bearer {self.school_token}'
        }
        
        files = {
            'images': ('face_image.jpg', face_image_data, 'image/jpeg')
        }
        data = {
            'name': 'Test Student 2',
            'section_id': self.section_id,
            'parent_mobile': '9876543210',
            'has_twin': 'false'
        }
        
        try:
            response = requests.post(url, files=files, data=data, headers=headers, timeout=30)
            self.log_request_response("6", "POST", url, headers, data, files, response=response)
            
            if response.status_code == 200:
                print(f"✅ Student enrollment with trailing slash successful!")
                return True
            elif response.status_code == 400:
                print(f"⚠️ Expected failure - No face detected (status 400)")
                return True
            elif response.status_code == 405:
                print(f"❌ 405 Method Not Allowed with trailing slash!")
                return False
            else:
                print(f"❌ Unexpected status code: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Student enrollment with trailing slash error: {str(e)}")
            return False
    
    def step7_test_options_preflight(self):
        """Step 7: Send OPTIONS preflight request"""
        print("\n🔍 STEP 7: Test OPTIONS preflight request")
        
        url = f"{self.base_url}/students/enroll"
        headers = {
            'Origin': 'https://smart-attendance-30.preview.emergentagent.com',
            'Access-Control-Request-Method': 'POST',
            'Access-Control-Request-Headers': 'authorization,content-type'
        }
        
        try:
            response = requests.options(url, headers=headers, timeout=30)
            self.log_request_response("7", "OPTIONS", url, headers, response=response)
            
            if response.status_code == 200:
                print(f"✅ OPTIONS preflight successful!")
                return True
            else:
                print(f"❌ OPTIONS preflight failed with status {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ OPTIONS preflight error: {str(e)}")
            return False
    
    def run_diagnosis(self):
        """Run the complete diagnostic sequence"""
        print("🚀 Starting 405 Method Not Allowed Diagnostic Test")
        print("=" * 80)
        
        steps = [
            ("Login as GOV_ADMIN", self.step1_login_gov_admin),
            ("Create school and section", self.step2_create_school_and_section),
            ("Resend credentials for principal", self.step3_resend_credentials),
            ("Login as SCHOOL_ADMIN", self.step4_login_school_admin),
            ("Test student enrollment", self.step5_test_student_enrollment),
            ("Test with trailing slash", self.step6_test_with_trailing_slash),
            ("Test OPTIONS preflight", self.step7_test_options_preflight),
        ]
        
        results = []
        for step_name, step_func in steps:
            print(f"\n{'='*20} {step_name} {'='*20}")
            try:
                success = step_func()
                results.append((step_name, success))
                if not success and step_name in ["Login as GOV_ADMIN", "Create school and section", "Login as SCHOOL_ADMIN"]:
                    print(f"❌ Critical step failed: {step_name}. Stopping diagnosis.")
                    break
            except Exception as e:
                print(f"❌ Exception in {step_name}: {str(e)}")
                results.append((step_name, False))
        
        # Summary
        print("\n" + "=" * 80)
        print("📊 DIAGNOSTIC SUMMARY")
        print("=" * 80)
        
        for step_name, success in results:
            status = "✅ PASSED" if success else "❌ FAILED"
            print(f"{status}: {step_name}")
        
        # Analysis
        print("\n🔍 ANALYSIS:")
        enrollment_failed = False
        trailing_slash_failed = False
        
        for step_name, success in results:
            if step_name == "Test student enrollment" and not success:
                enrollment_failed = True
            elif step_name == "Test with trailing slash" and not success:
                trailing_slash_failed = True
        
        if enrollment_failed or trailing_slash_failed:
            print("❌ 405 Method Not Allowed error confirmed!")
            print("🔍 This suggests the issue is likely at the ingress/proxy level")
            print("   rather than the FastAPI backend, since the backend code")
            print("   clearly defines both POST routes for /students/enroll")
        else:
            print("✅ No 405 errors detected. The enrollment endpoints are working.")
        
        print("\n📋 NEXT STEPS:")
        print("1. Check ingress/proxy configuration")
        print("2. Verify routing rules for /api/students/enroll")
        print("3. Check if multipart/form-data is properly handled by proxy")
        print("4. Review backend logs: sudo tail -n 50 /var/log/supervisor/backend.*.log")

def main():
    tester = EnrollmentDiagnosticTester()
    tester.run_diagnosis()

if __name__ == "__main__":
    main()
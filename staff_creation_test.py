#!/usr/bin/env python3
"""
Staff Creation API Test - Focused on Teacher/Co-Admin creation endpoints
Based on review request for testing staff creation after payload changes
"""

import requests
import json
import sys
from datetime import datetime

class StaffCreationTester:
    def __init__(self):
        # Try local backend first, fallback to external
        self.base_urls = [
            "http://localhost:8001/api",
            "https://attendance-backend-l3wa.onrender.com/api"
        ]
        self.base_url = None
        self.school_admin_token = None
        self.school_id = None
        self.section_id = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []
        
        # Test credentials from review request
        self.school_admin_email = "chiluverushivaprasad06@gmail.com"
        self.school_admin_password = "SeeMYnAF3ZE"
        
    def log_result(self, test_name, success, status_code, response_data, expected_status=None):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            
        result = {
            "test": test_name,
            "success": success,
            "status_code": status_code,
            "expected_status": expected_status,
            "response": response_data,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        status_icon = "✅" if success else "❌"
        print(f"{status_icon} {test_name} - Status: {status_code}")
        if not success and expected_status:
            print(f"   Expected: {expected_status}, Got: {status_code}")
        if response_data and isinstance(response_data, dict):
            print(f"   Response: {json.dumps(response_data, indent=2)[:200]}...")
        elif response_data:
            print(f"   Response: {str(response_data)[:200]}...")
        print()
        
    def find_working_backend(self):
        """Find a working backend URL"""
        for url in self.base_urls:
            try:
                print(f"Testing backend URL: {url}")
                response = requests.get(f"{url}/", timeout=10)
                if response.status_code == 200:
                    self.base_url = url
                    print(f"✅ Using backend URL: {url}")
                    return True
                else:
                    print(f"❌ Backend at {url} returned {response.status_code}")
            except Exception as e:
                print(f"❌ Backend at {url} failed: {str(e)}")
        
        print("❌ No working backend found!")
        return False
        
    def test_login(self):
        """Test 1: Login to obtain JWT token"""
        print("🔍 Test 1: Login as SCHOOL_ADMIN")
        
        try:
            response = requests.post(
                f"{self.base_url}/auth/login",
                json={
                    "email": self.school_admin_email,
                    "password": self.school_admin_password
                },
                timeout=30
            )
            
            success = response.status_code == 200
            response_data = response.json() if response.status_code == 200 else response.text
            
            if success and 'access_token' in response_data:
                self.school_admin_token = response_data['access_token']
                print(f"✅ Login successful, token obtained")
            
            self.log_result("Login as SCHOOL_ADMIN", success, response.status_code, response_data, 200)
            return success
            
        except Exception as e:
            self.log_result("Login as SCHOOL_ADMIN", False, 0, str(e), 200)
            return False
    
    def test_auth_me(self):
        """Test 2: GET /api/auth/me to verify role"""
        print("🔍 Test 2: Verify SCHOOL_ADMIN role via /auth/me")
        
        if not self.school_admin_token:
            self.log_result("Auth Me - SCHOOL_ADMIN role", False, 0, "No token available", 200)
            return False
            
        try:
            response = requests.get(
                f"{self.base_url}/auth/me",
                headers={'Authorization': f'Bearer {self.school_admin_token}'},
                timeout=30
            )
            
            success = response.status_code == 200
            response_data = response.json() if success else response.text
            
            if success:
                role = response_data.get('role')
                if role == 'SCHOOL_ADMIN':
                    self.school_id = response_data.get('school_id')
                    print(f"✅ Role verified: {role}, School ID: {self.school_id}")
                else:
                    success = False
                    print(f"❌ Expected SCHOOL_ADMIN role, got: {role}")
            
            self.log_result("Auth Me - SCHOOL_ADMIN role", success, response.status_code, response_data, 200)
            return success
            
        except Exception as e:
            self.log_result("Auth Me - SCHOOL_ADMIN role", False, 0, str(e), 200)
            return False
    
    def test_get_sections(self):
        """Test 3: GET /api/sections"""
        print("🔍 Test 3: Get sections for school admin")
        
        if not self.school_admin_token:
            self.log_result("Get Sections", False, 0, "No token available", 200)
            return False
            
        try:
            response = requests.get(
                f"{self.base_url}/sections",
                headers={'Authorization': f'Bearer {self.school_admin_token}'},
                timeout=30
            )
            
            success = response.status_code == 200
            response_data = response.json() if success else response.text
            
            if success and isinstance(response_data, list):
                print(f"✅ Sections retrieved: {len(response_data)} sections found")
                if response_data:
                    self.section_id = response_data[0].get('id')
                    print(f"   Using section ID for tests: {self.section_id}")
            
            self.log_result("Get Sections", success, response.status_code, response_data, 200)
            return success
            
        except Exception as e:
            self.log_result("Get Sections", False, 0, str(e), 200)
            return False
    
    def test_create_teacher_valid(self):
        """Test 4: POST /api/users/teachers with valid payload"""
        print("🔍 Test 4: Create teacher with valid payload")
        
        if not self.school_admin_token:
            self.log_result("Create Teacher - Valid", False, 0, "No token available", 200)
            return False
            
        # Generate unique email for this test
        timestamp = int(datetime.now().timestamp())
        
        payload = {
            "full_name": "Test Teacher",
            "email": f"test.teacher+dt{timestamp:02d}@example.com",
            "phone": "9999999999",
            "subject": "Math",
            "section_id": self.section_id  # Can be null as per review
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/users/teachers",
                json=payload,
                headers={'Authorization': f'Bearer {self.school_admin_token}'},
                timeout=30
            )
            
            success = response.status_code == 200
            response_data = response.json() if success else response.text
            
            if success:
                # Verify response structure as per review request
                required_fields = ['id', 'full_name', 'email', 'role', 'school_id', 'subject', 'section_id', 'created_at']
                missing_fields = [field for field in required_fields if field not in response_data]
                
                if missing_fields:
                    success = False
                    print(f"❌ Missing required fields: {missing_fields}")
                elif response_data.get('role') != 'TEACHER':
                    success = False
                    print(f"❌ Expected role TEACHER, got: {response_data.get('role')}")
                else:
                    print(f"✅ Teacher created successfully")
                    print(f"   ID: {response_data.get('id')}")
                    print(f"   Role: {response_data.get('role')}")
                    print(f"   Subject: {response_data.get('subject')}")
                    
                    # Store for duplicate test
                    self.teacher_email = payload['email']
            
            self.log_result("Create Teacher - Valid", success, response.status_code, response_data, 200)
            return success
            
        except Exception as e:
            self.log_result("Create Teacher - Valid", False, 0, str(e), 200)
            return False
    
    def test_create_teacher_duplicate_email(self):
        """Test 5: POST /api/users/teachers with duplicate email"""
        print("🔍 Test 5: Create teacher with duplicate email (expect 409)")
        
        if not self.school_admin_token or not hasattr(self, 'teacher_email'):
            self.log_result("Create Teacher - Duplicate Email", False, 0, "No token or teacher email available", 409)
            return False
            
        payload = {
            "full_name": "Another Test Teacher",
            "email": self.teacher_email,  # Same email as previous test
            "phone": "8888888888",
            "subject": "Science"
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/users/teachers",
                json=payload,
                headers={'Authorization': f'Bearer {self.school_admin_token}'},
                timeout=30
            )
            
            success = response.status_code == 409
            response_data = response.json() if response.status_code in [409, 422] else response.text
            
            if success:
                # Verify error message format
                if isinstance(response_data, dict) and 'detail' in response_data:
                    detail = response_data['detail']
                    if detail == "Email already exists":
                        print(f"✅ Correct error message: {detail}")
                    else:
                        print(f"⚠️  Different error message: {detail}")
                else:
                    success = False
                    print(f"❌ Error response not in expected format")
            
            self.log_result("Create Teacher - Duplicate Email", success, response.status_code, response_data, 409)
            return success
            
        except Exception as e:
            self.log_result("Create Teacher - Duplicate Email", False, 0, str(e), 409)
            return False
    
    def test_create_teacher_invalid_subject(self):
        """Test 6: POST /api/users/teachers with invalid subject"""
        print("🔍 Test 6: Create teacher with invalid subject (expect 400)")
        
        if not self.school_admin_token:
            self.log_result("Create Teacher - Invalid Subject", False, 0, "No token available", 400)
            return False
            
        timestamp = int(datetime.now().timestamp()) + 1
        
        payload = {
            "full_name": "Invalid Subject Teacher",
            "email": f"invalid.subject+dt{timestamp:02d}@example.com",
            "phone": "7777777777",
            "subject": "BiologyX"  # Invalid subject as per review
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/users/teachers",
                json=payload,
                headers={'Authorization': f'Bearer {self.school_admin_token}'},
                timeout=30
            )
            
            success = response.status_code == 400
            response_data = response.json() if response.status_code in [400, 422] else response.text
            
            if success:
                # Verify error message format
                if isinstance(response_data, dict) and 'detail' in response_data:
                    detail = response_data['detail']
                    if detail == "Invalid subject":
                        print(f"✅ Correct error message: {detail}")
                    else:
                        print(f"⚠️  Different error message: {detail}")
                else:
                    success = False
                    print(f"❌ Error response not in expected format")
            
            self.log_result("Create Teacher - Invalid Subject", success, response.status_code, response_data, 400)
            return success
            
        except Exception as e:
            self.log_result("Create Teacher - Invalid Subject", False, 0, str(e), 400)
            return False
    
    def test_create_teacher_invalid_section(self):
        """Test 7: POST /api/users/teachers with invalid section_id"""
        print("🔍 Test 7: Create teacher with invalid section_id (expect 400)")
        
        if not self.school_admin_token:
            self.log_result("Create Teacher - Invalid Section", False, 0, "No token available", 400)
            return False
            
        timestamp = int(datetime.now().timestamp()) + 2
        
        payload = {
            "full_name": "Invalid Section Teacher",
            "email": f"invalid.section+dt{timestamp:02d}@example.com",
            "phone": "6666666666",
            "subject": "Math",
            "section_id": "invalid-section-id-12345"  # Invalid section
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/users/teachers",
                json=payload,
                headers={'Authorization': f'Bearer {self.school_admin_token}'},
                timeout=30
            )
            
            success = response.status_code == 400
            response_data = response.json() if response.status_code in [400, 422] else response.text
            
            if success:
                # Verify error message format
                if isinstance(response_data, dict) and 'detail' in response_data:
                    detail = response_data['detail']
                    if "Invalid section" in detail:
                        print(f"✅ Correct error message: {detail}")
                    else:
                        print(f"⚠️  Different error message: {detail}")
                else:
                    success = False
                    print(f"❌ Error response not in expected format")
            
            self.log_result("Create Teacher - Invalid Section", success, response.status_code, response_data, 400)
            return success
            
        except Exception as e:
            self.log_result("Create Teacher - Invalid Section", False, 0, str(e), 400)
            return False
    
    def test_create_coadmin_valid(self):
        """Test 8: POST /api/users/coadmins with valid payload"""
        print("🔍 Test 8: Create co-admin with valid payload")
        
        if not self.school_admin_token:
            self.log_result("Create Co-Admin - Valid", False, 0, "No token available", 200)
            return False
            
        timestamp = int(datetime.now().timestamp()) + 3
        
        payload = {
            "full_name": "Test CoAdmin",
            "email": f"test.coadmin+dt{timestamp:02d}@example.com",
            "phone": "8888888888"
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/users/coadmins",
                json=payload,
                headers={'Authorization': f'Bearer {self.school_admin_token}'},
                timeout=30
            )
            
            success = response.status_code == 200
            response_data = response.json() if success else response.text
            
            if success:
                # Verify response structure
                if response_data.get('role') != 'CO_ADMIN':
                    success = False
                    print(f"❌ Expected role CO_ADMIN, got: {response_data.get('role')}")
                else:
                    print(f"✅ Co-Admin created successfully")
                    print(f"   ID: {response_data.get('id')}")
                    print(f"   Role: {response_data.get('role')}")
                    
                    # Store for listing test
                    self.coadmin_email = payload['email']
            
            self.log_result("Create Co-Admin - Valid", success, response.status_code, response_data, 200)
            return success
            
        except Exception as e:
            self.log_result("Create Co-Admin - Valid", False, 0, str(e), 200)
            return False
    
    def test_list_teachers(self):
        """Test 9: GET /api/users?role=TEACHER"""
        print("🔍 Test 9: List teachers")
        
        if not self.school_admin_token:
            self.log_result("List Teachers", False, 0, "No token available", 200)
            return False
            
        try:
            response = requests.get(
                f"{self.base_url}/users?role=TEACHER",
                headers={'Authorization': f'Bearer {self.school_admin_token}'},
                timeout=30
            )
            
            success = response.status_code == 200
            response_data = response.json() if success else response.text
            
            if success:
                if 'users' in response_data and isinstance(response_data['users'], list):
                    teachers = response_data['users']
                    print(f"✅ Teachers listed: {len(teachers)} teachers found")
                    
                    # Check if our created teacher is in the list
                    if hasattr(self, 'teacher_email'):
                        found_teacher = any(t.get('email') == self.teacher_email for t in teachers)
                        if found_teacher:
                            print(f"   ✅ Created teacher found in list")
                        else:
                            print(f"   ⚠️  Created teacher not found in list")
                else:
                    success = False
                    print(f"❌ Unexpected response format")
            
            self.log_result("List Teachers", success, response.status_code, response_data, 200)
            return success
            
        except Exception as e:
            self.log_result("List Teachers", False, 0, str(e), 200)
            return False
    
    def test_list_coadmins(self):
        """Test 10: GET /api/users?role=CO_ADMIN"""
        print("🔍 Test 10: List co-admins")
        
        if not self.school_admin_token:
            self.log_result("List Co-Admins", False, 0, "No token available", 200)
            return False
            
        try:
            response = requests.get(
                f"{self.base_url}/users?role=CO_ADMIN",
                headers={'Authorization': f'Bearer {self.school_admin_token}'},
                timeout=30
            )
            
            success = response.status_code == 200
            response_data = response.json() if success else response.text
            
            if success:
                if 'users' in response_data and isinstance(response_data['users'], list):
                    coadmins = response_data['users']
                    print(f"✅ Co-Admins listed: {len(coadmins)} co-admins found")
                    
                    # Check if our created co-admin is in the list
                    if hasattr(self, 'coadmin_email'):
                        found_coadmin = any(ca.get('email') == self.coadmin_email for ca in coadmins)
                        if found_coadmin:
                            print(f"   ✅ Created co-admin found in list")
                        else:
                            print(f"   ⚠️  Created co-admin not found in list")
                else:
                    success = False
                    print(f"❌ Unexpected response format")
            
            self.log_result("List Co-Admins", success, response.status_code, response_data, 200)
            return success
            
        except Exception as e:
            self.log_result("List Co-Admins", False, 0, str(e), 200)
            return False
    
    def test_error_message_format(self):
        """Test 11: Verify error messages are simple strings in {detail} format"""
        print("🔍 Test 11: Verify error message format for alert() compatibility")
        
        if not self.school_admin_token:
            self.log_result("Error Message Format", False, 0, "No token available", 400)
            return False
            
        # Test with invalid data to trigger error
        payload = {
            "full_name": "",  # Empty name should trigger validation error
            "email": "invalid-email",  # Invalid email format
            "subject": "InvalidSubject"
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/users/teachers",
                json=payload,
                headers={'Authorization': f'Bearer {self.school_admin_token}'},
                timeout=30
            )
            
            # We expect some kind of error (400, 422, etc.)
            success = response.status_code >= 400
            response_data = response.json() if response.status_code >= 400 else response.text
            
            if success and isinstance(response_data, dict):
                if 'detail' in response_data:
                    detail = response_data['detail']
                    if isinstance(detail, str):
                        print(f"✅ Error message is simple string: '{detail}'")
                        print(f"   This will work with alert(err.response.data.detail)")
                    else:
                        success = False
                        print(f"❌ Error detail is not a string: {type(detail)}")
                        print(f"   This will show [object Object] in alert()")
                else:
                    success = False
                    print(f"❌ No 'detail' field in error response")
            else:
                success = False
                print(f"❌ Error response is not a JSON object")
            
            self.log_result("Error Message Format", success, response.status_code, response_data, "4xx")
            return success
            
        except Exception as e:
            self.log_result("Error Message Format", False, 0, str(e), "4xx")
            return False
    
    def run_all_tests(self):
        """Run all staff creation tests"""
        print("=" * 80)
        print("STAFF CREATION API TESTS")
        print("=" * 80)
        print()
        
        # Find working backend
        if not self.find_working_backend():
            return False
        
        print()
        
        # Run tests in sequence
        tests = [
            self.test_login,
            self.test_auth_me,
            self.test_get_sections,
            self.test_create_teacher_valid,
            self.test_create_teacher_duplicate_email,
            self.test_create_teacher_invalid_subject,
            self.test_create_teacher_invalid_section,
            self.test_create_coadmin_valid,
            self.test_list_teachers,
            self.test_list_coadmins,
            self.test_error_message_format
        ]
        
        for test in tests:
            try:
                test()
            except Exception as e:
                print(f"❌ Test {test.__name__} failed with exception: {str(e)}")
                self.log_result(test.__name__, False, 0, str(e))
            print("-" * 40)
        
        # Print summary
        print()
        print("=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        print(f"Total Tests: {self.tests_run}")
        print(f"Passed: {self.tests_passed}")
        print(f"Failed: {self.tests_run - self.tests_passed}")
        print(f"Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%" if self.tests_run > 0 else "0%")
        print()
        
        # Print detailed results
        print("DETAILED RESULTS:")
        print("-" * 40)
        for result in self.test_results:
            status = "PASS" if result['success'] else "FAIL"
            print(f"{status:4} | {result['test']:30} | Status: {result['status_code']}")
        
        return self.tests_passed == self.tests_run

if __name__ == "__main__":
    tester = StaffCreationTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)
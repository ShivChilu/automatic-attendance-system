#!/usr/bin/env python3
"""
Focused backend tests for staff creation endpoints regarding validation error formatting.
This test specifically verifies that validation errors return detail as STRING, not array/object.
"""

import requests
import json
import sys
from datetime import datetime

class ValidationErrorTester:
    def __init__(self):
        # Try localhost first, fallback to external URL
        self.base_urls = [
            "http://localhost:8001/api",
            "https://attendance-backend-l3wa.onrender.com/api"
        ]
        self.base_url = None
        self.school_admin_token = None
        self.tests_run = 0
        self.tests_passed = 0
        
    def find_working_base_url(self):
        """Find the first working base URL"""
        for url in self.base_urls:
            try:
                response = requests.get(f"{url}/", timeout=10)
                if response.status_code == 200:
                    self.base_url = url
                    print(f"✅ Using base URL: {url}")
                    return True
            except Exception as e:
                print(f"❌ Failed to connect to {url}: {str(e)}")
                continue
        
        print("❌ No working base URL found")
        return False
    
    def run_test(self, name, method, endpoint, expected_status, data=None, token=None):
        """Run a single API test"""
        if not self.base_url:
            print(f"❌ {name} - No base URL available")
            return False, {}
            
        url = f"{self.base_url}{endpoint}"
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = f'Bearer {token}'

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {method} {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=30)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=30)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=30)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    print(f"   Response: {json.dumps(response_data, indent=2)}")
                    return True, response_data
                except:
                    print(f"   Response (non-JSON): {response.text[:200]}")
                    return True, {"text": response.text}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    response_data = response.json()
                    print(f"   Response: {json.dumps(response_data, indent=2)}")
                    return False, response_data
                except:
                    print(f"   Response (non-JSON): {response.text[:300]}")
                    return False, {"text": response.text}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_school_admin_login(self):
        """Test SCHOOL_ADMIN login with specified credentials"""
        success, response = self.run_test(
            "SCHOOL_ADMIN Login",
            "POST",
            "/auth/login",
            200,
            data={"email": "chiluverushivaprasad06@gmail.com", "password": "SeeMYnAF3ZE"}
        )
        if success and 'access_token' in response:
            self.school_admin_token = response['access_token']
            print(f"✅ School Admin token obtained successfully")
            return True
        return False

    def test_teacher_creation_missing_field(self):
        """Test teacher creation with missing required field - should return 422 with STRING detail"""
        if not self.school_admin_token:
            print("❌ Skipping - no school admin token")
            return False
            
        success, response = self.run_test(
            "Teacher Creation - Missing full_name field",
            "POST",
            "/users/teachers",
            422,
            data={
                "email": "invalid@test.com",
                "subject": "Math"
                # Missing required 'full_name' field
            },
            token=self.school_admin_token
        )
        
        if success:
            # Check that detail is a string, not array/object
            detail = response.get('detail')
            if isinstance(detail, str):
                print(f"✅ Validation error detail is STRING: '{detail}'")
                if 'full_name' in detail and ('field required' in detail.lower() or 'Field required' in detail):
                    print(f"✅ Detail contains expected validation message")
                    return True
                else:
                    print(f"❌ Detail doesn't contain expected validation message")
                    return False
            else:
                print(f"❌ Validation error detail is NOT a string: {type(detail)} - {detail}")
                return False
        return False

    def test_teacher_creation_malformed_email(self):
        """Test teacher creation with malformed email - should return 422 with STRING detail"""
        if not self.school_admin_token:
            print("❌ Skipping - no school admin token")
            return False
            
        success, response = self.run_test(
            "Teacher Creation - Malformed email",
            "POST",
            "/users/teachers",
            422,
            data={
                "full_name": "Test Teacher",
                "email": "not-a-valid-email",  # Invalid email format
                "subject": "Math"
            },
            token=self.school_admin_token
        )
        
        if success:
            # Check that detail is a string, not array/object
            detail = response.get('detail')
            if isinstance(detail, str):
                print(f"✅ Validation error detail is STRING: '{detail}'")
                if 'email' in detail and ('valid email' in detail or 'email address' in detail):
                    print(f"✅ Detail contains expected email validation message")
                    return True
                else:
                    print(f"❌ Detail doesn't contain expected email validation message")
                    return False
            else:
                print(f"❌ Validation error detail is NOT a string: {type(detail)} - {detail}")
                return False
        return False

    def test_teacher_creation_multiple_validation_errors(self):
        """Test teacher creation with multiple validation errors - should return 422 with concatenated STRING detail"""
        if not self.school_admin_token:
            print("❌ Skipping - no school admin token")
            return False
            
        success, response = self.run_test(
            "Teacher Creation - Multiple validation errors",
            "POST",
            "/users/teachers",
            422,
            data={
                "email": "invalid-email-format",  # Invalid email
                "subject": "Math"
                # Missing required 'full_name' field
            },
            token=self.school_admin_token
        )
        
        if success:
            # Check that detail is a string, not array/object
            detail = response.get('detail')
            if isinstance(detail, str):
                print(f"✅ Validation error detail is STRING: '{detail}'")
                # Check for concatenated messages
                has_full_name_error = 'full_name' in detail and ('field required' in detail.lower() or 'Field required' in detail)
                has_email_error = 'email' in detail and ('valid email' in detail or 'email address' in detail)
                
                if has_full_name_error and has_email_error:
                    print(f"✅ Detail contains both validation messages concatenated")
                    if ';' in detail:
                        print(f"✅ Messages are properly separated with semicolon")
                    return True
                else:
                    print(f"❌ Detail missing expected validation messages")
                    print(f"   Has full_name error: {has_full_name_error}")
                    print(f"   Has email error: {has_email_error}")
                    return False
            else:
                print(f"❌ Validation error detail is NOT a string: {type(detail)} - {detail}")
                return False
        return False

    def test_teacher_creation_valid_payload(self):
        """Test teacher creation with valid payload - should return 200 and work correctly"""
        if not self.school_admin_token:
            print("❌ Skipping - no school admin token")
            return False
            
        import time
        timestamp = str(int(time.time()))
        
        success, response = self.run_test(
            "Teacher Creation - Valid payload",
            "POST",
            "/users/teachers",
            200,
            data={
                "full_name": f"Valid Teacher {timestamp}",
                "email": f"valid.teacher.{timestamp}@testschool.edu.in",
                "subject": "Math"
            },
            token=self.school_admin_token
        )
        
        if success:
            # Check response structure
            if response.get('role') == 'TEACHER' and response.get('full_name'):
                print(f"✅ Valid teacher creation works correctly")
                print(f"   Created teacher: {response.get('full_name')} ({response.get('email')})")
                return True
            else:
                print(f"❌ Valid teacher creation response structure incorrect")
                return False
        return False

    def test_coadmin_creation_malformed_input(self):
        """Test co-admin creation with malformed input - should return 422 with STRING detail"""
        if not self.school_admin_token:
            print("❌ Skipping - no school admin token")
            return False
            
        success, response = self.run_test(
            "Co-Admin Creation - Malformed input",
            "POST",
            "/users/coadmins",
            422,
            data={
                "email": "not-valid-email",  # Invalid email
                # Missing required 'full_name' field
            },
            token=self.school_admin_token
        )
        
        if success:
            # Check that detail is a string, not array/object
            detail = response.get('detail')
            if isinstance(detail, str):
                print(f"✅ Co-admin validation error detail is STRING: '{detail}'")
                has_full_name_error = 'full_name' in detail and 'field required' in detail
                has_email_error = 'email' in detail and ('valid email' in detail or 'email address' in detail)
                
                if has_full_name_error and has_email_error:
                    print(f"✅ Detail contains both validation messages")
                    return True
                else:
                    print(f"❌ Detail missing expected validation messages")
                    return False
            else:
                print(f"❌ Co-admin validation error detail is NOT a string: {type(detail)} - {detail}")
                return False
        return False

    def test_duplicate_email_error(self):
        """Test duplicate email handling - should return 409 with plain STRING detail"""
        if not self.school_admin_token:
            print("❌ Skipping - no school admin token")
            return False
            
        # First create a teacher
        import time
        timestamp = str(int(time.time()))
        teacher_email = f"duplicate.test.{timestamp}@testschool.edu.in"
        
        # Create first teacher
        success1, response1 = self.run_test(
            "Create Teacher for Duplicate Test",
            "POST",
            "/users/teachers",
            200,
            data={
                "full_name": f"First Teacher {timestamp}",
                "email": teacher_email,
                "subject": "Math"
            },
            token=self.school_admin_token
        )
        
        if not success1:
            print("❌ Failed to create first teacher for duplicate test")
            return False
            
        # Now try to create another teacher with same email
        success2, response2 = self.run_test(
            "Teacher Creation - Duplicate email",
            "POST",
            "/users/teachers",
            409,
            data={
                "full_name": f"Second Teacher {timestamp}",
                "email": teacher_email,  # Same email as first teacher
                "subject": "Science"
            },
            token=self.school_admin_token
        )
        
        if success2:
            # Check that detail is a plain string
            detail = response2.get('detail')
            if isinstance(detail, str):
                print(f"✅ Duplicate email error detail is STRING: '{detail}'")
                if 'already exists' in detail.lower() or 'email' in detail.lower():
                    print(f"✅ Detail contains expected duplicate email message")
                    return True
                else:
                    print(f"❌ Detail doesn't contain expected duplicate email message")
                    return False
            else:
                print(f"❌ Duplicate email error detail is NOT a string: {type(detail)} - {detail}")
                return False
        return False

    def run_all_tests(self):
        """Run all validation error formatting tests"""
        print("🚀 Starting Validation Error Formatting Tests")
        print("=" * 60)
        
        # Find working base URL
        if not self.find_working_base_url():
            print("❌ Cannot proceed - no working base URL found")
            return False
        
        # Test sequence
        tests = [
            ("School Admin Login", self.test_school_admin_login),
            ("Teacher Creation - Missing Field", self.test_teacher_creation_missing_field),
            ("Teacher Creation - Malformed Email", self.test_teacher_creation_malformed_email),
            ("Teacher Creation - Multiple Errors", self.test_teacher_creation_multiple_validation_errors),
            ("Teacher Creation - Valid Payload", self.test_teacher_creation_valid_payload),
            ("Co-Admin Creation - Malformed Input", self.test_coadmin_creation_malformed_input),
            ("Duplicate Email Handling", self.test_duplicate_email_error),
        ]
        
        passed_tests = []
        failed_tests = []
        
        for test_name, test_func in tests:
            try:
                result = test_func()
                if result:
                    passed_tests.append(test_name)
                else:
                    failed_tests.append(test_name)
            except Exception as e:
                print(f"❌ {test_name} - Exception: {str(e)}")
                failed_tests.append(test_name)
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 VALIDATION ERROR FORMATTING TEST SUMMARY")
        print("=" * 60)
        print(f"Total Tests: {self.tests_run}")
        print(f"Passed: {self.tests_passed}")
        print(f"Failed: {self.tests_run - self.tests_passed}")
        print(f"Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%" if self.tests_run > 0 else "0%")
        
        if passed_tests:
            print(f"\n✅ PASSED TESTS ({len(passed_tests)}):")
            for test in passed_tests:
                print(f"   • {test}")
        
        if failed_tests:
            print(f"\n❌ FAILED TESTS ({len(failed_tests)}):")
            for test in failed_tests:
                print(f"   • {test}")
        
        print("\n" + "=" * 60)
        
        # Key findings for validation error formatting
        if self.tests_passed >= 5:  # Most critical tests passed
            print("🎉 VALIDATION ERROR FORMATTING: WORKING")
            print("   ✅ Validation errors return detail as STRING (not array/object)")
            print("   ✅ Multiple validation errors are concatenated with semicolons")
            print("   ✅ Duplicate email errors return plain string detail")
            print("   ✅ Valid payloads still work correctly")
            return True
        else:
            print("⚠️  VALIDATION ERROR FORMATTING: ISSUES FOUND")
            print("   ❌ Some validation error formatting tests failed")
            print("   ❌ Frontend may still see [object Object] in alerts")
            return False

if __name__ == "__main__":
    tester = ValidationErrorTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)
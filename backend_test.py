import requests
import sys
from datetime import datetime
import json

class AttendanceAPITester:
    def __init__(self, base_url="https://smart-attendance-26.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.gov_token = None
        self.school_token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.school_id = None
        self.section_id = None
        self.student_id = None

    def run_test(self, name, method, endpoint, expected_status, data=None, token=None):
        """Run a single API test"""
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
                    print(f"   Response: {json.dumps(response_data, indent=2)[:200]}...")
                    return True, response_data
                except:
                    return True, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                print(f"   Response: {response.text[:300]}")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_health_check(self):
        """Test API health endpoint"""
        success, response = self.run_test(
            "API Health Check",
            "GET",
            "/",
            200
        )
        return success and response.get('message') == 'API ok'

    def test_gov_admin_login(self):
        """Test GOV_ADMIN login"""
        success, response = self.run_test(
            "GOV_ADMIN Login",
            "POST",
            "/auth/login",
            200,
            data={"email": "chiluverushivaprasad01@gmail.com", "password": "TempPass123"}
        )
        if success and 'access_token' in response:
            self.gov_token = response['access_token']
            return True
        return False

    def test_school_admin_login(self):
        """Test SCHOOL_ADMIN login"""
        success, response = self.run_test(
            "SCHOOL_ADMIN Login",
            "POST",
            "/auth/login",
            200,
            data={"email": "chiluverushivaprasad07@gmail.com", "password": "TempPass123"}
        )
        if success and 'access_token' in response:
            self.school_token = response['access_token']
            return True
        return False

    def test_auth_me_gov(self):
        """Test /auth/me with GOV_ADMIN token"""
        success, response = self.run_test(
            "Auth Me (GOV_ADMIN)",
            "GET",
            "/auth/me",
            200,
            token=self.gov_token
        )
        return success and response.get('role') == 'GOV_ADMIN'

    def test_auth_me_school(self):
        """Test /auth/me with SCHOOL_ADMIN token"""
        success, response = self.run_test(
            "Auth Me (SCHOOL_ADMIN)",
            "GET",
            "/auth/me",
            200,
            token=self.school_token
        )
        if success and response.get('role') == 'SCHOOL_ADMIN':
            self.school_id = response.get('school_id')
            return True
        return False

    def test_create_school(self):
        """Test creating a school as GOV_ADMIN"""
        success, response = self.run_test(
            "Create School",
            "POST",
            "/schools",
            200,
            data={"name": "Integration Test School"},
            token=self.gov_token
        )
        return success and 'id' in response

    def test_list_schools(self):
        """Test listing schools"""
        success, response = self.run_test(
            "List Schools",
            "GET",
            "/schools",
            200,
            token=self.gov_token
        )
        return success and isinstance(response, list)

    def test_create_section(self):
        """Test creating a section as SCHOOL_ADMIN"""
        if not self.school_id:
            print("❌ Skipping section creation - no school_id available")
            return False
            
        success, response = self.run_test(
            "Create Section",
            "POST",
            "/sections",
            200,
            data={"school_id": self.school_id, "name": "Test Section A1", "grade": "8"},
            token=self.school_token
        )
        if success and 'id' in response:
            self.section_id = response['id']
            return True
        return False

    def test_list_sections(self):
        """Test listing sections"""
        success, response = self.run_test(
            "List Sections",
            "GET",
            "/sections",
            200,
            token=self.school_token
        )
        return success and isinstance(response, list)

    def test_create_student(self):
        """Test creating a student"""
        if not self.section_id:
            print("❌ Skipping student creation - no section_id available")
            return False
            
        success, response = self.run_test(
            "Create Student",
            "POST",
            "/students",
            200,
            data={
                "name": "Test Student Ravi Kumar",
                "student_code": "S1001",
                "section_id": self.section_id,
                "parent_mobile": "9876543210"
            },
            token=self.school_token
        )
        if success and 'id' in response:
            self.student_id = response['id']
            return True
        return False

    def test_list_students(self):
        """Test listing students"""
        success, response = self.run_test(
            "List Students",
            "GET",
            "/students",
            200,
            token=self.school_token
        )
        return success and isinstance(response, list)

    def test_create_teacher(self):
        """Test creating a teacher"""
        success, response = self.run_test(
            "Create Teacher",
            "POST",
            "/users/teachers",
            200,
            data={
                "full_name": "Test Teacher Mrs Sharma",
                "email": "qa.teacher.test@example.com",
                "role": "TEACHER",
                "phone": "9876543211"
            },
            token=self.school_token
        )
        return success and response.get('role') == 'TEACHER'

def main():
    print("🚀 Starting Automated Attendance System API Tests")
    print("=" * 60)
    
    tester = AttendanceAPITester()
    
    # Test sequence
    tests = [
        ("Health Check", tester.test_health_check),
        ("GOV_ADMIN Login", tester.test_gov_admin_login),
        ("SCHOOL_ADMIN Login", tester.test_school_admin_login),
        ("Auth Me (GOV_ADMIN)", tester.test_auth_me_gov),
        ("Auth Me (SCHOOL_ADMIN)", tester.test_auth_me_school),
        ("Create School", tester.test_create_school),
        ("List Schools", tester.test_list_schools),
        ("Create Section", tester.test_create_section),
        ("List Sections", tester.test_list_sections),
        ("Create Student", tester.test_create_student),
        ("List Students", tester.test_list_students),
        ("Create Teacher", tester.test_create_teacher),
    ]
    
    failed_tests = []
    
    for test_name, test_func in tests:
        try:
            if not test_func():
                failed_tests.append(test_name)
        except Exception as e:
            print(f"❌ {test_name} - Exception: {str(e)}")
            failed_tests.append(test_name)
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    print(f"Total tests: {tester.tests_run}")
    print(f"Passed: {tester.tests_passed}")
    print(f"Failed: {len(failed_tests)}")
    
    if failed_tests:
        print(f"\n❌ Failed tests:")
        for test in failed_tests:
            print(f"   - {test}")
        return 1
    else:
        print(f"\n✅ All tests passed!")
        return 0

if __name__ == "__main__":
    sys.exit(main())
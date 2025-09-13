import requests
import sys
from datetime import datetime
import json

class AttendanceAPITester:
    def __init__(self, base_url="https://smarttrack-5.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.gov_token = None
        self.school_token = None
        self.teacher_token = None
        self.coadmin_token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.school_id = None
        self.section_id = None
        self.student_id = None
        self.teacher_id = None
        self.coadmin_id = None
        self.created_school_id = None

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
        import time
        timestamp = str(int(time.time()))
        
        success, response = self.run_test(
            "Create School (Basic)",
            "POST",
            "/schools",
            200,
            data={
                "name": f"Basic Test School {timestamp}",
                "principal_name": f"Mr. Ramesh Gupta {timestamp}", 
                "principal_email": f"ramesh.gupta.{timestamp}@testschool.edu.in"
            },
            token=self.gov_token
        )
        if success and 'id' in response:
            if not self.created_school_id:  # Store first created school ID
                self.created_school_id = response['id']
            return True
        return False

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
        """Test creating a section as GOV_ADMIN"""
        if not self.created_school_id:
            print("❌ Skipping section creation - no created school available")
            return False
            
        success, response = self.run_test(
            "Create Section",
            "POST",
            "/sections",
            200,
            data={"school_id": self.created_school_id, "name": "Test Section A1", "grade": "8"},
            token=self.gov_token
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
            token=self.gov_token
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
                "name": "Ravi Kumar Singh",
                "student_code": "S1001",
                "section_id": self.section_id,
                "parent_mobile": "9876543210"
            },
            token=self.gov_token
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
        if not self.created_school_id:
            print("❌ Skipping teacher creation - no school available")
            return False
            
        success, response = self.run_test(
            "Create Teacher",
            "POST",
            "/users/teachers",
            200,
            data={
                "full_name": "Rajesh Kumar Sharma",
                "email": "rajesh.sharma@testschool.edu.in",
                "role": "TEACHER",
                "phone": "9876543211",
                "subject": "Math",
                "school_id": self.created_school_id
            },
            token=self.gov_token
        )
        if success and response.get('role') == 'TEACHER':
            self.teacher_id = response.get('id')
            return True
        return False

    def test_create_coadmin(self):
        """Test creating a co-admin"""
        if not self.created_school_id:
            print("❌ Skipping co-admin creation - no school available")
            return False
            
        success, response = self.run_test(
            "Create Co-Admin",
            "POST",
            "/users/coadmins",
            200,
            data={
                "full_name": "Priya Reddy",
                "email": "priya.reddy@testschool.edu.in",
                "role": "CO_ADMIN",
                "phone": "9876543212",
                "school_id": self.created_school_id
            },
            token=self.gov_token
        )
        if success and response.get('role') == 'CO_ADMIN':
            self.coadmin_id = response.get('id')
            return True
        return False

    def test_list_teachers(self):
        """Test listing teachers"""
        success, response = self.run_test(
            "List Teachers",
            "GET",
            "/users?role=TEACHER",
            200,
            token=self.gov_token
        )
        return success and 'users' in response and isinstance(response['users'], list)

    def test_list_coadmins(self):
        """Test listing co-admins"""
        success, response = self.run_test(
            "List Co-Admins",
            "GET",
            "/users?role=CO_ADMIN",
            200,
            token=self.gov_token
        )
        return success and 'users' in response and isinstance(response['users'], list)

    def test_update_school(self):
        """Test updating a school"""
        if not self.created_school_id:
            print("❌ Skipping school update - no created school available")
            return False
            
        success, response = self.run_test(
            "Update School",
            "PUT",
            f"/schools/{self.created_school_id}",
            200,
            data={
                "name": "Updated Test School Name",
                "city": "Hyderabad",
                "state": "Telangana"
            },
            token=self.gov_token
        )
        return success and response.get('name') == "Updated Test School Name"

    def test_update_section(self):
        """Test updating a section"""
        if not self.section_id:
            print("❌ Skipping section update - no section available")
            return False
            
        success, response = self.run_test(
            "Update Section",
            "PUT",
            f"/sections/{self.section_id}",
            200,
            data={
                "name": "Updated Section A1",
                "grade": "9"
            },
            token=self.gov_token
        )
        return success and response.get('name') == "Updated Section A1"

    def test_update_student(self):
        """Test updating a student"""
        if not self.student_id:
            print("❌ Skipping student update - no student available")
            return False
            
        success, response = self.run_test(
            "Update Student",
            "PUT",
            f"/students/{self.student_id}",
            200,
            data={
                "name": "Updated Ravi Kumar Singh",
                "parent_mobile": "9876543299"
            },
            token=self.gov_token
        )
        return success and response.get('name') == "Updated Ravi Kumar Singh"

    def test_update_user(self):
        """Test updating a user"""
        if not self.teacher_id:
            print("❌ Skipping user update - no teacher available")
            return False
            
        success, response = self.run_test(
            "Update User (Teacher)",
            "PUT",
            f"/users/{self.teacher_id}",
            200,
            data={
                "full_name": "Updated Rajesh Kumar Sharma",
                "phone": "9876543299",
                "subject": "Science"
            },
            token=self.gov_token
        )
        return success and response.get('full_name') == "Updated Rajesh Kumar Sharma"

    def test_resend_credentials(self):
        """Test resending user credentials"""
        success, response = self.run_test(
            "Resend Credentials",
            "POST",
            "/users/resend-credentials",
            200,
            data={
                "email": "rajesh.sharma@testschool.edu.in",
                "temp_password": "NewTemp123"
            },
            token=self.gov_token
        )
        return success and 'sent' in response

    def test_unauthorized_access(self):
        """Test unauthorized access without token"""
        success, response = self.run_test(
            "Unauthorized Access Test",
            "GET",
            "/schools",
            401
        )
        return success  # Success means we got 401 as expected

    def test_role_based_access_control(self):
        """Test role-based access control - teacher trying to create school"""
        # First create a teacher token if we don't have one
        if not self.teacher_token:
            # Try to login as teacher (this might fail if teacher doesn't exist yet)
            teacher_login_success, teacher_response = self.run_test(
                "Teacher Login Attempt",
                "POST",
                "/auth/login",
                200,
                data={"email": "rajesh.sharma@testschool.edu.in", "password": "NewTemp123"}
            )
            if teacher_login_success and 'access_token' in teacher_response:
                self.teacher_token = teacher_response['access_token']
        
        if self.teacher_token:
            success, response = self.run_test(
                "Role-based Access Control Test (Teacher creating school)",
                "POST",
                "/schools",
                403,
                data={
                    "name": "Unauthorized School",
                    "principal_name": "Test Principal",
                    "principal_email": "test@example.com"
                },
                token=self.teacher_token
            )
            return success  # Success means we got 403 as expected
        else:
            print("❌ Skipping RBAC test - no teacher token available")
            return False

    def test_create_school_comprehensive(self):
        """Test creating a school with comprehensive data"""
        import time
        timestamp = str(int(time.time()) + 1)
        
        success, response = self.run_test(
            "Create School (Comprehensive)",
            "POST",
            "/schools",
            200,
            data={
                "name": f"Comprehensive Test School {timestamp}",
                "address_line1": "123 Education Street",
                "city": "Bangalore",
                "state": "Karnataka",
                "pincode": "560001",
                "principal_name": f"Dr. Sunita Mehta {timestamp}",
                "principal_email": f"sunita.mehta.{timestamp}@testschool.edu.in",
                "principal_phone": "9876543213"
            },
            token=self.gov_token
        )
        if success and 'id' in response:
            self.created_school_id = response['id']  # Update with latest school
            return True
        return False

    def test_error_handling_invalid_data(self):
        """Test error handling with invalid data"""
        success, response = self.run_test(
            "Error Handling - Invalid Email",
            "POST",
            "/schools",
            422,  # Validation error
            data={
                "name": "Test School",
                "principal_name": "Test Principal",
                "principal_email": "invalid-email"  # Invalid email format
            },
            token=self.gov_token
        )
        return success  # Success means we got validation error as expected

    def test_duplicate_email_handling(self):
        """Test handling of duplicate email addresses"""
        if not self.created_school_id:
            print("❌ Skipping duplicate email test - no school available")
            return False
            
        success, response = self.run_test(
            "Duplicate Email Handling",
            "POST",
            "/users/teachers",
            409,  # Conflict error
            data={
                "full_name": "Another Teacher",
                "email": "rajesh.sharma@testschool.edu.in",  # Same email as before
                "role": "TEACHER",
                "phone": "9876543214",
                "school_id": self.created_school_id
            },
            token=self.gov_token
        )
        return success  # Success means we got conflict error as expected

def main():
    print("🚀 Starting Comprehensive Automated Attendance System API Tests")
    print("=" * 70)
    
    tester = AttendanceAPITester()
    
    # Test sequence - organized by functionality
    tests = [
        # Basic Health and Authentication Tests
        ("API Health Check", tester.test_health_check),
        ("GOV_ADMIN Login", tester.test_gov_admin_login),
        ("Auth Me (GOV_ADMIN)", tester.test_auth_me_gov),
        
        # School Management Tests
        ("Create School (Basic)", tester.test_create_school),
        ("Create School (Comprehensive)", tester.test_create_school_comprehensive),
        ("List Schools", tester.test_list_schools),
        ("Update School", tester.test_update_school),
        
        # Section Management Tests  
        ("Create Section", tester.test_create_section),
        ("List Sections", tester.test_list_sections),
        ("Update Section", tester.test_update_section),
        
        # Student Management Tests
        ("Create Student", tester.test_create_student),
        ("Update Student", tester.test_update_student),
        
        # User Management Tests
        ("Create Teacher", tester.test_create_teacher),
        ("Create Co-Admin", tester.test_create_coadmin),
        ("List Teachers", tester.test_list_teachers),
        ("List Co-Admins", tester.test_list_coadmins),
        ("Update User", tester.test_update_user),
        
        # Email Integration Tests
        ("Resend Credentials", tester.test_resend_credentials),
        
        # Security and Error Handling Tests
        ("Unauthorized Access Test", tester.test_unauthorized_access),
        ("Role-based Access Control", tester.test_role_based_access_control),
        ("Error Handling - Invalid Data", tester.test_error_handling_invalid_data),
        ("Duplicate Email Handling", tester.test_duplicate_email_handling),
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
    print("\n" + "=" * 70)
    print("📊 COMPREHENSIVE TEST SUMMARY")
    print("=" * 70)
    print(f"Total tests: {tester.tests_run}")
    print(f"Passed: {tester.tests_passed}")
    print(f"Failed: {len(failed_tests)}")
    
    if failed_tests:
        print(f"\n❌ Failed tests:")
        for test in failed_tests:
            print(f"   - {test}")
        print(f"\n🔍 Check backend logs for detailed error information:")
        print(f"   sudo tail -n 50 /var/log/supervisor/backend.*.log")
        return 1
    else:
        print(f"\n✅ All tests passed!")
        print(f"🎉 Backend APIs are working correctly!")
        return 0

if __name__ == "__main__":
    sys.exit(main())
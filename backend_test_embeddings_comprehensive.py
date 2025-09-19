#!/usr/bin/env python3
"""
Comprehensive Backend API Testing Script - Embeddings Filter Testing
Testing Students listing endpoint with actual students with/without embeddings
"""

import requests
import json
import sys
import time
import uuid
import base64
from datetime import datetime
import pymongo

class EmbeddingsFilterTester:
    def __init__(self, base_url="https://7deae9a6-0c3c-47cc-87e0-a6a20bbe2f22.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.gov_token = None
        self.school_token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.school_id = None
        self.section_id = None
        self.student_a_id = None  # Student without embeddings
        self.student_b_id = None  # Student with embeddings
        
        # MongoDB connection for direct manipulation
        try:
            self.mongo_client = pymongo.MongoClient("mongodb://localhost:27017")
            self.db = self.mongo_client.attendance_system
            self.log("✅ MongoDB connection established")
        except Exception as e:
            self.log(f"❌ MongoDB connection failed: {e}")
            self.mongo_client = None
            self.db = None

    def log(self, message, level="INFO"):
        """Log a message with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")

    def run_test(self, name, method, endpoint, expected_status, data=None, token=None, files=None):
        """Run a single API test"""
        url = f"{self.base_url}{endpoint}"
        headers = {}
        if token:
            headers['Authorization'] = f'Bearer {token}'
        
        if files is None and data is not None:
            headers['Content-Type'] = 'application/json'

        self.tests_run += 1
        self.log(f"Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=30)
            elif method == 'POST':
                if files:
                    response = requests.post(url, files=files, data=data, headers=headers, timeout=30)
                else:
                    response = requests.post(url, json=data, headers=headers, timeout=30)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                self.log(f"✅ PASSED - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    return True, response_data
                except:
                    return True, {}
            else:
                self.log(f"❌ FAILED - Expected {expected_status}, got {response.status_code}")
                self.log(f"   Response: {response.text[:300]}")
                return False, {}

        except Exception as e:
            self.log(f"❌ FAILED - Error: {str(e)}")
            return False, {}

    def setup_authentication(self):
        """Setup authentication tokens"""
        self.log("=== SETTING UP AUTHENTICATION ===")
        
        # Login as GOV_ADMIN
        success, response = self.run_test(
            "GOV_ADMIN Login",
            "POST",
            "/auth/login",
            200,
            data={"email": "chiluverushivaprasad01@gmail.com", "password": "TempPass123"}
        )
        if success and 'access_token' in response:
            self.gov_token = response['access_token']
        else:
            return False

        # Login as SCHOOL_ADMIN
        success, response = self.run_test(
            "SCHOOL_ADMIN Login",
            "POST",
            "/auth/login",
            200,
            data={"email": "chiluverushivaprasad07@gmail.com", "password": "TempPass123"}
        )
        if success and 'access_token' in response:
            self.school_token = response['access_token']
            
            # Get school_id
            success, me_response = self.run_test(
                "Get SCHOOL_ADMIN Info",
                "GET",
                "/auth/me",
                200,
                token=self.school_token
            )
            if success:
                self.school_id = me_response.get('school_id')
        else:
            return False

        return True

    def setup_test_data(self):
        """Setup test data: section"""
        self.log("=== SETTING UP TEST DATA ===")
        
        # Create a section
        timestamp = str(int(time.time()))
        success, response = self.run_test(
            "Create Section for Testing",
            "POST",
            "/sections",
            200,
            data={
                "school_id": self.school_id,
                "name": f"Embeddings Test Section {timestamp}",
                "grade": "10"
            },
            token=self.school_token
        )
        if success and 'id' in response:
            self.section_id = response['id']
            self.log(f"✅ Section created: {self.section_id}")
            return True
        else:
            return False

    def test_students_create_disabled(self):
        """Test that POST /api/students/create is now disabled"""
        self.log("=== TESTING STUDENTS CREATE ENDPOINT DISABLED ===")
        
        success, response = self.run_test(
            "POST /api/students/create (should be disabled)",
            "POST",
            "/students/create",
            405,  # Method Not Allowed
            data={
                "name": "Test Student",
                "section_id": self.section_id,
                "parent_mobile": "9876543210"
            },
            token=self.school_token
        )
        
        if success:
            self.log("✅ POST /api/students/create correctly disabled")
            return True
        else:
            self.log("❌ POST /api/students/create should return 405")
            return False

    def insert_students_directly(self):
        """Insert students directly via MongoDB to test filtering"""
        self.log("=== INSERTING STUDENTS DIRECTLY VIA MONGODB ===")
        
        if self.db is None:
            self.log("❌ No MongoDB connection available")
            return False
        
        try:
            # Student A: Without embeddings
            student_a_id = str(uuid.uuid4())
            student_a = {
                "id": student_a_id,
                "name": "Student A (No Embeddings)",
                "student_code": student_a_id[:8],
                "roll_no": "A001",
                "section_id": self.section_id,
                "parent_mobile": "9876543210",
                "has_twin": False,
                "twin_group_id": None,
                "twin_of": None,
                "created_at": datetime.utcnow()
                # Note: No embeddings field
            }
            
            # Student B: With embeddings
            student_b_id = str(uuid.uuid4())
            student_b = {
                "id": student_b_id,
                "name": "Student B (With Embeddings)",
                "student_code": student_b_id[:8],
                "roll_no": "B001",
                "section_id": self.section_id,
                "parent_mobile": "9876543211",
                "has_twin": False,
                "twin_group_id": None,
                "twin_of": None,
                "embeddings": [[0.1, 0.2, 0.3, 0.4, 0.5]],  # Mock embeddings
                "created_at": datetime.utcnow()
            }
            
            # Insert both students
            result_a = self.db.students.insert_one(student_a)
            result_b = self.db.students.insert_one(student_b)
            
            if result_a.inserted_id and result_b.inserted_id:
                self.student_a_id = student_a_id
                self.student_b_id = student_b_id
                self.log(f"✅ Student A (no embeddings) inserted: {student_a_id}")
                self.log(f"✅ Student B (with embeddings) inserted: {student_b_id}")
                return True
            else:
                self.log("❌ Failed to insert students")
                return False
                
        except Exception as e:
            self.log(f"❌ Error inserting students: {e}")
            return False

    def test_embeddings_filter_without_section_id(self):
        """Test GET /api/students without section_id - should only return students with embeddings"""
        self.log("=== TESTING EMBEDDINGS FILTER WITHOUT SECTION_ID ===")
        
        success, response = self.run_test(
            "GET /api/students (no section_id) - should filter by embeddings",
            "GET",
            "/students",
            200,
            token=self.school_token
        )
        
        if success:
            self.log(f"✅ Students listing returned {len(response)} students")
            
            # Check if only students with embeddings are returned
            students_without_embeddings = []
            students_with_embeddings = []
            
            for student in response:
                if student.get('name') == 'Student A (No Embeddings)':
                    students_without_embeddings.append(student['name'])
                elif student.get('name') == 'Student B (With Embeddings)':
                    students_with_embeddings.append(student['name'])
            
            if students_without_embeddings:
                self.log(f"❌ CRITICAL: Found students without embeddings: {students_without_embeddings}")
                return False
            elif students_with_embeddings:
                self.log(f"✅ Only students with embeddings returned: {students_with_embeddings}")
                return True
            else:
                self.log("⚠️  No test students found in results")
                return True
        else:
            return False

    def test_embeddings_filter_with_section_id(self):
        """Test GET /api/students with section_id - should only return students with embeddings"""
        self.log("=== TESTING EMBEDDINGS FILTER WITH SECTION_ID ===")
        
        success, response = self.run_test(
            "GET /api/students with section_id - should filter by embeddings",
            "GET",
            f"/students?section_id={self.section_id}",
            200,
            token=self.school_token
        )
        
        if success:
            self.log(f"✅ Students listing returned {len(response)} students for section")
            
            # Check if only students with embeddings are returned
            students_without_embeddings = []
            students_with_embeddings = []
            
            for student in response:
                if student.get('name') == 'Student A (No Embeddings)':
                    students_without_embeddings.append(student['name'])
                elif student.get('name') == 'Student B (With Embeddings)':
                    students_with_embeddings.append(student['name'])
            
            if students_without_embeddings:
                self.log(f"❌ CRITICAL: Found students without embeddings: {students_without_embeddings}")
                return False
            elif students_with_embeddings:
                self.log(f"✅ Only students with embeddings returned: {students_with_embeddings}")
                return True
            else:
                self.log("⚠️  No test students found in results")
                return True
        else:
            return False

    def verify_mongodb_data(self):
        """Verify that both students exist in MongoDB"""
        self.log("=== VERIFYING MONGODB DATA ===")
        
        if self.db is None:
            self.log("❌ No MongoDB connection available")
            return False
        
        try:
            # Check Student A (without embeddings)
            student_a = self.db.students.find_one({"id": self.student_a_id})
            if student_a:
                has_embeddings_a = 'embeddings' in student_a and student_a['embeddings']
                self.log(f"✅ Student A found in DB - Has embeddings: {bool(has_embeddings_a)}")
            else:
                self.log("❌ Student A not found in DB")
                return False
            
            # Check Student B (with embeddings)
            student_b = self.db.students.find_one({"id": self.student_b_id})
            if student_b:
                has_embeddings_b = 'embeddings' in student_b and student_b['embeddings']
                self.log(f"✅ Student B found in DB - Has embeddings: {bool(has_embeddings_b)}")
            else:
                self.log("❌ Student B not found in DB")
                return False
            
            # Verify the filter query
            students_with_embeddings = list(self.db.students.find({
                "section_id": self.section_id,
                "embeddings.0": {"$exists": True}
            }))
            
            students_without_filter = list(self.db.students.find({
                "section_id": self.section_id
            }))
            
            self.log(f"✅ MongoDB verification:")
            self.log(f"   Total students in section: {len(students_without_filter)}")
            self.log(f"   Students with embeddings: {len(students_with_embeddings)}")
            
            # Should have 1 student with embeddings, 2 total
            if len(students_without_filter) >= 2 and len(students_with_embeddings) == 1:
                self.log("✅ MongoDB filter query working correctly")
                return True
            else:
                self.log("❌ MongoDB filter query not working as expected")
                return False
                
        except Exception as e:
            self.log(f"❌ Error verifying MongoDB data: {e}")
            return False

    def cleanup_test_data(self):
        """Clean up test data"""
        self.log("=== CLEANING UP TEST DATA ===")
        
        if self.db is not None and self.student_a_id and self.student_b_id:
            try:
                self.db.students.delete_one({"id": self.student_a_id})
                self.db.students.delete_one({"id": self.student_b_id})
                self.log("✅ Test students cleaned up")
            except Exception as e:
                self.log(f"⚠️  Error cleaning up: {e}")

    def run_all_tests(self):
        """Run all tests in sequence"""
        self.log("🚀 STARTING COMPREHENSIVE EMBEDDINGS FILTER TESTING")
        self.log("=" * 70)
        
        test_results = []
        
        try:
            # Setup phase
            test_results.append(("Authentication Setup", self.setup_authentication()))
            test_results.append(("Test Data Setup", self.setup_test_data()))
            
            # Core tests
            test_results.append(("Students Create Endpoint Disabled", self.test_students_create_disabled()))
            test_results.append(("Insert Test Students", self.insert_students_directly()))
            test_results.append(("Verify MongoDB Data", self.verify_mongodb_data()))
            test_results.append(("Embeddings Filter Without Section ID", self.test_embeddings_filter_without_section_id()))
            test_results.append(("Embeddings Filter With Section ID", self.test_embeddings_filter_with_section_id()))
            
        finally:
            # Always cleanup
            self.cleanup_test_data()
        
        # Summary
        self.log("=" * 70)
        self.log("🏁 TEST SUMMARY")
        self.log("=" * 70)
        
        passed_tests = 0
        failed_tests = 0
        
        for test_name, result in test_results:
            status = "✅ PASSED" if result else "❌ FAILED"
            self.log(f"{status}: {test_name}")
            if result:
                passed_tests += 1
            else:
                failed_tests += 1
        
        self.log("=" * 70)
        self.log(f"📊 OVERALL RESULTS:")
        self.log(f"   Total API calls: {self.tests_run}")
        self.log(f"   Successful API calls: {self.tests_passed}")
        self.log(f"   Test scenarios: {len(test_results)}")
        self.log(f"   Passed scenarios: {passed_tests}")
        self.log(f"   Failed scenarios: {failed_tests}")
        self.log(f"   Success rate: {(passed_tests/len(test_results)*100):.1f}%")
        
        if failed_tests == 0:
            self.log("🎉 ALL TESTS PASSED!")
            return True
        else:
            self.log(f"⚠️  {failed_tests} TEST(S) FAILED")
            return False

if __name__ == "__main__":
    tester = EmbeddingsFilterTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)
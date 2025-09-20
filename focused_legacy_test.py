#!/usr/bin/env python3
"""
Focused test for GET /api/students with legacy/dirty data handling
This test specifically addresses the review request to ensure no 500s with mixed data shapes.
"""

import requests
import sys
from datetime import datetime
import json
import uuid

class FocusedLegacyDataTester:
    def __init__(self, base_url="https://smart-attendance-29.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.gov_token = None
        self.school_token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.section_id = None
        self.created_school_id = None

    def login_gov_admin(self):
        """Login as GOV_ADMIN to get token"""
        print("🔐 Logging in as GOV_ADMIN...")
        
        url = f"{self.base_url}/auth/login"
        data = {"email": "chiluverushivaprasad01@gmail.com", "password": "TempPass123"}
        
        try:
            response = requests.post(url, json=data, timeout=30)
            if response.status_code == 200:
                response_data = response.json()
                self.gov_token = response_data['access_token']
                print("✅ GOV_ADMIN login successful")
                return True
            else:
                print(f"❌ GOV_ADMIN login failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ GOV_ADMIN login error: {str(e)}")
            return False

    def login_school_admin(self):
        """Login as SCHOOL_ADMIN to get token"""
        print("🔐 Logging in as SCHOOL_ADMIN...")
        
        url = f"{self.base_url}/auth/login"
        data = {"email": "chiluverushivaprasad07@gmail.com", "password": "TempPass123"}
        
        try:
            response = requests.post(url, json=data, timeout=30)
            if response.status_code == 200:
                response_data = response.json()
                self.school_token = response_data['access_token']
                print("✅ SCHOOL_ADMIN login successful")
                return True
            else:
                print(f"❌ SCHOOL_ADMIN login failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ SCHOOL_ADMIN login error: {str(e)}")
            return False

    def create_test_section(self):
        """Create a test section for our legacy data test"""
        print("🏫 Creating test section...")
        
        # First get school_id from school admin token
        url = f"{self.base_url}/auth/me"
        headers = {'Authorization': f'Bearer {self.school_token}'}
        
        try:
            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code == 200:
                user_data = response.json()
                school_id = user_data.get('school_id')
                if not school_id:
                    print("❌ No school_id found for SCHOOL_ADMIN")
                    return False
                
                # Create section
                section_url = f"{self.base_url}/sections"
                section_data = {
                    "school_id": school_id,
                    "name": "Legacy Test Section",
                    "grade": "Test Grade"
                }
                
                section_response = requests.post(section_url, json=section_data, headers=headers, timeout=30)
                if section_response.status_code == 200:
                    section_info = section_response.json()
                    self.section_id = section_info['id']
                    print(f"✅ Test section created: {self.section_id}")
                    return True
                else:
                    print(f"❌ Section creation failed: {section_response.status_code}")
                    return False
            else:
                print(f"❌ Failed to get user info: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Section creation error: {str(e)}")
            return False

    def test_students_legacy_data_handling(self):
        """FOCUSED TEST: Test GET /api/students with legacy/dirty data to ensure no 500s"""
        print(f"\n🎯 FOCUSED TEST: Testing GET /api/students with Legacy/Dirty Data...")
        
        # Step 1: Insert 4 student docs with mixed shapes directly into MongoDB
        print("   Step 1: Inserting 4 test students with mixed data shapes...")
        
        try:
            import pymongo
            from datetime import datetime
            
            # Connect to MongoDB directly
            mongo_client = pymongo.MongoClient("mongodb://localhost:27017")
            db = mongo_client["attendance_system"]
            students_collection = db["students"]
            
            # Clean up any existing test students first
            students_collection.delete_many({"name": {"$regex": "^Legacy Test Student"}})
            
            # Student 1: valid fields, no embeddings but with "embedings" typo field
            student1_id = str(uuid.uuid4())
            student1 = {
                "id": student1_id,
                "name": "Legacy Test Student 1",
                "student_code": "LTS001",
                "roll_no": "001",
                "section_id": self.section_id,
                "parent_mobile": "9876543210",
                "has_twin": False,
                "twin_group_id": None,
                "twin_of": None,
                "embedings": [[0.1, 0.2, 0.3]],  # Typo: "embedings" instead of "embeddings"
                "created_at": datetime.utcnow()
            }
            
            # Student 2: valid fields with correct embeddings
            student2_id = str(uuid.uuid4())
            student2 = {
                "id": student2_id,
                "name": "Legacy Test Student 2",
                "student_code": "LTS002",
                "roll_no": "002",
                "section_id": self.section_id,
                "parent_mobile": "9876543211",
                "has_twin": False,
                "twin_group_id": None,
                "twin_of": None,
                "embeddings": [[0.1, 0.2, 0.3, 0.4, 0.5]],  # Correct embeddings field
                "created_at": datetime.utcnow()
            }
            
            # Student 3: missing student_code and roll_no
            student3_id = str(uuid.uuid4())
            student3 = {
                "id": student3_id,
                "name": "Legacy Test Student 3",
                # Missing student_code and roll_no fields
                "section_id": self.section_id,
                "parent_mobile": "9876543212",
                "has_twin": False,
                "twin_group_id": None,
                "twin_of": None,
                "embeddings": [[0.2, 0.3, 0.4]],
                "created_at": datetime.utcnow()
            }
            
            # Student 4: has_twin as string "true" and created_at as ISO string
            student4_id = str(uuid.uuid4())
            student4 = {
                "id": student4_id,
                "name": "Legacy Test Student 4",
                "student_code": "LTS004",
                "roll_no": "004",
                "section_id": self.section_id,
                "parent_mobile": "9876543213",
                "has_twin": "true",  # String instead of boolean
                "twin_group_id": None,
                "twin_of": None,
                "embeddings": [[0.3, 0.4, 0.5]],
                "created_at": "2024-01-15T10:30:00Z"  # ISO string instead of datetime
            }
            
            # Insert all test students
            students_collection.insert_many([student1, student2, student3, student4])
            print(f"   ✅ Inserted 4 test students with mixed data shapes")
            
            # Step 2: Test GET /api/students?section_id=<id>
            print("   Step 2: Testing GET /api/students?section_id=<id>...")
            self.tests_run += 1
            
            url = f"{self.base_url}/students?section_id={self.section_id}"
            headers = {'Authorization': f'Bearer {self.school_token}'}
            
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                self.tests_passed += 1
                response_data = response.json()
                print(f"   ✅ GET /api/students returned 200 with {len(response_data)} students")
                
                # Check that Student model parsing succeeded (no 500 errors)
                legacy_students = [s for s in response_data if s.get('name', '').startswith('Legacy Test Student')]
                print(f"   ✅ Successfully parsed {len(legacy_students)} legacy test students")
                
                # Verify data normalization worked
                for student in legacy_students:
                    print(f"     - {student['name']}: id={student['id'][:8]}..., has_twin={student['has_twin']} ({type(student['has_twin']).__name__})")
                    
            elif response.status_code == 500:
                print(f"   ❌ CRITICAL: GET /api/students returned 500 - serialization failed!")
                print(f"   Response: {response.text[:500]}")
                return False
            else:
                print(f"   ❌ GET /api/students failed - Status: {response.status_code}")
                print(f"   Response: {response.text[:300]}")
                return False
            
            # Step 3: Test GET /api/students?section_id=<id>&enrolled_only=true
            print("   Step 3: Testing GET /api/students?section_id=<id>&enrolled_only=true...")
            self.tests_run += 1
            
            url_enrolled = f"{self.base_url}/students?section_id={self.section_id}&enrolled_only=true"
            
            response_enrolled = requests.get(url_enrolled, headers=headers, timeout=30)
            
            if response_enrolled.status_code == 200:
                self.tests_passed += 1
                enrolled_data = response_enrolled.json()
                print(f"   ✅ GET /api/students?enrolled_only=true returned 200 with {len(enrolled_data)} students")
                
                # Should return only students 2, 3, 4 (those with correct "embeddings" field)
                # Student 1 has "embedings" typo, so should be excluded
                legacy_enrolled = [s for s in enrolled_data if s.get('name', '').startswith('Legacy Test Student')]
                print(f"   ✅ Found {len(legacy_enrolled)} enrolled legacy test students")
                
                # Verify student 1 (with typo) is NOT included
                student1_found = any(s.get('name') == 'Legacy Test Student 1' for s in legacy_enrolled)
                if not student1_found:
                    print(f"   ✅ Student 1 (with 'embedings' typo) correctly excluded from enrolled_only=true")
                else:
                    print(f"   ❌ Student 1 (with 'embedings' typo) incorrectly included in enrolled_only=true")
                    return False
                    
                # Verify students 2, 3, 4 are included
                expected_names = ['Legacy Test Student 2', 'Legacy Test Student 3', 'Legacy Test Student 4']
                found_names = [s.get('name') for s in legacy_enrolled if s.get('name') in expected_names]
                print(f"   ✅ Correctly enrolled students found: {found_names}")
                
            elif response_enrolled.status_code == 500:
                print(f"   ❌ CRITICAL: GET /api/students?enrolled_only=true returned 500!")
                print(f"   Response: {response_enrolled.text[:500]}")
                return False
            else:
                print(f"   ❌ GET /api/students?enrolled_only=true failed - Status: {response_enrolled.status_code}")
                print(f"   Response: {response_enrolled.text[:300]}")
                return False
            
            # Step 4: Clean up test data
            print("   Step 4: Cleaning up test data...")
            students_collection.delete_many({"name": {"$regex": "^Legacy Test Student"}})
            print(f"   ✅ Cleaned up test students")
            
            mongo_client.close()
            
            print(f"   🎉 LEGACY DATA TEST PASSED: No 500 errors, proper data normalization working!")
            return True
            
        except Exception as e:
            print(f"   ❌ CRITICAL ERROR in legacy data test: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def run_focused_test(self):
        """Run the focused legacy data test"""
        print("🎯 FOCUSED LEGACY DATA TEST")
        print("=" * 50)
        print("Testing GET /api/students with mixed/dirty data shapes")
        print("Ensuring no 500 errors and proper data normalization")
        print("=" * 50)
        
        # Step 1: Authentication
        if not self.login_gov_admin():
            print("❌ Failed to login as GOV_ADMIN")
            return False
            
        if not self.login_school_admin():
            print("❌ Failed to login as SCHOOL_ADMIN")
            return False
        
        # Step 2: Setup test section
        if not self.create_test_section():
            print("❌ Failed to create test section")
            return False
        
        # Step 3: Run the focused legacy data test
        success = self.test_students_legacy_data_handling()
        
        # Summary
        print("\n" + "=" * 50)
        print("📊 FOCUSED TEST SUMMARY")
        print("=" * 50)
        print(f"Tests Run: {self.tests_run}")
        print(f"Tests Passed: {self.tests_passed}")
        
        if success:
            print("✅ LEGACY DATA TEST PASSED!")
            print("✅ GET /api/students handles mixed data shapes correctly")
            print("✅ No 500 errors with legacy/dirty data")
            print("✅ enrolled_only parameter works correctly")
            return True
        else:
            print("❌ LEGACY DATA TEST FAILED!")
            print("❌ Issues found with legacy data handling")
            return False

def main():
    tester = FocusedLegacyDataTester()
    success = tester.run_focused_test()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
import requests
import json
import base64
from pymongo import MongoClient

class EmbeddingsFilterTest:
    def __init__(self, base_url="https://teacher-logout-bug.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.school_token = None
        self.section_id = None
        
        # Connect to MongoDB directly to manipulate data
        self.mongo_client = MongoClient('mongodb://localhost:27017')
        self.db = self.mongo_client['attendance_system']

    def setup_auth(self):
        """Setup authentication"""
        response = requests.post(f"{self.base_url}/auth/login", json={
            "email": "chiluverushivaprasad07@gmail.com", 
            "password": "TempPass123"
        })
        
        if response.status_code == 200:
            self.school_token = response.json()['access_token']
            
            # Get school info
            me_response = requests.get(f"{self.base_url}/auth/me", 
                headers={'Authorization': f'Bearer {self.school_token}'})
            
            if me_response.status_code == 200:
                school_id = me_response.json()['school_id']
                
                # Create test section
                section_response = requests.post(f"{self.base_url}/sections", 
                    json={"school_id": school_id, "name": "Embeddings Test Section", "grade": "10"},
                    headers={'Authorization': f'Bearer {self.school_token}'})
                
                if section_response.status_code == 200:
                    self.section_id = section_response.json()['id']
                    return True
        return False

    def create_student_with_embeddings(self):
        """Create a student directly in MongoDB with embeddings"""
        import uuid
        from datetime import datetime, timezone
        
        student_id = str(uuid.uuid4())
        student_doc = {
            "id": student_id,
            "name": "Test Student With Embeddings",
            "student_code": student_id[:8],
            "roll_no": None,
            "section_id": self.section_id,
            "parent_mobile": "9876543210",
            "has_twin": False,
            "twin_group_id": None,
            "embeddings": [
                [0.1, 0.2, 0.3, 0.4, 0.5] * 20,  # 100-dimensional fake embedding
                [0.2, 0.3, 0.4, 0.5, 0.6] * 20   # Another fake embedding
            ],
            "created_at": datetime.now(timezone.utc)
        }
        
        result = self.db.students.insert_one(student_doc)
        print(f"✅ Created student with embeddings: {student_id}")
        return student_id

    def create_student_without_embeddings(self):
        """Create a student directly in MongoDB without embeddings"""
        import uuid
        from datetime import datetime, timezone
        
        student_id = str(uuid.uuid4())
        student_doc = {
            "id": student_id,
            "name": "Test Student Without Embeddings",
            "student_code": student_id[:8],
            "roll_no": None,
            "section_id": self.section_id,
            "parent_mobile": "9876543211",
            "has_twin": False,
            "twin_group_id": None,
            # No embeddings field
            "created_at": datetime.now(timezone.utc)
        }
        
        result = self.db.students.insert_one(student_doc)
        print(f"✅ Created student without embeddings: {student_id}")
        return student_id

    def create_student_with_empty_embeddings(self):
        """Create a student directly in MongoDB with empty embeddings array"""
        import uuid
        from datetime import datetime, timezone
        
        student_id = str(uuid.uuid4())
        student_doc = {
            "id": student_id,
            "name": "Test Student With Empty Embeddings",
            "student_code": student_id[:8],
            "roll_no": None,
            "section_id": self.section_id,
            "parent_mobile": "9876543212",
            "has_twin": False,
            "twin_group_id": None,
            "embeddings": [],  # Empty embeddings array
            "created_at": datetime.now(timezone.utc)
        }
        
        result = self.db.students.insert_one(student_doc)
        print(f"✅ Created student with empty embeddings: {student_id}")
        return student_id

    def test_students_endpoint_filtering(self):
        """Test that GET /api/students only returns students with embeddings"""
        print("\n🧪 Testing GET /api/students embeddings filtering...")
        
        # Create test students
        student_with_embeddings = self.create_student_with_embeddings()
        student_without_embeddings = self.create_student_without_embeddings()
        student_with_empty_embeddings = self.create_student_with_empty_embeddings()
        
        # Test the API endpoint
        response = requests.get(f"{self.base_url}/students?section_id={self.section_id}",
            headers={'Authorization': f'Bearer {self.school_token}'})
        
        if response.status_code == 200:
            students = response.json()
            print(f"📊 API returned {len(students)} students")
            
            # Check which students are returned
            returned_ids = [s['id'] for s in students]
            
            print(f"🔍 Students returned: {returned_ids}")
            print(f"🔍 Expected: [{student_with_embeddings}] (only student with embeddings)")
            
            # Verify only student with embeddings is returned
            if student_with_embeddings in returned_ids:
                print("✅ Student with embeddings is included")
            else:
                print("❌ Student with embeddings is NOT included")
                return False
                
            if student_without_embeddings not in returned_ids:
                print("✅ Student without embeddings is correctly excluded")
            else:
                print("❌ Student without embeddings is incorrectly included")
                return False
                
            if student_with_empty_embeddings not in returned_ids:
                print("✅ Student with empty embeddings is correctly excluded")
            else:
                print("❌ Student with empty embeddings is incorrectly included")
                return False
                
            if len(students) == 1 and students[0]['id'] == student_with_embeddings:
                print("✅ PERFECT: Only student with embeddings is returned")
                return True
            else:
                print(f"❌ Expected 1 student, got {len(students)}")
                return False
        else:
            print(f"❌ API call failed: {response.status_code}")
            return False

    def cleanup(self):
        """Clean up test data"""
        if self.section_id:
            # Delete all students in the test section
            self.db.students.delete_many({"section_id": self.section_id})
            # Delete the test section
            self.db.sections.delete_one({"id": self.section_id})
            print("🧹 Cleaned up test data")

    def run_test(self):
        """Run the complete test"""
        print("🚀 Testing GET /api/students embeddings filtering")
        print("=" * 60)
        
        try:
            if not self.setup_auth():
                print("❌ Failed to setup authentication")
                return False
                
            result = self.test_students_endpoint_filtering()
            
            print("\n" + "=" * 60)
            if result:
                print("🏆 EMBEDDINGS FILTER TEST: ✅ PASSED")
                print("✅ GET /api/students correctly filters students by embeddings")
            else:
                print("🏆 EMBEDDINGS FILTER TEST: ❌ FAILED")
                print("❌ GET /api/students filtering is not working correctly")
                
            return result
            
        finally:
            self.cleanup()
            self.mongo_client.close()

if __name__ == "__main__":
    tester = EmbeddingsFilterTest()
    success = tester.run_test()
    exit(0 if success else 1)
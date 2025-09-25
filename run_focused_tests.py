#!/usr/bin/env python3

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, '/app')

from backend_test import AttendanceAPITester

def main():
    """Run focused face recognition tests as requested in review"""
    print("🎯 FOCUSED FACE RECOGNITION TESTING")
    print("=" * 60)
    print("Testing face recognition changes as requested:")
    print("1. POST /api/attendance/mark latency and response")
    print("2. Matching logic with mock students")
    print("3. Enrollment with multiple images")
    print("4. Environment variables configuration")
    print("5. Health endpoint verification")
    print("=" * 60)
    
    tester = AttendanceAPITester()
    
    # Run the focused tests
    success = tester.run_focused_tests()
    
    if success:
        print("\n✅ FOCUSED TESTING SUCCESSFUL")
        print("All face recognition changes are working correctly")
        return 0
    else:
        print("\n❌ FOCUSED TESTING FAILED")
        print("Some face recognition changes have issues")
        return 1

if __name__ == "__main__":
    sys.exit(main())
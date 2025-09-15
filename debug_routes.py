#!/usr/bin/env python3
"""
Debug script to check which routes are registered in the FastAPI app
"""

import sys
sys.path.append('/app/backend')

from server import app

def debug_routes():
    print("Registered routes in FastAPI app:")
    print("=" * 50)
    
    for route in app.routes:
        if hasattr(route, 'methods') and hasattr(route, 'path'):
            methods = ', '.join(route.methods)
            print(f"{methods:15} {route.path}")
        elif hasattr(route, 'path'):
            print(f"{'MOUNT':15} {route.path}")
    
    print("\nAPI Router routes:")
    print("=" * 50)
    
    # Find the API router
    for route in app.routes:
        if hasattr(route, 'app') and hasattr(route.app, 'routes'):
            print(f"Found mounted router at: {route.path}")
            for subroute in route.app.routes:
                if hasattr(subroute, 'methods') and hasattr(subroute, 'path'):
                    methods = ', '.join(subroute.methods)
                    full_path = route.path.rstrip('/') + subroute.path
                    print(f"{methods:15} {full_path}")

if __name__ == "__main__":
    debug_routes()
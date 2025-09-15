#!/usr/bin/env python3

import sys
sys.path.append('/app/backend')

from server import app

print("Registered routes:")
for route in app.routes:
    if hasattr(route, 'path') and hasattr(route, 'methods'):
        print(f"{route.methods} {route.path}")
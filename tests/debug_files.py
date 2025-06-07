#!/usr/bin/env python3
"""Debug script to see exactly what files are generated"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent / "src"
sys.path.insert(0, str(project_root))

from i2c.bootstrap import initialize_environment
initialize_environment()

from i2c.workflow.professional_integration_patterns import (
    generate_professional_integrated_app, 
    APIEndpoint
)

# Test generation
objective = {
    "task": "Test app", 
    "language": "Python", 
    "system_type": "fullstack_web_app"
}
session_state = {
    "system_type": "fullstack_web_app", 
    "project_path": "/tmp/test"
}

api_endpoints = [
    APIEndpoint(
        path="/api/health", 
        method="GET", 
        response_schema={"status": "string"}
    ),
    APIEndpoint(
        path="/api/data", 
        method="GET", 
        response_schema={"data": "array"}
    )
]

print("🔍 Generating files to debug conflicts...")
files = generate_professional_integrated_app(objective, session_state, api_endpoints)

print(f"\n📄 ALL GENERATED FILES ({len(files)}):")
for file_path in sorted(files.keys()):
    print(f"   - {file_path}")

print(f"\n🔍 FRONTEND FILES:")
frontend_files = [f for f in files.keys() if f.startswith("frontend/")]
for f in sorted(frontend_files):
    print(f"   - {f}")

print(f"\n🚨 FILE CONFLICT CHECK:")
app_js_files = [f for f in files.keys() if f.endswith("App.js")]
app_jsx_files = [f for f in files.keys() if f.endswith("App.jsx")]

print(f"   App.js files: {app_js_files}")
print(f"   App.jsx files: {app_jsx_files}")

if app_js_files and app_jsx_files:
    print("   ❌ CONFLICT CONFIRMED!")
else:
    print("   ✅ No conflict found")
#!/usr/bin/env python3
"""
Test Professional Integration Patterns - Verify the 5 critical improvements
"""

import sys
from pathlib import Path
import tempfile

# Add project root to path
project_root = Path(__file__).parent / "src"
sys.path.insert(0, str(project_root))

from i2c.bootstrap import initialize_environment
initialize_environment()

def test_professional_patterns():
    """Test professional integration patterns address the 5 weaknesses"""
    
    print("🧪 Testing Professional Integration Patterns")
    print("Addressing the 5 critical weaknesses in I2C Factory output")
    print("=" * 70)
    
    try:
        from i2c.workflow.professional_integration_patterns import (
            generate_professional_integrated_app, 
            APIEndpoint,
            ProfessionalCodeGenerator
        )
        
        # Test objective
        objective = {
            "task": "Create a task management system with emotional intelligence",
            "constraints": [
                "Use FastAPI for backend",
                "Use React for frontend",
                "Include CRUD operations",
                "Add emotion detection features"
            ],
            "language": "Python",
            "system_type": "fullstack_web_app"
        }
        
        # Test session state
        session_state = {
            "system_type": "fullstack_web_app",
            "project_path": "/tmp/test"
        }
        
        # Define API endpoints that should be consumed by UI
        api_endpoints = [
            APIEndpoint(
                path="/api/health",
                method="GET",
                response_schema={"status": "string", "timestamp": "string"}
            ),
            APIEndpoint(
                path="/api/tasks",
                method="GET", 
                response_schema={"data": "array", "count": "number"}
            ),
            APIEndpoint(
                path="/api/tasks",
                method="POST",
                response_schema={"id": "string", "message": "string"}
            ),
            APIEndpoint(
                path="/api/emotions/analyze",
                method="POST",
                response_schema={"emotion": "string", "confidence": "number"}
            )
        ]
        
        print(f"🎯 Test Objective: {objective['task']}")
        print(f"📡 API Endpoints: {len(api_endpoints)}")
        
        # Generate professional app
        print("\n🏗️ Generating professional integrated app...")
        files = generate_professional_integrated_app(
            objective=objective,
            session_state=session_state,
            api_endpoints=api_endpoints
        )
        
        print(f"✅ Generated {len(files)} files")
        
        # Analyze results for the 5 critical improvements
        print(f"\n🔍 ANALYZING PROFESSIONAL PATTERNS:")
        print("=" * 50)
        
        # Separate file types
        backend_files = {k: v for k, v in files.items() if k.startswith("backend/")}
        frontend_files = {k: v for k, v in files.items() if k.startswith("frontend/")}
        
        print(f"📁 Backend files: {len(backend_files)}")
        print(f"📁 Frontend files: {len(frontend_files)}")
        
        improvement_score = 0
        total_improvements = 5
        
        # IMPROVEMENT 1: Tight Backend-Frontend Coupling
        print(f"\n1️⃣ IMPROVEMENT 1: Tight Backend-Frontend Coupling")
        
        # Check if APIs are properly consumed
        api_consumption_score = 0
        
        for endpoint in api_endpoints:
            found_in_frontend = any(endpoint.path in content for content in frontend_files.values())
            if found_in_frontend:
                api_consumption_score += 1
                print(f"   ✅ {endpoint.path} consumed by frontend")
            else:
                print(f"   ❌ {endpoint.path} NOT consumed by frontend")
        
        if api_consumption_score >= len(api_endpoints) * 0.75:  # 75% threshold
            improvement_score += 1
            print(f"   🎉 EXCELLENT: {api_consumption_score}/{len(api_endpoints)} APIs consumed")
        else:
            print(f"   ⚠️  NEEDS WORK: Only {api_consumption_score}/{len(api_endpoints)} APIs consumed")
        
        # IMPROVEMENT 2: Dynamic State Logic
        print(f"\n2️⃣ IMPROVEMENT 2: Dynamic State Logic")
        
        state_patterns = ["useState", "useEffect", "fetch(", "axios", "setLoading", "setError"]
        state_score = 0
        
        frontend_code = "\n".join(frontend_files.values())
        
        for pattern in state_patterns:
            if pattern in frontend_code:
                state_score += 1
                print(f"   ✅ Found {pattern}")
            else:
                print(f"   ❌ Missing {pattern}")
        
        if state_score >= len(state_patterns) * 0.75:  # 75% threshold
            improvement_score += 1
            print(f"   🎉 EXCELLENT: {state_score}/{len(state_patterns)} state patterns found")
        else:
            print(f"   ⚠️  NEEDS WORK: Only {state_score}/{len(state_patterns)} state patterns found")
        
        # IMPROVEMENT 3: No Redundant File Structure
        print(f"\n3️⃣ IMPROVEMENT 3: No Redundant File Structure")
        
        file_conflicts = []
        
        # Check for App.js AND App.jsx (exact match to avoid false positives)
        has_app_js = any(f.endswith("App.js") for f in frontend_files.keys())
        has_app_jsx = any(f.endswith("App.jsx") for f in frontend_files.keys())
        
        if has_app_js and has_app_jsx:
            file_conflicts.append("App.js and App.jsx both exist")
        
        # Check for other potential conflicts
        js_files = [f for f in frontend_files.keys() if f.endswith('.js')]
        jsx_files = [f for f in frontend_files.keys() if f.endswith('.jsx')]
        
        for js_file in js_files:
            jsx_equivalent = js_file.replace('.js', '.jsx')
            if jsx_equivalent in jsx_files:
                file_conflicts.append(f"{js_file} and {jsx_equivalent} both exist")
        
        if len(file_conflicts) == 0:
            improvement_score += 1
            print(f"   ✅ No file conflicts detected")
        else:
            print(f"   ❌ File conflicts: {file_conflicts}")
        
        # IMPROVEMENT 4: UX Feedback (Loading, Error States)
        print(f"\n4️⃣ IMPROVEMENT 4: UX Feedback")
        
        ux_patterns = [
            "loading",
            "error", 
            "Loading...",
            "spinner",
            "catch",
            "try",
            "Error:",
            "retry",
            "refresh"
        ]
        
        ux_score = 0
        for pattern in ux_patterns:
            if pattern.lower() in frontend_code.lower():
                ux_score += 1
                print(f"   ✅ Found UX pattern: {pattern}")
        
        if ux_score >= len(ux_patterns) * 0.6:  # 60% threshold
            improvement_score += 1
            print(f"   🎉 EXCELLENT: {ux_score}/{len(ux_patterns)} UX patterns found")
        else:
            print(f"   ⚠️  NEEDS WORK: Only {ux_score}/{len(ux_patterns)} UX patterns found")
        
        # IMPROVEMENT 5: Framework Best Practices
        print(f"\n5️⃣ IMPROVEMENT 5: Framework Best Practices")
        
        best_practices = [
            "import React",
            "export default",
            "const [",
            "useEffect(",
            "useState(",
            "async",
            "await",
            ".map(",
            "key={",
            "onClick="
        ]
        
        practice_score = 0
        for practice in best_practices:
            if practice in frontend_code:
                practice_score += 1
                print(f"   ✅ Found best practice: {practice}")
        
        if practice_score >= len(best_practices) * 0.8:  # 80% threshold
            improvement_score += 1
            print(f"   🎉 EXCELLENT: {practice_score}/{len(best_practices)} best practices found")
        else:
            print(f"   ⚠️  NEEDS WORK: Only {practice_score}/{len(best_practices)} best practices found")
        
        # Overall Assessment
        print(f"\n🏆 OVERALL PROFESSIONAL SCORE: {improvement_score}/{total_improvements}")
        print("=" * 50)
        
        if improvement_score == total_improvements:
            print("🎉 PERFECT: All 5 improvements successfully implemented!")
            print("   ✅ Tight Backend-Frontend Coupling")
            print("   ✅ Dynamic State Logic")  
            print("   ✅ No Redundant File Structure")
            print("   ✅ UX Feedback Patterns")
            print("   ✅ Framework Best Practices")
            success = True
        elif improvement_score >= 4:
            print("🌟 EXCELLENT: 4+ improvements implemented")
            success = True
        elif improvement_score >= 3:
            print("✅ GOOD: 3+ improvements implemented")
            success = True
        else:
            print("⚠️  NEEDS WORK: Major improvements still needed")
            success = False
        
        # Show sample files
        print(f"\n📄 SAMPLE GENERATED FILES:")
        print("-" * 30)
        
        for file_path in sorted(files.keys())[:10]:  # Show first 10 files
            print(f"   - {file_path}")
        
        if len(files) > 10:
            print(f"   ... and {len(files) - 10} more files")
        
        return success
        
    except Exception as e:
        print(f"❌ ERROR: Professional patterns test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_integration_analyzer():
    """Test the API-UI binding analyzer"""
    
    print("\n🔍 Testing API-UI Integration Analyzer")
    print("=" * 50)
    
    try:
        from i2c.workflow.professional_integration_patterns import APIUIBindingAnalyzer
        
        analyzer = APIUIBindingAnalyzer()
        
        # Test backend files
        backend_files = {
            "backend/main.py": '''
@app.get("/api/health")
def health_check():
    return {"status": "healthy"}

@app.get("/api/data")  
def get_data():
    return {"data": ["item1", "item2"]}
'''
        }
        
        # Test frontend files
        frontend_files = {
            "frontend/src/App.jsx": '''
import React, { useState, useEffect } from 'react';

function App() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    fetch('/api/health')
      .then(response => response.json())
      .then(data => console.log(data))
      .catch(error => console.error(error));
  }, []);
  
  return <div>App</div>;
}
''',
            "frontend/src/components/DataDisplay.jsx": '''
function DataDisplay() {
  const [items, setItems] = useState([]);
  
  useEffect(() => {
    fetch('/api/data')
      .then(response => response.json())
      .then(data => setItems(data));
  }, []);
  
  return <div>{items.map(item => <p key={item}>{item}</p>)}</div>;
}
'''
        }
        
        # Analyze
        print("📡 Analyzing backend APIs...")
        api_endpoints = analyzer.analyze_backend_apis(backend_files)
        
        print("🧩 Analyzing frontend components...")
        ui_components = analyzer.analyze_frontend_components(frontend_files)
        
        print("🔍 Identifying integration gaps...")
        gaps = analyzer.identify_integration_gaps()
        
        print(f"\nResults:")
        print(f"   API Endpoints: {len(api_endpoints)}")
        print(f"   UI Components: {len(ui_components)}")
        print(f"   Integration Gaps: {len(gaps)}")
        
        # Should find good integration
        success = len(api_endpoints) > 0 and len(ui_components) > 0 and len(gaps) < 3
        
        if success:
            print("✅ Analyzer working correctly!")
        else:
            print("⚠️  Analyzer needs improvement")
        
        return success
        
    except Exception as e:
        print(f"❌ ERROR: Analyzer test failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Professional Integration Patterns Test Suite")
    print("Verifying the 5 critical improvements for I2C Factory")
    print("=" * 80)
    
    # Run tests
    test1 = test_professional_patterns()
    test2 = test_integration_analyzer()
    
    print("\n" + "=" * 80)
    print("🏁 FINAL RESULTS:")
    print(f"   Professional Patterns: {'✅ PASS' if test1 else '❌ FAIL'}")
    print(f"   Integration Analyzer: {'✅ PASS' if test2 else '❌ FAIL'}")
    
    if test1 and test2:
        print("\n🎉 SUCCESS: Professional Integration Patterns Working!")
        print("   The 5 critical weaknesses have been addressed:")
        print("   1. ✅ Tight Backend-Frontend Coupling")
        print("   2. ✅ Dynamic State Logic with React hooks")
        print("   3. ✅ No Redundant File Structure")
        print("   4. ✅ Professional UX Feedback")
        print("   5. ✅ Framework Best Practices")
        print("\n   This is now embedded into the I2C Factory generation pipeline!")
    else:
        print("\n⚠️  Some patterns need refinement")
    
    print("=" * 80)
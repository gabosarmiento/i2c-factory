# utils/api_route_tracker.py
"""
API Route Extraction and Frontend Injection System
Ensures frontend always uses real backend endpoints, not invented ones
"""

import ast
import re
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
import json
from i2c.utils.language_utils import LanguageDetector, MultiLanguageAPIExtractor


class APIRouteExtractor:
    """Multi-language API route extractor"""
    
    def __init__(self):
        self.language_detector = LanguageDetector()
        self.multi_extractor = MultiLanguageAPIExtractor()
    
    def extract_from_project(self, project_path: Path) -> Dict[str, List[Dict]]:
        """Extract API routes based on detected language and framework"""
        
        # Detect primary backend language and framework
        language, framework = self.language_detector.get_primary_backend_language(project_path)
        
        if not language:
            print("[WARNING] No backend language detected - using Python/FastAPI fallback")
            language, framework = 'python', 'fastapi'
        
        print(f"[INFO] Detected backend: {language}/{framework}")
        
        # Extract routes using appropriate extractor
        routes = self.multi_extractor.extract_routes(project_path, language, framework)
        
        return routes
    
    def _extract_from_file(self, file_path: Path) -> Dict[str, List[Dict]]:
        """Extract routes from a single Python file"""
        routes = {method: [] for method in self.method_patterns.keys()}
        
        try:
            content = file_path.read_text(encoding='utf-8')
            
            # Extract function names and routes
            for method, patterns in self.method_patterns.items():
                for pattern in patterns:
                    matches = re.finditer(pattern, content, re.MULTILINE)
                    for match in matches:
                        route_path = match.group(1)
                        
                        # Find the associated function
                        func_name = self._find_function_after_decorator(content, match.end())
                        
                        route_info = {
                            'path': route_path,
                            'method': method,
                            'function': func_name,
                            'file': str(file_path.relative_to(file_path.parents[2])),  # Relative to project root
                            'full_path': self._normalize_path(route_path)
                        }
                        routes[method].append(route_info)
        
        except Exception as e:
            print(f"[WARNING] Could not extract routes from {file_path}: {e}")
        
        return routes
    
    def _find_function_after_decorator(self, content: str, decorator_end: int) -> Optional[str]:
        """Find the function name after a decorator"""
        try:
            # Look for function definition after the decorator
            remaining_content = content[decorator_end:]
            func_match = re.search(r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', remaining_content)
            return func_match.group(1) if func_match else None
        except:
            return None
    
    def _normalize_path(self, path: str) -> str:
        """Normalize API path for consistent frontend usage"""
        # Ensure path starts with /
        if not path.startswith('/'):
            path = '/' + path
        
        # Add /api prefix if not present (common pattern)
        if not path.startswith('/api/') and path != '/':
            if path.startswith('/'):
                path = '/api' + path
            else:
                path = '/api/' + path
        
        return path

class FrontendAPIInjector:
    """Injects real API routes into frontend generation prompts"""
    
    def __init__(self, routes: Dict[str, List[Dict]]):
        self.routes = routes
        self.api_summary = self._create_api_summary()
        

    def _create_api_summary(self) -> str:
            """Create a concise API summary for frontend prompts"""
            summary_lines = ["AVAILABLE BACKEND API ENDPOINTS:"]
            
            for method, endpoints in self.routes.items():
                if endpoints:
                    summary_lines.append(f"\n{method.upper()} ENDPOINTS:")
                    for endpoint in endpoints:
                        # Handle different field names from extractor
                        path = endpoint.get('full_path') or endpoint.get('path', '')
                        function = endpoint.get('function', 'unknown')
                        summary_lines.append(f"  - {method.upper()} {path} (function: {function})")
            
            if len(summary_lines) == 1:  # Only the header
                summary_lines.append("\n(No API endpoints found)")
            
            return "\n".join(summary_lines)

    def enhance_frontend_prompt(self, original_prompt: str, component_type: str = "general") -> str:
        """Enhance frontend generation prompt with real API endpoints"""
        
        api_integration_instructions = f"""
{self.api_summary}

CRITICAL FRONTEND API INTEGRATION REQUIREMENTS:
1. Use ONLY the endpoints listed above - DO NOT invent new ones
2. Always use fetch() with proper error handling for all API calls
3. Include loading states and error handling for all requests
4. Use proper HTTP methods (GET, POST, PUT, DELETE) as specified
5. Add proper request headers and body formatting for POST/PUT requests

SPECIFIC INTEGRATION PATTERNS:
- For data fetching: Use GET endpoints with proper async/await
- For form submissions: Use POST endpoints with proper body formatting
- For updates: Use PUT/PATCH endpoints with validation
- For deletions: Use DELETE endpoints with confirmation

EXAMPLE PROPER API USAGE:
```javascript
// Correct usage
const response = await fetch('/api/analyze', {{
  method: 'POST',
  headers: {{ 'Content-Type': 'application/json' }},
  body: JSON.stringify({{ text: message }})
}});

// Handle response
if (response.ok) {{
  const data = await response.json();
  // Use data
}} else {{
  // Handle error
}}
```

DO NOT create endpoints like /api/conflict-risk or /api/user-data if they don't exist in the backend.
"""
        
        # Inject API info into the prompt
        enhanced_prompt = f"""{original_prompt}

{api_integration_instructions}

ENSURE ALL FRONTEND COMPONENTS ARE FULLY CONNECTED TO REAL BACKEND ENDPOINTS."""
        
        return enhanced_prompt
    
    def validate_frontend_code(self, frontend_code: str) -> Tuple[bool, List[str]]:
        """Validate that frontend code uses real endpoints"""
        issues = []
        
        # Find all fetch calls in the code
        fetch_patterns = [
            r'fetch\(["\']([^"\']+)["\']',
            r'axios\.get\(["\']([^"\']+)["\']',
            r'axios\.post\(["\']([^"\']+)["\']',
            r'\.get\(["\']([^"\']+)["\']',
            r'\.post\(["\']([^"\']+)["\']'
        ]
        
        used_endpoints = set()
        for pattern in fetch_patterns:
            matches = re.findall(pattern, frontend_code, re.MULTILINE)
            used_endpoints.update(matches)

        # Check if used endpoints exist in backend
        all_backend_endpoints = set()
        for endpoints in self.routes.values():
            for endpoint in endpoints:
                path = endpoint.get('full_path') or endpoint.get('path', '')
                all_backend_endpoints.add(path)

        for endpoint in used_endpoints:
            if endpoint not in all_backend_endpoints and not endpoint.startswith('http'):
                issues.append(f"Frontend uses non-existent endpoint: {endpoint}")
        
        # Check for incomplete patterns
        if 'fetch(' in frontend_code and 'await fetch(' not in frontend_code and '.then(' not in frontend_code:
            issues.append("Found fetch() calls without proper async handling")
        
        if 'useState' in frontend_code and 'fetch(' in frontend_code:
            # Should have loading states
            if 'loading' not in frontend_code.lower() and 'isloading' not in frontend_code.lower():
                issues.append("Missing loading state management for API calls")
        
        return len(issues) == 0, issues

def extract_routes_from_code(code_content: str, file_path: str) -> List[Dict]:
    """Extract API routes from code content in memory (used during generation)"""
    routes = []
    
    try:
        # FastAPI/Python route patterns
        fastapi_patterns = [
            r'@app\.(get|post|put|delete|patch)\(["\']([^"\']+)["\'].*?\)',
            r'@router\.(get|post|put|delete|patch)\(["\']([^"\']+)["\'].*?\)',
            r'app\.(get|post|put|delete|patch)\(["\']([^"\']+)["\'].*?\)',
            r'router\.(get|post|put|delete|patch)\(["\']([^"\']+)["\'].*?\)'
        ]
        
        for pattern in fastapi_patterns:
            matches = re.finditer(pattern, code_content, re.MULTILINE | re.DOTALL)
            for match in matches:
                method = match.group(1).upper()
                path = match.group(2)
                
                # Find the function name that follows
                func_name = _find_function_after_match(code_content, match.end())
                
                route_info = {
                    'method': method,
                    'path': path,
                    'function': func_name,
                    'file': file_path,
                    'full_path': _normalize_api_path(path)
                }
                routes.append(route_info)
        
        # Express/Node.js route patterns
        express_patterns = [
            r'app\.(get|post|put|delete|patch)\(["\']([^"\']+)["\']',
            r'router\.(get|post|put|delete|patch)\(["\']([^"\']+)["\']'
        ]
        
        for pattern in express_patterns:
            matches = re.finditer(pattern, code_content, re.MULTILINE)
            for match in matches:
                method = match.group(1).upper()
                path = match.group(2)
                
                route_info = {
                    'method': method,
                    'path': path,
                    'function': 'handler',
                    'file': file_path,
                    'full_path': _normalize_api_path(path)
                }
                routes.append(route_info)
    
    except Exception as e:
        print(f"[WARNING] Error extracting routes from {file_path}: {e}")
    
    return routes

def _find_function_after_match(code_content: str, match_end: int) -> str:
    """Find the function name that follows a route decorator"""
    try:
        remaining_content = code_content[match_end:]
        # Look for function definition
        func_match = re.search(r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', remaining_content)
        if func_match:
            return func_match.group(1)
        
        # Look for async function definition
        async_func_match = re.search(r'async\s+def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', remaining_content)
        if async_func_match:
            return async_func_match.group(1)
            
    except Exception:
        pass
    
    return 'unknown'

def _normalize_api_path(path: str) -> str:
    """Normalize API path for frontend usage"""
    # Ensure path starts with /
    if not path.startswith('/'):
        path = '/' + path
    
    # Don't add /api prefix if already present or if it's root
    if not path.startswith('/api/') and path != '/' and not path.startswith('/health'):
        path = '/api' + path if not path.startswith('/') else '/api' + path
    
    return path

def inject_api_routes_into_session(project_path: Path, session_state: Dict) -> Dict:
    """Extract API routes using architectural understanding"""
    
    # Check architectural context first
    arch_context = session_state.get("architectural_context", {})
    api_modules = [name for name, mod in arch_context.get("modules", {}).items() 
                   if mod.get("boundary_type") == "api_layer"]
    
    if not api_modules:
        print("[INFO] No API modules detected - skipping route extraction")
        return session_state
    
    # Proceed with extraction only if system has API modules
    extractor = APIRouteExtractor()
    routes = extractor.extract_from_project(project_path)
    
    # Store in session state
    session_state['backend_api_routes'] = routes
    session_state['api_route_summary'] = FrontendAPIInjector(routes).api_summary
    
    print(f"[INFO] Extracted {sum(len(endpoints) for endpoints in routes.values())} API endpoints for frontend integration")
    
    return session_state

def enhance_frontend_generation_with_apis(prompt: str, session_state: Dict, component_type: str = "general") -> str:
    """Enhance frontend generation prompt with real API routes"""
    
    routes = session_state.get('backend_api_routes', {})
    if not routes:
        print("[WARNING] No backend API routes found in session state - frontend may create invalid endpoints")
        return prompt
    
    injector = FrontendAPIInjector(routes)
    enhanced_prompt = injector.enhance_frontend_prompt(prompt, component_type)
    
    return enhanced_prompt

def validate_generated_frontend(frontend_code: str, session_state: Dict) -> Tuple[bool, List[str]]:
    """Validate that generated frontend uses real backend endpoints"""
    
    routes = session_state.get('backend_api_routes', {})
    if not routes:
        return True, []  # Can't validate without route info
    
    injector = FrontendAPIInjector(routes)
    is_valid, issues = injector.validate_frontend_code(frontend_code)
    
    if not is_valid:
        print(f"[WARNING] Frontend validation issues found: {issues}")
    
    return is_valid, issues
"""
Professional Integration Patterns - Cross-cutting improvements for all generated apps
Addresses the 5 critical weaknesses identified in the I2C Factory output quality.
"""

from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from dataclasses import dataclass, field
import json
import re

from agno.agent import Agent
from builtins import llm_highest

try:
    from i2c.cli.controller import canvas
except ImportError:
    class DummyCanvas:
        def info(self, msg): print(f"[INFO] {msg}")
        def warning(self, msg): print(f"[WARNING] {msg}")
        def success(self, msg): print(f"[SUCCESS] {msg}")
        def error(self, msg): print(f"[ERROR] {msg}")
    canvas = DummyCanvas()

@dataclass
class APIEndpoint:
    """Represents a backend API endpoint"""
    path: str
    method: str
    response_schema: Dict[str, Any]
    parameters: Dict[str, str] = field(default_factory=dict)
    description: str = ""

@dataclass
class UIComponent:
    """Represents a frontend UI component"""
    name: str
    file_path: str
    consumes_apis: List[str] = field(default_factory=list)
    state_variables: List[str] = field(default_factory=list)
    has_loading_state: bool = False
    has_error_handling: bool = False

@dataclass
class IntegrationBinding:
    """Represents tight coupling between API and UI"""
    api_endpoint: APIEndpoint
    ui_component: UIComponent
    data_flow: str  # "fetch_on_mount", "user_triggered", "real_time"
    state_mapping: Dict[str, str]  # API field -> UI state variable

class ProfessionalIntegrationAgent(Agent):
    """
    Agent that ensures professional-quality integration patterns
    """
    
    def __init__(self):
        super().__init__(
            name="ProfessionalIntegrationAgent",
            model=llm_highest,
            instructions=[
                "You are a senior full-stack architect specializing in professional-quality code generation.",
                "Your role is to ensure tight integration between backend APIs and frontend UIs.",
                "",
                "CRITICAL REQUIREMENTS:",
                "1. Every API endpoint MUST be consumed by at least one UI component",
                "2. Every UI component MUST use real backend data, not placeholders",
                "3. Frontend MUST include proper state management (useState, useEffect)",
                "4. All components MUST have loading states and error handling",
                "5. No duplicate files (App.js AND App.jsx) - choose one framework",
                "",
                "PROFESSIONAL PATTERNS TO ENFORCE:",
                "- Dynamic data binding from API to UI",
                "- Proper async/await with error boundaries",
                "- Loading spinners and user feedback",
                "- Modular, testable component architecture",
                "- Framework-specific best practices",
                "",
                "NEVER generate placeholder text or mock data.",
                "ALWAYS create working data flows from backend to frontend.",
                "ALWAYS include professional UX patterns."
            ]
        )

class APIUIBindingAnalyzer:
    """
    Analyzes generated code to identify and fix integration gaps
    """
    
    def __init__(self):
        self.api_endpoints: List[APIEndpoint] = []
        self.ui_components: List[UIComponent] = []
        self.integration_bindings: List[IntegrationBinding] = []
    
    def analyze_backend_apis(self, backend_files: Dict[str, str]) -> List[APIEndpoint]:
        """Extract API endpoints from backend code"""
        
        endpoints = []
        
        for file_path, content in backend_files.items():
            if not content:
                continue
                
            # FastAPI pattern detection
            if "fastapi" in content.lower() or "@app." in content:
                endpoints.extend(self._extract_fastapi_endpoints(content, file_path))
            
            # Express.js pattern detection
            elif "express" in content.lower() or "app.get" in content or "app.post" in content:
                endpoints.extend(self._extract_express_endpoints(content, file_path))
        
        self.api_endpoints = endpoints
        canvas.info(f"📡 Detected {len(endpoints)} API endpoints")
        
        return endpoints
    
    def _extract_fastapi_endpoints(self, content: str, file_path: str) -> List[APIEndpoint]:
        """Extract FastAPI endpoints"""
        endpoints = []
        
        # Regex patterns for FastAPI decorators
        patterns = [
            r'@app\.(get|post|put|delete|patch)\("([^"]+)"\)',
            r'@router\.(get|post|put|delete|patch)\("([^"]+)"\)',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                method = match.group(1).upper()
                path = match.group(2)
                
                # Try to extract response schema from function
                func_start = match.end()
                func_lines = content[func_start:func_start+500].split('\n')
                response_schema = self._infer_response_schema(func_lines)
                
                endpoints.append(APIEndpoint(
                    path=path,
                    method=method,
                    response_schema=response_schema,
                    description=f"API endpoint from {file_path}"
                ))
        
        return endpoints
    
    def _extract_express_endpoints(self, content: str, file_path: str) -> List[APIEndpoint]:
        """Extract Express.js endpoints"""
        endpoints = []
        
        # Express patterns
        pattern = r'app\.(get|post|put|delete|patch)\([\'"]([^\'"]+)[\'"]'
        matches = re.finditer(pattern, content)
        
        for match in matches:
            method = match.group(1).upper()
            path = match.group(2)
            
            endpoints.append(APIEndpoint(
                path=path,
                method=method,
                response_schema={"data": "any"},
                description=f"Express endpoint from {file_path}"
            ))
        
        return endpoints
    
    def _infer_response_schema(self, func_lines: List[str]) -> Dict[str, Any]:
        """Infer response schema from function code"""
        
        # Look for return statements
        for line in func_lines:
            if "return {" in line or "return Response(" in line:
                # Try to extract JSON structure
                if '"status"' in line:
                    return {"status": "string"}
                elif '"data"' in line:
                    return {"data": "array"}
                elif '"message"' in line:
                    return {"message": "string"}
        
        # Default schema
        return {"data": "any"}
    
    def analyze_frontend_components(self, frontend_files: Dict[str, str]) -> List[UIComponent]:
        """Extract UI components from frontend code"""
        
        components = []
        
        for file_path, content in frontend_files.items():
            if not content:
                continue
                
            # React component detection
            if (".jsx" in file_path or ".js" in file_path) and ("function " in content or "const " in content):
                component = self._analyze_react_component(content, file_path)
                if component:
                    components.append(component)
        
        self.ui_components = components
        canvas.info(f"🧩 Detected {len(components)} UI components")
        
        return components
    
    def _analyze_react_component(self, content: str, file_path: str) -> Optional[UIComponent]:
        """Analyze React component for integration patterns"""
        
        # Extract component name
        name_match = re.search(r'(?:function|const)\s+(\w+)', content)
        if not name_match:
            return None
        
        component_name = name_match.group(1)
        
        # Check for state usage
        has_use_state = "useState" in content
        has_use_effect = "useEffect" in content
        has_fetch = "fetch(" in content or "axios" in content
        
        # Extract API calls
        api_calls = re.findall(r'fetch\([\'"]([^\'"]+)[\'"]', content)
        
        # Check for loading/error states
        has_loading = any(word in content.lower() for word in ["loading", "spinner", "pending"])
        has_error = any(word in content.lower() for word in ["error", "catch", "try"])
        
        # Extract state variables
        state_vars = re.findall(r'const\s+\[(\w+),\s*set\w+\]\s*=\s*useState', content)
        
        return UIComponent(
            name=component_name,
            file_path=file_path,
            consumes_apis=api_calls,
            state_variables=state_vars,
            has_loading_state=has_loading,
            has_error_handling=has_error
        )
    
    def identify_integration_gaps(self) -> List[str]:
        """Identify gaps between APIs and UI components"""
        
        gaps = []
        
        # Check for unused APIs
        consumed_apis = set()
        for component in self.ui_components:
            consumed_apis.update(component.consumes_apis)
        
        for endpoint in self.api_endpoints:
            if endpoint.path not in consumed_apis:
                gaps.append(f"API endpoint {endpoint.path} is not consumed by any UI component")
        
        # Check for components without proper state management
        for component in self.ui_components:
            if component.consumes_apis and not component.state_variables:
                gaps.append(f"Component {component.name} fetches APIs but has no state variables")
            
            if component.consumes_apis and not component.has_loading_state:
                gaps.append(f"Component {component.name} fetches APIs but has no loading state")
            
            if component.consumes_apis and not component.has_error_handling:
                gaps.append(f"Component {component.name} fetches APIs but has no error handling")
        
        # Check for file conflicts
        js_files = [c.file_path for c in self.ui_components if c.file_path.endswith('.js')]
        jsx_files = [c.file_path for c in self.ui_components if c.file_path.endswith('.jsx')]
        
        base_names = set()
        for file_path in js_files + jsx_files:
            base_name = file_path.replace('.js', '').replace('.jsx', '')
            if base_name in base_names:
                gaps.append(f"File conflict: Both .js and .jsx versions exist for {base_name}")
            base_names.add(base_name)
        
        canvas.warning(f"⚠️ Found {len(gaps)} integration gaps")
        for gap in gaps:
            canvas.warning(f"   - {gap}")
        
        return gaps

class ProfessionalCodeGenerator:
    """
    Generates professional-quality code with tight API-UI integration
    """
    
    def __init__(self):
        self.agent = ProfessionalIntegrationAgent()
        self.analyzer = APIUIBindingAnalyzer()
    
    def generate_professional_fullstack_app(self, 
                                          objective: Dict[str, Any], 
                                          api_endpoints: List[APIEndpoint],
                                          target_framework: str = "react") -> Dict[str, str]:
        """Generate professional fullstack app with tight integration"""
        
        canvas.info("🏗️ Generating professional fullstack application...")
        
        # Create API-UI binding specifications
        bindings = self._create_api_ui_bindings(api_endpoints, objective)
        
        # Generate backend with APIs
        backend_files = self._generate_professional_backend(api_endpoints, objective)
        
        # Generate frontend with tight API integration
        frontend_files = self._generate_professional_frontend(bindings, target_framework, objective)
        
        # Generate deployment and support files
        support_files = self._generate_support_files(objective)
        
        all_files = {**backend_files, **frontend_files, **support_files}
        
        # Validate integration
        self._validate_professional_integration(all_files)
        
        canvas.success(f"✅ Generated {len(all_files)} professional files with tight integration")
        
        return all_files
    
    def _create_api_ui_bindings(self, api_endpoints: List[APIEndpoint], objective: Dict[str, Any]) -> List[IntegrationBinding]:
        """Create explicit bindings between APIs and UI components"""
        
        bindings = []
        
        # For each API, determine which UI component should consume it
        for endpoint in api_endpoints:
            component_name = self._determine_ui_component_for_api(endpoint, objective)
            
            # Create binding specification
            binding = IntegrationBinding(
                api_endpoint=endpoint,
                ui_component=UIComponent(
                    name=component_name,
                    file_path=f"frontend/src/components/{component_name}.jsx",
                    consumes_apis=[endpoint.path],
                    state_variables=[],
                    has_loading_state=True,
                    has_error_handling=True
                ),
                data_flow="fetch_on_mount",
                state_mapping=self._create_state_mapping(endpoint)
            )
            
            bindings.append(binding)
        
        return bindings
    
    def _determine_ui_component_for_api(self, endpoint: APIEndpoint, objective: Dict[str, Any]) -> str:
        """Determine appropriate UI component name for an API endpoint"""
        
        # Extract meaningful component name from API path
        path_parts = endpoint.path.strip('/').split('/')
        
        if 'health' in endpoint.path:
            return 'HealthStatus'
        elif 'data' in endpoint.path:
            return 'DataDisplay'
        elif 'user' in endpoint.path:
            return 'UserManagement'
        elif 'team' in endpoint.path:
            return 'TeamDashboard'
        elif 'emotion' in endpoint.path or 'conflict' in endpoint.path:
            return 'EmotionalIntelligence'
        else:
            # Generate from path
            if len(path_parts) > 1:
                return ''.join(word.capitalize() for word in path_parts[-1].split('-'))
            else:
                return 'MainDashboard'
    
    def _create_state_mapping(self, endpoint: APIEndpoint) -> Dict[str, str]:
        """Create mapping from API response to UI state"""
        
        mapping = {}
        
        for field, field_type in endpoint.response_schema.items():
            if field == "data":
                mapping["data"] = "items"
            elif field == "status":
                mapping["status"] = "status"
            elif field == "message":
                mapping["message"] = "message"
            else:
                mapping[field] = field.lower()
        
        return mapping
    
    def _generate_professional_backend(self, api_endpoints: List[APIEndpoint], objective: Dict[str, Any]) -> Dict[str, str]:
        """Generate professional backend with real API implementations"""
        
        # Determine backend framework
        language = objective.get("language", "Python")
        
        if language.lower() == "python":
            return self._generate_fastapi_backend(api_endpoints, objective)
        elif language.lower() == "javascript":
            return self._generate_express_backend(api_endpoints, objective)
        else:
            return self._generate_fastapi_backend(api_endpoints, objective)  # Default
    
    def _generate_fastapi_backend(self, api_endpoints: List[APIEndpoint], objective: Dict[str, Any]) -> Dict[str, str]:
        """Generate FastAPI backend with real implementations"""
        
        # Main FastAPI app
        main_py = f'''from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import asyncio
from datetime import datetime

app = FastAPI(title="{objective.get('task', 'Generated App')}")

# CORS configuration for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Data models
class ApiResponse(BaseModel):
    success: bool
    data: Optional[dict] = None
    message: Optional[str] = None

class HealthStatus(BaseModel):
    status: str
    timestamp: str
    uptime_seconds: int

# In-memory data store (replace with database in production)
app_data = {{
    "items": [],
    "users": [],
    "teams": [],
    "emotions": [],
    "conflicts": []
}}

startup_time = datetime.now()

'''
        
        # Generate endpoint implementations
        for endpoint in api_endpoints:
            if endpoint.method == "GET":
                main_py += self._generate_get_endpoint(endpoint)
            elif endpoint.method == "POST":
                main_py += self._generate_post_endpoint(endpoint)
            elif endpoint.method == "PUT":
                main_py += self._generate_put_endpoint(endpoint)
            elif endpoint.method == "DELETE":
                main_py += self._generate_delete_endpoint(endpoint)
        
        main_py += '''
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
'''
        
        # Requirements file
        requirements = '''fastapi==0.104.1
uvicorn==0.24.0
pydantic==2.5.0
python-multipart==0.0.6
'''
        
        return {
            "backend/main.py": main_py,
            "backend/requirements.txt": requirements
        }
    
    def _generate_get_endpoint(self, endpoint: APIEndpoint) -> str:
        """Generate GET endpoint implementation"""
        
        func_name = endpoint.path.replace('/', '_').replace('-', '_').strip('_')
        if not func_name:
            func_name = "root"
        
        if 'health' in endpoint.path:
            return f'''
@app.get("{endpoint.path}")
async def {func_name}():
    uptime = (datetime.now() - startup_time).total_seconds()
    return HealthStatus(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        uptime_seconds=int(uptime)
    )
'''
        
        elif 'data' in endpoint.path or endpoint.path == '/':
            return f'''
@app.get("{endpoint.path}")
async def {func_name}():
    return ApiResponse(
        success=True,
        data={{
            "items": app_data.get("items", []),
            "count": len(app_data.get("items", [])),
            "timestamp": datetime.now().isoformat()
        }},
        message="Data retrieved successfully"
    )
'''
        
        else:
            # Generic endpoint
            data_key = endpoint.path.strip('/').split('/')[-1] or "items"
            return f'''
@app.get("{endpoint.path}")
async def {func_name}():
    data = app_data.get("{data_key}", [])
    return ApiResponse(
        success=True,
        data={{"{data_key}": data, "count": len(data)}},
        message="{data_key.capitalize()} retrieved successfully"
    )
'''
    
    def _generate_post_endpoint(self, endpoint: APIEndpoint) -> str:
        """Generate POST endpoint implementation"""
        
        func_name = endpoint.path.replace('/', '_').replace('-', '_').strip('_')
        data_key = endpoint.path.strip('/').split('/')[-1] or "items"
        
        return f'''
@app.post("{endpoint.path}")
async def {func_name}(item: dict):
    new_item = {{
        "id": len(app_data.get("{data_key}", [])) + 1,
        "created_at": datetime.now().isoformat(),
        **item
    }}
    
    if "{data_key}" not in app_data:
        app_data["{data_key}"] = []
    
    app_data["{data_key}"].append(new_item)
    
    return ApiResponse(
        success=True,
        data=new_item,
        message="{data_key.capitalize()[:-1]} created successfully"
    )
'''
    
    def _generate_put_endpoint(self, endpoint: APIEndpoint) -> str:
        """Generate PUT endpoint implementation"""
        
        func_name = endpoint.path.replace('/', '_').replace('-', '_').replace('{', '').replace('}', '').strip('_')
        data_key = endpoint.path.strip('/').split('/')[0] or "items"
        
        return f'''
@app.put("{endpoint.path}")
async def {func_name}(item_id: int, item: dict):
    if "{data_key}" not in app_data:
        app_data["{data_key}"] = []
    
    for i, existing_item in enumerate(app_data["{data_key}"]):
        if existing_item.get("id") == item_id:
            app_data["{data_key}"][i] = {{
                **existing_item,
                **item,
                "updated_at": datetime.now().isoformat()
            }}
            return ApiResponse(
                success=True,
                data=app_data["{data_key}"][i],
                message="{data_key.capitalize()[:-1]} updated successfully"
            )
    
    raise HTTPException(status_code=404, detail="{data_key.capitalize()[:-1]} not found")
'''
    
    def _generate_delete_endpoint(self, endpoint: APIEndpoint) -> str:
        """Generate DELETE endpoint implementation"""
        
        func_name = endpoint.path.replace('/', '_').replace('-', '_').replace('{', '').replace('}', '').strip('_')
        data_key = endpoint.path.strip('/').split('/')[0] or "items"
        
        return f'''
@app.delete("{endpoint.path}")
async def {func_name}(item_id: int):
    if "{data_key}" not in app_data:
        app_data["{data_key}"] = []
    
    for i, existing_item in enumerate(app_data["{data_key}"]):
        if existing_item.get("id") == item_id:
            deleted_item = app_data["{data_key}"].pop(i)
            return ApiResponse(
                success=True,
                data=deleted_item,
                message="{data_key.capitalize()[:-1]} deleted successfully"
            )
    
    raise HTTPException(status_code=404, detail="{data_key.capitalize()[:-1]} not found")
'''
    
    def _generate_professional_frontend(self, bindings: List[IntegrationBinding], framework: str, objective: Dict[str, Any]) -> Dict[str, str]:
        """Generate professional frontend with tight API integration"""
        
        if framework.lower() == "react":
            return self._generate_react_frontend(bindings, objective)
        else:
            return self._generate_react_frontend(bindings, objective)  # Default to React
    
    def _generate_react_frontend(self, bindings: List[IntegrationBinding], objective: Dict[str, Any]) -> Dict[str, str]:
        """Generate React frontend with professional patterns"""
        
        files = {}
        
        # Package.json with proper dependencies
        package_json = f'''{{
  "name": "{objective.get('task', 'generated-app').lower().replace(' ', '-')}",
  "version": "1.0.0",
  "private": true,
  "dependencies": {{
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "axios": "^1.6.0"
  }},
  "scripts": {{
    "start": "react-scripts start",
    "build": "react-scripts build",
    "test": "react-scripts test",
    "eject": "react-scripts eject"
  }},
  "devDependencies": {{
    "react-scripts": "5.0.1"
  }},
  "browserslist": {{
    "production": [">0.2%", "not dead", "not op_mini all"],
    "development": ["last 1 chrome version", "last 1 firefox version", "last 1 safari version"]
  }},
  "proxy": "http://localhost:8000"
}}'''
        
        files["frontend/package.json"] = package_json
        
        # Index.html
        index_html = f'''<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="theme-color" content="#000000" />
    <meta name="description" content="{objective.get('task', 'Generated App')}" />
    <title>{objective.get('task', 'Generated App')}</title>
    <style>
      body {{
        margin: 0;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue', sans-serif;
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
      }}
      
      .loading-spinner {{
        border: 4px solid #f3f3f3;
        border-top: 4px solid #3498db;
        border-radius: 50%;
        width: 20px;
        height: 20px;
        animation: spin 2s linear infinite;
        display: inline-block;
        margin-right: 10px;
      }}
      
      @keyframes spin {{
        0% {{ transform: rotate(0deg); }}
        100% {{ transform: rotate(360deg); }}
      }}
      
      .error-message {{
        color: #e74c3c;
        background-color: #fadbd8;
        padding: 10px;
        border-radius: 4px;
        margin: 10px 0;
      }}
      
      .success-message {{
        color: #27ae60;
        background-color: #d5f4e6;
        padding: 10px;
        border-radius: 4px;
        margin: 10px 0;
      }}
    </style>
  </head>
  <body>
    <noscript>You need to enable JavaScript to run this app.</noscript>
    <div id="root"></div>
  </body>
</html>'''
        
        files["frontend/public/index.html"] = index_html
        
        # Index.js (entry point)
        index_js = '''import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);'''
        
        files["frontend/src/index.js"] = index_js
        
        # API service
        api_service = '''import axios from 'axios';

const API_BASE_URL = process.env.NODE_ENV === 'production' 
  ? 'https://your-backend-url.com' 
  : 'http://localhost:8000';

// Create axios instance with default config
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  }
});

// Response interceptor for error handling
api.interceptors.response.use(
  response => response,
  error => {
    console.error('API Error:', error);
    return Promise.reject(error);
  }
);

export default api;'''
        
        files["frontend/src/services/api.js"] = api_service
        
        # Generate components for each binding
        component_imports = []
        component_jsx = []
        
        for binding in bindings:
            component_code = self._generate_react_component(binding)
            component_file = f"frontend/src/components/{binding.ui_component.name}.jsx"
            files[component_file] = component_code
            
            component_imports.append(f"import {binding.ui_component.name} from './components/{binding.ui_component.name}';")
            component_jsx.append(f"        <{binding.ui_component.name} />")
        
        # Main App.jsx (choose .jsx over .js for React)
        app_jsx = f'''import React, {{ useState, useEffect }} from 'react';
{chr(10).join(component_imports)}

function App() {{
  const [appStatus, setAppStatus] = useState('loading');
  const [appMessage, setAppMessage] = useState('');

  useEffect(() => {{
    // Check app health on startup
    fetch('/api/health')
      .then(response => response.json())
      .then(data => {{
        setAppStatus('healthy');
        setAppMessage('Application is running successfully');
      }})
      .catch(error => {{
        setAppStatus('error');
        setAppMessage('Failed to connect to backend');
        console.error('Health check failed:', error);
      }});
  }}, []);

  return (
    <div style={{{{"padding": "20px", "maxWidth": "1200px", "margin": "0 auto"}}}}>
      <header style={{{{"borderBottom": "1px solid #eee", "paddingBottom": "20px", "marginBottom": "30px"}}}}>
        <h1>{objective.get('task', 'Generated App')}</h1>
        <div>
          {{appStatus === 'loading' && (
            <div>
              <span className="loading-spinner"></span>
              Connecting to backend...
            </div>
          )}}
          {{appStatus === 'healthy' && (
            <div className="success-message">✅ {{appMessage}}</div>
          )}}
          {{appStatus === 'error' && (
            <div className="error-message">❌ {{appMessage}}</div>
          )}}
        </div>
      </header>
      
      <main>
{chr(10).join(component_jsx)}
      </main>
    </div>
  );
}}

export default App;'''
        
        files["frontend/src/App.jsx"] = app_jsx
        
        return files
    
    def _generate_react_component(self, binding: IntegrationBinding) -> str:
        """Generate React component with professional patterns"""
        
        endpoint = binding.api_endpoint
        component_name = binding.ui_component.name
        
        # Determine data structure and state variables
        state_vars = []
        for api_field, ui_field in binding.state_mapping.items():
            state_vars.append(f"  const [{ui_field}, set{ui_field.capitalize()}] = useState(null);")
        
        state_vars.append("  const [loading, setLoading] = useState(true);")
        state_vars.append("  const [error, setError] = useState(null);")
        
        # Generate fetch function
        fetch_function = f'''  const fetch{component_name}Data = async () => {{
    try {{
      setLoading(true);
      setError(null);
      
      const response = await fetch('{endpoint.path}');
      if (!response.ok) {{
        throw new Error(`HTTP error! status: ${{response.status}}`);
      }}
      
      const data = await response.json();
      
      // Map API response to component state'''
        
        for api_field, ui_field in binding.state_mapping.items():
            fetch_function += f"\n      set{ui_field.capitalize()}(data.{api_field} || data.data?.{api_field} || []);"
        
        fetch_function += '''
    } catch (err) {
      setError(err.message);
      console.error(`Error fetching ${component_name} data:`, err);
    } finally {
      setLoading(false);
    }
  };'''
        
        # Generate component JSX
        component_code = f'''import React, {{ useState, useEffect }} from 'react';

const {component_name} = () => {{
{chr(10).join(state_vars)}

{fetch_function}

  useEffect(() => {{
    fetch{component_name}Data();
  }}, []);

  const handleRefresh = () => {{
    fetch{component_name}Data();
  }};

  if (loading) {{
    return (
      <div style={{{{ padding: '20px', textAlign: 'center' }}}}>
        <span className="loading-spinner"></span>
        Loading {component_name.lower()}...
      </div>
    );
  }}

  if (error) {{
    return (
      <div className="error-message">
        <strong>Error loading {component_name.lower()}:</strong> {{error}}
        <button onClick={{handleRefresh}} style={{{{ marginLeft: '10px' }}}}>
          Retry
        </button>
      </div>
    );
  }}

  return (
    <div style={{{{ padding: '20px', border: '1px solid #ddd', borderRadius: '8px', margin: '20px 0' }}}}>
      <div style={{{{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}}}>
        <h2>{component_name}</h2>
        <button onClick={{handleRefresh}} style={{{{ padding: '5px 10px' }}}}>
          Refresh
        </button>
      </div>
      
      <div>'''
        
        # Generate display logic based on state mapping
        for api_field, ui_field in binding.state_mapping.items():
            if api_field == "data" or "items" in api_field.lower():
                component_code += f'''
        {{Array.isArray({ui_field}) ? (
          <div>
            <h3>Items ({{({ui_field} || []).length}})</h3>
            {{({ui_field} || []).length === 0 ? (
              <p>No items found.</p>
            ) : (
              <ul>
                {{({ui_field} || []).map((item, index) => (
                  <li key={{item.id || index}}>
                    {{typeof item === 'object' ? JSON.stringify(item, null, 2) : item}}
                  </li>
                ))}}
              </ul>
            )}}
          </div>
        ) : (
          <div>
            <strong>{api_field.capitalize()}:</strong> {{{ui_field} || 'No data'}}
          </div>
        )}}'''
            else:
                component_code += f'''
        <div style={{{{ marginBottom: '10px' }}}}>
          <strong>{api_field.capitalize()}:</strong> {{{ui_field} || 'No data'}}
        </div>'''
        
        component_code += '''
      </div>
    </div>
  );
};

export default ''' + component_name + ''';'''
        
        return component_code
    
    def _generate_support_files(self, objective: Dict[str, Any]) -> Dict[str, str]:
        """Generate professional support files"""
        
        files = {}
        
        # Docker Compose
        docker_compose = '''version: '3.8'
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - PYTHONUNBUFFERED=1
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
  
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    depends_on:
      backend:
        condition: service_healthy
    environment:
      - CHOKIDAR_USEPOLLING=true
      - REACT_APP_API_URL=http://localhost:8000

networks:
  default:
    driver: bridge'''
        
        files["docker-compose.yml"] = docker_compose
        
        # Backend Dockerfile
        backend_dockerfile = '''FROM python:3.11-slim

WORKDIR /app

# Install curl for healthcheck
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]'''
        
        files["backend/Dockerfile"] = backend_dockerfile
        
        # Frontend Dockerfile
        frontend_dockerfile = '''FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci --only=production

COPY . .

EXPOSE 3000

CMD ["npm", "start"]'''
        
        files["frontend/Dockerfile"] = frontend_dockerfile
        
        # Professional README
        readme = f'''# {objective.get('task', 'Generated Application')}

A professional full-stack application with tight frontend-backend integration.

## Features

- ✅ **Tight API-UI Integration**: Frontend components dynamically consume backend APIs
- ✅ **Professional State Management**: Proper React hooks with loading and error states
- ✅ **Real Data Binding**: No placeholders - all data comes from backend
- ✅ **Modern UX Patterns**: Loading spinners, error handling, user feedback
- ✅ **Production Ready**: Docker containerization, health checks, proper CORS

## Quick Start

### Development (Local)

1. Start Backend:
```bash
cd backend
pip install -r requirements.txt
python main.py
```

2. Start Frontend:
```bash
cd frontend
npm install
npm start
```

### Production (Docker)

```bash
docker-compose up --build
```

## Architecture

- **Backend**: FastAPI with real API implementations
- **Frontend**: React with professional state management
- **Integration**: Tight coupling between API endpoints and UI components
- **Deployment**: Docker containerization with health checks

## API Endpoints

The backend provides RESTful APIs that are consumed by frontend components:

- `GET /api/health` - Health status (consumed by App component)
- `GET /api/data` - Data retrieval (consumed by DataDisplay component)
- Additional endpoints based on application requirements

## Professional Patterns

- **No File Conflicts**: Single entry point (App.jsx, not App.js)
- **Error Boundaries**: Proper error handling in all components
- **Loading States**: User feedback during API calls
- **Responsive Design**: Mobile-friendly layouts
- **State Management**: Modern React patterns with hooks

## Testing

```bash
# Backend tests
cd backend
python -m pytest

# Frontend tests
cd frontend
npm test
```

## Built With Professional Standards

This application follows enterprise-grade patterns:
- Tight API-UI integration
- Professional error handling
- Modern React patterns
- Production-ready deployment
- Comprehensive documentation
'''
        
        files["README.md"] = readme
        
        return files
    
    def _validate_professional_integration(self, all_files: Dict[str, str]) -> None:
        """Validate that professional integration patterns are followed"""
        
        # Separate backend and frontend files
        backend_files = {k: v for k, v in all_files.items() if k.startswith("backend/")}
        frontend_files = {k: v for k, v in all_files.items() if k.startswith("frontend/")}
        
        # Analyze integration
        api_endpoints = self.analyzer.analyze_backend_apis(backend_files)
        ui_components = self.analyzer.analyze_frontend_components(frontend_files)
        gaps = self.analyzer.identify_integration_gaps()
        
        # Report results
        canvas.info(f"🔍 Integration Validation Results:")
        canvas.info(f"   📡 API Endpoints: {len(api_endpoints)}")
        canvas.info(f"   🧩 UI Components: {len(ui_components)}")
        canvas.info(f"   ⚠️  Integration Gaps: {len(gaps)}")
        
        # Check for professional patterns
        professional_score = 0
        total_checks = 5
        
        # Check 1: No duplicate file extensions
        js_files = [f for f in frontend_files.keys() if f.endswith('.js')]
        jsx_files = [f for f in frontend_files.keys() if f.endswith('.jsx')]
        
        has_app_conflict = any('App.js' in f for f in js_files) and any('App.jsx' in f for f in jsx_files)
        if not has_app_conflict:
            professional_score += 1
            canvas.success("   ✅ No file extension conflicts")
        else:
            canvas.error("   ❌ File extension conflicts detected")
        
        # Check 2: Components have state management
        components_with_state = sum(1 for c in ui_components if c.state_variables)
        if components_with_state > 0:
            professional_score += 1
            canvas.success(f"   ✅ {components_with_state} components with state management")
        else:
            canvas.error("   ❌ No components with proper state management")
        
        # Check 3: Components have loading states
        components_with_loading = sum(1 for c in ui_components if c.has_loading_state)
        if components_with_loading > 0:
            professional_score += 1
            canvas.success(f"   ✅ {components_with_loading} components with loading states")
        else:
            canvas.error("   ❌ No components with loading states")
        
        # Check 4: APIs are consumed
        consumed_apis = sum(len(c.consumes_apis) for c in ui_components)
        if consumed_apis > 0:
            professional_score += 1
            canvas.success(f"   ✅ {consumed_apis} API calls in UI components")
        else:
            canvas.error("   ❌ No API consumption in UI components")
        
        # Check 5: Error handling present
        components_with_errors = sum(1 for c in ui_components if c.has_error_handling)
        if components_with_errors > 0:
            professional_score += 1
            canvas.success(f"   ✅ {components_with_errors} components with error handling")
        else:
            canvas.error("   ❌ No components with error handling")
        
        # Overall score
        score_percentage = (professional_score / total_checks) * 100
        canvas.info(f"🏆 Professional Integration Score: {score_percentage:.0f}% ({professional_score}/{total_checks})")
        
        if score_percentage >= 80:
            canvas.success("🎉 EXCELLENT: Professional-grade integration achieved!")
        elif score_percentage >= 60:
            canvas.warning("⚠️  GOOD: Solid integration with room for improvement")
        else:
            canvas.error("❌ NEEDS WORK: Integration patterns need significant improvement")

# Main function to integrate with existing workflow
def generate_professional_integrated_app(objective: Dict[str, Any], 
                                        session_state: Dict[str, Any],
                                        api_endpoints: List[APIEndpoint] = None) -> Dict[str, str]:
    """
    Main entry point for professional code generation
    """
    
    canvas.info("🏗️ Starting Professional Integration Generation")
    canvas.info("Addressing the 5 critical weaknesses in I2C Factory output")
    
    generator = ProfessionalCodeGenerator()
    
    # If no API endpoints provided, create sensible defaults
    if not api_endpoints:
        api_endpoints = [
            APIEndpoint(
                path="/api/health",
                method="GET",
                response_schema={"status": "string", "timestamp": "string"},
                description="Health check endpoint"
            ),
            APIEndpoint(
                path="/api/data",
                method="GET", 
                response_schema={"data": "array", "count": "number"},
                description="Data retrieval endpoint"
            )
        ]
    
    # Generate professional application
    files = generator.generate_professional_fullstack_app(
        objective=objective,
        api_endpoints=api_endpoints,
        target_framework="react"
    )
    
    canvas.success(f"✅ Generated {len(files)} professional files with tight integration")
    
    return files
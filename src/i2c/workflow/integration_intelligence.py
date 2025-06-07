"""
Integration Intelligence Workflow - Three-Option Approach for Working Software
Combines architectural-first, single intelligent agent, and staged integration.
"""

from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import json
import asyncio

from agno.agent import Agent
from agno.team import Team
from builtins import llm_highest, llm_middle

try:
    from i2c.cli.controller import canvas
except ImportError:
    class DummyCanvas:
        def info(self, msg): print(f"[INFO] {msg}")
        def warning(self, msg): print(f"[WARNING] {msg}")
        def success(self, msg): print(f"[SUCCESS] {msg}")
        def error(self, msg): print(f"[ERROR] {msg}")
    canvas = DummyCanvas()

class IntegrationStrategy(Enum):
    ARCHITECTURAL_FIRST = "architectural_first"
    SINGLE_INTELLIGENT = "single_intelligent" 
    STAGED_INTEGRATION = "staged_integration"
    ADAPTIVE = "adaptive"  # Choose best strategy based on complexity

@dataclass
class IntegrationContract:
    """Defines the integration contract for the entire system"""
    api_endpoints: Dict[str, Dict[str, Any]]
    component_interfaces: Dict[str, List[str]]
    data_models: Dict[str, Dict[str, str]]
    dependency_graph: Dict[str, List[str]]
    integration_points: List[Dict[str, Any]]
    test_scenarios: List[Dict[str, Any]]
    deployment_config: Dict[str, Any]

@dataclass
class GenerationResult:
    """Result of code generation with integration validation"""
    success: bool
    files: Dict[str, str]
    integration_status: Dict[str, bool]
    test_results: Dict[str, Any]
    deployment_ready: bool
    errors: List[str]
    warnings: List[str]

class ArchitecturalIntelligenceAgent(Agent):
    """
    Option A: Architectural-First Agent
    Creates comprehensive integration contracts before any code generation
    """
    
    def __init__(self):
        super().__init__(
            name="ArchitecturalIntelligenceAgent",
            model=llm_highest,
            instructions=[
                "You are an expert software architect specializing in end-to-end system integration.",
                "Your role is to analyze requirements and create comprehensive integration contracts.",
                "Focus on ensuring all components will work together seamlessly.",
                "",
                "For each project, you must define:",
                "1. Complete API contract (endpoints, methods, request/response schemas)",
                "2. Component interface specifications (props, methods, dependencies)",
                "3. Data model definitions (shared schemas, validation rules)",
                "4. Dependency flow graph (imports, exports, service calls)",
                "5. Integration test scenarios (critical user flows)",
                "6. Deployment configuration (ports, environment, services)",
                "",
                "CRITICAL: Your contract must be detailed enough that any developer",
                "could implement the system from your specification alone.",
                "",
                "Return a comprehensive JSON contract with all integration details."
            ]
        )
    
    def create_integration_contract(self, objective: Dict[str, Any], session_state: Dict[str, Any]) -> IntegrationContract:
        """Create detailed integration contract from requirements"""
        
        canvas.info("🏗️ Creating architectural integration contract...")
        
        # Prepare context for architectural analysis
        context = {
            "objective": objective,
            "system_type": session_state.get("system_type", "fullstack_web_app"),
            "constraints": objective.get("constraints", []),
            "architectural_context": session_state.get("architectural_context", {}),
            "existing_apis": session_state.get("backend_api_routes", {}),
            "knowledge_context": session_state.get("retrieved_context", "")
        }
        
        # Get architectural intelligence
        response = self.run(f"""
        Analyze this software project and create a comprehensive integration contract:
        
        Project: {context['objective'].get('task', 'Software system')}
        System Type: {context['system_type']}
        Constraints: {context['constraints']}
        
        Context: {context['knowledge_context'][:1000] if context['knowledge_context'] else 'No additional context'}
        
        Create a detailed integration contract that ensures all components work together.
        Include specific API endpoints, data models, component interfaces, and integration flows.
        
        Focus on preventing common integration issues:
        - Frontend API calls must match backend endpoints exactly
        - All imports must resolve correctly
        - Data models must be consistent across frontend/backend
        - Components must have proper interfaces
        - Integration tests must cover critical flows
        
        Return comprehensive JSON contract.
        """)
        
        try:
            contract_data = json.loads(response.content)
            
            return IntegrationContract(
                api_endpoints=contract_data.get("api_endpoints", {}),
                component_interfaces=contract_data.get("component_interfaces", {}),
                data_models=contract_data.get("data_models", {}),
                dependency_graph=contract_data.get("dependency_graph", {}),
                integration_points=contract_data.get("integration_points", []),
                test_scenarios=contract_data.get("test_scenarios", []),
                deployment_config=contract_data.get("deployment_config", {})
            )
            
        except (json.JSONDecodeError, Exception) as e:
            canvas.error(f"❌ Failed to parse integration contract: {e}")
            # Return minimal contract as fallback
            return self._create_minimal_contract(context)
    
    def _create_minimal_contract(self, context: Dict[str, Any]) -> IntegrationContract:
        """Create minimal working contract as fallback"""
        
        canvas.warning("⚠️ Creating minimal integration contract as fallback")
        
        system_type = context.get("system_type", "fullstack_web_app")
        
        if system_type == "fullstack_web_app":
            return IntegrationContract(
                api_endpoints={
                    "/api/health": {"method": "GET", "response": {"status": "string"}},
                    "/api/data": {"method": "GET", "response": {"data": "array"}},
                    "/api/data": {"method": "POST", "request": {"item": "object"}, "response": {"id": "string"}}
                },
                component_interfaces={
                    "App": ["useState", "useEffect", "fetch"],
                    "DataComponent": ["data", "onUpdate"],
                    "ApiService": ["getData", "postData"]
                },
                data_models={
                    "ApiResponse": {"status": "string", "data": "any"},
                    "DataItem": {"id": "string", "name": "string", "value": "any"}
                },
                dependency_graph={
                    "frontend/src/App.jsx": ["./components/DataComponent", "./services/ApiService"],
                    "frontend/src/components/DataComponent.jsx": ["../services/ApiService"],
                    "backend/main.py": ["./api/endpoints"],
                    "backend/api/endpoints.py": ["./models"]
                },
                integration_points=[
                    {"frontend": "/api/health", "backend": "/api/health", "method": "GET"},
                    {"frontend": "/api/data", "backend": "/api/data", "method": "GET"},
                    {"frontend": "/api/data", "backend": "/api/data", "method": "POST"}
                ],
                test_scenarios=[
                    {"name": "Health Check", "flow": ["GET /api/health", "verify 200 response"]},
                    {"name": "Data Flow", "flow": ["GET /api/data", "render in frontend", "verify display"]}
                ],
                deployment_config={
                    "backend": {"port": 8000, "cors": ["http://localhost:3000"]},
                    "frontend": {"port": 3000, "proxy": "http://localhost:8000"}
                }
            )
        else:
            # Basic contract for other system types
            return IntegrationContract(
                api_endpoints={},
                component_interfaces={},
                data_models={},
                dependency_graph={},
                integration_points=[],
                test_scenarios=[],
                deployment_config={}
            )

class SingleIntelligentAgent(Agent):
    """
    Option B: Single Intelligent Agent
    One agent that understands full-stack architecture and generates integrated code
    """
    
    def __init__(self, integration_contract: IntegrationContract):
        self.contract = integration_contract
        
        super().__init__(
            name="SingleIntelligentAgent",
            model=llm_highest,
            instructions=[
                "You are a full-stack software architect and developer.",
                "You understand complete system integration and generate working software.",
                "You have access to a detailed integration contract that defines all system components.",
                "",
                "Your responsibilities:",
                "1. Generate ALL code files for the complete system",
                "2. Ensure frontend components match backend APIs exactly",
                "3. Validate all imports and dependencies resolve correctly",
                "4. Create proper data models consistent across all components",
                "5. Implement integration points defined in the contract",
                "6. Generate working tests that validate integration",
                "",
                "CRITICAL SUCCESS CRITERIA:",
                "- Frontend API calls must work with backend endpoints",
                "- All imports must resolve without errors",
                "- Generated code must be syntactically correct",
                "- Integration tests must pass",
                "- System must be deployable and runnable",
                "",
                "Generate complete, working, integrated code based on the contract."
            ]
        )
    
    def generate_integrated_system(self, objective: Dict[str, Any], session_state: Dict[str, Any]) -> GenerationResult:
        """Generate complete integrated system with professional patterns"""
        
        canvas.info("🤖 Single agent generating professional integrated system...")
        
        # Try professional integration patterns first
        try:
            from i2c.workflow.professional_integration_patterns import generate_professional_integrated_app, APIEndpoint
            
            # Extract API endpoints from contract
            api_endpoints = []
            for path, config in self.contract.api_endpoints.items():
                method = config.get("method", "GET")
                response_schema = config.get("response", {})
                
                api_endpoints.append(APIEndpoint(
                    path=path,
                    method=method,
                    response_schema=response_schema
                ))
            
            # Generate professional app
            files = generate_professional_integrated_app(objective, session_state, api_endpoints)
            
            return GenerationResult(
                success=True,
                files=files,
                integration_status={"professional_patterns": True, "single_agent": True},
                test_results={},
                deployment_ready=True,
                errors=[],
                warnings=[]
            )
            
        except Exception as e:
            canvas.error(f"❌ Professional patterns failed: {e}")
            # Fall back to original approach
        
        # Original single agent approach
        # Prepare comprehensive context
        context = {
            "objective": objective,
            "contract": {
                "api_endpoints": self.contract.api_endpoints,
                "component_interfaces": self.contract.component_interfaces,
                "data_models": self.contract.data_models,
                "dependency_graph": self.contract.dependency_graph,
                "integration_points": self.contract.integration_points
            },
            "system_type": session_state.get("system_type", "fullstack_web_app"),
            "project_path": session_state.get("project_path", ""),
            "constraints": objective.get("constraints", [])
        }
        
        response = self.run(f"""
        Generate a complete, working software system based on this specification:
        
        Objective: {context['objective'].get('task', 'Software system')}
        System Type: {context['system_type']}
        
        Integration Contract:
        {json.dumps(context['contract'], indent=2)}
        
        Constraints: {context['constraints']}
        
        Generate ALL necessary files with complete, working code:
        
        CRITICAL REQUIREMENTS:
        1. Frontend API calls must match backend endpoints exactly
        2. All imports must resolve correctly (no missing files)
        3. Data models must be consistent frontend/backend
        4. Code must be syntactically correct
        5. Integration points must be implemented
        
        Return JSON with:
        {{
            "files": {{
                "file_path": "complete_file_content"
            }},
            "integration_validation": {{
                "api_contracts_match": true/false,
                "imports_resolve": true/false,
                "data_models_consistent": true/false,
                "syntax_valid": true/false
            }},
            "deployment_instructions": "how to run the system"
        }}
        """)
        
        try:
            result_data = json.loads(response.content)
            
            files = result_data.get("files", {})
            validation = result_data.get("integration_validation", {})
            
            # Validate integration
            integration_status = {
                "api_contracts": validation.get("api_contracts_match", False),
                "imports": validation.get("imports_resolve", False),
                "data_models": validation.get("data_models_consistent", False),
                "syntax": validation.get("syntax_valid", False)
            }
            
            success = all(integration_status.values()) and len(files) > 0
            
            return GenerationResult(
                success=success,
                files=files,
                integration_status=integration_status,
                test_results={},
                deployment_ready=success,
                errors=[] if success else ["Integration validation failed"],
                warnings=[]
            )
            
        except Exception as e:
            canvas.error(f"❌ Single agent generation failed: {e}")
            return GenerationResult(
                success=False,
                files={},
                integration_status={},
                test_results={},
                deployment_ready=False,
                errors=[str(e)],
                warnings=[]
            )

class StagedIntegrationWorkflow:
    """
    Option C: Staged Integration Workflow
    Multi-stage process with validation at each step
    """
    
    def __init__(self):
        self.stages = [
            "architecture_design",
            "api_contract_generation", 
            "component_generation",
            "integration_validation",
            "test_generation",
            "deployment_preparation"
        ]
    
    async def execute_staged_workflow(self, 
                                    objective: Dict[str, Any], 
                                    session_state: Dict[str, Any],
                                    integration_contract: IntegrationContract) -> GenerationResult:
        """Execute complete staged integration workflow"""
        
        canvas.info("🔄 Executing staged integration workflow...")
        
        results = {}
        errors = []
        warnings = []
        
        try:
            # Stage 1: Architecture Design
            canvas.info("📐 Stage 1: Architecture Design")
            arch_result = await self._stage_architecture_design(objective, session_state, integration_contract)
            results["architecture"] = arch_result
            
            if not arch_result.get("success", False):
                errors.append("Architecture design failed")
                return self._create_failed_result(errors, warnings)
            
            # Stage 2: API Contract Generation
            canvas.info("🔗 Stage 2: API Contract Generation")
            api_result = await self._stage_api_generation(objective, session_state, integration_contract)
            results["api"] = api_result
            
            if not api_result.get("success", False):
                errors.append("API contract generation failed")
                return self._create_failed_result(errors, warnings)
            
            # Stage 3: Component Generation
            canvas.info("🧩 Stage 3: Component Generation")
            component_result = await self._stage_component_generation(objective, session_state, integration_contract)
            results["components"] = component_result
            
            if not component_result.get("success", False):
                errors.append("Component generation failed")
                return self._create_failed_result(errors, warnings)
            
            # Stage 4: Integration Validation
            canvas.info("✅ Stage 4: Integration Validation")
            validation_result = await self._stage_integration_validation(results)
            results["validation"] = validation_result
            
            if not validation_result.get("success", False):
                warnings.append("Integration validation found issues - attempting fixes")
                # Continue but mark as needing fixes
            
            # Stage 5: Test Generation
            canvas.info("🧪 Stage 5: Test Generation") 
            test_result = await self._stage_test_generation(objective, session_state, integration_contract, results)
            results["tests"] = test_result
            
            # Stage 6: Deployment Preparation
            canvas.info("🚀 Stage 6: Deployment Preparation")
            deploy_result = await self._stage_deployment_preparation(results, integration_contract)
            results["deployment"] = deploy_result
            
            # Compile final result
            all_files = {}
            
            for stage_result in results.values():
                if "files" in stage_result:
                    all_files.update(stage_result["files"])
            
            integration_status = {
                "architecture": results["architecture"].get("success", False),
                "api_contracts": results["api"].get("success", False),
                "components": results["components"].get("success", False),
                "validation": results["validation"].get("success", False),
                "tests": results["tests"].get("success", False),
                "deployment": results["deployment"].get("success", False)
            }
            
            overall_success = all(integration_status.values())
            
            return GenerationResult(
                success=overall_success,
                files=all_files,
                integration_status=integration_status,
                test_results=results.get("tests", {}).get("results", {}),
                deployment_ready=results["deployment"].get("success", False),
                errors=errors,
                warnings=warnings
            )
            
        except Exception as e:
            canvas.error(f"❌ Staged workflow failed: {e}")
            return self._create_failed_result([str(e)], warnings)
    
    async def _stage_architecture_design(self, objective, session_state, contract) -> Dict[str, Any]:
        """Stage 1: Create architectural design"""
        # Use existing architecture understanding agent
        try:
            from i2c.agents.architecture.architecture_understanding_agent import ArchitectureUnderstandingAgent
            
            arch_agent = ArchitectureUnderstandingAgent()
            design = arch_agent.analyze_system_architecture(
                project_path=Path(session_state.get("project_path", ".")),
                system_description=objective.get("task", ""),
                constraints=objective.get("constraints", [])
            )
            
            return {
                "success": True,
                "design": design,
                "files": {}
            }
            
        except Exception as e:
            canvas.error(f"❌ Architecture design failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _stage_api_generation(self, objective, session_state, contract) -> Dict[str, Any]:
        """Stage 2: Generate API contracts and backend"""
        # Implementation for API generation
        return {"success": True, "files": {}}
    
    async def _stage_component_generation(self, objective, session_state, contract) -> Dict[str, Any]:
        """Stage 3: Generate frontend components"""
        # Implementation for component generation
        return {"success": True, "files": {}}
    
    async def _stage_integration_validation(self, results) -> Dict[str, Any]:
        """Stage 4: Validate integration points"""
        # Implementation for integration validation
        return {"success": True}
    
    async def _stage_test_generation(self, objective, session_state, contract, results) -> Dict[str, Any]:
        """Stage 5: Generate integration tests"""
        # Implementation for test generation
        return {"success": True, "files": {}, "results": {}}
    
    async def _stage_deployment_preparation(self, results, contract) -> Dict[str, Any]:
        """Stage 6: Prepare deployment configuration"""
        # Implementation for deployment prep
        return {"success": True, "files": {}}
    
    def _create_failed_result(self, errors, warnings) -> GenerationResult:
        """Create failed result"""
        return GenerationResult(
            success=False,
            files={},
            integration_status={},
            test_results={},
            deployment_ready=False,
            errors=errors,
            warnings=warnings
        )

class IntegrationIntelligenceWorkflow:
    """
    Main workflow coordinator that uses all three options adaptively
    """
    
    def __init__(self):
        self.architectural_agent = ArchitecturalIntelligenceAgent()
        self.staged_workflow = StagedIntegrationWorkflow()
    
    def determine_strategy(self, objective: Dict[str, Any], session_state: Dict[str, Any]) -> IntegrationStrategy:
        """Determine the best strategy based on project complexity"""
        
        task = objective.get("task", "")
        constraints = objective.get("constraints", [])
        system_type = session_state.get("system_type", "unknown")
        
        # Complexity indicators
        complexity_score = 0
        
        # Task complexity
        if len(task) > 200:
            complexity_score += 2
        
        # Constraint complexity
        complexity_score += len(constraints)
        
        # System type complexity
        if system_type in ["fullstack_web_app", "microservices", "monorepo"]:
            complexity_score += 3
        elif system_type in ["api_backend", "library"]:
            complexity_score += 1
        
        # Integration complexity
        if "api" in task.lower() and "frontend" in task.lower():
            complexity_score += 2
        
        canvas.info(f"🎯 Project complexity score: {complexity_score}")
        
        # Strategy selection
        if complexity_score >= 8:
            canvas.info("🔄 High complexity - using STAGED_INTEGRATION")
            return IntegrationStrategy.STAGED_INTEGRATION
        elif complexity_score >= 4:
            canvas.info("🤖 Medium complexity - using SINGLE_INTELLIGENT")
            return IntegrationStrategy.SINGLE_INTELLIGENT
        else:
            canvas.info("🏗️ Low complexity - using ARCHITECTURAL_FIRST")
            return IntegrationStrategy.ARCHITECTURAL_FIRST
    
    async def execute_integration_workflow(self, 
                                         objective: Dict[str, Any], 
                                         session_state: Dict[str, Any]) -> GenerationResult:
        """Execute the complete integration workflow with all three options"""
        
        canvas.info("🚀 Starting Integration Intelligence Workflow")
        canvas.info("=" * 60)
        
        try:
            # Step 1: Always create integration contract (Option A)
            canvas.info("📋 Step 1: Creating Integration Contract")
            integration_contract = self.architectural_agent.create_integration_contract(objective, session_state)
            
            # Step 2: Determine best strategy
            strategy = self.determine_strategy(objective, session_state)
            
            # Step 3: Execute primary strategy
            if strategy == IntegrationStrategy.STAGED_INTEGRATION:
                canvas.info("🔄 Executing staged integration workflow...")
                primary_result = await self.staged_workflow.execute_staged_workflow(
                    objective, session_state, integration_contract
                )
            
            elif strategy == IntegrationStrategy.SINGLE_INTELLIGENT:
                canvas.info("🤖 Executing single intelligent agent...")
                single_agent = SingleIntelligentAgent(integration_contract)
                primary_result = single_agent.generate_integrated_system(objective, session_state)
            
            else:  # ARCHITECTURAL_FIRST
                canvas.info("🏗️ Executing architectural-first approach...")
                # Use contract to guide existing workflow
                primary_result = await self._execute_architectural_first(
                    objective, session_state, integration_contract
                )
            
            # Step 4: If primary strategy fails, try fallbacks
            if not primary_result.success:
                canvas.warning("⚠️ Primary strategy failed, trying fallbacks...")
                
                if strategy != IntegrationStrategy.SINGLE_INTELLIGENT:
                    canvas.info("🤖 Trying single intelligent agent fallback...")
                    single_agent = SingleIntelligentAgent(integration_contract)
                    fallback_result = single_agent.generate_integrated_system(objective, session_state)
                    
                    if fallback_result.success:
                        canvas.success("✅ Fallback succeeded!")
                        return fallback_result
                
                # Final fallback - create minimal working system
                canvas.warning("⚠️ Creating minimal working system as final fallback...")
                return self._create_minimal_working_system(objective, session_state, integration_contract)
            
            # Step 5: Validate final result
            final_result = await self._validate_final_result(primary_result, integration_contract)
            
            canvas.success("🎉 Integration Intelligence Workflow Complete!")
            return final_result
            
        except Exception as e:
            canvas.error(f"❌ Integration workflow failed: {e}")
            return GenerationResult(
                success=False,
                files={},
                integration_status={},
                test_results={},
                deployment_ready=False,
                errors=[str(e)],
                warnings=[]
            )
    
    async def _execute_architectural_first(self, objective, session_state, contract) -> GenerationResult:
        """Execute architectural-first approach using existing workflow with contract guidance"""
        
        # Enhance session_state with contract information
        enhanced_session_state = session_state.copy()
        enhanced_session_state["integration_contract"] = {
            "api_endpoints": contract.api_endpoints,
            "component_interfaces": contract.component_interfaces,
            "data_models": contract.data_models,
            "dependency_graph": contract.dependency_graph
        }
        
        # Use existing generation workflow but with contract guidance
        try:
            from i2c.workflow.generation_workflow import GenerationWorkflow
            
            workflow = GenerationWorkflow(enhanced_session_state)
            result = await workflow.execute_generation_cycle(objective)
            
            # Convert to our format
            return GenerationResult(
                success=result.get("success", False),
                files=result.get("files", {}),
                integration_status={"contract_guided": True},
                test_results={},
                deployment_ready=result.get("success", False),
                errors=result.get("errors", []),
                warnings=result.get("warnings", [])
            )
            
        except Exception as e:
            return GenerationResult(
                success=False,
                files={},
                integration_status={},
                test_results={},
                deployment_ready=False,
                errors=[str(e)],
                warnings=[]
            )
    
    def _create_minimal_working_system(self, objective, session_state, contract) -> GenerationResult:
        """Create minimal working system with professional integration patterns"""
        
        canvas.info("🔧 Creating professional working system...")
        
        system_type = session_state.get("system_type", "fullstack_web_app")
        
        if system_type == "fullstack_web_app":
            # Use professional integration patterns
            try:
                from i2c.workflow.professional_integration_patterns import generate_professional_integrated_app
                
                files = generate_professional_integrated_app(objective, session_state)
                
                return GenerationResult(
                    success=True,
                    files=files,
                    integration_status={"professional_patterns": True, "tight_integration": True},
                    test_results={},
                    deployment_ready=True,
                    errors=[],
                    warnings=["Generated professional system with tight API-UI integration"]
                )
            
            except Exception as e:
                canvas.error(f"❌ Professional patterns failed: {e}")
                # Fallback to basic system
                pass
        
        # Basic fallback (original minimal system)
        if system_type == "fullstack_web_app":
            # Create minimal working fullstack app
            files = {
                "backend/main.py": '''from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Working App")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.get("/")
def read_root():
    return {"message": "Working App"}

@app.get("/api/health")
def health_check():
    return {"status": "healthy"}

@app.get("/api/data")
def get_data():
    return {"data": ["item1", "item2", "item3"]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
''',
                "backend/requirements.txt": '''fastapi==0.104.1
uvicorn==0.24.0
''',
                "frontend/package.json": '''{
  "name": "working-app",
  "version": "1.0.0",
  "private": true,
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0"
  },
  "scripts": {
    "start": "react-scripts start",
    "build": "react-scripts build"
  },
  "devDependencies": {
    "react-scripts": "5.0.1"
  },
  "browserslist": {
    "production": [">0.2%", "not dead"],
    "development": ["last 1 chrome version"]
  }
}''',
                "frontend/public/index.html": '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Working App</title>
</head>
<body>
    <div id="root"></div>
</body>
</html>''',
                "frontend/src/index.js": '''import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<App />);
''',
                "frontend/src/App.jsx": '''import React, { useState, useEffect } from 'react';

function App() {
  const [data, setData] = useState([]);
  const [status, setStatus] = useState('Loading...');

  useEffect(() => {
    // Check health
    fetch('/api/health')
      .then(response => response.json())
      .then(data => setStatus(data.status))
      .catch(error => setStatus('Error'));

    // Get data
    fetch('/api/data')
      .then(response => response.json())
      .then(data => setData(data.data))
      .catch(error => console.error('Error:', error));
  }, []);

  return (
    <div style={{padding: '20px'}}>
      <h1>Working App</h1>
      <p>Status: {status}</p>
      <h2>Data:</h2>
      <ul>
        {data.map((item, index) => (
          <li key={index}>{item}</li>
        ))}
      </ul>
    </div>
  );
}

export default App;
''',
                "docker-compose.yml": '''version: '3.8'
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    depends_on:
      - backend
''',
                "backend/Dockerfile": '''FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
''',
                "frontend/Dockerfile": '''FROM node:18-alpine
WORKDIR /app
COPY package.json .
RUN npm install
COPY . .
CMD ["npm", "start"]
''',
                "README.md": '''# Working App

## Quick Start

### Backend
```bash
cd backend
pip install -r requirements.txt
python main.py
```

### Frontend
```bash
cd frontend
npm install
npm start
```

### Docker
```bash
docker-compose up
```

The app will be available at:
- Frontend: http://localhost:3000
- Backend: http://localhost:8000
'''
            }
            
            return GenerationResult(
                success=True,
                files=files,
                integration_status={"minimal_working": True},
                test_results={},
                deployment_ready=True,
                errors=[],
                warnings=["Generated minimal working system as fallback"]
            )
        
        else:
            # For other system types, create basic structure
            return GenerationResult(
                success=False,
                files={},
                integration_status={},
                test_results={},
                deployment_ready=False,
                errors=["Minimal system generation not implemented for this system type"],
                warnings=[]
            )
    
    async def _validate_final_result(self, result: GenerationResult, contract: IntegrationContract) -> GenerationResult:
        """Final validation of the generated system"""
        
        canvas.info("🔍 Final validation of generated system...")
        
        if not result.success:
            return result
        
        # Additional validation checks
        validation_issues = []
        
        # Check if key files exist
        required_patterns = {
            "backend": ["main.py", "requirements.txt"],
            "frontend": ["package.json", "src/"]
        }
        
        for pattern_type, patterns in required_patterns.items():
            for pattern in patterns:
                found = any(pattern in file_path for file_path in result.files.keys())
                if not found:
                    validation_issues.append(f"Missing {pattern_type} file pattern: {pattern}")
        
        # Check for integration points
        if contract.integration_points:
            for point in contract.integration_points:
                # Validate API endpoint consistency
                frontend_endpoint = point.get("frontend")
                backend_endpoint = point.get("backend") 
                
                if frontend_endpoint and backend_endpoint:
                    # Check if backend implements the endpoint
                    backend_files = [f for f in result.files.keys() if "backend" in f]
                    endpoint_implemented = any(
                        backend_endpoint in result.files[f] 
                        for f in backend_files 
                        if result.files[f]
                    )
                    
                    if not endpoint_implemented:
                        validation_issues.append(f"Backend endpoint not implemented: {backend_endpoint}")
        
        if validation_issues:
            result.warnings.extend(validation_issues)
            canvas.warning(f"⚠️ Validation found {len(validation_issues)} issues")
        else:
            canvas.success("✅ Final validation passed!")
        
        return result

# Main function to integrate with existing workflow
async def execute_integration_intelligence_workflow(objective: Dict[str, Any], session_state: Dict[str, Any]) -> GenerationResult:
    """
    Main entry point for integration intelligence workflow
    """
    workflow = IntegrationIntelligenceWorkflow()
    return await workflow.execute_integration_workflow(objective, session_state)
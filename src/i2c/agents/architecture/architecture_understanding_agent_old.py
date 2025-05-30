"""
Architecture Understanding Agent - Provides deep structural intelligence
for software system architecture analysis and validation.
"""

from pathlib import Path
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, field
from enum import Enum
import json

from agno.agent import Agent
from builtins import llm_middle

class ArchitecturePattern(Enum):
    """Common architectural patterns"""
    MONOLITH = "monolith"
    LAYERED_MONOLITH = "layered_monolith"
    FULLSTACK_WEB = "fullstack_web"
    API_BACKEND = "api_backend"
    MICROSERVICES = "microservices"
    CLEAN_ARCHITECTURE = "clean_architecture"
    HEXAGONAL = "hexagonal"
    CLI_TOOL = "cli_tool"
    LIBRARY = "library"
    SERVERLESS = "serverless"
    MONOREPO = "monorepo"

class ModuleBoundary(Enum):
    """Types of module boundaries"""
    UI_LAYER = "ui_layer"
    API_LAYER = "api_layer"
    BUSINESS_LOGIC = "business_logic"
    DATA_ACCESS = "data_access"
    INFRASTRUCTURE = "infrastructure"
    SHARED_UTILITIES = "shared_utilities"
    EXTERNAL_SERVICES = "external_services"

@dataclass
class ArchitecturalModule:
    """Represents a logical module in the system"""
    name: str
    boundary_type: ModuleBoundary
    languages: Set[str]
    responsibilities: List[str]
    dependencies: List[str]
    file_patterns: List[str]
    folder_structure: Dict[str, Any]

@dataclass
class StructuralContext:
    """Complete structural understanding of the system"""
    architecture_pattern: ArchitecturePattern
    system_type: str  # "web_app", "cli_tool", "api_service", etc.
    modules: Dict[str, ArchitecturalModule]
    constraints: List[str]
    file_organization_rules: Dict[str, str]
    integration_patterns: List[str]
    quality_expectations: Dict[str, Any]

class ArchitectureUnderstandingAgent(Agent):
    """Agent that develops deep architectural understanding of software systems"""
    
    def __init__(self, **kwargs):
        super().__init__(
            name="ArchitectureAnalyst",
            model=llm_middle,
            description="Analyzes and understands software system architecture patterns and boundaries",
            instructions=[
                "You are an expert software architect who analyzes system requirements and existing code to understand architectural patterns.",
                "Your job is to identify the logical architecture of a software system, not just file structure.",
                "Focus on understanding:",
                "1. What TYPE of system this is (web app, CLI, API, microservice, etc.)",
                "2. What ARCHITECTURAL PATTERN it follows (clean, layered, hexagonal, etc.)",
                "3. Where the LOGICAL BOUNDARIES are (UI/API/business logic/data)",
                "4. How MODULES should be organized and what they're responsible for",
                "5. What CONSTRAINTS and RULES should govern file organization",
                "",
                "Always respond with structured JSON containing architectural analysis.",
                "Be specific about module responsibilities and boundaries.",
                "Consider both current state and intended architecture."
            ],
            **kwargs
        )

    def analyze_system_architecture(self, objective: str, existing_files: List[str] = None, 
                                content_samples: Dict[str, str] = None) -> StructuralContext:
        """Analyze and understand the system architecture with retry logic"""
        
        # Prepare analysis prompt
        analysis_prompt = self._build_analysis_prompt(objective, existing_files, content_samples)
        
        # Retry configuration
        max_retries = 3
        base_delay = 1.0  # Start with 1 second
        
        for attempt in range(max_retries):
            try:
                # Add delay for retry attempts
                if attempt > 0:
                    import time
                    delay = base_delay * (2 ** (attempt - 1))  # Exponential backoff
                    print(f"⏳ Retrying architectural analysis in {delay} seconds (attempt {attempt + 1}/{max_retries})")
                    time.sleep(delay)
                
                # Get architectural analysis
                response = self.run(analysis_prompt)
                content = self._safe_get_response_content(response)
                
                # Parse architectural understanding
                arch_data = self._parse_architectural_response(content)
                
                # Build structural context
                structural_context = self._build_structural_context(arch_data)
                
                print("✅ Architectural analysis completed successfully")
                return structural_context
                
            except Exception as e:
                error_msg = str(e).lower()
                
                # Check if it's a retryable error
                if any(retryable in error_msg for retryable in ['503', 'service unavailable', 'rate limit', 'timeout']):
                    if attempt < max_retries - 1:
                        print(f"⚠️ Retryable error on attempt {attempt + 1}: {e}")
                        continue  # Retry
                    else:
                        print(f"❌ Max retries reached for architectural analysis: {e}")
                else:
                    print(f"❌ Non-retryable error in architectural analysis: {e}")
                
                # Final attempt failed or non-retryable error
                break
        
        # All attempts failed, return fallback
        print("🔄 Using fallback architectural context due to API issues")
        return self._create_fallback_context(objective)

    def _safe_get_response_content(self, response) -> str:
        """Safely extract content from response"""
        try:
            if hasattr(response, 'content'):
                return str(response.content)
            elif hasattr(response, 'text'):
                return str(response.text)
            elif isinstance(response, str):
                return response
            else:
                return str(response)
        except Exception as e:
            print(f"⚠️ Error extracting response content: {e}")
            return ""

    def _build_analysis_prompt(self, objective: str, existing_files: List[str] = None, 
                            content_samples: Dict[str, str] = None) -> str:
        """Build comprehensive analysis prompt with fullstack app detection"""
        
        prompt = f"""Analyze this software system architecture:

    OBJECTIVE: {objective}

    EXISTING FILES: {existing_files or ['None - new project']}

    CONTENT SAMPLES:
    {self._format_content_samples(content_samples or {})}

    CRITICAL: Pay special attention to these patterns to detect system type:

    FULLSTACK WEB APP indicators:
    - Mentions: "React", "frontend", "backend", "API", "web app", "FastAPI", "Express"
    - Should have: frontend (React/Vue) + backend (FastAPI/Flask/Express) separation
    - File structure: frontend/src/ for UI, backend/api/ for endpoints

    API SERVICE indicators:
    - Mentions: "API", "endpoints", "REST", "GraphQL", "microservice"
    - Should have: organized API routes, models, services

    CLI TOOL indicators:
    - Mentions: "command line", "CLI", "terminal", "script"
    - Should have: main entry point, argument parsing

    Please provide architectural analysis in JSON format:

    {{
        "system_type": "fullstack_web_app|api_service|cli_tool|library|desktop_app",
        "architecture_pattern": "fullstack_web|clean_architecture|microservices|layered_monolith",
        "modules": {{
            "frontend": {{
                "boundary_type": "ui_layer",
                "languages": ["javascript", "typescript"],
                "responsibilities": ["React components", "user interface", "client-side logic"],
                "dependencies": ["backend"],
                "folder_structure": {{
                    "base_path": "frontend",
                    "subfolders": ["src", "src/components", "public"]
                }}
            }},
            "backend": {{
                "boundary_type": "api_layer", 
                "languages": ["python"],
                "responsibilities": ["REST API endpoints", "business logic", "data management"],
                "dependencies": [],
                "folder_structure": {{
                    "base_path": "backend",
                    "subfolders": ["api", "models", "services"]
                }}
            }}
        }},
        "file_organization_rules": {{
            "react_components": "frontend/src/components",
            "main_app": "frontend/src",
            "api_endpoints": "backend/api",
            "data_models": "backend/models",
            "business_logic": "backend/services",
            "main_backend": "backend"
        }},
        "constraints": [
            "Frontend components must be in frontend/src/components/",
            "Main React app in frontend/src/App.jsx",
            "Backend must use FastAPI with proper endpoints",
            "API routes in backend/api/ directory",
            "No mixing of frontend and backend code in same files"
        ],
        "integration_patterns": [
            "REST API communication between frontend and backend",
            "JSON data exchange",
            "CORS configuration for development"
        ],
        "code_generation_rules": {{
            "main_backend_file": "FastAPI application with proper imports and app instance",
            "main_frontend_file": "React App component with proper structure", 
            "api_endpoints": "FastAPI router patterns with proper HTTP methods",
            "react_components": "Functional components with hooks"
        }}
    }}

    IMPORTANT: If objective mentions web app, React, FastAPI, frontend+backend, always classify as "fullstack_web_app" with proper module separation."""

        return prompt

    def _format_content_samples(self, content_samples: Dict[str, str]) -> str:
        """Format content samples for analysis"""
        if not content_samples:
            return "No content samples provided"
        
        formatted = []
        for file_path, content in content_samples.items():
            preview = content[:300] + "..." if len(content) > 300 else content
            formatted.append(f"{file_path}:\n{preview}\n")
        
        return "\n".join(formatted)
    
    def _parse_architectural_response(self, content: str) -> Dict[str, Any]:
        """Parse the architectural analysis response with robust error handling"""
        try:
            # Handle different response types
            if hasattr(content, 'content'):
                content = content.content
            elif hasattr(content, 'reasoning_steps'):
                # Skip reasoning_steps attribute that causes errors
                content = str(content)
            else:
                content = str(content)
            
            # Clean response - remove markdown if present
            clean_content = content.strip()
            
            # Remove markdown code blocks
            if clean_content.startswith("```json"):
                clean_content = clean_content[7:]
                if clean_content.endswith("```"):
                    clean_content = clean_content[:-3]
            elif clean_content.startswith("```"):
                clean_content = clean_content[3:]
                if clean_content.endswith("```"):
                    clean_content = clean_content[:-3]
            
            clean_content = clean_content.strip()
            
            # --- Unified JSON extraction -----------------------------------
            from i2c.utils.json_extraction import extract_json_with_fallback

            fallback_data = {
                "system_type": "web_app",
                "architecture_pattern": "fullstack_web", 
                "modules": {},
                "constraints": [],
                "integration_patterns": []
            }

            parsed_data = extract_json_with_fallback(clean_content, fallback_data)

            # At this point we have a dict
            
            # Validate required fields and provide defaults
            validated_data = self._validate_and_fix_analysis_data(parsed_data)
            
            return validated_data
            
        except json.JSONDecodeError as e:
            print(f"⚠️ JSON parsing failed: {e}")
            print(f"⚠️ Raw content: {content[:200]}...")
            return self._create_fallback_analysis()
        except Exception as e:
            print(f"⚠️ Response parsing failed: {e}")
            print(f"⚠️ Content type: {type(content)}")
            return self._create_fallback_analysis()

    def _validate_and_fix_analysis_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and fix architectural analysis data structure"""
        
        # Ensure required fields exist with defaults
        validated: Dict[str, Any] = {
            "system_type": data.get("system_type", "web_app"),
            "architecture_pattern": data.get("architecture_pattern", "fullstack_web"),
            "modules": data.get("modules", {}),
            "file_organization_rules": data.get("file_organization_rules", {}),
            "constraints": data.get("constraints", []),
            "integration_patterns": data.get("integration_patterns", ["REST API"]),
            "quality_expectations": data.get("quality_expectations", {})
        }
        # Auto-upgrade generic “web_app” into a specific type when possible
        modules = validated.get("modules", {})
        if validated["system_type"] == "web_app":
            if {"frontend", "backend"} <= modules.keys():
                validated["system_type"] = "fullstack_web_app"
            elif modules.keys() == {"api"}:
                validated["system_type"] = "api_service"
            elif modules.keys() == {"cli"}:
                validated["system_type"] = "cli_tool"

        # ----- Keep pattern consistent with the chosen system_type ----------
        type_to_pattern: dict[str, str] = {
            "fullstack_web_app": "fullstack_web",
            "api_service": "api_service",
            "cli_tool": "cli_tool",
        }
        expected_pattern = type_to_pattern.get(validated["system_type"])
        if expected_pattern and validated["architecture_pattern"] != expected_pattern:
            validated["architecture_pattern"] = expected_pattern
            
        # Fix modules structure if needed
        if not isinstance(validated["modules"], dict):
            validated["modules"] = {}
        
        # Ensure each module has required fields
        for module_name, module_data in validated["modules"].items():
            if not isinstance(module_data, dict):
                validated["modules"][module_name] = {
                    "boundary_type": "business_logic",
                    "languages": ["python"],
                    "responsibilities": [f"{module_name} functionality"],
                    "dependencies": [],
                    "folder_structure": {"base_path": module_name.lower()}
                }
            else:
                # Fill in missing fields
                module_data.setdefault("boundary_type", "business_logic")
                module_data.setdefault("languages", ["python"])
                module_data.setdefault("responsibilities", [f"{module_name} functionality"])
                module_data.setdefault("dependencies", [])
                module_data.setdefault("folder_structure", {"base_path": module_name.lower()})
        
        # Ensure file organization rules are reasonable
        if not validated["file_organization_rules"]:
            validated["file_organization_rules"] = {
                "ui_components": "frontend/src/components",
                "api_routes": "backend/api/routes",
                "business_logic": "backend/services",
                "data_models": "backend/models"
            }
        
        return validated
 
    def _build_structural_context(self, arch_data: Dict[str, Any]) -> StructuralContext:
        """Build comprehensive structural context from analysis"""
        
        # Map architecture pattern
        pattern_mapping = {
            "monolith": ArchitecturePattern.MONOLITH,
            "layered_monolith": ArchitecturePattern.LAYERED_MONOLITH,  
            "fullstack_web": ArchitecturePattern.FULLSTACK_WEB,
            "clean_architecture": ArchitecturePattern.CLEAN_ARCHITECTURE,
            "hexagonal": ArchitecturePattern.HEXAGONAL,
            "microservices": ArchitecturePattern.MICROSERVICES,
            "cli_tool": ArchitecturePattern.CLI_TOOL,
            "library": ArchitecturePattern.LIBRARY
        }
        
        architecture_pattern = pattern_mapping.get(
            arch_data.get("architecture_pattern", "monolith"),
            ArchitecturePattern.MONOLITH
        )
        
        # Build modules
        modules = {}
        for module_name, module_data in arch_data.get("modules", {}).items():
            boundary_mapping = {
                "ui_layer": ModuleBoundary.UI_LAYER,
                "api_layer": ModuleBoundary.API_LAYER,
                "business_logic": ModuleBoundary.BUSINESS_LOGIC,
                "data_access": ModuleBoundary.DATA_ACCESS,
                "infrastructure": ModuleBoundary.INFRASTRUCTURE,
                "shared_utilities": ModuleBoundary.SHARED_UTILITIES
            }
            
            boundary_type = boundary_mapping.get(
                module_data.get("boundary_type", "business_logic"),
                ModuleBoundary.BUSINESS_LOGIC
            )
            
            modules[module_name] = ArchitecturalModule(
                name=module_name,
                boundary_type=boundary_type,
                languages=set(module_data.get("languages", ["python"])),
                responsibilities=module_data.get("responsibilities", []),
                dependencies=module_data.get("dependencies", []),
                file_patterns=[],  # Will be populated later
                folder_structure=module_data.get("folder_structure", {})
            )
        
        return StructuralContext(
            architecture_pattern=architecture_pattern,
            system_type=arch_data.get("system_type", "web_app"),
            modules=modules,
            constraints=arch_data.get("constraints", []),
            file_organization_rules=arch_data.get("file_organization_rules", {}),
            integration_patterns=arch_data.get("integration_patterns", []),
            quality_expectations=arch_data.get("quality_expectations", {})
        )
    
    def _create_fallback_analysis(self) -> Dict[str, Any]:
        """Create fallback analysis when parsing fails"""
        return {
            "system_type": "web_app",
            "architecture_pattern": "fullstack_web",
            "modules": {
                "frontend": {
                    "boundary_type": "ui_layer",
                    "languages": ["javascript"],
                    "responsibilities": ["user interface"],
                    "dependencies": [],
                    "folder_structure": {"base_path": "frontend/src"}
                },
                "backend": {
                    "boundary_type": "api_layer", 
                    "languages": ["python"],
                    "responsibilities": ["api endpoints"],
                    "dependencies": [],
                    "folder_structure": {"base_path": "backend/app"}
                }
            },
            "file_organization_rules": {
                "ui_components": "frontend/src/components",
                "api_routes": "backend/app/routes"
            },
            "constraints": [],
            "integration_patterns": ["REST API"],
            "quality_expectations": {}
        }
    
    def _create_fallback_context(self, objective: str) -> StructuralContext:
        """Create fallback structural context"""
        fallback_data = self._create_fallback_analysis()
        return self._build_structural_context(fallback_data)
    
    def validate_file_against_architecture(self, file_path: str, content: str, 
                                         structural_context: StructuralContext) -> Dict[str, Any]:
        """Validate if a file fits the architectural understanding"""
        
        validation_result = {
            "is_valid": True,
            "violations": [],
            "suggestions": [],
            "correct_location": file_path
        }
        
        # Check against file organization rules
        for rule_name, expected_path in structural_context.file_organization_rules.items():
            if self._file_matches_rule(file_path, content, rule_name):
                if not file_path.startswith(expected_path):
                    validation_result["is_valid"] = False
                    validation_result["violations"].append(
                        f"File should be in {expected_path} based on {rule_name} rule"
                    )
                    validation_result["correct_location"] = f"{expected_path}/{Path(file_path).name}"
        
        # Check architectural constraints
        for constraint in structural_context.constraints:
            violation = self._check_constraint_violation(file_path, content, constraint)
            if violation:
                validation_result["violations"].append(violation)
                validation_result["is_valid"] = False
        
        return validation_result
    
    def _file_matches_rule(self, file_path: str, content: str, rule_name: str) -> bool:
        """Check if file matches a specific organizational rule"""
        rule_patterns = {
            "ui_components": lambda f, c: "component" in f.lower() or "jsx" in c or "useState" in c,
            "api_routes": lambda f, c: "route" in f.lower() or "@app." in c or "router" in c,
            "business_logic": lambda f, c: "service" in f.lower() or "class " in c,
            "data_models": lambda f, c: "model" in f.lower() or "class " in c and "db" in c.lower()
        }
        
        pattern_func = rule_patterns.get(rule_name)
        return pattern_func(file_path, content) if pattern_func else False
    
    def _check_constraint_violation(self, file_path: str, content: str, constraint: str) -> Optional[str]:
        """Check if file violates an architectural constraint"""
        constraint_lower = constraint.lower()
        content_lower = content.lower()
        
        # Example constraint checks (can be expanded)
        if "ui components must not directly access database" in constraint_lower:
            if ("component" in file_path.lower() and 
                any(db_term in content_lower for db_term in ["sqlite", "mysql", "postgresql", "db.execute"])):
                return "UI component is directly accessing database"
        
        return None

# Global instance for easy access
architecture_agent = None

def get_architecture_agent(session_state=None):
    """Get or create architecture agent with proper session state"""
    global architecture_agent
    
    # Always create a new agent if current one is None
    if architecture_agent is None:
        try:
            # Try to create with session state
            if session_state:
                architecture_agent = ArchitectureUnderstandingAgent(session_state=session_state)
            else:
                architecture_agent = ArchitectureUnderstandingAgent()
                
        except Exception as e:
            print(f"⚠️ Error creating architecture agent with session state: {e}")
            # Fallback: create basic agent
            try:
                architecture_agent = ArchitectureUnderstandingAgent()
            except Exception as e2:
                print(f"❌ Failed to create basic architecture agent: {e2}")
                # Return None and let calling code handle it
                return None
    
    # Verify the agent is properly created
    if architecture_agent is None:
        print("❌ Architecture agent is still None after creation attempts")
        return None
        
    # Verify the agent has the required method
    if not hasattr(architecture_agent, 'analyze_system_architecture'):
        print("❌ Architecture agent missing analyze_system_architecture method")
        return None
    
    return architecture_agent
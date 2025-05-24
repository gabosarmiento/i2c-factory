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
        """Analyze and understand the system architecture from objective and existing code"""
        
        # Prepare analysis prompt
        analysis_prompt = self._build_analysis_prompt(objective, existing_files, content_samples)
        
        try:
            # Get architectural analysis
            response = self.run(analysis_prompt)
            content = response.content if hasattr(response, 'content') else str(response)
            
            # Parse architectural understanding
            arch_data = self._parse_architectural_response(content)
            
            # Build structural context
            structural_context = self._build_structural_context(arch_data)
            
            return structural_context
            
        except Exception as e:
            print(f"⚠️ Architecture analysis failed: {e}")
            return self._create_fallback_context(objective)
    
    def _build_analysis_prompt(self, objective: str, existing_files: List[str] = None, 
                              content_samples: Dict[str, str] = None) -> str:
        """Build comprehensive analysis prompt"""
        
        prompt = f"""Analyze this software system architecture:

OBJECTIVE: {objective}

EXISTING FILES: {existing_files or ['None - new project']}

CONTENT SAMPLES:
{self._format_content_samples(content_samples or {})}

Please provide a comprehensive architectural analysis in JSON format:

{{
    "system_type": "web_app|cli_tool|api_service|library|microservice|desktop_app",
    "architecture_pattern": "monolith|layered_monolith|fullstack_web|clean_architecture|hexagonal|microservices",
    "modules": {{
        "module_name": {{
            "boundary_type": "ui_layer|api_layer|business_logic|data_access|infrastructure|shared_utilities",
            "languages": ["python", "javascript"],
            "responsibilities": ["handle user interactions", "manage data persistence"],
            "dependencies": ["other_module_names"],
            "folder_structure": {{
                "base_path": "frontend/src",
                "subfolders": ["components", "services", "utils"]
            }}
        }}
    }},
    "file_organization_rules": {{
        "ui_components": "frontend/src/components",
        "api_routes": "backend/api/routes",
        "business_logic": "backend/services",
        "data_models": "backend/models"
    }},
    "constraints": [
        "UI components must not directly access database",
        "API layer should validate all inputs",
        "Business logic should be framework-agnostic"
    ],
    "integration_patterns": [
        "REST API between frontend and backend",
        "Repository pattern for data access"
    ],
    "quality_expectations": {{
        "test_coverage": "component_tests_and_integration_tests",
        "code_organization": "clear_separation_of_concerns",
        "documentation": "api_documentation_required"
    }}
}}

Focus on LOGICAL architecture, not just file paths. Understand the PURPOSE and BOUNDARIES of each module."""

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
        """Parse the architectural analysis response"""
        try:
            # Clean response - remove markdown if present
            clean_content = content.strip()
            if clean_content.startswith("```json"):
                clean_content = clean_content[7:-3].strip()
            elif clean_content.startswith("```"):
                clean_content = clean_content[3:-3].strip()
            
            return json.loads(clean_content)
            
        except json.JSONDecodeError as e:
            print(f"⚠️ Failed to parse architectural analysis: {e}")
            return self._create_fallback_analysis()
    
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
architecture_agent = ArchitectureUnderstandingAgent()
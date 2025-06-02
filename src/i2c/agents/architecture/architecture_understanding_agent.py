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

# RAG Integration - Context Builder
class ArchitecturalContextBuilder:
    """
    Utility class for building architectural context from knowledge base.
    
    This class provides methods to retrieve relevant architectural knowledge
    for different system types and architecture patterns.
    """
    
    def __init__(self, knowledge_base=None, default_chunk_count=5, max_tokens=6000):
        """
        Initialize the architectural context builder.
        
        Args:
            knowledge_base: The knowledge base to retrieve from
            default_chunk_count: Default number of chunks to retrieve
            max_tokens: Maximum tokens for context
        """
        self.knowledge_base = knowledge_base
        self.default_chunk_count = default_chunk_count
        self.max_tokens = max_tokens
        self._context_cache = {}
        
        # Try to import canvas for logging
        try:
            from i2c.cli.controller import canvas
            self.canvas = canvas
        except ImportError:
            class DummyCanvas:
                def info(self, msg): print(f"[INFO] {msg}")
                def warning(self, msg): print(f"[WARNING] {msg}")
                def success(self, msg): print(f"[SUCCESS] {msg}")
                def error(self, msg): print(f"[ERROR] {msg}")
            self.canvas = DummyCanvas()
    
    def retrieve_architectural_context(self, objective: str, system_type: str = None, 
                                    architecture_pattern: str = None) -> str:
        """
        Retrieve architectural context relevant to the given objective and system type.
        """
        if not self.knowledge_base:
            return ""

        # 🔐 Build cache key
        cache_key = f"{objective.lower()}_{(system_type or '').lower()}_{(architecture_pattern or '').lower()}"

        if cache_key in self._context_cache:
            self.canvas.info(f"[RAG:ARCH] Using cached architectural context for: {objective[:50]}...")
            return self._context_cache[cache_key]

        try:
            # Log the retrieval operation
            self.canvas.info(f"[RAG:ARCH] Retrieving architectural context for: {objective[:100]}...")

            # Build primary query based on system type and architecture pattern
            main_query = f"software architecture for {objective}"
            if system_type:
                main_query += f" {system_type}"
            if architecture_pattern:
                main_query += f" {architecture_pattern} pattern"

            # Define specific sub-queries for architectural context
            sub_queries = [
                f"software architecture patterns for {system_type or 'applications'}",
                f"{architecture_pattern or 'common'} architecture principles",
                f"module boundaries and responsibilities for {system_type or 'applications'}",
                f"file organization for {system_type or 'software'} projects"
            ]

            # Retrieve composite context
            context = self._retrieve_composite_context(
                main_query=main_query,
                sub_queries=sub_queries,
                main_chunk_count=4,
                sub_chunk_count=2
            )

            # Log stats
            if context:
                self.canvas.success(f"[RAG:ARCH] Retrieved architectural context: ~{len(context)//4} tokens")
            else:
                self.canvas.warning("[RAG:ARCH] No relevant architectural context found")

            # 🔁 Cache the result
            self._context_cache[cache_key] = context
            self.canvas.info(f"[RAG:ARCH] Cached keys: {len(self._context_cache)}")
            return context

        except Exception as e:
            self.canvas.warning(f"[RAG:ARCH] Error retrieving architectural context: {e}")
            return ""

    def retrieve_pattern_specific_context(self, pattern: str) -> str:
        """
        Retrieve context specific to an architecture pattern.
        
        Args:
            pattern: Architecture pattern name
            
        Returns:
            Pattern-specific context
        """
        if not self.knowledge_base or not pattern:
            return ""
            
        try:
            # Get context for this specific pattern
            chunks = self.knowledge_base.retrieve_knowledge(
                query=f"{pattern} architecture pattern best practices",
                limit=3
            )
            
            if not chunks:
                return ""
                
            # Format the chunks
            formatted_chunks = []
            for i, chunk in enumerate(chunks):
                source = chunk.get("source", "Unknown source")
                content = chunk.get("content", "").strip()
                if content:
                    formatted_chunks.append(f"[PATTERN {i+1}] SOURCE: {source}\n{content}")
            
            return "\n\n".join(formatted_chunks)
            
        except Exception as e:
            self.canvas.warning(f"[RAG:ARCH] Error retrieving pattern context: {e}")
            return ""
    
    def _retrieve_composite_context(self, main_query: str, sub_queries: List[str] = None,
                                  main_chunk_count: int = None, sub_chunk_count: int = 2) -> str:
        """
        Retrieve composite context from multiple queries.
        
        Args:
            main_query: The primary query
            sub_queries: List of secondary queries
            main_chunk_count: Number of chunks for main query
            sub_chunk_count: Number of chunks for each sub-query
            
        Returns:
            Combined context
        """
        if not self.knowledge_base:
            return ""
            
        try:
            all_chunks = []
            seen_content = set()  # For deduplication
            
            # Process main query
            main_chunks = self.knowledge_base.retrieve_knowledge(
                query=main_query,
                limit=main_chunk_count or self.default_chunk_count
            )
            
            # Add main chunks first (priority)
            for chunk in main_chunks:
                content = chunk.get("content", "")
                if content and content not in seen_content:
                    all_chunks.append(chunk)
                    seen_content.add(content)
            
            # Process sub-queries if any
            if sub_queries:
                self.canvas.info(f"[RAG:ARCH] Processing {len(sub_queries)} sub-queries...")
                
                for sub_query in sub_queries:
                    sub_chunks = self.knowledge_base.retrieve_knowledge(
                        query=sub_query,
                        limit=sub_chunk_count
                    )
                    
                    # Add only new, non-duplicate chunks
                    for chunk in sub_chunks:
                        content = chunk.get("content", "")
                        if content and content not in seen_content:
                            all_chunks.append(chunk)
                            seen_content.add(content)
                            
                    # Check token budget
                    estimated_tokens = sum(len(chunk.get("content", "")) for chunk in all_chunks) // 4
                    if estimated_tokens >= self.max_tokens:
                        self.canvas.info(f"[RAG:ARCH] Reached token budget with {len(all_chunks)} chunks")
                        break
            
            # Format the combined chunks
            if not all_chunks:
                return ""
                
            formatted_chunks = []
            for i, chunk in enumerate(all_chunks):
                source = chunk.get("source", "Unknown source")
                content = chunk.get("content", "").strip()
                if content:
                    formatted_chunks.append(f"[ARCH {i+1}] SOURCE: {source}\n{content}")
            
            combined_context = "\n\n".join(formatted_chunks)
            
            # Log stats about composite context
            self.canvas.info(f"[RAG:ARCH] Retrieved {len(all_chunks)} chunks for architectural context")
            
            return combined_context
            
        except Exception as e:
            self.canvas.warning(f"[RAG:ARCH] Error retrieving composite context: {e}")
            return ""

class ArchitectureUnderstandingAgent(Agent):
    """Agent that develops deep architectural understanding of software systems"""
    
    def __init__(self, knowledge_base=None, **kwargs):
        """
        Initialize the Architecture Understanding Agent with knowledge retrieval.
        
        Args:
            knowledge_base: Optional knowledge base for retrieving architectural knowledge
            **kwargs: Additional arguments for Agent initialization
        """
        # RAG Integration: Initialize context builder
        self.context_builder = ArchitecturalContextBuilder(
            knowledge_base=knowledge_base,
            default_chunk_count=5,
            max_tokens=8000  # Higher token limit for comprehensive architectural analysis
        )
       
        self.local_context_cache = {}
       
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
    
    def analyze_architecture(self, system_spec: Dict[str, Any]) -> StructuralContext:
            query = system_spec.get("description", "")
            
            # Optional local cache (safe to remove and rely entirely on context_builder cache)
            if query in self._local_context_cache:
                context = self._local_context_cache[query]
            else:
                context = self.context_builder.retrieve_architectural_context(query)
                self._local_context_cache[query] = context
            
    def analyze_system_architecture(self, objective: str, existing_files: List[str] = None, 
                                content_samples: Dict[str, str] = None) -> StructuralContext:
        """
        Analyze and understand the system architecture with knowledge-enhanced context.
        
        Args:
            objective: The system objective or description
            existing_files: Optional list of existing file paths
            content_samples: Optional dict of file content samples
            
        Returns:
            StructuralContext with architectural understanding
        """
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

    def _build_analysis_prompt(
        self,
        objective: str,
        existing_files: List[str] = None,
        content_samples: Dict[str, str] = None
    ) -> str:
        """
        Build a comprehensive analysis prompt with knowledge enhancement.

        Args:
            objective: The system objective.
            existing_files: Optional list of existing file paths.
            content_samples: Optional dict of file content samples.

        Returns:
            Enhanced analysis prompt.
        """
        # Detect system type and architecture pattern from objective
        system_type, architecture_pattern = self._detect_system_type(objective)

        # RAG Integration: Retrieve relevant architectural knowledge
        knowledge_context = ""
        if hasattr(self, 'context_builder') and self.context_builder.knowledge_base:
            arch_context = self.context_builder.retrieve_architectural_context(
                objective=objective,
                system_type=system_type,
                architecture_pattern=architecture_pattern
            )

            pattern_context = ""
            if architecture_pattern:
                pattern_context = self.context_builder.retrieve_pattern_specific_context(
                    pattern=architecture_pattern
                )

            if arch_context and pattern_context:
                knowledge_context = f"{arch_context}\n\n{pattern_context}"
            else:
                knowledge_context = arch_context or pattern_context

            if knowledge_context:
                knowledge_context = f"""
    # ARCHITECTURAL KNOWLEDGE CONTEXT
    The following architectural knowledge is relevant to this analysis:

    {knowledge_context}
    """

        # Construct the full analysis prompt
        prompt = f"""Analyze this software system architecture:

    OBJECTIVE: {objective}

    EXISTING FILES: {existing_files or ['None - new project']}

    CONTENT SAMPLES:
    {self._format_content_samples(content_samples or {})}

    {knowledge_context}CRITICAL: Pay special attention to these patterns to detect system type:

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

    IMPORTANT: If objective mentions web app, React, FastAPI, frontend+backend, always classify as "fullstack_web_app" with proper module separation.
    """

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
    
    def _detect_system_type(self, objective: str) -> tuple:
        """
        Detect system type and architecture pattern from objective.
        
        Args:
            objective: System objective or description
            
        Returns:
            Tuple of (system_type, architecture_pattern)
        """
        objective_lower = objective.lower()
        
        # Detect system type
        system_type = None
        if any(kw in objective_lower for kw in ["web app", "website", "frontend", "react", "vue", "angular"]):
            system_type = "web_app"
            if any(kw in objective_lower for kw in ["backend", "api", "fastapi", "express"]):
                system_type = "fullstack_web_app"
        elif any(kw in objective_lower for kw in ["api", "rest", "graphql", "endpoint", "microservice"]):
            system_type = "api_service"
        elif any(kw in objective_lower for kw in ["cli", "command line", "terminal", "script"]):
            system_type = "cli_tool"
        elif any(kw in objective_lower for kw in ["library", "package", "sdk"]):
            system_type = "library"
            
        # Detect architecture pattern
        architecture_pattern = None
        if "clean architecture" in objective_lower:
            architecture_pattern = "clean_architecture"
        elif "hexagonal" in objective_lower:
            architecture_pattern = "hexagonal"
        elif "microservice" in objective_lower:
            architecture_pattern = "microservices"
        elif "layered" in objective_lower:
            architecture_pattern = "layered_monolith"
        elif any(kw in objective_lower for kw in ["monolith", "single tier"]):
            architecture_pattern = "monolith"
            
        # Map system type to default architecture pattern
        if system_type == "fullstack_web_app" and not architecture_pattern:
            architecture_pattern = "fullstack_web"
        elif system_type == "api_service" and not architecture_pattern:
            architecture_pattern = "clean_architecture"
            
        return system_type, architecture_pattern
    
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
            
            # Use your robust JSON extraction utility
            from i2c.utils.json_extraction import extract_json_with_fallback
            
            # Extract JSON with fallback to default analysis
            parsed_data = extract_json_with_fallback(
                content, 
                fallback=self._create_fallback_analysis()
            )
            
            # Validate required fields and provide defaults
            validated_data = self._validate_and_fix_analysis_data(parsed_data)
            
            return validated_data
            
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
        # Auto-upgrade generic "web_app" into a specific type when possible
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
            """
            Validate if a file fits the architectural understanding.
            
            Args:
                file_path: Path to the file
                content: Content of the file
                structural_context: Architectural context to validate against
                
            Returns:
                Validation result with violations and suggestions
            """
            # RAG Integration: Retrieve relevant file organization knowledge
            file_organization_context = ""
            if hasattr(self, 'context_builder') and self.context_builder.knowledge_base:
                try:
                    # Extract file type and module info for targeted query
                    file_ext = Path(file_path).suffix.lower()
                    module_match = self._identify_module_for_file(file_path, structural_context)
                    
                    # Build query based on file and module
                    query = f"file organization rules for {file_ext} files"
                    if module_match:
                        query += f" in {module_match} module"
                        
                    # Retrieve relevant knowledge
                    file_organization_context = self.context_builder.knowledge_base.retrieve_knowledge(
                        query=query,
                        limit=2
                    )
                    
                    if file_organization_context:
                        # Format knowledge
                        formatted_context = []
                        for i, chunk in enumerate(file_organization_context):
                            source = chunk.get("source", "Unknown source")
                            chunk_content = chunk.get("content", "").strip()
                            if chunk_content:
                                formatted_context.append(f"[FILE ORGANIZATION {i+1}] SOURCE: {source}\n{chunk_content}")
                        
                        file_organization_context = "\n\n".join(formatted_context)
                except Exception as e:
                    print(f"⚠️ Error retrieving file organization context: {e}")
                    file_organization_context = ""
            
            # Base validation result
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
            
            # Add suggestions based on retrieved knowledge if available
            if file_organization_context:
                # Use a simple prompt to extract suggestions from knowledge
                suggestion_prompt = f"""
                    Based on the following file organization rules:

                    {file_organization_context}

                    Extract 1-2 specific suggestions for organizing this file:
                    File: {file_path}
                    Module Type: {self._identify_module_for_file(file_path, structural_context) or 'unknown'}

                    Provide ONLY the suggestions, one per line.
                """
                try:
                    suggestion_response = self.model.run(suggestion_prompt)
                    suggestion_text = getattr(suggestion_response, 'content', str(suggestion_response))
                    
                    # Clean and add suggestions
                    for line in suggestion_text.strip().split('\n'):
                        if line and not line.startswith('#') and len(line) > 10:
                            validation_result["suggestions"].append(line.strip())
                except Exception as e:
                    print(f"⚠️ Error generating suggestions: {e}")
            
            return validation_result
        
    def _identify_module_for_file(self, file_path: str, structural_context: StructuralContext) -> Optional[str]:
        """Identify which module a file belongs to based on path patterns"""
        for module_name, module in structural_context.modules.items():
            folder_structure = module.folder_structure or {}
            base_path = folder_structure.get("base_path", "")
            
            if base_path and file_path.startswith(base_path):
                return module_name
                
        return None
    
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
    
    def analyze_project_architecture(self, project_path: Path, file_patterns: List[str] = None) -> Dict[str, Any]:
        """
        Analyze the architecture of an existing project.
        
        Args:
            project_path: Path to the project root
            file_patterns: Optional list of file patterns to include
            
        Returns:
            Dictionary with architectural analysis
        """
        # Set default file patterns if not provided
        if not file_patterns:
            file_patterns = ["*.py", "*.js", "*.ts", "*.jsx", "*.tsx", "*.java", "*.go"]
            
        # Collect files matching patterns
        all_files = []
        for pattern in file_patterns:
            all_files.extend(list(project_path.glob(f"**/{pattern}")))
            
        # Sort files by path
        all_files.sort()
        
        # Select sample files for analysis (up to 20 files)
        sample_files = []
        content_samples = {}
        
        # Select representative files from different directories
        dirs_seen = set()
        for file_path in all_files:
            rel_path = file_path.relative_to(project_path)
            parent_dir = str(rel_path.parent)
            
            # Take first file from each directory
            if parent_dir not in dirs_seen and len(sample_files) < 20:
                sample_files.append(str(rel_path))
                dirs_seen.add(parent_dir)
                
                # Read file content for sample
                try:
                    content = file_path.read_text(errors='ignore')
                    # Limit content size
                    content = content[:2000] + "..." if len(content) > 2000 else content
                    content_samples[str(rel_path)] = content
                except Exception as e:
                    print(f"⚠️ Error reading {rel_path}: {e}")
        
        # RAG Integration: Retrieve project-specific knowledge
        project_knowledge = ""
        if hasattr(self, 'context_builder') and self.context_builder.knowledge_base:
            try:
                # Extract key terms from file paths for better query
                file_terms = " ".join(sample_files)
                query = f"architecture patterns for project with files: {file_terms[:200]}"
                
                chunks = self.context_builder.knowledge_base.retrieve_knowledge(
                    query=query,
                    limit=3
                )
                
                if chunks:
                    # Format knowledge
                    formatted_chunks = []
                    for i, chunk in enumerate(chunks):
                        source = chunk.get("source", "Unknown source")
                        content = chunk.get("content", "").strip()
                        if content:
                            formatted_chunks.append(f"[PROJECT PATTERN {i+1}] SOURCE: {source}\n{content}")
                    
                    project_knowledge = "\n\n".join(formatted_chunks)
            except Exception as e:
                print(f"⚠️ Error retrieving project knowledge: {e}")
        
        # Infer project objective from file structure
        objective = self._infer_project_objective(sample_files, content_samples)
        
        # Analyze architecture with samples and inferred objective
        if project_knowledge:
            # Add project knowledge to the objective
            enhanced_objective = f"{objective}\n\nRELEVANT PROJECT PATTERNS:\n{project_knowledge}"
        else:
            enhanced_objective = objective
            
        structural_context = self.analyze_system_architecture(
            objective=enhanced_objective,
            existing_files=sample_files,
            content_samples=content_samples
        )
        
        # Convert to dictionary for easier serialization
        result = {
            "project_path": str(project_path),
            "files_analyzed": len(sample_files),
            "inferred_objective": objective,
            "system_type": structural_context.system_type,
            "architecture_pattern": structural_context.architecture_pattern.value,
            "modules": {
                name: {
                    "boundary_type": module.boundary_type.value,
                    "languages": list(module.languages),
                    "responsibilities": module.responsibilities,
                    "dependencies": module.dependencies,
                    "folder_structure": module.folder_structure
                }
                for name, module in structural_context.modules.items()
            },
            "constraints": structural_context.constraints,
            "file_organization_rules": structural_context.file_organization_rules,
            "integration_patterns": structural_context.integration_patterns
        }
        
        return result
    
    def _infer_project_objective(self, files: List[str], content_samples: Dict[str, str]) -> str:
        """Infer project objective from file structure and content samples"""
        # Prepare a simple prompt for objective inference
        file_list = "\n".join(files[:15])  # Limit to first 15 files
        
        # Build content preview
        content_preview = ""
        for i, (file_path, content) in enumerate(list(content_samples.items())[:5]):
            # Take just first few lines
            preview = "\n".join(content.split("\n")[:10])
            content_preview += f"--- {file_path} ---\n{preview}\n\n"
        
        inference_prompt = f"""
            Based on the following file structure and content samples, infer the main objective and purpose of this software project.
            Be specific about what the project does, but keep your answer concise (2-3 sentences).

            FILE STRUCTURE:
            {file_list}

            CONTENT SAMPLES:
            {content_preview}

            Objective:
        """
        
        try:
            response = self.model.run(inference_prompt)
            inferred_objective = getattr(response, 'content', str(response)).strip()
            
            # Clean up the objective
            inferred_objective = inferred_objective.replace("Objective:", "").strip()
            
            return inferred_objective
        except Exception as e:
            print(f"⚠️ Error inferring project objective: {e}")
            return "Unknown project objective"

# Global instance for easy access
architecture_agent = None

def get_architecture_agent(session_state=None, knowledge_base=None):
    """
    Get or create architecture agent with proper knowledge integration.
    
    Args:
        session_state: Optional session state for configuration
        knowledge_base: Optional knowledge base for context retrieval
        
    Returns:
        Configured ArchitectureUnderstandingAgent
    """
    global architecture_agent
    
    # Create a new agent if current one is None
    # if architecture_agent is None:
    try:
        # Try to get knowledge base from session state if not provided
        if knowledge_base is None and session_state is not None:
            from i2c.workflow.modification.rag_config import get_embed_model
            
            # Get embed model from session or create new
            embed_model = session_state.get("embed_model")
            if embed_model is None:
                embed_model = get_embed_model()
                
            if embed_model:
                # Create knowledge manager
                try:
                    from i2c.agents.knowledge.knowledge_manager import ExternalKnowledgeManager
                    
                    # Get db path from session state or use default
                    db_path = session_state.get("db_path", "./data/lancedb")
                    
                    knowledge_base = ExternalKnowledgeManager(
                        embed_model=embed_model,
                        db_path=db_path
                    )
                except Exception as e:
                    print(f"⚠️ Error creating knowledge base: {e}")
        
        # Create the agent with knowledge base if available            
        architecture_agent = ArchitectureUnderstandingAgent(
            knowledge_base=knowledge_base,
            session_state=session_state
        )
            
    except Exception as e:
        print(f"⚠️ Error creating architecture agent with session state: {e}")
        # Fallback: create basic agent without knowledge base
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
"""
Project Layout Analyzer - Detects and models project architecture patterns
for intelligent file routing and placement across different project types.
"""

from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
from enum import Enum
import re

class ArchitectureType(Enum):
    MONOLITH = "monolith"
    FRONTEND_BACKEND = "frontend_backend"
    MICROSERVICES = "microservices"
    CLEAN_ARCHITECTURE = "clean_architecture"
    LIBRARY = "library"
    UNKNOWN = "unknown"

class ComponentType(Enum):
    FRONTEND = "frontend"
    BACKEND = "backend"
    API = "api"
    DATABASE = "database"
    TESTS = "tests"
    DOCS = "docs"
    CONFIG = "config"
    SHARED = "shared"
    SERVICES = "services"

@dataclass
class ProjectComponent:
    """Represents a semantic component of the project"""
    name: str
    type: ComponentType
    path: Path
    languages: Set[str]
    patterns: List[str]  # File patterns that belong to this component
    
@dataclass
class ProjectLayout:
    """Semantic model of project structure"""
    root_path: Path
    architecture: ArchitectureType
    components: Dict[ComponentType, ProjectComponent]
    language_primary: str
    languages_detected: Set[str]
    routing_rules: Dict[str, str]  # Logical name -> actual path mapping

class ProjectLayoutAnalyzer:
    """Analyzes project structure and builds semantic layout model"""
    
    def __init__(self):
        self.ignore_patterns = {
            '.git', '__pycache__', '.venv', 'node_modules', 
            '.pytest_cache', 'dist', 'build', '.next',
            'target', 'bin', 'obj'
        }
        
    def analyze(self, project_path: Path) -> ProjectLayout:
        """Analyze project and return semantic layout model"""
        if not project_path.exists() or not project_path.is_dir():
            return self._create_default_layout(project_path)
        
        # Scan project structure
        files_and_dirs = self._scan_project(project_path)
        
        # Detect languages
        languages = self._detect_languages(files_and_dirs['files'])
        primary_language = self._determine_primary_language(languages)
        
        # Detect architecture pattern
        architecture = self._detect_architecture(project_path, files_and_dirs)
        
        # Identify components
        components = self._identify_components(project_path, files_and_dirs, architecture)
        
        # Build routing rules
        routing_rules = self._build_routing_rules(components, architecture)
        
        return ProjectLayout(
            root_path=project_path,
            architecture=architecture,
            components=components,
            language_primary=primary_language,
            languages_detected=languages,
            routing_rules=routing_rules
        )
    
    def _scan_project(self, project_path: Path) -> Dict[str, List[Path]]:
        """Scan project and categorize files and directories"""
        files = []
        directories = []
        
        for item in project_path.rglob("*"):
            # Skip ignored patterns
            if any(ignore in item.parts for ignore in self.ignore_patterns):
                continue
                
            if item.is_file():
                files.append(item)
            elif item.is_dir():
                directories.append(item)
        
        return {"files": files, "directories": directories}
    
    def _detect_languages(self, files: List[Path]) -> Set[str]:
        """Detect programming languages used in project"""
        language_extensions = {
            '.py': 'python',
            '.js': 'javascript',
            '.jsx': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.go': 'go',
            '.java': 'java',
            '.cs': 'csharp',
            '.cpp': 'cpp',
            '.c': 'c',
            '.rb': 'ruby',
            '.php': 'php',
            '.rs': 'rust',
            '.swift': 'swift',
            '.kt': 'kotlin'
        }
        
        languages = set()
        for file_path in files:
            ext = file_path.suffix.lower()
            if ext in language_extensions:
                languages.add(language_extensions[ext])
        
        return languages
    
    def _determine_primary_language(self, languages: Set[str]) -> str:
        """Determine the primary programming language"""
        if not languages:
            return "unknown"
        
        # Priority order for primary language detection
        priority = ['python', 'javascript', 'typescript', 'go', 'java']
        
        for lang in priority:
            if lang in languages:
                return lang
        
        return list(languages)[0]  # Return first detected if no priority match
    
    def _detect_architecture(self, project_path: Path, files_and_dirs: Dict) -> ArchitectureType:
        """Detect project architecture pattern"""
        directories = [d.name.lower() for d in files_and_dirs['directories']]
        files = [f.name.lower() for f in files_and_dirs['files']]
        
        # Check for frontend/backend separation
        has_frontend = any(name in directories for name in ['frontend', 'client', 'web', 'ui', 'app'])
        has_backend = any(name in directories for name in ['backend', 'server', 'api', 'service'])
        
        if has_frontend and has_backend:
            return ArchitectureType.FRONTEND_BACKEND
        
        # Check for microservices
        service_indicators = ['services', 'microservices', 'ms-', 'service-']
        has_services = any(any(indicator in d for indicator in service_indicators) for d in directories)
        
        if has_services or len([d for d in directories if 'service' in d]) > 2:
            return ArchitectureType.MICROSERVICES
        
        # Check for clean architecture
        clean_indicators = ['domain', 'application', 'infrastructure', 'presentation']
        clean_matches = sum(1 for indicator in clean_indicators if indicator in directories)
        
        if clean_matches >= 2:
            return ArchitectureType.CLEAN_ARCHITECTURE
        
        # Check for library structure
        lib_indicators = ['lib', 'src', 'tests', 'examples']
        lib_matches = sum(1 for indicator in lib_indicators if indicator in directories)
        setup_py = 'setup.py' in files or 'pyproject.toml' in files
        package_json = 'package.json' in files
        
        if (lib_matches >= 2 and (setup_py or package_json)) or len(directories) <= 3:
            return ArchitectureType.LIBRARY
        
        # Default to monolith
        return ArchitectureType.MONOLITH
    
    def _identify_components(self, project_path: Path, files_and_dirs: Dict, 
                           architecture: ArchitectureType) -> Dict[ComponentType, ProjectComponent]:
        """Identify semantic components in the project"""
        components = {}
        directories = files_and_dirs['directories']
        
        # Component detection patterns
        patterns = {
            ComponentType.FRONTEND: ['frontend', 'client', 'web', 'ui', 'app', 'www'],
            ComponentType.BACKEND: ['backend', 'server', 'api', 'service'],
            ComponentType.API: ['api', 'endpoints', 'routes', 'controllers'],
            ComponentType.DATABASE: ['db', 'database', 'data', 'models', 'migrations'],
            ComponentType.TESTS: ['tests', 'test', 'spec', '__tests__'],
            ComponentType.DOCS: ['docs', 'documentation', 'doc'],
            ComponentType.CONFIG: ['config', 'conf', 'settings'],
            ComponentType.SHARED: ['shared', 'common', 'utils', 'lib'],
            ComponentType.SERVICES: ['services', 'microservices']
        }
        
        for directory in directories:
            dir_name = directory.name.lower()
            relative_path = directory.relative_to(project_path)
            
            for component_type, component_patterns in patterns.items():
                for pattern in component_patterns:
                    if pattern in dir_name or dir_name.startswith(pattern):
                        if component_type not in components:
                            # Detect languages in this component
                            component_files = list(directory.rglob("*"))
                            component_languages = self._detect_languages([f for f in component_files if f.is_file()])
                            
                            components[component_type] = ProjectComponent(
                                name=directory.name,
                                type=component_type,
                                path=relative_path,
                                languages=component_languages,
                                patterns=component_patterns
                            )
                        break
        
        return components
    
    def _build_routing_rules(self, components: Dict[ComponentType, ProjectComponent], 
                           architecture: ArchitectureType) -> Dict[str, str]:
        """Build routing rules for logical names to actual paths"""
        rules = {}
        
        # Basic routing for common logical names
        if ComponentType.FRONTEND in components:
            frontend_comp = components[ComponentType.FRONTEND]
            rules['frontend'] = str(frontend_comp.path)
            
            # Frontend-specific routing
            if 'javascript' in frontend_comp.languages or 'typescript' in frontend_comp.languages:
                rules['frontend_component'] = f"{frontend_comp.path}/src"
                rules['frontend_test'] = f"{frontend_comp.path}/src"
            
        if ComponentType.BACKEND in components:
            backend_comp = components[ComponentType.BACKEND]
            rules['backend'] = str(backend_comp.path)
            
            # Backend-specific routing  
            if 'python' in backend_comp.languages:
                rules['backend_module'] = f"{backend_comp.path}/app"
                rules['backend_test'] = f"{backend_comp.path}/tests"
            
        if ComponentType.API in components:
            api_comp = components[ComponentType.API]
            rules['api'] = str(api_comp.path)
            
        if ComponentType.TESTS in components:
            tests_comp = components[ComponentType.TESTS]
            rules['tests'] = str(tests_comp.path)
        
        # Architecture-specific rules
        if architecture == ArchitectureType.CLEAN_ARCHITECTURE:
            rules['domain'] = 'domain'
            rules['application'] = 'application'
            rules['infrastructure'] = 'infrastructure'
        
        return rules
    
    def _create_default_layout(self, project_path: Path) -> ProjectLayout:
        """Create default layout for new/empty projects"""
        return ProjectLayout(
            root_path=project_path,
            architecture=ArchitectureType.UNKNOWN,
            components={},
            language_primary="python",  # Default assumption
            languages_detected=set(),
            routing_rules={}
        )
    
    def resolve_logical_path(self, layout: ProjectLayout, logical_name: str, 
                           file_extension: str = "") -> str:
        """Resolve a logical component name to actual file path"""
        
        # Direct routing rule match
        if logical_name in layout.routing_rules:
            base_path = layout.routing_rules[logical_name]
            return f"{base_path}/{self._generate_filename(logical_name, file_extension)}"
        
        # Fallback resolution based on architecture
        if layout.architecture == ArchitectureType.FRONTEND_BACKEND:
            if 'frontend' in logical_name.lower():
                return f"frontend/src/{self._generate_filename(logical_name, file_extension)}" 
            elif 'backend' in logical_name.lower():
                return f"backend/app/{self._generate_filename(logical_name, file_extension)}"
        
        # Default to root level
        return self._generate_filename(logical_name, file_extension)
    
    def _generate_filename(self, logical_name: str, extension: str) -> str:
        """Generate appropriate filename from logical name"""
        if extension:
            return f"{logical_name}{extension}"
        
        # Guess extension based on logical name
        if 'test' in logical_name.lower():
            return f"test_{logical_name.lower()}.py"
        elif 'component' in logical_name.lower():
            return f"{logical_name}.jsx"
        else:
            return f"{logical_name}.py"

# Global analyzer instance
project_analyzer = ProjectLayoutAnalyzer()
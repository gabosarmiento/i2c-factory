"""
File Path Resolver - Intelligently resolves LLM-generated file paths
to actual project paths using semantic project layout analysis.
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
import re
from dataclasses import dataclass

from .project_layout_analyzer import ProjectLayoutAnalyzer, ProjectLayout, ComponentType, ArchitectureType

@dataclass
class ResolvedPath:
    """Result of path resolution"""
    original_path: str
    resolved_path: str
    component_type: Optional[ComponentType]
    is_valid: bool
    conflicts: List[str]
    suggestions: List[str]

class FilePathResolver:
    """Resolves logical/ambiguous file paths to actual project structure"""
    
    def __init__(self, project_path: Path):
        self.project_path = project_path
        self.analyzer = ProjectLayoutAnalyzer()
        self.layout: Optional[ProjectLayout] = None
        self._refresh_layout()
        
    def _refresh_layout(self):
        """Refresh project layout analysis"""
        self.layout = self.analyzer.analyze(self.project_path)
    
    def resolve_code_map(self, code_map: Dict[str, str]) -> Dict[str, str]:
        """Resolve all paths in a code map to valid project paths"""
        resolved_map = {}
        conflicts = self._detect_conflicts(code_map)
        
        for original_path, content in code_map.items():
            resolved = self.resolve_path(original_path, content, conflicts)
            
            if resolved.is_valid:
                resolved_map[resolved.resolved_path] = content
            else:
                # Handle invalid paths gracefully
                fallback_path = self._create_fallback_path(original_path, content)
                resolved_map[fallback_path] = content
                print(f"⚠️ Path resolution failed for '{original_path}', using fallback: '{fallback_path}'")
        
        return resolved_map
    
    def resolve_path(self, path: str, content: str = "", conflicts: List[str] = None) -> ResolvedPath:
        """Resolve a single file path using project layout intelligence"""
        conflicts = conflicts or []
        
        # Handle obvious invalid paths first
        if self._is_invalid_path(path):
            return self._resolve_invalid_path(path, content)
        
        # Path is already valid - check for conflicts
        if self._is_valid_file_path(path):
            return ResolvedPath(
                original_path=path,
                resolved_path=path,
                component_type=self._detect_component_type(path),
                is_valid=True,
                conflicts=[],
                suggestions=[]
            )
        
        # Resolve using layout intelligence
        return self._intelligent_resolve(path, content, conflicts)
    
    def _detect_conflicts(self, code_map: Dict[str, str]) -> List[str]:
        """Detect conflicting paths in code map"""
        conflicts = []
        paths = list(code_map.keys())
        
        for i, path1 in enumerate(paths):
            for path2 in paths[i+1:]:
                if self._paths_conflict(path1, path2):
                    conflicts.append(f"{path1} conflicts with {path2}")
        
        return conflicts
    
    def _paths_conflict(self, path1: str, path2: str) -> bool:
        """Check if two paths would conflict (file vs directory)"""
        # Path1 is a prefix of path2 (file vs directory conflict)
        if path2.startswith(path1 + "/"):
            return True
        if path1.startswith(path2 + "/"):
            return True
        return False
    
    def _is_invalid_path(self, path: str) -> bool:
        """Check if path is obviously invalid (no extension, conflicts with directories)"""
        # No extension and no slash = likely invalid top-level name
        if "/" not in path and "." not in path:
            # Check if it's a known component name without proper structure
            component_names = ['frontend', 'backend', 'api', 'client', 'server', 'app', 'web']
            return any(name in path.lower() for name in component_names)
        
        return False
    
    def _is_valid_file_path(self, path: str) -> bool:
        """Check if path looks like a valid file path"""
        # Has extension or is clearly a file
        if "." in Path(path).name:
            return True
        
        # Special cases for valid files without extensions
        special_files = ['Dockerfile', 'Makefile', 'README', 'LICENSE']
        return Path(path).name in special_files
    
    def _resolve_invalid_path(self, path: str, content: str) -> ResolvedPath:
        """Resolve obviously invalid paths using content analysis"""
        # Analyze content to determine file type
        file_type = self._analyze_content_type(content)
        component_type = self._infer_component_from_content(content)
        
        # Generate proper path based on layout and content
        resolved_path = self._generate_proper_path(path, file_type, component_type)
        
        return ResolvedPath(
            original_path=path,
            resolved_path=resolved_path,
            component_type=component_type,
            is_valid=True,
            conflicts=[],
            suggestions=[]
        )
    
    def _intelligent_resolve(self, path: str, content: str, conflicts: List[str]) -> ResolvedPath:
        """Use layout intelligence to resolve ambiguous paths with fullstack awareness"""
        
        # Extract logical component from path
        logical_component = self._extract_logical_component(path)
        
        # Determine target component type and file extension
        component_type = self._infer_component_from_content(content)
        file_type = self._analyze_content_type(content)
        
        # FULLSTACK WEB APP SPECIAL HANDLING
        if logical_component == "frontend" or component_type == ComponentType.FRONTEND:
            return self._resolve_frontend_structure(path, content, file_type)
        
        elif logical_component == "backend" or component_type == ComponentType.BACKEND:
            return self._resolve_backend_structure(path, content, file_type)
        
        # Use layout routing rules (existing logic)
        if self.layout and logical_component in self.layout.routing_rules:
            base_path = self.layout.routing_rules[logical_component]
            filename = self._generate_filename_from_path(path, file_type)
            resolved_path = f"{base_path}/{filename}"
        else:
            # Fallback to architecture-based resolution
            resolved_path = self._resolve_by_architecture(path, content, component_type)
        
        return ResolvedPath(
            original_path=path,
            resolved_path=resolved_path,
            component_type=component_type,
            is_valid=True,
            conflicts=[],
            suggestions=[]
        )

    def _resolve_frontend_structure(self, path: str, content: str, file_type: str) -> ResolvedPath:
        """Resolve frontend files to proper React structure"""
        
        # Detect specific frontend file types
        content_lower = content.lower()
        
        # Main App component
        if "function app" in content_lower or "const app" in content_lower or path.lower() == "frontend":
            resolved_path = f"frontend/src/App{file_type}"
        
        # Component files (detect component names from content)
        elif "component" in content_lower or any(comp in content_lower for comp in ["editor", "selector", "toggle", "preview"]):
            # Extract component name from content or path
            component_name = self._extract_component_name(content, path)
            resolved_path = f"frontend/src/components/{component_name}{file_type}"
        
        # CSS files
        elif file_type == ".css" or "css" in path.lower():
            if "index" in path.lower() or "main" in path.lower():
                resolved_path = "frontend/src/index.css"
            else:
                css_name = self._extract_file_name(path)
                resolved_path = f"frontend/src/{css_name}.css"
        
        # Config files (vite, webpack, etc.)
        elif any(config in content_lower for config in ["vite", "webpack", "config"]):
            config_name = self._extract_file_name(path)
            resolved_path = f"frontend/{config_name}{file_type}"
        
        # Main entry file
        elif "main" in path.lower() or "index" in path.lower():
            resolved_path = f"frontend/src/main{file_type}"
        
        # Default frontend file
        else:
            filename = self._extract_file_name(path)
            resolved_path = f"frontend/src/{filename}{file_type}"
        
        return ResolvedPath(
            original_path=path,
            resolved_path=resolved_path,
            component_type=ComponentType.FRONTEND,
            is_valid=True,
            conflicts=[],
            suggestions=[]
        )

    def _resolve_backend_structure(self, path: str, content: str, file_type: str) -> ResolvedPath:
        """Resolve backend files to proper API structure"""
        
        content_lower = content.lower()
        
        # Main FastAPI app
        if ("fastapi" in content_lower or "app = " in content_lower) and "main" in path.lower():
            resolved_path = f"backend/main{file_type}"
        
        # API routes
        elif "router" in content_lower or "@app." in content_lower or "route" in path.lower():
            route_name = self._extract_file_name(path)
            resolved_path = f"backend/api/{route_name}{file_type}"
        
        # Models/Schemas  
        elif "model" in content_lower or "schema" in content_lower or "pydantic" in content_lower:
            model_name = self._extract_file_name(path)
            resolved_path = f"backend/models/{model_name}{file_type}"
        
        # Services/Business Logic
        elif "service" in content_lower or "business" in path.lower():
            service_name = self._extract_file_name(path)
            resolved_path = f"backend/services/{service_name}{file_type}"
        
        # Database/Repository
        elif "database" in content_lower or "repository" in content_lower or "db" in path.lower():
            db_name = self._extract_file_name(path)
            resolved_path = f"backend/db/{db_name}{file_type}"
        
        # Default backend file
        else:
            filename = self._extract_file_name(path)
            resolved_path = f"backend/{filename}{file_type}"
        
        return ResolvedPath(
            original_path=path,
            resolved_path=resolved_path,
            component_type=ComponentType.BACKEND,
            is_valid=True,
            conflicts=[],
            suggestions=[]
        )

    def _extract_component_name(self, content: str, path: str) -> str:
        """Extract React component name from content or path"""
        
        # SAFETY: Skip if content has markdown artifacts
        if '```' in content:
            content = self._extract_code_from_markdown(content)
        
        # Try to find component name in content
        import re
        
        # Look for component declarations
        patterns = [
            r'(?:const|function)\s+(\w+)\s*[=\(].*?(?:React\.Component|=>)',
            r'class\s+(\w+)\s+extends',
            r'export\s+(?:default\s+)?(?:const|function)\s+(\w+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1)
        
        # Fallback to path-based naming
        if "editor" in path.lower():
            return "CodeEditor"
        elif "selector" in path.lower():
            return "LanguageSelector" 
        elif "toggle" in path.lower():
            return "ThemeToggle"
        elif "preview" in path.lower():
            return "CodePreview"
        
        # Generic component name
        return "Component"

    def _extract_file_name(self, path: str) -> str:
        """Extract clean file name from path"""
        if "/" in path:
            name = path.split("/")[-1]
        else:
            name = path
        
        # Remove extension if present
        if "." in name:
            name = name.split(".")[0]
        
        return name
    
    def _analyze_content_type(self, content: str) -> str:
        """Analyze content to determine file type/extension - IMPROVED ROBUSTNESS"""
        content_lower = content.lower().strip()
        
        # SAFETY CHECK: Skip if content contains markdown artifacts
        if content.strip().startswith('```') or '```' in content:
            # This indicates malformed content from LLM - extract actual code
            content = self._extract_code_from_markdown(content)
            content_lower = content.lower().strip()
        
        # React/JSX patterns (CHECK FIRST - most specific)
        if any(pattern in content for pattern in ['import React', 'export default', 'useState', 'jsx', 'tsx']):
            if 'typescript' in content or 'interface ' in content:
                return '.tsx'
            return '.jsx'
        
        # PURE CSS (must be very specific to avoid false positives)
        if self._is_pure_css_content(content_lower):
            return '.css'
        
        # JavaScript patterns
        if any(pattern in content for pattern in ['function', 'const ', 'let ', 'var ', 'export']):
            if 'typescript' in content or ': string' in content or 'interface ' in content:
                return '.ts'
            return '.js'
        
        # Python patterns
        if any(pattern in content for pattern in ['def ', 'import ', 'from ', 'class ', 'if __name__']):
            return '.py'
        
        # Test file patterns
        if any(pattern in content_lower for pattern in ['test', 'describe(', 'it(', 'assert', 'unittest']):
            if 'react' in content_lower or 'jsx' in content_lower:
                return '.test.jsx'
            elif 'javascript' in content_lower or 'js' in content_lower:
                return '.test.js'
            else:
                return '.py'  # Default test to Python
        
        # HTML
        if any(pattern in content for pattern in ['<html', '<div', '<body', '<!DOCTYPE']):
            return '.html'
        
        # Go
        if any(pattern in content for pattern in ['package ', 'func ', 'import "', 'var ']):
            return '.go'
        
        # Java
        if any(pattern in content for pattern in ['public class', 'private ', 'public static']):
            return '.java'
        
        # Default
        return '.py'

    def _is_pure_css_content(self, content_lower: str) -> bool:
        """Check if content is pure CSS (not JS/JSON with braces)"""
        # Must have CSS-specific patterns, not just braces
        css_indicators = ['color:', 'margin:', 'padding:', 'font-', 'background-', '@media', 'display:', 'position:']
        js_indicators = ['function', 'const ', 'let ', 'var ', 'import', 'export', 'return']
        
        has_css_patterns = any(indicator in content_lower for indicator in css_indicators)
        has_js_patterns = any(indicator in content_lower for indicator in js_indicators)
        
        # Only CSS if it has CSS patterns and NO JS patterns
        return has_css_patterns and not has_js_patterns

    def _extract_code_from_markdown(self, content: str) -> str:
        """Extract actual code from markdown code blocks"""
        lines = content.split('\n')
        code_lines = []
        in_code_block = False
        
        for line in lines:
            if line.strip().startswith('```'):
                in_code_block = not in_code_block
                continue
            if in_code_block:
                code_lines.append(line)
        
        return '\n'.join(code_lines) if code_lines else content
    
    def _infer_component_from_content(self, content: str) -> Optional[ComponentType]:
        """Infer component type from content analysis"""
        # SAFETY: Clean content first
        if '```' in content:
            content = self._extract_code_from_markdown(content)
            
        content_lower = content.lower()
        
        # Frontend indicators
        if any(pattern in content_lower for pattern in ['react', 'vue', 'angular', 'jsx', 'component']):
            return ComponentType.FRONTEND
        
        # Backend/API indicators
        if any(pattern in content_lower for pattern in ['flask', 'django', 'fastapi', 'express', 'router']):
            return ComponentType.BACKEND
        
        # API specific
        if any(pattern in content_lower for pattern in ['endpoint', 'route', '@app.', 'api']):
            return ComponentType.API
        
        # Database/Models
        if any(pattern in content_lower for pattern in ['model', 'database', 'db.', 'sqlalchemy']):
            return ComponentType.DATABASE
        
        # Tests
        if any(pattern in content_lower for pattern in ['test', 'spec', 'unittest', 'pytest']):
            return ComponentType.TESTS
        
        return None
    
    def _extract_logical_component(self, path: str) -> str:
        """Extract logical component name from path"""
        parts = path.split('/')
        
        # First part is usually the logical component
        if parts:
            return parts[0].lower()
        
        return path.lower()
    
    def _generate_proper_path(self, original_path: str, file_type: str, 
                            component_type: Optional[ComponentType]) -> str:
        """Generate proper file path based on layout and component type"""
        
        if not self.layout or not component_type:
            # Fallback to simple resolution
            return f"{original_path}{file_type}"
        
        # Use component mapping
        if component_type in self.layout.components:
            component = self.layout.components[component_type]
            base_path = component.path
            
            # Generate appropriate filename
            if component_type == ComponentType.FRONTEND:
                if file_type in ['.jsx', '.tsx']:
                    filename = f"App{file_type}"
                else:
                    filename = f"{original_path}{file_type}"
                return f"{base_path}/src/{filename}"
            
            elif component_type == ComponentType.BACKEND:
                if file_type == '.py':
                    filename = f"{original_path}.py" if not original_path.endswith('.py') else original_path
                else:
                    filename = f"{original_path}{file_type}"
                return f"{base_path}/app/{filename}"
            
            else:
                filename = f"{original_path}{file_type}"
                return f"{base_path}/{filename}"
        
        # Architecture-based fallback
        return self._resolve_by_architecture(original_path, "", component_type)
    
    def _resolve_by_architecture(self, path: str, content: str, 
                               component_type: Optional[ComponentType]) -> str:
        """Resolve path based on detected architecture pattern"""
        
        if not self.layout:
            return path
        
        arch = self.layout.architecture
        file_type = self._analyze_content_type(content) if content else self._guess_extension(path)
        
        if arch == ArchitectureType.FRONTEND_BACKEND:
            if component_type == ComponentType.FRONTEND:
                return f"frontend/src/{path}{file_type}"
            elif component_type == ComponentType.BACKEND:
                return f"backend/app/{path}{file_type}"
                
        elif arch == ArchitectureType.MICROSERVICES:
            if component_type == ComponentType.API:
                return f"services/{path}-service/{path}{file_type}"
                
        elif arch == ArchitectureType.CLEAN_ARCHITECTURE:
            if component_type == ComponentType.DATABASE:
                return f"infrastructure/{path}{file_type}"
            elif component_type == ComponentType.API:
                return f"application/{path}{file_type}"
        
        # Default resolution
        return f"{path}{file_type}"
    
    def _generate_filename_from_path(self, path: str, file_type: str) -> str:
        """Generate filename from path and file type"""
        if "/" in path:
            filename = path.split("/")[-1]
        else:
            filename = path
        
        if not filename.endswith(file_type):
            filename += file_type
        
        return filename
    
    def _guess_extension(self, path: str) -> str:
        """Guess file extension from path name"""
        path_lower = path.lower()
        
        if 'test' in path_lower:
            return '.py'
        elif 'component' in path_lower:
            return '.jsx'
        elif 'api' in path_lower or 'route' in path_lower:
            return '.py'
        else:
            return '.py'  # Default
    
    def _detect_component_type(self, path: str) -> Optional[ComponentType]:
        """Detect component type from path structure"""
        path_lower = path.lower()
        
        if any(comp in path_lower for comp in ['frontend', 'client', 'web']):
            return ComponentType.FRONTEND
        elif any(comp in path_lower for comp in ['backend', 'server', 'api']):
            return ComponentType.BACKEND
        elif 'test' in path_lower:
            return ComponentType.TESTS
        
        return None
    
    def _create_fallback_path(self, original_path: str, content: str) -> str:
        """Create fallback path when resolution fails"""
        file_type = self._analyze_content_type(content)
        
        # Simple fallback - add extension and put in root
        if "." not in original_path:
            return f"{original_path}{file_type}"
        
        return original_path

# Helper function for easy integration
def resolve_code_map_paths(code_map: Dict[str, str], project_path: Path) -> Dict[str, str]:
    """Convenience function to resolve code map paths"""
    resolver = FilePathResolver(project_path)
    return resolver.resolve_code_map(code_map)
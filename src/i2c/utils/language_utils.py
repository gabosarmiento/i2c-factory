# utils/language_utils.py
"""
Multi-language detection and API route extraction system
Supports Python, JavaScript/TypeScript, Java, Go, and more
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple
import re
import json

class LanguageDetector:
    """Detects programming languages and frameworks in a project"""
    
    LANGUAGE_PATTERNS = {
        'python': {
            'extensions': ['.py'],
            'frameworks': {
                'fastapi': ['FastAPI', 'from fastapi', '@app.get', '@app.post'],
                'flask': ['Flask', 'from flask', '@app.route'],
                'django': ['django', 'from django', 'class.*View', 'def get\\(', 'def post\\('],
                'starlette': ['Starlette', 'from starlette']
            }
        },
        'javascript': {
            'extensions': ['.js', '.mjs'],
            'frameworks': {
                'express': ['express', 'app.get', 'app.post', 'router.get', 'router.post'],
                'koa': ['koa', 'ctx.body', 'ctx.request'],
                'hapi': ['hapi', '@hapi', 'server.route'],
                'nestjs': ['@Controller', '@Get', '@Post', 'from @nestjs']
            }
        },
        'typescript': {
            'extensions': ['.ts'],
            'frameworks': {
                'express': ['express', 'app.get', 'app.post', 'router.get', 'router.post'],
                'nestjs': ['@Controller', '@Get', '@Post', 'from @nestjs'],
                'koa': ['koa', 'ctx.body', 'ctx.request']
            }
        },
        'java': {
            'extensions': ['.java'],
            'frameworks': {
                'spring': ['@RestController', '@GetMapping', '@PostMapping', '@RequestMapping', 'Spring'],
                'jersey': ['@Path', '@GET', '@POST', 'javax.ws.rs'],
                'micronaut': ['@Controller', '@Get', '@Post', 'io.micronaut']
            }
        },
        'go': {
            'extensions': ['.go'],
            'frameworks': {
                'gin': ['gin.Default', 'gin.Engine', 'c.JSON', 'router.GET', 'router.POST'],
                'echo': ['echo.New', 'e.GET', 'e.POST', 'labstack/echo'],
                'mux': ['mux.NewRouter', 'r.HandleFunc', 'gorilla/mux'],
                'fiber': ['fiber.New', 'app.Get', 'app.Post', 'gofiber/fiber']
            }
        },
        'csharp': {
            'extensions': ['.cs'],
            'frameworks': {
                'aspnet': ['[ApiController]', '[HttpGet]', '[HttpPost]', 'ControllerBase'],
                'minimal': ['app.MapGet', 'app.MapPost', 'WebApplication']
            }
        },
        'rust': {
            'extensions': ['.rs'],
            'frameworks': {
                'actix': ['actix_web', 'HttpResponse', 'web::get', 'web::post'],
                'rocket': ['rocket', '#[get]', '#[post]', 'routes!'],
                'warp': ['warp', 'warp::Filter']
            }
        }
    }
    
    def detect_project_languages(self, project_path: Path) -> Dict[str, Dict]:
        """Detect all languages and frameworks used in a project"""
        detected = {}
        
        for lang, config in self.LANGUAGE_PATTERNS.items():
            lang_info = self._detect_language(project_path, lang, config)
            if lang_info['files_found'] > 0:
                detected[lang] = lang_info
        
        return detected
    
    def _detect_language(self, project_path: Path, language: str, config: Dict) -> Dict:
        """Detect specific language usage in project"""
        extensions = config['extensions']
        frameworks = config['frameworks']
        
        # Find files with matching extensions
        files = []
        for ext in extensions:
            files.extend(project_path.glob(f"**/*{ext}"))
        
        if not files:
            return {'files_found': 0, 'frameworks': [], 'files': []}
        
        # Analyze files for framework patterns
        detected_frameworks = []
        framework_confidence = {}
        
        for file_path in files:
            try:
                content = file_path.read_text(encoding='utf-8')
                
                for framework, patterns in frameworks.items():
                    confidence = 0
                    for pattern in patterns:
                        matches = len(re.findall(pattern, content, re.IGNORECASE))
                        confidence += matches
                    
                    if confidence > 0:
                        framework_confidence[framework] = framework_confidence.get(framework, 0) + confidence
            
            except Exception as e:
                continue
        
        # Select frameworks above threshold
        for framework, confidence in framework_confidence.items():
            if confidence >= 2:  # Minimum confidence threshold
                detected_frameworks.append({
                    'name': framework,
                    'confidence': confidence,
                    'language': language
                })
        
        return {
            'files_found': len(files),
            'frameworks': detected_frameworks,
            'files': [str(f.relative_to(project_path)) for f in files[:10]]  # Limit for readability
        }
    
    def get_primary_backend_language(self, project_path: Path) -> Tuple[Optional[str], Optional[str]]:
        """Get the primary backend language and framework"""
        detected = self.detect_project_languages(project_path)
        
        # Priority order for backend languages
        backend_priority = ['python', 'java', 'javascript', 'typescript', 'go', 'csharp', 'rust']
        
        for lang in backend_priority:
            if lang in detected and detected[lang]['frameworks']:
                primary_framework = max(detected[lang]['frameworks'], key=lambda x: x['confidence'])
                return lang, primary_framework['name']
        
        # Fallback: return language with most files
        if detected:
            primary_lang = max(detected.items(), key=lambda x: x[1]['files_found'])
            frameworks = primary_lang[1]['frameworks']
            framework = frameworks[0]['name'] if frameworks else None
            return primary_lang[0], framework
        
        return None, None

class MultiLanguageAPIExtractor:
    """Extract API routes from multiple programming languages"""
    
    def __init__(self):
        self.extractors = {
            'python': PythonAPIExtractor(),
            'javascript': JavaScriptAPIExtractor(),
            'typescript': TypeScriptAPIExtractor(),
            'java': JavaAPIExtractor(),
            'go': GoAPIExtractor(),
            'csharp': CSharpAPIExtractor(),
            'rust': RustAPIExtractor()
        }
    
    def extract_routes(self, project_path: Path, language: str, framework: str) -> Dict[str, List[Dict]]:
        """Extract API routes based on detected language and framework"""
        
        extractor = self.extractors.get(language)
        if not extractor:
            print(f"[WARNING] No API extractor available for {language}")
            return {}
        
        return extractor.extract_routes(project_path, framework)

class PythonAPIExtractor:
    """Extract API routes from Python frameworks"""
    
    def extract_routes(self, project_path: Path, framework: str) -> Dict[str, List[Dict]]:
        if framework == 'fastapi':
            return self._extract_fastapi_routes(project_path)
        elif framework == 'flask':
            return self._extract_flask_routes(project_path)
        elif framework == 'django':
            return self._extract_django_routes(project_path)
        return {}
    
    def _extract_fastapi_routes(self, project_path: Path) -> Dict[str, List[Dict]]:
        """Extract FastAPI routes"""
        routes = {method: [] for method in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']}
        
        patterns = {
            'GET': [r'@app\.get\(["\']([^"\']+)["\']', r'@router\.get\(["\']([^"\']+)["\']'],
            'POST': [r'@app\.post\(["\']([^"\']+)["\']', r'@router\.post\(["\']([^"\']+)["\']'],
            'PUT': [r'@app\.put\(["\']([^"\']+)["\']', r'@router\.put\(["\']([^"\']+)["\']'],
            'DELETE': [r'@app\.delete\(["\']([^"\']+)["\']', r'@router\.delete\(["\']([^"\']+)["\']'],
            'PATCH': [r'@app\.patch\(["\']([^"\']+)["\']', r'@router\.patch\(["\']([^"\']+)["\']']
        }
        
        for py_file in project_path.glob("**/*.py"):
            try:
                content = py_file.read_text(encoding='utf-8')
                for method, method_patterns in patterns.items():
                    for pattern in method_patterns:
                        matches = re.finditer(pattern, content, re.MULTILINE)
                        for match in matches:
                            routes[method].append({
                                'path': match.group(1),
                                'method': method,
                                'file': str(py_file.relative_to(project_path)),
                                'framework': 'fastapi'
                            })
            except:
                continue
        
        return routes
    
    def _extract_flask_routes(self, project_path: Path) -> Dict[str, List[Dict]]:
        """Extract Flask routes"""
        routes = {method: [] for method in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']}
        
        # Flask route pattern: @app.route('/path', methods=['GET', 'POST'])
        pattern = r'@app\.route\(["\']([^"\']+)["\'](?:,\s*methods\s*=\s*\[([^\]]+)\])?'
        
        for py_file in project_path.glob("**/*.py"):
            try:
                content = py_file.read_text(encoding='utf-8')
                matches = re.finditer(pattern, content, re.MULTILINE)
                for match in matches:
                    path = match.group(1)
                    methods_str = match.group(2)
                    
                    if methods_str:
                        # Parse methods list
                        methods = re.findall(r'["\']([^"\']+)["\']', methods_str)
                    else:
                        methods = ['GET']  # Default Flask method
                    
                    for method in methods:
                        if method in routes:
                            routes[method].append({
                                'path': path,
                                'method': method,
                                'file': str(py_file.relative_to(project_path)),
                                'framework': 'flask'
                            })
            except:
                continue
        
        return routes
    
    def _extract_django_routes(self, project_path: Path) -> Dict[str, List[Dict]]:
        """Extract Django routes (simplified)"""
        routes = {method: [] for method in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']}
        
        # Look for url patterns in urls.py files
        for urls_file in project_path.glob("**/urls.py"):
            try:
                content = urls_file.read_text(encoding='utf-8')
                
                # Django URL pattern: path('admin/', admin.site.urls)
                url_patterns = re.findall(r'path\(["\']([^"\']+)["\']', content)
                
                for pattern in url_patterns:
                    # Django defaults to all methods unless restricted
                    for method in ['GET', 'POST', 'PUT', 'DELETE']:
                        routes[method].append({
                            'path': pattern,
                            'method': method,
                            'file': str(urls_file.relative_to(project_path)),
                            'framework': 'django'
                        })
            except:
                continue
        
        return routes

class JavaScriptAPIExtractor:
    """Extract API routes from JavaScript frameworks"""
    
    def extract_routes(self, project_path: Path, framework: str) -> Dict[str, List[Dict]]:
        if framework == 'express':
            return self._extract_express_routes(project_path)
        elif framework == 'nestjs':
            return self._extract_nestjs_routes(project_path)
        return {}
    
    def _extract_express_routes(self, project_path: Path) -> Dict[str, List[Dict]]:
        """Extract Express.js routes"""
        routes = {method: [] for method in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']}
        
        patterns = {
            'GET': [r'app\.get\(["\']([^"\']+)["\']', r'router\.get\(["\']([^"\']+)["\']'],
            'POST': [r'app\.post\(["\']([^"\']+)["\']', r'router\.post\(["\']([^"\']+)["\']'],
            'PUT': [r'app\.put\(["\']([^"\']+)["\']', r'router\.put\(["\']([^"\']+)["\']'],
            'DELETE': [r'app\.delete\(["\']([^"\']+)["\']', r'router\.delete\(["\']([^"\']+)["\']'],
            'PATCH': [r'app\.patch\(["\']([^"\']+)["\']', r'router\.patch\(["\']([^"\']+)["\']']
        }
        
        for js_file in project_path.glob("**/*.js"):
            try:
                content = js_file.read_text(encoding='utf-8')
                for method, method_patterns in patterns.items():
                    for pattern in method_patterns:
                        matches = re.finditer(pattern, content, re.MULTILINE)
                        for match in matches:
                            routes[method].append({
                                'path': match.group(1),
                                'method': method,
                                'file': str(js_file.relative_to(project_path)),
                                'framework': 'express'
                            })
            except:
                continue
        
        return routes
    
    def _extract_nestjs_routes(self, project_path: Path) -> Dict[str, List[Dict]]:
        """Extract NestJS routes"""
        routes = {method: [] for method in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']}
        
        # NestJS uses decorators: @Get('path'), @Post('path')
        patterns = {
            'GET': r'@Get\(["\']([^"\']+)["\']\)',
            'POST': r'@Post\(["\']([^"\']+)["\']\)',
            'PUT': r'@Put\(["\']([^"\']+)["\']\)',
            'DELETE': r'@Delete\(["\']([^"\']+)["\']\)',
            'PATCH': r'@Patch\(["\']([^"\']+)["\']\)'
        }
        
        for ts_file in project_path.glob("**/*.ts"):
            try:
                content = ts_file.read_text(encoding='utf-8')
                for method, pattern in patterns.items():
                    matches = re.finditer(pattern, content, re.MULTILINE)
                    for match in matches:
                        routes[method].append({
                            'path': match.group(1),
                            'method': method,
                            'file': str(ts_file.relative_to(project_path)),
                            'framework': 'nestjs'
                        })
            except:
                continue
        
        return routes

class TypeScriptAPIExtractor(JavaScriptAPIExtractor):
    """TypeScript API extractor (inherits from JavaScript)"""
    
    def extract_routes(self, project_path: Path, framework: str) -> Dict[str, List[Dict]]:
        # TypeScript uses similar patterns to JavaScript
        routes = super().extract_routes(project_path, framework)
        
        # Also check .ts files for TypeScript-specific patterns
        for ts_file in project_path.glob("**/*.ts"):
            # Add TypeScript-specific extraction logic here if needed
            pass
        
        return routes

# Placeholder extractors for other languages
class JavaAPIExtractor:
    def extract_routes(self, project_path: Path, framework: str) -> Dict[str, List[Dict]]:
        # TODO: Implement Java/Spring extraction
        return {}

class GoAPIExtractor:
    def extract_routes(self, project_path: Path, framework: str) -> Dict[str, List[Dict]]:
        # TODO: Implement Go extraction
        return {}

class CSharpAPIExtractor:
    def extract_routes(self, project_path: Path, framework: str) -> Dict[str, List[Dict]]:
        # TODO: Implement C#/ASP.NET extraction
        return {}

class RustAPIExtractor:
    def extract_routes(self, project_path: Path, framework: str) -> Dict[str, List[Dict]]:
        # TODO: Implement Rust extraction
        return {}
# /agents/sre_team/dependency.py
# Enhanced Agent for checking dependencies with container-aware security scanning.

import subprocess
import json
import ast
import time
from pathlib import Path
from typing import Dict, List, Any, Tuple
# Import CLI for logging and user input
try:
    from i2c.cli.controller import canvas
except ImportError:
    class FallbackCanvas:
        def warning(self, msg): print(f"[WARN_SANDBOX] {msg}")
        def error(self, msg): print(f"[ERROR_SANDBOX] {msg}")
        def info(self, msg): print(f"[INFO_SANDBOX] {msg}")
        def success(self, msg): print(f"[SUCCESS_SANDBOX] {msg}")
    canvas = FallbackCanvas()

# Helper functions for dependency detection
PYTHON_IMPORT_MAP = {
    "fastapi": "fastapi",
    "flask": "flask",
    "sqlalchemy": "sqlalchemy",
    "pydantic": "pydantic",
    "requests": "requests",
    "django": "django",
    "pandas": "pandas",
    "numpy": "numpy",
}

NODE_IMPORT_MAP = {
    "react": "react",
    "next": "next",
    "express": "express",
    "axios": "axios",
    "lodash": "lodash",
    "vue": "vue",
    "angular": "@angular/core",
}

def _detect_py_deps(root: Path) -> List[str]:
    """Detect Python dependencies from import analysis"""
    req: set[str] = set()
    for py in root.rglob("*.py"):
        try:
            content = py.read_text(encoding='utf-8')
            tree = ast.parse(content)
            for node in ast.walk(tree):
                mod = None
                if isinstance(node, ast.Import):
                    mod = node.names[0].name.split(".")[0]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    mod = node.module.split(".")[0]
                if mod and mod.lower() in PYTHON_IMPORT_MAP:
                    req.add(PYTHON_IMPORT_MAP[mod.lower()])
        except:
            continue
    return sorted(req)

def _detect_node_deps(root: Path) -> Dict[str, str]:
    """Detect Node.js dependencies from import analysis"""
    deps: Dict[str, str] = {}
    for js_file in root.rglob("*.js"):
        try:
            content = js_file.read_text(encoding='utf-8')
            for line in content.splitlines():
                if "require(" in line or "from" in line:
                    for key in NODE_IMPORT_MAP:
                        if key in line.lower():
                            deps[NODE_IMPORT_MAP[key]] = "latest"
        except:
            continue
    return deps

def _write_json(path: Path, obj) -> None:
    """Write JSON to file safely"""
    path.write_text(json.dumps(obj, indent=2) + "\n", encoding='utf-8')

class DependencyVerifierAgent:
    """
    Enhanced dependency checker with container-aware security scanning:
    - Checks dependencies in requirements.txt for vulnerabilities using pip-audit
    - Supports container-based scanning for production-like environments
    - Multi-language support (Python, Node.js, Go, Java)
    - Generates dependency manifests based on architectural intelligence
    """
    
    def __init__(self, project_path=None, session_state=None, **kwargs):
        self.project_path = Path(project_path) if project_path else Path(".")
        self.session_state = session_state or {}
        self.name = "DependencyVerifier"
        # DEBUG: Check if dependency agent gets knowledge_base
        canvas.info(f"🔍 DEBUG: DependencyVerifierAgent init")
        if session_state:
            canvas.info(f"🔍 DEBUG: DependencyVerifier session_state keys: {list(session_state.keys())}")
            if 'knowledge_base' in session_state:
                canvas.success("✅ DEBUG: DependencyVerifier received knowledge_base")
            else:
                canvas.error("❌ DEBUG: DependencyVerifier missing knowledge_base")
        

        print("📦 [DependencyVerifierAgent] Initialized (Container-Enhanced Mode).")
        self.docker_available = self._check_docker_availability()
        self.audit_tools = self._check_audit_tools()
    
    async def run(self) -> Dict[str, Any]:
        """
        AGNO-compatible async run method for SRE team integration.
        Runs dependency security scanning.
        """
        try:
            # Run dependency security check
            issues = self.check_dependencies(self.project_path)
            
            return {
                "passed": len(issues) == 0,
                "issues": issues,
                "container_based": self.docker_available and self._has_docker_configuration(self.project_path),
                "audit_tools_available": self.audit_tools
            }
        except Exception as e:
            return {
                "passed": False,
                "issues": [f"Dependency check failed: {str(e)}"],
                "container_based": False,
                "audit_tools_available": {}
            }
        
    def _check_docker_availability(self) -> bool:
        """Check if Docker is available for container-based scanning"""
        try:
            result = subprocess.run(['docker', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                result = subprocess.run(['docker', 'info'], 
                                      capture_output=True, text=True, timeout=10)
                return result.returncode == 0
        except:
            return False
        return False

    def _check_audit_tools(self) -> Dict[str, bool]:
        """Check availability of security audit tools"""
        tools = {}
        
        # Check pip-audit for Python
        try:
            subprocess.run(['pip-audit', '--version'], capture_output=True, check=True, text=True)
            tools['pip-audit'] = True
            print("   ✅ pip-audit found for Python security scanning.")
        except:
            tools['pip-audit'] = False
            print("   ⚠️ pip-audit not found. Install with: pip install pip-audit")

        # Check npm audit for Node.js
        try:
            subprocess.run(['npm', 'audit', '--version'], capture_output=True, check=True, text=True)
            tools['npm-audit'] = True
            print("   ✅ npm audit found for Node.js security scanning.")
        except:
            tools['npm-audit'] = False
            print("   ⚠️ npm not found for Node.js security scanning.")

        return tools

    def generate_requirements_manifest(self, project_path: Path, architectural_context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate dependency manifests based on architectural intelligence"""
        
        system_type = architectural_context.get("system_type", "unknown")
        modules = architectural_context.get("modules", {})
        
        manifests_created = []
        
        # Generate backend requirements
        if "backend" in modules or system_type == "fullstack_web_app":
            backend_deps = self._detect_backend_dependencies(project_path)
            backend_requirements = self._generate_backend_requirements(backend_deps, system_type)
            
            backend_path = project_path / "backend" / "requirements.txt"
            if not backend_path.exists():
                backend_path.parent.mkdir(parents=True, exist_ok=True)
                backend_path.write_text(backend_requirements, encoding='utf-8')
                manifests_created.append("backend/requirements.txt")
        
        # Generate frontend package.json
        if "frontend" in modules or system_type == "fullstack_web_app":
            frontend_deps = self._detect_frontend_dependencies(project_path)
            package_json = self._generate_package_json(frontend_deps, system_type)
            
            frontend_path = project_path / "frontend" / "package.json"
            if not frontend_path.exists():
                frontend_path.parent.mkdir(parents=True, exist_ok=True)
                frontend_path.write_text(package_json, encoding='utf-8')
                manifests_created.append("frontend/package.json")
        
        return {
            "manifests_created": manifests_created,
            "backend_dependencies": backend_deps if 'backend_deps' in locals() else [],
            "frontend_dependencies": frontend_deps if 'frontend_deps' in locals() else []
        }

    def _detect_backend_dependencies(self, project_path: Path) -> List[str]:
        """Detect Python dependencies from code analysis"""
        dependencies = set()
        
        # Scan Python files for imports
        for py_file in project_path.rglob("*.py"):
            try:
                content = py_file.read_text(encoding='utf-8')
                # Common framework detection
                if "fastapi" in content.lower() or "from fastapi" in content:
                    dependencies.update(["fastapi", "uvicorn[standard]", "python-multipart"])
                if "flask" in content.lower():
                    dependencies.update(["flask", "gunicorn"])
                if "pydantic" in content.lower():
                    dependencies.add("pydantic")
                if "sqlalchemy" in content.lower():
                    dependencies.update(["sqlalchemy", "alembic"])
                if "jwt" in content.lower() or "jose" in content.lower():
                    dependencies.add("python-jose[cryptography]")
                if "bcrypt" in content.lower():
                    dependencies.add("bcrypt")
                if "cors" in content.lower():
                    dependencies.add("fastapi-cors")
            except:
                continue
        
        return list(dependencies)

    def _detect_frontend_dependencies(self, project_path: Path) -> List[str]:
        """Detect Node.js dependencies from React code analysis"""
        dependencies = set()
        
        # Scan JSX/JS files for imports and usage
        for js_file in project_path.rglob("*.jsx") or project_path.rglob("*.js"):
            try:
                content = js_file.read_text(encoding='utf-8')
                if "import React" in content:
                    dependencies.update(["react", "react-dom"])
                if "useState" in content or "useEffect" in content:
                    dependencies.add("react")
                if "axios" in content:
                    dependencies.add("axios")
                if "react-router" in content:
                    dependencies.add("react-router-dom")
            except:
                continue
        
        return list(dependencies)

    def _generate_backend_requirements(self, dependencies: List[str], system_type: str) -> str:
        """Generate requirements.txt content with proper versions"""
        
        # Default versions for common packages (updated for security)
        version_map = {
            "fastapi": "0.109.1",  # Fixed PYSEC-2024-38
            "uvicorn[standard]": "0.24.0",
            "python-multipart": "0.0.18",  # Fixed GHSA-59g5-xgcq-4qw3 and GHSA-2jv5-9r88-3w3p
            "pydantic": "2.5.0",
            "sqlalchemy": "2.0.23",
            "python-jose[cryptography]": "3.3.0",
            "bcrypt": "4.1.2",
            "pytest": "7.4.3",
            "httpx": "0.25.2",
            "starlette": "0.40.0"  # Fixed GHSA-f96h-pmfr-66vw
        }
        
        # Always include testing dependencies
        if "pytest" not in dependencies:
            dependencies.append("pytest")
        if "httpx" not in dependencies:
            dependencies.append("httpx")
        
        requirements = []
        for dep in sorted(dependencies):
            version = version_map.get(dep, "")
            if version:
                requirements.append(f"{dep}=={version}")
            else:
                requirements.append(dep)
        
        return "\n".join(requirements) + "\n"

    def _generate_package_json(self, dependencies: List[str], system_type: str) -> str:
        """Generate package.json content"""
        
        # Default versions for React packages
        version_map = {
            "react": "^18.2.0",
            "react-dom": "^18.2.0",
            "axios": "^1.6.0",
            "react-router-dom": "^6.18.0",
            "@vitejs/plugin-react": "^4.1.0",
            "vite": "^4.5.0"
        }
        
        # Ensure basic React setup
        if not dependencies:
            dependencies = ["react", "react-dom"]
        
        # Always include build tools
        dev_dependencies = ["@vitejs/plugin-react", "vite"]
        
        package_json = {
            "name": "frontend",
            "version": "0.1.0",
            "type": "module",
            "scripts": {
                "dev": "vite",
                "build": "vite build",
                "preview": "vite preview",
                "test": "vitest",
                "audit": "npm audit --audit-level moderate"
            },
            "dependencies": {
                dep: version_map.get(dep, "^1.0.0") for dep in dependencies
            },
            "devDependencies": {
                dep: version_map.get(dep, "^1.0.0") for dep in dev_dependencies
            }
        }
        
        return json.dumps(package_json, indent=2) + "\n"

    def check_dependencies(self, project_path: Path) -> List[str]:
        """Enhanced dependency checking with container-aware scanning"""
        print("🤖 [DependencyVerifierAgent] Running enhanced dependency security scan...")
        
        issues_found = []
        
        # Check if we have Docker and should use container-based scanning
        has_docker_config = self._has_docker_configuration(project_path)
        
        if self.docker_available and has_docker_config:
            issues_found.extend(self._container_based_security_scan(project_path))
        else:
            print("   📋 Using local security scanning...")
            issues_found.extend(self._local_security_scan(project_path))
        
        if not issues_found:
            print("✅ [DependencyVerifierAgent] No dependency security issues detected.")
        else:
            print(f"⚠️ [DependencyVerifierAgent] Found {len(issues_found)} dependency issue(s).")
        
        return issues_found

    def _has_docker_configuration(self, project_path: Path) -> bool:
        """Check if project has Docker configuration"""
        docker_files = [
            project_path / "Dockerfile",
            project_path / "backend" / "Dockerfile",
            project_path / "frontend" / "Dockerfile",
            project_path / "docker-compose.yml"
        ]
        return any(f.exists() for f in docker_files)

    def _container_based_security_scan(self, project_path: Path) -> List[str]:
        """Run security scans inside Docker containers for production-like environment"""
        print("   🐳 Running container-based security scanning...")
        issues = []
        
        # Check for docker-compose setup
        compose_file = project_path / "docker-compose.yml"
        if compose_file.exists():
            issues.extend(self._scan_compose_services(project_path))
        else:
            # Scan individual Dockerfiles
            dockerfile_paths = [
                project_path / "backend" / "Dockerfile",
                project_path / "frontend" / "Dockerfile",
                project_path / "Dockerfile"
            ]
            
            for dockerfile in dockerfile_paths:
                if dockerfile.exists():
                    issues.extend(self._scan_dockerfile_dependencies(dockerfile))
        
        return issues

    def _scan_compose_services(self, project_path: Path) -> List[str]:
        """Scan dependencies for all services defined in docker-compose.yml."""
        issues: List[str] = []

        try:
            # 1️⃣ Build all images up-front so dependency scans run in a clean layer set
            print("   📦 Building containers for security scanning...")
            try:
                build_result = subprocess.run(
                    ["docker", "compose", "build", "--no-cache"],
                    cwd=project_path,
                    capture_output=True,
                    text=True,
                    timeout=300,          # 5 minutes
                )
            except FileNotFoundError:
                build_result = subprocess.run(
                    ["docker-compose", "build", "--no-cache"],
                    cwd=project_path,
                    capture_output=True,
                    text=True,
                    timeout=300,          # 5 minutes
                )

            if build_result.returncode != 0:
                issues.append(
                    f"Container build failed for security scan:\n{build_result.stderr}"
                )
                return issues

            # 2️⃣ Scan the backend (Python) service, if present
            if self._service_exists_in_compose(project_path, "backend"):
                issues.extend(
                    self._scan_service_dependencies(project_path, "backend", "python")
                )

            # 3️⃣ Scan the frontend (Node/JS) service, if present
            if self._service_exists_in_compose(project_path, "frontend"):
                issues.extend(
                    self._scan_service_dependencies(project_path, "frontend", "node")
                )

            # 4️⃣ Done – return everything we found
            return issues

        except subprocess.TimeoutExpired:
            issues.append("docker-compose build timed out after 5 minutes.")
        except FileNotFoundError:
            issues.append("docker-compose executable not found. Is Docker Compose installed and on PATH?")
        except Exception as exc:
            issues.append(f"Unexpected error while scanning compose services: {exc}")

        # Ensure the caller always gets a list back
        return issues

    def _service_exists_in_compose(self, project_path: Path, service_name: str) -> bool:
        """Check if a service is defined in docker-compose.yml"""
        try:
            compose_file = project_path / "docker-compose.yml"
            content = compose_file.read_text(encoding='utf-8')
            return f"{service_name}:" in content
        except:
            return False

    def _scan_service_dependencies(self, project_path: Path, service_name: str, language: str) -> List[str]:
        """Scan dependencies for a specific service inside container"""
        issues = []
        
        try:
            print(f"   🔍 Scanning {service_name} service dependencies ({language})...")
            
            if language == "python":
                # Run pip-audit inside the backend container with unique name
                container_name = f"audit-{service_name}-{int(time.time())}"
                try:
                    audit_result = subprocess.run([
                        'docker', 'compose', 'run', '--rm', '--name', container_name, service_name,
                        'pip-audit', '--format=json', '--exit-zero'
                    ], cwd=project_path, capture_output=True, text=True, timeout=120)
                except FileNotFoundError:
                    audit_result = subprocess.run([
                        'docker-compose', 'run', '--rm', '--name', container_name, service_name,
                        'pip-audit', '--format=json', '--exit-zero'
                    ], cwd=project_path, capture_output=True, text=True, timeout=120)
                
                if audit_result.returncode == 0 and audit_result.stdout:
                    try:
                        audit_data = json.loads(audit_result.stdout)
                        vulnerabilities = audit_data.get("vulnerabilities", [])
                        
                        for vuln in vulnerabilities:
                            pkg = vuln.get("name", "Unknown")
                            version = vuln.get("version", "?.?.?")
                            vuln_id = vuln.get("id", "NO_ID")
                            description = vuln.get("description", "No description").split('\n')[0]
                            issues.append(f"{service_name}: {pkg} ({version}) - {vuln_id}: {description}")
                            
                    except json.JSONDecodeError:
                        issues.append(f"{service_name}: pip-audit output parsing failed")
                else:
                    issues.append(f"{service_name}: pip-audit scan failed")
                    
            elif language == "node":
                # Run npm audit inside the frontend container with unique name
                container_name = f"audit-{service_name}-{int(time.time())}"
                try:
                    audit_result = subprocess.run([
                        'docker', 'compose', 'run', '--rm', '--name', container_name, service_name,
                        'npm', 'audit', '--json'
                    ], cwd=project_path, capture_output=True, text=True, timeout=120)
                except FileNotFoundError:
                    audit_result = subprocess.run([
                        'docker-compose', 'run', '--rm', '--name', container_name, service_name,
                        'npm', 'audit', '--json'
                    ], cwd=project_path, capture_output=True, text=True, timeout=120)
                
                if audit_result.stdout:
                    try:
                        audit_data = json.loads(audit_result.stdout)
                        advisories = audit_data.get("advisories", {})
                        
                        for advisory_id, advisory in advisories.items():
                            title = advisory.get("title", "Unknown vulnerability")
                            severity = advisory.get("severity", "unknown")
                            module_name = advisory.get("module_name", "unknown")
                            issues.append(f"{service_name}: {module_name} - {severity}: {title}")
                            
                    except json.JSONDecodeError:
                        issues.append(f"{service_name}: npm audit output parsing failed")
                        
        except subprocess.TimeoutExpired:
            issues.append(f"{service_name}: Security scan timed out")
        except Exception as e:
            issues.append(f"{service_name}: Security scan error - {str(e)}")
            
        return issues

    def _scan_dockerfile_dependencies(self, dockerfile: Path) -> List[str]:
        """Scan dependencies defined in a Dockerfile"""
        issues = []
        
        try:
            # Build temporary image for scanning
            import time
            image_name = f"security-scan-{int(time.time())}"
            
            build_result = subprocess.run([
                'docker', 'build', '-t', image_name, '-f', str(dockerfile), '.'
            ], cwd=dockerfile.parent, capture_output=True, text=True, timeout=300)
            
            if build_result.returncode != 0:
                issues.append(f"Failed to build image from {dockerfile.name}: {build_result.stderr}")
                return issues
            
            # Determine scan command based on dockerfile content
            dockerfile_content = dockerfile.read_text(encoding='utf-8').lower()
            
            if 'python' in dockerfile_content or 'pip' in dockerfile_content:
                # Python container - run pip-audit
                scan_result = subprocess.run([
                    'docker', 'run', '--rm', image_name,
                    'pip-audit', '--format=json', '--exit-zero'
                ], capture_output=True, text=True, timeout=120)
                
                if scan_result.stdout:
                    try:
                        audit_data = json.loads(scan_result.stdout)
                        vulnerabilities = audit_data.get("vulnerabilities", [])
                        
                        for vuln in vulnerabilities:
                            pkg = vuln.get("name", "Unknown")
                            version = vuln.get("version", "?.?.?")
                            vuln_id = vuln.get("id", "NO_ID")
                            description = vuln.get("description", "No description").split('\n')[0]
                            issues.append(f"Container ({dockerfile.name}): {pkg} ({version}) - {vuln_id}: {description}")
                            
                    except json.JSONDecodeError:
                        issues.append(f"Container ({dockerfile.name}): pip-audit output parsing failed")
            
            elif 'node' in dockerfile_content or 'npm' in dockerfile_content:
                # Node container - run npm audit
                scan_result = subprocess.run([
                    'docker', 'run', '--rm', image_name,
                    'npm', 'audit', '--json'
                ], cwd=dockerfile.parent, capture_output=True, text=True, timeout=120)
                
                if scan_result.stdout:
                    try:
                        audit_data = json.loads(scan_result.stdout)
                        advisories = audit_data.get("advisories", {})
                        
                        for advisory_id, advisory in advisories.items():
                            title = advisory.get("title", "Unknown vulnerability")
                            severity = advisory.get("severity", "unknown")
                            module_name = advisory.get("module_name", "unknown")
                            issues.append(f"Container ({dockerfile.name}): {module_name} - {severity}: {title}")
                            
                    except json.JSONDecodeError:
                        issues.append(f"Container ({dockerfile.name}): npm audit output parsing failed")
            
            # Cleanup temporary image
            subprocess.run(['docker', 'rmi', image_name], 
                         capture_output=True, timeout=30)
            
        except subprocess.TimeoutExpired:
            issues.append(f"Container scan timed out for {dockerfile.name}")
        except Exception as e:
            issues.append(f"Container scan error for {dockerfile.name}: {str(e)}")
            
        return issues

    def _local_security_scan(self, project_path: Path) -> List[str]:
        """Run security scans locally without containers"""
        issues = []
        
        # Python security scan
        requirements_file = project_path / "requirements.txt"
        if requirements_file.exists() and self.audit_tools.get('pip-audit', False):
            try:
                result = subprocess.run([
                    'pip-audit', '-r', str(requirements_file), '--format=json', '--exit-zero'
                ], capture_output=True, text=True, timeout=60)
                
                if result.stdout:
                    try:
                        audit_data = json.loads(result.stdout)
                        vulnerabilities = audit_data.get("vulnerabilities", [])
                        
                        for vuln in vulnerabilities:
                            pkg = vuln.get("name", "Unknown")
                            version = vuln.get("version", "?.?.?")
                            vuln_id = vuln.get("id", "NO_ID")
                            description = vuln.get("description", "No description").split('\n')[0]
                            issues.append(f"Python: {pkg} ({version}) - {vuln_id}: {description}")
                            
                    except json.JSONDecodeError:
                        issues.append("Python: pip-audit output parsing failed")
                        
            except subprocess.TimeoutExpired:
                issues.append("Python: pip-audit scan timed out")
            except Exception as e:
                issues.append(f"Python: pip-audit scan error - {str(e)}")
        
        # Node.js security scan
        package_json = project_path / "package.json"
        if package_json.exists() and self.audit_tools.get('npm-audit', False):
            try:
                result = subprocess.run([
                    'npm', 'audit', '--json'
                ], cwd=project_path, capture_output=True, text=True, timeout=60)
                
                if result.stdout:
                    try:
                        audit_data = json.loads(result.stdout)
                        advisories = audit_data.get("advisories", {})
                        
                        for advisory_id, advisory in advisories.items():
                            title = advisory.get("title", "Unknown vulnerability")
                            severity = advisory.get("severity", "unknown")
                            module_name = advisory.get("module_name", "unknown")
                            issues.append(f"Node.js: {module_name} - {severity}: {title}")
                            
                    except json.JSONDecodeError:
                        issues.append("Node.js: npm audit output parsing failed")
                        
            except subprocess.TimeoutExpired:
                issues.append("Node.js: npm audit scan timed out")
            except Exception as e:
                issues.append(f"Node.js: npm audit scan error - {str(e)}")
        
        return issues

    def generate_manifests(self) -> List[str]:
        """Generate dependency manifests for the project"""
        created: List[str] = []
        
        # -------- Python
        req = self.project_path / "requirements.txt"
        if not req.exists():
            pkgs = _detect_py_deps(self.project_path)
            if pkgs:
                req.write_text("\n".join(pkgs) + "\n", encoding='utf-8')
                created.append(str(req.relative_to(self.project_path)))
        
        # -------- Node
        pkg = self.project_path / "package.json"
        if not pkg.exists():
            deps = _detect_node_deps(self.project_path)
            if deps:
                _write_json(pkg, {"name": "app", "dependencies": deps})
                created.append(str(pkg.relative_to(self.project_path)))
        
        return created

    def run_security_scan(self) -> List[str]:
        """Run security scanning based on available configurations"""
        compose = self.project_path / "docker-compose.yml"
        issues: List[str] = []
        
        if compose.is_file():
            # Container-based scanning
            if (self.project_path / "requirements.txt").is_file():
                try:
                    subprocess.check_call(
                        ["docker", "compose", "run", "--rm", "backend",
                         "pip-audit", "-r", "requirements.txt"],
                        cwd=self.project_path,
                    )
                except subprocess.CalledProcessError:
                    issues.append("pip-audit failed in container")
            
            if (self.project_path / "package.json").is_file():
                try:
                    subprocess.check_call(
                        ["docker", "compose", "run", "--rm", "frontend", 
                         "npm", "audit", "--json"],
                        cwd=self.project_path,
                    )
                except subprocess.CalledProcessError:
                    issues.append("npm audit failed in container")
        else:
            # Local scanning fallback
            issues.extend(self._local_security_scan(self.project_path))
        
        return issues

    async def run(self, payload=None, **kwargs):
        """Main orchestrated run method for the agent"""
        created = self.generate_manifests()
        issues = self.run_security_scan()
        
        return {
            "name": self.name,
            "passed": len(issues) == 0,
            "files_created": created,
            "issues": issues,
            "container_based": self.docker_available and self._has_docker_configuration(self.project_path),
            "audit_tools_available": self.audit_tools
        }

# Pre-instantiated agent for quick access
dependency_verifier = DependencyVerifierAgent(project_path=Path("."), session_state={})

# Factory function for dynamic instantiation
def build_dependency_verifier_agent(project_path=None, session_state=None) -> DependencyVerifierAgent:
    return DependencyVerifierAgent(
        project_path=Path(project_path or "."),
        session_state=session_state or {}
    )
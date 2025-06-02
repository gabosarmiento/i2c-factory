# /workflow/self_healing_controller.py
# Phase 1: Stable self-healing controller with infinite loop prevention

from pathlib import Path
from typing import Tuple, Dict, Any, Optional, List
from datetime import datetime, timezone
import asyncio
import time

# Modern imports
# from i2c.agents.sre_team.sre_team import build_sre_team
# from i2c.agents.quality_team.quality_team import build_quality_team
# from i2c.agents.modification_team.code_modification_manager_agno import build_code_modification_team
from i2c.agents.budget_manager import BudgetManagerAgent
from i2c.workflow.modification.rag_config import get_embed_model
from i2c.db_utils import get_db_connection

try:
    from i2c.cli.controller import canvas
except ImportError:
    class FallbackCanvas:
        def warning(self, msg): print(f"[WARN_HEAL] {msg}")
        def error(self, msg): print(f"[ERROR_HEAL] {msg}")
        def info(self, msg): print(f"[INFO_HEAL] {msg}")
        def success(self, msg): print(f"[SUCCESS_HEAL] {msg}")
    canvas = FallbackCanvas()

class CircuitBreaker:
    """Circuit breaker to prevent endless loops in self-healing"""
    
    def __init__(self, failure_threshold: int = 3, timeout: int = 300):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.timeout:
                self.state = "HALF_OPEN"
                canvas.info("🔄 Circuit breaker transitioning to HALF_OPEN")
            else:
                raise Exception("Circuit breaker is OPEN - too many recent failures")
        
        try:
            result = func(*args, **kwargs)
            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
                self.failure_count = 0
                canvas.success("✅ Circuit breaker reset to CLOSED")
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
                canvas.error(f"🚫 Circuit breaker OPEN after {self.failure_count} failures")
            raise e

class SelfHealingController:
    """
    Phase 1: Stable self-healing controller with infinite loop prevention.
    Simple, reliable approach that prevents cascading failures.
    """

    def __init__(self, session_id: str, budget_manager: Optional[BudgetManagerAgent] = None):
        self.session_id = session_id
        self.budget_manager = budget_manager or BudgetManagerAgent(session_budget=None)
        
        # Phase 1: Simple loop prevention
        self.healing_in_progress = False
        self.max_healing_attempts = 2  # Keep it low to prevent long delays
        
        # Circuit breakers for different operations
        self.sre_circuit_breaker = CircuitBreaker(failure_threshold=2, timeout=180)
        self.quality_circuit_breaker = CircuitBreaker(failure_threshold=2, timeout=120)
        self.modification_circuit_breaker = CircuitBreaker(failure_threshold=3, timeout=240)
        
        # Recovery tracking
        self.recovery_log = []
        self.session_state = {
            "healing_session_id": session_id,
            "recovery_attempts": 0,
            "last_successful_pattern": None,
            "known_working_configurations": [],
            "failure_patterns": {},
            "budget_manager": self.budget_manager,
            "healing_in_progress": False
        }
        
        # Initialize modern components
        self._initialize_modern_components()
    
    def _initialize_modern_components(self):
        """Initialize modern RAG and knowledge components"""
        try:
            # Initialize database and embedding model
            self.db = get_db_connection()
            self.embed_model = get_embed_model()
            
            if self.db and self.embed_model:
                self.session_state.update({
                    "db": self.db,
                    "embed_model": self.embed_model,
                    "use_rag": True
                })
                canvas.success("🧠 Modern RAG components initialized")
            else:
                canvas.warning("⚠️ RAG components not available, using fallback mode")
                self.session_state["use_rag"] = False
                
        except Exception as e:
            canvas.warning(f"⚠️ Error initializing modern components: {e}")
            self.session_state["use_rag"] = False

    def _detect_project_language(self, project_path: Path) -> str:
        """Detect the primary language of the project"""
        if not project_path.exists():
            return "python"  # Default fallback
            
        # Count file extensions
        extensions = {}
        for file_path in project_path.glob("**/*"):
            if file_path.is_file():
                ext = file_path.suffix.lower()
                if ext:
                    extensions[ext] = extensions.get(ext, 0) + 1
        
        # Map to languages
        language_map = {
            ".py": "python",
            ".js": "javascript", 
            ".jsx": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".java": "java",
            ".go": "go",
            ".rs": "rust",
            ".cpp": "cpp",
            ".c": "c",
            ".rb": "ruby",
            ".php": "php",
            ".cs": "csharp",
        }
        
        # Find most common language
        language_counts = {}
        for ext, count in extensions.items():
            lang = language_map.get(ext, "unknown")
            if lang != "unknown":
                language_counts[lang] = language_counts.get(lang, 0) + count
        
        if language_counts:
            return max(language_counts.items(), key=lambda x: x[1])[0]
        
        return "python"  # Default fallback

    def _analyze_failure_patterns(self, error: Exception, context: Dict[str, Any]) -> str:
        """Simple pattern analysis for Phase 1"""
        error_str = str(error).lower()
        
        # Simple pattern matching
        if "api_key" in error_str or "openai" in error_str:
            return "api_configuration"
        elif "rate limit" in error_str or "quota" in error_str:
            return "rate_limiting"
        elif "syntax" in error_str or "invalid" in error_str:
            return "syntax_error"
        elif "import" in error_str or "module" in error_str:
            return "import_error"
        elif "network" in error_str or "connection" in error_str:
            return "network_error"
        elif "permission" in error_str or "access" in error_str:
            return "permission_error"
        else:
            return "unknown_error"

    async def _simple_retry(self, project_path: Path, language: str) -> Tuple[bool, Dict[str, Any]]:
        """Phase 1: Simple validation without calling SRE team again"""
        try:
            canvas.info("🔄 Simple retry with basic file validation")
            
            validation_results = {}
            
            # Check 1: Project exists and has files
            if not project_path.exists():
                return False, {"error": "Project path does not exist"}
            
            files = list(project_path.glob("**/*"))
            if not files:
                return False, {"error": "No files found in project"}
            
            validation_results["files_found"] = len(files)
            
            # Check 2: Language-specific basic validation
            language_files = []
            if language == "python":
                language_files = list(project_path.glob("**/*.py"))
            elif language in ["javascript", "typescript"]:
                language_files = list(project_path.glob("**/*.js")) + list(project_path.glob("**/*.ts")) + list(project_path.glob("**/*.jsx")) + list(project_path.glob("**/*.tsx"))
            elif language == "java":
                language_files = list(project_path.glob("**/*.java"))
            elif language == "go":
                language_files = list(project_path.glob("**/*.go"))
            else:
                # For unknown languages, just check if any code files exist
                language_files = [f for f in files if f.suffix in ['.py', '.js', '.ts', '.java', '.go', '.cpp', '.c', '.rb']]
            
            if not language_files:
                return False, {"error": f"No {language} files found"}
            
            validation_results["language_files"] = len(language_files)
            
            # Check 3: Basic syntax validation (language-specific)
            syntax_ok = await self._basic_syntax_check(project_path, language)
            validation_results["syntax_valid"] = syntax_ok
            
            # Check 4: File size sanity check (detect empty or corrupted files)
            non_empty_files = [f for f in language_files if f.stat().st_size > 0]
            validation_results["non_empty_files"] = len(non_empty_files)
            
            # Pass if we have files and basic syntax is OK
            success = (
                validation_results["files_found"] > 0 and
                validation_results["language_files"] > 0 and
                validation_results["non_empty_files"] > 0 and
                validation_results["syntax_valid"]
            )
            
            return success, {
                "validation_method": "basic_file_validation",
                "results": validation_results,
                "language": language
            }
            
        except Exception as e:
            return False, {"error": f"Simple retry failed: {str(e)}"}

    async def _basic_syntax_check(self, project_path: Path, language: str) -> bool:
        """Basic syntax validation for different languages"""
        try:
            if language == "python":
                import ast
                for py_file in project_path.glob("**/*.py"):
                    try:
                        with open(py_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                        if content.strip():  # Only check non-empty files
                            ast.parse(content)
                    except (SyntaxError, ValueError):
                        return False
                        
            elif language in ["javascript", "typescript"]:
                # Basic JS/TS validation - check for balanced brackets
                for js_file in project_path.glob("**/*.js") or project_path.glob("**/*.ts") or project_path.glob("**/*.jsx") or project_path.glob("**/*.tsx"):
                    try:
                        with open(js_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                        if content.strip():
                            # Check for balanced braces/brackets/parens
                            if (content.count('{') != content.count('}') or
                                content.count('[') != content.count(']') or
                                content.count('(') != content.count(')')):
                                return False
                    except Exception:
                        return False
                        
            elif language == "java":
                # Basic Java validation
                for java_file in project_path.glob("**/*.java"):
                    try:
                        with open(java_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                        if content.strip():
                            # Check for basic class structure
                            if 'class ' in content and '{' not in content:
                                return False
                    except Exception:
                        return False
                        
            elif language == "go":
                # Basic Go validation
                for go_file in project_path.glob("**/*.go"):
                    try:
                        with open(go_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                        if content.strip():
                            # Check for package declaration
                            if not content.strip().startswith('package '):
                                return False
                    except Exception:
                        return False
            
            return True
            
        except Exception:
            return False

    async def _attempt_basic_recovery(self, failure_pattern: str, project_path: Path, language: str) -> Tuple[bool, Dict[str, Any]]:
        """Phase 1: Basic recovery strategies"""
        
        canvas.info(f"🛠️ Attempting basic recovery for: {failure_pattern}")
        
        try:
            if failure_pattern == "api_configuration":
                # For API issues, just validate what we have
                return await self._simple_retry(project_path, language)
                
            elif failure_pattern == "rate_limiting":
                # For rate limiting, wait a bit then validate
                canvas.info("⏳ Waiting 5 seconds for rate limit cooldown...")
                await asyncio.sleep(5)
                return await self._simple_retry(project_path, language)
                
            elif failure_pattern == "syntax_error":
                # For syntax errors, try basic file fixes
                await self._apply_basic_syntax_fixes(project_path, language)
                return await self._simple_retry(project_path, language)
                
            elif failure_pattern == "import_error":
                # For import errors, create basic __init__.py files
                await self._create_missing_init_files(project_path)
                return await self._simple_retry(project_path, language)
                
            elif failure_pattern == "permission_error":
                # For permission errors, ensure directory exists
                project_path.mkdir(parents=True, exist_ok=True)
                return await self._simple_retry(project_path, language)
                
            else:
                # For unknown errors, just do basic validation
                return await self._simple_retry(project_path, language)
                
        except Exception as e:
            return False, {"error": f"Basic recovery failed: {str(e)}"}

    async def _apply_basic_syntax_fixes(self, project_path: Path, language: str):
        """Apply basic syntax fixes"""
        try:
            if language == "python":
                for py_file in project_path.glob("**/*.py"):
                    if py_file.exists():
                        content = py_file.read_text(encoding='utf-8')
                        # Basic fixes
                        content = content.replace('\t', '    ')  # Tabs to spaces
                        content = '\n'.join(line.rstrip() for line in content.splitlines())  # Remove trailing spaces
                        if content and not content.endswith('\n'):
                            content += '\n'
                        py_file.write_text(content, encoding='utf-8')
        except Exception as e:
            canvas.warning(f"Basic syntax fixes failed: {e}")

    async def _create_missing_init_files(self, project_path: Path):
        """Create missing __init__.py files for Python packages"""
        try:
            # Find Python directories without __init__.py
            for py_file in project_path.glob("**/*.py"):
                parent_dir = py_file.parent
                init_file = parent_dir / "__init__.py"
                if not init_file.exists():
                    init_file.write_text("# Auto-generated __init__.py\n", encoding='utf-8')
        except Exception as e:
            canvas.warning(f"Creating __init__.py files failed: {e}")

    async def run_with_recovery(self, project_path: Path, language: str = None) -> Tuple[bool, Dict[str, Any]]:
        """
        Phase 1: Simple, stable recovery with infinite loop prevention.
        
        Args:
            project_path: Path to the project directory
            language: Primary language (auto-detected if None)
            
        Returns:
            Tuple of (success: bool, results: Dict[str, Any])
        """
        
        # Phase 1: Prevent nested healing calls
        if self.healing_in_progress:
            canvas.warning("⚠️ Healing already in progress, preventing infinite loop")
            return False, {"error": "Healing already in progress"}
        
        # Phase 1: Auto-detect language if not provided
        if language is None:
            language = self._detect_project_language(project_path)
            canvas.info(f"🔍 Auto-detected project language: {language}")
        
        self.healing_in_progress = True
        self.session_state["healing_in_progress"] = True
        
        try:
            canvas.info(f"🚀 Starting stable self-healing for {project_path} ({language})")
            
            # Update session state
            self.session_state.update({
                "project_path": str(project_path),
                "language": language,
                "workflow_start_time": datetime.now(timezone.utc).isoformat()
            })
            
            # Phase 1: Try simple validation first (maybe nothing is wrong)
            try:
                simple_success, simple_result = await self._simple_retry(project_path, language)
                if simple_success:
                    canvas.success("✅ Project validation passed - no healing needed")
                    return True, simple_result
                else:
                    canvas.info("⚠️ Basic validation failed, attempting recovery")
            except Exception as e:
                canvas.warning(f"⚠️ Basic validation error: {e}")
            
            # Phase 1: Limited recovery attempts
            for attempt in range(1, self.max_healing_attempts + 1):
                self.session_state["recovery_attempts"] = attempt
                
                canvas.info(f"🔧 Recovery attempt {attempt}/{self.max_healing_attempts}")
                
                try:
                    # Analyze the failure pattern
                    failure_pattern = self._analyze_failure_patterns(
                        Exception("Validation failed"), 
                        {"attempt": attempt, "project_path": str(project_path)}
                    )
                    
                    # Attempt basic recovery
                    recovery_success, recovery_result = await self._attempt_basic_recovery(
                        failure_pattern, project_path, language
                    )
                    
                    # Log recovery attempt
                    recovery_log_entry = {
                        "attempt": attempt,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "failure_pattern": failure_pattern,
                        "success": recovery_success,
                        "result": recovery_result
                    }
                    self.recovery_log.append(recovery_log_entry)
                    
                    if recovery_success:
                        canvas.success(f"✅ Recovery successful with pattern: {failure_pattern}")
                        return True, {
                            "validation_results": recovery_result,
                            "recovery_applied": True,
                            "recovery_pattern": failure_pattern,
                            "recovery_attempts": attempt,
                            "language": language
                        }
                    else:
                        canvas.warning(f"⚠️ Recovery pattern {failure_pattern} failed")
                        
                except Exception as recovery_error:
                    canvas.error(f"❌ Recovery attempt {attempt} failed: {recovery_error}")
                    
                    recovery_log_entry = {
                        "attempt": attempt,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "success": False,
                        "error": str(recovery_error)
                    }
                    self.recovery_log.append(recovery_log_entry)
            
            # Phase 1: All recovery attempts failed
            canvas.error("💥 All recovery attempts exhausted")
            
            return False, {
                "validation_results": {},
                "recovery_applied": False,
                "recovery_attempts": self.max_healing_attempts,
                "recovery_log": self.recovery_log,
                "final_error": "All recovery strategies failed",
                "language": language
            }
            
        finally:
            # Always reset the healing flag
            self.healing_in_progress = False
            self.session_state["healing_in_progress"] = False

    def get_recovery_stats(self) -> Dict[str, Any]:
        """Get recovery statistics"""
        total_attempts = len(self.recovery_log)
        successful_attempts = sum(1 for log in self.recovery_log if log.get("success"))
        
        return {
            "total_recovery_attempts": total_attempts,
            "successful_recoveries": successful_attempts,
            "overall_success_rate": successful_attempts / total_attempts if total_attempts > 0 else 0,
            "healing_in_progress": self.healing_in_progress,
            "max_healing_attempts": self.max_healing_attempts,
            "session_id": self.session_id
        }
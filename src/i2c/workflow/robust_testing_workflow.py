"""
Robust Testing Workflow - Ensures quality through testable, iterative development
Integrates professional patterns with container-based validation for reliable software.
"""

import asyncio
from pathlib import Path
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass

try:
    from i2c.cli.controller import canvas
except ImportError:
    class DummyCanvas:
        def info(self, msg): print(f"[INFO] {msg}")
        def warning(self, msg): print(f"[WARNING] {msg}")
        def success(self, msg): print(f"[SUCCESS] {msg}")
        def error(self, msg): print(f"[ERROR] {msg}")
    canvas = DummyCanvas()

# Import the enhanced components
from i2c.workflow.professional_integration_patterns import generate_professional_integrated_app, APIEndpoint
from i2c.agents.sre_team.lightweight_container_tester import test_lightweight_containers, ensure_lightweight_images_cached, cleanup_old_test_images
from i2c.agents.sre_team.sandbox import SandboxExecutorAgent

@dataclass
class RobustTestResult:
    """Result of robust testing workflow"""
    generation_success: bool
    files_generated: Dict[str, str]
    container_test_success: bool
    professional_patterns_validated: List[str]
    issues_found: List[str]
    iteration_count: int
    final_quality_score: float

class RobustTestingWorkflow:
    """
    Robust, iterative workflow that ensures quality through actual testing.
    
    Instead of randomly generating code, this workflow:
    1. Generates professional code with integration patterns
    2. Tests it in production-like containers
    3. Iteratively fixes issues until quality standards are met
    4. Ensures working software, not disconnected silos
    """
    
    def __init__(self, max_iterations: int = 3, quality_threshold: float = 0.8):
        self.max_iterations = max_iterations
        self.quality_threshold = quality_threshold
        self.sandbox_agent = SandboxExecutorAgent()
        
        # Ensure lightweight images are cached on initialization
        asyncio.create_task(ensure_lightweight_images_cached())
        
    async def execute_robust_development_cycle(
        self, 
        objective: Dict[str, Any], 
        session_state: Dict[str, Any],
        project_path: Path = None
    ) -> RobustTestResult:
        """
        Execute robust development cycle with iterative testing and improvement.
        
        Process:
        1. Generate professional code
        2. Test in containers
        3. Identify and fix issues
        4. Repeat until quality threshold met
        5. Return working, tested software
        """
        
        canvas.info("🚀 Starting Robust Testing Workflow")
        canvas.info("Building working software through iterative testing")
        canvas.info("=" * 70)
        
        project_path = project_path or Path(".")
        iteration = 0
        final_files = {}
        all_issues = []
        validated_patterns = []
        
        while iteration < self.max_iterations:
            iteration += 1
            canvas.info(f"🔄 Iteration {iteration}/{self.max_iterations}")
            
            # Step 1: Generate professional code
            generation_result = await self._generate_professional_code(objective, session_state, iteration)
            
            if not generation_result["success"]:
                canvas.error(f"❌ Generation failed in iteration {iteration}")
                continue
            
            final_files = generation_result["files"]
            canvas.success(f"✅ Generated {len(final_files)} files")
            
            # Step 2: Test in production-like containers
            test_result = await self._test_in_containers(final_files, objective, project_path)
            
            if test_result["success"]:
                validated_patterns = test_result["patterns_validated"]
                canvas.success(f"🎉 Container testing passed! Patterns validated: {len(validated_patterns)}")
                break
            else:
                issues = test_result["issues_found"]
                all_issues.extend(issues)
                canvas.warning(f"⚠️  Issues found: {issues}")
                
                # Step 3: Analyze and attempt to fix issues
                fix_result = await self._attempt_to_fix_issues(final_files, issues, objective)
                
                if fix_result["success"]:
                    canvas.info("🔧 Applied fixes - retrying testing")
                    # Update session_state with lessons learned
                    session_state["quality_feedback"] = fix_result["lessons_learned"]
                else:
                    canvas.warning("⚠️  Could not automatically fix all issues")
        
        # Calculate final quality score
        quality_score = self._calculate_quality_score(validated_patterns, all_issues)
        
        # Final assessment
        overall_success = (
            len(final_files) > 0 and 
            len(validated_patterns) >= 3 and 
            quality_score >= self.quality_threshold
        )
        
        canvas.info(f"🏁 Robust Testing Workflow Complete!")
        canvas.info(f"   📊 Quality Score: {quality_score:.1%}")
        canvas.info(f"   ✅ Patterns Validated: {len(validated_patterns)}")
        canvas.info(f"   🔄 Iterations Used: {iteration}")
        
        if overall_success:
            canvas.success("🎉 HIGH QUALITY: Working software delivered!")
        else:
            canvas.warning("⚠️  NEEDS IMPROVEMENT: Additional work required")
        
        # Cleanup Docker resources to avoid bloat
        try:
            await cleanup_old_test_images()
        except Exception as e:
            canvas.warning(f"⚠️  Cleanup warning: {e}")
        
        return RobustTestResult(
            generation_success=len(final_files) > 0,
            files_generated=final_files,
            container_test_success=len(validated_patterns) >= 3,
            professional_patterns_validated=validated_patterns,
            issues_found=all_issues,
            iteration_count=iteration,
            final_quality_score=quality_score
        )
    
    async def _generate_professional_code(
        self, 
        objective: Dict[str, Any], 
        session_state: Dict[str, Any], 
        iteration: int
    ) -> Dict[str, Any]:
        """Generate professional code with lessons learned from previous iterations"""
        
        canvas.info(f"🏗️  Generating professional code (iteration {iteration})")
        
        try:
            # Extract API endpoints if specified
            api_endpoints = self._extract_api_endpoints_from_objective(objective)
            
            # Apply quality feedback from previous iterations
            enhanced_objective = self._enhance_objective_with_feedback(objective, session_state)
            
            # Generate professional integrated app
            files = generate_professional_integrated_app(
                objective=enhanced_objective,
                session_state=session_state,
                api_endpoints=api_endpoints
            )
            
            return {
                "success": True,
                "files": files,
                "message": f"Generated {len(files)} professional files"
            }
            
        except Exception as e:
            canvas.error(f"❌ Code generation failed: {e}")
            return {
                "success": False,
                "files": {},
                "message": str(e)
            }
    
    async def _test_in_containers(
        self, 
        files: Dict[str, str], 
        objective: Dict[str, Any], 
        project_path: Path
    ) -> Dict[str, Any]:
        """Test generated code using lightweight containers (optimized approach)"""
        
        canvas.info("🐳 Testing with lightweight containers (50MB vs 500MB+)")
        
        try:
            # Use lightweight container testing (no heavy builds)
            test_result = await test_lightweight_containers(files, objective)
            
            # Map lightweight results to our format
            patterns_validated = []
            
            if test_result.syntax_valid:
                patterns_validated.append("Syntax Validation")
            if test_result.integration_patterns_valid:
                patterns_validated.append("Integration Patterns")
            if test_result.performance_acceptable:
                patterns_validated.append("Performance")
            
            # Add additional validations based on our professional patterns
            if test_result.syntax_valid and test_result.integration_patterns_valid:
                patterns_validated.append("Professional Code Quality")
            
            success = len(test_result.issues_found) == 0 and len(patterns_validated) >= 2
            
            return {
                "success": success,
                "patterns_validated": patterns_validated,
                "issues_found": test_result.issues_found,
                "performance_metrics": {"lightweight_test": True, "test_output": test_result.test_output}
            }
            
        except Exception as e:
            canvas.error(f"❌ Lightweight container testing failed: {e}")
            return {
                "success": False,
                "patterns_validated": [],
                "issues_found": [str(e)],
                "performance_metrics": {}
            }
    
    async def _attempt_to_fix_issues(
        self, 
        files: Dict[str, str], 
        issues: List[str], 
        objective: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Attempt to automatically fix identified issues"""
        
        canvas.info("🔧 Attempting to fix identified issues")
        
        fixes_applied = []
        lessons_learned = []
        
        for issue in issues:
            if "file conflict" in issue.lower():
                fix_result = self._fix_file_conflicts(files, issue)
                if fix_result["success"]:
                    fixes_applied.append(fix_result["fix_description"])
                    lessons_learned.append("Ensure consistent file naming (App.jsx not App.js)")
            
            elif "cors" in issue.lower():
                fix_result = self._fix_cors_issues(files, issue)
                if fix_result["success"]:
                    fixes_applied.append(fix_result["fix_description"])
                    lessons_learned.append("Ensure CORS configuration for API access")
            
            elif "api" in issue.lower() and "ui" in issue.lower():
                fix_result = self._fix_api_ui_integration(files, issue)
                if fix_result["success"]:
                    fixes_applied.append(fix_result["fix_description"])
                    lessons_learned.append("Ensure tight API-UI coupling")
        
        success = len(fixes_applied) > 0
        
        if success:
            canvas.success(f"✅ Applied {len(fixes_applied)} fixes")
        else:
            canvas.warning("⚠️  No automatic fixes available")
        
        return {
            "success": success,
            "fixes_applied": fixes_applied,
            "lessons_learned": lessons_learned
        }
    
    def _fix_file_conflicts(self, files: Dict[str, str], issue: str) -> Dict[str, Any]:
        """Fix file naming conflicts"""
        
        # Remove App.js if App.jsx exists
        if "frontend/src/App.js" in files and "frontend/src/App.jsx" in files:
            del files["frontend/src/App.js"]
            return {
                "success": True,
                "fix_description": "Removed App.js to resolve conflict with App.jsx"
            }
        
        return {"success": False, "fix_description": "Could not fix file conflict"}
    
    def _fix_cors_issues(self, files: Dict[str, str], issue: str) -> Dict[str, Any]:
        """Fix CORS configuration issues"""
        
        backend_main = "backend/main.py"
        if backend_main in files:
            content = files[backend_main]
            
            if "CORSMiddleware" not in content:
                # Add CORS middleware
                cors_import = "from fastapi.middleware.cors import CORSMiddleware\n"
                cors_config = '''
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
'''
                
                # Insert after FastAPI app creation
                if "app = FastAPI(" in content:
                    lines = content.split('\n')
                    new_lines = []
                    app_created = False
                    
                    for line in lines:
                        new_lines.append(line)
                        if not app_created and "from fastapi import" in line:
                            new_lines.append(cors_import.strip())
                        elif "app = FastAPI(" in line and not app_created:
                            new_lines.append(cors_config)
                            app_created = True
                    
                    files[backend_main] = '\n'.join(new_lines)
                    
                    return {
                        "success": True,
                        "fix_description": "Added CORS middleware configuration"
                    }
        
        return {"success": False, "fix_description": "Could not fix CORS issue"}
    
    def _fix_api_ui_integration(self, files: Dict[str, str], issue: str) -> Dict[str, Any]:
        """Fix API-UI integration issues"""
        
        # This would require more sophisticated analysis and fixes
        # For now, return a placeholder
        return {
            "success": False, 
            "fix_description": "API-UI integration fixes not yet implemented"
        }
    
    def _extract_api_endpoints_from_objective(self, objective: Dict[str, Any]) -> List[APIEndpoint]:
        """Extract API endpoints from objective description"""
        
        # Default endpoints for fullstack apps
        endpoints = [
            APIEndpoint(
                path="/api/health",
                method="GET",
                response_schema={"status": "string", "timestamp": "string"}
            ),
            APIEndpoint(
                path="/api/data",
                method="GET",
                response_schema={"data": "array", "count": "number"}
            )
        ]
        
        # Add task-specific endpoints based on objective
        task = objective.get("task", "").lower()
        
        if "task" in task or "todo" in task:
            endpoints.append(APIEndpoint(
                path="/api/tasks",
                method="POST",
                response_schema={"id": "string", "message": "string"}
            ))
        
        if "emotion" in task or "sentiment" in task:
            endpoints.append(APIEndpoint(
                path="/api/emotions/analyze",
                method="POST",
                response_schema={"emotion": "string", "confidence": "number"}
            ))
        
        if "user" in task or "auth" in task:
            endpoints.append(APIEndpoint(
                path="/api/users",
                method="GET",
                response_schema={"users": "array", "count": "number"}
            ))
        
        return endpoints
    
    def _enhance_objective_with_feedback(
        self, 
        objective: Dict[str, Any], 
        session_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Enhance objective with lessons learned from quality feedback"""
        
        enhanced = objective.copy()
        
        quality_feedback = session_state.get("quality_feedback", [])
        
        if quality_feedback:
            # Add quality constraints based on feedback
            existing_constraints = enhanced.get("constraints", [])
            quality_constraints = [
                f"Apply lesson learned: {lesson}" for lesson in quality_feedback
            ]
            enhanced["constraints"] = existing_constraints + quality_constraints
        
        return enhanced
    
    def _calculate_quality_score(self, validated_patterns: List[str], issues: List[str]) -> float:
        """Calculate overall quality score"""
        
        # Base score from validated patterns (0-1)
        pattern_score = min(len(validated_patterns) / 5.0, 1.0)  # 5 patterns max
        
        # Penalty for issues (0-1)
        issue_penalty = min(len(issues) * 0.1, 0.5)  # Max 50% penalty
        
        # Combined score
        quality_score = max(pattern_score - issue_penalty, 0.0)
        
        return quality_score

# Main entry point for integration with existing workflow
async def execute_robust_testing_workflow(
    objective: Dict[str, Any], 
    session_state: Dict[str, Any],
    project_path: Path = None,
    max_iterations: int = 3,
    quality_threshold: float = 0.8
) -> RobustTestResult:
    """
    Execute robust testing workflow with iterative improvement.
    
    Use this instead of random code generation to ensure working software.
    """
    
    workflow = RobustTestingWorkflow(
        max_iterations=max_iterations,
        quality_threshold=quality_threshold
    )
    
    return await workflow.execute_robust_development_cycle(
        objective=objective,
        session_state=session_state,
        project_path=project_path
    )
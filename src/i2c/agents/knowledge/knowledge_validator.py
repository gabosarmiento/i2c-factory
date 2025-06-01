from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path
import json
from dataclasses import dataclass

from i2c.agents.knowledge.pattern_extractor import PatternExtractorAgent


@dataclass
class ValidationResult:
    """Result of knowledge application validation"""
    success: bool
    score: float  # 0.0 to 1.0
    violations: List[str]
    applied_patterns: List[str]
    missing_patterns: List[str]
    details: Dict[str, Any]


class KnowledgeValidator:
    """Validates that generated outputs apply retrieved knowledge patterns"""
    
    def __init__(self):
        self.reasoner = PatternExtractorAgent()
        self.validation_history = []
    
    def validate_generation_output(
        self, 
        generated_files: Dict[str, str], 
        retrieved_context: str,
        task_description: str = ""
    ) -> ValidationResult:
        """
        Validate entire generation output against knowledge context
        
        Args:
            generated_files: {file_path: content} mapping of generated code
            retrieved_context: Raw knowledge context from RAG/vector DB
            task_description: Original task for context
            
        Returns:
            ValidationResult with success status and detailed feedback
        """
        if not generated_files or not retrieved_context:
            return ValidationResult(
                success=True, score=1.0, violations=[], 
                applied_patterns=[], missing_patterns=[], details={}
            )
        
        # Extract patterns from knowledge context
        patterns = self.reasoner.extract_actionable_patterns(retrieved_context)
        
        if not patterns:
            return ValidationResult(
                success=True, score=1.0, violations=["No patterns found in context"],
                applied_patterns=[], missing_patterns=[], details={"patterns": patterns}
            )
        
        # Validate each file
        file_results = {}
        total_violations = []
        total_applied = []
        
        for file_path, content in generated_files.items():
            success, violations = self.reasoner.validate_pattern_application(content, patterns)
            applied = self._extract_applied_patterns(content, patterns)
            
            file_results[file_path] = {
                "success": success,
                "violations": violations,
                "applied_patterns": applied
            }
            
            total_violations.extend([f"{file_path}: {v}" for v in violations])
            total_applied.extend(applied)
        
        # Calculate overall score
        total_files = len(generated_files)
        successful_files = sum(1 for r in file_results.values() if r["success"])
        file_success_rate = successful_files / total_files if total_files > 0 else 0
        
        # Pattern application rate
        unique_patterns = set()
        for pattern_list in patterns.values():
            unique_patterns.update(pattern_list)
        
        applied_pattern_rate = len(set(total_applied)) / len(unique_patterns) if unique_patterns else 1.0
        
        # Combined score
        overall_score = (file_success_rate * 0.6) + (applied_pattern_rate * 0.4)
        overall_success = overall_score >= 0.7 and len(total_violations) == 0
        
        # Identify missing patterns
        missing_patterns = self._identify_missing_patterns(patterns, total_applied)
        
        result = ValidationResult(
            success=overall_success,
            score=overall_score,
            violations=total_violations,
            applied_patterns=list(set(total_applied)),
            missing_patterns=missing_patterns,
            details={
                "file_results": file_results,
                "patterns_available": patterns,
                "file_success_rate": file_success_rate,
                "pattern_application_rate": applied_pattern_rate,
                "task": task_description
            }
        )
        
        # Store in history for analysis
        self.validation_history.append(result)
        
        return result
    
    def validate_single_file(
        self, 
        file_content: str, 
        retrieved_context: str,
        file_type: str = "code"
    ) -> ValidationResult:
        """Validate a single file against knowledge context"""
        return self.validate_generation_output(
            {"single_file": file_content}, 
            retrieved_context, 
            f"Single {file_type} validation"
        )
    
    def get_validation_report(self, result: ValidationResult) -> str:
        """Generate human-readable validation report"""
        report = []
        
        # Header
        status = "✅ PASSED" if result.success else "❌ FAILED"
        report.append(f"Knowledge Application Validation: {status}")
        report.append(f"Score: {result.score:.2f}/1.00")
        report.append("")
        
        # Applied patterns
        if result.applied_patterns:
            report.append("🎯 Applied Patterns:")
            for pattern in result.applied_patterns:
                report.append(f"  ✓ {pattern}")
            report.append("")
        
        # Missing patterns
        if result.missing_patterns:
            report.append("❌ Missing Patterns:")
            for pattern in result.missing_patterns:
                report.append(f"  ✗ {pattern}")
            report.append("")
        
        # Violations
        if result.violations:
            report.append("⚠️ Violations:")
            for violation in result.violations:
                report.append(f"  • {violation}")
            report.append("")
        
        # File-level details
        if "file_results" in result.details:
            report.append("📁 File Analysis:")
            for file_path, file_result in result.details["file_results"].items():
                file_status = "✓" if file_result["success"] else "✗"
                report.append(f"  {file_status} {file_path}")
                if file_result["violations"]:
                    for violation in file_result["violations"]:
                        report.append(f"    ⚠️ {violation}")
        
        return "\n".join(report)
    
    def get_improvement_suggestions(self, result: ValidationResult) -> List[str]:
        """Generate actionable improvement suggestions"""
        suggestions = []
        
        if result.score < 0.5:
            suggestions.append("Consider regenerating with stronger knowledge enforcement prompts")
        
        if result.missing_patterns:
            suggestions.append(f"Explicitly require these patterns: {', '.join(result.missing_patterns[:3])}")
        
        if any("generic code" in v for v in result.violations):
            suggestions.append("Add anti-pattern detection to prevent generic fallbacks")
        
        if any("missing.*justification" in v for v in result.violations):
            suggestions.append("Require agents to end responses with 'Applied patterns: [list]'")
        
        return suggestions
    
    def _extract_applied_patterns(self, content: str, patterns: Dict) -> List[str]:
        """Extract which patterns were actually applied in the content"""
        applied = []
        content_lower = content.lower()
        
        # Check import patterns
        for import_pattern in patterns.get('imports', []):
            import_key = self.reasoner._extract_import_key(import_pattern)
            if import_key and import_key.lower() in content_lower:
                applied.append(f"import:{import_key}")
        
        # Check conventions
        for convention in patterns.get('conventions', []):
            # Simple keyword matching for conventions
            if any(word in content_lower for word in convention.lower().split()[:3]):
                applied.append(f"convention:{convention[:30]}...")
        
        # Check architecture patterns
        for arch_rule in patterns.get('architecture', []):
            if any(word in content_lower for word in arch_rule.lower().split()[:3]):
                applied.append(f"architecture:{arch_rule[:30]}...")
        
        return applied
    
    def _identify_missing_patterns(self, patterns: Dict, applied_patterns: List[str]) -> List[str]:
        """Identify patterns that should have been applied but weren't"""
        missing = []
        
        applied_types = set(p.split(':')[0] for p in applied_patterns)
        
        if patterns.get('imports') and 'import' not in applied_types:
            missing.append("No documented imports used")
        
        if patterns.get('conventions') and 'convention' not in applied_types:
            missing.append("Documented conventions ignored")
        
        if patterns.get('architecture') and 'architecture' not in applied_types:
            missing.append("Architectural patterns not followed")
        
        return missing


# Utility functions for easy integration
def quick_validate(generated_code: str, knowledge_context: str) -> bool:
    """Quick validation check - returns True if knowledge was applied"""
    validator = KnowledgeValidator()
    result = validator.validate_single_file(generated_code, knowledge_context)
    return result.success


def validate_project_generation(project_path: Path, knowledge_context: str) -> ValidationResult:
    """Validate entire project directory against knowledge"""
    validator = KnowledgeValidator()
    
    # Read all code files
    generated_files = {}
    code_extensions = {'.py', '.js', '.jsx', '.ts', '.tsx', '.java', '.cpp', '.rs', '.go'}
    
    for file_path in project_path.rglob("*"):
        if file_path.is_file() and file_path.suffix in code_extensions:
            try:
                relative_path = str(file_path.relative_to(project_path))
                content = file_path.read_text(encoding='utf-8')
                generated_files[relative_path] = content
            except Exception:
                continue  # Skip files that can't be read
    
    return validator.validate_generation_output(generated_files, knowledge_context)


# Test examples
if __name__ == "__main__":
    # Test 1: Basic validation
    def test_basic_validation():
        validator = KnowledgeValidator()
        
        knowledge_context = """
        from agno.agent import Agent
        from agno.team import Team
        
        Always separate frontend and backend code.
        Use Agent(model=..., instructions=...) pattern.
        """
        
        good_code = """
        from agno.agent import Agent
        from agno.models.openai import OpenAIChat
        
        # Backend agent following documented pattern
        agent = Agent(
            model=OpenAIChat(id="gpt-4"),
            instructions=["Handle backend tasks"]
        )
        
        # Applied patterns: import:agno.agent, convention:agent pattern
        """
        
        bad_code = """
        def main():
            print("Hello, World!")
        """
        
        # Test good code
        good_result = validator.validate_single_file(good_code, knowledge_context)
        print("Good code validation:", good_result.success)
        print("Score:", good_result.score)
        
        # Test bad code
        bad_result = validator.validate_single_file(bad_code, knowledge_context)
        print("Bad code validation:", bad_result.success)
        print("Violations:", bad_result.violations)
    
    # Test 2: Project validation
    def test_project_validation():
        """Test with mock project files"""
        files = {
            "main.py": "from agno.agent import Agent\nagent = Agent(model=..., instructions=...)",
            "utils.py": "def helper(): return 'generic'"
        }
        
        context = "from agno.agent import Agent\nUse Agent pattern for all components"
        
        validator = KnowledgeValidator()
        result = validator.validate_generation_output(files, context, "Test project")
        
        print("\nProject Validation Report:")
        print(validator.get_validation_report(result))
        
        if not result.success:
            print("\nSuggestions:")
            for suggestion in validator.get_improvement_suggestions(result):
                print(f"  • {suggestion}")
    
    test_basic_validation()
    test_project_validation()
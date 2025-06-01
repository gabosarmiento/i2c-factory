from typing import Dict, List, Any
import json
from agno.agent import Agent
from builtins import llm_highest
from i2c.cli.controller import canvas

class PatternExtractorAgent(Agent):
    """
    Agno Agent for intelligent pattern extraction from documentation.
    Integrates with the existing KnowledgeTeam architecture.
    """
    
    def __init__(self, **kwargs):
        super().__init__(
            name="PatternExtractor",
            model=llm_highest,
            role="Extract actionable development patterns from documentation",
            instructions=[
                "You are an expert at analyzing development documentation and extracting actionable patterns.",
                "Your job is to infer file structures, imports, conventions, and architecture from text.",
                "Be intelligent about implied patterns - if docs mention 'FastAPI best practices', infer typical FastAPI project structure.",
                "Return well-structured JSON with specific, actionable patterns that developers can follow.",
                "Focus on patterns that can be validated in generated code.",
                "Work collaboratively with the KnowledgeTeam to enhance code generation."
            ],
            **kwargs
        )
    
    def extract_actionable_patterns(self, raw_context: str) -> Dict[str, List[str]]:
        """Use Agno agent to intelligently extract patterns"""
        if not raw_context.strip():
            return {}
        
        extraction_prompt = f"""
Analyze this documentation and extract actionable development patterns:

DOCUMENTATION:
{raw_context}

Extract patterns in this JSON format:
{{
    "imports": ["specific import statements that should be used"],
    "file_structure": ["files/directories that should be created based on framework/practices mentioned"],
    "conventions": ["coding conventions and naming patterns to follow"],
    "architecture": ["architectural principles and structural requirements"],
    "examples": ["concrete code examples if present"]
}}

INTELLIGENCE REQUIRED:
- If documentation mentions "FastAPI", infer typical FastAPI project structure (main.py, api/, models/)
- If it mentions "React", infer frontend structure (src/, components/, App.jsx)
- If it discusses "best practices", translate into specific file/code requirements
- Extract both explicit and IMPLIED patterns from the context

Return ONLY the JSON, no explanation.
"""
        
        try:
            response = self.run(extraction_prompt)
            content = response.content if hasattr(response, 'content') else str(response)
            
            # Parse JSON response with better error handling
            if '```json' in content:
                json_start = content.find('```json') + 7
                json_end = content.find('```', json_start)
                content = content[json_start:json_end].strip()
            elif '```' in content:
                json_start = content.find('```') + 3
                json_end = content.find('```', json_start)
                content = content[json_start:json_end].strip()
            
            # Check if content is empty or invalid
            if not content.strip():
                canvas.warning("Empty JSON content from PatternExtractorAgent")
                raise ValueError("Empty JSON response")
            
            patterns = json.loads(content)
            
            # Ensure all required keys exist
            required_keys = ['imports', 'file_structure', 'conventions', 'architecture', 'examples']
            for key in required_keys:
                if key not in patterns:
                    patterns[key] = []
            
            return patterns
            
        except Exception as e:
            canvas.error(f"Pattern extraction failed: {e}")
            # Return generic fallback patterns that work with any framework
            return {
                "imports": [],
                "file_structure": [],
                "conventions": ["Follow best practices", "Use clear naming"],
                "architecture": ["Modular design", "Clean separation of concerns"],
                "examples": []
            }
    
    def validate_pattern_application(self, output: str, patterns: Dict) -> tuple[bool, List[str]]:
        """Validate output applies extracted patterns"""
        if not output or not patterns:
            return True, []
        
        validation_prompt = f"""
    Validate if this generated code follows the extracted patterns:

    EXTRACTED PATTERNS:
    {json.dumps(patterns, indent=2)}

    GENERATED CODE:
    {output}

    Check if the code:
    1. Uses the documented imports (if applicable)
    2. Follows applicable conventions (ignore file structure for single files)
    3. Shows pattern application (looks for "Applied patterns:" in code)
    4. Avoids generic code when patterns are available

    IMPORTANT VALIDATION RULES:
    - For single-file code, don't penalize missing multi-file structure
    - Focus on imports, conventions, and pattern usage that CAN be shown in one file
    - If code shows FastAPI usage with imports and proper patterns, consider it successful
    - Be lenient about file organization patterns when validating single files

    Return JSON:
    {{
        "success": true/false,
        "violations": ["list of specific violations"],
        "applied_patterns": ["list of patterns that were correctly applied"]
    }}

    Be fair - if the code demonstrates clear application of applicable patterns and includes justification, mark as success.
    """
        
        try:
            response = self.run(validation_prompt)
            content = response.content if hasattr(response, 'content') else str(response)
            
            # Parse JSON response
            if '```json' in content:
                json_start = content.find('```json') + 7
                json_end = content.find('```', json_start)
                content = content[json_start:json_end].strip()
            elif '```' in content:
                json_start = content.find('```') + 3
                json_end = content.find('```', json_start)
                content = content[json_start:json_end].strip()
            
            result = json.loads(content)
            return result.get('success', False), result.get('violations', [])
            
        except Exception as e:
            # Fallback: check for basic pattern application
            output_lower = output.lower()
            has_imports = any(imp.lower() in output_lower for imp in patterns.get('imports', []))
            has_justification = 'applied patterns:' in output_lower
            
            if has_imports and has_justification:
                return True, []
            else:
                violations = []
                if not has_imports:
                    violations.append("Missing documented imports")
                if not has_justification:
                    violations.append("Missing pattern application justification")
                return False, violations
            
    def create_reasoning_requirements(self, patterns: Dict, task_type: str) -> List[str]:
        """Convert extracted patterns into agent instructions"""
        requirements = []
        
        # Core reasoning mandate
        requirements.append("REASONING REQUIREMENT: Explain which retrieved pattern guided each decision.")
        
        # Pattern-specific requirements
        if patterns.get('imports'):
            requirements.append("IMPORT ENFORCEMENT: Use these documented import patterns:")
            for imp in patterns['imports'][:3]:
                requirements.append(f"  - {imp}")
        
        if patterns.get('file_structure'):
            requirements.append("STRUCTURE ENFORCEMENT: Follow documented file organization:")
            for structure in patterns['file_structure'][:3]:
                requirements.append(f"  - {structure}")
        
        if patterns.get('conventions'):
            requirements.append("CONVENTION ENFORCEMENT: Apply documented standards:")
            for conv in patterns['conventions'][:3]:
                requirements.append(f"  - {conv}")
        
        if patterns.get('architecture'):
            requirements.append("ARCHITECTURE ENFORCEMENT: Implement documented patterns:")
            for arch in patterns['architecture'][:2]:
                requirements.append(f"  - {arch}")
        
        # Task-specific reasoning
        if task_type in ['planning', 'planner']:
            requirements.append("PLANNING VALIDATION: Justify file structure against retrieved patterns.")
        elif task_type in ['building', 'code_builder']:
            requirements.append("CODE VALIDATION: Reference specific pattern for each major code section.")
        
        # Universal requirements
        requirements.extend([
            "ANTI-PATTERN: Never generate generic 'Hello World' when rich patterns are available.",
            "JUSTIFICATION: End response with: 'Applied patterns: [list specific patterns used]'"
        ])
        
        return requirements

    def _extract_import_key(self, import_pattern: str) -> str:
        """Extract key module/package name from import"""
        # Simple extraction of main module name
        if 'from' in import_pattern:
            parts = import_pattern.split()
            if len(parts) >= 2:
                return parts[1].split('.')[0]  # Get first part of module
        elif 'import' in import_pattern:
            parts = import_pattern.spcorelit()
            if len(parts) >= 2:
                return parts[1].split('.')[0]
        return import_pattern
    
    def _extract_structure_key(self, structure: str) -> str:
        """Extract key path component"""
        # Get last meaningful part of path
        if '/' in structure:
            return structure.split('/')[-1] if structure.endswith('/') else structure.split('/')[-2]
        return structure

# Integration with existing KnowledgeTeam
def create_pattern_extractor_for_knowledge_team():
    """Create PatternExtractorAgent for integration with KnowledgeTeam"""
    return PatternExtractorAgent()
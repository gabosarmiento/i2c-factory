from typing import Dict, List, Any
import re
from pathlib import Path

class KnowledgeApplicationScorer:
    """Score how well agents apply knowledge patterns in their outputs"""
    
    def __init__(self):
        self.pattern_weights = {
            "agno_imports": 0.25,
            "agent_creation": 0.25, 
            "team_coordination": 0.20,
            "best_practices": 0.15,
            "code_structure": 0.15
        }
    
    def score_pattern_application(self, agent_output: str, expected_patterns: Dict[str, Any]) -> Dict[str, Any]:
        """Score how well agent applied knowledge patterns"""
        
        if not agent_output or not expected_patterns:
            return {"overall_score": 0.0, "pattern_scores": {}, "missing_patterns": []}
        
        scores = {}
        
        for pattern_name, pattern_rules in expected_patterns.items():
            score = self._calculate_pattern_score(agent_output, pattern_rules)
            scores[pattern_name] = score
            
        overall_score = sum(scores.values()) / len(scores) if scores else 0.0
        missing_patterns = [p for p, s in scores.items() if s < 0.5]
        
        return {
            "overall_score": overall_score,
            "pattern_scores": scores,
            "missing_patterns": missing_patterns,
            "feedback": self._generate_feedback(scores, missing_patterns)
        }
    
    def _calculate_pattern_score(self, output: str, pattern_rules: List[str]) -> float:
        """Calculate score for a specific pattern"""
        if not pattern_rules:
            return 1.0
            
        matches = 0
        total_rules = len(pattern_rules)
        
        for rule in pattern_rules:
            if self._check_pattern_match(output, rule):
                matches += 1
        
        return matches / total_rules if total_rules > 0 else 0.0
    
    def _check_pattern_match(self, output: str, rule: str) -> bool:
        """Check if output matches a specific pattern rule"""
        output_lower = output.lower()
        
        # Check for specific patterns
        if "import" in rule.lower():
            return bool(re.search(r'from\s+agno\.|import\s+agno', output, re.IGNORECASE))
        elif "agent(" in rule.lower():
            return bool(re.search(r'Agent\s*\(', output, re.IGNORECASE))
        elif "team(" in rule.lower():
            return bool(re.search(r'Team\s*\(', output, re.IGNORECASE))
        elif "model=" in rule.lower():
            return "model=" in output_lower
        elif "instructions=" in rule.lower():
            return "instructions=" in output_lower
        else:
            return rule.lower() in output_lower
    
    def _generate_feedback(self, scores: Dict[str, float], missing_patterns: List[str]) -> List[str]:
        """Generate actionable feedback for improving pattern application"""
        feedback = []
        
        if "agno_imports" in missing_patterns:
            feedback.append("Add proper AGNO imports: from agno.agent import Agent")
        
        if "agent_creation" in missing_patterns:
            feedback.append("Use proper Agent creation pattern with model= and instructions=")
            
        if "team_coordination" in missing_patterns:
            feedback.append("Create Team with members= and mode= parameters")
        
        # Add positive feedback for good scores
        good_patterns = [p for p, s in scores.items() if s >= 0.8]
        if good_patterns:
            feedback.append(f"Excellent application of: {', '.join(good_patterns)}")
        
        return feedback

    def create_agno_pattern_expectations(self, task_type: str = "general") -> Dict[str, List[str]]:
        """Create expected patterns based on task type"""
        
        base_patterns = {
            "agno_imports": [
                "from agno.agent import Agent",
                "from agno.team import Team", 
                "from agno.models"
            ],
            "agent_creation": [
                "Agent(",
                "model=",
                "instructions="
            ],
            "team_coordination": [
                "Team(",
                "members=",
                "mode="
            ]
        }
        
        if task_type == "code_generation":
            base_patterns["best_practices"] = [
                "reasoning=True",
                "tools=",
                "markdown=True"
            ]
        elif task_type == "multi_agent":
            base_patterns["team_coordination"].extend([
                "coordinate",
                "collaborate" 
            ])
        
        return base_patterns
class PrincipleTransformer:
    def transform_knowledge_to_principles(self, knowledge_chunks):
        """Convert raw knowledge into actionable principles"""
        
        principles = []
        for chunk in knowledge_chunks:
            # Extract actionable patterns
            if "MUST" in chunk or "ALWAYS" in chunk:
                principles.append(self._extract_rule(chunk))
            elif "pattern" in chunk.lower():
                principles.append(self._extract_pattern(chunk))
            elif "example" in chunk.lower():
                principles.append(self._extract_principle_from_example(chunk))
        
        return self._synthesize_principles(principles)
    
class DeepPrincipleTransformer:
    def extract_contextual_patterns(self, knowledge_chunks):
        """Extract not just what to do, but when, why, and how"""
        
        patterns = {
            "core_rules": [],      # What to always do
            "context_rules": [],   # When to apply variations
            "error_patterns": [],  # What goes wrong and why
            "optimization_tips": [], # How to do it better
            "integration_patterns": [] # How it works with other code
        }
        
        for chunk in knowledge_chunks:
            content = chunk.get("content", "")
            
            # Deep pattern extraction
            if "when" in content.lower() or "if" in content.lower():
                patterns["context_rules"].append(self._extract_conditional(content))
            elif "error" in content.lower() or "wrong" in content.lower():
                patterns["error_patterns"].append(self._extract_error_pattern(content))
            elif "performance" in content.lower() or "optimize" in content.lower():
                patterns["optimization_tips"].append(content)
            elif "always" in content.lower() or "must" in content.lower():
                patterns["core_rules"].append(content)
            elif "with" in content.lower() or "together" in content.lower():
                patterns["integration_patterns"].append(content)
                
        return patterns
    
    def _extract_conditional(self, content):
        """Extract conditional logic from content"""
        lines = content.split('\n')
        conditionals = []
        
        for line in lines:
            line = line.strip()
            if any(word in line.lower() for word in ['when', 'if', 'unless', 'should']):
                if len(line) > 10 and len(line) < 200:
                    conditionals.append(line)
        
        return conditionals[0] if conditionals else content[:100]
    
    def _extract_error_pattern(self, content):
        """Extract what goes wrong and why"""
        lines = content.split('\n')
        errors = []
        
        for line in lines:
            line = line.strip()
            if any(word in line.lower() for word in ['error', 'wrong', 'avoid', 'never', 'don\'t']):
                if len(line) > 10 and len(line) < 200:
                    errors.append(line)
        
        return errors[0] if errors else content[:100]
    
    def synthesize_deep_expertise(self, patterns):
        """Convert deep patterns into expert-level guidance"""
        
        expertise = []
        
        # Core rules (highest priority)
        if patterns["core_rules"]:
            expertise.append("CORE PRINCIPLES (always apply):")
            for rule in patterns["core_rules"][:3]:
                expertise.append(f"  → {rule}")
        
        # Context-specific guidance
        if patterns["context_rules"]:
            expertise.append("\nCONTEXT-AWARE DECISIONS:")
            for rule in patterns["context_rules"][:3]:
                expertise.append(f"  → {rule}")
        
        # Error prevention
        if patterns["error_patterns"]:
            expertise.append("\nAVOID THESE MISTAKES:")
            for error in patterns["error_patterns"][:2]:
                expertise.append(f"  → {error}")
        
        # Optimization insights
        if patterns["optimization_tips"]:
            expertise.append("\nOPTIMIZATION INSIGHTS:")
            for tip in patterns["optimization_tips"][:2]:
                expertise.append(f"  → {tip}")
        
        return "\n".join(expertise)
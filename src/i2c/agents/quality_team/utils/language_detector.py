from pathlib import Path
from typing import Dict, Any, List

class LanguageDetector:
    """
    Detects programming language and appropriate quality gates based on file extensions.
    """
    
    # Mapping of file extensions to languages
    EXTENSION_TO_LANGUAGE = {
        # Python
        '.py': 'python',
        
        # JavaScript/TypeScript
        '.js': 'javascript',
        '.jsx': 'javascript',
        '.ts': 'typescript',
        '.tsx': 'typescript',
        
        # Go
        '.go': 'go',
        
        # Java
        '.java': 'java',
        
        # C/C++
        '.c': 'c',
        '.cpp': 'cpp',
        '.h': 'c',
        '.hpp': 'cpp',
        
        # Ruby
        '.rb': 'ruby',
        
        # Others
        '.html': 'html',
        '.css': 'css',
        '.rs': 'rust',
        '.php': 'php',
        '.cs': 'csharp',
    }
    
    # Quality gates per language
    QUALITY_GATES = {
        'python': [
            'flake8',
            'black',
            'mypy',
            'pytest',
            'bandit'
        ],
        'javascript': [
            'eslint'
        ],
        'typescript': [
            'eslint',
            'tsc'
        ],
        'go': [
            'govet'
        ],
        'java': [
            'checkstyle'
        ],
        # Add more languages and their quality gates as needed
    }
    
    @classmethod
    def detect_language(cls, file_path: str) -> str:
        """
        Detect the programming language based on file extension.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Language identifier string or 'unknown'
        """
        ext = Path(file_path).suffix.lower()
        return cls.EXTENSION_TO_LANGUAGE.get(ext, 'unknown')
    
    @classmethod
    def get_quality_gates(cls, file_path: str) -> List[str]:
        """
        Get the appropriate quality gates for a file based on its language.
        
        Args:
            file_path: Path to the file
            
        Returns:
            List of quality gate identifiers
        """
        language = cls.detect_language(file_path)
        return cls.QUALITY_GATES.get(language, [])
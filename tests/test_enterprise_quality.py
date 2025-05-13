import unittest
from pathlib import Path
import tempfile
import os
import asyncio
from typing import Dict

# Import modules to test
from i2c.agents.quality_team.enterprise_static_analyzer import enterprise_static_analyzer
from i2c.agents.quality_team.quality_team import QualityLeadAgent

class TestEnterpriseQualityGates(unittest.TestCase):
    """Test the enterprise quality gates functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create temporary directory for test files
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project_path = Path(self.temp_dir.name)
        
        # Create the QualityLeadAgent
        self.quality_lead = QualityLeadAgent()
        
        # Sample files with intentional issues for each language
        self.python_file = """
import os, sys, math  # flake8: multiple imports on one line
def hello():
  print("world")  # black: incorrect indentation
x = "test"  # mypy: missing type annotation
assert True  # pytest will pass this
password = "hardcoded_password"  # bandit will flag this
"""
        
        self.javascript_file = """
const x = 10
console.log(x)  // eslint: missing semicolon
const unused = 20  // eslint: unused variable
"""
        
        self.typescript_file = """
const x: number = 10;
const y: string = 100;  // tsc: Type error
console.log(x);
"""
        
        self.go_file = """
package main

import "fmt"

func main() {
    var x int
    fmt.Println("Hello, World!")  // No issues, but govet will run
}
"""
        
        self.java_file = """
public class Test {
  public static void main(String[] args) {
    System.out.println("Hello World!");  // checkstyle: indentation issues
  }
}
"""
    
    def tearDown(self):
        """Clean up test fixtures"""
        self.temp_dir.cleanup()
    
    def write_files(self) -> Dict[str, str]:
        """Write test files to disk and return the file mapping"""
        files = {
            "test_python.py": self.python_file,
            "test_javascript.js": self.javascript_file,
            "test_typescript.ts": self.typescript_file,
            "test_go.go": self.go_file,
            "Test.java": self.java_file
        }
        
        # Write each file
        for filename, content in files.items():
            file_path = self.project_path / filename
            with open(file_path, 'w') as f:
                f.write(content)
        
        return files
    
    def test_enterprise_static_analyzer_direct(self):
        """Test the EnterpriseStaticAnalyzer directly"""
        # Create the files mapping
        files = {
            "test_python.py": self.python_file,
            "test_javascript.js": self.javascript_file,
            "test_typescript.ts": self.typescript_file,
            "test_go.go": self.go_file,
            "Test.java": self.java_file
        }
        
        # Test Python file with flake8 and black
        python_results = enterprise_static_analyzer.analyze_files(
            {"test_python.py": self.python_file}, 
            ["flake8", "black"]
        )
        
        # Check that analysis ran and found issues
        self.assertFalse(python_results["passed"], "Python analysis should fail due to issues")
        self.assertGreater(python_results["summary"]["total_issues"], 0, 
                          "Python analysis should find issues")
        
        # Test JavaScript file with eslint
        js_results = enterprise_static_analyzer.analyze_files(
            {"test_javascript.js": self.javascript_file}, 
            ["eslint"]
        )
        
        # We might not have eslint installed in the test environment,
        # so just check that the analysis ran
        self.assertIn("test_javascript.js", js_results["issues"], 
                     "JavaScript file should be analyzed")
        
        # Test all files with all quality gates
        all_results = enterprise_static_analyzer.analyze_files(files)
        
        # Check that analysis ran for all files
        self.assertEqual(len(all_results["issues"]), len(files),
                        "All files should be analyzed")
    
    def test_quality_lead_agent(self):
        """Test the QualityLeadAgent integration"""
        # Write files to disk
        files = self.write_files()
        
        # Run validation through the QualityLeadAgent
        loop = asyncio.get_event_loop()
        
        # Test Python files only
        python_results = loop.run_until_complete(
            self.quality_lead.validate_changes(
                self.project_path,
                {"test_python.py": self.python_file},
                ["python"]  # Use the Python preset
            )
        )
        
        # Check enterprise results
        self.assertIn("enterprise_results", python_results, 
                     "Enterprise quality gates should run")
        
        # Test all files with all gates
        modified_files = {}
        for filename, content in files.items():
            file_path = self.project_path / filename
            with open(file_path, 'r') as f:
                modified_files[str(file_path)] = f.read()
        
        all_results = loop.run_until_complete(
            self.quality_lead.validate_changes(
                self.project_path,
                modified_files,
                ["all"]  # Use the all preset
            )
        )
        
        # Check that validation ran
        self.assertFalse(all_results.get("passed", True), 
                        "Validation should fail due to issues")
    
    def test_individual_quality_gates(self):
        """Test each quality gate individually"""
        test_cases = [
            ("flake8", "test_python.py", self.python_file),
            ("black", "test_python.py", self.python_file),
            ("mypy", "test_python.py", self.python_file),
            ("pytest", "test_python.py", self.python_file),
            ("bandit", "test_python.py", self.python_file),
            ("eslint", "test_javascript.js", self.javascript_file),
            ("tsc", "test_typescript.ts", self.typescript_file),
            ("govet", "test_go.go", self.go_file),
            ("checkstyle", "Test.java", self.java_file)
        ]
        
        for gate, filename, content in test_cases:
            # Test each gate individually
            result = enterprise_static_analyzer.analyze_files(
                {filename: content}, 
                [gate]
            )
            
            # Check that analysis ran
            self.assertIn(filename, result["issues"], 
                         f"{gate} should analyze {filename}")
            
            # Check that the gate results exist
            file_results = result["issues"].get(filename, {})
            self.assertIn(gate, file_results, 
                         f"{gate} results should be present for {filename}")


if __name__ == "__main__":
    unittest.main()
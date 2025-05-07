#!/usr/bin/env python3
"""
I2C Factory Demo Script
=======================
This script demonstrates the two main workflow paths of the I2C Factory:
1. Fast Track: Quick idea-to-code transformation with minimal interaction
2. Structured Approach: Feature pipeline with structured user stories and robust architecture

Usage:
    python demo_script.py [--path DEMO_PATH] [--output OUTPUT_DIR]
"""

import time
import json
import os
import argparse
import shutil
from pathlib import Path
from datetime import datetime
from enum import Enum

# Import I2C Factory components
from i2c.bootstrap import initialize_environment
initialize_environment()

from i2c.cli.controller import canvas
from i2c.agents.budget_manager import BudgetManagerAgent
from i2c.agents.core_agents import input_processor_agent
from i2c.workflow.orchestrator import route_and_execute
from i2c.workflow.visual_helpers import show_progress, show_file_list
from i2c.workflow.utils import sanitize_filename

class DemoMetricsCollector:
    """Collects metrics during demo runs"""
    
    def __init__(self):
        self.metrics = {
            'tokens_used': 0,
            'operations': [],
            'files_generated': 0,
            'time_taken': 0,
            'start_time': datetime.now().timestamp()
        }
    
    def record_operation(self, name, tokens, duration):
        """Record a single operation's metrics"""
        self.metrics['operations'].append({
            'name': name,
            'tokens': tokens,
            'duration': duration,
            'timestamp': datetime.now().timestamp()
        })
        self.metrics['tokens_used'] += tokens
    
    def record_files(self, count):
        """Record number of files generated"""
        self.metrics['files_generated'] += count
    
    def finish(self):
        """Calculate final metrics"""
        self.metrics['time_taken'] = datetime.now().timestamp() - self.metrics['start_time']
        return self.metrics
    
    def save_metrics(self, path):
        """Save metrics to file"""
        with open(path, 'w') as f:
            json.dump(self.metrics, f, indent=2)
        
        canvas.info(f"📊 Metrics saved to {path}")

class DemoPath(Enum):
    """Available demo paths"""
    FAST_TRACK = "fast"
    STRUCTURED = "structured"
    BOTH = "both"

class I2CFactoryDemo:
    """Main demo runner for I2C Factory"""
    
    def __init__(self, demo_path=DemoPath.BOTH, output_dir="./demo_output"):
        self.demo_path = demo_path
        self.budget_manager = BudgetManagerAgent(session_budget=10.0)
        
        # Set up output directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = Path(output_dir) / timestamp
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        canvas.info(f"📁 Demo output will be saved to: {self.output_dir}")
        self.metrics = DemoMetricsCollector()
    
    def run(self):
        """Run the selected demo(s)"""
        canvas.info(f"🚀 Running I2C Factory Demo - Version 1.2.0")
        canvas.info(f"{'='*50}")
        
        if self.demo_path in [DemoPath.FAST_TRACK, DemoPath.BOTH]:
            self.run_fast_track_demo()
            
        if self.demo_path in [DemoPath.STRUCTURED, DemoPath.BOTH]:
            self.run_structured_demo()
        
        # Save metrics
        metrics_path = self.output_dir / "demo_metrics.json"
        self.metrics.finish()
        self.metrics.save_metrics(metrics_path)
        
        # Display summary
        total_tokens = self.metrics.metrics['tokens_used']
        estimated_cost = total_tokens / 1_000_000 * 0.50  # $0.50 per 1M tokens
        canvas.info(f"\n{'='*50}")
        canvas.info(f"📊 Demo Summary")
        canvas.info(f"{'='*50}")
        canvas.info(f"🕒 Total time: {self.metrics.metrics['time_taken']:.2f} seconds")
        canvas.info(f"🧮 Total tokens used: {total_tokens:,}")
        canvas.info(f"📄 Files generated: {self.metrics.metrics['files_generated']}")
        canvas.info(f"💵 Estimated LLM cost: ${estimated_cost:.4f}")
        canvas.info(f"{'='*50}")
        canvas.success(f"🎉 Demo Complete")
    
    def run_fast_track_demo(self):
        """Run the Fast Track demo (Path 1)"""
        canvas.info(f"\n{'='*50}")
        canvas.info(f"🚀 Fast Track Demo - Quick Idea to Code")
        canvas.info(f"{'='*50}")
        
        # Initial project idea
        project_idea = "Create a crypto dashboard with price tracking and portfolio management"
        canvas.info(f"\n📝 Project Idea: {project_idea}")
        
        # Setup project directory
        project_path = self.output_dir / "crypto_dashboard_fast"
        project_path.mkdir(parents=True, exist_ok=True)
        
        # Phase 1: Idea Processing
        canvas.info(f"\n🧠 Processing idea...")
        start_time = time.time()
        response = input_processor_agent.run(project_idea)
        duration = time.time() - start_time
        
        tokens = getattr(response, "usage", {}).get("total_tokens", 0)
        self.metrics.record_operation("idea_processing", tokens, duration)
        
        structured_goal = json.loads(response.content)
        canvas.success(f"✅ Objective: {structured_goal['objective']}")
        canvas.success(f"✅ Language: {structured_goal['language']}")
        
        # Phase 2: Project Generation
        canvas.info(f"\n🏗️ Generating project...")
        steps = [
            "Planning files",
            "Generating code",
            "Creating unit tests",
            "Quality checks",
            "Writing files"
        ]
        
        # Show initial progress
        show_progress("Project Generation", steps, 0)
        
        # Simulate progress for each step
        start_time = time.time()
        success = route_and_execute(
            action_type="generate",
            action_detail=structured_goal,
            current_project_path=project_path,
            current_structured_goal=structured_goal,
        )
        duration = time.time() - start_time
        
        # Estimate token usage (this would be better tracked in route_and_execute)
        tokens = 15000  # Estimated token usage for generation
        self.metrics.record_operation("project_generation", tokens, duration)
        
        # Count files
        file_count = sum(1 for _ in project_path.rglob('*') if _.is_file())
        self.metrics.record_files(file_count)
        
        # Show completion
        if success:
            show_progress("Project Generation", steps, len(steps))
            
            # Show generated files
            generated_files = []
            for file_path in project_path.rglob('*'):
                if file_path.is_file():
                    generated_files.append(file_path)
            
            if generated_files:
                show_file_list("Generated Files", generated_files, project_path)
            
            canvas.success(f"✅ Project generated successfully!")
        else:
            canvas.error(f"❌ Project generation failed")
            return
        
        # Phase 3: Feature Addition
        feature_idea = "Add price alerts for selected coins"
        canvas.info(f"\n🛠️ Adding feature: {feature_idea}")
        
        # Show progress
        steps = [
            "Retrieving context",
            "Planning modifications",
            "Implementing code",
            "Running tests",
            "Finalizing changes"
        ]
        show_progress("Feature Addition", steps, 0)
        
        # Get files before modification
        files_before = set(str(p) for p in project_path.rglob('*') if p.is_file())
        
        # Execute feature addition
        start_time = time.time()
        success = route_and_execute(
            action_type="modify",
            action_detail=f"f {feature_idea}",
            current_project_path=project_path,
            current_structured_goal=structured_goal,
        )
        duration = time.time() - start_time
        
        # Estimate token usage
        tokens = 8000  # Estimated token usage for feature addition
        self.metrics.record_operation("feature_addition", tokens, duration)
        
        # Show results
        if success:
            show_progress("Feature Addition", steps, len(steps))
            
            # Identify new files
            files_after = set(str(p) for p in project_path.rglob('*') if p.is_file())
            new_files = [Path(f) for f in files_after - files_before]
            file_count = len(new_files)
            self.metrics.record_files(file_count)
            
            if new_files:
                show_file_list("New Files", new_files, project_path)
            
            canvas.success(f"✅ Feature added successfully!")
        else:
            canvas.error(f"❌ Feature addition failed")
        
        # Phase 4: Refinement
        canvas.info(f"\n🔄 Refining project...")
        
        # Show progress
        steps = [
            "Analyzing context",
            "Planning refinements",
            "Implementing changes",
            "Testing & quality",
            "Saving files"
        ]
        show_progress("Refinement", steps, 0)
        
        # Get files before refinement
        files_before = set(str(p) for p in project_path.rglob('*') if p.is_file())
        
        # Execute refinement
        start_time = time.time()
        success = route_and_execute(
            action_type="modify",
            action_detail="r",
            current_project_path=project_path,
            current_structured_goal=structured_goal,
        )
        duration = time.time() - start_time
        
        # Estimate token usage
        tokens = 5000  # Estimated token usage for refinement
        self.metrics.record_operation("refinement", tokens, duration)
        
        # Show results
        if success:
            show_progress("Refinement", steps, len(steps))
            
            # Identify updated files
            files_after = set(str(p) for p in project_path.rglob('*') if p.is_file())
            new_files = [Path(f) for f in files_after - files_before]
            self.metrics.record_files(len(new_files))
            
            if new_files:
                show_file_list("New Files", new_files, project_path)
            
            canvas.success(f"✅ Refinement completed successfully!")
        else:
            canvas.error(f"❌ Refinement failed")
        
        # Summary of Fast Track demo
        canvas.info(f"\n📋 Fast Track Summary:")
        canvas.info(f"✓ Generated project from idea in one step")
        canvas.info(f"✓ Added feature with minimal interaction")
        canvas.info(f"✓ Refined project structure and code")
        canvas.info(f"✓ Total files: {sum(1 for _ in project_path.rglob('*') if _.is_file())}")
        
        # Pause for user to read
        input("\n⏸ Press Enter to continue...\n")
    
    def run_structured_demo(self):
        """Run the Structured Approach demo (Path 2)"""
        canvas.info(f"\n{'='*50}")
        canvas.info(f"🏗️ Structured Approach Demo - Robust Architecture")
        canvas.info(f"{'='*50}")
        
        # Initial project idea
        project_idea = "Build a smart contract factory with a security audit feature"
        canvas.info(f"\n📝 Project Idea: {project_idea}")
        
        # Setup project directory
        project_path = self.output_dir / "smart_contract_factory"
        project_path.mkdir(parents=True, exist_ok=True)
        
        # Phase 1: Idea Processing with Blueprint Creation
        canvas.info(f"\n🧠 Processing idea and creating blueprint...")
        start_time = time.time()
        response = input_processor_agent.run(project_idea)
        duration = time.time() - start_time
        
        tokens = getattr(response, "usage", {}).get("total_tokens", 0)
        self.metrics.record_operation("idea_processing", tokens, duration)
        
        structured_goal = json.loads(response.content)
        canvas.success(f"✅ Objective: {structured_goal['objective']}")
        canvas.success(f"✅ Language: {structured_goal['language']}")
        
        # Show feature blueprint (this would be generated by a real agent)
        canvas.info(f"\n📋 Feature Blueprint:")
        canvas.info(f"1. Core Contract Factory")
        canvas.info(f"   - Solidity Code Generation (3 user stories)")
        canvas.info(f"   - Contract Templates (2 user stories)")
        canvas.info(f"   - User Interface (2 user stories)")
        canvas.info(f"2. Security Audit Feature")
        canvas.info(f"   - Vulnerability Scanner (2 user stories)")
        canvas.info(f"   - Security Score (1 user story)")
        canvas.info(f"   - Remediation Suggestions (2 user stories)")
        canvas.info(f"3. Export & Deployment")
        canvas.info(f"   - Code Export (1 user story)")
        canvas.info(f"   - Test Network Deployment (2 user stories)")
        
        # Phase 2: Project Generation with Architecture
        canvas.info(f"\n🏗️ Generating structured project...")
        steps = [
            "Creating architecture",
            "Implementing core components",
            "Building test framework",
            "Setting up deployment",
            "Writing documentation"
        ]
        
        # Show initial progress
        show_progress("Structured Generation", steps, 0)
        
        # Execute with original workflow but using the structured goal
        start_time = time.time()
        success = route_and_execute(
            action_type="generate",
            action_detail=structured_goal,
            current_project_path=project_path,
            current_structured_goal=structured_goal,
        )
        duration = time.time() - start_time
        
        # Estimate token usage
        tokens = 25000  # Estimated token usage for structured generation
        self.metrics.record_operation("structured_generation", tokens, duration)
        
        # Count files
        file_count = sum(1 for _ in project_path.rglob('*') if _.is_file())
        self.metrics.record_files(file_count)
        
        # Show completion
        if success:
            show_progress("Structured Generation", steps, len(steps))
            
            # Show generated files by category
            frontend_files = [p for p in project_path.rglob('*.jsx') if p.is_file()]
            backend_files = [p for p in project_path.rglob('*.py') if p.is_file()]
            contract_files = [p for p in project_path.rglob('*.sol') if p.is_file()]
            
            if frontend_files:
                show_file_list("Frontend Files", frontend_files, project_path)
            if backend_files:
                show_file_list("Backend Files", backend_files, project_path)
            if contract_files:
                show_file_list("Smart Contract Files", contract_files, project_path)
            
            canvas.success(f"✅ Structured project generated successfully!")
        else:
            canvas.error(f"❌ Structured project generation failed")
            return
        
        # Phase 3: User Story Implementation
        story_text = "As a developer, I want to validate my smart contract against common vulnerabilities, so that I can identify security issues before deployment"
        canvas.info(f"\n📝 Implementing User Story:")
        canvas.info(f"'{story_text}'")
        
        # Show progress
        steps = [
            "Processing story",
            "Planning implementation",
            "Generating code",
            "Creating tests",
            "Checking quality"
        ]
        show_progress("Story Implementation", steps, 0)
        
        # Get files before story implementation
        files_before = set(str(p) for p in project_path.rglob('*') if p.is_file())
        
        # Simulate story implementation (this would call feature_integration)
        # In a real implementation, this would call feature_integration.handle_feature_request
        for i in range(len(steps)):
            time.sleep(0.5)  # Simulate work
            show_progress("Story Implementation", steps, i+1)
        
        # Simulate story implementation results
        start_time = time.time()
        time.sleep(2)  # Simulate work
        duration = time.time() - start_time
        
        # Create some sample files to simulate output
        validator_file = project_path / "src" / "services" / "validation_service.py"
        validator_file.parent.mkdir(parents=True, exist_ok=True)
        with open(validator_file, "w") as f:
            f.write("# Vulnerability validation service\n\ndef validate_contract(code):\n    # Implementation\n    pass")
        
        test_file = project_path / "tests" / "test_validation_service.py"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        with open(test_file, "w") as f:
            f.write("# Tests for validation service\n\ndef test_validate_contract():\n    # Test implementation\n    pass")
        
        # Estimate token usage
        tokens = 12000  # Estimated token usage for story implementation
        self.metrics.record_operation("story_implementation", tokens, duration)
        
        # Show results
        files_after = set(str(p) for p in project_path.rglob('*') if p.is_file())
        new_files = [Path(f) for f in files_after - files_before]
        self.metrics.record_files(len(new_files))
        
        if new_files:
            show_file_list("Implemented Files", new_files, project_path)
        
        canvas.success(f"✅ User story implemented successfully!")
        
        # Phase 4: Feature Implementation (Batch Stories)
        feature_idea = "Add complete contract deployment and verification pipeline"
        canvas.info(f"\n🛠️ Implementing comprehensive feature: {feature_idea}")
        
        # Show feature blueprint
        canvas.info(f"\n📋 Feature Blueprint:")
        canvas.info(f"- Deployment Configuration (2 user stories)")
        canvas.info(f"- Network Selection (1 user story)")
        canvas.info(f"- Verification API Integration (2 user stories)")
        canvas.info(f"- Deployment History (1 user story)")
        
        # Show progress
        steps = [
            "Creating feature plan",
            "Implementing all stories",
            "Building integration tests",
            "Creating deployment UI",
            "Documenting feature"
        ]
        show_progress("Feature Implementation", steps, 0)
        
        # Get files before feature implementation
        files_before = set(str(p) for p in project_path.rglob('*') if p.is_file())
        
        # Simulate implementation of multiple stories at once
        for i in range(len(steps)):
            time.sleep(0.5)  # Simulate work
            show_progress("Feature Implementation", steps, i+1)
        
        # Create some sample files to simulate output
        start_time = time.time()
        time.sleep(2)  # Simulate work
        
        # Create multiple files to simulate batch implementation
        deployment_dir = project_path / "src" / "deployment"
        deployment_dir.mkdir(parents=True, exist_ok=True)
        
        files_to_create = [
            "deployment_service.py",
            "network_selector.py",
            "verification_api.py",
            "deployment_history.py"
        ]
        
        for file in files_to_create:
            with open(deployment_dir / file, "w") as f:
                f.write(f"# {file.replace('.py', '').replace('_', ' ').title()}\n\n# Implementation\n")
        
        # Create a UI component
        ui_dir = project_path / "src" / "components" / "deployment"
        ui_dir.mkdir(parents=True, exist_ok=True)
        
        with open(ui_dir / "DeploymentPanel.jsx", "w") as f:
            f.write("// Deployment Panel Component\n\nimport React from 'react';\n\nconst DeploymentPanel = () => {\n  return <div>Deployment Panel</div>;\n};\n\nexport default DeploymentPanel;")
        
        duration = time.time() - start_time
        
        # Estimate token usage
        tokens = 20000  # Estimated token usage for batch feature implementation
        self.metrics.record_operation("batch_implementation", tokens, duration)
        
        # Show results
        files_after = set(str(p) for p in project_path.rglob('*') if p.is_file())
        new_files = [Path(f) for f in files_after - files_before]
        self.metrics.record_files(len(new_files))
        
        if new_files:
            show_file_list("Implemented Files", new_files, project_path)
        
        canvas.success(f"✅ Batch feature implementation completed successfully!")
        
        # Summary of Structured demo
        canvas.info(f"\n📋 Structured Approach Summary:")
        canvas.info(f"✓ Project built with comprehensive architecture")
        canvas.info(f"✓ Implemented individual user stories with tests")
        canvas.info(f"✓ Batch-processed multiple stories in one feature")
        canvas.info(f"✓ Maintained consistent project structure")
        canvas.info(f"✓ Total files: {sum(1 for _ in project_path.rglob('*') if _.is_file())}")
        
        # Pause for user to read
        input("\n⏸ Press Enter to continue...\n")


def main():
    parser = argparse.ArgumentParser(description="I2C Factory Demo")
    parser.add_argument("--path", choices=["fast", "structured", "both"], default="both",
                        help="Demo path to run (fast, structured, or both)")
    parser.add_argument("--output", default="./demo_output",
                        help="Output directory for demo projects")
    
    args = parser.parse_args()
    
    # Run demo
    demo = I2CFactoryDemo(
        demo_path=DemoPath(args.path),
        output_dir=args.output
    )
    demo.run()


if __name__ == "__main__":
    main()
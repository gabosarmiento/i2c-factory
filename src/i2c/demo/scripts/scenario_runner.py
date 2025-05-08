#!/usr/bin/env python3
"""
I2C Factory Scenario Runner with Knowledge Management

This script loads and executes scenario JSON files for the I2C Factory,
automating the demo or batch processing workflow. It supports adding
documentation through the knowledge management interface.

Usage:
    python scenario_runner.py path/to/scenario.json [--i2c-path PATH]
"""
from i2c.bootstrap import initialize_environment
initialize_environment()

import json
import time
import sys
import os
import subprocess
import tempfile
from pathlib import Path
import argparse
import threading
import queue

# Colors for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_header(text):
    """Print a formatted header text"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(60)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 60}{Colors.ENDC}\n")

def print_step(text):
    """Print a formatted step text"""
    print(f"{Colors.GREEN}➤ {text}{Colors.ENDC}")

def print_narration(text):
    """Print a formatted narration text"""
    print(f"\n{Colors.BLUE}{Colors.BOLD}🎬 {text}{Colors.ENDC}\n")

def print_error(text):
    """Print a formatted error text"""
    print(f"{Colors.RED}❌ ERROR: {text}{Colors.ENDC}")

def print_warning(text):
    """Print a formatted warning text"""
    print(f"{Colors.YELLOW}⚠️ WARNING: {text}{Colors.ENDC}")

def read_scenario_file(file_path):
    """Read and parse a scenario JSON file"""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print_error(f"Invalid JSON in scenario file: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print_error(f"Scenario file not found: {file_path}")
        sys.exit(1)
    except Exception as e:
        print_error(f"Error reading scenario file: {e}")
        sys.exit(1)

def find_i2c_executable():
    """Try to find the I2C Factory executable in common locations"""
    # Look in current directory and parent directories
    current_dir = Path.cwd()
    
    # Check for main.py in src/i2c or similar patterns
    patterns = [
        current_dir / "src" / "i2c" / "main.py",
        current_dir / "i2c" / "main.py",
        current_dir / "main.py",
        current_dir.parent / "src" / "i2c" / "main.py",
        current_dir.parent / "i2c" / "main.py",
    ]
    
    for pattern in patterns:
        if pattern.exists():
            return str(pattern)
    
    # If we couldn't find it, return None
    return None

def run_i2c_factory_with_input(input_queue, i2c_path=None):
    """
    Run the I2C Factory in a subprocess and feed it inputs from the queue
    
    Args:
        input_queue: Queue containing inputs to send to the I2C Factory
        i2c_path: Path to the I2C Factory main script (optional)
    """
    # Find the I2C Factory executable if path not provided
    if not i2c_path:
        i2c_path = find_i2c_executable()
        if not i2c_path:
            print_error("Could not find I2C Factory executable. Please provide the path with --i2c-path.")
            sys.exit(1)
    
    print_step(f"Starting I2C Factory from: {i2c_path}")
    
    # Build the command to run the I2C Factory
    if i2c_path.endswith(".py"):
        # It's a Python file, run with Python
        cmd = ["python", i2c_path]
    else:
        # It might be a directory or executable
        cmd = [i2c_path]
    
    # Start the I2C Factory process
    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )
    
    # Thread to handle reading stdout and detecting prompts
    def read_output():
        while True:
            line = process.stdout.readline()
            if not line:
                break
            # Echo the output
            print(line.rstrip())
            
            # If we detect any prompt, get and send the next input
            prompt_markers = ["🎯", "Select option", "Enter path", "Enter directory", "Press Enter"]
            if any(marker in line for marker in prompt_markers):
                try:
                    next_input = input_queue.get(block=False)
                    print(f"{Colors.YELLOW}➤ Sending: {next_input}{Colors.ENDC}")
                    process.stdin.write(next_input + "\n")
                    process.stdin.flush()
                except queue.Empty:
                    # No more inputs, let the user take over
                    print_warning("Scenario completed. Handing control to user...")
                    # Send control to the user for manual input
                    while True:
                        try:
                            user_input = input()
                            process.stdin.write(user_input + "\n")
                            process.stdin.flush()
                        except (EOFError, KeyboardInterrupt):
                            process.terminate()
                            return
    
    # Start the output reading thread
    output_thread = threading.Thread(target=read_output, daemon=True)
    output_thread.start()
    
    # Wait for the process to finish
    try:
        process.wait()
    except KeyboardInterrupt:
        print_warning("Interrupted by user. Terminating...")
        process.terminate()
    
    # Check for errors
    stderr = process.stderr.read()
    if stderr:
        print_error(f"I2C Factory errors:\n{stderr}")

def process_knowledge_step(step, input_queue):
    """
    Process a knowledge step to add documentation
    
    Args:
        step: The knowledge step configuration
        input_queue: Queue for CLI inputs
    """
    doc_path = step.get("doc_path", "")
    doc_type = step.get("doc_type", "API Documentation")
    framework = step.get("framework", "")
    version = step.get("version", "")
    
    if not doc_path:
        print_warning("Knowledge step missing doc_path. Skipping...")
        return
    
    # Navigate to knowledge management
    input_queue.put("k")
    
    # Select "Add documentation file" option
    input_queue.put("1")
    
    # Enter the documentation file path
    input_queue.put(doc_path)
    
    # Select document type (using the type provided or default)
    # This assumes the CLI will present numeric options for document types
    # We're adding extra inputs to handle the selection menu
    input_queue.put(doc_type)
    
    # Enter framework info
    input_queue.put(framework)
    
    # Enter version info
    input_queue.put(version)
    
    # Return to main menu (after processing completes)
    input_queue.put("6")

def process_knowledge_folder_step(step, input_queue):
    """
    Process a knowledge_folder step to add a directory of documentation
    
    Args:
        step: The knowledge_folder step configuration
        input_queue: Queue for CLI inputs
    """
    folder_path = step.get("folder_path", "")
    doc_type = step.get("doc_type", "API Documentation")
    framework = step.get("framework", "")
    version = step.get("version", "")
    recursive = step.get("recursive", True)
    
    if not folder_path:
        print_warning("Knowledge folder step missing folder_path. Skipping...")
        return
    
    # Navigate to knowledge management
    input_queue.put("k")
    
    # Select "Add documentation folder" option
    input_queue.put("2")
    
    # Enter the documentation folder path
    input_queue.put(folder_path)
    
    # Select recursive option
    input_queue.put("y" if recursive else "n")
    
    # Select document type
    input_queue.put(doc_type)
    
    # Enter framework info
    input_queue.put(framework)
    
    # Enter version info
    input_queue.put(version)
    
    # Return to main menu (after processing completes)
    input_queue.put("6")

def process_scenario(scenario, project_name=None, i2c_path=None):
    """
    Process a scenario step by step
    
    Args:
        scenario: List of scenario steps
        project_name: Optional custom project name
        i2c_path: Path to the I2C Factory main script
    """
    # Queue to hold inputs for the I2C Factory
    input_queue = queue.Queue()
    
    # Process each step in the scenario
    for i, step in enumerate(scenario):
        step_type = step.get("type")
        step_name = step.get("name", f"Step {i+1}")
        
        print_step(f"Processing step {i+1}/{len(scenario)}: {step_name}")
        
        if step_type == "narration":
            # Display narration with optional pause
            message = step.get("message", "")
            print_narration(message)
            pause_time = step.get("pause", 2)
            time.sleep(pause_time)
            
        elif step_type == "initial_generation":
            # Initial project generation
            prompt = step.get("prompt", "")
            if prompt:
                # Add the initial generation prompt to the input queue
                input_queue.put(prompt)
                
                # If project_name is provided, use it when prompted
                # Otherwise, use the default suggestion
                if project_name:
                    input_queue.put(project_name)
                else:
                    input_queue.put("")  # Empty string to use default name
                
        elif step_type == "modification":
            # Project modification
            prompt = step.get("prompt", "")
            if prompt:
                # Add the modification command to the input queue
                input_queue.put(f"f {prompt}")
        
        elif step_type == "refine":
            # Simple refinement
            input_queue.put("r")
            
        elif step_type == "knowledge":
            # Add documentation file to knowledge base
            process_knowledge_step(step, input_queue)
            
        elif step_type == "knowledge_folder":
            # Add documentation folder to knowledge base
            process_knowledge_folder_step(step, input_queue)
            
        elif step_type == "pause":
            # Manual pause - wait for user to press enter before continuing
            print_warning(f"Manual pause: {step.get('message', 'Paused')}")
            print_warning("Press Enter to continue...")
            input()
            
        else:
            print_warning(f"Unknown step type: {step_type}")
    
    # Run the I2C Factory with our prepared inputs
    run_i2c_factory_with_input(input_queue, i2c_path)

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="I2C Factory Scenario Runner")
    parser.add_argument("scenario_file", help="Path to scenario JSON file")
    parser.add_argument("--project-name", help="Custom project name (optional)")
    parser.add_argument("--i2c-path", help="Path to the I2C Factory main script or executable")
    
    args = parser.parse_args()
    
    print_header("I2C Factory Scenario Runner")
    
    # Read the scenario file
    scenario = read_scenario_file(args.scenario_file)
    
    # Process the scenario
    process_scenario(scenario, args.project_name, args.i2c_path)

if __name__ == "__main__":
    main()
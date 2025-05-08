#!/usr/bin/env python3
"""
I2C Factory Scenario Runner

This script loads and executes scenario JSON files for the I2C Factory,
automating the demo or batch processing workflow.

Usage:
    python scenario_runner.py src/i2c/demo/scenarios/scenario.json
"""

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

def run_i2c_factory_with_input(input_queue):
    """
    Run the I2C Factory in a subprocess and feed it inputs from the queue
    
    Args:
        input_queue: Queue containing inputs to send to the I2C Factory
    """
    # Start the I2C Factory process
    process = subprocess.Popen(
        ["python", "-m", "i2c.main"],  # Adjust this path as needed
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
            # If we detect the CLI prompt, get and send the next input
            if "🎯" in line:
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

def process_scenario(scenario, project_name=None):
    """
    Process a scenario step by step
    
    Args:
        scenario: List of scenario steps
        project_name: Optional custom project name
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
            
        else:
            print_warning(f"Unknown step type: {step_type}")
    
    # Run the I2C Factory with our prepared inputs
    run_i2c_factory_with_input(input_queue)

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="I2C Factory Scenario Runner")
    parser.add_argument("scenario_file", help="Path to scenario JSON file")
    parser.add_argument("--project-name", help="Custom project name (optional)")
    
    args = parser.parse_args()
    
    print_header("I2C Factory Scenario Runner")
    
    # Read the scenario file
    scenario = read_scenario_file(args.scenario_file)
    
    # Process the scenario
    process_scenario(scenario, args.project_name)

if __name__ == "__main__":
    main()
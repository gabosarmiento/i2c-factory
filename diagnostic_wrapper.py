# diagnostic_wrapper.py
"""
Diagnostic wrapper for tracking and analyzing API calls, prompt sizes, and timeouts.
This is a non-invasive tool that can be used alongside your existing code.
"""
# debug_knowledge_base.py
from i2c.bootstrap import initialize_environment
initialize_environment()

import time
import json
import os
import sys
import traceback
import functools
import threading
from datetime import datetime
from typing import Dict, Any, Optional, Callable, List
import inspect

# Set to True to enable detailed logging
DEBUG_MODE = True

# Global diagnostics state
diagnostics = {
    "api_calls": [],
    "prompt_sizes": [],
    "response_times": [],
    "timeouts": [],
    "errors": [],
    "memory_snapshots": [],
    "thread_counts": []
}

# File to save diagnostics to
DIAGNOSTICS_FILE = "i2c_diagnostics.json"

def log_diagnostic(category: str, data: Any):
    """Log diagnostic information to the global state."""
    timestamp = datetime.now().isoformat()
    entry = {
        "timestamp": timestamp,
        "category": category,
        "data": data
    }
    
    # Add to in-memory diagnostics
    if category in diagnostics:
        diagnostics[category].append(entry)
    else:
        diagnostics[category] = [entry]
    
    # Print if debug mode is enabled
    if DEBUG_MODE:
        print(f"[DIAGNOSTIC] {timestamp} | {category}: {json.dumps(data, default=str)[:200]}...")
    
    # Periodically save diagnostics to file
    if len(diagnostics["api_calls"]) % 5 == 0:
        save_diagnostics()

def save_diagnostics():
    """Save current diagnostics to file."""
    try:
        with open(DIAGNOSTICS_FILE, 'w') as f:
            json.dump(diagnostics, f, default=str, indent=2)
    except Exception as e:
        print(f"[ERROR] Failed to save diagnostics: {e}")

def take_memory_snapshot():
    """Take a snapshot of current memory usage."""
    try:
        import psutil
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        cpu_percent = process.cpu_percent(interval=0.1)
        
        snapshot = {
            "rss_mb": memory_info.rss / (1024 * 1024),  # RSS in MB
            "vms_mb": memory_info.vms / (1024 * 1024),  # VMS in MB
            "cpu_percent": cpu_percent,
            "thread_count": threading.active_count(),
            "open_files": len(process.open_files()),
            "connections": len(process.connections())
        }
        
        log_diagnostic("memory_snapshots", snapshot)
        return snapshot
    except ImportError:
        print("[WARNING] psutil not installed. Cannot take memory snapshot.")
        return {}
    except Exception as e:
        print(f"[ERROR] Failed to take memory snapshot: {e}")
        return {}

def estimate_token_size(text: str) -> int:
    """Roughly estimate the number of tokens in a string."""
    # Very rough approximation: ~4 characters per token for English text
    return len(text) // 4

def track_api_call(func):
    """
    Decorator to track API calls, their size, and response times.
    
    Usage:
    @track_api_call
    def your_api_function(param1, param2, ...):
        # function body
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Take memory snapshot before call
        take_memory_snapshot()
        
        # Log thread count
        log_diagnostic("thread_counts", {
            "active_threads": threading.active_count(),
            "thread_names": [t.name for t in threading.enumerate()]
        })
        
        # Extract function info
        func_name = func.__name__
        module_name = func.__module__
        
        # Try to extract argument info
        call_args = {}
        try:
            # Combine args and kwargs based on function signature
            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()
            
            # Convert args to dict for logging
            for param_name, param_value in bound_args.arguments.items():
                # Handle special case for first argument of methods (self/cls)
                if param_name in ('self', 'cls') and hasattr(param_value, '__class__'):
                    call_args[param_name] = param_value.__class__.__name__
                else:
                    # For large string values, just log the length
                    if isinstance(param_value, str) and len(param_value) > 500:
                        # Estimate token size
                        tokens = estimate_token_size(param_value)
                        
                        # Log token size for prompt-like parameters
                        if param_name.lower() in ('prompt', 'content', 'message', 'messages', 'input'):
                            log_diagnostic("prompt_sizes", {
                                "function": f"{module_name}.{func_name}",
                                "param": param_name,
                                "length": len(param_value),
                                "estimated_tokens": tokens
                            })
                        
                        # Store truncated version for logging
                        call_args[param_name] = f"<string of length {len(param_value)} (~{tokens} tokens)>"
                    elif isinstance(param_value, (dict, list)) and len(str(param_value)) > 500:
                        call_args[param_name] = f"<{type(param_value).__name__} of size {len(param_value)}>"
                    else:
                        call_args[param_name] = repr(param_value)
        except Exception as e:
            call_args = {"error_extracting_args": str(e)}
        
        # Log API call
        call_id = f"{int(time.time())}_{threading.get_ident()}"
        call_data = {
            "id": call_id,
            "function": f"{module_name}.{func_name}",
            "args": call_args,
            "thread_id": threading.get_ident(),
            "thread_name": threading.current_thread().name
        }
        log_diagnostic("api_calls", call_data)
        
        # Call the function and track time
        start_time = time.time()
        timeout_occurred = False
        error_occurred = False
        error_info = None
        
        try:
            result = func(*args, **kwargs)
            
            # Check for timeout in result
            if hasattr(result, 'get') and callable(result.get) and result.get('error', '').startswith('timeout'):
                timeout_occurred = True
        except Exception as e:
            error_occurred = True
            error_info = {
                "type": type(e).__name__,
                "message": str(e),
                "traceback": traceback.format_exc()
            }
            
            # Check if the error is a timeout
            if "timeout" in str(e).lower() or "disconnected" in str(e).lower():
                timeout_occurred = True
                
            # Re-raise the exception
            raise
        finally:
            # Calculate time taken
            end_time = time.time()
            duration = end_time - start_time
            
            # Log response time
            log_diagnostic("response_times", {
                "id": call_id,
                "function": f"{module_name}.{func_name}",
                "duration": duration,
                "timeout": timeout_occurred,
                "error": error_occurred
            })
            
            # Log timeout if it occurred
            if timeout_occurred:
                log_diagnostic("timeouts", {
                    "id": call_id,
                    "function": f"{module_name}.{func_name}",
                    "duration": duration,
                    "thread_id": threading.get_ident(),
                    "thread_name": threading.current_thread().name
                })
            
            # Log error if it occurred
            if error_occurred:
                log_diagnostic("errors", {
                    "id": call_id,
                    "function": f"{module_name}.{func_name}",
                    "error": error_info,
                    "thread_id": threading.get_ident(),
                    "thread_name": threading.current_thread().name
                })
            
            # Take memory snapshot after call
            take_memory_snapshot()
        
        if not error_occurred:
            return result
    
    return wrapper

# Integration helpers for common libraries

def patch_httpx():
    """Patch httpx library to track API calls."""
    try:
        import httpx
        original_send = httpx.Client.send
        
        @track_api_call
        def tracked_send(self, request, *args, **kwargs):
            return original_send(self, request, *args, **kwargs)
        
        httpx.Client.send = tracked_send
        print("[DIAGNOSTIC] Successfully patched httpx.Client.send")
    except ImportError:
        print("[DIAGNOSTIC] httpx not installed, skipping patch")
    except Exception as e:
        print(f"[DIAGNOSTIC] Failed to patch httpx: {e}")

def patch_agno_team():
    """Patch Agno's Team run method to track calls."""
    try:
        from agno.team.team import Team
        original_run = Team.run
        
        @track_api_call
        def tracked_run(self, message, *args, **kwargs):
            return original_run(self, message, *args, **kwargs)
        
        Team.run = tracked_run
        print("[DIAGNOSTIC] Successfully patched agno.team.Team.run")
    except ImportError:
        print("[DIAGNOSTIC] agno.team.Team not found, skipping patch")
    except Exception as e:
        print(f"[DIAGNOSTIC] Failed to patch agno.team.Team: {e}")

def patch_agno_agent():
    """Patch Agno's Agent predict method to track calls."""
    try:
        from agno.agent import Agent
        original_predict = Agent.predict
        
        @track_api_call
        def tracked_predict(self, messages, *args, **kwargs):
            return original_predict(self, messages, *args, **kwargs)
        
        Agent.predict = tracked_predict
        print("[DIAGNOSTIC] Successfully patched agno.agent.Agent.predict")
    except ImportError:
        print("[DIAGNOSTIC] agno.agent.Agent not found, skipping patch")
    except Exception as e:
        print(f"[DIAGNOSTIC] Failed to patch agno.agent.Agent: {e}")

def initialize_diagnostics():
    """
    Initialize diagnostic tracking.
    Call this at the start of your program.
    """
    print("[DIAGNOSTIC] Initializing diagnostic tracking")
    
    # Patch common libraries
    patch_httpx()
    patch_agno_team()
    patch_agno_agent()
    
    # Take initial memory snapshot
    take_memory_snapshot()
    
    # Log system info
    system_info = {
        "python_version": sys.version,
        "platform": sys.platform,
        "argv": sys.argv,
        "pid": os.getpid(),
        "processors": os.cpu_count()
    }
    log_diagnostic("system_info", system_info)
    
    print("[DIAGNOSTIC] Diagnostics initialized")
    return diagnostics

# Usage example:
"""
# At the start of your main program
from diagnostic_wrapper import initialize_diagnostics

# Initialize diagnostics
diagnostics = initialize_diagnostics()

# Run your normal code
# The diagnostics will track API calls, response times, etc.

# At the end of your program or when an error occurs
from diagnostic_wrapper import save_diagnostics
save_diagnostics()

# Or manually track a specific function
from diagnostic_wrapper import track_api_call

@track_api_call
def my_function():
    # Your code here
    pass
"""
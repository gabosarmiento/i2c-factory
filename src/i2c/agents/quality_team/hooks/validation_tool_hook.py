from typing import Any, Callable, Dict
from agno.utils.log import logger
import json
import hashlib

_validation_cache = {}

def validation_tool_hook(function_name: str, function_call: Callable, arguments: Dict[str, Any]) -> Any:
    """
    Hook that adds caching and logging to validation tool calls.
    
    Args:
        function_name: Name of the function being called
        function_call: The actual function to call
        arguments: Arguments to pass to the function
    
    Returns:
        The result of the function call, potentially from cache
    """
    # Create a cache key based on function name and arguments
    # Use a hash for file contents to avoid potential path issues
    serialized_args = json.dumps(arguments, sort_keys=True)
    key_hash = hashlib.md5(serialized_args.encode()).hexdigest()
    cache_key = f"{function_name}-{key_hash}"
    
    # Check if result is already cached
    if cache_key in _validation_cache:
        logger.info(f"[VALIDATION CACHE HIT] {function_name}")
        return _validation_cache[cache_key]
    
    # If not in cache, run the function
    logger.info(f"[VALIDATION TOOL] Running {function_name}")
    result = function_call(**arguments)
    
    # Cache the result
    _validation_cache[cache_key] = result
    
    # Log summary of the result (minimal)
    if isinstance(result, dict):
        status = "PASSED" if result.get("passed", False) else "FAILED"
        issue_count = len(result.get("issues", [])) if "issues" in result else "N/A"
        logger.info(f"[VALIDATION RESULT] {function_name} {status} with {issue_count} issues")
    
    return result
import warnings
from functools import wraps

def deprecated(reason="This function is deprecated"):
    """
    Mark a function as deprecated with a custom warning message.
    
    Usage:
        @deprecated("Use new_function() instead")
        def old_function():
            pass
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            warnings.warn(
                f"{func.__name__} is deprecated: {reason}",
                DeprecationWarning,
                stacklevel=2
            )
            return func(*args, **kwargs)
        return wrapper
    return decorator
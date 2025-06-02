import warnings
import pytest
from i2c.utils import deprecated

def test_deprecated_decorator():
    """Test that deprecated decorator shows warning"""
    
    @deprecated("Use new_function() instead")
    def old_function():
        return "old result"
    
    # Test that warning is raised
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")  # Catch all warnings
        
        result = old_function()
        
        # Check function still works
        assert result == "old result"
        
        # Check warning was raised
        assert len(w) == 1
        assert issubclass(w[0].category, DeprecationWarning)
        assert "old_function is deprecated" in str(w[0].message)
        assert "Use new_function() instead" in str(w[0].message)

def test_deprecated_with_args():
    """Test deprecated decorator with function arguments"""
    
    @deprecated("This is old")
    def add_numbers(a, b):
        return a + b
    
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        
        result = add_numbers(2, 3)
        
        assert result == 5
        assert len(w) == 1
        assert "add_numbers is deprecated" in str(w[0].message)
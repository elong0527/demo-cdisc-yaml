"""
Function registry for ADaM derivations.
Maps short function names to full module paths for cleaner specifications.
"""

from .get_bmi import get_bmi

# Function registry mapping short names to full paths
FUNCTION_REGISTRY = {
    # BMI calculation
    "get_bmi": "adamyaml.adam_derivation.functions.get_bmi.get_bmi",
    
    # Future functions can be added here
    # "calculate_age": "adamyaml.adam_derivation.functions.age.calculate_age",
    # "convert_units": "adamyaml.adam_derivation.functions.units.convert_units",
}

def get_function_path(short_name: str) -> str:
    """
    Get the full function path from a short name.
    
    Args:
        short_name: Short function name (e.g., "get_bmi")
        
    Returns:
        Full module path (e.g., "adamyaml.adam_derivation.functions.get_bmi.get_bmi")
        
    Raises:
        KeyError: If short name is not found in registry
    """
    if short_name not in FUNCTION_REGISTRY:
        raise KeyError(f"Function '{short_name}' not found in registry. Available: {list(FUNCTION_REGISTRY.keys())}")
    
    return FUNCTION_REGISTRY[short_name]

def list_available_functions() -> list[str]:
    """List all available short function names."""
    return list(FUNCTION_REGISTRY.keys())

def register_function(short_name: str, full_path: str) -> None:
    """
    Register a new function mapping.
    
    Args:
        short_name: Short name to use in specifications
        full_path: Full module path to the function
    """
    FUNCTION_REGISTRY[short_name] = full_path

# Export the main functions
__all__ = [
    "get_bmi",
    "get_function_path", 
    "list_available_functions",
    "register_function",
    "FUNCTION_REGISTRY"
]
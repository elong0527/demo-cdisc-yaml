"""Dynamic function derivation using Python's import system."""

from typing import Any
import polars as pl
import logging
import importlib
import sys
from pathlib import Path
from .base import BaseDerivation

logger = logging.getLogger(__name__)


class FunctionDerivation(BaseDerivation):
    """
    Dynamically loads and executes Python functions for derivations.
    
    Supports:
    - Module functions: "numpy.abs", "polars.col"
    - Local functions: "get_bmi" from functions.py or get_bmi.py
    """
    
    def derive(self) -> pl.Series:
        """Derive column using dynamically loaded function."""
        
        derivation = self.col_spec.get("derivation", {})
        function_name = derivation.get("function")
        
        if not function_name:
            raise ValueError("Function derivation requires 'function' field")
        
        # Extract arguments from specification
        args = self._extract_arguments(derivation)
        
        # Load and execute function
        try:
            func = self._load_function(function_name)
            result = func(**args)
            
            # Ensure result is a proper Series
            result = self._ensure_series(result)
            
            logger.info(f"Applied function {function_name}")
            return result
            
        except Exception as e:
            logger.error(f"Function {function_name} failed: {e}")
            return pl.Series([None] * self.target_df.height)
    
    def _extract_arguments(self, derivation: dict[str, Any]) -> dict[str, Any]:
        """Extract function arguments from derivation spec."""
        args = {}
        
        for key, value in derivation.items():
            if key == "function":
                continue
                
            # If value is a column name in target_df, use that column
            if isinstance(value, str) and value in self.target_df.columns:
                args[key] = self.target_df[value]
            else:
                args[key] = value
                
        return args
    
    def _load_function(self, function_name: str):
        """
        Load a function using Python's import system.
        
        Args:
            function_name: Can be:
                - Short name: "get_bmi" (looked up in registry)
                - Full path: "adamyaml.adam_derivation.functions.get_bmi.get_bmi"
                - Module function: "numpy.abs", "polars.col"
                - Local function: "get_bmi" (fallback)
            
        Returns:
            Callable function object
        """
        
        # First, try to resolve short names using the registry
        if "." not in function_name:
            try:
                from ..functions import get_function_path
                function_name = get_function_path(function_name)
                logger.debug(f"Resolved '{function_name}' from registry")
            except (ImportError, KeyError):
                # Fall back to local function loading
                return self._load_local_function(function_name)
        
        # Now load the function (either from registry or direct path)
        if "." in function_name:
            return self._load_module_function(function_name)
        else:
            return self._load_local_function(function_name)
    
    def _load_module_function(self, function_name: str):
        """Load function from an installed module."""
        parts = function_name.rsplit(".", 1)
        module_name = parts[0]
        func_name = parts[1]
        
        try:
            module = importlib.import_module(module_name)
            return getattr(module, func_name)
        except (ImportError, AttributeError) as e:
            raise ImportError(f"Cannot import {function_name}: {e}")
    
    def _load_local_function(self, function_name: str):
        """Load function from local Python files."""
        
        # Try functions.py first
        if self._try_load_from_functions_module(function_name):
            return getattr(sys.modules["functions"], function_name)
        
        # Try dedicated file (function_name.py)
        func = self._try_load_from_dedicated_file(function_name)
        if func:
            return func
            
        raise ImportError(
            f"Function '{function_name}' not found in functions.py "
            f"or {function_name}.py in current directory"
        )
    
    def _try_load_from_functions_module(self, function_name: str) -> bool:
        """Try to load function from functions.py."""
        
        # Check if already loaded
        if "functions" in sys.modules:
            return hasattr(sys.modules["functions"], function_name)
        
        # Try to load functions.py
        functions_path = Path.cwd() / "functions.py"
        if not functions_path.exists():
            return False
            
        try:
            spec = importlib.util.spec_from_file_location("functions", functions_path)
            module = importlib.util.module_from_spec(spec)
            sys.modules["functions"] = module
            spec.loader.exec_module(module)
            return hasattr(module, function_name)
        except Exception as e:
            logger.debug(f"Failed to load functions.py: {e}")
            return False
    
    def _try_load_from_dedicated_file(self, function_name: str):
        """Try to load function from dedicated file."""
        
        func_file = Path.cwd() / f"{function_name}.py"
        if not func_file.exists():
            return None
            
        try:
            spec = importlib.util.spec_from_file_location(function_name, func_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return getattr(module, function_name)
        except Exception as e:
            logger.debug(f"Failed to load {function_name}.py: {e}")
            return None
    
    def _ensure_series(self, result: Any) -> pl.Series:
        """Convert result to a proper Polars Series with correct length."""
        
        # Already a Series with correct length
        if isinstance(result, pl.Series):
            if len(result) == self.target_df.height:
                return result
            elif len(result) == 1:
                # Broadcast single value
                return pl.Series([result[0]] * self.target_df.height)
            else:
                raise ValueError(
                    f"Function returned {len(result)} values, "
                    f"expected {self.target_df.height}"
                )
        
        # Convert iterables to Series
        if hasattr(result, '__iter__') and not isinstance(result, str):
            series = pl.Series(result)
            if len(series) == self.target_df.height:
                return series
            elif len(series) == 1:
                return pl.Series([series[0]] * self.target_df.height)
            else:
                raise ValueError(
                    f"Function returned {len(series)} values, "
                    f"expected {self.target_df.height}"
                )
        
        # Scalar value - broadcast to all rows
        return pl.Series([result] * self.target_df.height)
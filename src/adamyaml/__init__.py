"""
ADaM YAML Package - YAML-driven ADaM dataset generation

A comprehensive toolkit for CDISC ADaM dataset generation using YAML specifications.
"""

# Import main components for convenient access
from .adam_spec import AdamSpec, Column, merge_yaml, SchemaValidator
from .adam_derivation import AdamDerivation
from .adam_validation import DataValidator

__version__ = "0.2.0"
__all__ = [
    # Specification components
    "AdamSpec",
    "Column", 
    "merge_yaml",
    "SchemaValidator",
    # Derivation components
    "AdamDerivation",
    # Validation components
    "DataValidator",
]
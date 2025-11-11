"""
ADaM YAML Specification Module - Single Class Implementation

A minimal, easy-to-maintain module for handling hierarchical YAML specifications
for ADaM (Analysis Data Model) datasets following CDISC standards.
"""

from .adam_spec import AdamSpec, Column
from .merge_yaml import merge_yaml
from .schema_validator import SchemaValidator, ValidationResult

__version__ = "2.0.0"
__author__ = "ADaM YAML Team"

__all__ = [
    "AdamSpec",
    "Column",
    "merge_yaml",
    "SchemaValidator",
    "ValidationResult"
]
"""
ADaM Derivation Module

A modular framework for deriving ADaM datasets from SDTM data using YAML specifications.
Follows CDISC ADaM standards and supports configuration-driven derivations.
"""

from .engine import AdamDerivation

__version__ = "0.1.0"
__all__ = ["AdamDerivation"]
"""Minimal base class for derivations."""

from abc import ABC, abstractmethod
from typing import Any
import polars as pl


class BaseDerivation(ABC):
    """Simple abstract base for all derivations."""
    
    def __init__(self):
        self.col_spec: dict[str, Any] = {}
        self.source_data: dict[str, pl.DataFrame] = {}
        self.target_df: pl.DataFrame = pl.DataFrame()
    
    def setup(self, 
              col_spec: dict[str, Any], 
              source_data: dict[str, pl.DataFrame],
              target_df: pl.DataFrame) -> 'BaseDerivation':
        """
        Set up the derivation context.
        
        Args:
            col_spec: Column specification including derivation rules
            source_data: Dictionary of available source DataFrames
            target_df: Target DataFrame being built
            
        Returns:
            Self for chaining
        """
        self.col_spec = col_spec
        self.source_data = source_data
        self.target_df = target_df
        return self
    
    @abstractmethod
    def derive(self) -> pl.Series:
        """
        Derive a column based on the setup context.
        
        Returns:
            Series with derived values
        """
        pass
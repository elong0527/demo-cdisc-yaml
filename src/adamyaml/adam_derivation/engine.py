"""
Main derivation engine for ADaM dataset generation using Polars
"""

import polars as pl
from pathlib import Path
from typing import Any
import logging

from .loaders import SDTMLoader
from ..adam_spec import AdamSpec


class AdamDerivation:
    """
    Engine for deriving ADaM datasets from SDTM data using YAML specifications
    """
    
    def __init__(self, spec_path: str):
        self.spec = AdamSpec(spec_path)
        
        if self.spec._errors:
            raise ValueError(f"Specification errors: {self.spec._errors}")
        
        self.sdtm_loader = SDTMLoader(self.spec.sdtm_dir)
        self.logger = logging.getLogger(__name__)
        self.target_df = pl.DataFrame()
        self.source_data = {}
    
    def _build_keys(self) -> pl.DataFrame:
        """Build base dataset with key variables."""
        key_vars = self.spec.key
        self.logger.info(f"Building base dataset with key variables: {key_vars}")
        
        dependencies = self.spec.get_data_dependency()
        key_deps = [dep for dep in dependencies if dep['adam_variable'] in key_vars]
        
        source_dataset = key_deps[0]['sdtm_data']
        key_columns_map = {
            dep['adam_variable']: dep['sdtm_variable'] 
            for dep in key_deps
        }
        
        # Use already loaded renamed data (key variables are preserved)
        source_df = self.source_data[source_dataset]
        self.logger.info(f"Using source dataset {source_dataset}")
        
        # Key columns are preserved without renaming, so use original names
        columns_to_select = list(key_columns_map.values())
        base_df = source_df.select(columns_to_select)
        
        # Check for duplicates
        n_rows = base_df.height
        n_unique = base_df.unique(subset=key_vars).height
        
        if n_rows != n_unique:
            n_duplicates = n_rows - n_unique
            self.logger.error(
                f"ERROR: Found {n_duplicates} duplicate key combinations. "
                f"Total: {n_rows}, Unique: {n_unique}"
            )
            
            duplicated = base_df.filter(
                base_df.select(key_vars).is_duplicated()
            ).head(5)
            self.logger.error(f"Sample duplicates:\n{duplicated}")
            
            base_df = base_df.unique(subset=key_vars, keep="first")
            self.logger.warning(f"Continuing with {base_df.height} unique records")
        else:
            self.logger.info(f"Base dataset has {base_df.height} unique rows")
        
        return base_df
    
    
    def _load_source_data(self) -> None:
        """Load all required source data once."""
        dependencies = self.spec.get_data_dependency()
        required_datasets = list(set(dep['sdtm_data'] for dep in dependencies 
                                     if dep['sdtm_data'] != self.spec.domain))
        
        key_vars = self.spec.key or []
        self.source_data = self.sdtm_loader.load_datasets(
            required_datasets, rename_columns=True, preserve_keys=key_vars
        )
    
    
    def _get_derivation(self, col_spec: dict[str, Any]):
        """Get appropriate derivation class based on specification."""
        derivation = col_spec.get("derivation", {})
        
        # Determine which derivation to use
        # Function derivation handles custom functions
        if "function" in derivation:
            from .derivations import FunctionDerivation
            return FunctionDerivation()
        # Everything else can be handled by SQL derivation
        else:
            from .derivations import SQLDerivation
            return SQLDerivation()
    
    def _derive_column(self, col_spec: dict[str, Any]) -> None:
        """Derive a single column."""
        # Add key variables to column spec for derivations to use
        col_spec['_key_vars'] = self.spec.key or ["USUBJID"]
        
        derivation_obj = self._get_derivation(col_spec)
        self.logger.info(f"Deriving {col_spec['name']} using {derivation_obj.__class__.__name__}")
        
        # Setup context and derive
        derivation_obj.setup(col_spec, self.source_data, self.target_df)
        derived_series = derivation_obj.derive()
        self.target_df = self.target_df.with_columns(derived_series.alias(col_spec['name']))
    
    
    def build(self) -> pl.DataFrame:
        """Build the ADaM dataset."""
        self.logger.info(f"Starting derivation for {self.spec.domain}")
        
        # Load all source data once (with renaming, preserving key variables)
        self._load_source_data()
        self.logger.info(f"Loaded {len(self.source_data)} source datasets")
        
        self.target_df = self._build_keys()
        
        # Derive each column
        for col_spec in self.spec.get_column_specs():
            col_name = col_spec["name"]
            
            if col_name in self.spec.key or col_spec.get("drop"):
                continue
            
            try:
                self._derive_column(col_spec)
            except Exception as e:
                self.logger.error(f"Failed to derive {col_name}: {e}")
                # Add null column to maintain structure
                if self.target_df.height > 0:
                    self.target_df = self.target_df.with_columns(pl.lit(None).alias(col_name))
        
        self.logger.info(f"Derivation complete: {self.target_df.shape}")
        return self.target_df
    
    def save(self) -> Path:
        """Save dataset to parquet file."""
        df = self.build()
        output_path = Path(self.spec.adam_dir) / f"{self.spec.domain.lower()}.parquet"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.write_parquet(output_path)
        self.logger.info(f"Saved to {output_path}")
        return output_path
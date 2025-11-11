"""
Data validation for derived ADaM datasets using Polars
"""

import polars as pl
from typing import Any
import logging


class DataValidator:
    """Validate derived ADaM datasets against specifications"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def validate_dataset(self, df: pl.DataFrame, spec: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Validate dataset against specification
        
        Args:
            df: Dataset to validate
            spec: Specification dictionary
        
        Returns:
            List of validation results
        """
        results = []
        
        # Validate dataset-level requirements
        results.extend(self._validate_dataset_level(df, spec))
        
        # Validate each column
        columns = spec.get("columns", [])
        for col_spec in columns:
            col_name = col_spec.get("name")
            
            # Skip dropped columns
            if col_spec.get("drop", False):
                continue
            
            if col_name in df.columns:
                results.extend(self._validate_column(df[col_name], col_spec))
            else:
                results.append({
                    "status": "error",
                    "column": col_name,
                    "message": f"Required column {col_name} not found in dataset"
                })
        
        return results
    
    def _validate_dataset_level(self, df: pl.DataFrame, spec: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Validate dataset-level requirements
        
        Args:
            df: Dataset to validate
            spec: Specification dictionary
        
        Returns:
            List of validation results
        """
        results = []
        
        # Check key variables
        key_vars = spec.get("key", [])
        for key_var in key_vars:
            if key_var not in df.columns:
                results.append({
                    "status": "error",
                    "message": f"Key variable {key_var} not found in dataset"
                })
        
        # Check for duplicate keys if all key variables present
        if all(k in df.columns for k in key_vars) and key_vars:
            n_unique = df.select(key_vars).unique().height
            if n_unique < df.height:
                n_dups = df.height - n_unique
                results.append({
                    "status": "error",
                    "message": f"Dataset has {n_dups} duplicate records based on key variables {key_vars}"
                })
        
        # Check domain matches
        if "DOMAIN" in df.columns:
            expected_domain = spec.get("domain")
            actual_domains = df["DOMAIN"].unique().to_list()
            if len(actual_domains) == 1 and actual_domains[0] != expected_domain:
                results.append({
                    "status": "warning",
                    "column": "DOMAIN",
                    "message": f"Domain mismatch: expected {expected_domain}, got {actual_domains[0]}"
                })
        
        return results
    
    def _validate_column(self, series: pl.Series, col_spec: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Validate a single column
        
        Args:
            series: Column data
            col_spec: Column specification
        
        Returns:
            List of validation results
        """
        results = []
        col_name = col_spec.get("name")
        validation = col_spec.get("validation", {})
        
        # Check missing percentage
        max_missing = validation.get("maximum_missing_percentage")
        if max_missing is not None:
            missing_pct = (series.null_count() / len(series)) * 100
            if missing_pct > max_missing:
                results.append({
                    "status": "warning",
                    "column": col_name,
                    "message": f"Column {col_name} has {missing_pct:.1f}% missing values, exceeds maximum of {max_missing}%"
                })
        
        # Check uniqueness
        if validation.get("unique", False):
            n_unique = series.n_unique()
            if n_unique < len(series):
                n_dups = len(series) - n_unique
                results.append({
                    "status": "error",
                    "column": col_name,
                    "message": f"Column {col_name} should be unique but has {n_dups} duplicate values"
                })
        
        # Check allowed values
        allowed = validation.get("allowed_values")
        if allowed:
            # Get unique values that are not null and not in allowed list
            unique_vals = series.drop_nulls().unique().to_list()
            invalid_vals = [v for v in unique_vals if v not in allowed]
            if invalid_vals:
                results.append({
                    "status": "warning",
                    "column": col_name,
                    "message": f"Column {col_name} has invalid values: {invalid_vals[:5]}"
                })
        
        # Check numeric ranges
        if col_spec.get("type") in ["int", "float"]:
            min_val = validation.get("min")
            max_val = validation.get("max")
            
            # Try to convert to numeric if needed
            numeric_series = series
            if series.dtype == pl.Utf8:
                try:
                    numeric_series = series.cast(pl.Float64, strict=False)
                except:
                    # If conversion fails, skip numeric validation
                    return results
            
            if min_val is not None and numeric_series.dtype in [pl.Int32, pl.Int64, pl.Float32, pl.Float64]:
                below_min = (numeric_series < min_val).sum()
                if below_min > 0:
                    results.append({
                        "status": "warning",
                        "column": col_name,
                        "message": f"Column {col_name} has {below_min} values below minimum {min_val}"
                    })
            
            if max_val is not None and numeric_series.dtype in [pl.Int32, pl.Int64, pl.Float32, pl.Float64]:
                above_max = (numeric_series > max_val).sum()
                if above_max > 0:
                    results.append({
                        "status": "warning",
                        "column": col_name,
                        "message": f"Column {col_name} has {above_max} values above maximum {max_val}"
                    })
        
        return results
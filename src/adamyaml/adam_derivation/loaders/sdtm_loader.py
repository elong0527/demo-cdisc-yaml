import polars as pl
from pathlib import Path
import logging


class SDTMLoader:
    """Load and cache SDTM datasets."""
    
    def __init__(self, sdtm_dir: str):
        """
        Initialize SDTM loader.
        
        Args:
            sdtm_dir: Directory containing SDTM parquet files
        """
        self.sdtm_dir = Path(sdtm_dir)
        if not self.sdtm_dir.exists():
            raise FileNotFoundError(f"SDTM directory not found: {sdtm_dir}")
        
        self._cache: dict[str, pl.DataFrame] = {}
        self.logger = logging.getLogger(__name__)
    
    def load_dataset(self, dataset_name: str, rename_columns: bool = False, preserve_keys: list[str] | None = None) -> pl.DataFrame:
        """
        Load a single SDTM dataset with caching and optional column renaming.
        Uses the DOMAIN value from the dataset for renaming, not the filename.
        
        Args:
            dataset_name: Name of dataset file (e.g., 'DM', 'VS', 'EX')
            rename_columns: If True, rename columns to {DOMAIN}.{column} format
            preserve_keys: List of key columns to preserve without renaming
        
        Returns:
            DataFrame containing the dataset
        """
        dataset_name = dataset_name.upper()
        cache_key = f"{dataset_name}_{'renamed' if rename_columns else 'original'}"
        
        # Return from cache if available
        if cache_key in self._cache:
            self.logger.debug(f"Returning {cache_key} from cache")
            return self._cache[cache_key]
        
        # Load from file
        file_path = self.sdtm_dir / f"{dataset_name.lower()}.parquet"
        if not file_path.exists():
            raise FileNotFoundError(f"SDTM dataset not found: {file_path}")
        
        self.logger.info(f"Loading {dataset_name} from {file_path}")
        df = pl.read_parquet(file_path)
        
        # Get the DOMAIN value from the dataset
        domain_value = dataset_name  # Default to filename
        if "DOMAIN" in df.columns:
            unique_domains = df["DOMAIN"].unique()
            if len(unique_domains) == 1:
                domain_value = unique_domains[0]
                self.logger.debug(f"Using DOMAIN value '{domain_value}' for dataset {dataset_name}")
            else:
                self.logger.warning(f"Multiple DOMAIN values in {dataset_name}: {unique_domains}, using filename")
        else:
            self.logger.debug(f"No DOMAIN column in {dataset_name}, using filename for renaming")
        
        # Rename columns if requested
        if rename_columns:
            preserve_keys = preserve_keys or []
            renamed_columns = {}
            for col in df.columns:
                if col not in preserve_keys:
                    renamed_columns[col] = f"{domain_value}.{col}"
            
            if renamed_columns:
                df = df.rename(renamed_columns)
                self.logger.debug(f"Renamed {len(renamed_columns)} columns in {dataset_name} using domain '{domain_value}'")
        
        # Cache the dataset
        self._cache[cache_key] = df
        
        return df
    
    def load_datasets(self, dataset_names: list[str], rename_columns: bool = False, preserve_keys: list[str] | None = None) -> dict[str, pl.DataFrame]:
        """
        Load multiple SDTM datasets.
        
        Args:
            dataset_names: List of dataset names
            rename_columns: If True, rename columns to {dataset}.{column} format
            preserve_keys: List of key columns to preserve without renaming
        
        Returns:
            Dictionary mapping dataset names to DataFrames
        """
        datasets = {}
        for name in dataset_names:
            try:
                datasets[name.upper()] = self.load_dataset(name, rename_columns, preserve_keys)
            except FileNotFoundError as e:
                self.logger.warning(f"Could not load {name}: {e}")
        
        return datasets
    
    def clear_cache(self):
        """Clear the dataset cache."""
        self._cache.clear()
        self.logger.debug("Cleared SDTM cache")
import yaml
import re
from pathlib import Path
from dataclasses import dataclass, asdict
from copy import deepcopy
import logging
from .merge_yaml import merge_yaml
from .schema_validator import SchemaValidator, ValidationResult

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class Column:
    """ADaM column specification."""
    name: str
    type: str
    label: str | None = None
    core: str | None = None
    derivation: dict | None = None
    validation: dict | None = None
    drop: bool | None = None
    
    def __post_init__(self):
        if self.label is None:
            self.label = self.name
    
    def to_dict(self) -> dict:
        """Convert to dictionary, excluding None values and drop flag."""
        result = {}
        for key, value in asdict(self).items():
            if value is not None and key != 'drop':
                result[key] = value
        return result


class AdamSpec:
    """
    Load and validate ADaM specifications from YAML files with inheritance support.
    
    Attributes:
        domain: Dataset domain (e.g., 'ADSL')
        key: List of key variables
        columns: List of Column objects
        parents: List of parent YAML files
    """
    
    def __init__(self, path: str | Path, schema_path: str | Path | None = None):
        """
        Load YAML specification with automatic parent merging and validation.
        
        Args:
            path: Path to YAML specification file
            schema_path: Optional schema for validation (defaults to spec's schema field)
        """
        self.path = Path(path)
        self.schema_path = Path(schema_path) if schema_path else None
        self.domain: str = ""  
        self.key: list[str] = []
        self.columns: list[Column] = []
        self.parents: list[str] = []
        self._errors: list[str] = []
        self._warnings: list[str] = []
        self._raw_spec: dict = {}
        self._schema_results: list[ValidationResult] = []
        
        self._build_spec()
        
        # Use schema from spec if not provided
        if not self.schema_path and 'schema' in self._raw_spec:
            schema_from_spec = self._raw_spec['schema']
            potential_schema_path = self.path.parent / schema_from_spec
            if potential_schema_path.exists():
                self.schema_path = potential_schema_path
                logger.info(f"Using schema from specification: {schema_from_spec}")
        
        # Validate if schema available
        if self.schema_path:
            self._validate_with_schema()
            if self._errors:
                logger.warning(f"Validation found {len(self._errors)} errors")
        else:
            logger.warning(f"No schema found for {self.path.name} - validation skipped")
        
        # Validate key variables (strict validation - fail early)
        self._validate_key_variables()
        if self._errors:
            error_msg = "\n".join(self._errors)
            raise ValueError(f"Key variable validation failed:\n{error_msg}")
    
    def _build_spec(self) -> None:
        """Build specification with inheritance."""
        if not self.path.exists():
            raise FileNotFoundError(f"YAML file not found: {self.path}")
        
        try:
            with open(self.path, 'r') as f:
                study_spec = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in {self.path}: {e}")
        
        yaml_files = self._collect_yaml_files(study_spec)
        
        final_spec = merge_yaml(
            yaml_files,
            list_merge_strategy="merge_by_key",
            list_merge_keys={"columns": "name"}
        )
        
        self._raw_spec = final_spec
        self._extract_fields(final_spec)
    
    def _collect_yaml_files(self, study_spec: dict) -> list[str]:
        """Collect YAML files including parents."""
        yaml_files = []
        spec_dir = self.path.parent
        
        if 'parents' in study_spec:
            self.parents = study_spec['parents'] if isinstance(study_spec['parents'], list) else [study_spec['parents']]
            
            for parent_file in self.parents:
                parent_path = spec_dir / parent_file
                if not parent_path.exists():
                    raise FileNotFoundError(f"Parent file not found: {parent_path}")
                yaml_files.append(str(parent_path))
        
        yaml_files.append(str(self.path))  # Study file last to override
        return yaml_files
    
    def _extract_fields(self, spec: dict) -> None:
        """Extract fields from merged specification."""
        self.domain = spec.get('domain', '')
        self.key = spec.get('key', [])
        
        raw_columns = spec.get('columns', [])
        processed_columns = self._process_columns(raw_columns)
        
        self.columns = []
        for col_dict in processed_columns:
            try:
                if 'type' not in col_dict:
                    self._errors.append(f"Column {col_dict.get('name', 'unknown')} missing required 'type' field")
                    continue
                    
                col = Column(**{k: v for k, v in col_dict.items() if k != 'drop'})
                self.columns.append(col)
            except TypeError as e:
                self._errors.append(f"Invalid column specification: {e}")
    
    def _process_columns(self, columns: list[dict]) -> list[dict]:
        """Process columns, handling drop flags."""
        result = []
        dropped_names = set()
        
        for col in columns:
            if col.get('drop', False):
                dropped_names.add(col['name'])
                logger.debug(f"Column marked for drop: {col['name']}")
        
        for col in columns:
            if col.get('name') not in dropped_names and not col.get('drop', False):
                if 'label' not in col or col['label'] is None:
                    col['label'] = col['name']
                result.append(col)
        
        return result
    
    def _validate_with_schema(self) -> None:
        """Validate specification against schema."""
        try:
            validator = SchemaValidator(self.schema_path)
            self._schema_results = validator.validate(self._raw_spec)
            
            for error in validator.get_errors():
                self._errors.append(f"[{error.rule}] {error.message}")
            
            for warning in validator.get_warnings():
                self._warnings.append(f"[{warning.rule}] {warning.message}")
            
            logger.info(f"Schema validation complete: {len(validator.get_errors())} errors, {len(validator.get_warnings())} warnings")
        except Exception as e:
            logger.error(f"Schema validation failed: {e}")
            self._errors.append(f"Schema validation error: {e}")

    def _validate_key_variables(self) -> None:
        """
        Validate key variables follow strict rules.
        Adds errors to self._errors if validation fails.
        """
        if not self.key:
            return  # No key variables to validate
        
        source_datasets = set()
        key_var_errors = []
        
        for key_var in self.key:
            # Get column specification for this key variable
            col_spec = None
            for col in self.columns:
                if col.name == key_var:
                    col_spec = col
                    break
            
            if not col_spec:
                key_var_errors.append(f"Key variable '{key_var}' not found in column specifications")
                continue
            
            # Get derivation dict directly
            derivation = col_spec.derivation or {}
            
            # Rule 1: Must use source derivation only
            if 'source' not in derivation:
                key_var_errors.append(
                    f"Key variable '{key_var}' must use 'source' derivation, "
                    f"found: {list(derivation.keys())}"
                )
                continue
            
            # Check for additional derivation types (should be source only)
            other_keys = set(derivation.keys()) - {'source'}
            if other_keys:
                key_var_errors.append(
                    f"Key variable '{key_var}' must use only 'source' derivation, "
                    f"found additional: {other_keys}"
                )
            
            # Rule 2: Source must be in DATASET.COLUMN format
            source_str = derivation.get('source', '')
            if '.' not in source_str:
                key_var_errors.append(
                    f"Key variable '{key_var}' source must be in format 'DATASET.COLUMN', "
                    f"found: '{source_str}'"
                )
                continue
            
            # Track source dataset
            dataset_name = source_str.split('.', 1)[0]
            source_datasets.add(dataset_name)
        
        # Rule 3: All key variables must come from the same dataset
        if len(source_datasets) > 1:
            key_var_errors.append(
                f"All key variables must come from the same source dataset, "
                f"found multiple: {source_datasets}"
            )
        
        # Add all errors to self._errors
        if key_var_errors:
            self._errors.extend(key_var_errors)
    
    def to_dict(self, include_parents: bool = False) -> dict:
        """Convert to dictionary format."""
        result = deepcopy(self._raw_spec)
        
        result["domain"] = self.domain
        result["key"] = self.key
        result["columns"] = [col.to_dict() for col in self.columns]
        
        if not include_parents:
            result.pop('parents', None)
        
        return result
    
    def to_yaml(self, include_parents: bool = False) -> str:
        """Convert to YAML string."""
        return yaml.dump(
            self.to_dict(include_parents),
            default_flow_style=False,
            sort_keys=False
        )
    
    def save(self, output_path: str | Path) -> None:
        """Save specification to YAML file."""
        output = Path(output_path)
        
        with open(output, 'w') as f:
            f.write(self.to_yaml())
        
        logger.info(f"Saved YAML specification to {output}")
    
    def get_column_specs(self, names: str | list[str] | None = None) -> dict | list[dict] | None:
        """
        Get column specifications.
        
        Args:
            names: Column name(s) - string, list, or None for all
        
        Returns:
            Single dict, list of dicts, or None if not found
        """
        if names is not None:
            if isinstance(names, str):
                for col in self.columns:
                    if col.name == names:
                        return col.to_dict()
                return None
            
            elif isinstance(names, list):
                result = []
                for name in names:
                    for col in self.columns:
                        if col.name == name:
                            result.append(col.to_dict())
                            break
                return result
        
        return [col.to_dict() for col in self.columns]
    
    def get_data_dependency(self) -> list[dict]:
        """
        Extract SDTM data dependencies.
        
        Returns:
            List of dicts with adam_variable, sdtm_data, sdtm_variable
        """
        pattern = re.compile(r'\b([A-Z][A-Z0-9_]{0,19})\.([A-Z][A-Z0-9_]{0,19})\b')
        
        dependencies = []
        seen = set()
        
        for column in self.columns:
            matches = pattern.findall(str(column.to_dict()))
            
            for sdtm_data, sdtm_variable in matches:
                key = (column.name, sdtm_data, sdtm_variable)
                if key not in seen:
                    seen.add(key)
                    dependencies.append({
                        'adam_variable': column.name,
                        'sdtm_data': sdtm_data,
                        'sdtm_variable': sdtm_variable
                    })
        
        return dependencies
    
    @property
    def sdtm_dir(self) -> str:
        """
        Get the SDTM directory path from specification.
        
        Returns:
            Absolute path to SDTM directory
            
        Raises:
            ValueError: If dir.sdtm is not specified in the specification
        """
        # Check for new structure first (dir.sdtm)
        dir_config = self._raw_spec.get('dir', {})
        sdtm_dir = dir_config.get('sdtm')
        
        # Fallback to old structure for backward compatibility
        if not sdtm_dir:
            sdtm_dir = self._raw_spec.get('sdtm_dir')
        
        if not sdtm_dir:
            raise ValueError(f"No dir.sdtm specified in {self.path}. This is a required field.")
        
        # Convert to Path for proper handling
        sdtm_path = Path(sdtm_dir)
        
        # If relative path, resolve relative to spec file directory
        if not sdtm_path.is_absolute():
            sdtm_path = self.path.parent / sdtm_path
            
        return str(sdtm_path.resolve())
    
    @property
    def adam_dir(self) -> str:
        """
        Get the ADaM output directory path from specification.
        
        Returns:
            Absolute path to ADaM output directory
            
        Raises:
            ValueError: If dir.adam is not specified in the specification
        """
        # Get from new structure (dir.adam)
        dir_config = self._raw_spec.get('dir', {})
        adam_dir = dir_config.get('adam')
        
        if not adam_dir:
            raise ValueError(f"No dir.adam specified in {self.path}. This is a required field.")
        
        # Convert to Path for proper handling
        adam_path = Path(adam_dir)
        
        # If relative path, resolve relative to spec file directory
        if not adam_path.is_absolute():
            adam_path = self.path.parent / adam_path
            
        return str(adam_path.resolve())
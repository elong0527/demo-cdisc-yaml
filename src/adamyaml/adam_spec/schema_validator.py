import re
import yaml
from pathlib import Path
from typing import Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of a validation check"""
    field: str
    rule: str
    severity: str  # 'error', 'warning', 'info'
    message: str
    value: Any = None
    expected: Any = None


class SchemaValidator:
    """
    Validates ADaM specifications against a schema
    
    Usage:
        validator = SchemaValidator("spec/schema.yaml")
        results = validator.validate(spec_dict)
    """
    
    def __init__(self, schema_path: str | Path):
        """
        Initialize with schema file
        
        Args:
            schema_path: Path to schema YAML file
        """
        self.schema_path = Path(schema_path)
        self.schema = self._load_schema()
        self.results: list[ValidationResult] = []
    
    def _load_schema(self) -> dict:
        """Load schema from YAML file"""
        if not self.schema_path.exists():
            raise FileNotFoundError(f"Schema file not found: {self.schema_path}")
        
        try:
            with open(self.schema_path, 'r') as f:
                schema = yaml.safe_load(f)
                logger.debug(f"Loaded schema from {self.schema_path}")
                return schema
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in schema file: {e}")
    
    def validate(self, spec: dict) -> list[ValidationResult]:
        """
        Validate a specification against the schema
        
        Args:
            spec: Specification dictionary to validate
            
        Returns:
            List of validation results
        """
        self.results = []
        
        # Validate root level
        self._validate_root(spec)
        
        # Validate root fields
        self._validate_fields(spec)
        
        # Validate columns rules
        if 'columns' in spec:
            self._validate_columns(spec['columns'])
        
        # Apply custom validation rules
        self._apply_custom_rules(spec)
        
        return self.results
    
    def _validate_root(self, spec: dict) -> None:
        """Validate root-level requirements"""
        root_schema = self.schema.get('root', {})
        
        # Check required root fields
        required_fields = root_schema.get('required', [])
        for field_name in required_fields:
            if field_name not in spec or spec[field_name] is None:
                self.results.append(ValidationResult(
                    field=field_name,
                    rule='required_field',
                    severity='error',
                    message=f"Required field '{field_name}' is missing",
                    expected=f"Field '{field_name}' must be present"
                ))
        
        # Check for unknown fields (info level)
        optional_fields = root_schema.get('optional', [])
        all_known_fields = set(required_fields + optional_fields)
        
        for field_name in spec.keys():
            if field_name not in all_known_fields:
                logger.debug(f"Unknown root field: {field_name}")
                # Not an error, just log it
    
    def _validate_fields(self, spec: dict) -> None:
        """Validate individual root fields against their schemas"""
        fields_schema = self.schema.get('fields', {})
        
        for field_name, field_value in spec.items():
            if field_name in fields_schema:
                field_schema = fields_schema[field_name]
                self._validate_field(field_name, field_value, field_schema)
    
    def _validate_field(self, name: str, value: Any, schema: dict) -> None:
        """Validate a single field against its schema"""
        # Skip if value is None
        if value is None:
            return
        
        # Type validation
        expected_type = schema.get('type')
        if expected_type and not self._check_type(value, expected_type):
            self.results.append(ValidationResult(
                field=name,
                rule='invalid_type',
                severity='error',
                message=f"Field '{name}' should be type {expected_type}, got {type(value).__name__}",
                value=value,
                expected=expected_type
            ))
            return
        
        # String-specific validations
        if isinstance(value, str):
            # Pattern validation
            if 'pattern' in schema:
                pattern = schema['pattern']
                if not re.match(pattern, value):
                    self.results.append(ValidationResult(
                        field=name,
                        rule='invalid_pattern',
                        severity='error',
                        message=f"Field '{name}' value '{value}' doesn't match required pattern",
                        value=value,
                        expected=f"Pattern: {pattern}"
                    ))
            
            # Max length validation
            if 'max_length' in schema and len(value) > schema['max_length']:
                self.results.append(ValidationResult(
                    field=name,
                    rule='max_length_exceeded',
                    severity='warning',
                    message=f"Field '{name}' exceeds max length of {schema['max_length']} (actual: {len(value)})",
                    value=len(value),
                    expected=schema['max_length']
                ))
        
        # List-specific validations
        elif isinstance(value, list):
            self._validate_list_field(name, value, schema)
        
        # Dict-specific validations
        elif isinstance(value, dict):
            self._validate_dict_field(name, value, schema)
        
        # Allowed values validation
        if 'allowed_values' in schema:
            if value not in schema['allowed_values']:
                self.results.append(ValidationResult(
                    field=name,
                    rule='invalid_value',
                    severity='warning',
                    message=f"Field '{name}' has non-standard value: '{value}'",
                    value=value,
                    expected=schema['allowed_values']
                ))
    
    def _validate_list_field(self, name: str, items: list, schema: dict) -> None:
        """Validate a list field"""
        # Min items validation
        min_items = schema.get('min_items', 0)
        if len(items) < min_items:
            severity = 'error' if schema.get('required') else 'warning'
            self.results.append(ValidationResult(
                field=name,
                rule='min_items',
                severity=severity,
                message=f"Field '{name}' has {len(items)} items, minimum required is {min_items}",
                value=len(items),
                expected=f">= {min_items}"
            ))
        
        # Max items validation
        max_items = schema.get('max_items')
        if max_items and len(items) > max_items:
            self.results.append(ValidationResult(
                field=name,
                rule='max_items',
                severity='warning',
                message=f"Field '{name}' has {len(items)} items, maximum allowed is {max_items}",
                value=len(items),
                expected=f"<= {max_items}"
            ))
        
        # Item type validation
        item_type = schema.get('item_type')
        if item_type:
            for i, item in enumerate(items):
                if not self._check_type(item, item_type):
                    self.results.append(ValidationResult(
                        field=f"{name}[{i}]",
                        rule='invalid_item_type',
                        severity='error',
                        message=f"Item {i} in '{name}' has wrong type (expected {item_type})",
                        value=type(item).__name__,
                        expected=item_type
                    ))
    
    def _validate_dict_field(self, name: str, value: dict, schema: dict) -> None:
        """Validate a dictionary field with nested structure"""
        # Check required fields within the dict
        required_fields = schema.get('required_fields', [])
        for req_field in required_fields:
            if req_field not in value or value[req_field] is None:
                self.results.append(ValidationResult(
                    field=f"{name}.{req_field}",
                    rule='required_field',
                    severity='error',
                    message=f"Required field '{name}.{req_field}' is missing",
                    expected=f"Field '{req_field}' must be present in '{name}'"
                ))
        
        # Validate nested fields if schema provided
        nested_fields_schema = schema.get('fields', {})
        for field_name, field_value in value.items():
            if field_name in nested_fields_schema:
                nested_schema = nested_fields_schema[field_name]
                self._validate_field(f"{name}.{field_name}", field_value, nested_schema)
    
    def _validate_columns(self, columns: list[dict]) -> None:
        """Validate column specifications with updated schema rules"""
        column_schema = self.schema.get('column', {})
        required_fields = column_schema.get('required', [])
        optional_fields = column_schema.get('optional', [])
        column_field_schemas = column_schema.get('fields', {})
        
        column_names = []
        
        for i, col in enumerate(columns):
            col_name = col.get('name', f'column_{i}')
            column_names.append(col_name)
            
            # Check required column fields (name, type, derivation)
            for req_field in required_fields:
                if req_field not in col or col[req_field] is None:
                    self.results.append(ValidationResult(
                        field=f"columns[{i}].{req_field}",
                        rule='required_column_field',
                        severity='error',
                        message=f"Column '{col_name}' missing required field '{req_field}'",
                        value=col_name,
                        expected=f"Field '{req_field}' is required"
                    ))
            
            # Validate each column field against its schema
            for field_name, field_value in col.items():
                if field_name in column_field_schemas:
                    self._validate_column_field(
                        col_name, i, field_name, field_value,
                        column_field_schemas[field_name]
                    )
                elif field_name not in required_fields and field_name not in optional_fields:
                    # Unknown field - just log
                    logger.debug(f"Unknown column field '{field_name}' in column '{col_name}'")
        
        # Check for duplicate column names
        seen_names = set()
        duplicates = set()
        for name in column_names:
            if name in seen_names:
                duplicates.add(name)
            seen_names.add(name)
        
        if duplicates:
            self.results.append(ValidationResult(
                field='columns',
                rule='duplicate_columns',
                severity='error',
                message=f"Duplicate column names found: {sorted(duplicates)}",
                value=list(duplicates),
                expected="Unique column names"
            ))
    
    def _validate_column_field(self, col_name: str, col_index: int,
                               field_name: str, value: Any, schema: dict) -> None:
        """Validate a single column field"""
        field_path = f"columns[{col_index}].{field_name}"
        
        # Skip None values
        if value is None:
            return
        
        # Type validation
        expected_type = schema.get('type')
        if expected_type and not self._check_type(value, expected_type):
            self.results.append(ValidationResult(
                field=field_path,
                rule='invalid_type',
                severity='error',
                message=f"Column '{col_name}' field '{field_name}' has wrong type",
                value=type(value).__name__,
                expected=expected_type
            ))
            return
        
        # String validations
        if isinstance(value, str):
            # Pattern validation (e.g., column names must be uppercase, max 8 chars)
            if 'pattern' in schema:
                pattern = schema['pattern']
                if not re.match(pattern, value):
                    self.results.append(ValidationResult(
                        field=field_path,
                        rule='invalid_pattern',
                        severity='error',
                        message=f"Column '{col_name}' field '{field_name}' value '{value}' doesn't match pattern",
                        value=value,
                        expected=f"Pattern: {pattern}"
                    ))
            
            # Max length
            if 'max_length' in schema and len(value) > schema['max_length']:
                self.results.append(ValidationResult(
                    field=field_path,
                    rule='max_length',
                    severity='warning',
                    message=f"Column '{col_name}' field '{field_name}' exceeds max length",
                    value=len(value),
                    expected=schema['max_length']
                ))
        
        # Allowed values (e.g., type must be str/int/float/etc.)
        if 'allowed_values' in schema and value not in schema['allowed_values']:
            self.results.append(ValidationResult(
                field=field_path,
                rule='invalid_value',
                severity='warning',
                message=f"Column '{col_name}' field '{field_name}' has non-standard value: '{value}'",
                value=value,
                expected=schema['allowed_values']
            ))
        
        # Numeric validations
        if isinstance(value, (int, float)):
            if 'min' in schema and value < schema['min']:
                self.results.append(ValidationResult(
                    field=field_path,
                    rule='below_minimum',
                    severity='error',
                    message=f"Column '{col_name}' field '{field_name}' value {value} is below minimum",
                    value=value,
                    expected=f">= {schema['min']}"
                ))
            
            if 'max' in schema and value > schema['max']:
                self.results.append(ValidationResult(
                    field=field_path,
                    rule='above_maximum',
                    severity='error',
                    message=f"Column '{col_name}' field '{field_name}' value {value} is above maximum",
                    value=value,
                    expected=f"<= {schema['max']}"
                ))
        
        # Dict validations (for derivation, validation sub-fields)
        if isinstance(value, dict) and 'fields' in schema:
            self._validate_nested_fields(col_name, col_index, field_name, value, schema['fields'])
    
    def _validate_nested_fields(self, col_name: str, col_index: int,
                                parent_field: str, value: dict, fields_schema: dict) -> None:
        """Validate nested fields within a column field (e.g., derivation, validation)"""
        for sub_field, sub_value in value.items():
            if sub_field in fields_schema:
                sub_schema = fields_schema[sub_field]
                field_path = f"columns[{col_index}].{parent_field}.{sub_field}"
                
                # Type check
                if 'type' in sub_schema:
                    if not self._check_type(sub_value, sub_schema['type']):
                        self.results.append(ValidationResult(
                            field=field_path,
                            rule='invalid_type',
                            severity='error',
                            message=f"Column '{col_name}' nested field has wrong type",
                            value=type(sub_value).__name__,
                            expected=sub_schema['type']
                        ))
    
    def _apply_custom_rules(self, spec: dict) -> None:
        """Apply custom validation rules"""
        # Rule 1: Key variables must exist in columns
        self._validate_key_variables_exist(spec)
        
        # Rule 2: Type consistency for validation rules
        self._validate_type_consistency(spec.get('columns', []))
        
        # Rule 3: Valid derivation (must have source, function, or constant)
        self._validate_derivations(spec.get('columns', []))
        
        # Rule 4: Key variables must follow strict rules
        self._validate_key_variable_rules(spec)
    
    def _validate_key_variables_exist(self, spec: dict) -> None:
        """Validate that all key variables exist as columns"""
        key_vars = spec.get('key', [])
        if not key_vars:
            return
        
        column_names = {col.get('name') for col in spec.get('columns', []) if col.get('name')}
        
        for key_var in key_vars:
            if key_var not in column_names:
                self.results.append(ValidationResult(
                    field='key',
                    rule='key_variable_not_found',
                    severity='error',
                    message=f"Key variable '{key_var}' not found in columns",
                    value=key_var,
                    expected=f"Must be one of: {sorted(column_names)}"
                ))
    
    def _validate_type_consistency(self, columns: list[dict]) -> None:
        """Validate that validation rules match column types"""
        for i, col in enumerate(columns):
            col_type = col.get('type')
            col_validation = col.get('validation', {})
            col_name = col.get('name', f'column_{i}')
            
            if not col_type or not col_validation:
                continue
            
            # Numeric types shouldn't have string validations
            if col_type in ['int', 'float']:
                string_validations = {'min_length', 'max_length', 'pattern'}
                invalid_validations = string_validations & set(col_validation.keys())
                if invalid_validations:
                    self.results.append(ValidationResult(
                        field=f"columns[{i}].validation",
                        rule='type_consistency',
                        severity='warning',
                        message=f"Numeric column '{col_name}' has string validation rules: {invalid_validations}",
                        value=list(invalid_validations),
                        expected=f"Numeric validations for type '{col_type}'"
                    ))
            
            # String types shouldn't have numeric min/max (unless they're lengths)
            elif col_type == 'str':
                if 'min' in col_validation and not isinstance(col_validation['min'], str):
                    self.results.append(ValidationResult(
                        field=f"columns[{i}].validation.min",
                        rule='type_consistency',
                        severity='warning',
                        message=f"String column '{col_name}' has numeric min validation",
                        value=col_validation['min'],
                        expected="Use min_length for string length validation"
                    ))
                
                if 'max' in col_validation and not isinstance(col_validation['max'], str):
                    self.results.append(ValidationResult(
                        field=f"columns[{i}].validation.max",
                        rule='type_consistency',
                        severity='warning',
                        message=f"String column '{col_name}' has numeric max validation",
                        value=col_validation['max'],
                        expected="Use max_length for string length validation"
                    ))
    
    def _validate_derivations(self, columns: list[dict]) -> None:
        """Validate derivation specifications"""
        for i, col in enumerate(columns):
            derivation = col.get('derivation')
            col_name = col.get('name', f'column_{i}')
            
            # Derivation is required based on updated schema
            if not derivation:
                # This should already be caught by required field check
                continue
            
            # Must have at least one of: source, function, constant
            required_keys = {'source', 'function', 'constant'}
            if not any(key in derivation for key in required_keys):
                self.results.append(ValidationResult(
                    field=f"columns[{i}].derivation",
                    rule='invalid_derivation',
                    severity='error',
                    message=f"Column '{col_name}' derivation must have at least one of: source, function, or constant",
                    value=list(derivation.keys()),
                    expected=f"At least one of: {required_keys}"
                ))
    
    def _validate_key_variable_rules(self, spec: dict) -> None:
        """Validate that key variables follow strict rules"""
        key_vars = spec.get('key', [])
        if not key_vars:
            return
        
        columns = spec.get('columns', [])
        source_datasets = set()
        
        for key_var in key_vars:
            # Find the column specification for this key variable
            col_spec = None
            for col in columns:
                if col.get('name') == key_var:
                    col_spec = col
                    break
            
            if not col_spec:
                continue  # Already reported by _validate_key_variables_exist
            
            derivation = col_spec.get('derivation', {})
            
            # Rule 1: Key variables must use source derivation only
            if 'source' not in derivation:
                self.results.append(ValidationResult(
                    field=f'key.{key_var}',
                    rule='key_variable_source_only',
                    severity='error',
                    message=f"Key variable '{key_var}' must use 'source' derivation only",
                    value=list(derivation.keys()),
                    expected='source'
                ))
                continue
            
            if len(derivation) > 1:
                # Check if there are other derivation types besides source
                other_keys = set(derivation.keys()) - {'source'}
                if other_keys:
                    self.results.append(ValidationResult(
                        field=f'key.{key_var}',
                        rule='key_variable_source_only',
                        severity='error',
                        message=f"Key variable '{key_var}' must use only 'source' derivation, found additional: {other_keys}",
                        value=list(derivation.keys()),
                        expected='source only'
                    ))
            
            # Rule 2: Track source datasets
            source_str = derivation.get('source', '')
            if '.' in source_str:
                dataset_name = source_str.split('.', 1)[0]
                source_datasets.add(dataset_name)
            else:
                self.results.append(ValidationResult(
                    field=f'key.{key_var}.derivation.source',
                    rule='invalid_source_format',
                    severity='error',
                    message=f"Key variable '{key_var}' source must be in format 'DATASET.COLUMN'",
                    value=source_str,
                    expected='DATASET.COLUMN'
                ))
        
        # Rule 3: All key variables must come from the same dataset
        if len(source_datasets) > 1:
            self.results.append(ValidationResult(
                field='key',
                rule='key_variables_same_dataset',
                severity='error',
                message=f"All key variables must come from the same source dataset",
                value=list(source_datasets),
                expected='Single source dataset'
            ))
    
    def _check_type(self, value: Any, expected_type: str | list[str]) -> bool:
        """Check if value matches expected type(s)"""
        if isinstance(expected_type, list):
            return any(self._check_type(value, t) for t in expected_type)
        
        type_map = {
            'str': str,
            'int': int,
            'float': (int, float),  # int is acceptable for float
            'bool': bool,
            'list': list,
            'dict': dict,
            'any': object
        }
        
        expected_class = type_map.get(expected_type, object)
        return isinstance(value, expected_class)
    
    def get_errors(self) -> list[ValidationResult]:
        """Get only error-level results"""
        return [r for r in self.results if r.severity == 'error']
    
    def get_warnings(self) -> list[ValidationResult]:
        """Get only warning-level results"""
        return [r for r in self.results if r.severity == 'warning']
    
    def get_info(self) -> list[ValidationResult]:
        """Get only info-level results"""
        return [r for r in self.results if r.severity == 'info']
    
    def is_valid(self) -> bool:
        """Check if specification is valid (no errors)"""
        return len(self.get_errors()) == 0
    
    def summary(self) -> str:
        """Get validation summary"""
        errors = self.get_errors()
        warnings = self.get_warnings()
        info = self.get_info()
        
        lines = []
        lines.append("Schema Validation Summary")
        lines.append("-" * 40)
        lines.append(f"Total Results: {len(self.results)}")
        lines.append(f"  Errors: {len(errors)}")
        lines.append(f"  Warnings: {len(warnings)}")
        lines.append(f"  Info: {len(info)}")
        lines.append(f"Valid: {self.is_valid()}")
        
        if errors:
            lines.append("\nErrors (first 5):")
            for err in errors[:5]:
                lines.append(f"  [{err.rule}] {err.message}")
                if err.expected:
                    lines.append(f"    Expected: {err.expected}")
            if len(errors) > 5:
                lines.append(f"  ... and {len(errors) - 5} more errors")
        
        if warnings:
            lines.append("\nWarnings (first 5):")
            for warn in warnings[:5]:
                lines.append(f"  [{warn.rule}] {warn.message}")
            if len(warnings) > 5:
                lines.append(f"  ... and {len(warnings) - 5} more warnings")
        
        return "\n".join(lines)
    
    def detailed_report(self) -> str:
        """Get detailed validation report"""
        lines = []
        lines.append("=" * 60)
        lines.append("SCHEMA VALIDATION DETAILED REPORT")
        lines.append("=" * 60)
        
        # Group results by field
        by_field = {}
        for result in self.results:
            if result.field not in by_field:
                by_field[result.field] = []
            by_field[result.field].append(result)
        
        for field, results in sorted(by_field.items()):
            lines.append(f"\nField: {field}")
            lines.append("-" * 40)
            for r in results:
                icon = "[X]" if r.severity == 'error' else "[!]" if r.severity == 'warning' else "[i]"
                lines.append(f"  {icon} [{r.severity.upper()}] {r.rule}")
                lines.append(f"     {r.message}")
                if r.value is not None:
                    lines.append(f"     Current: {r.value}")
                if r.expected is not None:
                    lines.append(f"     Expected: {r.expected}")
        
        lines.append("\n" + "=" * 60)
        lines.append(f"SUMMARY: {'VALID' if self.is_valid() else 'INVALID'}")
        lines.append("=" * 60)
        
        return "\n".join(lines)
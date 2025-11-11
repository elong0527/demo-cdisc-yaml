# adam_spec Module Documentation

## Module Purpose
The `adam_spec` module is a **YAML specification consolidation tool** for ADaM datasets. It handles the critical first step in the ADaM dataset generation pipeline: merging multiple hierarchical YAML specification files into a single, validated, consolidated specification.

## Scope and Boundaries

### What This Module DOES
- **Merge YAML Files**: Combines multiple YAML specifications using inheritance
- **Validate Specifications**: Ensures YAML conforms to CDISC ADaM schema rules
- **Handle Inheritance**: Supports parent-child YAML relationships
- **Column Management**: Merges columns by name, supports dropping inherited columns
- **Export Formats**: Outputs consolidated YAML, JSON, or Python dictionaries
- **Data Dependency Analysis**: Identifies required source datasets

### What This Module DOES NOT DO
- **Execute Derivations**: Does not run data transformations
- **Access Data**: Does not read SDTM/ADaM datasets
- **Generate Code**: Does not produce executable derivation code
- **Process Data**: No DataFrame operations or calculations

## Architecture Overview

```
adam_spec/
+-- __init__.py
+-- adam_spec.py         # Main class for loading and merging specs
+-- merge_yaml.py        # Generic YAML merging utilities
+-- schema_validator.py  # Schema-based validation engine
+-- tests/              # Unit tests for all components
```

## Core Components

### 1. AdamSpec Class (adam_spec.py)
Main entry point for specification handling:

```python
class AdamSpec:
    def __init__(self, yaml_path: str, schema_path: str | None = None)
    def get_column(self, name: str) -> Column | None
    def get_data_dependency(self) -> set[str]
    def save(self, output_path: str) -> None
    def to_dict(self) -> dict[str, Any]
    def to_json(self) -> str
```

Key features:
- Automatic parent file resolution
- Hierarchical specification merging
- Schema validation integration
- Multiple export formats

### 2. merge_yaml Function (merge_yaml.py)
Generic YAML merging utility:

```python
def merge_yaml(paths: list[str],
              list_merge_strategy: str = "replace",
              list_merge_keys: dict[str, str] | None = None) -> dict
```

Merge strategies:
- **replace**: Later values override earlier ones
- **append**: Concatenate lists
- **merge_by_key**: Merge list items by specified key field

### 3. SchemaValidator Class (schema_validator.py)
Validation engine for specifications:

```python
class SchemaValidator:
    def __init__(self, schema_path: str)
    def validate(self, spec_dict: dict[str, Any]) -> ValidationResult
    def is_valid(self) -> bool
    def get_errors(self) -> list[ValidationError]
    def get_warnings(self) -> list[ValidationWarning]
```

Validation types:
- Pattern validation (regex)
- Type checking
- Required field validation
- CDISC-specific rules
- Cross-field validation

## Usage Pattern

### Basic Workflow
```python
from adamyaml.adam_spec import AdamSpec

# Step 1: Load and consolidate specifications
spec = AdamSpec("spec/adsl_study.yaml", schema_path="spec/schema.yaml")

# Step 2: Check validation
if not spec.is_valid:
    for error in spec.validation_errors:
        print(f"Error: {error}")

# Step 3: Access specification data
print(f"Domain: {spec.domain}")
print(f"Key variables: {spec.key}")
print(f"Required datasets: {spec.get_data_dependency()}")

# Step 4: Export consolidated specification
spec.save("output/adsl_consolidated.yaml")

# Step 5: Pass to derivation engine
# engine = AdamDerivation(spec.to_dict())  # Used by derivation module
```

## YAML Specification Structure

### Inheritance Hierarchy
```
adsl_common.yaml     # Base template with common variables
    |
    v
adsl_project.yaml    # Project-level specifications
    |
    v
adsl_study.yaml      # Study-specific specifications
```

### Example Specification
```yaml
# adsl_study.yaml
parents:
  - adsl_project.yaml  # Inherits from project level

domain: ADSL
key: [USUBJID, SUBJID]
sdtm_dir: ../../data/sdtm
adam_dir: ../../data/adam

columns:
  - name: USUBJID
    type: str
    label: Unique Subject Identifier
    core: required
    derivation:
      source: DM.USUBJID
  
  - name: AGE
    type: int
    label: Age
    derivation:
      source: DM.AGE
  
  - name: BMI
    type: float
    label: Body Mass Index
    derivation:
      function: get_bmi
      height: HEIGHT
      weight: WEIGHT
```

## Schema Validation Rules

### Domain Naming
- Pattern: `^AD[A-Z0-9]{0,6}$`
- Must start with "AD"
- Maximum 8 characters
- Examples: ADSL, ADAE, ADLB

### Column Naming
- Pattern: `^[A-Z][A-Z0-9_]{0,7}$`
- Uppercase letters, numbers, underscore
- Maximum 8 characters
- Examples: USUBJID, AGE, TRT01P

### Required Fields
```yaml
domain: required        # Dataset domain
columns: required       # List of column specifications
column.name: required   # Column name
column.type: required   # Data type
column.derivation: required  # How to derive
```

## Column Merging Strategy

### How Columns Are Merged
1. Columns matched by `name` field
2. Later specifications override earlier ones
3. All properties merged (not just replaced)
4. `drop: true` removes inherited column

### Example
```yaml
# Parent file
columns:
  - name: AGE
    type: int
    label: Age

# Child file
columns:
  - name: AGE
    derivation:      # Adds derivation
      source: DM.AGE # Parent properties retained
```

## Data Dependency Analysis

### get_data_dependency() Method
Analyzes specifications to identify required source datasets:

```python
# Returns set of required dataset names
deps = spec.get_data_dependency()
# {'DM', 'VS', 'EX'}  # Example output
```

Uses:
- Pre-loading validation
- Dependency checking
- Documentation generation

## Export Formats

### YAML Export
```python
spec.save("output/consolidated.yaml")
```

### JSON Export
```python
json_str = spec.to_json()
with open("output/spec.json", "w") as f:
    f.write(json_str)
```

### Dictionary Export
```python
spec_dict = spec.to_dict()
# Pass to other modules
```

## Error Handling

### File Errors
- **FileNotFoundError**: Missing YAML or parent files
- **Solution**: Check file paths and working directory

### YAML Errors
- **ValueError**: Invalid YAML syntax
- **Solution**: Validate YAML syntax with linter

### Validation Errors
- **Domain pattern mismatch**: Check CDISC naming
- **Missing required fields**: Add required properties
- **Type mismatches**: Correct data types

## Testing

### Test Coverage
- **Loading**: File loading, parent resolution
- **Merging**: All merge strategies, column handling
- **Validation**: Schema rules, patterns, types
- **Export**: All export formats
- **Dependencies**: Data dependency extraction

### Running Tests
```bash
# Run all adam_spec tests
uv run python -m unittest adamyaml.adam_spec.tests

# Run specific test
uv run python -m unittest adamyaml.adam_spec.tests.test_adam_spec
```

## Performance Considerations

### Current Performance
- Linear time complexity for merging
- Suitable for typical specifications (100s of columns)
- Fast validation with compiled regex patterns

### Limitations
- Reloads parent files for each specification
- No caching mechanism
- Not optimized for very large specifications (1000s+ columns)

## Integration with Derivation Engine

### Clear Interface
The adam_spec module provides a clean interface to the derivation engine:

```python
# In derivation engine
from adamyaml.adam_spec import AdamSpec

class AdamDerivation:
    def __init__(self, spec_path: str):
        self.spec = AdamSpec(spec_path)  # Load and validate
        # Use self.spec.to_dict() for processing
```

### Separation of Concerns
- **adam_spec**: Handles YAML operations and validation
- **adam_derivation**: Handles data processing and transformation
- No circular dependencies
- Clear module boundaries

## Best Practices

### Specification Design
1. Use inheritance for common variables
2. Override only what changes per study
3. Document derivation logic clearly
4. Follow CDISC naming conventions

### Validation
1. Always provide schema_path
2. Check validation errors before processing
3. Review warnings for potential issues
4. Test specifications before production use

## ASCII-Only Policy
- All code uses ASCII characters only
- No emojis or special Unicode characters
- Status indicators: [OK], [FAIL], [INFO], [WARNING]
- Tree structures use +-- and |

## Summary

The `adam_spec` module is a **focused, single-purpose tool** for consolidating and validating ADaM YAML specifications. It provides a clean interface between human-readable YAML files and the programmatic derivation engine, ensuring specifications are valid and complete before any data processing begins. Its clear separation from the derivation engine allows both modules to evolve independently while maintaining a stable interface.
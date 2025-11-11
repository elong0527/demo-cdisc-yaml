# Project Context for Claude

## Important Guidelines
- **Use ASCII characters only** - No emojis or special Unicode characters in code or commits

## Project Overview
This project provides two complementary Python modules for ADaM (Analysis Data Model) dataset generation in clinical trials:
1. **adam_yaml**: YAML specification consolidation and validation
2. **adam_derivation**: Dataset generation engine with simplified derivation architecture

## Project Structure
```
demo_adam_yaml/
+-- src/
|   +-- adamyaml/
|   +-- adam_spec/           # YAML specification module
|   |   +-- __init__.py
|   |   +-- adam_spec.py     # Core specification class
|   |   +-- merge_yaml.py    # YAML merging utilities
|   |   +-- schema_validator.py  # Schema validation
|   |   +-- tests/           # Unit tests
|   +-- adam_derivation/     # Derivation engine module
|       +-- __init__.py
|       +-- engine.py        # Simplified orchestration engine
|       +-- loaders/
|       |   +-- sdtm_loader.py  # SDTM data loader with column renaming
|       +-- derivations/
|           +-- base.py      # Base class and factory
|           +-- source.py    # Direct source mapping
|           +-- constant.py  # Constant values
|           +-- aggregation.py  # Aggregation functions
|           +-- custom.py    # Custom functions
|           +-- categorization.py  # Cut-based categories
|           +-- condition.py  # Conditional logic
+-- spec/                    # YAML specifications
|   +-- adsl_common.yaml    # Common variables
|   +-- adsl_project.yaml   # Project-level specs
|   +-- adsl_study.yaml     # Study-specific specs
|   +-- schema.yaml         # Validation schema
+-- data/                    # CDISC pilot study data
|   +-- sdtm/               # SDTM datasets (22 files)
|   +-- adam/               # ADaM datasets (10 files)
```

## Key Technologies
- **Python 3.10+**: Core programming language with modern type hints
- **Polars**: High-performance DataFrame library for data processing
- **PyYAML**: YAML parsing and generation
- **Pathlib**: Modern path handling
- **Dataclasses**: Structured data representation
- **Type hints**: Modern Python 3.10+ syntax (using `|` for unions)
- **unittest**: Built-in testing framework

## Module Architecture

### Design Principles
1. **Simplified Architecture**: Minimal abstraction layers, direct operations
2. **Column Renaming Strategy**: Source columns renamed to `{DOMAIN}.{column}` format
3. **Unified Derivation Interface**: All derivations return DataFrames directly
4. **No Complex Joins**: One row per key combination principle
5. **Clear Separation**: Specification handling vs. data processing
6. **Efficient Caching**: Source data loaded once with renaming, reused throughout

## Module Features

### 1. adam_yaml Module (Specification Handling)
- **AdamSpec Class**: Load and merge hierarchical YAML specifications
- **merge_yaml Function**: Generic YAML merging with strategies
- **SchemaValidator Class**: Pattern and type validation
- **Export Formats**: YAML, JSON, dictionary

### 2. adam_derivation Module (Data Processing)

#### Simplified Engine (engine.py)
```python
class AdamDerivation:
    def __init__(self, spec_path: str):
        self.spec = AdamSpec(spec_path)
        self.sdtm_loader = SDTMLoader(self.spec.sdtm_dir)
        self.target_df = pl.DataFrame()
        self.source_data = {}
    
    def _derive_column(self, col_spec: dict[str, Any]) -> None:
        derivation_obj = self._get_derivation(col_spec)
        self.target_df = derivation_obj.derive(self.source_data, self.target_df, col_spec)
```

#### Key Components
- **SDTMLoader**: Handles data loading with automatic column renaming
- **BaseDerivation**: Abstract base with unified `derive()` method returning DataFrames
- **Derivation Dispatch**: Integrated into engine's `_get_derivation()` method
- **Derivation Types**: Source, Constant, Aggregation, Custom, Categorization, Conditional

#### Column Renaming Strategy
- Source columns automatically renamed to `{DOMAIN}.{column}` format
- Key variables preserved without renaming
- Eliminates need for complex joining logic

## Usage Examples

### Specification Handling (adam_yaml)
```python
from src.adamyaml.adam_spec import AdamSpec

# Load and validate specification
spec = AdamSpec("spec/adsl_study.yaml", schema_path="spec/schema.yaml")
print(spec.domain)  # "ADSL"
print(spec.key)     # ['USUBJID', 'SUBJID']
```

### Dataset Generation (adam_derivation)
```python
from src.adamyaml.adam_derivation import AdamDerivation

# Create engine and build dataset
engine = AdamDerivation("spec/adsl_study.yaml")
adam_df = engine.build()
print(f"Generated {adam_df.height} rows, {adam_df.width} columns")
```

### How Column Renaming Works
```python
# Original SDTM data:
# DM dataset: USUBJID, AGE, SEX, ...
# VS dataset: USUBJID, VSTESTCD, VSORRES, ...

# After loading with rename_columns=True:
# DM: USUBJID, DM.AGE, DM.SEX, ...
# VS: USUBJID, VS.VSTESTCD, VS.VSORRES, ...

# In YAML specification:
derivation:
  source: DM.AGE  # References renamed column
```

## YAML Specification Structure

### Inheritance Model
1. **adsl_common.yaml**: Base template with common variables
2. **adsl_project.yaml**: Project-level specifications (inherits from common)
3. **adsl_study.yaml**: Study-specific specifications (inherits from project)

### Example Specification
```yaml
parents:
  - adsl_common.yaml
  - adsl_project.yaml

domain: ADSL
key: [DOMAIN, USUBJID]

columns:
  - name: USUBJID
    type: str
    label: Unique Subject Identifier
    core: cdisc-required
    derivation:
      source: DM.USUBJID
```

## Schema Rules

### Domain Naming
- Must start with "AD" prefix
- Maximum 8 characters
- Pattern: `^AD[A-Z0-9]{0,6}$`

### Column Naming
- Uppercase letters, numbers, underscore
- Maximum 8 characters
- Pattern: `^[A-Z][A-Z0-9_]{0,7}$`

### Required Fields
- Domain name
- Column specifications
- Column name, type, and derivation

## Testing

### Run All Tests
```bash
# From project root
uv run python run_tests.py

# Or using unittest
uv run python -m unittest discover -s src/adam_yaml/tests
```

### Test Coverage
- AdamSpec: 7 tests (loading, inheritance, validation, export)
- merge_yaml: 5 tests (strategies, edge cases)
- SchemaValidator: 6 tests (validation rules, patterns)

## Development Commands

```bash
# Install dependencies
uv sync

# Run tests
uv run python run_tests.py

# Test specific module
uv run python -m unittest adam_spec.tests.test_adam_spec

# Check for non-ASCII characters
find . -name "*.py" -exec grep -l "[^\x00-\x7F]" {} \;
```

## Important Notes

### ASCII-Only Policy
- All code uses ASCII characters only
- No emojis in code, comments, or commits
- Use [OK], [FAIL], [X], [!], [i] for status indicators
- Use +-- and | for tree structures

### Error Handling
- FileNotFoundError for missing files
- ValueError for invalid YAML
- Detailed validation error messages
- Warning logs for skipped validation

### Best Practices
- Always provide schema_path for validation
- Use hierarchical YAML structure for DRY principle
- Follow CDISC naming conventions
- Test all changes with unit tests

### Modern Python Type Hints (Python 3.10+)
- Use `str | None` instead of `Optional[str]`
- Use `list[str]` instead of `List[str]`
- Use `dict[str, Any]` instead of `Dict[str, Any]`
- Use `tuple[int, str]` instead of `Tuple[int, str]`
- Avoid importing from `typing` when built-in types work
- Only import `Any`, `TYPE_CHECKING` from typing when needed

## API Summary

### Classes
- **AdamSpec**: Main specification handler
- **Column**: Column specification dataclass
- **SchemaValidator**: Schema-based validator
- **ValidationResult**: Validation result dataclass

### Functions
- **merge_yaml()**: Merge multiple YAML files with strategies

### Properties
- **spec.domain**: Dataset domain name
- **spec.columns**: List of Column objects
- **spec.validation_errors**: List of validation errors
- **spec.is_valid**: Boolean validation status

## References
- [CDISC ADaM v2.1](https://www.cdisc.org/standards/foundational/adam)
- [CDISC Pilot Project](https://github.com/cdisc-org/sdtm-adam-pilot-project)
- [ADaM Implementation Guide](https://www.cdisc.org/standards/foundational/adam/adam-implementation-guide-v1-3)
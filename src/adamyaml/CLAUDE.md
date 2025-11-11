# adam_yaml Module Documentation

## Module Purpose
The `adam_yaml` module is a **YAML specification consolidation tool** for ADaM datasets. It handles the first step in the ADaM dataset generation pipeline: merging multiple hierarchical YAML specification files into a single, validated, consolidated YAML file.

## Scope and Boundaries

### What This Module DOES
- **Merge YAML Files**: Combines multiple YAML specifications using inheritance
- **Validate Specifications**: Ensures YAML conforms to CDISC ADaM schema rules
- **Handle Inheritance**: Supports parent-child YAML relationships (common -> project -> study)
- **Column Management**: Merges columns by name, supports dropping inherited columns
- **Export Formats**: Outputs consolidated YAML, JSON, or Python dictionaries

### What This Module DOES NOT DO
- **Execute Derivations**: Does not run the actual data transformations
- **Access Data**: Does not read SDTM/ADaM datasets or perform calculations
- **Generate Code**: Does not produce executable derivation code
- **Handle Metadata**: Does not manage Define-XML or other metadata formats

## Architecture Overview

```
adam_yaml/
+-- adam_spec.py         # Main class for loading and merging specs
+-- merge_yaml.py        # Generic YAML merging utilities
+-- schema_validator.py  # Schema-based validation engine
```

## Key Components

### 1. AdamSpec Class (adam_spec.py)
Main entry point for specification handling:
- Loads YAML files with automatic parent resolution
- Merges specifications hierarchically
- Validates against schema if provided
- Exports consolidated specification

### 2. merge_yaml Function (merge_yaml.py)
Generic YAML merging utility:
- Supports multiple merge strategies (replace, append, merge_by_key)
- Deep merging for nested structures
- Column-specific merging by name field

### 3. SchemaValidator Class (schema_validator.py)
Validation engine for specifications:
- Pattern validation (regex)
- Type checking
- Required field validation
- CDISC-specific rules (domain naming, column patterns)
- Detailed error and warning reporting

## Usage Pattern

### Basic Workflow
```python
from adam_yaml import AdamSpec

# Step 1: Load and consolidate specifications
spec = AdamSpec("spec/adsl_study.yaml", schema_path="spec/schema.yaml")

# Step 2: Validate consolidation
if not spec.is_valid:
    for error in spec.validation_errors:
        print(f"Error: {error}")

# Step 3: Export consolidated YAML
spec.save("spec/adsl_consolidated.yaml")

# Step 4: Pass to derivation engine (separate module)
# derivation_engine.execute(spec.to_dict())  # Not part of this module
```

### Inheritance Example
```yaml
# adsl_common.yaml - Base template
domain: ADSL
columns:
  - name: STUDYID
    type: str
    label: Study Identifier

# adsl_project.yaml - Project level
parents: [adsl_common.yaml]
columns:
  - name: STUDYID
    derivation:
      constant: "PROJ001"

# adsl_study.yaml - Study specific
parents: [adsl_project.yaml]
columns:
  - name: STUDYID
    derivation:
      constant: "STUDY001"  # Overrides project value
```

## Module Boundaries

### Input
- Multiple YAML specification files
- Optional schema YAML for validation

### Output
- Single consolidated YAML specification
- Validation results (errors, warnings)
- No data processing or code generation

### Integration Points
This module is designed as **Step 1** in a pipeline:
1. **adam_yaml** -> Consolidate YAML specifications
2. **Derivation Engine** -> Execute transformations (separate module)
3. **Output Writer** -> Generate final ADaM datasets (separate module)

## Key Design Decisions

### Why Separate Consolidation from Execution?
- **Modularity**: Clear separation of concerns
- **Testability**: Each component can be tested independently
- **Flexibility**: Different derivation engines can consume the same spec
- **Validation**: Catch specification errors before expensive data operations

### Merge Strategy
- Uses "merge_by_key" for columns to handle inheritance properly
- Later specifications override earlier ones
- Drop flag removes inherited columns entirely

### Validation Approach
- Schema-based validation using YAML schema definition
- Validates after merging (on final specification)
- Separates errors (must fix) from warnings (should review)

## Testing

### Test Coverage
- **adam_spec**: Loading, inheritance, validation, export formats
- **merge_yaml**: All merge strategies, edge cases
- **schema_validator**: Pattern matching, type checking, custom rules

### Running Tests
```bash
# From project root
uv run python -m unittest discover -s src/adam_yaml/tests
```

## Limitations and Assumptions

### Current Limitations
1. **Column Ordering**: No explicit control over column order in output
2. **Circular Dependencies**: No detection of circular parent references
3. **Performance**: Reloads parent files for each specification
4. **Merge Conflicts**: No detailed reporting of what was overridden

### Assumptions
1. All YAML files use consistent structure
2. Parent files exist in same directory as child files
3. Schema file follows the defined schema structure
4. Column names are unique within a specification

## Future Enhancements (Out of Scope)

These would require separate modules:
- Derivation execution engine
- Data validation against actual datasets
- Define-XML generation
- Data preparation code generation

## Error Handling

### Common Errors
- **FileNotFoundError**: Missing YAML or parent files
- **ValueError**: Invalid YAML syntax
- **Validation Errors**: Schema violations (domain naming, required fields)

### Error Recovery
- Module fails fast on file/syntax errors
- Collects all validation errors before reporting
- Continues processing despite warnings

## Performance Considerations

### Current Performance
- Linear time complexity for merging
- No caching of loaded files
- Suitable for typical specification sizes (100s of columns)

### Not Optimized For
- Very large specifications (1000s of columns)
- Real-time specification editing
- Concurrent specification processing

## ASCII-Only Policy
- All code uses ASCII characters only
- No emojis or special Unicode characters
- Status indicators: [OK], [FAIL], [X], [!], [i]
- Tree structures: +-- and |

## Summary

The `adam_yaml` module is a **focused, single-purpose tool** for consolidating ADaM YAML specifications. It does this job well with proper validation and flexible merging strategies. It explicitly does not handle derivation execution, which should be implemented in a separate module that consumes the consolidated specifications produced by this module.
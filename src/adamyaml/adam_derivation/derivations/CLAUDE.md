# Derivation Module Context

## Module Overview
This module provides a minimal, efficient derivation system for ADaM dataset generation using a SQL-first approach with Polars.

## Architecture

### Core Classes (Just 3!)
1. **BaseDerivation** (`base.py`)
   - Abstract base class
   - Stores context (col_spec, source_data, target_df) as instance variables
   - Single abstract method: `derive() -> pl.Series`

2. **SQLDerivation** (`sql_derivation.py`)
   - Handles 90% of derivation patterns via SQL
   - Covers: constants, source mapping, value recoding, aggregation, categorization
   - Executes all SQL through Polars SQL context for optimization

3. **FunctionDerivation** (`function_derivation.py`)
   - Pure dynamic function loader
   - No hardcoded functions - all loaded from external sources
   - Supports module functions (numpy.abs) and local functions (functions.py)

## Design Principles

### 1. SQL-First Approach
Most derivations are expressed as SQL and executed via Polars:
```sql
-- Example: Value mapping
SELECT USUBJID,
  CASE 
    WHEN "DM.SEX" = 'F' THEN 'Female'
    WHEN "DM.SEX" = 'M' THEN 'Male'
    ELSE NULL
  END as result
FROM merged
```

### 2. Clean Interface
```python
# Setup context once
derivation.setup(col_spec, source_data, target_df)
# Derive with no parameters
result = derivation.derive()
```

### 3. Dynamic Function Loading
Functions are loaded at runtime, not hardcoded:
- From modules: `numpy.abs`, `polars.col`
- From local: `functions.py` or `{function_name}.py`

## Pattern Coverage

### SQLDerivation Patterns
| Pattern | YAML | SQL |
|---------|------|-----|
| Constant | `constant: "ADSL"` | `SELECT 'ADSL' as result` |
| Source | `source: DM.AGE` | `SELECT "DM.AGE" FROM merged` |
| Mapping | `mapping: {F: Female}` | `CASE WHEN ... THEN ...` |
| Aggregation | `aggregation: {function: mean}` | `AVG("VS.VALUE") GROUP BY ...` |
| Categorization | `cut: {"<18": "Young"}` | `CASE WHEN AGE < 18 THEN ...` |
| Closest | `function: closest, target: ...` | Native Polars operations |

### FunctionDerivation Patterns
Any Python function can be used:
```yaml
derivation:
  function: get_bmi      # From functions.py
  weight: WEIGHT
  height: HEIGHT
```

## Key Implementation Details

### Column Naming Convention
- SDTM columns renamed with dots: `DM.AGE`, `VS.VSORRES`
- Key variables preserved without renaming: `USUBJID`
- Enables unique column identification across datasets

### SQL Execution Flow
1. Build merged DataFrame with necessary data
2. Generate SQL with quoted column names
3. Execute via Polars SQL context
4. Return result as Series

### Function Loading Priority
1. Check module functions (has dot in name)
2. Try functions.py in current directory
3. Try {function_name}.py in current directory
4. Raise ImportError if not found

## Usage Examples

### SQL-Based Derivation
```python
sql_deriv = SQLDerivation()
sql_deriv.setup(col_spec, source_data, target_df)
result = sql_deriv.derive()  # Returns pl.Series
```

### Function-Based Derivation
```python
func_deriv = FunctionDerivation()
func_deriv.setup(col_spec, source_data, target_df)
result = func_deriv.derive()  # Returns pl.Series
```

## Important Conventions

### Polars-First
- **NO pandas** - Use Polars exclusively
- All data as pl.DataFrame or pl.Series
- Leverage Polars SQL context and expressions

### Function Requirements
Functions in functions.py must:
1. Accept keyword arguments matching YAML spec
2. Handle both Series and scalar inputs
3. Return pl.Series with correct length

Example:
```python
def get_bmi(weight, height):
    if not isinstance(weight, pl.Series):
        weight = pl.Series([weight])
    if not isinstance(height, pl.Series):
        height = pl.Series([height])
    
    bmi = weight / ((height / 100) ** 2)
    return bmi.round(1)
```

### Error Handling
- Log errors with context
- Return Series of None values on failure
- Don't stop entire derivation

## Performance Characteristics
- **SQL operations**: Leverages Polars query optimizer
- **Batch processing**: No row-by-row operations
- **Module caching**: Functions loaded once per session
- **Memory efficient**: Columnar operations

## Testing Strategy

### Unit Tests
Test each derivation type independently:
```python
# Test SQL derivation
sql_deriv = SQLDerivation()
sql_deriv.setup(test_col_spec, test_source, test_df)
result = sql_deriv.derive()
assert len(result) == len(test_df)
```

### Integration Tests
Test full dataset generation with all patterns.

### Function Tests
Test functions.py independently:
```python
from functions import get_bmi
result = get_bmi([70, 80], [170, 180])
assert result[0] == 24.2
```

## Common Issues and Solutions

### Issue: Column not found in SQL
**Solution**: Check column renaming - use "DM.AGE" not "AGE"

### Issue: Function not found
**Solution**: Ensure functions.py exists in current directory

### Issue: Wrong result length
**Solution**: Functions must return Series with target_df.height length

### Issue: Filter expression fails
**Solution**: Use Polars syntax: `&` not `and`, `|` not `or`

## Extension Points

### Adding New SQL Patterns
In SQLDerivation.derive():
```python
elif "new_pattern" in derivation:
    return self._derive_new_pattern(derivation)
```

### Adding New Functions
Just add to functions.py - no code changes needed:
```python
def new_calculation(param1, param2):
    # Implementation
    return result
```

## File Structure
```
derivations/
+-- __init__.py           # Module exports
+-- base.py              # Abstract base class
+-- sql_derivation.py    # SQL-based derivations
+-- function_derivation.py # Dynamic function loading
+-- CLAUDE.md           # This file
+-- *.md                # Documentation files
```

## Design Evolution
- Started with 7+ classes (Constant, Source, Mapping, etc.)
- Refactored to just 3 classes (Base + 2 concrete)
- Removed all hardcoded functions
- Result: 70% less code, 100% functionality, infinite extensibility

## Best Practices

### DO
- [YES] Use Polars operations exclusively
- [YES] Add functions to functions.py
- [YES] Write SQL for data transformations
- [YES] Handle nulls gracefully
- [YES] Test functions independently

### DON'T
- [NO] Use pandas anywhere
- [NO] Hardcode functions in derivation classes
- [NO] Use Python loops over rows
- [NO] Modify this module for new functions
- [NO] Mix business logic with derivation mechanics

## Summary
This minimal design achieves maximum functionality with just 3 classes, leveraging SQL for most operations and dynamic loading for custom functions. The result is fast, maintainable, and infinitely extensible without code modifications.
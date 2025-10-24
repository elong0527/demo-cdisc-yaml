# YAML Specifications Context

## Overview
This directory contains YAML specification files for ADaM datasets following CDISC standards.

## Files Structure

### Core Specifications
- **adsl_common.yaml**: Base template with common ADaM variables shared across all datasets
- **adsl_project.yaml**: Project-level specifications that inherit from common
- **adsl_study.yaml**: Study-specific specifications that inherit from project

### Schema
- **schema.yaml**: Validation schema defining rules and constraints for specifications

## Inheritance Model
```
adsl_common.yaml (base)
    +-- adsl_project.yaml (inherits common)
        +-- adsl_study.yaml (inherits project)
```

## Key Concepts

### Column Specifications
Each column in the YAML files includes:
- **name**: Variable name (8 chars max, uppercase)
- **type**: Data type (str, int, float, date, datetime)
- **label**: Human-readable description
- **core**: CDISC requirement level
- **derivation**: Source and transformation logic

### Core Values
- **cdisc-required**: Required by CDISC standards
- **org-required**: Required by organization
- **expected**: Conditionally expected
- **permissible**: Optional but allowed

### Derivation Types
- **source**: Direct mapping from SDTM
- **constant**: Fixed values

## Validation Rules
- Domain names must start with "AD" (e.g., ADSL, ADAE)
- Column names: uppercase, max 8 characters
- Required fields: domain, columns, column.name, column.type

## Update final spec 

```python
# create spec with schema validation
adsl_spec1 = AdamSpec("spec/adsl_study1.yaml", schema_path="spec/schema.yaml")
adsl_spec2 = AdamSpec("spec/adsl_study2.yaml", schema_path="spec/schema.yaml")

# store the combined YAML file
adsl_spec1.save("spec/adsl_study_combined1.yaml")
adsl_spec2.save("spec/adsl_study_combined2.yaml")
```

# ADaM Variable Derivation Methods

## Assumptions

- XX.YYYY are variables from a SDTM.XX or ADaM.XX dataset YYYY variable.
- YYYY are variables from current dataset. 
- date and time imputation following pre-specified business rule. 
- tie breaker following pre-specified business rule.

## Core Derivation Patterns

### Method 1: Constant Assignment
**Use Case**: Fixed values across all records (e.g., STUDYID, DOMAIN)
- Apply **constant** value to all records
- No validation required
- Example: `STUDYID = "CDISCPILOT01"`

### Method 2: Direct Source Mapping  
**Use Case**: One-to-one variable mapping from SDTM
- Apply **filter** conditions if specified
- Map **source** variable using subject **key** for row matching
- Validate exactly one source value per subject
- Example: `AGE from DM.AGE`

### Method 3: Source with Value Recoding
**Use Case**: Variable mapping with value transformation
- Apply **filter** conditions if specified
- Map **source** variable using subject **key**
- Apply **mapping** dictionary for value recoding
- Handle unmapped values (null, default, error)
- Validate exactly one source value per subject
- Example: `SEX from DM.SEX with F->Female, M->Male`

### Method 4: Source with Aggregation
**Use Case**: Summarizing multiple records per subject
- Apply **filter** conditions if specified
- Group records by subject **key**
- Apply **aggregation** function:
  - Statistical: mean, median, min, max, sum, count
  - Temporal: first, last, closest (to reference date)
  - Custom: user-defined functions
- Handle missing/partial data per rules
- Example: `WEIGHT from VS where VSTESTCD="WEIGHT" that before and closest to start date`

### Method 5: Conditional/Derived Logic
**Use Case**: Complex business rules and calculations
- Apply **filter** conditions if specified
- Group records by subject **key**
- Apply **cut** to break a numeric value into ordered group.
- Example: `AGEGR1 based on AGE ranges`

### Method 6: Custom Function Application
**Use Case**: Study-specific complex algorithms
- Apply custom **function** with **arguments**
- Support external function libraries
- Pass multiple input variables
- Handle function errors gracefully
- Document function specifications
- Example: `BMI derivation using HEIGHT and WEIGHT`

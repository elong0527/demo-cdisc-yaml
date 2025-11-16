# Demo project for CDISC datasets and TLFs generation

- A hierarchical YAML-based specification system for defining SDTM and ADaM datasets starting from ODM XML files in clinical trials, following CDISC standards.
- Creating TLFs using SDTM / ADaM datasets as source. 

## Overview on ADaM datasets

This project provides a flexible and maintainable way to define ADaM dataset specifications using YAML files with inheritance and validation capabilities. It enables clinical data programmers to create reusable, hierarchical specifications that follow CDISC ADaM standards.

## Features

- **Hierarchical Inheritance**: Build specifications from multiple YAML files with inheritance
- **Smart Merging**: Override and extend parent specifications at any level
- **Comprehensive Validation**: Validate specifications against defined schema rules
- **Multiple Output Formats**: Display specs as YAML, JSON, or readable tables
- **CDISC Compliant**: Follows ADaM v2.1 standards and implementation guides

## Installation

### Using uv (recommended)

```bash
# Clone the repository
git clone https://github.com/elong0527/demo_adam_yaml
cd demo_adam_yaml

# Install dependencies with uv
uv sync

# Activate the environment
source .venv/bin/activate
```

### Using pip

```bash
# Install in development mode
pip install -e .

# Or install from source
pip install .
```

### Inheritance Model

1. **Common Level** (`adsl_common.yaml`): Base specifications used across all studies
2. **Project Level** (`adsl_project.yaml`): Project-specific overrides and additions
3. **Study Level** (`adsl_study.yaml`): Study-specific final specifications

## Data Preparation

The project includes CDISC pilot study data. To prepare the data:

```bash
# Run the data preparation script
python script/prepare_data.py
```

This downloads SDTM and ADaM datasets from the CDISC pilot project and converts them to Parquet format.

## Development

### Running Tests

```bash
# Run all tests
uv run pytest

# Run specific test module
PYTHONPATH=src python -m unittest adam_yaml.tests.test_models -v
```

### Code Quality

```bash
# Format code
uv run black src/

# Lint code
uv run ruff check src/

# Type checking
uv run mypy src/
```

## References

- [CDISC ADaM v2.1](https://www.cdisc.org/standards/foundational/adam)
- [ADaM Implementation Guide v1.3](https://www.cdisc.org/standards/foundational/adam/adam-implementation-guide-v1-3)
- [CDISC Pilot Project](https://github.com/cdisc-org/sdtm-adam-pilot-project)

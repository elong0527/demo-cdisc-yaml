"""
Minimal unit tests for SchemaValidator class
"""

import unittest
import tempfile
from pathlib import Path
import yaml
from adamyaml.adam_spec import SchemaValidator


class TestSchemaValidator(unittest.TestCase):
    """Test SchemaValidator functionality"""
    
    def setUp(self):
        """Create test schema and spec"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        
        # Create test schema
        self.schema_file = self.temp_path / "test_schema.yaml"
        with open(self.schema_file, 'w') as f:
            yaml.dump({
                "root": {
                    "required": ["domain", "columns"],
                    "optional": ["key"]
                },
                "fields": {
                    "domain": {
                        "type": "str",
                        "pattern": "^AD[A-Z0-9]{0,6}$"
                    }
                },
                "column": {
                    "required": ["name", "type"],
                    "fields": {
                        "name": {
                            "pattern": "^[A-Z][A-Z0-9_]{0,7}$"
                        },
                        "type": {
                            "allowed_values": ["str", "int", "float"]
                        }
                    }
                }
            }, f)
        
        # Valid spec
        self.valid_spec = {
            "domain": "ADSL",
            "columns": [
                {"name": "USUBJID", "type": "str"},
                {"name": "AGE", "type": "int"}
            ]
        }
        
        # Invalid spec
        self.invalid_spec = {
            "domain": "INVALID",  # Doesn't start with AD
            "columns": [
                {"name": "lowercase", "type": "str"},  # Invalid name
                {"name": "GOOD", "type": "unknown"}  # Invalid type
            ]
        }
    
    def tearDown(self):
        """Clean up temporary files"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_valid_spec(self):
        """Test validation of valid specification"""
        validator = SchemaValidator(self.schema_file)
        results = validator.validate(self.valid_spec)
        
        self.assertTrue(validator.is_valid())
        self.assertEqual(len(validator.get_errors()), 0)
    
    def test_invalid_spec(self):
        """Test validation of invalid specification"""
        validator = SchemaValidator(self.schema_file)
        results = validator.validate(self.invalid_spec)
        
        self.assertFalse(validator.is_valid())
        errors = validator.get_errors()
        self.assertTrue(len(errors) > 0)
    
    def test_missing_required_field(self):
        """Test detection of missing required fields"""
        spec_missing_domain = {
            "columns": [{"name": "COL1", "type": "str"}]
        }
        
        validator = SchemaValidator(self.schema_file)
        validator.validate(spec_missing_domain)
        
        self.assertFalse(validator.is_valid())
        errors = validator.get_errors()
        self.assertTrue(any("domain" in str(e.message) for e in errors))
    
    def test_pattern_validation(self):
        """Test pattern matching validation"""
        spec_bad_pattern = {
            "domain": "NOTADAM",  # Doesn't match pattern
            "columns": [{"name": "TEST", "type": "str"}]
        }
        
        validator = SchemaValidator(self.schema_file)
        validator.validate(spec_bad_pattern)
        
        self.assertFalse(validator.is_valid())
    
    def test_summary_output(self):
        """Test summary generation"""
        validator = SchemaValidator(self.schema_file)
        validator.validate(self.valid_spec)
        
        summary = validator.summary()
        self.assertIn("Valid: True", summary)
    
    def test_missing_schema_file(self):
        """Test error handling for missing schema file"""
        with self.assertRaises(FileNotFoundError):
            SchemaValidator("nonexistent_schema.yaml")


if __name__ == '__main__':
    unittest.main()
"""
Minimal unit tests for AdamSpec class
"""

import unittest
from pathlib import Path
import tempfile
import yaml
from adamyaml.adam_spec import AdamSpec


class TestAdamSpec(unittest.TestCase):
    """Test AdamSpec functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Find project root (where spec folder is)
        current = Path(__file__).parent
        while current != current.parent:
            if (current / "spec").exists():
                self.test_dir = current / "spec"
                break
            current = current.parent
        else:
            # Fallback to relative path from tests directory
            self.test_dir = Path(__file__).parent.parent.parent.parent / "spec"
        
        self.test_file = self.test_dir / "study1" / "adsl_study1.yaml"
    
    def test_load_spec(self):
        """Test basic loading of specification"""
        spec = AdamSpec(self.test_file)
        self.assertEqual(spec.domain, "ADSL")
        self.assertIsInstance(spec.columns, list)
        self.assertTrue(len(spec.columns) > 0)
    
    def test_inheritance(self):
        """Test parent file inheritance"""
        spec = AdamSpec(self.test_file)
        self.assertTrue(len(spec.parents) > 0)
        # Check that columns from parents are included
        col_names = {col.name for col in spec.columns}
        self.assertIn("USUBJID", col_names)
    
    
    def test_export_formats(self):
        """Test export to different formats"""
        spec = AdamSpec(self.test_file)
        
        # Test to_dict
        spec_dict = spec.to_dict()
        self.assertIn("domain", spec_dict)
        self.assertIn("columns", spec_dict)
        
        # Test to_yaml
        yaml_str = spec.to_yaml()
        self.assertIsInstance(yaml_str, str)
        self.assertIn("domain:", yaml_str)
    
    def test_missing_file(self):
        """Test error handling for missing file"""
        with self.assertRaises(FileNotFoundError):
            AdamSpec("nonexistent.yaml")
    
    def test_invalid_yaml(self):
        """Test error handling for invalid YAML"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: [")
            temp_path = f.name
        
        try:
            with self.assertRaises(ValueError):
                AdamSpec(temp_path)
        finally:
            Path(temp_path).unlink()


if __name__ == '__main__':
    unittest.main()
"""
Minimal unit tests for merge_yaml function
"""

import unittest
import tempfile
from pathlib import Path
import yaml
from adamyaml.adam_spec import merge_yaml


class TestMergeYaml(unittest.TestCase):
    """Test merge_yaml functionality"""
    
    def setUp(self):
        """Create temporary YAML files for testing"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        
        # Create test YAML files
        self.file1 = self.temp_path / "base.yaml"
        self.file2 = self.temp_path / "override.yaml"
        
        with open(self.file1, 'w') as f:
            yaml.dump({
                "domain": "BASE",
                "key": ["ID"],
                "columns": [
                    {"name": "COL1", "type": "str"},
                    {"name": "COL2", "type": "int"}
                ]
            }, f)
        
        with open(self.file2, 'w') as f:
            yaml.dump({
                "domain": "OVERRIDE",
                "columns": [
                    {"name": "COL2", "type": "float"},
                    {"name": "COL3", "type": "str"}
                ]
            }, f)
    
    def tearDown(self):
        """Clean up temporary files"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_simple_merge(self):
        """Test basic merging with replace strategy"""
        result = merge_yaml([str(self.file1), str(self.file2)])
        
        # Later file should override
        self.assertEqual(result["domain"], "OVERRIDE")
        # Key should remain from first file
        self.assertEqual(result["key"], ["ID"])
        # Columns should be replaced
        self.assertEqual(len(result["columns"]), 2)
    
    def test_append_strategy(self):
        """Test list append strategy"""
        result = merge_yaml(
            [str(self.file1), str(self.file2)],
            list_merge_strategy="append"
        )
        
        # Columns should be concatenated
        self.assertEqual(len(result["columns"]), 4)
    
    def test_merge_by_key_strategy(self):
        """Test merge by key strategy"""
        result = merge_yaml(
            [str(self.file1), str(self.file2)],
            list_merge_strategy="merge_by_key",
            list_merge_keys={"columns": "name"}
        )
        
        # Should have 3 unique columns (COL1, COL2 merged, COL3)
        self.assertEqual(len(result["columns"]), 3)
        
        # COL2 should have updated type
        col2 = next(c for c in result["columns"] if c["name"] == "COL2")
        self.assertEqual(col2["type"], "float")
    
    def test_empty_file_list(self):
        """Test with empty file list"""
        result = merge_yaml([])
        self.assertEqual(result, {})
    
    def test_single_file(self):
        """Test with single file"""
        result = merge_yaml([str(self.file1)])
        self.assertEqual(result["domain"], "BASE")


if __name__ == '__main__':
    unittest.main()
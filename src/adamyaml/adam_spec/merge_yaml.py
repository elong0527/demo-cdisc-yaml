import yaml
from pathlib import Path
from typing import Any
from copy import deepcopy


def merge_yaml(
    paths: list[str | Path], 
    list_merge_strategy: str = "replace",
    list_merge_keys: dict[str, str] = None
) -> dict[str, Any]:
    """
    Merge multiple YAML files in order with deep merging
    
    Args:
        paths: List of YAML file paths to merge in order
        list_merge_strategy: How to merge lists:
            - "replace": Replace entire list (default)
            - "append": Append items from override to base
            - "merge_by_key": Merge list items by matching a key field
        list_merge_keys: Dict mapping list field names to their merge key
            e.g., {"columns": "name"} means merge columns by matching "name" field
    
    Returns:
        Merged dictionary from all YAML files
    
    Examples:
        # Simple merge (lists replaced)
        result = merge_yaml(["file1.yaml", "file2.yaml"])
        
        # Merge with column deep merging
        result = merge_yaml(
            ["base.yaml", "override.yaml"],
            list_merge_strategy="merge_by_key",
            list_merge_keys={"columns": "name"}
        )
    """
    list_merge_keys = list_merge_keys or {}
    
    def merge_lists(base_list: list, override_list: list, key_field: str = None) -> list:
        """Merge two lists based on strategy"""
        if list_merge_strategy == "append":
            return base_list + override_list
        elif list_merge_strategy == "merge_by_key" and key_field:
            # Deep merge list items by matching key field
            result_dict = {}
            # Add all base items
            for item in base_list:
                if isinstance(item, dict) and key_field in item:
                    result_dict[item[key_field]] = deepcopy(item)
                else:
                    # If no key, just append
                    return base_list + override_list
            # Merge override items
            for item in override_list:
                if isinstance(item, dict) and key_field in item:
                    key = item[key_field]
                    if key in result_dict:
                        # Deep merge the item
                        result_dict[key] = deep_merge(result_dict[key], item, path="")
                    else:
                        result_dict[key] = deepcopy(item)
            return list(result_dict.values())
        else:
            # Default: replace
            return override_list
    
    def deep_merge(base: Any, override: Any, path: str = "") -> Any:
        """Deep merge two values"""
        if isinstance(base, dict) and isinstance(override, dict):
            result = deepcopy(base)
            for key, value in override.items():
                new_path = f"{path}.{key}" if path else key
                if key in result:
                    result[key] = deep_merge(result[key], value, new_path)
                else:
                    result[key] = deepcopy(value)
            return result
        elif isinstance(base, list) and isinstance(override, list):
            # Check if this list field has a merge key defined
            key_field = None
            if path in list_merge_keys:
                key_field = list_merge_keys[path]
            return merge_lists(base, override, key_field)
        else:
            return deepcopy(override)
    
    # Start with empty dict
    merged = {}
    
    # Merge each file in order
    for path in paths:
        with open(path, 'r') as f:
            content = yaml.safe_load(f) or {}
        merged = deep_merge(merged, content)
    
    return merged
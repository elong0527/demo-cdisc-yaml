"""
ODM (Operational Data Model) XML loader for OpenClinica data.

This module provides functionality to load and parse ODM XML files
containing clinical trial data from OpenClinica.
"""

import xml.etree.ElementTree as ET
from pathlib import Path
import polars as pl
import re


def get_struct_columns(df: pl.DataFrame) -> list[str]:
    """
    Get list of column names that have struct data types.

    Args:
        df: DataFrame to inspect

    Returns:
        List of column names with struct data types
    """
    return [col for col in df.columns if isinstance(df[col].dtype, pl.Struct)]


def remove_namespaces(xml_content: str) -> str:
    """
    Remove XML namespaces to simplify parsing.

    Args:
        xml_content: Raw XML content string

    Returns:
        Cleaned XML content without namespaces
    """
    # Remove xmlns declarations
    xml_content = re.sub(r'\s*xmlns[^=]*="[^"]*"', '', xml_content)
    xml_content = re.sub(r'\s*xmlns[^=]*=\'[^\']*\'', '', xml_content)

    # Remove namespace prefixes from opening tags
    xml_content = re.sub(r'<([^/>\s]+:)([^>\s/]+)', r'<\2', xml_content)
    # Remove namespace prefixes from closing tags
    xml_content = re.sub(r'</([^>\s]+:)([^>\s]+)', r'</\2', xml_content)
    # Remove namespace prefixes from attributes
    xml_content = re.sub(r'(\s)([^=\s]+:)([^=\s]+)=', r'\1\3=', xml_content)

    return xml_content


def odm_xml_to_df_dict(file_path: str | Path) -> pl.DataFrame:
    """
    Load ODM XML into a DataFrame with struct columns.

    Creates one row per item with hierarchical data in struct columns.
    Automatically handles duplicate field names by prefixing and converts all to lowercase.

    Args:
        file_path: Path to ODM XML file

    Returns:
        DataFrame with 6 struct columns: study, subject, event, form, item_group, item

    Example:
        >>> df = odm_xml_to_df_dict('data.xml')
        >>> df.columns
        ['study', 'subject', 'event', 'form', 'item_group', 'item']
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"ODM XML file not found: {file_path}")

    try:
        # Read XML content and remove namespaces
        with open(file_path, 'r', encoding='utf-8') as f:
            xml_content = f.read()

        clean_content = remove_namespaces(xml_content)
        root = ET.fromstring(clean_content)
    except ET.ParseError as e:
        raise ET.ParseError(f"Failed to parse ODM XML file: {e}")
    except UnicodeDecodeError as e:
        raise ValueError(f"Failed to read ODM XML file with UTF-8 encoding: {e}")

    # Extract data from ODM structure
    data_records = []

    # Navigate through ODM structure: ODM > ClinicalData > SubjectData > StudyEventData > FormData > ItemGroupData > ItemData
    for clinical_data in root.findall('ClinicalData'):
        study = clinical_data.attrib

        for subject_data in clinical_data.findall('SubjectData'):
            subject = subject_data.attrib

            for study_event_data in subject_data.findall('StudyEventData'):
                event = study_event_data.attrib

                for form_data in study_event_data.findall('FormData'):
                    form = form_data.attrib

                    for item_group_data in form_data.findall('ItemGroupData'):
                        item_group = item_group_data.attrib

                        for item_data in item_group_data.findall('ItemData'):
                            item = item_data.attrib

                            # Create record for each item
                            record = {
                                'study': study,
                                'subject': subject,
                                'event': event,
                                'form': form,
                                'item_group': item_group,
                                'item': item,
                            }
                            data_records.append(record)

    df = pl.DataFrame(data_records)

    # Handle duplicate field names in struct columns using selectors
    # Find duplicate field names across all struct columns
    all_field_names = []
    for col in get_struct_columns(df):
        struct_dtype = df[col].dtype
        all_field_names.extend(struct_dtype.to_schema().keys())

    # Identify duplicated field names
    duplicated_fields = {name for name in set(all_field_names) if all_field_names.count(name) > 1}

    # Rename fields in structs: add prefix only to duplicated fields
    struct_transformations = []
    for col in get_struct_columns(df):
        struct_dtype = df[col].dtype
        original_fields = list(struct_dtype.to_schema().keys())
        new_field_names = []

        for field_name in original_fields:
            if field_name in duplicated_fields:
                new_field_names.append(f"{col}_{field_name}".lower())
            else:
                new_field_names.append(field_name.lower())

        # Add transformation for this struct column
        struct_transformations.append(
            pl.col(col).struct.rename_fields(new_field_names)
        )

    # Apply all struct transformations at once
    if struct_transformations:
        df = df.with_columns(struct_transformations)

    return df

def odm_xml_to_df(file_path: str | Path) -> pl.DataFrame:
    """
    Load ODM XML into a flattened DataFrame.

    Unnests struct columns into individual columns with smart naming:
    only duplicated fields get prefixes, unique fields stay clean.

    Args:
        file_path: Path to ODM XML file

    Returns:
        Flattened DataFrame with lowercase column names

    Example:
        >>> df = odm_xml_to_df('data.xml')
        >>> 'study_translateoid' in df.columns  # True (was duplicated)
        >>> 'studyoid' in df.columns  # True (was unique, no prefix)
    """
    df_dict = odm_xml_to_df_dict(file_path)
    struct_cols = get_struct_columns(df_dict)
    return df_dict.unnest(struct_cols)
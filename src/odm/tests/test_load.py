"""
Unit tests for ODM load module.
"""

import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

import polars as pl
import polars.selectors as cs

from src.odm.load import odm_xml_to_df, odm_xml_to_df_dict, remove_namespaces


class TestRemoveNamespaces(unittest.TestCase):
    """Test remove_namespaces function"""

    def test_remove_xmlns_declarations_double_quotes(self):
        """Test removal of xmlns declarations with double quotes"""
        xml = '<root xmlns="http://example.com" xmlns:ns="http://ns.com">content</root>'
        result = remove_namespaces(xml)
        expected = "<root>content</root>"
        self.assertEqual(result, expected)

    def test_remove_xmlns_declarations_single_quotes(self):
        """Test removal of xmlns declarations with single quotes"""
        xml = "<root xmlns='http://example.com' xmlns:ns='http://ns.com'>content</root>"
        result = remove_namespaces(xml)
        expected = "<root>content</root>"
        self.assertEqual(result, expected)

    def test_remove_namespace_prefixes_tags(self):
        """Test removal of namespace prefixes from tags"""
        xml = "<ns:root><ns:child>content</ns:child></ns:root>"
        result = remove_namespaces(xml)
        expected = "<root><child>content</child></root>"
        self.assertEqual(result, expected)

    def test_remove_namespace_prefixes_attributes(self):
        """Test removal of namespace prefixes from attributes"""
        xml = '<root ns:attr="value" other="normal">content</root>'
        result = remove_namespaces(xml)
        expected = '<root attr="value" other="normal">content</root>'
        self.assertEqual(result, expected)

    def test_complex_xml_with_namespaces(self):
        """Test complex XML with multiple namespace features"""
        xml = """<ns:ODM xmlns:ns="http://www.cdisc.org/ns/odm/v1.3"
                 xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
                 <ns:ClinicalData ns:StudyOID="STUDY001">
                   <ns:SubjectData ns:SubjectKey="001">
                     <ns:StudyEventData xsi:type="event">data</ns:StudyEventData>
                   </ns:SubjectData>
                 </ns:ClinicalData>
               </ns:ODM>"""
        result = remove_namespaces(xml)

        # Should remove all namespace prefixes and declarations
        self.assertNotIn("xmlns", result)
        self.assertNotIn("ns:", result)
        self.assertNotIn("xsi:", result)
        self.assertIn("<ODM>", result)
        self.assertIn("<ClinicalData", result)

    def test_empty_string(self):
        """Test with empty string"""
        result = remove_namespaces("")
        self.assertEqual(result, "")

    def test_xml_without_namespaces(self):
        """Test XML that already has no namespaces"""
        xml = '<root><child attr="value">content</child></root>'
        result = remove_namespaces(xml)
        self.assertEqual(result, xml)


class TestODMXMLToDataFrame(unittest.TestCase):
    """Test ODM XML to DataFrame conversion functions"""

    def setUp(self):
        """Set up test fixtures"""
        # Create sample ODM XML content for testing
        self.sample_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <ODM xmlns="http://www.cdisc.org/ns/odm/v1.3">
          <ClinicalData StudyOID="STUDY001" TranslateOID="false">
            <SubjectData SubjectKey="001" TranslateOID="true" Sex="M" DateOfBirth="1990-01-01">
              <StudyEventData StudyEventOID="SE_VISIT1" StartDate="2023-01-15">
                <FormData FormOID="F_DEMOGRAPHICS">
                  <ItemGroupData ItemGroupOID="IG_DEMO" TransactionType="Insert">
                    <ItemData ItemOID="I_AGE" Value="33" DataType="integer"/>
                    <ItemData ItemOID="I_HEIGHT" Value="175" DataType="float"/>
                  </ItemGroupData>
                  <ItemGroupData ItemGroupOID="IG_DEMO" TransactionType="Insert">
                    <ItemData ItemOID="I_WEIGHT" Value="75" DataType="float"/>
                  </ItemGroupData>
                </FormData>
              </StudyEventData>
            </SubjectData>
            <SubjectData SubjectKey="002" TranslateOID="false" Sex="F" DateOfBirth="1985-05-20">
              <StudyEventData StudyEventOID="SE_VISIT1" StartDate="2023-01-16">
                <FormData FormOID="F_DEMOGRAPHICS">
                  <ItemGroupData ItemGroupOID="IG_DEMO" TransactionType="Insert">
                    <ItemData ItemOID="I_AGE" Value="38" DataType="integer"/>
                  </ItemGroupData>
                </FormData>
              </StudyEventData>
            </SubjectData>
          </ClinicalData>
        </ODM>"""

        # Create a temporary XML file
        self.temp_file = tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False)
        self.temp_file.write(self.sample_xml)
        self.temp_file.close()
        self.temp_path = Path(self.temp_file.name)

    def tearDown(self):
        """Clean up test fixtures"""
        if self.temp_path.exists():
            self.temp_path.unlink()

    def test_file_not_found(self):
        """Test error handling for non-existent file"""
        with self.assertRaises(FileNotFoundError):
            odm_xml_to_df_dict("nonexistent.xml")

    def test_malformed_xml(self):
        """Test error handling for malformed XML"""
        bad_xml = "<ODM><unclosed_tag></ODM>"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
            f.write(bad_xml)
            temp_path = f.name

        try:
            with self.assertRaises(ET.ParseError):
                odm_xml_to_df_dict(temp_path)
        finally:
            Path(temp_path).unlink()

    def test_odm_xml_to_df_dict_structure(self):
        """Test that odm_xml_to_df_dict returns correct structure"""
        df = odm_xml_to_df_dict(self.temp_path)

        # Check column structure
        expected_columns = ["study", "subject", "event", "form", "item_group", "item"]
        self.assertEqual(df.columns, expected_columns)

        # Check that all columns are struct type
        for col in df.columns:
            self.assertEqual(df[col].dtype, pl.Struct)

        # Check that we have the expected number of rows (4 items total)
        self.assertEqual(df.height, 4)

    def test_odm_xml_to_df_dict_duplicate_field_handling(self):
        """Test that duplicate fields are properly prefixed"""
        df = odm_xml_to_df_dict(self.temp_path)

        # Check study struct fields
        study_fields = list(df["study"].dtype.to_schema().keys())
        self.assertIn("study_translateoid", study_fields)  # Prefixed duplicate
        self.assertIn("studyoid", study_fields)  # Unique field, lowercased

        # Check subject struct fields
        subject_fields = list(df["subject"].dtype.to_schema().keys())
        self.assertIn("subject_translateoid", subject_fields)  # Prefixed duplicate
        self.assertIn("sex", subject_fields)  # Unique field, lowercased
        self.assertIn("dateofbirth", subject_fields)  # Unique field, lowercased

    def test_odm_xml_to_df_dict_lowercase_fields(self):
        """Test that all field names are converted to lowercase"""
        df = odm_xml_to_df_dict(self.temp_path)

        # Check all struct fields are lowercase
        for col in df.select(cs.struct()).columns:
            struct_fields = list(df[col].dtype.to_schema().keys())
            for field in struct_fields:
                self.assertEqual(field, field.lower())

    def test_odm_xml_to_df_flattened_structure(self):
        """Test that odm_xml_to_df returns flattened DataFrame"""
        df = odm_xml_to_df(self.temp_path)

        # Should have no struct columns after flattening
        struct_columns = df.select(cs.struct()).columns
        self.assertEqual(len(struct_columns), 0)

        # Should have the expected flattened columns
        self.assertIn("study_translateoid", df.columns)
        self.assertIn("subject_translateoid", df.columns)
        self.assertIn("studyoid", df.columns)
        self.assertIn("sex", df.columns)
        self.assertIn("value", df.columns)

    def test_odm_xml_to_df_duplicate_prefix_logic(self):
        """Test that only duplicated fields get prefixes in flattened DataFrame"""
        df = odm_xml_to_df(self.temp_path)

        # Check that TranslateOID gets prefixed (it was duplicated)
        self.assertIn("study_translateoid", df.columns)
        self.assertIn("subject_translateoid", df.columns)
        self.assertNotIn("translateoid", df.columns)  # Should not exist unprefixed

        # Check that unique fields don't get prefixed
        self.assertIn("studyoid", df.columns)  # Not study_studyoid
        self.assertIn("sex", df.columns)  # Not subject_sex
        self.assertIn("value", df.columns)  # Not item_value

    def test_odm_xml_to_df_all_lowercase(self):
        """Test that all column names in flattened DataFrame are lowercase"""
        df = odm_xml_to_df(self.temp_path)

        for col in df.columns:
            self.assertEqual(col, col.lower())

    def test_odm_xml_to_df_data_integrity(self):
        """Test that data values are preserved correctly"""
        df = odm_xml_to_df(self.temp_path)

        # Check that we have the expected number of rows
        self.assertEqual(df.height, 4)

        # Check some specific data values
        age_rows = df.filter(pl.col("itemoid") == "I_AGE")
        self.assertEqual(age_rows.height, 2)  # Two subjects have age data

        # Check that the values are correct
        age_values = age_rows.select("value").to_series().to_list()
        self.assertIn("33", age_values)
        self.assertIn("38", age_values)

    def test_pathlib_path_input(self):
        """Test that functions accept pathlib.Path objects"""
        path_obj = Path(self.temp_path)

        # Should work with Path objects
        df_dict = odm_xml_to_df_dict(path_obj)
        df = odm_xml_to_df(path_obj)

        self.assertIsInstance(df_dict, pl.DataFrame)
        self.assertIsInstance(df, pl.DataFrame)

    def test_empty_xml_structure(self):
        """Test handling of minimal XML structure"""
        minimal_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <ODM xmlns="http://www.cdisc.org/ns/odm/v1.3">
          <ClinicalData StudyOID="EMPTY_STUDY">
          </ClinicalData>
        </ODM>"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
            f.write(minimal_xml)
            temp_path = f.name

        try:
            df = odm_xml_to_df_dict(temp_path)
            # Should return empty DataFrame
            self.assertEqual(df.height, 0)
            self.assertEqual(len(df.columns), 0)  # No data means no columns
        finally:
            Path(temp_path).unlink()


if __name__ == "__main__":
    unittest.main()

"""Tests for schema loading service."""

from pathlib import Path

import pytest

from src.services.schema_service import (
    EntityField,
    EntitySchema,
    SchemaService,
    get_schema_service,
)


class TestSchemaService:
    """Tests for SchemaService class."""

    def test_get_schema_service_singleton(self):
        """Test that get_schema_service returns a cached singleton."""
        service1 = get_schema_service()
        service2 = get_schema_service()
        assert service1 is service2

    def test_load_basic_info_schema(self):
        """Test loading basic_info entity schema."""
        service = SchemaService()
        schema = service.load_schema("basic_info")

        assert isinstance(schema, EntitySchema)
        assert schema.display_name_key == "entity.basic_info.title"
        assert len(schema.fields) > 0

        # Check for expected fields
        field_names = [f.name for f in schema.fields]
        assert "patient_id" in field_names
        assert "patient_name" in field_names
        assert "gender" in field_names
        assert "age" in field_names

    def test_load_surgery_indicator_schema(self):
        """Test loading surgery_indicator entity schema."""
        service = SchemaService()
        schema = service.load_schema("surgery_indicator")

        assert isinstance(schema, EntitySchema)
        assert schema.display_name_key == "entity.surgery_indicator.title"

        # Check for expected fields
        field_names = [f.name for f in schema.fields]
        assert "stone_location" in field_names
        assert "alt_value_before" in field_names
        assert "alt_value_after" in field_names

    def test_load_clinical_followup_schema(self):
        """Test loading clinical_followup entity schema with stages."""
        service = SchemaService()
        schema = service.load_schema("clinical_followup")

        assert isinstance(schema, EntitySchema)
        assert schema.stages is not None
        assert len(schema.stages) == 5  # 5 clinical followup stages

        # Check stages
        stage_numbers = [s["number"] for s in schema.stages]
        assert stage_numbers == [1, 2, 3, 4, 5]

        # Check for stage-specific fields
        stage_specific_fields = [f for f in schema.fields if f.stage_specific]
        assert len(stage_specific_fields) > 0

    def test_load_nursing_followup_schema(self):
        """Test loading nursing_followup entity schema with stages."""
        service = SchemaService()
        schema = service.load_schema("nursing_followup")

        assert isinstance(schema, EntitySchema)
        assert schema.stages is not None
        assert len(schema.stages) == 6  # 6 nursing followup stages

    def test_load_nonexistent_schema_raises_error(self):
        """Test that loading a non-existent schema raises FileNotFoundError."""
        service = SchemaService()

        with pytest.raises(FileNotFoundError):
            service.load_schema("nonexistent_entity")

    def test_get_all_schemas(self):
        """Test getting all available schemas."""
        service = SchemaService()
        schemas = service.get_all_schemas()

        assert isinstance(schemas, dict)
        assert "basic_info" in schemas
        assert "surgery_indicator" in schemas
        assert "clinical_followup" in schemas
        assert "nursing_followup" in schemas

    def test_field_validation_parsing(self):
        """Test that field validations are properly parsed."""
        service = SchemaService()
        schema = service.load_schema("basic_info")

        # Find the age field which has validation
        age_field = next((f for f in schema.fields if f.name == "age"), None)
        assert age_field is not None
        assert age_field.validation.required is True
        assert age_field.validation.min_value == 0
        assert age_field.validation.max_value == 150

    def test_enum_options_parsing(self):
        """Test that enum options are properly parsed."""
        service = SchemaService()
        schema = service.load_schema("basic_info")

        # Find the gender field which is an enum
        gender_field = next((f for f in schema.fields if f.name == "gender"), None)
        assert gender_field is not None
        assert gender_field.type == "enum"
        assert gender_field.enum_options is not None
        assert len(gender_field.enum_options) == 2

        option_keys = [opt["key"] for opt in gender_field.enum_options]
        assert "male" in option_keys
        assert "female" in option_keys

    def test_load_normalization_rules(self):
        """Test loading normalization rules."""
        service = SchemaService()
        rules = service.load_normalization_rules()

        assert isinstance(rules, dict)
        assert "character_mappings" in rules
        assert "checkbox_formats" in rules
        assert "multi_checkbox_formats" in rules
        assert "field_normalizations" in rules
        assert "wildcard_rules" in rules

    def test_checkbox_formats_loaded(self):
        """Test that checkbox formats are properly loaded."""
        service = SchemaService()
        rules = service.load_normalization_rules()

        checkbox_formats = rules.get("checkbox_formats", {})
        assert "yes_no" in checkbox_formats
        assert "none_has" in checkbox_formats
        assert "stone_clearance" in checkbox_formats
        assert "urine_color_scale" in checkbox_formats

    def test_build_llm_extraction_prompt(self):
        """Test building LLM extraction prompt from schema."""
        service = SchemaService()
        prompt = service.build_llm_extraction_prompt("basic_info")

        assert isinstance(prompt, str)
        assert "patient_id" in prompt
        assert "patient_name" in prompt
        assert "gender" in prompt
        # Should include type hints
        assert "string" in prompt or "integer" in prompt

    def test_build_llm_extraction_prompt_for_followup(self):
        """Test building LLM extraction prompt for followup with stages."""
        service = SchemaService()
        prompt = service.build_llm_extraction_prompt("clinical_followup")

        assert isinstance(prompt, str)
        # Should mention stages
        assert "stage" in prompt.lower() or "术后" in prompt

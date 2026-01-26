"""Tests for schema API endpoints."""

import pytest
from fastapi.testclient import TestClient


class TestSchemaAPI:
    """Tests for /api/schemas endpoints."""

    def test_list_schemas(self, client: TestClient):
        """Test listing all available schemas."""
        response = client.get("/api/schemas")

        assert response.status_code == 200
        data = response.json()

        assert "schemas" in data
        schemas = data["schemas"]
        assert len(schemas) >= 4  # At least 4 entity types

        # Check schema list structure
        schema_types = [s["entity_type"] for s in schemas]
        assert "basic_info" in schema_types
        assert "surgery_indicator" in schema_types
        assert "clinical_followup" in schema_types
        assert "nursing_followup" in schema_types

        # Each item should have required fields
        for schema in schemas:
            assert "entity_type" in schema
            assert "display_name_key" in schema
            assert "field_count" in schema
            assert "has_stages" in schema

    def test_list_schemas_followup_has_stages(self, client: TestClient):
        """Test that followup schemas are marked as having stages."""
        response = client.get("/api/schemas")
        data = response.json()
        schemas = {s["entity_type"]: s for s in data["schemas"]}

        # Followups should have stages
        assert schemas["clinical_followup"]["has_stages"] is True
        assert schemas["nursing_followup"]["has_stages"] is True

        # Non-followups should not have stages
        assert schemas["basic_info"]["has_stages"] is False
        assert schemas["surgery_indicator"]["has_stages"] is False

    def test_get_basic_info_schema(self, client: TestClient):
        """Test getting basic_info schema details."""
        response = client.get("/api/schemas/basic_info")

        assert response.status_code == 200
        data = response.json()

        assert data["entity_type"] == "basic_info"
        assert data["display_name_key"] == "entity.basic_info.title"
        assert "fields" in data
        assert len(data["fields"]) > 0

        # Check field structure
        field_names = [f["name"] for f in data["fields"]]
        assert "patient_id" in field_names
        assert "patient_name" in field_names
        assert "gender" in field_names

    def test_get_surgery_indicator_schema(self, client: TestClient):
        """Test getting surgery_indicator schema details."""
        response = client.get("/api/schemas/surgery_indicator")

        assert response.status_code == 200
        data = response.json()

        assert data["entity_type"] == "surgery_indicator"
        field_names = [f["name"] for f in data["fields"]]
        assert "stone_location" in field_names
        assert "alt_value_before" in field_names
        assert "alt_value_after" in field_names

    def test_get_clinical_followup_schema_with_stages(self, client: TestClient):
        """Test getting clinical_followup schema with stages."""
        response = client.get("/api/schemas/clinical_followup")

        assert response.status_code == 200
        data = response.json()

        assert data["entity_type"] == "clinical_followup"
        assert "stages" in data
        assert data["stages"] is not None
        assert len(data["stages"]) == 5

        # Check stage structure
        stage_numbers = [s["number"] for s in data["stages"]]
        assert stage_numbers == [1, 2, 3, 4, 5]

        # Check stage details
        first_stage = data["stages"][0]
        assert first_stage["name"] == "术后7天"
        assert first_stage["days_after_surgery"] == 7

    def test_get_nursing_followup_schema_with_stages(self, client: TestClient):
        """Test getting nursing_followup schema with 6 stages."""
        response = client.get("/api/schemas/nursing_followup")

        assert response.status_code == 200
        data = response.json()

        assert data["entity_type"] == "nursing_followup"
        assert len(data["stages"]) == 6

    def test_get_schema_field_validation(self, client: TestClient):
        """Test that field validations are included in schema response."""
        response = client.get("/api/schemas/basic_info")
        data = response.json()

        # Find the age field
        age_field = next((f for f in data["fields"] if f["name"] == "age"), None)
        assert age_field is not None
        assert "validation" in age_field
        assert age_field["validation"]["required"] is True
        assert age_field["validation"]["min_value"] == 0
        assert age_field["validation"]["max_value"] == 150

    def test_get_schema_enum_options(self, client: TestClient):
        """Test that enum options are included in schema response."""
        response = client.get("/api/schemas/basic_info")
        data = response.json()

        # Find the gender field
        gender_field = next((f for f in data["fields"] if f["name"] == "gender"), None)
        assert gender_field is not None
        assert gender_field["type"] == "enum"
        assert "enum_options" in gender_field
        assert len(gender_field["enum_options"]) == 2

        option_keys = [opt["key"] for opt in gender_field["enum_options"]]
        assert "male" in option_keys
        assert "female" in option_keys

    def test_get_nonexistent_schema_returns_404(self, client: TestClient):
        """Test that requesting a non-existent schema returns 404."""
        response = client.get("/api/schemas/nonexistent_entity")

        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    def test_get_normalization_rules(self, client: TestClient):
        """Test getting normalization rules."""
        response = client.get("/api/schemas/normalization-rules")

        assert response.status_code == 200
        data = response.json()

        assert "character_mappings" in data
        assert "checkbox_formats" in data
        assert "multi_checkbox_formats" in data
        assert "field_normalizations" in data
        assert "wildcard_rules" in data

    def test_normalization_rules_checkbox_formats(self, client: TestClient):
        """Test that checkbox formats are included in normalization rules."""
        response = client.get("/api/schemas/normalization-rules")
        data = response.json()

        checkbox_formats = data["checkbox_formats"]
        assert "yes_no" in checkbox_formats
        assert "none_has" in checkbox_formats
        assert "stone_clearance" in checkbox_formats
        assert "urine_color_scale" in checkbox_formats

    def test_normalization_rules_field_specific(self, client: TestClient):
        """Test that field-specific rules are included."""
        response = client.get("/api/schemas/normalization-rules")
        data = response.json()

        field_rules = data["field_normalizations"]
        assert "family_history_of_stone" in field_rules
        assert "stone_location" in field_rules
        assert "nursing_adverse_effects" in field_rules

    def test_get_extraction_prompt(self, client: TestClient):
        """Test getting LLM extraction prompt for an entity."""
        response = client.get("/api/schemas/basic_info/prompt")

        assert response.status_code == 200
        data = response.json()

        assert data["entity_type"] == "basic_info"
        assert "prompt" in data
        assert len(data["prompt"]) > 0

        # Prompt should contain field names
        assert "patient_id" in data["prompt"]
        assert "patient_name" in data["prompt"]

    def test_get_extraction_prompt_nonexistent(self, client: TestClient):
        """Test getting extraction prompt for non-existent entity."""
        response = client.get("/api/schemas/nonexistent/prompt")

        assert response.status_code == 404

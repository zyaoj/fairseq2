"""Tests for normalizer service."""

import pytest

from src.services.normalizer import (
    NormalizationResult,
    NormalizerService,
    get_normalizer_service,
)


class TestNormalizerService:
    """Tests for NormalizerService class."""

    def test_get_normalizer_service_singleton(self):
        """Test that get_normalizer_service returns a cached singleton."""
        service1 = get_normalizer_service()
        service2 = get_normalizer_service()
        assert service1 is service2

    def test_apply_character_mappings(self):
        """Test character mapping normalization."""
        service = NormalizerService()
        # √ should be normalized to ☑
        result = service.apply_character_mappings("√是☐否")
        assert "☑" in result

    def test_normalize_yes_no_true(self):
        """Test yes/no normalization for true values."""
        service = NormalizerService()

        # Test with selected yes checkbox
        result = service.normalize_yes_no("☑是☐否")
        assert result.normalized_value is True
        assert result.normalization_type == "yes_no"

        # Test with checkmark variant
        result = service.normalize_yes_no("√是☐否")
        assert result.normalized_value is True

    def test_normalize_yes_no_false(self):
        """Test yes/no normalization for false values."""
        service = NormalizerService()

        # Test with selected no checkbox
        result = service.normalize_yes_no("☐是☑否")
        assert result.normalized_value is False
        assert result.normalization_type == "yes_no"

    def test_normalize_yes_no_with_spacing(self):
        """Test yes/no normalization with various spacing."""
        service = NormalizerService()

        # With spacing
        result = service.normalize_yes_no("☑是      ☐否", spacing=6)
        assert result.normalized_value is True

        result = service.normalize_yes_no("☐是      ☑否", spacing=6)
        assert result.normalized_value is False

    def test_normalize_none_has_none(self):
        """Test none/has normalization for none values."""
        service = NormalizerService()

        result = service.normalize_none_has("☑无 ☐有")
        assert result.normalized_value == "none"
        assert result.normalization_type == "none_has"

    def test_normalize_none_has_has(self):
        """Test none/has normalization for has values."""
        service = NormalizerService()

        result = service.normalize_none_has("☐无 ☑有")
        assert result.normalized_value == "has"

    def test_normalize_none_has_with_detail(self):
        """Test none/has normalization with detail extraction."""
        service = NormalizerService()

        result = service.normalize_none_has("☐无 ☑有：胃肠不适", has_detail=True)
        assert result.normalized_value == "has"
        assert result.details.get("detail") is not None

    def test_normalize_stone_clearance_no_residual(self):
        """Test stone clearance normalization for no residual."""
        service = NormalizerService()

        result = service.normalize_stone_clearance("☑无残留结石 ☐残留结石")
        assert result.normalized_value == "no_residual"
        assert result.normalization_type == "stone_clearance"

    def test_normalize_stone_clearance_residual(self):
        """Test stone clearance normalization for residual."""
        service = NormalizerService()

        result = service.normalize_stone_clearance("☐无残留结石 ☑残留结石")
        assert result.normalized_value == "residual"

    def test_normalize_stone_clearance_with_size(self):
        """Test stone clearance normalization with size extraction."""
        service = NormalizerService()

        result = service.normalize_stone_clearance("☐无残留 ☑残留 5mm")
        assert result.normalized_value == "residual"
        assert result.details.get("size_mm") == 5

    def test_normalize_scale_urine_color(self):
        """Test scale normalization for urine color."""
        service = NormalizerService()

        # Test with numeric value
        result = service.normalize_scale("3", "urine_color_scale")
        assert result.normalized_value == 3
        assert result.normalization_type == "scale"

        # Value should be within range
        result = service.normalize_scale("5", "urine_color_scale")
        assert result.normalized_value == 5

    def test_normalize_scale_checkbox_format(self):
        """Test scale normalization with checkbox format."""
        service = NormalizerService()

        # 8 checkboxes, 3rd one selected
        result = service.normalize_scale("☐☐☑☐☐☐☐☐", "urine_color_scale")
        assert result.normalized_value == 3

    def test_normalize_multi_checkbox_medical_history(self):
        """Test multi-checkbox normalization for medical history."""
        service = NormalizerService()

        result = service.normalize_multi_checkbox(
            "☑高血压 ☐糖尿病 ☑其他", "medical_history"
        )
        assert result.normalization_type == "multi_checkbox"
        assert isinstance(result.normalized_value, list)
        assert "hypertension" in result.normalized_value
        assert "other" in result.normalized_value
        assert "diabetes" not in result.normalized_value

    def test_normalize_multi_checkbox_stone_location(self):
        """Test multi-checkbox normalization for stone location."""
        service = NormalizerService()

        result = service.normalize_multi_checkbox(
            "☑左肾 ☑右肾 ☐左输尿管 ☐右输尿管 ☐膀胱", "stone_location"
        )
        assert isinstance(result.normalized_value, list)
        assert "left_kidney" in result.normalized_value
        assert "right_kidney" in result.normalized_value
        assert "bladder" not in result.normalized_value

    def test_normalize_extract_components(self):
        """Test component extraction for stone composition."""
        service = NormalizerService()

        result = service.normalize_extract_components(
            "草酸钙+碳酸钙+尿酸", separator="+", exclude_words=["是", "否"]
        )
        assert result.normalization_type == "extract_components"
        assert isinstance(result.normalized_value, list)
        assert "草酸钙" in result.normalized_value
        assert "碳酸钙" in result.normalized_value
        assert "尿酸" in result.normalized_value

    def test_normalize_extract_text(self):
        """Test text extraction removing checkbox markers."""
        service = NormalizerService()

        result = service.normalize_extract_text("☑左肾输尿管切开取石术")
        assert result.normalization_type == "extract_text"
        assert "☑" not in result.normalized_value
        assert "左肾输尿管切开取石术" in result.normalized_value

    def test_get_field_rule_exact_match(self):
        """Test getting field rule by exact match."""
        service = NormalizerService()

        rule = service.get_field_rule("family_history_of_stone")
        assert rule is not None
        assert rule.get("type") == "yes_no"

    def test_get_field_rule_wildcard_match(self):
        """Test getting field rule by wildcard pattern."""
        service = NormalizerService()

        rule = service.get_field_rule("nursing_1_urine_color")
        assert rule is not None
        assert rule.get("type") == "scale"

        rule = service.get_field_rule("followup_3_recurrence")
        assert rule is not None
        assert rule.get("type") == "yes_no"

    def test_get_field_rule_no_match(self):
        """Test getting field rule with no match."""
        service = NormalizerService()

        rule = service.get_field_rule("unknown_field_xyz")
        assert rule is None

    def test_normalize_field_yes_no(self):
        """Test normalize_field for yes/no type."""
        service = NormalizerService()

        result = service.normalize_field("family_history_of_stone", "☑是      ☐否")
        assert isinstance(result, NormalizationResult)
        assert result.normalized_value is True

    def test_normalize_field_none_has(self):
        """Test normalize_field for none/has type."""
        service = NormalizerService()

        result = service.normalize_field("nursing_adverse_effects", "☑无 ☐有")
        assert result.normalized_value == "none"

    def test_normalize_field_passthrough_empty(self):
        """Test normalize_field with empty value."""
        service = NormalizerService()

        result = service.normalize_field("any_field", "")
        assert result.normalization_type == "passthrough"

    def test_normalize_field_passthrough_no_rule(self):
        """Test normalize_field with no matching rule."""
        service = NormalizerService()

        result = service.normalize_field("unknown_field", "some value")
        assert result.normalization_type == "passthrough"
        assert result.normalized_value == "some value"

    def test_normalize_extracted_data(self):
        """Test normalizing a full extracted data dictionary."""
        service = NormalizerService()

        data = {
            "family_history_of_stone": "☑是      ☐否",
            "repeated_urinary_infection": "☐是      ☑否",
            "patient_name": "张三",
            "age": 45,  # Non-string should pass through
        }

        result = service.normalize_extracted_data(data)

        assert result["family_history_of_stone"] is True
        assert result["repeated_urinary_infection"] is False
        assert result["patient_name"] == "张三"
        assert result["age"] == 45

    def test_normalize_scale_out_of_range(self):
        """Test scale normalization with out of range value."""
        service = NormalizerService()

        # Value 10 is out of range (1-8)
        result = service.normalize_scale("10", "urine_color_scale")
        assert result.normalized_value is None

    def test_normalize_yes_no_unclear(self):
        """Test yes/no normalization with unclear selection."""
        service = NormalizerService()

        # Neither clearly selected
        result = service.normalize_yes_no("☐是☐否")
        assert result.normalized_value is None


class TestNormalizerHospitalInheritance:
    """Tests for NormalizerService hospital inheritance functionality."""

    @pytest.fixture
    def schema_dir(self, tmp_path):
        """Create a temporary schema directory with base and hospital rules."""
        # Create base directory
        base_dir = tmp_path / "base"
        base_dir.mkdir()

        # Create hospitals directory
        hospitals_dir = tmp_path / "hospitals"
        hospitals_dir.mkdir()

        # Create hospital_001 directory
        hospital_001_dir = hospitals_dir / "hospital_001"
        hospital_001_dir.mkdir()

        # Create base normalization rules
        base_rules = """
version: "1.0"
description: "Base normalization rules"

character_mappings:
  "√": "☑"
  "✓": "☑"

checkbox_formats:
  yes_no:
    true_values:
      - "☑是"
      - "√是"
    false_values:
      - "☑否"
      - "√否"

  none_has:
    none_values:
      - "☑无"
    has_values:
      - "☑有"

field_normalizations:
  family_history_of_stone:
    type: yes_no
    spacing: 6
  patient_name:
    type: plain_text

wildcard_rules:
  - pattern: "*_followup_*"
    type: yes_no
"""
        (base_dir / "normalization_rules.yaml").write_text(base_rules)

        # Create hospital_001 specific overrides
        hospital_rules = """
version: "1.0"
extends: base

# Hospital 001 uses ✔ instead of ☑
character_mapping_additions:
  "✔": "☑"

# Hospital 001 has different checkbox patterns
checkbox_format_overrides:
  yes_no:
    true_values:
      - "☑是"
      - "✔是"
      - "○是"
    false_values:
      - "☑否"
      - "✔否"
      - "○否"

# Hospital 001 has additional fields
field_normalization_additions:
  department_code:
    type: plain_text
  hospital_specific_field:
    type: yes_no

# Hospital 001 modifies existing field rules
field_normalization_overrides:
  family_history_of_stone:
    spacing: 4

# Hospital 001 additional wildcard rules
wildcard_rule_additions:
  - pattern: "h001_*"
    type: extract_text
"""
        (hospital_001_dir / "normalization_rules.yaml").write_text(hospital_rules)

        return tmp_path

    def test_load_base_rules_only(self, schema_dir):
        """Test loading base rules without hospital_id."""
        service = NormalizerService(schema_dir=schema_dir)

        # Should have base checkbox formats
        assert "yes_no" in service.checkbox_formats
        assert "☑是" in service.checkbox_formats["yes_no"]["true_values"]

        # Should have base field normalizations
        assert "family_history_of_stone" in service.field_normalizations
        assert service.field_normalizations["family_history_of_stone"]["spacing"] == 6

        # Should NOT have hospital-specific fields
        assert "department_code" not in service.field_normalizations
        assert "hospital_specific_field" not in service.field_normalizations

    def test_load_hospital_rules_with_inheritance(self, schema_dir):
        """Test loading hospital rules merged with base."""
        service = NormalizerService(schema_dir=schema_dir, hospital_id="hospital_001")

        # Should have base checkbox formats with hospital overrides
        assert "yes_no" in service.checkbox_formats
        # Hospital override adds new values
        assert "○是" in service.checkbox_formats["yes_no"]["true_values"]
        assert "✔是" in service.checkbox_formats["yes_no"]["true_values"]

        # Should have merged field normalizations
        assert "family_history_of_stone" in service.field_normalizations
        # Hospital override changes spacing from 6 to 4
        assert service.field_normalizations["family_history_of_stone"]["spacing"] == 4

        # Should have hospital-specific fields
        assert "department_code" in service.field_normalizations
        assert "hospital_specific_field" in service.field_normalizations

    def test_character_mapping_additions(self, schema_dir):
        """Test that hospital adds character mappings."""
        service = NormalizerService(schema_dir=schema_dir, hospital_id="hospital_001")

        # Base mappings should still exist
        assert "√" in service.character_mappings
        assert "✓" in service.character_mappings

        # Hospital additions should exist
        assert "✔" in service.character_mappings

    def test_wildcard_rule_additions(self, schema_dir):
        """Test that hospital adds wildcard rules."""
        service = NormalizerService(schema_dir=schema_dir, hospital_id="hospital_001")

        # Should have both base and hospital wildcard rules
        patterns = [rule["pattern"] for rule in service.wildcard_rules]
        assert "*_followup_*" in patterns  # Base rule
        assert "h001_*" in patterns  # Hospital addition

    def test_hospital_fallback_to_base(self, schema_dir):
        """Test that non-existent hospital falls back to base rules."""
        service = NormalizerService(
            schema_dir=schema_dir, hospital_id="nonexistent_hospital"
        )

        # Should have base rules only
        assert "yes_no" in service.checkbox_formats
        assert service.field_normalizations["family_history_of_stone"]["spacing"] == 6

        # Should NOT have hospital-specific fields
        assert "department_code" not in service.field_normalizations

    def test_normalize_with_hospital_rules(self, schema_dir):
        """Test that normalization uses hospital-specific rules."""
        service = NormalizerService(schema_dir=schema_dir, hospital_id="hospital_001")

        # Hospital 001 adds ✔ as a character mapping to ☑
        # and adds ✔是 to true_values
        # This tests the full flow: character mapping + hospital-specific true_values
        result = service.normalize_yes_no("✔是☐否")
        assert result.normalized_value is True

        # Base service without hospital rules should not have ✔ mapping
        base_service = NormalizerService(schema_dir=schema_dir)
        result_base = base_service.normalize_yes_no("✔是☐否")
        # Base has no ✔ mapping, but ✔是 is listed in hospital checkbox_format_overrides
        # With base rules only, ✔是 won't be recognized (no mapping, not in base true_values)
        assert result_base.normalized_value is None

    def test_clear_cache(self, schema_dir):
        """Test clearing the rules cache."""
        service = NormalizerService(schema_dir=schema_dir, hospital_id="hospital_001")

        # Verify rules loaded
        assert "department_code" in service.field_normalizations

        # Clear cache
        service.clear_cache()

        # Cache should be empty
        assert len(service._cache) == 0

    def test_multiple_hospitals_use_correct_rules(self, schema_dir):
        """Test that different hospitals get their own merged rules."""
        # Create hospital_002 with different overrides
        hospital_002_dir = schema_dir / "hospitals" / "hospital_002"
        hospital_002_dir.mkdir()

        hospital_002_rules = """
version: "1.0"
extends: base

field_normalization_additions:
  hospital_002_field:
    type: extract_text
"""
        (hospital_002_dir / "normalization_rules.yaml").write_text(hospital_002_rules)

        service_001 = NormalizerService(schema_dir=schema_dir, hospital_id="hospital_001")
        service_002 = NormalizerService(schema_dir=schema_dir, hospital_id="hospital_002")

        # Hospital 001 should have its fields
        assert "department_code" in service_001.field_normalizations
        assert "hospital_002_field" not in service_001.field_normalizations

        # Hospital 002 should have its fields
        assert "hospital_002_field" in service_002.field_normalizations
        assert "department_code" not in service_002.field_normalizations

    def test_no_base_rules_file(self, tmp_path):
        """Test behavior when base rules file doesn't exist."""
        base_dir = tmp_path / "base"
        base_dir.mkdir()

        service = NormalizerService(schema_dir=tmp_path)

        # Should have empty rules
        assert service.checkbox_formats == {}
        assert service.field_normalizations == {}
        assert service.wildcard_rules == []

    def test_deep_merge_nested_dicts(self, schema_dir):
        """Test that nested dictionaries are properly deep merged."""
        # This is tested implicitly through checkbox_format_overrides
        service = NormalizerService(schema_dir=schema_dir, hospital_id="hospital_001")

        # The yes_no format should have merged values
        yes_no = service.checkbox_formats.get("yes_no", {})

        # Hospital override provides complete true_values list (replaces)
        assert "✔是" in yes_no.get("true_values", [])

    def test_caching_works(self, schema_dir):
        """Test that rules are cached per hospital_id."""
        service = NormalizerService(schema_dir=schema_dir, hospital_id="hospital_001")

        # First load should populate cache
        assert "hospital_001" in service._cache

        # Access rules to ensure cache is used
        _ = service.checkbox_formats

        # Cache should still have the rules
        assert service._cache.get("hospital_001") is not None

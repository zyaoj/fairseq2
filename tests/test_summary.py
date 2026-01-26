"""Tests for patient summary service."""

from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from src.services.summary import (
    PatientSummary,
    PatientSummaryService,
    SummaryServiceError,
    get_summary_service,
)


class TestPatientSummaryDataclass:
    """Tests for PatientSummary dataclass."""

    def test_create_summary(self):
        """Test creating a PatientSummary instance."""
        summary = PatientSummary(
            patient_id="550e8400-e29b-41d4-a716-446655440000",
            summary_text="Patient summary text",
            key_findings=["Finding 1", "Finding 2"],
            recommendations=["Recommendation 1"],
            risk_factors=["Risk 1"],
            followup_status={"clinical_completed": 3, "clinical_total": 5},
            generated_at="2024-01-15T10:30:00Z",
            model="claude-sonnet-4-20250514",
        )

        assert summary.patient_id == "550e8400-e29b-41d4-a716-446655440000"
        assert summary.summary_text == "Patient summary text"
        assert len(summary.key_findings) == 2
        assert len(summary.recommendations) == 1
        assert len(summary.risk_factors) == 1
        assert summary.followup_status["clinical_completed"] == 3
        assert summary.model == "claude-sonnet-4-20250514"
        assert summary.metadata == {}  # Default empty dict

    def test_summary_with_metadata(self):
        """Test creating a PatientSummary with metadata."""
        summary = PatientSummary(
            patient_id="test-id",
            summary_text="Summary",
            key_findings=[],
            recommendations=[],
            risk_factors=[],
            followup_status={},
            generated_at="2024-01-15T10:30:00Z",
            model="claude-sonnet-4-20250514",
            metadata={"raw_response": "some text", "parse_error": "error"},
        )

        assert summary.metadata["raw_response"] == "some text"
        assert summary.metadata["parse_error"] == "error"


class TestSummaryServiceError:
    """Tests for SummaryServiceError exception."""

    def test_error_message(self):
        """Test that error message is preserved."""
        error = SummaryServiceError("Summary generation failed")
        assert str(error) == "Summary generation failed"

    def test_error_inheritance(self):
        """Test that error inherits from Exception."""
        error = SummaryServiceError("test")
        assert isinstance(error, Exception)


class TestPatientSummaryServiceInit:
    """Tests for PatientSummaryService initialization."""

    def test_init_with_client(self):
        """Test initialization with valid client."""
        mock_client = MagicMock()
        service = PatientSummaryService(anthropic_client=mock_client)

        assert service.anthropic_client == mock_client
        assert service.model == PatientSummaryService.DEFAULT_MODEL

    def test_init_with_custom_model(self):
        """Test initialization with custom model."""
        mock_client = MagicMock()
        service = PatientSummaryService(
            anthropic_client=mock_client,
            model="claude-3-opus-20240229",
        )

        assert service.model == "claude-3-opus-20240229"

    def test_init_without_client_raises_error(self):
        """Test that initialization without client raises error."""
        with pytest.raises(SummaryServiceError, match="Anthropic client is required"):
            PatientSummaryService(anthropic_client=None)

    def test_default_constants(self):
        """Test default constants."""
        assert PatientSummaryService.DEFAULT_MODEL == "claude-sonnet-4-20250514"
        assert PatientSummaryService.MAX_TOKENS == 4096


class TestCalculateAge:
    """Tests for _calculate_age method."""

    def test_calculate_age_basic(self):
        """Test basic age calculation."""
        mock_client = MagicMock()
        service = PatientSummaryService(anthropic_client=mock_client)

        # Use a fixed reference to calculate expected age
        dob = date(1990, 6, 15)
        today = date.today()
        expected_age = today.year - dob.year
        if (today.month, today.day) < (dob.month, dob.day):
            expected_age -= 1

        age = service._calculate_age(dob)
        assert age == expected_age

    def test_calculate_age_birthday_not_yet(self):
        """Test age calculation when birthday hasn't occurred yet this year."""
        mock_client = MagicMock()
        service = PatientSummaryService(anthropic_client=mock_client)

        # Use a date in the far future this year
        dob = date(date.today().year - 30, 12, 31)
        today = date.today()

        age = service._calculate_age(dob)

        if today.month == 12 and today.day == 31:
            assert age == 30
        else:
            assert age == 29

    def test_calculate_age_none(self):
        """Test age calculation with None date."""
        mock_client = MagicMock()
        service = PatientSummaryService(anthropic_client=mock_client)

        age = service._calculate_age(None)
        assert age is None


class TestSerializationMethods:
    """Tests for serialization helper methods."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_client = MagicMock()
        self.service = PatientSummaryService(anthropic_client=self.mock_client)

    def test_serialize_basic_info(self):
        """Test serializing BasicInfo."""
        mock_info = MagicMock()
        mock_info.patient_name = "John Doe"
        mock_info.gender = "male"
        mock_info.age = 45
        mock_info.height = 175.0
        mock_info.weight = 70.0
        mock_info.occupation = "Engineer"
        mock_info.medical_history = "Hypertension"
        mock_info.family_history_of_stone = True
        mock_info.repeated_urinary_infection = False
        mock_info.surgery_type = "PCNL"
        mock_info.surgery_date = date(2024, 1, 10)
        mock_info.stone_composition = "Calcium oxalate"
        mock_info.daily_water_intake = "2000ml"
        mock_info.diet_preference = "Normal"

        result = self.service._serialize_basic_info(mock_info)

        assert result["patient_name"] == "John Doe"
        assert result["gender"] == "male"
        assert result["height"] == 175.0
        assert result["family_history_of_stone"] is True
        assert result["surgery_date"] == "2024-01-10"

    def test_serialize_basic_info_null_date(self):
        """Test serializing BasicInfo with null surgery date."""
        mock_info = MagicMock()
        mock_info.surgery_date = None
        # Set other required fields
        for field in [
            "patient_name",
            "gender",
            "age",
            "height",
            "weight",
            "occupation",
            "medical_history",
            "family_history_of_stone",
            "repeated_urinary_infection",
            "surgery_type",
            "stone_composition",
            "daily_water_intake",
            "diet_preference",
        ]:
            setattr(mock_info, field, None)

        result = self.service._serialize_basic_info(mock_info)

        assert result["surgery_date"] is None

    def test_serialize_surgery_indicator(self):
        """Test serializing SurgeryIndicator."""
        mock_indicator = MagicMock()
        mock_indicator.clinical_diagnosis = "Kidney stones"
        mock_indicator.stone_location = "Left kidney"
        mock_indicator.stone_size = "15mm"
        mock_indicator.hydronephrosis_degree = "Mild"
        # Pre-op values
        mock_indicator.alt_value_before = 25.0
        mock_indicator.ast_value_before = 22.0
        mock_indicator.ggt_value_before = 30.0
        mock_indicator.scr_value_before = 1.0
        mock_indicator.wbc_value_before = 6.5
        mock_indicator.hb_value_before = 14.0
        mock_indicator.urine_ph_value_before = 6.0
        mock_indicator.urine_culture_result_before = "Negative"
        # Post-op values
        mock_indicator.alt_value_after = 28.0
        mock_indicator.ast_value_after = 24.0
        mock_indicator.ggt_value_after = 32.0
        mock_indicator.scr_value_after = 1.1
        mock_indicator.wbc_value_after = 8.0
        mock_indicator.hb_value_after = 13.5
        mock_indicator.urine_ph_value_after = 6.5
        mock_indicator.urine_culture_result_after = "Negative"
        mock_indicator.stone_clearance_after = "Complete"
        mock_indicator.stone_composition_after = "Calcium oxalate"

        result = self.service._serialize_surgery_indicator(mock_indicator)

        assert result["clinical_diagnosis"] == "Kidney stones"
        assert result["stone_location"] == "Left kidney"
        assert result["pre_op"]["alt"] == 25.0
        assert result["post_op"]["wbc"] == 8.0
        assert result["stone_clearance"] == "Complete"

    def test_serialize_clinical_followup(self):
        """Test serializing ClinicalFollowup."""
        mock_followup = MagicMock()
        mock_followup.stage = 1
        mock_followup.stage_name = "7天随访"
        mock_followup.followup_date = date(2024, 1, 17)
        mock_followup.followup_recurrence = False
        mock_followup.followup_stone_size = "None"
        mock_followup.followup_imaging = "CT scan"
        mock_followup.followup_alt = 26.0
        mock_followup.followup_ast = 23.0
        mock_followup.followup_scr = 1.0
        mock_followup.followup_wbc = 7.0
        mock_followup.followup_urine_culture = "Negative"
        mock_followup.followup_medication = "Antibiotics"
        mock_followup.followup_compliance = "Good"
        mock_followup.followup_adverse = "None"
        mock_followup.followup_plan = "Continue monitoring"

        result = self.service._serialize_clinical_followup(mock_followup)

        assert result["stage"] == 1
        assert result["stage_name"] == "7天随访"
        assert result["followup_date"] == "2024-01-17"
        assert result["lab_values"]["alt"] == 26.0
        assert result["compliance"] == "Good"

    def test_serialize_clinical_followup_null_date(self):
        """Test serializing ClinicalFollowup with null date."""
        mock_followup = MagicMock()
        mock_followup.stage = 1
        mock_followup.stage_name = "7天随访"
        mock_followup.followup_date = None
        # Set other fields
        for field in [
            "followup_recurrence",
            "followup_stone_size",
            "followup_imaging",
            "followup_alt",
            "followup_ast",
            "followup_scr",
            "followup_wbc",
            "followup_urine_culture",
            "followup_medication",
            "followup_compliance",
            "followup_adverse",
            "followup_plan",
        ]:
            setattr(mock_followup, field, None)

        result = self.service._serialize_clinical_followup(mock_followup)

        assert result["followup_date"] is None

    def test_serialize_nursing_followup(self):
        """Test serializing NursingFollowup."""
        mock_followup = MagicMock()
        mock_followup.stage = 1
        mock_followup.stage_name = "7天随访"
        mock_followup.followup_date = date(2024, 1, 17)
        mock_followup.nursing_mode = "Phone"
        mock_followup.nursing_antibiotic = "Yes"
        mock_followup.nursing_timed_med = "Yes"
        mock_followup.nursing_urine_ph = 6.5
        mock_followup.nursing_urine_output = True
        mock_followup.nursing_adverse_effects = "None"
        mock_followup.nursing_residual_stone = False
        mock_followup.nursing_water = "2000ml"
        mock_followup.nursing_diet = "Low sodium"
        mock_followup.nursing_depression = False
        mock_followup.nursing_support = "Family support available"

        result = self.service._serialize_nursing_followup(mock_followup)

        assert result["stage"] == 1
        assert result["mode"] == "Phone"
        assert result["urine_ph"] == 6.5
        assert result["urine_output_sufficient"] is True
        assert result["water_intake"] == "2000ml"

    def test_serialize_lab_result(self):
        """Test serializing LabResult."""
        mock_lab_result = MagicMock()
        mock_lab_result.id = "550e8400-e29b-41d4-a716-446655440000"
        mock_lab_result.title = "Blood Test"
        mock_lab_result.event_date = date(2024, 1, 15)
        mock_lab_result.extraction_status = MagicMock(value="completed")
        mock_lab_result.extracted_data = {"wbc": 7.5, "rbc": 5.0}
        mock_lab_result.extraction_confidence = 0.95

        result = self.service._serialize_lab_result(mock_lab_result)

        assert result["id"] == "550e8400-e29b-41d4-a716-446655440000"
        assert result["title"] == "Blood Test"
        assert result["event_date"] == "2024-01-15"
        assert result["extraction_status"] == "completed"
        assert result["extracted_data"]["wbc"] == 7.5
        assert result["confidence"] == 0.95

    def test_serialize_lab_result_null_values(self):
        """Test serializing LabResult with null values."""
        mock_lab_result = MagicMock()
        mock_lab_result.id = "test-id"
        mock_lab_result.title = "Test"
        mock_lab_result.event_date = None
        mock_lab_result.extraction_status = None
        mock_lab_result.extracted_data = None
        mock_lab_result.extraction_confidence = None

        result = self.service._serialize_lab_result(mock_lab_result)

        assert result["event_date"] is None
        assert result["extraction_status"] is None


class TestBuildSummaryPrompt:
    """Tests for _build_summary_prompt method."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_client = MagicMock()
        self.service = PatientSummaryService(anthropic_client=self.mock_client)

    def test_build_prompt_chinese_locale(self):
        """Test building prompt with Chinese locale."""
        patient_data = {
            "patient": {
                "id": "test-id",
                "name": "Test Patient",
            }
        }

        prompt = self.service._build_summary_prompt(patient_data, "zh-CN")

        assert "请用中文生成摘要" in prompt
        assert "test-id" in prompt
        assert "Test Patient" in prompt

    def test_build_prompt_english_locale(self):
        """Test building prompt with English locale."""
        patient_data = {
            "patient": {
                "id": "test-id",
                "name": "Test Patient",
            }
        }

        prompt = self.service._build_summary_prompt(patient_data, "en")

        assert "Generate the summary in English" in prompt
        assert "test-id" in prompt

    def test_prompt_contains_required_sections(self):
        """Test that prompt contains all required sections."""
        patient_data = {"patient": {"id": "test-id"}}

        prompt = self.service._build_summary_prompt(patient_data, "en")

        assert "Patient Data" in prompt
        assert "Instructions" in prompt
        assert "Output Format" in prompt
        assert "Guidelines" in prompt
        assert "summary_text" in prompt
        assert "key_findings" in prompt
        assert "recommendations" in prompt
        assert "risk_factors" in prompt
        assert "followup_status" in prompt


class TestParseSummaryResponse:
    """Tests for _parse_summary_response method."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_client = MagicMock()
        self.service = PatientSummaryService(anthropic_client=self.mock_client)
        self.patient_id = "550e8400-e29b-41d4-a716-446655440000"
        self.patient_data = {"patient": {"id": self.patient_id}}

    def test_parse_json_in_code_block(self):
        """Test parsing JSON wrapped in code block."""
        response = """Here's the summary:
```json
{
  "summary_text": "Patient summary",
  "key_findings": ["Finding 1"],
  "recommendations": ["Rec 1"],
  "risk_factors": ["Risk 1"],
  "followup_status": {"clinical_completed": 3}
}
```"""

        result = self.service._parse_summary_response(
            response, self.patient_id, self.patient_data
        )

        assert result.patient_id == self.patient_id
        assert result.summary_text == "Patient summary"
        assert result.key_findings == ["Finding 1"]
        assert result.recommendations == ["Rec 1"]
        assert result.risk_factors == ["Risk 1"]
        assert result.followup_status["clinical_completed"] == 3

    def test_parse_raw_json(self):
        """Test parsing raw JSON without code block."""
        response = """{
  "summary_text": "Patient summary",
  "key_findings": ["Finding 1"],
  "recommendations": [],
  "risk_factors": [],
  "followup_status": {}
}"""

        result = self.service._parse_summary_response(
            response, self.patient_id, self.patient_data
        )

        assert result.summary_text == "Patient summary"
        assert result.key_findings == ["Finding 1"]

    def test_parse_no_json_returns_raw_text(self):
        """Test that response without JSON returns raw text as summary."""
        response = "This is just plain text without any JSON."

        result = self.service._parse_summary_response(
            response, self.patient_id, self.patient_data
        )

        assert result.summary_text == response
        assert result.key_findings == []
        assert result.recommendations == []
        assert result.risk_factors == []
        assert result.followup_status == {}
        assert result.metadata["raw_response"] == response

    def test_parse_invalid_json(self):
        """Test handling of invalid JSON (matches regex but fails to parse)."""
        # Use malformed JSON that has both braces but is still invalid
        response = '{"summary_text": "incomplete", invalid}'

        result = self.service._parse_summary_response(
            response, self.patient_id, self.patient_data
        )

        assert result.summary_text == response
        assert "parse_error" in result.metadata

    def test_parse_no_json_found(self):
        """Test handling when no JSON structure is found."""
        response = 'Just plain text without any JSON structure'

        result = self.service._parse_summary_response(
            response, self.patient_id, self.patient_data
        )

        assert result.summary_text == response
        assert "raw_response" in result.metadata
        assert "parse_error" not in result.metadata

    def test_parse_missing_fields_uses_defaults(self):
        """Test that missing fields use empty defaults."""
        response = '{"summary_text": "Only summary provided"}'

        result = self.service._parse_summary_response(
            response, self.patient_id, self.patient_data
        )

        assert result.summary_text == "Only summary provided"
        assert result.key_findings == []
        assert result.recommendations == []
        assert result.risk_factors == []
        assert result.followup_status == {}

    def test_parse_sets_metadata(self):
        """Test that metadata is set correctly."""
        response = '{"summary_text": "Test"}'
        patient_data = {"patient": {}, "basic_info": {}, "surgery_indicator": {}}

        result = self.service._parse_summary_response(
            response, self.patient_id, patient_data
        )

        assert "patient_data_keys" in result.metadata
        assert set(result.metadata["patient_data_keys"]) == {
            "patient",
            "basic_info",
            "surgery_indicator",
        }


class TestGatherPatientData:
    """Tests for _gather_patient_data method."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_client = MagicMock()
        self.service = PatientSummaryService(anthropic_client=self.mock_client)
        self.mock_db = MagicMock()

    def test_gather_basic_patient_data(self):
        """Test gathering basic patient data."""
        mock_patient = MagicMock()
        mock_patient.id = "test-patient-id"
        mock_patient.mrn = "MRN001"
        mock_patient.first_name = "John"
        mock_patient.last_name = "Doe"
        mock_patient.date_of_birth = date(1980, 5, 15)
        mock_patient.gender = "male"
        mock_patient.basic_info = None
        mock_patient.surgery_indicator = None
        mock_patient.clinical_followups = []
        mock_patient.nursing_followups = []

        # Mock the lab results query
        self.mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = (
            []
        )

        result = self.service._gather_patient_data(mock_patient, self.mock_db, True)

        assert result["patient"]["id"] == "test-patient-id"
        assert result["patient"]["mrn"] == "MRN001"
        assert result["patient"]["name"] == "John Doe"
        assert result["patient"]["gender"] == "male"
        assert "basic_info" not in result
        assert "surgery_indicator" not in result
        assert "clinical_followups" not in result
        assert "nursing_followups" not in result
        assert "lab_results" not in result

    def test_gather_data_with_basic_info(self):
        """Test gathering data with basic info."""
        mock_patient = MagicMock()
        mock_patient.id = "test-id"
        mock_patient.mrn = "MRN001"
        mock_patient.first_name = "John"
        mock_patient.last_name = "Doe"
        mock_patient.date_of_birth = None
        mock_patient.gender = "male"

        mock_basic_info = MagicMock()
        mock_basic_info.patient_name = "John Doe"
        mock_basic_info.gender = "male"
        mock_basic_info.age = 45
        mock_basic_info.height = 175.0
        mock_basic_info.weight = 70.0
        mock_basic_info.occupation = None
        mock_basic_info.medical_history = None
        mock_basic_info.family_history_of_stone = False
        mock_basic_info.repeated_urinary_infection = False
        mock_basic_info.surgery_type = None
        mock_basic_info.surgery_date = None
        mock_basic_info.stone_composition = None
        mock_basic_info.daily_water_intake = None
        mock_basic_info.diet_preference = None

        mock_patient.basic_info = mock_basic_info
        mock_patient.surgery_indicator = None
        mock_patient.clinical_followups = []
        mock_patient.nursing_followups = []

        self.mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = (
            []
        )

        result = self.service._gather_patient_data(mock_patient, self.mock_db, True)

        assert "basic_info" in result
        assert result["basic_info"]["patient_name"] == "John Doe"

    def test_gather_data_without_lab_results(self):
        """Test gathering data with include_lab_results=False."""
        mock_patient = MagicMock()
        mock_patient.id = "test-id"
        mock_patient.mrn = "MRN001"
        mock_patient.first_name = "John"
        mock_patient.last_name = "Doe"
        mock_patient.date_of_birth = None
        mock_patient.gender = "male"
        mock_patient.basic_info = None
        mock_patient.surgery_indicator = None
        mock_patient.clinical_followups = []
        mock_patient.nursing_followups = []

        result = self.service._gather_patient_data(mock_patient, self.mock_db, False)

        # Should not query for lab results
        self.mock_db.query.assert_not_called()
        assert "lab_results" not in result


class TestGenerateSummary:
    """Tests for generate_summary method."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_client = MagicMock()
        self.service = PatientSummaryService(anthropic_client=self.mock_client)
        self.mock_db = MagicMock()

    def test_generate_summary_success(self):
        """Test successful summary generation."""
        mock_patient = MagicMock()
        mock_patient.id = "test-patient-id"
        mock_patient.mrn = "MRN001"
        mock_patient.first_name = "John"
        mock_patient.last_name = "Doe"
        mock_patient.date_of_birth = date(1980, 5, 15)
        mock_patient.gender = "male"
        mock_patient.basic_info = None
        mock_patient.surgery_indicator = None
        mock_patient.clinical_followups = []
        mock_patient.nursing_followups = []

        self.mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = (
            []
        )

        # Mock Claude response
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(
                text="""{
                "summary_text": "Generated summary",
                "key_findings": ["Finding 1"],
                "recommendations": ["Rec 1"],
                "risk_factors": ["Risk 1"],
                "followup_status": {"clinical_completed": 0}
            }"""
            )
        ]
        self.mock_client.messages.create.return_value = mock_response

        result = self.service.generate_summary(
            patient=mock_patient,
            db=self.mock_db,
            include_lab_results=True,
            locale="en",
        )

        assert result.patient_id == mock_patient.id
        assert result.summary_text == "Generated summary"
        assert result.key_findings == ["Finding 1"]
        assert result.model == PatientSummaryService.DEFAULT_MODEL
        self.mock_client.messages.create.assert_called_once()

    def test_generate_summary_api_error(self):
        """Test handling of API error during generation."""
        mock_patient = MagicMock()
        mock_patient.id = "test-id"
        mock_patient.mrn = "MRN001"
        mock_patient.first_name = "John"
        mock_patient.last_name = "Doe"
        mock_patient.date_of_birth = None
        mock_patient.gender = "male"
        mock_patient.basic_info = None
        mock_patient.surgery_indicator = None
        mock_patient.clinical_followups = []
        mock_patient.nursing_followups = []

        self.mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = (
            []
        )

        # Mock API error
        self.mock_client.messages.create.side_effect = Exception("API connection failed")

        with pytest.raises(SummaryServiceError, match="Summary generation failed"):
            self.service.generate_summary(
                patient=mock_patient,
                db=self.mock_db,
                include_lab_results=True,
                locale="en",
            )

    def test_generate_summary_chinese_locale(self):
        """Test summary generation with Chinese locale."""
        mock_patient = MagicMock()
        mock_patient.id = "test-id"
        mock_patient.mrn = "MRN001"
        mock_patient.first_name = "张"
        mock_patient.last_name = "三"
        mock_patient.date_of_birth = None
        mock_patient.gender = "male"
        mock_patient.basic_info = None
        mock_patient.surgery_indicator = None
        mock_patient.clinical_followups = []
        mock_patient.nursing_followups = []

        self.mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = (
            []
        )

        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(text='{"summary_text": "中文摘要", "key_findings": [], "recommendations": [], "risk_factors": [], "followup_status": {}}')
        ]
        self.mock_client.messages.create.return_value = mock_response

        result = self.service.generate_summary(
            patient=mock_patient,
            db=self.mock_db,
            include_lab_results=False,
            locale="zh-CN",
        )

        # Verify the prompt was built with Chinese locale
        call_args = self.mock_client.messages.create.call_args
        prompt = call_args[1]["messages"][0]["content"]
        assert "请用中文生成摘要" in prompt


class TestGetSummaryService:
    """Tests for get_summary_service factory function."""

    def test_get_service_with_client(self):
        """Test getting service with valid client."""
        mock_client = MagicMock()

        service = get_summary_service(anthropic_client=mock_client)

        assert isinstance(service, PatientSummaryService)
        assert service.anthropic_client == mock_client
        assert service.model == PatientSummaryService.DEFAULT_MODEL

    def test_get_service_with_custom_model(self):
        """Test getting service with custom model."""
        mock_client = MagicMock()

        service = get_summary_service(
            anthropic_client=mock_client,
            model="claude-3-opus-20240229",
        )

        assert service.model == "claude-3-opus-20240229"

    def test_get_service_without_client_raises_error(self):
        """Test that getting service without client raises error."""
        with pytest.raises(SummaryServiceError):
            get_summary_service(anthropic_client=None)

    def test_each_call_creates_new_instance(self):
        """Test that each call creates a new instance."""
        mock_client = MagicMock()

        service1 = get_summary_service(anthropic_client=mock_client)
        service2 = get_summary_service(anthropic_client=mock_client)

        assert service1 is not service2

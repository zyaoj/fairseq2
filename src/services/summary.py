"""LLM-powered patient summary generation service.

This service uses Claude to generate comprehensive patient summaries by:
1. Aggregating patient data from all related entities
2. Formatting data for LLM consumption
3. Generating structured, clinically-relevant summaries
"""

import logging
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from src.models.basic_info import BasicInfo
from src.models.clinical_event import LabResult
from src.models.clinical_followup import ClinicalFollowup
from src.models.nursing_followup import NursingFollowup
from src.models.patient import Patient
from src.models.surgery_indicator import SurgeryIndicator

logger = logging.getLogger(__name__)


class SummaryServiceError(Exception):
    """Raised when summary generation fails."""

    pass


@dataclass
class PatientSummary:
    """Result of patient summary generation.

    Attributes:
        patient_id: The patient's UUID
        summary_text: Main narrative summary
        key_findings: List of key clinical findings
        recommendations: List of recommendations
        risk_factors: Identified risk factors
        followup_status: Summary of follow-up completion
        generated_at: Timestamp of generation
        model: Model used for generation
    """

    patient_id: str
    summary_text: str
    key_findings: list[str]
    recommendations: list[str]
    risk_factors: list[str]
    followup_status: dict[str, Any]
    generated_at: str
    model: str
    metadata: dict[str, Any] = field(default_factory=dict)


class PatientSummaryService:
    """Service for generating AI-powered patient summaries.

    This service aggregates patient data from multiple entities and uses
    Claude to generate comprehensive clinical summaries.
    """

    # Default model for summary generation
    DEFAULT_MODEL = "claude-sonnet-4-20250514"

    # Maximum tokens for summary response
    MAX_TOKENS = 4096

    def __init__(
        self,
        anthropic_client: Any,
        model: str | None = None,
    ):
        """Initialize the summary service.

        Args:
            anthropic_client: Anthropic client for API calls (required).
            model: Model to use for generation (default: claude-sonnet-4-20250514).

        Raises:
            SummaryServiceError: If anthropic_client is None.
        """
        if anthropic_client is None:
            raise SummaryServiceError("Anthropic client is required for summary generation")

        self.anthropic_client = anthropic_client
        self.model = model or self.DEFAULT_MODEL

    def generate_summary(
        self,
        patient: Patient,
        db: Session,
        include_lab_results: bool = True,
        locale: str = "zh-CN",
    ) -> PatientSummary:
        """Generate a comprehensive summary for a patient.

        Args:
            patient: The patient model instance
            db: Database session for loading related entities
            include_lab_results: Whether to include extracted lab result data
            locale: Locale for the summary language (default: Chinese)

        Returns:
            PatientSummary with generated content

        Raises:
            SummaryServiceError: If summary generation fails
        """
        try:
            # Gather all patient data
            patient_data = self._gather_patient_data(patient, db, include_lab_results)

            # Build the prompt
            prompt = self._build_summary_prompt(patient_data, locale)

            # Call Claude API
            response = self.anthropic_client.messages.create(
                model=self.model,
                max_tokens=self.MAX_TOKENS,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
            )

            # Parse response
            raw_response = response.content[0].text
            return self._parse_summary_response(
                raw_response,
                patient.id,
                patient_data,
            )

        except SummaryServiceError:
            raise
        except Exception as e:
            logger.exception(f"Failed to generate summary for patient {patient.id}: {e}")
            raise SummaryServiceError(f"Summary generation failed: {e}") from e

    def _gather_patient_data(
        self,
        patient: Patient,
        db: Session,
        include_lab_results: bool,
    ) -> dict[str, Any]:
        """Gather all relevant patient data for summary generation.

        Args:
            patient: The patient model instance
            db: Database session
            include_lab_results: Whether to include lab results

        Returns:
            Dictionary with all patient data
        """
        data: dict[str, Any] = {
            "patient": {
                "id": str(patient.id),
                "mrn": patient.mrn,
                "name": f"{patient.first_name} {patient.last_name}",
                "date_of_birth": patient.date_of_birth.isoformat() if patient.date_of_birth else None,
                "gender": patient.gender,
                "age": self._calculate_age(patient.date_of_birth),
            },
        }

        # Basic info
        if patient.basic_info:
            data["basic_info"] = self._serialize_basic_info(patient.basic_info)

        # Surgery indicators
        if patient.surgery_indicator:
            data["surgery_indicator"] = self._serialize_surgery_indicator(
                patient.surgery_indicator
            )

        # Clinical follow-ups
        if patient.clinical_followups:
            data["clinical_followups"] = [
                self._serialize_clinical_followup(f) for f in patient.clinical_followups
            ]

        # Nursing follow-ups
        if patient.nursing_followups:
            data["nursing_followups"] = [
                self._serialize_nursing_followup(f) for f in patient.nursing_followups
            ]

        # Lab results (if enabled)
        if include_lab_results:
            lab_results = (
                db.query(LabResult)
                .filter(LabResult.patient_id == patient.id)
                .order_by(LabResult.event_date.desc())
                .limit(10)  # Limit to most recent 10
                .all()
            )
            if lab_results:
                data["lab_results"] = [
                    self._serialize_lab_result(lr) for lr in lab_results
                ]

        return data

    def _calculate_age(self, dob: date | None) -> int | None:
        """Calculate age from date of birth."""
        if not dob:
            return None
        today = date.today()
        age = today.year - dob.year
        if (today.month, today.day) < (dob.month, dob.day):
            age -= 1
        return age

    def _serialize_basic_info(self, info: BasicInfo) -> dict[str, Any]:
        """Serialize BasicInfo to dictionary."""
        return {
            "patient_name": info.patient_name,
            "gender": info.gender,
            "age": info.age,
            "height": info.height,
            "weight": info.weight,
            "occupation": info.occupation,
            "medical_history": info.medical_history,
            "family_history_of_stone": info.family_history_of_stone,
            "repeated_urinary_infection": info.repeated_urinary_infection,
            "surgery_type": info.surgery_type,
            "surgery_date": info.surgery_date.isoformat() if info.surgery_date else None,
            "stone_composition": info.stone_composition,
            "daily_water_intake": info.daily_water_intake,
            "diet_preference": info.diet_preference,
        }

    def _serialize_surgery_indicator(self, indicator: SurgeryIndicator) -> dict[str, Any]:
        """Serialize SurgeryIndicator to dictionary."""
        return {
            "clinical_diagnosis": indicator.clinical_diagnosis,
            "stone_location": indicator.stone_location,
            "stone_size": indicator.stone_size,
            "hydronephrosis_degree": indicator.hydronephrosis_degree,
            # Pre-operative values
            "pre_op": {
                "alt": indicator.alt_value_before,
                "ast": indicator.ast_value_before,
                "ggt": indicator.ggt_value_before,
                "scr": indicator.scr_value_before,
                "wbc": indicator.wbc_value_before,
                "hb": indicator.hb_value_before,
                "urine_ph": indicator.urine_ph_value_before,
                "urine_culture": indicator.urine_culture_result_before,
            },
            # Post-operative values
            "post_op": {
                "alt": indicator.alt_value_after,
                "ast": indicator.ast_value_after,
                "ggt": indicator.ggt_value_after,
                "scr": indicator.scr_value_after,
                "wbc": indicator.wbc_value_after,
                "hb": indicator.hb_value_after,
                "urine_ph": indicator.urine_ph_value_after,
                "urine_culture": indicator.urine_culture_result_after,
            },
            "stone_clearance": indicator.stone_clearance_after,
            "stone_composition": indicator.stone_composition_after,
        }

    def _serialize_clinical_followup(self, followup: ClinicalFollowup) -> dict[str, Any]:
        """Serialize ClinicalFollowup to dictionary."""
        return {
            "stage": followup.stage,
            "stage_name": followup.stage_name,
            "followup_date": followup.followup_date.isoformat() if followup.followup_date else None,
            "recurrence": followup.followup_recurrence,
            "stone_size": followup.followup_stone_size,
            "imaging": followup.followup_imaging,
            "lab_values": {
                "alt": followup.followup_alt,
                "ast": followup.followup_ast,
                "scr": followup.followup_scr,
                "wbc": followup.followup_wbc,
                "urine_culture": followup.followup_urine_culture,
            },
            "medication": followup.followup_medication,
            "compliance": followup.followup_compliance,
            "adverse_effects": followup.followup_adverse,
            "plan": followup.followup_plan,
        }

    def _serialize_nursing_followup(self, followup: NursingFollowup) -> dict[str, Any]:
        """Serialize NursingFollowup to dictionary."""
        return {
            "stage": followup.stage,
            "stage_name": followup.stage_name,
            "followup_date": followup.followup_date.isoformat() if followup.followup_date else None,
            "mode": followup.nursing_mode,
            "antibiotic": followup.nursing_antibiotic,
            "timed_medication": followup.nursing_timed_med,
            "urine_ph": followup.nursing_urine_ph,
            "urine_output_sufficient": followup.nursing_urine_output,
            "adverse_effects": followup.nursing_adverse_effects,
            "residual_stone": followup.nursing_residual_stone,
            "water_intake": followup.nursing_water,
            "diet": followup.nursing_diet,
            "depression": followup.nursing_depression,
            "support": followup.nursing_support,
        }

    def _serialize_lab_result(self, lab_result: LabResult) -> dict[str, Any]:
        """Serialize LabResult to dictionary."""
        return {
            "id": str(lab_result.id),
            "title": lab_result.title,
            "event_date": lab_result.event_date.isoformat() if lab_result.event_date else None,
            "extraction_status": lab_result.extraction_status.value if lab_result.extraction_status else None,
            "extracted_data": lab_result.extracted_data,
            "confidence": lab_result.extraction_confidence,
        }

    def _build_summary_prompt(self, patient_data: dict[str, Any], locale: str) -> str:
        """Build the prompt for summary generation.

        Args:
            patient_data: Aggregated patient data
            locale: Locale for summary language

        Returns:
            Prompt string for Claude
        """
        import json

        language_instruction = (
            "请用中文生成摘要。" if locale.startswith("zh") else "Generate the summary in English."
        )

        return f"""You are a medical AI assistant specializing in urology. Generate a comprehensive patient summary based on the provided data.

## Patient Data

```json
{json.dumps(patient_data, indent=2, ensure_ascii=False, default=str)}
```

## Instructions

{language_instruction}

Analyze the patient data and generate a structured clinical summary. Focus on:
1. Patient overview and demographics
2. Medical history relevant to urology (especially urinary tract infections and stones)
3. Surgical history and outcomes
4. Follow-up progress and compliance
5. Current clinical status
6. Risk factors for recurrence
7. Recommendations for ongoing care

## Output Format

Return a JSON object with this EXACT structure:

```json
{{
  "summary_text": "A comprehensive narrative summary (2-3 paragraphs) covering the patient's condition, treatment journey, and current status.",
  "key_findings": [
    "Key finding 1",
    "Key finding 2",
    "..."
  ],
  "recommendations": [
    "Recommendation 1",
    "Recommendation 2",
    "..."
  ],
  "risk_factors": [
    "Risk factor 1",
    "Risk factor 2",
    "..."
  ],
  "followup_status": {{
    "clinical_completed": 3,
    "clinical_total": 5,
    "nursing_completed": 4,
    "nursing_total": 6,
    "next_due": "Stage 4 clinical follow-up",
    "overdue": false
  }}
}}
```

Guidelines:
- Be clinically accurate and use appropriate medical terminology
- Highlight any abnormal lab values or concerning trends
- Note medication compliance issues if present
- Identify patterns in follow-up data
- For missing data, note it in the summary rather than making assumptions
- Keep recommendations actionable and specific

Return ONLY the JSON object, no additional text."""

    def _parse_summary_response(
        self,
        response_text: str,
        patient_id: str,
        patient_data: dict[str, Any],
    ) -> PatientSummary:
        """Parse the Claude response into a PatientSummary.

        Args:
            response_text: Raw response from Claude
            patient_id: Patient UUID
            patient_data: Original patient data

        Returns:
            PatientSummary with parsed content
        """
        import json
        import re
        from datetime import datetime, timezone

        # Try to extract JSON from response
        json_match = re.search(r"```json\s*([\s\S]*?)\s*```", response_text)
        if json_match:
            json_str = json_match.group(1)
        else:
            json_match = re.search(r"\{[\s\S]*\}", response_text)
            if json_match:
                json_str = json_match.group(0)
            else:
                # If no JSON found, create a basic summary
                logger.warning(f"No JSON found in summary response for patient {patient_id}")
                return PatientSummary(
                    patient_id=patient_id,
                    summary_text=response_text,
                    key_findings=[],
                    recommendations=[],
                    risk_factors=[],
                    followup_status={},
                    generated_at=datetime.now(timezone.utc).isoformat(),
                    model=self.model,
                    metadata={"raw_response": response_text},
                )

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse summary JSON for patient {patient_id}: {e}")
            return PatientSummary(
                patient_id=patient_id,
                summary_text=response_text,
                key_findings=[],
                recommendations=[],
                risk_factors=[],
                followup_status={},
                generated_at=datetime.now(timezone.utc).isoformat(),
                model=self.model,
                metadata={"raw_response": response_text, "parse_error": str(e)},
            )

        return PatientSummary(
            patient_id=patient_id,
            summary_text=data.get("summary_text", ""),
            key_findings=data.get("key_findings", []),
            recommendations=data.get("recommendations", []),
            risk_factors=data.get("risk_factors", []),
            followup_status=data.get("followup_status", {}),
            generated_at=datetime.now(timezone.utc).isoformat(),
            model=self.model,
            metadata={
                "patient_data_keys": list(patient_data.keys()),
            },
        )


def get_summary_service(
    anthropic_client: Any,
    model: str | None = None,
) -> PatientSummaryService:
    """Get a patient summary service instance.

    Note: Each call creates a new instance because the anthropic_client must be provided.

    Args:
        anthropic_client: Anthropic client for API calls (required)
        model: Optional model to use for generation

    Returns:
        PatientSummaryService instance
    """
    return PatientSummaryService(
        anthropic_client=anthropic_client,
        model=model,
    )

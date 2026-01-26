"""Tests for SQLAlchemy models."""

from datetime import date, datetime, timezone

import pytest


class TestPatientModel:
    """Test Patient model."""

    def test_patient_creation(self) -> None:
        """Test creating a Patient instance."""
        from src.models import Patient

        patient = Patient(
            mrn="MRN001",
            first_name="John",
            last_name="Doe",
            date_of_birth=date(1980, 1, 15),
            gender="male",
        )

        assert patient.mrn == "MRN001"
        assert patient.first_name == "John"
        assert patient.last_name == "Doe"
        assert patient.gender == "male"

    def test_patient_repr(self) -> None:
        """Test Patient string representation."""
        from src.models import Patient

        patient = Patient(
            id="test-uuid",
            mrn="MRN001",
            first_name="John",
            last_name="Doe",
            date_of_birth=date(1980, 1, 15),
            gender="male",
        )

        assert "MRN001" in repr(patient)
        assert "John" in repr(patient)


class TestClinicalEventModel:
    """Test ClinicalEvent and LabResult models."""

    def test_lifecycle_phase_enum(self) -> None:
        """Test LifecyclePhase enum values."""
        from src.models import LifecyclePhase

        assert LifecyclePhase.CONSULTATION.value == "consultation"
        assert LifecyclePhase.PRE_SURGERY.value == "pre_surgery"
        assert LifecyclePhase.SURGERY.value == "surgery"
        assert LifecyclePhase.POST_SURGERY.value == "post_surgery"
        assert LifecyclePhase.FOLLOW_UP.value == "follow_up"

    def test_extraction_status_enum(self) -> None:
        """Test ExtractionStatus enum values."""
        from src.models import ExtractionStatus

        assert ExtractionStatus.PENDING.value == "pending"
        assert ExtractionStatus.PROCESSING.value == "processing"
        assert ExtractionStatus.COMPLETED.value == "completed"
        assert ExtractionStatus.FAILED.value == "failed"

    def test_lab_result_creation(self) -> None:
        """Test creating a LabResult instance."""
        from src.models import ExtractionStatus, LabResult, LifecyclePhase

        lab_result = LabResult(
            patient_id="patient-uuid",
            phase=LifecyclePhase.PRE_SURGERY,
            event_type="lab_result",
            event_date=datetime.now(timezone.utc),
            title="Blood Test",
            original_file_path="/uploads/test.pdf",
            file_type="pdf",
            extraction_status=ExtractionStatus.PENDING,
        )

        assert lab_result.phase == LifecyclePhase.PRE_SURGERY
        assert lab_result.file_type == "pdf"
        assert lab_result.extraction_status == ExtractionStatus.PENDING


class TestUserModel:
    """Test User model."""

    def test_user_creation(self) -> None:
        """Test creating a User instance."""
        from src.models import User

        user = User(
            username="drsmith",
            email="drsmith@hospital.com",
            hashed_password="hashed_pw",
            role="urologist",
            is_active=True,
        )

        assert user.username == "drsmith"
        assert user.email == "drsmith@hospital.com"
        assert user.role == "urologist"
        assert user.is_active is True

    def test_user_repr(self) -> None:
        """Test User string representation."""
        from src.models import User

        user = User(
            id="test-uuid",
            username="drsmith",
            email="drsmith@hospital.com",
            hashed_password="hashed_pw",
            role="urologist",
        )

        assert "drsmith" in repr(user)
        assert "urologist" in repr(user)

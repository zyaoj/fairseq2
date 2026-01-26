"""Tests for Pydantic schemas."""

from datetime import date, datetime

import pytest
from pydantic import ValidationError

from src.schemas import (
    ClinicalEventCreate,
    LabResultCreate,
    PatientCreate,
    PatientUpdate,
    Token,
    UserCreate,
    UserLogin,
)
from src.models.clinical_event import ExtractionStatus, LifecyclePhase


class TestPatientSchemas:
    """Tests for Patient schemas."""

    def test_patient_create_valid(self) -> None:
        """Test creating a valid patient."""
        patient = PatientCreate(
            mrn="MRN001",
            first_name="John",
            last_name="Doe",
            date_of_birth=date(1990, 1, 15),
            gender="male",
            hospital_id="HOSP001",
        )
        assert patient.mrn == "MRN001"
        assert patient.first_name == "John"
        assert patient.hospital_id == "HOSP001"

    def test_patient_create_without_hospital_id(self) -> None:
        """Test creating a patient without optional hospital_id."""
        patient = PatientCreate(
            mrn="MRN002",
            first_name="Jane",
            last_name="Doe",
            date_of_birth=date(1985, 6, 20),
            gender="female",
        )
        assert patient.hospital_id is None

    def test_patient_create_invalid_mrn(self) -> None:
        """Test that empty MRN fails validation."""
        with pytest.raises(ValidationError):
            PatientCreate(
                mrn="",  # Invalid: empty string
                first_name="John",
                last_name="Doe",
                date_of_birth=date(1990, 1, 15),
                gender="male",
            )

    def test_patient_update_partial(self) -> None:
        """Test partial patient update."""
        update = PatientUpdate(first_name="NewName")
        assert update.first_name == "NewName"
        assert update.last_name is None
        assert update.date_of_birth is None


class TestUserSchemas:
    """Tests for User schemas."""

    def test_user_create_valid(self) -> None:
        """Test creating a valid user."""
        user = UserCreate(
            username="testuser",
            email="test@example.com",
            password="securepassword123",
            role="urologist",
            hospital_id="HOSP001",
        )
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.password == "securepassword123"

    def test_user_create_invalid_email(self) -> None:
        """Test that invalid email fails validation."""
        with pytest.raises(ValidationError):
            UserCreate(
                username="testuser",
                email="invalid-email",  # Invalid email format
                password="securepassword123",
            )

    def test_user_create_short_password(self) -> None:
        """Test that short password fails validation."""
        with pytest.raises(ValidationError):
            UserCreate(
                username="testuser",
                email="test@example.com",
                password="short",  # Too short
            )

    def test_user_login(self) -> None:
        """Test user login schema."""
        login = UserLogin(username="testuser", password="mypassword")
        assert login.username == "testuser"
        assert login.password == "mypassword"


class TestClinicalEventSchemas:
    """Tests for ClinicalEvent schemas."""

    def test_clinical_event_create(self) -> None:
        """Test creating a clinical event."""
        event = ClinicalEventCreate(
            patient_id="patient-uuid-123",
            phase=LifecyclePhase.CONSULTATION,
            event_type="lab_result",
            event_date=datetime(2024, 1, 15, 10, 30),
            title="Blood Test Results",
            description="Annual blood work",
        )
        assert event.phase == LifecyclePhase.CONSULTATION
        assert event.event_type == "lab_result"

    def test_lab_result_create(self) -> None:
        """Test creating a lab result."""
        lab_result = LabResultCreate(
            patient_id="patient-uuid-123",
            phase=LifecyclePhase.PRE_SURGERY,
            event_type="lab_result",
            event_date=datetime(2024, 1, 15, 10, 30),
            title="PSA Test",
            original_file_path="/uploads/psa_result.pdf",
            file_type="pdf",
        )
        assert lab_result.original_file_path == "/uploads/psa_result.pdf"
        assert lab_result.file_type == "pdf"


class TestCommonSchemas:
    """Tests for common schemas."""

    def test_token_schema(self) -> None:
        """Test token schema."""
        token = Token(access_token="jwt-token-here")
        assert token.access_token == "jwt-token-here"
        assert token.token_type == "bearer"

    def test_token_with_custom_type(self) -> None:
        """Test token with custom type."""
        token = Token(access_token="jwt-token-here", token_type="custom")
        assert token.token_type == "custom"

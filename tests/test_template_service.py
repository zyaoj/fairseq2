"""Tests for template service with hospital inheritance."""

import tempfile
from pathlib import Path

import pytest

from src.services.template_service import (
    TemplateNotFoundError,
    TemplateService,
    get_template_service,
)


@pytest.fixture
def template_dir(tmp_path: Path) -> Path:
    """Create a temporary template directory structure."""
    # Create base directory
    base_dir = tmp_path / "base"
    base_dir.mkdir()

    # Create hospitals directory
    hospitals_dir = tmp_path / "hospitals"
    hospitals_dir.mkdir()

    # Create hospital_001 directory
    hospital_001_dir = hospitals_dir / "hospital_001"
    hospital_001_dir.mkdir()

    # Create base templates
    (base_dir / "followup_registration.docx").write_text("base template content")
    (base_dir / "discharge_summary.docx").write_text("base discharge content")

    # Create hospital-specific template (override)
    (hospital_001_dir / "followup_registration.docx").write_text(
        "hospital_001 template content"
    )
    # Create hospital-only template
    (hospital_001_dir / "admission_form.docx").write_text(
        "hospital_001 admission content"
    )

    return tmp_path


class TestTemplateService:
    """Tests for TemplateService class."""

    def test_get_template_service_returns_instance(self):
        """Test that get_template_service returns a TemplateService instance."""
        service = get_template_service()
        assert isinstance(service, TemplateService)

    def test_init_with_custom_dir(self, template_dir: Path):
        """Test initialization with custom template directory."""
        service = TemplateService(template_dir=template_dir)
        assert service.template_dir == template_dir

    def test_get_template_path_base_only(self, template_dir: Path):
        """Test getting template path when only base template exists."""
        service = TemplateService(template_dir=template_dir)

        # discharge_summary only exists in base
        path = service.get_template_path("discharge_summary")
        assert path == template_dir / "base" / "discharge_summary.docx"

    def test_get_template_path_base_without_hospital_id(self, template_dir: Path):
        """Test getting template path without hospital_id falls back to base."""
        service = TemplateService(template_dir=template_dir)

        path = service.get_template_path("followup_registration")
        assert path == template_dir / "base" / "followup_registration.docx"

    def test_get_template_path_hospital_override(self, template_dir: Path):
        """Test getting template path with hospital override."""
        service = TemplateService(template_dir=template_dir)

        # hospital_001 has its own followup_registration
        path = service.get_template_path("followup_registration", "hospital_001")
        assert path == template_dir / "hospitals" / "hospital_001" / "followup_registration.docx"

    def test_get_template_path_hospital_fallback_to_base(self, template_dir: Path):
        """Test that hospital without override falls back to base."""
        service = TemplateService(template_dir=template_dir)

        # hospital_001 doesn't have discharge_summary, should fall back to base
        path = service.get_template_path("discharge_summary", "hospital_001")
        assert path == template_dir / "base" / "discharge_summary.docx"

    def test_get_template_path_nonexistent_hospital(self, template_dir: Path):
        """Test getting template for non-existent hospital falls back to base."""
        service = TemplateService(template_dir=template_dir)

        # hospital_999 doesn't exist, should fall back to base
        path = service.get_template_path("followup_registration", "hospital_999")
        assert path == template_dir / "base" / "followup_registration.docx"

    def test_get_template_path_not_found(self, template_dir: Path):
        """Test that TemplateNotFoundError is raised for non-existent template."""
        service = TemplateService(template_dir=template_dir)

        with pytest.raises(TemplateNotFoundError) as exc_info:
            service.get_template_path("nonexistent_template")

        assert "nonexistent_template" in str(exc_info.value)

    def test_get_template_path_not_found_with_hospital(self, template_dir: Path):
        """Test TemplateNotFoundError with hospital_id context."""
        service = TemplateService(template_dir=template_dir)

        with pytest.raises(TemplateNotFoundError):
            service.get_template_path("nonexistent_template", "hospital_001")


class TestListAvailableTemplates:
    """Tests for list_available_templates method."""

    def test_list_base_templates_only(self, template_dir: Path):
        """Test listing templates without hospital_id returns base templates."""
        service = TemplateService(template_dir=template_dir)

        templates = service.list_available_templates()

        # Should have 2 base templates
        assert len(templates) == 2
        names = [t["name"] for t in templates]
        assert "followup_registration" in names
        assert "discharge_summary" in names

        # All should be marked as 'base'
        for t in templates:
            assert t["source"] == "base"

    def test_list_templates_with_hospital_override(self, template_dir: Path):
        """Test listing templates with hospital override."""
        service = TemplateService(template_dir=template_dir)

        templates = service.list_available_templates("hospital_001")

        # Should have base templates + hospital-specific ones
        names = [t["name"] for t in templates]
        assert "followup_registration" in names
        assert "discharge_summary" in names
        assert "admission_form" in names

        # Check sources
        template_dict = {t["name"]: t["source"] for t in templates}
        assert template_dict["followup_registration"] == "hospital"  # Overridden
        assert template_dict["discharge_summary"] == "base"  # Not overridden
        assert template_dict["admission_form"] == "hospital"  # Hospital-only

    def test_list_templates_nonexistent_hospital(self, template_dir: Path):
        """Test listing templates for non-existent hospital returns base only."""
        service = TemplateService(template_dir=template_dir)

        templates = service.list_available_templates("hospital_999")

        # Should only have base templates
        assert len(templates) == 2
        for t in templates:
            assert t["source"] == "base"

    def test_list_templates_sorted_by_name(self, template_dir: Path):
        """Test that templates are sorted alphabetically by name."""
        service = TemplateService(template_dir=template_dir)

        templates = service.list_available_templates("hospital_001")
        names = [t["name"] for t in templates]

        assert names == sorted(names)


class TestTemplateExists:
    """Tests for template_exists method."""

    def test_template_exists_base(self, template_dir: Path):
        """Test checking existence of base template."""
        service = TemplateService(template_dir=template_dir)

        assert service.template_exists("followup_registration") is True
        assert service.template_exists("discharge_summary") is True
        assert service.template_exists("nonexistent") is False

    def test_template_exists_with_hospital(self, template_dir: Path):
        """Test checking existence with hospital_id."""
        service = TemplateService(template_dir=template_dir)

        # Hospital override exists
        assert service.template_exists("followup_registration", "hospital_001") is True
        # Falls back to base
        assert service.template_exists("discharge_summary", "hospital_001") is True
        # Doesn't exist anywhere
        assert service.template_exists("nonexistent", "hospital_001") is False

    def test_template_exists_hospital_only(self, template_dir: Path):
        """Test checking hospital-only template."""
        service = TemplateService(template_dir=template_dir)

        # admission_form only exists in hospital_001
        assert service.template_exists("admission_form", "hospital_001") is True
        # Should not exist without hospital_id
        assert service.template_exists("admission_form") is False


class TestGetTemplateSource:
    """Tests for get_template_source method."""

    def test_get_source_base(self, template_dir: Path):
        """Test getting source of base template."""
        service = TemplateService(template_dir=template_dir)

        assert service.get_template_source("discharge_summary") == "base"
        assert service.get_template_source("followup_registration") == "base"

    def test_get_source_hospital_override(self, template_dir: Path):
        """Test getting source of hospital-overridden template."""
        service = TemplateService(template_dir=template_dir)

        # With hospital_id, should return 'hospital' for overridden template
        assert service.get_template_source("followup_registration", "hospital_001") == "hospital"
        # discharge_summary not overridden, should return 'base'
        assert service.get_template_source("discharge_summary", "hospital_001") == "base"

    def test_get_source_hospital_only(self, template_dir: Path):
        """Test getting source of hospital-only template."""
        service = TemplateService(template_dir=template_dir)

        assert service.get_template_source("admission_form", "hospital_001") == "hospital"

    def test_get_source_not_found(self, template_dir: Path):
        """Test getting source of non-existent template returns None."""
        service = TemplateService(template_dir=template_dir)

        assert service.get_template_source("nonexistent") is None
        assert service.get_template_source("nonexistent", "hospital_001") is None


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_empty_base_dir(self, tmp_path: Path):
        """Test behavior when base directory is empty."""
        base_dir = tmp_path / "base"
        base_dir.mkdir()

        service = TemplateService(template_dir=tmp_path)

        templates = service.list_available_templates()
        assert templates == []

    def test_no_base_dir(self, tmp_path: Path):
        """Test behavior when base directory doesn't exist."""
        service = TemplateService(template_dir=tmp_path)

        templates = service.list_available_templates()
        assert templates == []

    def test_hospital_dir_only(self, tmp_path: Path):
        """Test when only hospital directory exists (no base)."""
        hospitals_dir = tmp_path / "hospitals" / "hospital_001"
        hospitals_dir.mkdir(parents=True)
        (hospitals_dir / "custom.docx").write_text("content")

        service = TemplateService(template_dir=tmp_path)

        # Without hospital_id, should find nothing (no base)
        templates = service.list_available_templates()
        assert templates == []

        # With hospital_id, should find hospital-only template
        templates = service.list_available_templates("hospital_001")
        assert len(templates) == 1
        assert templates[0]["name"] == "custom"
        assert templates[0]["source"] == "hospital"

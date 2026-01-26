"""Hospital-aware Word template resolution service.

This service loads Word document templates with hospital inheritance:
- Base templates (required) in word_templates/base/
- Hospital-specific templates (optional) in word_templates/hospitals/{hospital_id}/
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class TemplateNotFoundError(Exception):
    """Raised when a requested template cannot be found."""

    pass


class TemplateService:
    """Service for resolving Word document templates with hospital fallback.

    Resolution order:
    1. hospitals/{hospital_id}/{template_name}.docx (if hospital_id provided)
    2. base/{template_name}.docx
    """

    def __init__(self, template_dir: Path | None = None):
        """Initialize the template service.

        Args:
            template_dir: Directory containing Word template files.
                          Defaults to src/word_templates/
        """
        if template_dir is None:
            template_dir = Path(__file__).parent.parent / "word_templates"
        self.template_dir = template_dir

    def get_template_path(
        self, template_name: str, hospital_id: str | None = None
    ) -> Path:
        """Resolve template path with hospital fallback.

        Resolution order:
        1. hospitals/{hospital_id}/{template_name}.docx
        2. base/{template_name}.docx

        Args:
            template_name: Name of the template (without .docx extension)
            hospital_id: Optional hospital ID for hospital-specific template

        Returns:
            Path to the resolved template file

        Raises:
            TemplateNotFoundError: If no template is found
        """
        # Try hospital-specific template first
        if hospital_id:
            hospital_path = (
                self.template_dir
                / "hospitals"
                / hospital_id
                / f"{template_name}.docx"
            )
            if hospital_path.exists():
                return hospital_path

        # Fall back to base template
        base_path = self.template_dir / "base" / f"{template_name}.docx"
        if base_path.exists():
            return base_path

        raise TemplateNotFoundError(
            f"Template '{template_name}' not found in base or hospital-specific directories"
        )

    def list_available_templates(
        self, hospital_id: str | None = None
    ) -> list[dict[str, str]]:
        """List all templates available for a hospital.

        Returns base templates plus any hospital-specific templates.
        Hospital-specific templates override base templates with the same name.

        Args:
            hospital_id: Optional hospital ID to include hospital-specific templates

        Returns:
            List of template info dicts with 'name', 'source' ('base' or 'hospital')
        """
        templates: dict[str, str] = {}  # name -> source

        # Collect base templates
        base_dir = self.template_dir / "base"
        if base_dir.exists():
            for template_file in base_dir.glob("*.docx"):
                templates[template_file.stem] = "base"

        # Collect hospital-specific templates (override base)
        if hospital_id:
            hospital_dir = self.template_dir / "hospitals" / hospital_id
            if hospital_dir.exists():
                for template_file in hospital_dir.glob("*.docx"):
                    templates[template_file.stem] = "hospital"

        return [
            {"name": name, "source": source}
            for name, source in sorted(templates.items())
        ]

    def template_exists(
        self, template_name: str, hospital_id: str | None = None
    ) -> bool:
        """Check if a template exists.

        Args:
            template_name: Name of the template (without .docx extension)
            hospital_id: Optional hospital ID for hospital-specific template

        Returns:
            True if template exists, False otherwise
        """
        try:
            self.get_template_path(template_name, hospital_id)
            return True
        except TemplateNotFoundError:
            return False

    def get_template_source(
        self, template_name: str, hospital_id: str | None = None
    ) -> str | None:
        """Get the source of a template (base or hospital).

        Args:
            template_name: Name of the template
            hospital_id: Optional hospital ID

        Returns:
            'base', 'hospital', or None if not found
        """
        if hospital_id:
            hospital_path = (
                self.template_dir
                / "hospitals"
                / hospital_id
                / f"{template_name}.docx"
            )
            if hospital_path.exists():
                return "hospital"

        base_path = self.template_dir / "base" / f"{template_name}.docx"
        if base_path.exists():
            return "base"

        return None


def get_template_service() -> TemplateService:
    """Get template service instance."""
    return TemplateService()

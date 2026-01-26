"""YAML-based entity schema loading service with hospital inheritance.

This service loads entity schemas from YAML files, enabling configurable
entity definitions without hardcoding field names, types, or validations.

Supports hierarchical inheritance:
- Base schemas (required) in entity_schemas/base/
- Hospital-specific overrides (optional) in entity_schemas/hospitals/{hospital_id}/
"""

import copy
import logging

logger = logging.getLogger(__name__)
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml


@dataclass
class FieldValidation:
    """Validation rules for an entity field."""

    required: bool = False
    min_length: int | None = None
    max_length: int | None = None
    min_value: float | None = None
    max_value: float | None = None
    pattern: str | None = None
    allowed_values: list[str] | None = None


@dataclass
class EntityField:
    """Definition of a single field in an entity schema."""

    name: str
    type: str  # string, integer, float, boolean, date, datetime, enum, multi_enum
    i18n_key: str
    description: str = ""
    validation: FieldValidation = field(default_factory=FieldValidation)
    enum_options: list[dict[str, str]] | None = None  # For enum/multi_enum types
    default: Any = None
    stage_specific: bool = False  # True for fields that vary by follow-up stage


@dataclass
class EntitySchema:
    """Complete schema definition for an entity type."""

    name: str
    display_name_key: str  # i18n key for display name
    description: str
    fields: list[EntityField]
    stages: list[dict[str, Any]] | None = None  # For follow-up entities with stages
    hospital_id: str | None = None  # Hospital this schema is resolved for

    def get_field(self, field_name: str) -> EntityField | None:
        """Get a field by name."""
        for f in self.fields:
            if f.name == field_name:
                return f
        return None

    def get_required_fields(self) -> list[EntityField]:
        """Get all required fields."""
        return [f for f in self.fields if f.validation.required]

    def get_field_names(self) -> list[str]:
        """Get all field names."""
        return [f.name for f in self.fields]


class SchemaService:
    """Service for loading entity schemas with hospital inheritance.

    Resolution order:
    1. Load base schema (required) from entity_schemas/base/
    2. If hospital_id provided, load hospital override from entity_schemas/hospitals/{hospital_id}/
    3. Deep merge: base + override (hospital values win on conflicts)
    """

    def __init__(self, schema_dir: Path | None = None):
        """Initialize the schema service.

        Args:
            schema_dir: Directory containing YAML schema files.
                        Defaults to src/entity_schemas/
        """
        if schema_dir is None:
            # Default to src/entity_schemas/ relative to this file
            schema_dir = Path(__file__).parent.parent / "entity_schemas"
        self.schema_dir = schema_dir
        self._cache: dict[tuple[str, str | None], EntitySchema] = {}
        self._normalization_cache: dict[str | None, dict[str, Any]] = {}

    def load_schema(
        self, entity_type: str, hospital_id: str | None = None
    ) -> EntitySchema:
        """Load an entity schema with hospital inheritance.

        Args:
            entity_type: Name of the entity (e.g., 'basic_info', 'clinical_followup')
            hospital_id: Optional hospital ID for hospital-specific overrides

        Returns:
            EntitySchema object (merged if hospital override exists)

        Raises:
            FileNotFoundError: If base schema file doesn't exist
            ValueError: If schema file is invalid
        """
        cache_key = (entity_type, hospital_id)
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Load base schema (required)
        base_path = self.schema_dir / "base" / f"{entity_type}.yaml"
        if not base_path.exists():
            raise FileNotFoundError(f"Base schema file not found: {base_path}")

        with open(base_path, encoding="utf-8") as f:
            raw_schema = yaml.safe_load(f)

        # Load hospital override if exists
        if hospital_id:
            hospital_path = (
                self.schema_dir / "hospitals" / hospital_id / f"{entity_type}.yaml"
            )
            if hospital_path.exists():
                with open(hospital_path, encoding="utf-8") as f:
                    hospital_override = yaml.safe_load(f)
                raw_schema = self._merge_schemas(raw_schema, hospital_override)

        schema = self._parse_schema(entity_type, raw_schema, hospital_id)
        self._cache[cache_key] = schema
        return schema

    def _merge_schemas(
        self, base: dict[str, Any], override: dict[str, Any]
    ) -> dict[str, Any]:
        """Deep merge base schema with hospital override.

        Supports:
        - field_overrides: Modify existing base field properties
        - field_additions: Add new fields not in base schema
        - Direct field replacement via 'fields' key
        """
        result = copy.deepcopy(base)

        # Handle field_overrides: modify existing field properties
        field_overrides = override.get("field_overrides", [])
        if field_overrides:
            base_fields = {f["name"]: f for f in result.get("fields", [])}
            for override_field in field_overrides:
                field_name = override_field["name"]
                if field_name in base_fields:
                    # Merge override into base field
                    base_fields[field_name] = self._deep_merge_dict(
                        base_fields[field_name], override_field
                    )
            result["fields"] = list(base_fields.values())

        # Handle field_additions: add new fields
        field_additions = override.get("field_additions", [])
        if field_additions:
            result.setdefault("fields", []).extend(field_additions)

        # Handle direct field replacement (full override)
        if "fields" in override and "field_overrides" not in override:
            # Full replacement mode: hospital provides complete fields list
            result["fields"] = override["fields"]

        # Merge top-level properties (except fields which are handled specially)
        for key in override:
            if key not in ("fields", "field_overrides", "field_additions", "extends"):
                result[key] = override[key]

        return result

    def _deep_merge_dict(
        self, base: dict[str, Any], override: dict[str, Any]
    ) -> dict[str, Any]:
        """Recursively merge two dictionaries, override wins on conflicts."""
        result = copy.deepcopy(base)
        for key, value in override.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = self._deep_merge_dict(result[key], value)
            else:
                result[key] = copy.deepcopy(value)
        return result

    def _parse_schema(
        self, entity_type: str, raw: dict[str, Any], hospital_id: str | None = None
    ) -> EntitySchema:
        """Parse raw YAML data into EntitySchema object."""
        fields = []
        for field_data in raw.get("fields", []):
            validation_data = field_data.get("validation", {})
            validation = FieldValidation(
                required=validation_data.get("required", False),
                min_length=validation_data.get("min_length"),
                max_length=validation_data.get("max_length"),
                min_value=validation_data.get("min_value"),
                max_value=validation_data.get("max_value"),
                pattern=validation_data.get("pattern"),
                allowed_values=validation_data.get("allowed_values"),
            )

            entity_field = EntityField(
                name=field_data["name"],
                type=field_data["type"],
                i18n_key=field_data.get("i18n_key", f"{entity_type}.{field_data['name']}"),
                description=field_data.get("description", ""),
                validation=validation,
                enum_options=field_data.get("enum_options"),
                default=field_data.get("default"),
                stage_specific=field_data.get("stage_specific", False),
            )
            fields.append(entity_field)

        return EntitySchema(
            name=entity_type,
            display_name_key=raw.get("display_name_key", f"{entity_type}.title"),
            description=raw.get("description", ""),
            fields=fields,
            stages=raw.get("stages"),
            hospital_id=hospital_id,
        )

    def get_all_schemas(
        self, hospital_id: str | None = None
    ) -> dict[str, EntitySchema]:
        """Load and return all available entity schemas.

        Args:
            hospital_id: Optional hospital ID for hospital-specific overrides

        Returns:
            Dictionary of entity_type -> EntitySchema
        """
        base_dir = self.schema_dir / "base"
        if not base_dir.exists():
            return {}

        result = {}
        for schema_file in base_dir.glob("*.yaml"):
            entity_type = schema_file.stem
            if entity_type != "normalization_rules":
                result[entity_type] = self.load_schema(entity_type, hospital_id)

        return result

    def load_normalization_rules(
        self, hospital_id: str | None = None
    ) -> dict[str, Any]:
        """Load normalization rules with hospital inheritance.

        Resolution order:
        1. Load base rules from entity_schemas/base/normalization_rules.yaml
        2. If hospital_id provided, merge hospital overrides

        Args:
            hospital_id: Optional hospital ID for hospital-specific overrides

        Returns:
            Dictionary containing checkbox formats and field normalizations
        """
        if hospital_id in self._normalization_cache:
            return self._normalization_cache[hospital_id]

        # Load base rules (required)
        base_path = self.schema_dir / "base" / "normalization_rules.yaml"
        if not base_path.exists():
            return {}

        with open(base_path, encoding="utf-8") as f:
            rules = yaml.safe_load(f) or {}

        # Load hospital override if exists
        if hospital_id:
            hospital_path = (
                self.schema_dir
                / "hospitals"
                / hospital_id
                / "normalization_rules.yaml"
            )
            if hospital_path.exists():
                with open(hospital_path, encoding="utf-8") as f:
                    hospital_rules = yaml.safe_load(f) or {}
                rules = self._merge_normalization_rules(rules, hospital_rules)

        self._normalization_cache[hospital_id] = rules
        return rules

    def _merge_normalization_rules(
        self, base: dict[str, Any], override: dict[str, Any]
    ) -> dict[str, Any]:
        """Merge normalization rules with hospital overrides.

        Supports:
        - checkbox_format_overrides: Modify existing checkbox format definitions
        - field_normalization_additions: Add new field normalizations
        """
        result = copy.deepcopy(base)

        # Handle checkbox_format_overrides
        format_overrides = override.get("checkbox_format_overrides", {})
        if format_overrides:
            result.setdefault("checkbox_formats", {})
            for format_name, format_override in format_overrides.items():
                if format_name in result["checkbox_formats"]:
                    result["checkbox_formats"][format_name] = self._deep_merge_dict(
                        result["checkbox_formats"][format_name], format_override
                    )
                else:
                    result["checkbox_formats"][format_name] = format_override

        # Handle field_normalization_additions
        field_additions = override.get("field_normalization_additions", {})
        if field_additions:
            result.setdefault("field_normalizations", {})
            result["field_normalizations"].update(field_additions)

        # Direct overrides for other keys
        for key in override:
            if key not in (
                "checkbox_format_overrides",
                "field_normalization_additions",
                "extends",
            ):
                if key == "checkbox_formats":
                    # Full replacement of checkbox formats
                    result["checkbox_formats"] = override[key]
                elif key == "field_normalizations":
                    # Full replacement of field normalizations
                    result["field_normalizations"] = override[key]
                else:
                    result[key] = override[key]

        return result

    def get_checkbox_format(
        self, format_name: str, hospital_id: str | None = None
    ) -> dict[str, Any] | None:
        """Get a specific checkbox format definition.

        Args:
            format_name: Name of the checkbox format (e.g., 'yes_no', 'has_none')
            hospital_id: Optional hospital ID for hospital-specific overrides

        Returns:
            Dictionary with patterns, true_values, false_values
        """
        rules = self.load_normalization_rules(hospital_id)
        return rules.get("checkbox_formats", {}).get(format_name)

    def get_field_normalization(
        self, field_name: str, hospital_id: str | None = None
    ) -> dict[str, Any] | None:
        """Get normalization config for a specific field.

        Args:
            field_name: Name of the field
            hospital_id: Optional hospital ID for hospital-specific overrides

        Returns:
            Dictionary with normalization type and options
        """
        rules = self.load_normalization_rules(hospital_id)
        return rules.get("field_normalizations", {}).get(field_name)

    def build_llm_extraction_prompt(
        self, entity_type: str, hospital_id: str | None = None
    ) -> str:
        """Build an LLM extraction prompt from entity schema.

        This generates a structured prompt for Claude to extract data
        from Word documents based on the entity schema definition.

        Args:
            entity_type: Name of the entity schema
            hospital_id: Optional hospital ID for hospital-specific overrides

        Returns:
            Formatted prompt string for LLM extraction
        """
        schema = self.load_schema(entity_type, hospital_id)

        field_descriptions = []
        for f in schema.fields:
            desc = f"- {f.name} ({f.type}): {f.description or f.i18n_key}"
            if f.validation.required:
                desc += " [REQUIRED]"
            if f.enum_options:
                options = ", ".join(opt["key"] for opt in f.enum_options)
                desc += f" Options: [{options}]"
            field_descriptions.append(desc)

        prompt = f"""Extract the following fields from the document for entity type "{schema.name}":

{chr(10).join(field_descriptions)}

Return the extracted data as a JSON object with field names as keys.
For checkbox fields, return true/false based on whether they are checked.
For enum fields, return the matching option key.
For multi_enum fields, return a list of matching option keys.
If a field cannot be found, return null.
"""
        return prompt

    def clear_cache(self) -> None:
        """Clear all cached schemas and normalization rules."""
        self._cache.clear()
        self._normalization_cache.clear()


@lru_cache
def get_schema_service() -> SchemaService:
    """Get cached schema service instance."""
    return SchemaService()

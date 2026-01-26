"""
Normalizer service that reads normalization rules from YAML configuration.

Replaces the ~500 lines of hardcoded normalization logic from the PoC's
llm_extractor.py with a configurable, data-driven approach.

Supports hospital-specific rule overrides via hierarchical configuration:
- Base rules in entity_schemas/base/normalization_rules.yaml (required)
- Hospital overrides in entity_schemas/hospitals/{hospital_id}/normalization_rules.yaml (optional)
"""

import copy
import logging

logger = logging.getLogger(__name__)
import re
from dataclasses import dataclass, field
from fnmatch import fnmatch
from pathlib import Path
from typing import Any

import yaml


@dataclass
class NormalizationResult:
    """Result of normalizing a field value."""

    normalized_value: Any
    original_value: str
    normalization_type: str
    details: dict[str, Any] = field(default_factory=dict)


class NormalizerService:
    """Service for normalizing extracted field values based on YAML rules.

    Supports hospital-specific rule overrides with inheritance:
    1. Load base rules from entity_schemas/base/normalization_rules.yaml
    2. If hospital_id provided, merge overrides from entity_schemas/hospitals/{hospital_id}/
    3. Deep merge: base + override (hospital values win on conflicts)
    """

    def __init__(
        self,
        schema_dir: Path | None = None,
        hospital_id: str | None = None,
    ):
        """Initialize the normalizer service.

        Args:
            schema_dir: Directory containing entity_schemas (with base/ and hospitals/).
                       Defaults to src/entity_schemas/.
            hospital_id: Optional hospital ID for hospital-specific rule overrides.
        """
        if schema_dir is None:
            schema_dir = Path(__file__).parent.parent / "entity_schemas"
        self.schema_dir = schema_dir
        self.hospital_id = hospital_id
        self._rules: dict[str, Any] = {}
        self._cache: dict[str | None, dict[str, Any]] = {}
        self._load_rules()

    def _load_rules(self) -> None:
        """Load normalization rules with hospital inheritance."""
        # Check cache first
        if self.hospital_id in self._cache:
            self._rules = self._cache[self.hospital_id]
            return

        # Load base rules (required)
        base_path = self.schema_dir / "base" / "normalization_rules.yaml"
        if base_path.exists():
            with open(base_path, encoding="utf-8") as f:
                self._rules = yaml.safe_load(f) or {}
        else:
            self._rules = {}

        # Load and merge hospital-specific overrides if hospital_id provided
        if self.hospital_id:
            hospital_path = (
                self.schema_dir / "hospitals" / self.hospital_id / "normalization_rules.yaml"
            )
            if hospital_path.exists():
                with open(hospital_path, encoding="utf-8") as f:
                    hospital_rules = yaml.safe_load(f) or {}
                self._rules = self._merge_rules(self._rules, hospital_rules)

        # Cache the merged rules
        self._cache[self.hospital_id] = self._rules

    def _merge_rules(
        self, base: dict[str, Any], override: dict[str, Any]
    ) -> dict[str, Any]:
        """Merge base rules with hospital overrides.

        Supports:
        - checkbox_format_overrides: Modify existing checkbox format definitions
        - field_normalization_additions: Add new field normalizations
        - Direct key overrides for other sections
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

        # Handle multi_checkbox_format_overrides
        multi_format_overrides = override.get("multi_checkbox_format_overrides", {})
        if multi_format_overrides:
            result.setdefault("multi_checkbox_formats", {})
            for format_name, format_override in multi_format_overrides.items():
                if format_name in result["multi_checkbox_formats"]:
                    result["multi_checkbox_formats"][format_name] = self._deep_merge_dict(
                        result["multi_checkbox_formats"][format_name], format_override
                    )
                else:
                    result["multi_checkbox_formats"][format_name] = format_override

        # Handle field_normalization_additions
        field_additions = override.get("field_normalization_additions", {})
        if field_additions:
            result.setdefault("field_normalizations", {})
            result["field_normalizations"].update(field_additions)

        # Handle field_normalization_overrides (modify existing field rules)
        field_overrides = override.get("field_normalization_overrides", {})
        if field_overrides:
            result.setdefault("field_normalizations", {})
            for field_name, field_override in field_overrides.items():
                if field_name in result["field_normalizations"]:
                    result["field_normalizations"][field_name] = self._deep_merge_dict(
                        result["field_normalizations"][field_name], field_override
                    )
                else:
                    result["field_normalizations"][field_name] = field_override

        # Handle character_mapping_additions
        char_additions = override.get("character_mapping_additions", {})
        if char_additions:
            result.setdefault("character_mappings", {})
            result["character_mappings"].update(char_additions)

        # Handle wildcard_rule_additions
        wildcard_additions = override.get("wildcard_rule_additions", [])
        if wildcard_additions:
            result.setdefault("wildcard_rules", [])
            result["wildcard_rules"].extend(wildcard_additions)

        # Direct overrides for other keys (full replacement)
        for key in override:
            if key not in (
                "checkbox_format_overrides",
                "multi_checkbox_format_overrides",
                "field_normalization_additions",
                "field_normalization_overrides",
                "character_mapping_additions",
                "wildcard_rule_additions",
                "extends",
            ):
                if key == "checkbox_formats" and "checkbox_format_overrides" not in override:
                    # Full replacement of checkbox formats
                    result["checkbox_formats"] = override[key]
                elif key == "field_normalizations" and "field_normalization_additions" not in override:
                    # Full replacement of field normalizations
                    result["field_normalizations"] = override[key]
                elif key == "character_mappings" and "character_mapping_additions" not in override:
                    # Full replacement of character mappings
                    result["character_mappings"] = override[key]
                else:
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

    def clear_cache(self) -> None:
        """Clear the rules cache."""
        self._cache.clear()

    @property
    def character_mappings(self) -> dict[str, str]:
        """Get character mappings for checkbox normalization."""
        mappings = self._rules.get("character_mappings", {})
        result = {}
        for key, value in mappings.items():
            if "→" in value:
                parts = value.split("→")
                result[parts[0]] = parts[1]
            else:
                result[key] = value
        return result

    @property
    def checkbox_formats(self) -> dict[str, Any]:
        """Get checkbox format definitions."""
        return self._rules.get("checkbox_formats", {})

    @property
    def multi_checkbox_formats(self) -> dict[str, Any]:
        """Get multi-checkbox format definitions."""
        return self._rules.get("multi_checkbox_formats", {})

    @property
    def field_normalizations(self) -> dict[str, Any]:
        """Get field-specific normalization rules."""
        return self._rules.get("field_normalizations", {})

    @property
    def wildcard_rules(self) -> list[dict[str, Any]]:
        """Get wildcard pattern rules."""
        return self._rules.get("wildcard_rules", [])

    def get_field_rule(self, field_name: str) -> dict[str, Any] | None:
        """Get the normalization rule for a specific field.

        First checks exact match in field_normalizations, then checks
        wildcard_rules for pattern matches.

        Args:
            field_name: The field name to look up.

        Returns:
            The normalization rule dict, or None if no rule found.
        """
        # Check exact match first
        if field_name in self.field_normalizations:
            return self.field_normalizations[field_name]

        # Check wildcard patterns
        for rule in self.wildcard_rules:
            pattern = rule.get("pattern", "")
            if fnmatch(field_name, pattern):
                return rule

        return None

    def apply_character_mappings(self, text: str) -> str:
        """Apply character mappings to normalize checkbox markers.

        Args:
            text: The text to normalize.

        Returns:
            Text with checkbox markers normalized.
        """
        result = text
        for old_char, new_char in self.character_mappings.items():
            result = result.replace(old_char, new_char)
        return result

    def normalize_yes_no(
        self, value: str, spacing: int = 0
    ) -> NormalizationResult:
        """Normalize a yes/no (是/否) checkbox value.

        Args:
            value: The raw value to normalize.
            spacing: Expected spacing between checkboxes.

        Returns:
            NormalizationResult with boolean value.
        """
        format_def = self.checkbox_formats.get("yes_no", {})
        true_values = format_def.get("true_values", ["☑是", "√是", "是"])
        false_values = format_def.get("false_values", ["☑否", "√否", "否"])

        # Apply character mappings first
        normalized_text = self.apply_character_mappings(value)

        # Check for true values (only match if explicitly checked with ☑ or √)
        for tv in true_values:
            # Only count as "true" if it has a checked marker
            if ("☑" in tv or "√" in tv) and tv in normalized_text:
                return NormalizationResult(
                    normalized_value=True,
                    original_value=value,
                    normalization_type="yes_no",
                    details={"matched": tv, "spacing": spacing},
                )

        # Check for false values (explicitly selected with ☑ or √)
        for fv in false_values:
            if ("☑" in fv or "√" in fv) and fv in normalized_text:
                return NormalizationResult(
                    normalized_value=False,
                    original_value=value,
                    normalization_type="yes_no",
                    details={"matched": fv, "spacing": spacing},
                )

        # Default to None if neither clearly selected
        return NormalizationResult(
            normalized_value=None,
            original_value=value,
            normalization_type="yes_no",
            details={"matched": None, "spacing": spacing},
        )

    def normalize_none_has(
        self, value: str, has_detail: bool = False
    ) -> NormalizationResult:
        """Normalize a none/has (无/有) checkbox value.

        Args:
            value: The raw value to normalize.
            has_detail: Whether to extract additional detail text.

        Returns:
            NormalizationResult with value and optional detail.
        """
        format_def = self.checkbox_formats.get("none_has", {})
        none_values = format_def.get("none_values", ["☑无", "√无", "无"])
        has_values = format_def.get("has_values", ["☑有", "√有", "有"])

        normalized_text = self.apply_character_mappings(value)

        details = {"has_detail": has_detail}

        # Check for "none" values
        for nv in none_values:
            if ("☑" in nv or "√" in nv) and nv in normalized_text:
                return NormalizationResult(
                    normalized_value="none",
                    original_value=value,
                    normalization_type="none_has",
                    details={**details, "matched": nv},
                )

        # Check for "has" values
        for hv in has_values:
            if ("☑" in hv or "√" in hv) and hv in normalized_text:
                detail_text = None
                if has_detail:
                    # Try to extract text after the checkbox
                    # Pattern: after ☑有 or √有, get the remaining text
                    match = re.search(r"[☑√]有[：:]?\s*(.+?)(?:\s*[☐☑]|$)", normalized_text)
                    if match:
                        detail_text = match.group(1).strip()
                return NormalizationResult(
                    normalized_value="has",
                    original_value=value,
                    normalization_type="none_has",
                    details={**details, "matched": hv, "detail": detail_text},
                )

        return NormalizationResult(
            normalized_value=None,
            original_value=value,
            normalization_type="none_has",
            details=details,
        )

    def normalize_stone_clearance(self, value: str) -> NormalizationResult:
        """Normalize stone clearance status.

        Args:
            value: The raw value to normalize.

        Returns:
            NormalizationResult with clearance status and optional size.
        """
        format_def = self.checkbox_formats.get("stone_clearance", {})
        no_residual_keywords = format_def.get("no_residual_keywords", ["无残留", "无残石"])
        residual_keywords = format_def.get("residual_keywords", ["残留", "残石"])
        size_pattern = format_def.get("size_pattern", r"(\d+)\s*mm")

        normalized_text = self.apply_character_mappings(value)

        # Check for no residual stone
        for keyword in no_residual_keywords:
            if f"☑{keyword}" in normalized_text or f"√{keyword}" in normalized_text:
                return NormalizationResult(
                    normalized_value="no_residual",
                    original_value=value,
                    normalization_type="stone_clearance",
                    details={"matched": keyword},
                )

        # Check for residual stone
        for keyword in residual_keywords:
            if f"☑{keyword}" in normalized_text or f"√{keyword}" in normalized_text:
                # Extract size if present
                size = None
                if format_def.get("extract_size"):
                    size_match = re.search(size_pattern, normalized_text)
                    if size_match:
                        size = int(size_match.group(1))
                return NormalizationResult(
                    normalized_value="residual",
                    original_value=value,
                    normalization_type="stone_clearance",
                    details={"matched": keyword, "size_mm": size},
                )

        return NormalizationResult(
            normalized_value=None,
            original_value=value,
            normalization_type="stone_clearance",
            details={},
        )

    def normalize_scale(self, value: str, format_name: str = "urine_color_scale") -> NormalizationResult:
        """Normalize a scale value (e.g., urine color 1-8).

        Args:
            value: The raw value to normalize.
            format_name: The scale format name from config.

        Returns:
            NormalizationResult with integer scale value.
        """
        format_def = self.checkbox_formats.get(format_name, {})
        min_value = format_def.get("min_value", 1)
        max_value = format_def.get("max_value", 8)
        selected_char = format_def.get("selected_char", "☑")

        normalized_text = self.apply_character_mappings(value)

        # Count position of selected checkbox
        # The scale is represented as a series of checkboxes where only one is selected
        checkboxes = []
        current_pos = 0
        for char in normalized_text:
            if char in ("☐", "☑", "√"):
                is_selected = char in ("☑", "√")
                checkboxes.append({"pos": current_pos, "selected": is_selected})
                current_pos += 1

        # Find the selected position
        selected_pos = None
        for i, cb in enumerate(checkboxes):
            if cb["selected"]:
                selected_pos = i + min_value  # Convert 0-indexed to scale value
                break

        if selected_pos is not None and min_value <= selected_pos <= max_value:
            return NormalizationResult(
                normalized_value=selected_pos,
                original_value=value,
                normalization_type="scale",
                details={"format": format_name, "min": min_value, "max": max_value},
            )

        # Try to extract a number directly
        match = re.search(r"(\d+)", value)
        if match:
            num = int(match.group(1))
            if min_value <= num <= max_value:
                return NormalizationResult(
                    normalized_value=num,
                    original_value=value,
                    normalization_type="scale",
                    details={"format": format_name, "extracted_number": True},
                )

        return NormalizationResult(
            normalized_value=None,
            original_value=value,
            normalization_type="scale",
            details={"format": format_name},
        )

    def normalize_multi_checkbox(
        self, value: str, format_name: str
    ) -> NormalizationResult:
        """Normalize a multi-checkbox field (e.g., medical history, stone location).

        Args:
            value: The raw value to normalize.
            format_name: The multi-checkbox format name from config.

        Returns:
            NormalizationResult with list of selected options.
        """
        format_def = self.multi_checkbox_formats.get(format_name, {})
        options = format_def.get("options", [])

        normalized_text = self.apply_character_mappings(value)

        selected = []
        details_map = {}

        for option in options:
            key = option.get("key", "")
            patterns = option.get("detection_patterns", [])
            has_detail = option.get("has_detail", False)
            detail_pattern = option.get("detail_pattern")

            # Check if this option is selected
            is_selected = False
            for pattern in patterns:
                if pattern in normalized_text:
                    # Check if it's a checkbox-selected pattern (has ☑ or √)
                    if "☑" in pattern or "√" in pattern:
                        is_selected = True
                        break

            if is_selected:
                selected.append(key)

                # Extract detail if applicable
                if has_detail and detail_pattern:
                    match = re.search(detail_pattern, normalized_text)
                    if match:
                        details_map[f"{key}_detail"] = match.group(1).strip()

        return NormalizationResult(
            normalized_value=selected,
            original_value=value,
            normalization_type="multi_checkbox",
            details={"format": format_name, **details_map},
        )

    def normalize_extract_components(
        self, value: str, separator: str = "+", exclude_words: list[str] | None = None
    ) -> NormalizationResult:
        """Extract components from a value (e.g., stone composition).

        Args:
            value: The raw value to normalize.
            separator: The separator between components.
            exclude_words: Words to exclude from extraction.

        Returns:
            NormalizationResult with list of components.
        """
        if exclude_words is None:
            exclude_words = []

        # Remove checkbox markers
        cleaned = self.apply_character_mappings(value)
        cleaned = re.sub(r"[☐☑√]", "", cleaned)

        # Split by separator
        parts = cleaned.split(separator)

        # Clean and filter
        components = []
        for part in parts:
            part = part.strip()
            if part and part not in exclude_words:
                components.append(part)

        return NormalizationResult(
            normalized_value=components,
            original_value=value,
            normalization_type="extract_components",
            details={"separator": separator},
        )

    def normalize_extract_text(self, value: str) -> NormalizationResult:
        """Extract plain text, removing checkbox markers.

        Args:
            value: The raw value to normalize.

        Returns:
            NormalizationResult with cleaned text.
        """
        # Remove checkbox markers
        cleaned = re.sub(r"[☐☑√]", "", value)
        # Normalize whitespace
        cleaned = " ".join(cleaned.split())

        return NormalizationResult(
            normalized_value=cleaned.strip(),
            original_value=value,
            normalization_type="extract_text",
            details={},
        )

    def normalize_field(self, field_name: str, value: str) -> NormalizationResult:
        """Normalize a field value based on its configured rules.

        This is the main entry point for field normalization. It looks up
        the field's normalization rule and applies the appropriate method.

        Args:
            field_name: The name of the field to normalize.
            value: The raw value to normalize.

        Returns:
            NormalizationResult with the normalized value.
        """
        if not value or not isinstance(value, str):
            return NormalizationResult(
                normalized_value=value,
                original_value=str(value) if value else "",
                normalization_type="passthrough",
                details={"reason": "empty_or_non_string"},
            )

        rule = self.get_field_rule(field_name)

        if rule is None:
            # No rule found, return as-is
            return NormalizationResult(
                normalized_value=value,
                original_value=value,
                normalization_type="passthrough",
                details={"reason": "no_rule_found"},
            )

        norm_type = rule.get("type", "plain_text")

        if norm_type == "yes_no":
            spacing = rule.get("spacing", 0)
            return self.normalize_yes_no(value, spacing)

        elif norm_type == "none_has":
            has_detail = rule.get("has_detail", False)
            return self.normalize_none_has(value, has_detail)

        elif norm_type == "checkbox":
            format_name = rule.get("format", "")
            if format_name == "stone_clearance":
                return self.normalize_stone_clearance(value)
            # Handle other checkbox formats
            return self.normalize_yes_no(value)

        elif norm_type == "scale":
            format_name = rule.get("format", "urine_color_scale")
            return self.normalize_scale(value, format_name)

        elif norm_type == "multi_checkbox":
            format_name = rule.get("format", "")
            return self.normalize_multi_checkbox(value, format_name)

        elif norm_type == "extract_components":
            separator = rule.get("separator", "+")
            exclude_words = rule.get("exclude_words", [])
            return self.normalize_extract_components(value, separator, exclude_words)

        elif norm_type == "extract_text":
            return self.normalize_extract_text(value)

        elif norm_type == "plain_text":
            # Return as-is but mark as processed
            return NormalizationResult(
                normalized_value=value,
                original_value=value,
                normalization_type="plain_text",
                details={},
            )

        else:
            # Unknown type, return as-is
            return NormalizationResult(
                normalized_value=value,
                original_value=value,
                normalization_type="unknown",
                details={"configured_type": norm_type},
            )

    def normalize_extracted_data(
        self, data: dict[str, Any], entity_type: str | None = None
    ) -> dict[str, Any]:
        """Normalize all fields in an extracted data dictionary.

        Args:
            data: Dictionary of field_name -> raw_value.
            entity_type: Optional entity type for context (not currently used).

        Returns:
            Dictionary of field_name -> normalized_value.
        """
        result = {}
        for field_name, value in data.items():
            if isinstance(value, str):
                norm_result = self.normalize_field(field_name, value)
                result[field_name] = norm_result.normalized_value
            else:
                # Non-string values pass through
                result[field_name] = value
        return result


# Cached instances by hospital_id
_normalizer_services: dict[str | None, NormalizerService] = {}


def get_normalizer_service(hospital_id: str | None = None) -> NormalizerService:
    """Get or create a cached NormalizerService instance.

    Args:
        hospital_id: Optional hospital ID for hospital-specific rules.

    Returns:
        NormalizerService instance (cached per hospital_id).
    """
    global _normalizer_services
    if hospital_id not in _normalizer_services:
        _normalizer_services[hospital_id] = NormalizerService(hospital_id=hospital_id)
    return _normalizer_services[hospital_id]

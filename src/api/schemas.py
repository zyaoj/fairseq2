"""Entity Schema API router for schema introspection."""

from typing import Any

from fastapi import APIRouter, HTTPException, status

from src.schemas.entity_schema import (
    EntitySchemaListItem,
    EntitySchemaListResponse,
    EntitySchemaResponse,
    NormalizationRulesResponse,
)
from src.services.schema_service import get_schema_service

import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/schemas", tags=["schemas"])


@router.get("", response_model=EntitySchemaListResponse)
def list_schemas() -> EntitySchemaListResponse:
    """List all available entity schemas.

    Returns:
        List of entity schema summaries with basic info.
    """
    schema_service = get_schema_service()
    schemas = schema_service.get_all_schemas()

    items = []
    for entity_type, schema in schemas.items():
        items.append(
            EntitySchemaListItem(
                entity_type=entity_type,
                display_name_key=schema.display_name_key,
                description=schema.description,
                field_count=len(schema.fields),
                has_stages=schema.stages is not None and len(schema.stages) > 0,
            )
        )

    return EntitySchemaListResponse(schemas=items)


@router.get("/normalization-rules", response_model=NormalizationRulesResponse)
def get_normalization_rules() -> dict[str, Any]:
    """Get normalization rules configuration.

    Returns:
        Normalization rules including checkbox formats, field rules, and wildcard patterns.
    """
    schema_service = get_schema_service()
    rules = schema_service.load_normalization_rules()

    # Process character mappings for display
    character_mappings = {}
    raw_mappings = rules.get("character_mappings", {})
    for key, value in raw_mappings.items():
        if "→" in value:
            parts = value.split("→")
            character_mappings[parts[0]] = parts[1]
        else:
            character_mappings[key] = value

    return {
        "character_mappings": character_mappings,
        "checkbox_formats": rules.get("checkbox_formats", {}),
        "multi_checkbox_formats": rules.get("multi_checkbox_formats", {}),
        "field_normalizations": rules.get("field_normalizations", {}),
        "wildcard_rules": rules.get("wildcard_rules", []),
    }


@router.get("/{entity_type}", response_model=EntitySchemaResponse)
def get_schema(entity_type: str) -> EntitySchemaResponse:
    """Get the full schema definition for a specific entity type.

    Args:
        entity_type: Entity type identifier (e.g., 'basic_info', 'surgery_indicator')

    Returns:
        Complete entity schema with all fields, validations, and stages.

    Raises:
        HTTPException: If entity type is not found.
    """
    schema_service = get_schema_service()

    try:
        schema = schema_service.load_schema(entity_type)
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entity schema not found: {entity_type}",
        )

    # Convert stages if present
    stages = None
    if schema.stages:
        stages = [
            {
                "number": s.get("number"),
                "name": s.get("name"),
                "i18n_key": s.get("i18n_key"),
                "days_after_surgery": s.get("days_after_surgery"),
            }
            for s in schema.stages
        ]

    # Convert fields
    fields = []
    for f in schema.fields:
        field_data = {
            "name": f.name,
            "type": f.type,
            "i18n_key": f.i18n_key,
            "description": f.description,
            "validation": {
                "required": f.validation.required,
                "min_value": f.validation.min_value,
                "max_value": f.validation.max_value,
                "min_length": f.validation.min_length,
                "max_length": f.validation.max_length,
                "pattern": f.validation.pattern,
            },
            "default": f.default,
            "stage_specific": f.stage_specific,
        }

        if f.enum_options:
            field_data["enum_options"] = [
                {"key": opt.get("key", ""), "i18n_key": opt.get("i18n_key", "")}
                for opt in f.enum_options
            ]

        fields.append(field_data)

    return EntitySchemaResponse(
        entity_type=entity_type,
        display_name_key=schema.display_name_key,
        description=schema.description,
        fields=fields,
        stages=stages,
    )


@router.get("/{entity_type}/prompt")
def get_extraction_prompt(entity_type: str) -> dict[str, str]:
    """Get the LLM extraction prompt for a specific entity type.

    This endpoint generates the prompt that would be sent to the LLM
    for extracting structured data from documents.

    Args:
        entity_type: Entity type identifier

    Returns:
        Dictionary with the generated prompt.

    Raises:
        HTTPException: If entity type is not found.
    """
    schema_service = get_schema_service()

    try:
        prompt = schema_service.build_llm_extraction_prompt(entity_type)
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entity schema not found: {entity_type}",
        )

    return {"entity_type": entity_type, "prompt": prompt}

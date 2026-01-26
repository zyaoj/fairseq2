"""Services module exports."""

from src.services.normalizer import (
    NormalizationResult,
    NormalizerService,
    get_normalizer_service,
)
from src.services.schema_service import (
    EntityField,
    EntitySchema,
    SchemaService,
    get_schema_service,
)
from src.services.template_service import (
    TemplateNotFoundError,
    TemplateService,
    get_template_service,
)
from src.services.word_generator import (
    WordGeneratorError,
    WordGeneratorService,
    get_word_generator_service,
)
from src.services.word_extractor import (
    WordExtractorError,
    WordExtractorService,
    get_word_extractor_service,
)

__all__ = [
    # Schema service
    "EntityField",
    "EntitySchema",
    "SchemaService",
    "get_schema_service",
    # Normalizer service
    "NormalizationResult",
    "NormalizerService",
    "get_normalizer_service",
    # Template service
    "TemplateNotFoundError",
    "TemplateService",
    "get_template_service",
    # Word generator service
    "WordGeneratorError",
    "WordGeneratorService",
    "get_word_generator_service",
    # Word extractor service
    "WordExtractorError",
    "WordExtractorService",
    "get_word_extractor_service",
]

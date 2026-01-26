"""FastAPI application entry point."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.auth import router as auth_router
from src.api.health import router as health_router
from src.api.documents import router as documents_router
from src.api.followups import router as followups_router
from src.api.i18n import router as i18n_router
from src.api.patients import router as patients_router
from src.api.scheduling import router as scheduling_router
from src.api.schemas import router as schemas_router
from src.api.search import router as search_router
from src.api.terminology import router as terminology_router
from src.api.upload import router as upload_router
from src.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

app = FastAPI(
    title="Urology Data Platform",
    description="Multi-modal patient data platform for urology",
    version="0.1.0",
    debug=settings.debug,
)

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health_router)  # Health checks at root level
app.include_router(auth_router, prefix="/api")
app.include_router(patients_router, prefix="/api")
app.include_router(followups_router, prefix="/api")
app.include_router(scheduling_router, prefix="/api")
app.include_router(documents_router, prefix="/api")
app.include_router(upload_router, prefix="/api")
app.include_router(i18n_router, prefix="/api")
app.include_router(schemas_router, prefix="/api")
app.include_router(search_router, prefix="/api")
app.include_router(terminology_router, prefix="/api")

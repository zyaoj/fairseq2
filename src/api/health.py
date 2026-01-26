"""Health check API router with service connectivity verification."""

import logging
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.core.config import get_settings
from src.core.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


class ServiceStatus(BaseModel):
    """Status of an individual service."""

    name: str
    status: str = Field(..., description="Service status: healthy, degraded, or unhealthy")
    message: str | None = Field(None, description="Additional status information")


class HealthResponse(BaseModel):
    """Health check response with service statuses."""

    status: str = Field(..., description="Overall status: healthy, degraded, or unhealthy")
    services: list[ServiceStatus] = Field(default_factory=list)


def check_database(db: Session) -> ServiceStatus:
    """Check PostgreSQL database connectivity."""
    try:
        db.execute(text("SELECT 1"))
        return ServiceStatus(name="postgresql", status="healthy")
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return ServiceStatus(
            name="postgresql",
            status="unhealthy",
            message=str(e),
        )


def check_milvus() -> ServiceStatus:
    """Check Milvus vector database connectivity."""
    settings = get_settings()
    try:
        from pymilvus import connections, utility

        # Try to connect to Milvus
        connections.connect(
            alias="health_check",
            host=settings.milvus_host,
            port=settings.milvus_port,
            timeout=5,
        )
        # Check if we can list collections
        utility.list_collections(using="health_check")
        connections.disconnect(alias="health_check")
        return ServiceStatus(name="milvus", status="healthy")
    except ImportError:
        return ServiceStatus(
            name="milvus",
            status="degraded",
            message="pymilvus not installed",
        )
    except Exception as e:
        logger.warning(f"Milvus health check failed: {e}")
        return ServiceStatus(
            name="milvus",
            status="unhealthy",
            message=str(e),
        )


def check_minio() -> ServiceStatus:
    """Check MinIO object storage connectivity."""
    settings = get_settings()
    try:
        from minio import Minio

        client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
        # Check if we can list buckets (lightweight operation)
        client.list_buckets()
        return ServiceStatus(name="minio", status="healthy")
    except ImportError:
        return ServiceStatus(
            name="minio",
            status="degraded",
            message="minio not installed",
        )
    except Exception as e:
        logger.warning(f"MinIO health check failed: {e}")
        return ServiceStatus(
            name="minio",
            status="unhealthy",
            message=str(e),
        )


def determine_overall_status(services: list[ServiceStatus]) -> str:
    """Determine overall health status based on service statuses.

    Rules:
    - If all services are healthy: overall healthy
    - If any required service (postgresql) is unhealthy: overall unhealthy
    - If only optional services (milvus, minio) are unhealthy: overall degraded
    """
    required_services = {"postgresql"}
    has_unhealthy_required = False
    has_any_issue = False

    for service in services:
        if service.status != "healthy":
            has_any_issue = True
            if service.name in required_services:
                has_unhealthy_required = True

    if has_unhealthy_required:
        return "unhealthy"
    elif has_any_issue:
        return "degraded"
    return "healthy"


@router.get("/health", response_model=HealthResponse)
def health_check(
    db: Session = Depends(get_db),
) -> HealthResponse:
    """Comprehensive health check endpoint.

    Checks connectivity to:
    - PostgreSQL (required)
    - Milvus vector database (optional)
    - MinIO object storage (optional)

    Returns:
        HealthResponse with overall status and individual service statuses
    """
    services: list[ServiceStatus] = []

    # Check required services
    services.append(check_database(db))

    # Check optional services
    services.append(check_milvus())
    services.append(check_minio())

    overall_status = determine_overall_status(services)

    if overall_status == "unhealthy":
        logger.error(f"Health check failed: {[s.model_dump() for s in services]}")
    elif overall_status == "degraded":
        logger.warning(f"Health check degraded: {[s.model_dump() for s in services]}")

    return HealthResponse(status=overall_status, services=services)


@router.get("/health/live")
def liveness_check() -> dict[str, str]:
    """Kubernetes liveness probe endpoint.

    Returns 200 if the application process is running.
    Does not check external dependencies.
    """
    return {"status": "alive"}


@router.get("/health/ready", response_model=HealthResponse)
def readiness_check(
    db: Session = Depends(get_db),
) -> HealthResponse:
    """Kubernetes readiness probe endpoint.

    Returns 200 only if the application is ready to receive traffic.
    Checks database connectivity (required for serving requests).
    """
    services = [check_database(db)]
    overall_status = determine_overall_status(services)

    return HealthResponse(status=overall_status, services=services)

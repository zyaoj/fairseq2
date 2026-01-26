"""Semantic search API router."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.api.deps import get_current_active_user
from src.core.database import get_db
from src.models.patient import Patient
from src.models.user import User
from src.services.embedding import (
    MilvusService,
    OpenAIEmbeddingProvider,
    SearchResult,
    get_milvus_service,
)

import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/search", tags=["search"])


def _verify_patient_access(
    patient_id: str,
    current_user: User,
    db: Session,
) -> None:
    """Verify the current user has access to the specified patient.

    Authorization rules:
    - Admin users have access to all patients
    - Non-admin users can only access patients from their hospital

    Args:
        patient_id: The patient UUID to check access for
        current_user: The authenticated user
        db: Database session

    Raises:
        HTTPException: 404 if patient not found, 403 if access denied
    """
    # Look up the patient
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )

    # Admin users have access to all patients
    if current_user.role == "admin":
        return

    # Non-admin users can only access patients from their hospital
    if current_user.hospital_id and patient.hospital_id != current_user.hospital_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: patient belongs to a different hospital",
        )


class SearchRequest(BaseModel):
    """Request body for semantic search."""

    query: str = Field(..., min_length=1, max_length=1000, description="Search query text")
    limit: int = Field(default=10, ge=1, le=100, description="Maximum number of results")
    patient_id: str | None = Field(default=None, description="Optional patient ID to filter by")


class SearchResultResponse(BaseModel):
    """Search result response."""

    lab_result_id: str
    patient_id: str
    score: float = Field(..., description="Similarity score (higher is more similar)")
    content_preview: str = Field(..., description="Preview of matched content")


class SearchResponse(BaseModel):
    """Response for search endpoint."""

    results: list[SearchResultResponse]
    query: str
    total_results: int


class SearchStatsResponse(BaseModel):
    """Response for search stats endpoint."""

    collection_name: str | None = Field(None, description="Name of the vector collection")
    indexed_documents: int = Field(0, description="Number of indexed documents")
    status: str = Field(..., description="Collection status (ready, loading, or unavailable)")


def _get_accessible_patient_ids(
    db: Session,
    current_user: User,
) -> set[str] | None:
    """Get set of patient IDs the user can access, or None if admin (all access).

    Args:
        db: Database session
        current_user: The authenticated user

    Returns:
        Set of patient_id strings the user can access, or None for admin (unrestricted)
    """
    # Admin users have access to all patients
    if current_user.role == "admin":
        return None

    # Non-admin users can only access patients from their hospital
    if current_user.hospital_id:
        patients = db.query(Patient.id).filter(
            Patient.hospital_id == current_user.hospital_id
        ).all()
        return {str(p.id) for p in patients}

    # User has no hospital_id - return empty set (no access)
    return set()


@router.post("", response_model=SearchResponse)
def semantic_search(
    request: SearchRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> SearchResponse:
    """Perform semantic search across lab results.

    This endpoint uses vector similarity search to find lab results
    that are semantically similar to the query text.

    Results are scoped to patients accessible by the current user:
    - Admin users can search across all patients
    - Non-admin users only see results from their hospital's patients

    Args:
        request: Search request with query and parameters
        db: Database session
        current_user: Current authenticated user

    Returns:
        Search results with similarity scores

    Raises:
        HTTPException: If search service is unavailable
    """
    # Verify patient access if patient_id filter is provided
    if request.patient_id:
        _verify_patient_access(request.patient_id, current_user, db)

    # Get accessible patient IDs for post-filtering (None = admin, all access)
    accessible_patient_ids = _get_accessible_patient_ids(db, current_user)

    try:
        # Initialize embedding provider and Milvus service
        embedding_provider = OpenAIEmbeddingProvider()
        milvus_service = get_milvus_service(embedding_provider=embedding_provider)

        # Request more results than limit to account for post-filtering
        # when user has limited access
        search_limit = request.limit
        if accessible_patient_ids is not None and not request.patient_id:
            # Request extra results since some may be filtered out
            search_limit = min(request.limit * 3, 100)

        # Perform search
        results: list[SearchResult] = milvus_service.search(
            query_text=request.query,
            limit=search_limit,
            patient_id=request.patient_id,
        )

        # Post-filter results by hospital scoping (if not admin)
        if accessible_patient_ids is not None:
            results = [r for r in results if r.patient_id in accessible_patient_ids]

        # Trim to requested limit after filtering
        results = results[:request.limit]

        # Convert to response format
        response_results = [
            SearchResultResponse(
                lab_result_id=r.lab_result_id,
                patient_id=r.patient_id,
                score=r.score,
                content_preview=r.content_preview,
            )
            for r in results
        ]

        return SearchResponse(
            results=response_results,
            query=request.query,
            total_results=len(response_results),
        )

    except ValueError as e:
        # Invalid UUID format
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except ImportError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OpenAI package not available for embedding generation",
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Search service unavailable: {str(e)}",
        ) from e


@router.get("", response_model=SearchResponse)
def semantic_search_get(
    query: Annotated[str, Query(min_length=1, max_length=1000, description="Search query text")],
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    limit: Annotated[int, Query(ge=1, le=100, description="Maximum results")] = 10,
    patient_id: Annotated[str | None, Query(description="Filter by patient ID")] = None,
) -> SearchResponse:
    """Perform semantic search across lab results (GET endpoint).

    This is a convenience GET endpoint for semantic search.
    Uses query parameters instead of request body.

    Args:
        query: Search query text
        db: Database session
        current_user: Current authenticated user
        limit: Maximum number of results
        patient_id: Optional patient ID to filter by

    Returns:
        Search results with similarity scores
    """
    request = SearchRequest(query=query, limit=limit, patient_id=patient_id)
    return semantic_search(request, db, current_user)


@router.get("/stats", response_model=SearchStatsResponse)
def get_search_stats(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> SearchStatsResponse:
    """Get statistics about the vector search collection.

    Args:
        db: Database session
        current_user: Current authenticated user

    Returns:
        Collection statistics including number of indexed documents
    """
    try:
        milvus_service = get_milvus_service()
        stats = milvus_service.get_collection_stats()
        return SearchStatsResponse(
            collection_name=stats["name"],
            indexed_documents=stats["num_entities"],
            status="ready" if stats["loaded"] else "loading",
        )
    except Exception as e:
        return SearchStatsResponse(
            collection_name=None,
            indexed_documents=0,
            status=f"unavailable: {str(e)}",
        )

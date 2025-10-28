# Copyright 2024 Heinrich Krupp
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Search endpoints for the HTTP interface.

Provides semantic search, tag-based search, and time-based recall functionality.
"""

import logging
from typing import List, Optional, Dict, Any, TYPE_CHECKING
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field

from ...storage.base import MemoryStorage
from ...models.memory import Memory, MemoryQueryResult
from ...config import OAUTH_ENABLED
from ..dependencies import get_storage
from .memories import MemoryResponse, memory_to_response
from ..sse import sse_manager, create_search_completed_event

# Constants
_TIME_SEARCH_CANDIDATE_POOL_SIZE = 100  # Number of candidates to retrieve for time filtering (reduced for performance)

# OAuth authentication imports (conditional)
if OAUTH_ENABLED or TYPE_CHECKING:
    from ..oauth.middleware import require_read_access, AuthenticationResult
else:
    # Provide type stubs when OAuth is disabled
    AuthenticationResult = None
    require_read_access = None

router = APIRouter()
logger = logging.getLogger(__name__)


# Request Models
class SemanticSearchRequest(BaseModel):
    """Request model for semantic similarity search."""
    query: str = Field(..., description="The search query for semantic similarity")
    n_results: int = Field(default=10, ge=1, le=100, description="Maximum number of results to return")
    similarity_threshold: Optional[float] = Field(None, ge=0.0, le=1.0, description="Minimum similarity score")


class TagSearchRequest(BaseModel):
    """Request model for tag-based search."""
    tags: List[str] = Field(..., description="List of tags to search for (ANY match)")
    match_all: bool = Field(default=False, description="If true, memory must have ALL tags; if false, ANY tag")


class TimeSearchRequest(BaseModel):
    """Request model for time-based search."""
    query: str = Field(..., description="Natural language time query (e.g., 'last week', 'yesterday')")
    n_results: int = Field(default=10, ge=1, le=100, description="Maximum number of results to return")
    semantic_query: Optional[str] = Field(None, description="Optional semantic query for relevance filtering within time range")


# Response Models
class SearchResult(BaseModel):
    """Individual search result with similarity score."""
    memory: MemoryResponse
    similarity_score: Optional[float] = Field(None, description="Similarity score (0-1, higher is more similar)")
    relevance_reason: Optional[str] = Field(None, description="Why this result was included")


class SearchResponse(BaseModel):
    """Response model for search operations."""
    results: List[SearchResult]
    total_found: int
    query: str
    search_type: str
    processing_time_ms: Optional[float] = None


def memory_query_result_to_search_result(query_result: MemoryQueryResult) -> SearchResult:
    """Convert MemoryQueryResult to SearchResult format."""
    return SearchResult(
        memory=memory_to_response(query_result.memory),
        similarity_score=query_result.relevance_score,
        relevance_reason=f"Semantic similarity: {query_result.relevance_score:.3f}" if query_result.relevance_score else None
    )


def memory_to_search_result(memory: Memory, reason: str = None) -> SearchResult:
    """Convert Memory to SearchResult format."""
    return SearchResult(
        memory=memory_to_response(memory),
        similarity_score=None,
        relevance_reason=reason
    )


@router.post("/search", response_model=SearchResponse, tags=["search"])
async def semantic_search(
    request: SemanticSearchRequest,
    storage: MemoryStorage = Depends(get_storage),
    user: AuthenticationResult = Depends(require_read_access) if OAUTH_ENABLED else None
):
    """
    Perform semantic similarity search on memory content.
    
    Uses vector embeddings to find memories with similar meaning to the query,
    even if they don't share exact keywords.
    """
    try:
        from ...services.memory_service import MemoryService
        
        # Use shared service for consistent logic
        memory_service = MemoryService(storage)
        result = await memory_service.retrieve_memory(
            query=request.query,
            n_results=request.n_results,
            similarity_threshold=request.similarity_threshold
        )
        
        # Convert service result to API response format
        search_results = []
        for item in result["results"]:
            # Convert memory response to MemoryResponse format
            memory_response = MemoryResponse(
                content=item["memory"]["content"],
                content_hash=item["memory"]["content_hash"],
                tags=item["memory"]["tags"],
                memory_type=item["memory"]["memory_type"],
                created_at=item["memory"]["created_at"],
                created_at_iso=None,  # Not provided by service
                updated_at=None,      # Not provided by service
                updated_at_iso=None,  # Not provided by service
                metadata=item["memory"]["metadata"]
            )
            
            search_result = SearchResult(
                memory=memory_response,
                similarity_score=item["similarity_score"],
                relevance_reason=item["relevance_reason"]
            )
            search_results.append(search_result)
        
        # Broadcast SSE event for search completion
        try:
            event = create_search_completed_event(
                query=result["query"],
                search_type=result["search_type"],
                results_count=result["total_found"],
                processing_time_ms=result["processing_time_ms"]
            )
            await sse_manager.broadcast_event(event)
        except Exception as e:
            logger.warning(f"Failed to broadcast search_completed event: {e}")
        
        return SearchResponse(
            results=search_results,
            total_found=result["total_found"],
            query=result["query"],
            search_type=result["search_type"],
            processing_time_ms=result["processing_time_ms"]
        )
        
    except Exception as e:
        logger.error(f"Semantic search failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Search operation failed. Please try again.")


@router.post("/search/by-tag", response_model=SearchResponse, tags=["search"])
async def tag_search(
    request: TagSearchRequest,
    storage: MemoryStorage = Depends(get_storage),
    user: AuthenticationResult = Depends(require_read_access) if OAUTH_ENABLED else None
):
    """
    Search memories by tags.
    
    Finds memories that contain any of the specified tags (OR search) or
    all of the specified tags (AND search) based on the match_all parameter.
    """
    try:
        from ...services.memory_service import MemoryService
        
        # Use shared service for consistent logic
        memory_service = MemoryService(storage)
        result = await memory_service.search_by_tag(
            tags=request.tags,
            match_all=request.match_all
        )
        
        # Check for errors from service
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        # Convert service result to API response format
        search_results = []
        for item in result["results"]:
            # Convert memory response to MemoryResponse format
            memory_response = MemoryResponse(
                content=item["memory"]["content"],
                content_hash=item["memory"]["content_hash"],
                tags=item["memory"]["tags"],
                memory_type=item["memory"]["memory_type"],
                created_at=item["memory"]["created_at"],
                created_at_iso=None,  # Not provided by service
                updated_at=None,      # Not provided by service
                updated_at_iso=None,  # Not provided by service
                metadata=item["memory"]["metadata"]
            )
            
            search_result = SearchResult(
                memory=memory_response,
                similarity_score=item["similarity_score"],
                relevance_reason=item["relevance_reason"]
            )
            search_results.append(search_result)
        
        # Broadcast SSE event for search completion
        try:
            event = create_search_completed_event(
                query=result["query"],
                search_type=result["search_type"],
                results_count=result["total_found"],
                processing_time_ms=result["processing_time_ms"]
            )
            await sse_manager.broadcast_event(event)
        except Exception as e:
            logger.warning(f"Failed to broadcast search_completed event: {e}")
        
        return SearchResponse(
            results=search_results,
            total_found=result["total_found"],
            query=result["query"],
            search_type=result["search_type"],
            processing_time_ms=result["processing_time_ms"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tag search failed: {str(e)}")


@router.post("/search/by-time", response_model=SearchResponse, tags=["search"])
async def time_search(
    request: TimeSearchRequest,
    storage: MemoryStorage = Depends(get_storage),
    user: AuthenticationResult = Depends(require_read_access) if OAUTH_ENABLED else None
):
    """
    Search memories by time-based queries.
    
    Supports natural language time expressions like 'yesterday', 'last week',
    'this month', etc. Uses shared MemoryService for consistent logic.
    """
    try:
        from ...services.memory_service import MemoryService
        
        # Use shared service for consistent logic
        memory_service = MemoryService(storage)
        result = await memory_service.search_by_time(
            query=request.query,
            n_results=request.n_results
        )
        
        # Check for errors from service
        if "error" in result:
            raise HTTPException(
                status_code=400,
                detail=result["error"]
            )

        # Return the result from memory service
        return SearchResponse(
            results=result["results"],
            total_found=result["total_found"],
            query=result["query"],
            search_type=result["search_type"],
            processing_time_ms=result["processing_time_ms"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Time search failed: {str(e)}")


@router.get("/search/similar/{content_hash}", response_model=SearchResponse, tags=["search"])
async def find_similar(
    content_hash: str,
    n_results: int = Query(default=10, ge=1, le=100, description="Number of similar memories to find"),
    storage: MemoryStorage = Depends(get_storage),
    user: AuthenticationResult = Depends(require_read_access) if OAUTH_ENABLED else None
):
    """
    Find memories similar to a specific memory identified by its content hash.
    
    Uses the content of the specified memory as a search query to find
    semantically similar memories.
    """
    try:
        from ...services.memory_service import MemoryService
        
        # Use shared service for consistent logic
        memory_service = MemoryService(storage)
        result = await memory_service.search_similar(
            content_hash=content_hash,
            limit=n_results
        )
        
        # Check for service-level errors
        if not result.get("success", True):
            raise HTTPException(
                status_code=404 if "not found" in result.get("message", "").lower() else 500,
                detail=result.get("message", "Similar search failed")
            )
        
        # Convert service result to API response format
        search_results = []
        for item in result["results"]:
            # Convert memory response to MemoryResponse format
            memory_response = MemoryResponse(
                content=item["memory"]["content"],
                content_hash=item["memory"]["content_hash"],
                tags=item["memory"]["tags"],
                memory_type=item["memory"]["memory_type"],
                created_at=item["memory"]["created_at"],
                created_at_iso=item["memory"]["created_at_iso"],
                updated_at=item["memory"]["updated_at"],
                updated_at_iso=item["memory"]["updated_at_iso"],
                metadata=item["memory"]["metadata"]
            )
            
            search_result = SearchResult(
                memory=memory_response,
                similarity_score=item["similarity_score"],
                relevance_reason=item["relevance_reason"]
            )
            search_results.append(search_result)
        
        return SearchResponse(
            results=search_results,
            total_found=result["total_found"],
            query=result["query"],
            search_type=result["search_type"],
            processing_time_ms=result["processing_time_ms"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Similar search failed: {str(e)}")


# Helper functions for time parsing
def parse_time_query(query: str) -> Optional[Dict[str, Any]]:
    """
    Parse natural language time queries into time ranges.

    This is a basic implementation - can be enhanced with more sophisticated
    natural language processing later.
    """
    query_lower = query.lower().strip()
    now = datetime.now(timezone.utc)
    
    # Define time mappings
    if query_lower in ['yesterday']:
        start = now - timedelta(days=1)
        end = now
        return {'start': start.replace(hour=0, minute=0, second=0), 'end': start.replace(hour=23, minute=59, second=59)}
    
    elif query_lower in ['today']:
        return {'start': now.replace(hour=0, minute=0, second=0), 'end': now}
    
    elif query_lower in ['last week', 'past week']:
        start = now - timedelta(weeks=1)
        return {'start': start, 'end': now}
    
    elif query_lower in ['last month', 'past month']:
        start = now - timedelta(days=30)
        return {'start': start, 'end': now}
    
    elif query_lower in ['this week']:
        # Start of current week (Monday)
        days_since_monday = now.weekday()
        start = now - timedelta(days=days_since_monday)
        return {'start': start.replace(hour=0, minute=0, second=0), 'end': now}
    
    elif query_lower in ['this month']:
        start = now.replace(day=1, hour=0, minute=0, second=0)
        return {'start': start, 'end': now}

    elif query_lower in ['last 2 weeks', 'past 2 weeks', 'last-2-weeks']:
        start = now - timedelta(weeks=2)
        return {'start': start, 'end': now}

    # Add more time expressions as needed
    return None


def is_within_time_range(memory_time: datetime, time_filter: Dict[str, Any]) -> bool:
    """Check if a memory's timestamp falls within the specified time range."""
    start_time = time_filter.get('start')
    end_time = time_filter.get('end')
    
    if start_time and end_time:
        return start_time <= memory_time <= end_time
    elif start_time:
        return memory_time >= start_time
    elif end_time:
        return memory_time <= end_time
    
    return True
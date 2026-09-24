from fastapi import APIRouter, Query, HTTPException, status
from typing import List, Optional
import logging
from pydantic import BaseModel
from app.services.embeddings import semantic_search

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Search"])


class SearchResultItem(BaseModel):
    id: str
    meeting_id: str
    meeting_title: Optional[str] = None
    chunk_type: str
    content: str
    similarity: float


class SearchResponse(BaseModel):
    query: str
    total_results: int
    results: List[SearchResultItem]


@router.get("/search", response_model=SearchResponse, status_code=status.HTTP_200_OK)
def search_meetings(
    q: str = Query(..., min_length=1, description="Natural language search query"),
    limit: int = Query(10, ge=1, le=50, description="Max matching excerpts to return"),
    threshold: float = Query(0.35, ge=0.0, le=1.0, description="Minimum cosine similarity threshold"),
    user_id: Optional[str] = Query(None, description="Optional filter for specific user's meetings"),
):
    """
    Semantic search across past meetings:
    1. Embeds query text into 768-dim vector using Gemini API.
    2. Runs HNSW cosine similarity search via pgvector match_meeting_embeddings RPC.
    3. Returns ranked excerpts across summaries, decisions, action items, and transcripts.
    """
    query_str = q.strip()
    if not query_str:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query parameter 'q' must not be empty."
        )

    try:
        matches = semantic_search(
            query=query_str,
            match_threshold=threshold,
            match_count=limit,
            filter_user_id=user_id,
        )
        return {
            "query": query_str,
            "total_results": len(matches),
            "results": matches,
        }
    except Exception as e:
        logger.error(f"Semantic search failed for query '{query_str}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Semantic search error: {str(e)}"
        )

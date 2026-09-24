from fastapi import APIRouter, HTTPException, status, Query
from typing import List, Optional, Dict, Any
import logging
import time
import uuid
from pydantic import BaseModel, Field

from app.core.config import settings
from app.services.supabase_client import get_supabase_admin
from app.services.embeddings import semantic_search
from google import genai

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["Chat"])


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, description="Natural language question to ask about meetings")
    meeting_id: Optional[str] = Field(None, description="Optional meeting ID to scope the Q&A context to a specific meeting")
    user_id: Optional[str] = Field(None, description="User ID for meeting ownership filter and chat history persistence")


class CitedChunk(BaseModel):
    id: str
    meeting_id: str
    meeting_title: Optional[str] = None
    chunk_type: str
    content: str
    similarity: float


class AskResponse(BaseModel):
    question: str
    answer: str
    meeting_id: Optional[str] = None
    cited_chunks: List[CitedChunk]
    message_id: Optional[str] = None


class ChatMessageItem(BaseModel):
    id: str
    user_id: str
    meeting_id: Optional[str] = None
    question: str
    answer: str
    cited_chunks: List[Dict[str, Any]]
    created_at: str


def generate_rag_answer(question: str, context_chunks: List[Dict[str, Any]]) -> str:
    """
    Constructs a grounded RAG prompt for Gemini using retrieved meeting chunks.
    Instructs the model to answer strictly based on the provided context.
    """
    gemini_key = settings.GEMINI_API_KEY.strip() if settings.GEMINI_API_KEY else ""
    if not gemini_key or gemini_key.startswith("your-"):
        raise ValueError("Valid GEMINI_API_KEY is required for chat Q&A generation.")

    client = genai.Client(api_key=gemini_key)

    # Format context passages clearly with source metadata
    if not context_chunks:
        return "I do not have enough information from your meetings or lectures to answer this question. No matching content was found in the recorded discussions."

    context_snippets = []
    for idx, chunk in enumerate(context_chunks, 1):
        m_title = chunk.get("meeting_title") or "Unknown Meeting"
        c_type = chunk.get("chunk_type") or "transcript"
        content = chunk.get("content", "").strip()
        context_snippets.append(
            f"[Source {idx}] Meeting: \"{m_title}\" | Type: {c_type}\n{content}"
        )

    context_text = "\n\n---\n\n".join(context_snippets)

    system_instruction = (
        "You are an AI assistant answering questions about recorded meetings, lectures, and discussions. "
        "Answer the user's question using ONLY the provided context sources below. "
        "Strict Guidelines:\n"
        "1. Be accurate, concise, and direct.\n"
        "2. When stating facts, refer naturally to the meeting or source context (e.g. 'According to the discussion in [Meeting Title]...').\n"
        "3. If the provided context does NOT contain enough information to answer the question with confidence, "
        "explicitly state: 'Based on the provided meeting records, there is not enough information to answer this question.' Do NOT guess or extrapolate beyond what is stated in the context.\n"
        "4. Do not invent dates, names, or decisions that are not explicitly mentioned in the context."
    )

    user_prompt = f"""Context Sources from Meetings:
{context_text}

Question:
{question}

Answer:"""

    candidate_models = ["gemini-3.5-flash-lite", "gemini-3.6-flash", "gemini-3.7-flash"]
    raw_answer = ""

    for model_name in candidate_models:
        for attempt in range(2):
            try:
                logger.info(f"Generating RAG answer using {model_name}...")
                resp = client.models.generate_content(
                    model=model_name,
                    contents=f"{system_instruction}\n\n{user_prompt}",
                )
                if resp.text and resp.text.strip():
                    raw_answer = resp.text.strip()
                    break
            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                    logger.warning(f"Quota 429 on {model_name}. Trying alternative model...")
                    break
                elif "503" in err_str or "UNAVAILABLE" in err_str or "10060" in err_str:
                    time.sleep(2.0)
                    continue
                else:
                    logger.warning(f"Model {model_name} error: {err_str[:80]}")
                    break
        if raw_answer:
            break

    if not raw_answer:
        raise RuntimeError("Failed to generate an answer from Gemini models. Please try again in a few moments.")

    return raw_answer


@router.post("/ask", response_model=AskResponse, status_code=status.HTTP_200_OK)
def ask_meeting_question(request: AskRequest):
    """
    RAG-powered Q&A endpoint:
    1. Embeds question using Gemini 768-dim embedding model.
    2. Calls match_meeting_embeddings RPC to retrieve top 5-8 relevant chunks.
       (Filtered to meeting_id if provided, otherwise across all user's meetings).
    3. Prompts Gemini with retrieved chunks labeled with meeting title & chunk type.
    4. Enforces grounded answers (explicitly says if not enough information is present).
    5. Saves question, answer, and cited chunk/meeting IDs to chat_messages table.
    6. Returns answer along with source citations.
    """
    question_clean = request.question.strip()
    if not question_clean:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question must not be empty."
        )

    user_id = request.user_id or settings.DEFAULT_USER_ID

    # Validate UUIDs if provided
    if request.meeting_id:
        try:
            uuid.UUID(str(request.meeting_id))
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid meeting_id format: '{request.meeting_id}'"
            )

    try:
        # Step 1 & 2: Embed and retrieve chunks via match_meeting_embeddings RPC
        # Retrieve top 8 chunks to provide rich context
        raw_matches = semantic_search(
            query=question_clean,
            match_threshold=0.30,
            match_count=8 if not request.meeting_id else 15,
            filter_user_id=user_id,
        )

        # Apply meeting_id filter if scoped
        if request.meeting_id:
            matches = [m for m in raw_matches if str(m.get("meeting_id")) == str(request.meeting_id)]
            # If threshold was too strict for scoped meeting, pull top chunks for that meeting
            if not matches and raw_matches:
                matches = [m for m in raw_matches if str(m.get("meeting_id")) == str(request.meeting_id)][:6]
        else:
            matches = raw_matches[:8]

        # Step 3 & 4: Construct prompt & generate grounded answer with Gemini
        answer = generate_rag_answer(question_clean, matches)

        # Step 5: Format citations and save to chat_messages table
        cited_chunks_data = [
            {
                "id": str(m.get("id")),
                "meeting_id": str(m.get("meeting_id")),
                "meeting_title": m.get("meeting_title"),
                "chunk_type": m.get("chunk_type"),
                "content": m.get("content"),
                "similarity": round(float(m.get("similarity", 0.0)), 4),
            }
            for m in matches
        ]

        supabase = get_supabase_admin()
        message_id = None
        try:
            insert_data = {
                "user_id": user_id,
                "meeting_id": request.meeting_id if request.meeting_id else None,
                "question": question_clean,
                "answer": answer,
                "cited_chunks": cited_chunks_data,
            }
            res = supabase.table("chat_messages").insert(insert_data).execute()
            if res.data and len(res.data) > 0:
                message_id = res.data[0].get("id")
        except Exception as db_err:
            logger.warning(f"Could not save chat history to chat_messages: {db_err}")

        # Step 6: Return answer and citations
        return {
            "question": question_clean,
            "answer": answer,
            "meeting_id": request.meeting_id,
            "cited_chunks": cited_chunks_data,
            "message_id": message_id,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to process meeting question: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat generation error: {str(e)}"
        )


@router.get("/history", response_model=List[ChatMessageItem], status_code=status.HTTP_200_OK)
def get_chat_history(
    meeting_id: Optional[str] = Query(None, description="Filter history by meeting ID"),
    user_id: Optional[str] = Query(None, description="User ID"),
    limit: int = Query(20, ge=1, le=100, description="Max history items to retrieve"),
):
    """
    Fetches chat history log for the user or specific meeting.
    """
    active_user_id = user_id or settings.DEFAULT_USER_ID
    supabase = get_supabase_admin()

    try:
        query = supabase.table("chat_messages").select("*").eq("user_id", active_user_id)
        if meeting_id:
            query = query.eq("meeting_id", meeting_id)
        res = query.order("created_at", desc=True).limit(limit).execute()
        return res.data or []
    except Exception as e:
        logger.error(f"Failed to fetch chat history: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch chat history: {str(e)}"
        )


import logging
from typing import List, Dict, Any, Optional
from google import genai
from google.genai import types
from app.core.config import settings
from app.services.supabase_client import get_supabase_admin

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIM = 768


def get_gemini_client() -> genai.Client:
    api_key = settings.GEMINI_API_KEY.strip() if settings.GEMINI_API_KEY else ""
    if not api_key or api_key.startswith("your-"):
        raise ValueError("GEMINI_API_KEY is not configured with a valid API key.")
    return genai.Client(api_key=api_key)


import time

def generate_embedding_vectors(texts: List[str]) -> List[List[float]]:
    """
    Generates 768-dimensional normalized embeddings for a list of texts using Gemini API.
    Handles batching, rate limits, and exponential backoff to stay within API quota.
    """
    if not texts:
        return []

    client = get_gemini_client()
    embeddings: List[List[float]] = []
    
    # Process in batches of 25 texts
    BATCH_SIZE = 25
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i:i + BATCH_SIZE]
        clean_batch = [t.strip() if t and t.strip() else "meeting excerpt" for t in batch]
        
        # Retry with backoff for 429/503
        max_retries = 5
        success = False
        for attempt in range(max_retries):
            try:
                resp = client.models.embed_content(
                    model=EMBEDDING_MODEL,
                    contents=clean_batch,
                    config=types.EmbedContentConfig(output_dimensionality=EMBEDDING_DIM)
                )
                for emb in resp.embeddings:
                    embeddings.append(emb.values)
                success = True
                break
            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "quota" in err_str.lower():
                    # Parse retry delay if provided, else exponential backoff
                    retry_sec = 10.0 * (attempt + 1)
                    if "retry in " in err_str:
                        try:
                            sec_part = err_str.split("retry in ")[1].split("s")[0]
                            retry_sec = max(5.0, float(sec_part) + 2.0)
                        except Exception:
                            pass
                    logger.warning(f"Embedding rate limit encountered. Waiting {retry_sec:.1f}s before retry {attempt + 1}/{max_retries}...")
                    time.sleep(retry_sec)
                elif "503" in err_str or "UNAVAILABLE" in err_str:
                    time.sleep(4.0 * (attempt + 1))
                else:
                    logger.error(f"Unexpected Gemini embedding error: {e}", exc_info=True)
                    raise RuntimeError(f"Gemini embedding error: {e}")

        if not success:
            raise RuntimeError(f"Failed to generate embeddings after {max_retries} retries due to rate limits.")

        # Brief pacing delay between batches
        if i + BATCH_SIZE < len(texts):
            time.sleep(1.5)

    return embeddings


def generate_single_embedding(text: str) -> List[float]:
    """Generates 768-dimensional embedding for a single query text."""
    res = generate_embedding_vectors([text])
    if not res:
        raise ValueError("No embedding returned for query text.")
    return res[0]


def chunk_transcript_sentences(sentences: List[Dict[str, Any]], chunk_size: int = 5, overlap: int = 1) -> List[Dict[str, Any]]:
    """
    Groups consecutive transcript sentences into overlapping conversational chunks.
    Preserves context and timing boundaries.
    """
    if not sentences:
        return []

    chunks = []
    i = 0
    total = len(sentences)
    while i < total:
        group = sentences[i:min(i + chunk_size, total)]
        combined_text = " ".join(s.get("text", "").strip() for s in group if s.get("text"))
        if combined_text:
            chunks.append({
                "chunk_type": "transcript_chunk",
                "content": combined_text,
                "metadata": {
                    "start_time": group[0].get("start_time", 0.0),
                    "end_time": group[-1].get("end_time", 0.0),
                    "start_order": group[0].get("sentence_order", 0),
                    "end_order": group[-1].get("sentence_order", 0),
                    "speaker": group[0].get("speaker"),
                }
            })
        if i + chunk_size >= total:
            break
        i += (chunk_size - overlap)

    return chunks


def index_meeting_embeddings(meeting_id: str) -> Dict[str, Any]:
    """
    Creates and indexes embeddings for a meeting across its summary, decisions,
    action items, and chunked transcript:
    1. Fetches meeting summary, decisions, action items, and transcripts.
    2. Constructs discrete semantic chunks.
    3. Generates 768-dim embeddings using Gemini API.
    4. Persists chunks and vectors to public.embeddings table.
    """
    supabase = get_supabase_admin()
    logger.info(f"Indexing embeddings for meeting: {meeting_id}")

    chunks_to_index: List[Dict[str, Any]] = []

    # 1. Summary chunk
    sum_res = supabase.table("summaries").select("executive_summary, key_points").eq("meeting_id", meeting_id).execute()
    if sum_res.data:
        s_data = sum_res.data[0]
        exec_sum = s_data.get("executive_summary") or ""
        key_pts = s_data.get("key_points") or []
        summary_text = exec_sum + "\n" + "\n".join(f"- {p}" for p in key_pts)
        if summary_text.strip():
            chunks_to_index.append({
                "chunk_type": "summary",
                "content": summary_text.strip(),
                "metadata": {"type": "executive_summary"}
            })

    # 2. Key Decisions chunks
    dec_res = supabase.table("decisions").select("decision, context, decided_by").eq("meeting_id", meeting_id).execute()
    for d in dec_res.data or []:
        text = d.get("decision", "").strip()
        if d.get("context"):
            text += f" (Context: {d['context']})"
        if d.get("decided_by"):
            text += f" [Decided by: {d['decided_by']}]"
        if text:
            chunks_to_index.append({
                "chunk_type": "decision",
                "content": text,
                "metadata": {"decision": d.get("decision"), "decided_by": d.get("decided_by")}
            })

    # 3. Action Items chunks
    act_res = supabase.table("action_items").select("task, assignee, deadline, priority").eq("meeting_id", meeting_id).execute()
    for a in act_res.data or []:
        text = f"Action Item: {a.get('task')}"
        if a.get("assignee"):
            text += f" (Assignee: {a['assignee']})"
        if a.get("deadline"):
            text += f" [Due: {a['deadline']}]"
        if a.get("priority"):
            text += f" <Priority: {a['priority']}>"
        chunks_to_index.append({
            "chunk_type": "action_item",
            "content": text,
            "metadata": {"task": a.get("task"), "assignee": a.get("assignee")}
        })

    # 4. Transcript chunks (paginated fetch)
    sentences = []
    PAGE_SIZE = 1000
    current_offset = 0
    while True:
        t_res = (
            supabase.table("transcripts")
            .select("sentence_order, start_time, end_time, text, speaker")
            .eq("meeting_id", meeting_id)
            .order("sentence_order", desc=False)
            .range(current_offset, current_offset + PAGE_SIZE - 1)
            .execute()
        )
        batch = t_res.data or []
        sentences.extend(batch)
        if len(batch) < PAGE_SIZE:
            break
        current_offset += PAGE_SIZE

    # Group into chunks of 10 sentences (with 2 sentence overlap) for rich semantic context
    t_chunks = chunk_transcript_sentences(sentences, chunk_size=10, overlap=2)
    chunks_to_index.extend(t_chunks)

    if not chunks_to_index:
        logger.warning(f"No content to embed for meeting {meeting_id}.")
        return {"meeting_id": meeting_id, "indexed_chunks": 0}

    # Delete existing embeddings for meeting to ensure clean idempotency
    supabase.table("embeddings").delete().eq("meeting_id", meeting_id).execute()

    # Generate embeddings via Gemini API
    texts = [c["content"] for c in chunks_to_index]
    logger.info(f"Generating embeddings for {len(texts)} chunks of meeting {meeting_id}...")
    vectors = generate_embedding_vectors(texts)

    # Insert rows into public.embeddings
    rows_to_insert = []
    for c, vec in zip(chunks_to_index, vectors):
        rows_to_insert.append({
            "meeting_id": meeting_id,
            "chunk_type": c["chunk_type"],
            "content": c["content"],
            "metadata": c.get("metadata", {}),
            "embedding": vec,
        })

    BATCH_SIZE = 100
    for i in range(0, len(rows_to_insert), BATCH_SIZE):
        batch = rows_to_insert[i:i + BATCH_SIZE]
        supabase.table("embeddings").insert(batch).execute()

    logger.info(f"Successfully indexed {len(rows_to_insert)} embeddings for meeting {meeting_id}.")
    return {
        "meeting_id": meeting_id,
        "indexed_chunks": len(rows_to_insert),
        "chunk_types": {
            "summary": sum(1 for c in chunks_to_index if c["chunk_type"] == "summary"),
            "decision": sum(1 for c in chunks_to_index if c["chunk_type"] == "decision"),
            "action_item": sum(1 for c in chunks_to_index if c["chunk_type"] == "action_item"),
            "transcript_chunk": sum(1 for c in chunks_to_index if c["chunk_type"] == "transcript_chunk"),
        }
    }


def semantic_search(
    query: str,
    match_threshold: float = 0.35,
    match_count: int = 10,
    filter_user_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Performs semantic vector search across all indexed meetings:
    1. Embeds the user query text into a 768-dim vector.
    2. Calls the Supabase match_meeting_embeddings RPC function utilizing pgvector HNSW index.
    3. Returns ranked matching excerpts with similarity scores, meeting titles, and chunk types.
    """
    if not query or not query.strip():
        return []

    supabase = get_supabase_admin()
    query_vector = generate_single_embedding(query.strip())

    rpc_params = {
        "query_embedding": query_vector,
        "match_threshold": match_threshold,
        "match_count": match_count,
    }
    if filter_user_id:
        rpc_params["filter_user_id"] = filter_user_id

    res = supabase.rpc("match_meeting_embeddings", rpc_params).execute()
    return res.data or []

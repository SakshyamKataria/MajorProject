"""Meeting Clustering Service

Handles:
1. Extracting summary embeddings across a user's meetings.
2. Dynamic K-Means clustering with silhouette score optimization across range [2, min(8, N-1)].
3. Gemini auto-generation of concise descriptive 2-4 word labels for each cluster.
4. Persisting cluster_id and cluster_label back to public.meetings in Supabase.
5. Querying meetings grouped by cluster for UI display.
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import normalize
from google import genai
from postgrest.exceptions import APIError

from app.core.config import settings
from app.services.supabase_client import get_supabase_admin

logger = logging.getLogger(__name__)


def get_gemini_client() -> Optional[genai.Client]:
    """Initializes Gemini API client if API key is configured."""
    api_key = settings.GEMINI_API_KEY.strip()
    if not api_key or api_key.startswith("your-"):
        logger.warning("GEMINI_API_KEY is not configured. Falling back to rule-based cluster labels.")
        return None
    return genai.Client(api_key=api_key)


def fetch_user_summary_embeddings(user_id: str) -> List[Dict[str, Any]]:
    """
    Pulls summary-level embeddings (chunk_type = 'summary') for all meetings belonging to user_id.
    Maps them to meeting titles and metadata.
    """
    supabase = get_supabase_admin()

    # 1. Fetch meeting metadata for user
    m_query = (
        supabase.table("meetings")
        .select("id, title, duration_seconds, status, created_at")
    )
    if user_id:
        m_query = m_query.eq("user_id", user_id)

    meetings_resp = m_query.execute()
    meeting_meta = {m["id"]: m for m in (meetings_resp.data or [])}

    if not meeting_meta:
        logger.info(f"No meetings found for user_id={user_id}")
        return []

    meeting_ids = list(meeting_meta.keys())

    # 2. Query summary embeddings for these meetings
    query = (
        supabase.table("embeddings")
        .select("id, meeting_id, chunk_type, content, embedding")
        .eq("chunk_type", "summary")
        .in_("meeting_id", meeting_ids)
    )

    emb_resp = query.execute()
    records = emb_resp.data or []

    if not records:
        logger.info(f"No summary embeddings found for user_id={user_id}")
        return []

    meetings_data = {}
    for r in records:
        m_id = r.get("meeting_id")
        if not m_id or m_id not in meeting_meta:
            continue

        raw_emb = r.get("embedding")
        if isinstance(raw_emb, str):
            try:
                emb_vec = json.loads(raw_emb)
            except Exception:
                try:
                    emb_vec = eval(raw_emb)
                except Exception:
                    continue
        elif isinstance(raw_emb, list):
            emb_vec = raw_emb
        else:
            continue

        if m_id not in meetings_data:
            meta = meeting_meta[m_id]
            meetings_data[m_id] = {
                "id": m_id,
                "title": meta.get("title") or "Untitled Meeting",
                "duration_seconds": meta.get("duration_seconds", 0),
                "created_at": meta.get("created_at"),
                "content": r.get("content") or "",
                "embedding": np.array(emb_vec, dtype=np.float32),
            }

    return list(meetings_data.values())


def evaluate_cluster_range(
    embeddings_matrix: np.ndarray, min_k: int, max_k: int, random_state: int = 42
) -> Dict[int, Tuple[float, np.ndarray, KMeans]]:
    """Evaluates K-Means across k in [min_k, max_k], computing cosine silhouette scores."""
    scores = {}
    n_samples = embeddings_matrix.shape[0]

    for k in range(min_k, max_k + 1):
        if k >= n_samples:
            break
        kmeans = KMeans(n_clusters=k, random_state=random_state, n_init=10)
        labels = kmeans.fit_predict(embeddings_matrix)

        n_unique_labels = len(set(labels))
        if 1 < n_unique_labels < n_samples:
            score = float(silhouette_score(embeddings_matrix, labels, metric="cosine"))
            scores[k] = (score, labels, kmeans)
        else:
            scores[k] = (-1.0, labels, kmeans)

    return scores


def generate_cluster_label_with_gemini(
    cluster_meetings: List[Dict[str, Any]], gemini_client: Optional[genai.Client] = None
) -> str:
    """Uses Gemini to generate a short, descriptive 2-4 word label for a cluster of meetings."""
    if not cluster_meetings:
        return "Empty Cluster"

    first_title = cluster_meetings[0]["title"]
    default_fallback = f"{first_title} & Related" if len(cluster_meetings) > 1 else first_title

    if not gemini_client:
        return default_fallback

    # Build concise context
    lines = []
    for m in cluster_meetings:
        summary_snippet = m.get("content", "").strip().replace("\n", " ")
        if len(summary_snippet) > 220:
            summary_snippet = summary_snippet[:217] + "..."
        lines.append(f"- Title: \"{m['title']}\"\n  Summary: {summary_snippet}")

    meetings_context = "\n".join(lines)

    prompt = f"""You are an expert meeting taxonomy and categorization assistant.
Analyze the following meetings that belong to the same semantic cluster and generate a short, highly descriptive category label.

Meetings in this cluster:
{meetings_context}

Requirements:
1. Provide a short descriptive label of 2 to 4 words (e.g. "Municipal Council Meetings", "Product Marketing Operations", "Engineering Key Reviews", "Research Methodology Planning").
2. The label must capture the unifying domain, business function, or academic topic of these meetings.
3. Return ONLY the 2-4 word label. Do not include quotes, periods, bullet points, markdown formatting, or preamble text.

Cluster Label:"""

    candidate_models = ["gemini-3.5-flash-lite", "gemini-3.6-flash", "gemini-3.7-flash"]
    for model_name in candidate_models:
        for attempt in range(2):
            try:
                resp = gemini_client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                )
                if resp.text and resp.text.strip():
                    clean_label = (
                        resp.text.strip()
                        .replace('"', "")
                        .replace("'", "")
                        .replace("*", "")
                        .strip(". \n\t")
                    )
                    words = clean_label.split()
                    if len(words) > 5:
                        clean_label = " ".join(words[:4])
                    return clean_label
            except Exception as e:
                logger.warning(f"Error calling Gemini model {model_name} for cluster label: {e}")
                continue

    return default_fallback


def cluster_user_meetings(
    user_id: str,
    k: Optional[int] = None,
    min_k: int = 2,
    max_k: int = 8,
    random_state: int = 42,
) -> Dict[str, Any]:
    """
    Executes end-to-end meeting clustering for a user:
    1. Retrieves summary embeddings.
    2. Runs spherical K-Means with silhouette score optimization across range.
    3. Auto-generates descriptive 2-4 word cluster labels via Gemini.
    4. Updates public.meetings table with cluster_id and cluster_label.
    5. Returns structured response with cluster breakdown and metrics.
    """
    meetings = fetch_user_summary_embeddings(user_id)
    n_meetings = len(meetings)

    if n_meetings < 2:
        return {
            "status": "insufficient_data",
            "message": f"Need at least 2 processed meetings with summary embeddings to perform clustering (found {n_meetings}).",
            "k": 0,
            "silhouette_score": 0.0,
            "total_meetings": n_meetings,
            "clusters": [],
            "migration_needed": False,
        }

    # Normalize vectors for spherical K-Means (cosine distance)
    X = np.stack([m["embedding"] for m in meetings])
    X_norm = normalize(X, norm="l2")

    eval_min_k = max(2, min_k)
    eval_max_k = min(max_k, n_meetings - 1)

    scores = {}
    if eval_min_k <= eval_max_k:
        scores = evaluate_cluster_range(X_norm, eval_min_k, eval_max_k, random_state=random_state)

    if k is not None:
        if k < 2 or k > n_meetings:
            raise ValueError(f"Specified k={k} must be between 2 and {n_meetings}.")
        selected_k = k
        if selected_k in scores:
            selected_score, labels, _ = scores[selected_k]
        else:
            kmeans = KMeans(n_clusters=selected_k, random_state=random_state, n_init=10)
            labels = kmeans.fit_predict(X_norm)
            selected_score = (
                float(silhouette_score(X_norm, labels, metric="cosine"))
                if selected_k < n_meetings
                else 0.0
            )
    else:
        # Pick best scoring k
        best_k = eval_min_k
        best_score = -2.0
        for cand_k, (score, _, _) in scores.items():
            if score > best_score:
                best_score = score
                best_k = cand_k

        selected_k = best_k
        if best_k in scores:
            selected_score, labels, _ = scores[best_k]
        else:
            kmeans = KMeans(n_clusters=selected_k, random_state=random_state, n_init=10)
            labels = kmeans.fit_predict(X_norm)
            selected_score = 0.0

    # Group meetings by cluster
    clusters_map: Dict[int, List[Dict[str, Any]]] = {i: [] for i in range(selected_k)}
    for idx, label in enumerate(labels):
        clusters_map[label].append(meetings[idx])

    # Generate labels using Gemini
    gemini_client = get_gemini_client()
    cluster_results = []
    supabase = get_supabase_admin()
    migration_needed = False

    for cluster_idx, c_meetings in sorted(clusters_map.items()):
        label = generate_cluster_label_with_gemini(c_meetings, gemini_client)
        cluster_id = cluster_idx + 1

        meeting_summaries = []
        for m in c_meetings:
            meeting_summaries.append({
                "id": m["id"],
                "title": m["title"],
                "duration_seconds": m["duration_seconds"],
                "created_at": m["created_at"],
            })

            # Update meeting row in Supabase
            try:
                supabase.table("meetings").update({
                    "cluster_id": cluster_id,
                    "cluster_label": label,
                }).eq("id", m["id"]).execute()
            except Exception as update_err:
                err_text = str(update_err).lower()
                if "cluster_id" in err_text or "42703" in err_text:
                    migration_needed = True
                else:
                    logger.error(f"Error updating meeting {m['id']} cluster info: {update_err}")

        cluster_results.append({
            "cluster_id": cluster_id,
            "cluster_label": label,
            "meeting_count": len(c_meetings),
            "meetings": meeting_summaries,
        })

    return {
        "status": "success",
        "k": selected_k,
        "silhouette_score": round(selected_score, 4),
        "total_meetings": n_meetings,
        "clusters": cluster_results,
        "silhouette_scores_by_k": {
            str(cand_k): round(sc[0], 4) for cand_k, sc in scores.items()
        },
        "migration_needed": migration_needed,
    }


def get_meetings_grouped_by_cluster(user_id: str) -> Dict[str, Any]:
    """
    Retrieves all meetings for user_id, grouped by cluster_id and cluster_label.
    Meetings without a cluster_id appear under unclustered.
    """
    supabase = get_supabase_admin()

    try:
        query = (
            supabase.table("meetings")
            .select("id, title, duration_seconds, status, created_at, cluster_id, cluster_label")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
        )
        resp = query.execute()
        meetings = resp.data or []
    except Exception as e:
        err_text = str(e).lower()
        if "cluster_id" in err_text or "42703" in err_text:
            # Migration not yet applied in DB: fall back to query without cluster columns
            query = (
                supabase.table("meetings")
                .select("id, title, duration_seconds, status, created_at")
                .eq("user_id", user_id)
                .order("created_at", desc=True)
            )
            resp = query.execute()
            meetings = resp.data or []
            return {
                "clusters": [],
                "unclustered": meetings,
                "total_meetings": len(meetings),
                "migration_needed": True,
            }
        raise e

    clusters_dict: Dict[int, Dict[str, Any]] = {}
    unclustered: List[Dict[str, Any]] = []

    for m in meetings:
        cid = m.get("cluster_id")
        clabel = m.get("cluster_label")

        if cid is not None:
            if cid not in clusters_dict:
                clusters_dict[cid] = {
                    "cluster_id": cid,
                    "cluster_label": clabel or f"Cluster {cid}",
                    "meeting_count": 0,
                    "meetings": [],
                }
            clusters_dict[cid]["meetings"].append(m)
            clusters_dict[cid]["meeting_count"] += 1
        else:
            unclustered.append(m)

    sorted_clusters = [clusters_dict[cid] for cid in sorted(clusters_dict.keys())]

    return {
        "clusters": sorted_clusters,
        "unclustered": unclustered,
        "total_meetings": len(meetings),
        "migration_needed": False,
    }

"""Standalone Meeting Clustering & Auto-Labeling Script

1. Pulls summary-level embeddings from Supabase pgvector embeddings table (chunk_type = 'summary').
2. Evaluates K-Means clustering across a range of k values using cosine silhouette scores.
3. Automatically selects the optimal k (or accepts a CLI override).
4. Uses Gemini to generate a short descriptive label (2-4 words) for each cluster.
5. Prints the final mapping: cluster label -> list of meeting titles in that cluster.
"""

import os
import sys
import json
import argparse
import numpy as np
from pathlib import Path
from dotenv import load_dotenv

# Reconfigure stdout for utf-8 on Windows consoles if needed
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Ensure backend root is on sys.path
backend_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_root))

env_path = backend_root / ".env"
load_dotenv(dotenv_path=env_path)

from supabase import create_client
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import normalize
from google import genai


def get_supabase_client():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        print("Error: SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY missing from environment.", file=sys.stderr)
        sys.exit(1)
    return create_client(url, key)


def get_gemini_client():
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key or api_key.startswith("your-"):
        print("Warning: GEMINI_API_KEY missing or invalid in environment. Labeling will fall back to heuristics.", file=sys.stderr)
        return None
    return genai.Client(api_key=api_key)


def fetch_summary_embeddings(client, user_id=None):
    """
    Pulls summary-level embeddings (chunk_type = 'summary') and maps them
    to meeting titles and metadata.
    """
    query = client.table("embeddings").select("id, meeting_id, chunk_type, content, embedding").eq("chunk_type", "summary")
    if user_id:
        query = query.eq("user_id", user_id)
    
    resp = query.execute()
    records = resp.data or []
    
    if not records:
        print("No summary embeddings found in the database.", file=sys.stderr)
        return []

    # Get distinct meeting IDs
    meeting_ids = list(set(r["meeting_id"] for r in records if r.get("meeting_id")))
    
    # Query meeting titles
    meetings_resp = client.table("meetings").select("id, title, duration_seconds, created_at").in_("id", meeting_ids).execute()
    meeting_meta = {m["id"]: m for m in (meetings_resp.data or [])}

    # Deduplicate in case there are multiple summary chunks per meeting
    meetings_data = {}
    for r in records:
        m_id = r.get("meeting_id")
        if not m_id or m_id not in meeting_meta:
            continue
        
        # Parse embedding vector
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
            meetings_data[m_id] = {
                "meeting_id": m_id,
                "title": meeting_meta[m_id].get("title") or "Untitled Meeting",
                "content": r.get("content") or "",
                "embedding": np.array(emb_vec, dtype=np.float32),
            }

    return list(meetings_data.values())


def evaluate_clusters(embeddings_matrix, min_k, max_k, random_state=42):
    """
    Computes K-Means and silhouette scores for each k from min_k to max_k.
    """
    scores = {}
    n_samples = embeddings_matrix.shape[0]

    for k in range(min_k, max_k + 1):
        if k >= n_samples:
            break
        kmeans = KMeans(n_clusters=k, random_state=random_state, n_init=10)
        labels = kmeans.fit_predict(embeddings_matrix)
        
        n_unique_labels = len(set(labels))
        if 1 < n_unique_labels < n_samples:
            score = silhouette_score(embeddings_matrix, labels, metric="cosine")
            scores[k] = (score, labels, kmeans)
        else:
            scores[k] = (-1.0, labels, kmeans)

    return scores


def generate_cluster_label(cluster_meetings, gemini_client=None):
    """
    Uses Gemini to generate a short, descriptive 2-4 word label for a cluster of meetings.
    """
    if not cluster_meetings:
        return "Empty Cluster"

    if not gemini_client:
        first_title = cluster_meetings[0]["title"]
        return f"{first_title} & Related" if len(cluster_meetings) > 1 else first_title

    # Assemble concise context of meetings in this cluster
    lines = []
    for m in cluster_meetings:
        summary_snippet = m.get("content", "").strip().replace("\n", " ")
        if len(summary_snippet) > 220:
            summary_snippet = summary_snippet[:217] + "..."
        lines.append(f"- Title: \"{m['title']}\"\n  Summary: {summary_snippet}")
    
    meetings_context = "\n".join(lines)

    prompt = f"""You are an expert taxonomy and meeting categorization assistant.
Analyze the following meetings that belong to the same semantic cluster and generate a short, highly descriptive category label.

Meetings in this cluster:
{meetings_context}

Requirements:
1. Provide a short descriptive label of 2 to 4 words (e.g., "Council Budget Meetings", "Research Coordination", "Engineering & Product Operations", "Facility Odor Mitigation").
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
                    clean_label = resp.text.strip().replace('"', '').replace("'", "").replace("*", "").strip(". \n\t")
                    words = clean_label.split()
                    if len(words) > 5:
                        clean_label = " ".join(words[:4])
                    return clean_label
            except Exception:
                continue

    return f"{cluster_meetings[0]['title']} Cluster"


def main():
    parser = argparse.ArgumentParser(description="Cluster meetings based on summary embeddings and auto-generate labels with Gemini.")
    parser.add_argument("--k", type=int, default=None, help="Explicit number of clusters to use (overrides automatic selection).")
    parser.add_argument("--min-k", type=int, default=2, help="Minimum number of clusters to evaluate (default: 2).")
    parser.add_argument("--max-k", type=int, default=8, help="Maximum number of clusters to evaluate (default: 8).")
    parser.add_argument("--user-id", type=str, default=None, help="Optional user_id filter.")
    parser.add_argument("--random-state", type=int, default=42, help="Random state seed for reproducibility.")
    args = parser.parse_args()

    print("================================================================")
    print("      MEETING INTELLIGENCE CLUSTERING & LABELING ENGINE         ")
    print("================================================================\n")

    client = get_supabase_client()
    gemini_client = get_gemini_client()

    print("Fetching summary embeddings from Supabase...")
    meetings = fetch_summary_embeddings(client, user_id=args.user_id)

    num_meetings = len(meetings)
    print(f"Retrieved {num_meetings} meetings with summary-level embeddings.\n")

    if num_meetings < 2:
        print(f"Error: Need at least 2 meetings with summary embeddings to perform clustering (found {num_meetings}).")
        return

    # Prepare embedding matrix
    X = np.stack([m["embedding"] for m in meetings])
    X_norm = normalize(X, norm="l2")

    # Determine range of k
    min_k = max(2, args.min_k)
    max_k = min(args.max_k, num_meetings - 1)

    if min_k > max_k:
        if num_meetings == 2:
            print("With exactly 2 meetings, only k=2 is possible (silhouette score is not defined for k=N).")
            selected_k = 2
            kmeans = KMeans(n_clusters=2, random_state=args.random_state, n_init=10)
            labels = kmeans.fit_predict(X_norm)
            selected_score = 0.0
            scores = {2: (selected_score, labels, kmeans)}
        else:
            print(f"Error: Invalid k range: min_k ({min_k}) > max_k ({max_k}).")
            return
    else:
        print(f"Evaluating silhouette scores for k in range [{min_k}, {max_k}]...")
        scores = evaluate_clusters(X_norm, min_k, max_k, random_state=args.random_state)
        
        print("\n----------------------------------------------------------------")
        print(f" {'k':<5} | {'Silhouette Score (Cosine)':<26} | {'Status':<15}")
        print("----------------------------------------------------------------")
        
        best_k = min_k
        best_score = -2.0
        
        for k, (score, _, _) in scores.items():
            if score > best_score:
                best_score = score
                best_k = k
            score_str = f"{score:+.4f}" if score != -1.0 else "N/A"
            status = "Optimal Candidate" if score == best_score and score > 0 else ""
            print(f" {k:<5} | {score_str:<26} | {status}")
        print("----------------------------------------------------------------\n")

        if args.k is not None:
            if args.k < 2 or args.k > num_meetings:
                print(f"Error: Specified --k={args.k} is invalid for {num_meetings} meetings (must be between 2 and {num_meetings}).")
                return
            selected_k = args.k
            print(f">> User override applied: Using k={selected_k}")
            if selected_k in scores:
                selected_score, labels, kmeans = scores[selected_k]
            else:
                kmeans = KMeans(n_clusters=selected_k, random_state=args.random_state, n_init=10)
                labels = kmeans.fit_predict(X_norm)
                selected_score = silhouette_score(X_norm, labels, metric="cosine") if selected_k < num_meetings else 0.0
        else:
            selected_k = best_k
            selected_score, labels, kmeans = scores[best_k]
            print(f">> Automatically selected best k={selected_k} (Silhouette Score: {selected_score:+.4f})\n")

    # Group meetings by cluster
    clusters = {i: [] for i in range(selected_k)}
    for idx, label in enumerate(labels):
        clusters[label].append(meetings[idx])

    # Auto-generate labels with Gemini
    print("Generating short descriptive cluster labels using Gemini...")
    cluster_labels = {}
    for cluster_id, cluster_meetings in sorted(clusters.items()):
        label = generate_cluster_label(cluster_meetings, gemini_client)
        cluster_labels[cluster_id] = label
        print(f"  Cluster {cluster_id + 1}: \"{label}\"")

    print("\n================================================================")
    print(f"          DETAILED CLUSTER BREAKDOWN (k = {selected_k})        ")
    print("================================================================\n")

    for cluster_id, cluster_meetings in sorted(clusters.items()):
        label = cluster_labels[cluster_id]
        print(f"Cluster {cluster_id + 1}: {label} ({len(cluster_meetings)} meeting{'s' if len(cluster_meetings) != 1 else ''})")
        print("-" * 65)
        for m in cluster_meetings:
            summary_snippet = m["content"].strip().replace("\n", " ")
            if len(summary_snippet) > 130:
                summary_snippet = summary_snippet[:127] + "..."
            print(f"  * {m['title']}")
            print(f"    ID: {m['meeting_id']}")
            print(f"    Summary: {summary_snippet}\n")

    print("================================================================")
    print("           FINAL RESULT: CLUSTER LABEL -> MEETING TITLES        ")
    print("================================================================\n")

    for cluster_id, cluster_meetings in sorted(clusters.items()):
        label = cluster_labels[cluster_id]
        titles_formatted = ", ".join(f'"{m["title"]}"' for m in cluster_meetings)
        print(f"* {label} -> [{titles_formatted}]")

    print("\nClustering & labeling execution complete.")


if __name__ == "__main__":
    main()

import os
import sys
import json
import re
import time
import logging
from typing import List, Dict, Any, Tuple
import joblib

from app.core.config import settings
from app.services.supabase_client import get_supabase_admin

logger = logging.getLogger(__name__)

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))

# Potential model locations saved by train_classifier.py
PIPELINE_PATH = os.path.join(BACKEND_DIR, "app", "ml", "classifier_pipeline.joblib")
MODEL_PATH = os.path.join(BACKEND_DIR, "models", "sentence_classifier.joblib")
VEC_PATH = os.path.join(BACKEND_DIR, "models", "tfidf_vectorizer.joblib")

_classifier_pipeline = None


def load_classifier():
    """
    Loads and caches the trained TF-IDF + Logistic Regression pipeline.
    """
    global _classifier_pipeline
    if _classifier_pipeline is not None:
        return _classifier_pipeline

    if os.path.exists(PIPELINE_PATH):
        logger.info(f"Loading classifier pipeline from {PIPELINE_PATH}...")
        _classifier_pipeline = joblib.load(PIPELINE_PATH)
        return _classifier_pipeline

    if os.path.exists(MODEL_PATH) and os.path.exists(VEC_PATH):
        logger.info("Loading classifier and vectorizer from models directory...")
        from sklearn.pipeline import Pipeline
        vec = joblib.load(VEC_PATH)
        clf = joblib.load(MODEL_PATH)
        _classifier_pipeline = Pipeline([("tfidf", vec), ("clf", clf)])
        return _classifier_pipeline

    raise FileNotFoundError("Trained classifier model not found. Run train_classifier.py first.")


def classify_transcript_sentences(sentences: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Takes transcript rows from the database:
    [{'id': ..., 'sentence_order': ..., 'text': ...}]
    Computes classifier_label and classifier_confidence for each sentence.
    Returns the enriched list.
    """
    if not sentences:
        return []

    pipeline = load_classifier()
    texts = [s["text"] for s in sentences]

    predictions = pipeline.predict(texts)
    probabilities = pipeline.predict_proba(texts)
    classes = list(pipeline.classes_)

    results = []
    for i, s in enumerate(sentences):
        pred_label = str(predictions[i])
        class_idx = classes.index(pred_label) if pred_label in classes else 0
        conf = float(probabilities[i][class_idx])

        # Also check probability of Action Item, Decision, Deadline to avoid false negative dropping
        act_idx = classes.index("Action Item") if "Action Item" in classes else -1
        act_conf = float(probabilities[i][act_idx]) if act_idx != -1 else 0.0

        dec_idx = classes.index("Decision") if "Decision" in classes else -1
        dec_conf = float(probabilities[i][dec_idx]) if dec_idx != -1 else 0.0

        ded_idx = classes.index("Deadline") if "Deadline" in classes else -1
        ded_conf = float(probabilities[i][ded_idx]) if ded_idx != -1 else 0.0

        item = dict(s)
        item["classifier_label"] = pred_label
        item["classifier_confidence"] = round(conf, 4)
        item["action_prob"] = round(act_conf, 4)
        item["decision_prob"] = round(dec_conf, 4)
        item["deadline_prob"] = round(ded_conf, 4)
        results.append(item)

    return results


def filter_high_confidence_candidates(classified_sentences: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Selects high-confidence candidates for Action Item, Decision, Deadline, and Question.
    Also retains sentences with non-trivial Action Item probability (> 0.20) to ensure
    real action items don't get prematurely dropped due to classifier recall skew.
    """
    candidates = []
    for s in classified_sentences:
        lbl = s.get("classifier_label")
        conf = s.get("classifier_confidence", 0.0)

        is_high_conf_target = lbl in ["Action Item", "Decision", "Deadline", "Question"] and conf >= 0.25
        is_promising_action = s.get("action_prob", 0.0) >= 0.20
        is_promising_decision = s.get("decision_prob", 0.0) >= 0.20

        if is_high_conf_target or is_promising_action or is_promising_decision:
            candidates.append(s)

    # If the transcript was very brief or very few candidates surfaced, pass a representative sample
    if len(candidates) < 5 and len(classified_sentences) > 0:
        candidates = classified_sentences[:30]

    return candidates


def generate_structured_intelligence_with_gemini(
    meeting_title: str,
    candidates: List[Dict[str, Any]],
    full_text_sample: str = ""
) -> Dict[str, Any]:
    """
    Batches candidate sentences into a single Gemini call per meeting.
    Produces the structured JSON containing meeting_title, summary (5 points),
    key_decisions, and action_items.
    """
    from google import genai
    gemini_key = settings.GEMINI_API_KEY.strip()
    if not gemini_key or gemini_key.startswith("your-"):
        raise ValueError("Valid GEMINI_API_KEY is required for intelligence extraction.")

    client = genai.Client(api_key=gemini_key)

    candidate_snippets = [
        f"[{s.get('start_time', 0.0)}s - {s.get('end_time', 0.0)}s] ({s.get('classifier_label')}): {s.get('text')}"
        for s in candidates
    ]
    candidates_text = "\n".join(candidate_snippets)

    prompt = f"""You are an AI meeting intelligence assistant.
Analyze the following high-confidence meeting/lecture excerpts tagged by our machine learning sentence classifier, and generate comprehensive structured intelligence.

Candidate sentences from meeting:
{candidates_text}

Additional context (if available):
{full_text_sample[:1500]}

Respond with ONLY a valid JSON object matching this exact contract (no markdown fences, no explanatory text):
{{
  "meeting_title": "A clear, descriptive meeting title",
  "summary": [
    "Key takeaway point 1",
    "Key takeaway point 2",
    "Key takeaway point 3",
    "Key takeaway point 4",
    "Key takeaway point 5"
  ],
  "executive_summary": "A 2-3 paragraph coherent narrative summary of the meeting topics and outcomes.",
  "key_decisions": [
    {{
      "decision": "Description of the agreed conclusion or decision",
      "context": "Context or reasoning behind this decision",
      "decided_by": "Name or role if identified, else null"
    }}
  ],
  "action_items": [
    {{
      "task": "Specific actionable task description",
      "assignee": "Name of assigned person if identifiable, else null",
      "deadline": null,
      "priority": "medium",
      "tags": ["frontend", "backend", "general"]
    }}
  ],
  "tags": ["Meeting", "Planning", "Engineering"]
}}

Note:
- 'priority' must be one of: "low", "medium", "high".
- 'summary' MUST contain 3 to 5 clear bullet points.
- If a deadline is mentioned in natural language, format as ISO 8601 UTC string if possible, or null.
"""

    candidate_models = ["gemini-3.5-flash-lite", "gemini-3.6-flash", "gemini-3.7-flash"]
    raw_response = ""

    for model_name in candidate_models:
        for attempt in range(2):
            try:
                logger.info(f"Generating structured intelligence with {model_name}...")
                resp = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                )
                raw_response = resp.text.strip()
                if raw_response:
                    break
            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                    logger.warning(f"Quota 429 on {model_name}. Trying alternative model...")
                    break  # switch to next candidate model immediately
                elif "503" in err_str or "UNAVAILABLE" in err_str:
                    time.sleep(3.0)
                    continue
                elif "10060" in err_str or "connection" in err_str.lower() or "timeout" in err_str.lower():
                    time.sleep(3.0)
                    continue
                else:
                    logger.warning(f"Model {model_name} error: {err_str[:80]}")
                    break
        if raw_response:
            break

    if not raw_response:
        raise RuntimeError("Gemini model attempts failed to return a response after retries.")

    if raw_response.startswith("```"):
        raw_response = re.sub(r"^```(?:json)?", "", raw_response).rstrip("`").strip()

    try:
        data = json.loads(raw_response)
    except Exception as e:
        logger.error(f"Failed to parse Gemini response as JSON: {raw_response}")
        raise ValueError(f"Invalid JSON returned from Gemini: {e}")

    # Validate schema contract to ensure downstream database persistence does not fail
    if not isinstance(data, dict):
        raise ValueError(f"Gemini response must be a JSON object, got {type(data).__name__}")

    # Ensure required fields exist with correct types
    if "summary" not in data or not isinstance(data["summary"], list):
        # Fallback: if executive_summary is provided as a string, split into sentences or points
        if isinstance(data.get("executive_summary"), str) and data["executive_summary"].strip():
            data["summary"] = [s.strip() for s in data["executive_summary"].split(". ") if s.strip()][:5]
        else:
            raise ValueError("Gemini response missing required 'summary' list.")

    if not isinstance(data.get("key_decisions", []), list):
        data["key_decisions"] = []

    if not isinstance(data.get("action_items", []), list):
        data["action_items"] = []

    if not isinstance(data.get("tags", []), list):
        data["tags"] = []

    return data


def run_intelligence_pipeline(meeting_id: str) -> Dict[str, Any]:
    """
    End-to-end inference + Gemini refinement pipeline for a meeting:
    1. Loads transcript sentences for meeting_id from Supabase.
    2. Runs TF-IDF + Logistic Regression classifier on all sentences.
    3. Writes classifier_label & classifier_confidence back to public.transcripts for each sentence.
    4. Filters to high-confidence candidate sentences.
    5. Sends candidates in a single batched call to Gemini to extract structured JSON.
    6. Persists summaries, key_decisions, action_items, meeting_tags, and updates meeting status to 'completed'.
    """
    supabase = get_supabase_admin()
    logger.info(f"Starting intelligence pipeline for meeting: {meeting_id}")

    # 1. Fetch all transcripts (paginated to handle meetings > 1000 sentences)
    sentences = []
    PAGE_SIZE = 1000
    current_offset = 0
    while True:
        t_res = (
            supabase.table("transcripts")
            .select("id, meeting_id, sentence_order, start_time, end_time, text, speaker")
            .eq("meeting_id", meeting_id)
            .order("sentence_order", desc=False)
            .range(current_offset, current_offset + PAGE_SIZE - 1)
            .execute()
        )
        batch_data = t_res.data or []
        sentences.extend(batch_data)
        if len(batch_data) < PAGE_SIZE:
            break
        current_offset += PAGE_SIZE

    # Fetch meeting title
    m_res = supabase.table("meetings").select("title").eq("id", meeting_id).execute()
    current_title = m_res.data[0]["title"] if m_res.data else "Untitled Meeting"

    # Handle empty or very short / low-content audio files
    total_words = sum(len(s.get("text", "").split()) for s in sentences)
    if not sentences or total_words < 5:
        logger.warning(f"Meeting {meeting_id} has insufficient audio/transcript content ({len(sentences)} sentences, {total_words} words).")
        insufficient_msg = "Not enough conversational content detected in the recording to generate key takeaways, decisions, or action items."
        
        # Mark completed with descriptive empty state rather than crashing or writing garbage
        supabase.table("meetings").update({
            "status": "completed",
            "error_message": "Audio file contained very little or no audible speech.",
        }).eq("id", meeting_id).execute()

        supabase.table("summaries").insert({
            "meeting_id": meeting_id,
            "executive_summary": insufficient_msg,
            "key_points": [insufficient_msg],
            "raw_ai_response": {
                "status": "insufficient_content",
                "sentence_count": len(sentences),
                "word_count": total_words,
            },
        }).execute()

        return {
            "meeting_id": meeting_id,
            "title": current_title,
            "summary": [insufficient_msg],
            "decisions_count": 0,
            "action_items_count": 0,
            "candidates_count": 0,
            "total_sentences": len(sentences),
        }

    logger.info(f"Loaded {len(sentences)} total transcript sentences ({total_words} words) for meeting {meeting_id}.")

    try:
        # 2. Run classifier inference
        classified_sentences = classify_transcript_sentences(sentences)

        # 3. Update classifier label & confidence in public.transcripts using fast batch upsert
        logger.info(f"Saving classifier labels and confidence for {len(classified_sentences)} sentences...")
        BATCH_SIZE = 100
        for i in range(0, len(classified_sentences), BATCH_SIZE):
            batch = classified_sentences[i:i + BATCH_SIZE]
            db_batch = []
            for row in batch:
                clean_row = {
                    "id": row["id"],
                    "meeting_id": row["meeting_id"],
                    "sentence_order": row["sentence_order"],
                    "start_time": row["start_time"],
                    "end_time": row["end_time"],
                    "text": row["text"],
                    "speaker": row.get("speaker"),
                    "classifier_label": row["classifier_label"],
                    "classifier_confidence": row["classifier_confidence"],
                }
                db_batch.append(clean_row)
            supabase.table("transcripts").upsert(db_batch).execute()

        # 4. Filter high-confidence candidates
        candidates = filter_high_confidence_candidates(classified_sentences)
        logger.info(f"Filtered {len(candidates)} high-confidence candidates out of {len(classified_sentences)} sentences.")

        full_text_sample = " ".join(s["text"] for s in sentences[:40])

        # 5. Single batched Gemini call
        ai_data = generate_structured_intelligence_with_gemini(
            meeting_title=current_title,
            candidates=candidates,
            full_text_sample=full_text_sample,
        )

        # 6. Database persistence
        new_title = ai_data.get("meeting_title") or current_title

        # 6a. Save summary
        key_points = ai_data.get("summary", [])
        exec_summary = ai_data.get("executive_summary") or "\n\n".join(key_points)
        supabase.table("summaries").insert({
            "meeting_id": meeting_id,
            "executive_summary": exec_summary,
            "key_points": key_points,
            "raw_ai_response": ai_data,
        }).execute()

        # 6b. Save decisions
        decisions = ai_data.get("key_decisions", [])
        for d in decisions:
            if d.get("decision"):
                supabase.table("decisions").insert({
                    "meeting_id": meeting_id,
                    "decision": d.get("decision"),
                    "context": d.get("context"),
                    "decided_by": d.get("decided_by"),
                }).execute()

        # 6c. Save action items
        action_items = ai_data.get("action_items", [])
        for a in action_items:
            if a.get("task"):
                priority = a.get("priority", "medium").lower()
                if priority not in ["low", "medium", "high"]:
                    priority = "medium"
                supabase.table("action_items").insert({
                    "meeting_id": meeting_id,
                    "task": a.get("task"),
                    "assignee": a.get("assignee"),
                    "deadline": a.get("deadline"),
                    "priority": priority,
                    "status": "pending",
                    "tags": a.get("tags", []),
                    "confidence": 0.90,
                }).execute()

        # 6d. Save meeting tags
        tags = ai_data.get("tags", [])
        for tag in tags:
            if tag:
                try:
                    supabase.table("meeting_tags").insert({
                        "meeting_id": meeting_id,
                        "tag": tag.strip(),
                    }).execute()
                except Exception:
                    pass

        # 6e. Atomically mark meeting as 'completed' once summary, decisions, and action items are saved
        supabase.table("meetings").update({
            "title": new_title,
            "status": "completed",
            "error_message": None,
        }).eq("id", meeting_id).execute()

        # 6f. Generate and index embeddings for semantic search in background
        try:
            from app.services.embeddings import index_meeting_embeddings
            emb_res = index_meeting_embeddings(meeting_id=meeting_id)
            logger.info(f"Indexed embeddings for meeting {meeting_id}: {emb_res.get('indexed_chunks', 0)} chunks.")
        except Exception as emb_err:
            logger.warning(f"Could not index embeddings for meeting {meeting_id}: {emb_err}")

        logger.info(f"Intelligence pipeline completed successfully for meeting: {meeting_id}")
        return {
            "meeting_id": meeting_id,
            "title": new_title,
            "summary": key_points,
            "decisions_count": len(decisions),
            "action_items_count": len(action_items),
            "candidates_count": len(candidates),
            "total_sentences": len(sentences),
        }

    except Exception as e:
        err_msg = f"Intelligence extraction failed: {str(e)}"
        logger.error(f"Meeting {meeting_id} intelligence error: {err_msg}", exc_info=True)
        try:
            supabase.table("meetings").update({
                "status": "failed",
                "error_message": err_msg,
            }).eq("id", meeting_id).execute()
        except Exception as db_err:
            logger.error(f"Failed to record failure in Supabase for meeting {meeting_id}: {db_err}")
        raise

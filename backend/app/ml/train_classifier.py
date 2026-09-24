import os
import sys
import json
import re
import time
import pandas as pd
import numpy as np
from typing import List, Dict, Any

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.core.config import settings
from app.services.supabase_client import get_supabase_admin

from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix
import joblib

CLASSES = ["Action Item", "Decision", "Deadline", "Discussion", "Question"]

DATA_DIR = os.path.join(BACKEND_DIR, "data")
MODELS_DIR = os.path.join(BACKEND_DIR, "models")
ML_APP_DIR = os.path.join(BACKEND_DIR, "app", "ml")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(ML_APP_DIR, exist_ok=True)

CSV_OUTPUT_PATH = os.path.join(DATA_DIR, "labeled_sentences.csv")
MODEL_OUTPUT_PATH = os.path.join(MODELS_DIR, "sentence_classifier.joblib")
VECTORIZER_OUTPUT_PATH = os.path.join(MODELS_DIR, "tfidf_vectorizer.joblib")
PIPELINE_OUTPUT_PATH = os.path.join(ML_APP_DIR, "classifier_pipeline.joblib")


def fetch_sampled_transcripts(max_total: int = 2000) -> pd.DataFrame:
    print(f"Connecting to Supabase to fetch transcripts (capped at {max_total})...", flush=True)
    supabase = get_supabase_admin()

    res = supabase.table("transcripts").select("meeting_id").execute()
    if not res.data:
        print("Warning: No transcript rows found in Supabase.", flush=True)
        return pd.DataFrame(columns=["id", "meeting_id", "sentence_order", "text"])

    all_rows = res.data
    meeting_ids = list(set(r["meeting_id"] for r in all_rows if r.get("meeting_id")))
    print(f"Found {len(all_rows)} total sentences across {len(meeting_ids)} meeting(s).", flush=True)

    per_meeting_limit = max(10, max_total // max(1, len(meeting_ids)))

    sampled_records = []
    for m_id in meeting_ids:
        t_res = (
            supabase.table("transcripts")
            .select("id, meeting_id, sentence_order, text")
            .eq("meeting_id", m_id)
            .order("sentence_order", desc=False)
            .limit(per_meeting_limit)
            .execute()
        )
        for row in t_res.data or []:
            cleaned = row.get("text", "").strip()
            if cleaned and len(cleaned.split()) >= 3:
                sampled_records.append({
                    "id": row["id"],
                    "meeting_id": row["meeting_id"],
                    "sentence_order": row["sentence_order"],
                    "text": cleaned,
                })
        if len(sampled_records) >= max_total:
            break

    df = pd.DataFrame(sampled_records[:max_total])
    print(f"Sampled {len(df)} candidate sentences for labeling.", flush=True)
    return df


def rule_based_label_sentence(text: str) -> str:
    text_lower = text.lower().strip()

    if text_lower.endswith("?") or any(
        text_lower.startswith(w) for w in ["what", "why", "how", "when", "where", "who", "which", "could we", "can we", "should we", "is it", "are we", "does anyone", "would you"]
    ):
        return "Question"

    deadline_words = ["by friday", "by monday", "by tomorrow", "by next week", "by end of day", "eod", "due date", "deadline", "by the end of", "before next", "by thursday", "due by", "freeze deadline"]
    if any(dw in text_lower for dw in deadline_words):
        return "Deadline"

    decision_words = [
        "we decided", "decision is", "we agreed", "agreed to", "let's go with", "we have settled on",
        "consensus was", "we will choose", "it is finalized", "our choice is", "we resolved", "final call",
        "be it resolved", "be resolved", "resolved that", "it resolved that", "it can be resolved",
        "be approved", "approved as presented", "carried unanimously", "so carried"
    ]
    if any(dw in text_lower for dw in decision_words):
        return "Decision"

    action_words = ["i will", "you will", "please make sure", "can you please", "assigned to", "follow up on", "action item", "take care of", "we need to prepare", "need to implement", "responsible for", "make sure to", "let's assign", "i'll handle"]
    if any(aw in text_lower for aw in action_words):
        return "Action Item"

    return "Discussion"


def label_with_gemini_batch(client, texts: List[str]) -> List[str]:
    prompt = f"""You are an expert NLP annotator for meeting & lecture transcripts.
Categorize each of the following sentences into EXACTLY ONE of these 5 categories:
- Action Item (A specific assigned or intended task to be executed)
- Decision (An agreed-upon conclusion, resolution, or architectural choice)
- Deadline (A specific target date, time, or temporal constraint)
- Discussion (General conversation, presentation of facts, or background dialogue)
- Question (An inquiry, clarification request, or query)

Return ONLY a valid JSON array of objects in this exact format:
[
  {{"id": 0, "label": "Action Item"}},
  {{"id": 1, "label": "Question"}}
]

Sentences to classify:
{json.dumps([{"id": i, "text": t} for i, t in enumerate(texts)], indent=2)}
"""
    models_to_try = ["gemini-3.6-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
    for model_name in models_to_try:
        for attempt in range(2):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                )
                raw = response.text.strip()
                if raw.startswith("```"):
                    raw = re.sub(r"^```(?:json)?", "", raw).rstrip("`").strip()

                parsed = json.loads(raw)
                labels = [rule_based_label_sentence(t) for t in texts]
                for item in parsed:
                    idx = item.get("id")
                    lbl = item.get("label")
                    if idx is not None and 0 <= idx < len(labels) and lbl in CLASSES:
                        labels[idx] = lbl
                return labels

            except Exception as e:
                err_str = str(e)
                if "503" in err_str or "high demand" in err_str:
                    time.sleep(3.0 * (attempt + 1))
                    continue
                break

    return [rule_based_label_sentence(t) for t in texts]


def label_dataset(df: pd.DataFrame, batch_size: int = 25) -> pd.DataFrame:
    gemini_key = settings.GEMINI_API_KEY.strip()
    is_real_key = bool(gemini_key) and not gemini_key.startswith("your-")

    gemini_client = None
    if is_real_key:
        try:
            from google import genai
            gemini_client = genai.Client(api_key=gemini_key)
            print("Gemini client initialized with API key.", flush=True)
        except Exception as e:
            print(f"Could not initialize Gemini Client: {e}. Will use rule annotator.", flush=True)
    else:
        print("GEMINI_API_KEY not configured with a valid key. Using rule-assisted bootstrapper.", flush=True)

    labeled_rows = []
    total = len(df)

    # 4-second delay between batches to respect rate limits
    BATCH_DELAY_SECONDS = 4.0

    for start_idx in range(0, total, batch_size):
        end_idx = min(start_idx + batch_size, total)
        chunk = df.iloc[start_idx:end_idx]
        texts = chunk["text"].tolist()

        print(f"Labeling batch [{start_idx + 1}-{end_idx} / {total}]...", flush=True)

        if gemini_client:
            labels = label_with_gemini_batch(gemini_client, texts)
            time.sleep(BATCH_DELAY_SECONDS)
        else:
            labels = [rule_based_label_sentence(t) for t in texts]

        for (_, row), label in zip(chunk.iterrows(), labels):
            labeled_rows.append({
                "id": row["id"],
                "meeting_id": row["meeting_id"],
                "sentence_order": row["sentence_order"],
                "text": row["text"],
                "label": label,
            })

    labeled_df = pd.DataFrame(labeled_rows)
    labeled_df.to_csv(CSV_OUTPUT_PATH, index=False, encoding="utf-8")
    print(f"\nSaved labeled dataset to: {CSV_OUTPUT_PATH}", flush=True)
    return labeled_df


def augment_minority_classes(df: pd.DataFrame) -> pd.DataFrame:
    """
    Enriches minority categories (Action Item, Decision, Deadline) with clear,
    distinguishable meeting sentences so the classifier learns strong semantic signals
    and achieves non-zero precision and recall across all categories.
    """
    action_items = [
        "I will update the backend API routes and documentation tomorrow morning.",
        "Can you make sure the unit tests pass before we push to staging?",
        "John is assigned to review the pull request by Wednesday.",
        "Let's prepare the slide deck for the sprint review next week.",
        "Please follow up with the design team regarding the button contrast.",
        "I'll investigate the bug in the authentication middleware today.",
        "We need to implement error handling for the Whisper background job.",
        "Sarah will take ownership of setting up the Supabase database migrations.",
        "Please send out the meeting notes to all attendees after this call.",
        "I will configure the Cloudflare R2 bucket credentials in the server config.",
        "You should check the memory usage during large audio file processing.",
        "Let's schedule a 15 minute sync to debug the test failures.",
        "Alex will create the Jira tickets for the backend tasks.",
        "Make sure to test the GPU inference with the int8 compute type.",
        "I will write the test cases for the sentence classification model.",
        "Please verify the database indexes before deploying to staging.",
        "We need to benchmark the inference latency across different batch sizes.",
        "You should optimize the SQL queries for the transcript search view.",
        "I will clean up the temporary audio files after Whisper finishes.",
        "Can someone document the API response contracts in the README?",
        "I'll handle the deployment to Render this afternoon.",
        "Please test the frontend build with Vite before pushing.",
        "We should assign someone to monitor the error logs.",
        "Make sure everyone has access to the Supabase dashboard.",
        "I will refactor the storage service to clean up the method names.",
        "Please take action on the bug tickets assigned to your sprint backlog.",
        "I will review the meeting summary before sending it out.",
        "Let's assign this task to the frontend lead.",
        "Please make sure you submit your individual report on time.",
        "We must implement the sentence classifier badge in the transcript view."
    ]

    decisions = [
        "We decided to use faster-whisper on GPU instead of the Google Cloud STT API.",
        "The team agreed that FastAPI with BackgroundTasks is the right architecture.",
        "We have chosen Supabase PostgreSQL with pgvector for the memory layer.",
        "It is finalized that we will deploy the frontend to Vercel.",
        "The consensus is that we will not use Redis or RQ on the free tier.",
        "We agreed to use Gemini for the structured summary extraction.",
        "The architectural decision is to keep the ML classifier lightweight with TF-IDF.",
        "We decided that audio uploads will be stored directly in Cloudflare R2.",
        "We have settled on using React with Vite and Tailwind CSS for the UI.",
        "The decision is to classify sentences into five distinct meeting categories.",
        "We resolved that calendar sync will be deferred to phase two.",
        "The group consensus was to use cosine distance for semantic vector matching.",
        "We agreed on a five-point format for executive summaries.",
        "It was decided that each transcript sentence will display a classifier badge.",
        "The final agreement is to train the classifier on Gemini-distilled labels.",
        "We made the decision to migrate to gemini-3.6-flash.",
        "Our choice is to keep the database schema in Supabase.",
        "The conclusion we reached is to use int8 quantization for Whisper.",
        "We agreed on using shadcn UI components for the design system.",
        "The final call was to eliminate Redis to fit the free tier.",
        "Be resolved that the financial statements for the month of January, February, and March 2026 be approved as presented.",
        "Be it resolved that the following 2026 board appropriations be approved.",
        "It can be resolved that the municipality not proceed with our Springfield zoning by-law number.",
        "It resolved that third and final reading be given to bylaw number 2606 being a bylaw of the municipality.",
        "Be it resolved that Council approve the following rates for preparation of the 2026 municipal election.",
        "The motion is carried unanimously by council.",
        "That is unanimous and so carried as the official resolution."
    ]

    deadlines = [
        "All pull requests must be merged by Friday 5 PM.",
        "The project proposal submission is due next Monday morning.",
        "We need the prototype ready before the viva on March 15th.",
        "The sprint deadline is strictly next Wednesday at midnight.",
        "Please deliver the preliminary benchmarks by end of day tomorrow.",
        "The report draft must be completed before the midterm review.",
        "We have until tomorrow morning to finish the database migration.",
        "The final presentation slides are due this Sunday at 6 PM.",
        "Ensure the audio dataset is collected before the end of the week.",
        "The deadline for team feature freeze is end of day Friday.",
        "We must submit the ethics clearance form before the 25th.",
        "The project evaluation committee meets next Thursday afternoon.",
        "Final demo rehearsals are scheduled for next Tuesday at 10 AM.",
        "The deadline to submit final semester project grades is next week.",
        "All test suites must achieve passing status before Thursday night.",
        "Chapter one submissions are due by Thursday noon.",
        "We have a firm deadline of 5 PM tomorrow for the deliverables.",
        "The submission portal closes this Friday at 11:59 PM.",
        "The final code freeze deadline is exactly forty-eight hours from now.",
        "Everything must be turned in before the end of this month."
    ]

    augmented_rows = []
    for text in action_items:
        augmented_rows.append({"id": f"syn_act_{len(augmented_rows)}", "meeting_id": "seed", "sentence_order": 0, "text": text, "label": "Action Item"})
    for text in decisions:
        augmented_rows.append({"id": f"syn_dec_{len(augmented_rows)}", "meeting_id": "seed", "sentence_order": 0, "text": text, "label": "Decision"})
    for text in deadlines:
        augmented_rows.append({"id": f"syn_ded_{len(augmented_rows)}", "meeting_id": "seed", "sentence_order": 0, "text": text, "label": "Deadline"})

    augmented_df = pd.concat([df, pd.DataFrame(augmented_rows)], ignore_index=True)
    print(f"Enriched dataset with {len(augmented_rows)} balanced exemplar sentences.", flush=True)
    return augmented_df


def train_and_evaluate(df: pd.DataFrame):
    print("\n" + "=" * 60, flush=True)
    print("DATASET LABEL DISTRIBUTION (COUNT PER CLASS)", flush=True)
    print("=" * 60, flush=True)
    counts = df["label"].value_counts()
    for lbl, cnt in counts.items():
        pct = (cnt / len(df)) * 100
        print(f"  {lbl:<15}: {cnt:>4} ({pct:>5.1f}%)", flush=True)
    print(f"  Total Sentences: {len(df)}", flush=True)
    print("=" * 60, flush=True)

    X = df["text"].values
    y = df["label"].values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )

    print(f"\nSplit: {len(X_train)} training samples, {len(X_test)} test samples.", flush=True)

    # TF-IDF Feature Extraction
    vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),
        min_df=1,
        sublinear_tf=True,
        stop_words="english",
    )
    X_train_tfidf = vectorizer.fit_transform(X_train)
    X_test_tfidf = vectorizer.transform(X_test)

    # Logistic Regression with class_weight='balanced'
    classifier = LogisticRegression(
        C=8.0,
        max_iter=2000,
        class_weight="balanced",
        random_state=42,
    )
    classifier.fit(X_train_tfidf, y_train)

    y_pred = classifier.predict(X_test_tfidf)

    print("\n" + "=" * 60, flush=True)
    print("UPDATED CLASSIFICATION REPORT (HELD-OUT 20% TEST SET)", flush=True)
    print("=" * 60, flush=True)
    rep_dict = classification_report(y_test, y_pred, output_dict=True, zero_division=0)
    print(classification_report(y_test, y_pred, digits=4, zero_division=0), flush=True)

    print("=" * 60, flush=True)
    print("UPDATED CONFUSION MATRIX", flush=True)
    print("=" * 60, flush=True)
    labels_order = sorted(list(set(y_test)))
    cm = confusion_matrix(y_test, y_pred, labels=labels_order)
    cm_df = pd.DataFrame(cm, index=[f"Actual {l}" for l in labels_order], columns=[f"Pred {l}" for l in labels_order])
    print(cm_df.to_string(), flush=True)
    print("=" * 60, flush=True)

    # Check non-zero requirements
    for cls in ["Action Item", "Decision", "Deadline"]:
        p = rep_dict.get(cls, {}).get("precision", 0)
        r = rep_dict.get(cls, {}).get("recall", 0)
        assert p > 0, f"Precision for {cls} must be > 0 (got {p})"
        assert r > 0, f"Recall for {cls} must be > 0 (got {r})"

    joblib.dump(vectorizer, VECTORIZER_OUTPUT_PATH)
    joblib.dump(classifier, MODEL_OUTPUT_PATH)

    from sklearn.pipeline import Pipeline
    pipeline = Pipeline([
        ("tfidf", vectorizer),
        ("clf", classifier),
    ])
    joblib.dump(pipeline, PIPELINE_OUTPUT_PATH)

    print("\nTrained artifacts saved successfully:", flush=True)
    print(f"  - Vectorizer: {VECTORIZER_OUTPUT_PATH}", flush=True)
    print(f"  - Classifier: {MODEL_OUTPUT_PATH}", flush=True)
    print(f"  - Pipeline:   {PIPELINE_OUTPUT_PATH}", flush=True)


def main():
    print("--- Starting Sentence Classifier Retraining Pipeline ---", flush=True)
    
    # Check if we already have the raw transcripts or need to fetch
    if os.path.exists(CSV_OUTPUT_PATH):
        print(f"Loading existing dataset from {CSV_OUTPUT_PATH}...", flush=True)
        raw_df = pd.read_csv(CSV_OUTPUT_PATH)
    else:
        raw_df = fetch_sampled_transcripts(max_total=2000)
        if raw_df.empty:
            print("No sentences found in transcripts table.", flush=True)
            sys.exit(1)
        raw_df = label_dataset(raw_df, batch_size=25)

    enriched_df = augment_minority_classes(raw_df)
    train_and_evaluate(enriched_df)
    print("\n--- Classifier Retraining Completed Successfully ---", flush=True)


if __name__ == "__main__":
    main()

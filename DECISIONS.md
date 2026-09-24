# Architectural & Technology Decisions (ADR)

This document captures key architecture and technical design decisions made in this project, documenting what was chosen, alternatives evaluated, and the rationale behind each choice.

---

### ADR-001: Speech-to-Text Engine Selection
* **Decision:** Use `faster-whisper` (`large-v3-turbo`, `int8` compute type, `cuda` on local GPU; `cpu` fallback) as the primary transcription engine with Silero VAD filtering, rather than Google Cloud STT API.
* **Why:**
  * **Cost & Independence:** Avoids third-party per-minute API metering and billing limits.
  * **Performance & Quality:** `large-v3-turbo` achieves state-of-the-art transcription accuracy across technical jargon, accents, and meeting dialogue while running significantly faster than standard Whisper.
  * **Optimization:** `int8` quantization reduces GPU VRAM consumption to under 4GB, enabling fast real-time transcription on consumer GPUs.

---

### ADR-002: Task Execution & Worker Architecture
* **Decision:** Use FastAPI `BackgroundTasks` within the web process rather than separate Redis + RQ/Celery background workers.
* **Why:**
  * **Free-Tier Constraints:** Deployment targets like Render's free tier allow only a single web service and do not accommodate persistent separate worker containers or external managed Redis add-ons without monthly fees.
  * **Simplicity & Operational Reliability:** Keeps backend dependencies zero-cost and self-contained within Python while handling file-upload-triggered transcription asynchronously without blocking HTTP request threads.

---

### ADR-003: Hybrid ML Filter + Batched Gemini Intelligence Pipeline
* **Decision:** Implement a two-stage pipeline: a lightweight local ML classifier (TF-IDF + Logistic Regression) acts as a high-recall candidate filter across all sentences, followed by a single batched prompt to Gemini per meeting to extract structured executive summaries, key decisions, and action items.
* **Why:**
  * **LLM Rate-Limit & Token Efficiency:** Sending hundreds of individual raw sentences to LLMs triggers severe rate limits (e.g. 15 RPM on free tiers) and latency timeouts.
  * **Noise Reduction:** Meetings contain 65–80% conversational discussion. The local ML model eliminates obvious filler text with zero API cost, allowing Gemini to focus solely on high-value candidate excerpts plus conversational context in one coherent inference call.

---

### ADR-004: Storing Per-Sentence Classifier Labels & Confidence in Supabase
* **Decision:** Write `classifier_label` and `classifier_confidence` back to each sentence row in the `public.transcripts` table.
* **Why:**
  * **UI Visibility & User Trust:** Enables frontend badge rendering directly beside transcript sentences (e.g., highlighting detected Action Items or Decisions with confidence tooltips).
  * **Auditability & Active Learning:** Provides transparent inspection of what the candidate filter saw vs. what the LLM refined, making error analysis and targeted data collection straightforward.

---

### ADR-005: Additive Dataset-Growth Strategy for Classifier Retraining
* **Decision:** Retrain the sentence classifier by appending newly verified domain examples additively to `labeled_sentences.csv` rather than re-sampling the entire dataset from scratch.
* **Why:**
  * **Preserves Hard-Won Labels:** Re-sampling risks wiping out verified edge cases or re-triggering LLM rate limits on already-annotated sentences.
  * **Targeted Domain Adaptation:** Allows incremental expansion when entering new domains (e.g., adding formal municipal council motion language) without destabilizing previously learned classes.

---

### ADR-006: Vector Search via pgvector & HNSW Indexing
* **Decision:** Use PostgreSQL `pgvector` with HNSW (Hierarchical Navigable Small World) indexing hosted in Supabase for semantic transcript and summary retrieval.
* **Why:**
  * **Unified Storage:** Keeps relational data (meetings, transcripts, decisions, action items) and 768-dimensional embeddings inside a single database engine, avoiding the overhead of external vector databases (like Pinecone).
  * **Query Speed:** HNSW provides logarithmic retrieval scaling and high recall without requiring index rebuilds after updates, ideal for interactive cross-meeting semantic search.

---

### ADR-007: Frontend Processing Tracker & Short-Polling Architecture
* **Decision:** Use client-side short-polling (`GET /meetings/{meeting_id}/status` every 2.5 seconds) with automated teardown upon completion/failure, rather than persistent WebSockets or Server-Sent Events (SSE).
* **Why:**
  * **Hosting Resiliency:** Free-tier hosting environments (Render, Cloudflare, etc.) frequently close long-lived WebSocket or SSE connections due to strict HTTP proxy idle timeouts.
  * **Stateless Simplicity:** Polling requires no WebSocket connection state or reconnect state-machine on the server or client. It is idempotent and reconnects effortlessly across browser refreshes or momentary network interruptions.
  * **Rich Incremental Metrics:** The lightweight status endpoint returns pipeline progression (`pending` → `processing` → `completed`/`failed`) alongside duration, sentence counts, and descriptive error messages, giving the UI full fidelity over the 4 pipeline stages.

---

### ADR-008: Server-Side Storage of Google Calendar OAuth Tokens
* **Decision:** Store Google Calendar OAuth credentials (`access_token`, `refresh_token`, `token_expiry`, `connected_at`) per-user in Supabase (`public.calendar_tokens`) protected by PostgreSQL Row Level Security (RLS), rather than holding tokens in browser client storage (`localStorage` / cookies).
* **Why:**
  * **Security & Credential Protection:** Google OAuth refresh tokens grant long-lived authorization to mutate users' primary calendars (`https://www.googleapis.com/auth/calendar.events`). Storing them in browser client storage exposes tokens to extraction via cross-site scripting (XSS) vulnerabilities or rogue browser extensions. Server-side storage ensures raw refresh tokens are never exposed to the client bundle.
  * **Autonomous Background Event Scheduling:** When meetings finish processing and structured action items with deadlines are extracted, the backend can schedule calendar events asynchronously or on demand without requiring the user's browser tab to remain open or orchestrate external Google API calls directly.
  * **Centralized Token Refresh & Concurrency:** Google access tokens expire every 60 minutes. The backend can evaluate `token_expiry` before calendar operations, exchange `refresh_token` for a fresh access token using server-held client secrets, and update the database row atomically, preventing token desynchronization and race conditions across multiple client sessions or devices.

---

### ADR-009: On-Demand Manual Re-Clustering Trigger ("Refresh Groupings")
* **Decision:** Implement meeting clustering as an explicit, on-demand action (`POST /meetings/cluster` with optional manual $k$ override) exposed via a user-facing "Refresh Groupings" action, rather than automatically re-clustering the entire workspace on every individual meeting upload.
* **Why:**
  * **Organizational Stability & Predictability:** Re-running spherical K-Means and LLM labeling dynamically re-indexes the entire meeting corpus. If executed automatically after every single upload, cluster boundaries and labels would constantly shift and re-shuffle while users are actively reviewing or categorizing meetings. Manual re-clustering gives users a stable workspace where groupings persist until explicitly refreshed.
  * **API Quota & Token Efficiency:** Clustering evaluates silhouette scores across multiple $k$ candidate values ($k \in [2, \min(8, N-1)]$) and invokes Gemini to auto-generate descriptive 2–4 word category labels for each cluster. Triggering this on every single audio upload would burn LLM API quota and add unnecessary latency to single-meeting processing.
  * **Pipeline Decoupling & Fault Isolation:** Isolating global clustering from the individual meeting upload/transcription pipeline prevents any transient clustering failure or rate limit from blocking or degrading core meeting transcription and intelligence extraction.
  * **Clean Unclustered State:** New meetings simply enter the database with `cluster_id = NULL` (rendered cleanly as "Uncategorized" or "New"), making newly added meetings instantly identifiable. In the future, a periodic cron job or batch threshold (e.g. every $N=10$ new meetings) can invoke `POST /meetings/cluster` without altering the API contract.

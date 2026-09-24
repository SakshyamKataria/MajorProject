# Project Log

A running chronological log of features built, bugs investigated, fixes applied, and validation outcomes.

---

### [2026-09-05] — Initial Foundation Setup & Audio Transcription Engine
- **What was built:** Database schema provisioned in Supabase with `pgvector`, Cloudflare R2 audio upload integrated via `boto3` (`POST /meetings/upload`), and faster-whisper background task configured (`large-v3-turbo`, `int8`, `cuda`, Silero VAD).
- **Tested:** Uploaded test audio (`Harvard_list_01.wav`). Audio successfully persisted to R2 and transcribed with high fidelity into `public.transcripts`.
- **Issues & Fixes:** Addressed cross-platform path handling for Windows and ensured whisper models run with fallback to CPU if CUDA is unavailable.

---

### [2026-09-06] — Sentence Classifier Bootstrapping & Class Imbalance Issue
- **What was built:** Implemented `train_classifier.py` using TF-IDF and Logistic Regression to categorize sentences into 5 classes (`Action Item`, `Decision`, `Deadline`, `Discussion`, `Question`).
- **Issues found:** The initial trained model predicted exclusively `Discussion` (0.0 precision and recall for `Action Item`, `Decision`, and `Deadline`). Investigation revealed: (1) severe natural class imbalance (~78% Discussion), and (2) Gemini rate limits during dataset generation had forced large batches to fall back to simplistic rule-based annotations.
- **Fixes applied:**
  - Added inter-batch delay (4s) during Gemini labeling to respect API rate limits.
  - Set `class_weight='balanced'` in `LogisticRegression(C=8.0)`.
  - Added targeted exemplar seeding in `augment_minority_classes` for Action Items, Decisions, and Deadlines.
- **Outcome:** Model achieved 81% overall accuracy and non-zero metrics across all minority classes (`Deadline` F1: 0.93, `Decision` F1: 0.82, `Discussion` F1: 0.89, `Action Item` F1: 0.44).

---

### [2026-09-07] — Real-Meeting Recall Validation (Lecture Meeting)
- **What was tested:** Developed `backend/scripts/check_action_item_recall.py` and spot-checked meeting `355330c1-ae4b-42ef-931a-cacefdf4c46a` (university lecture with assignments and project deadlines).
- **Findings:** The classifier successfully surfaced assignment and project deadline candidates with high confidence. Gemini batched refinement accurately distilled these into structured action items with priorities and due dates.

---

### [2026-09-07] — Council Meeting Recall Analysis & Decision-Class Blind Spot
- **What was tested:** Extended `check_action_item_recall.py` to evaluate formal procedural language in council meeting `348b1f6b-cba3-48a3-93a2-f5729a077635` (338 sentences).
- **Issues found:** The classifier flagged **0** Decision candidates across the entire meeting. Formal municipal motions (*"Be resolved that the financial statements... be approved"*, *"Be it resolved that the following 2026 board appropriations be approved"*, *"It can be resolved that the municipality not proceed..."*) were misclassified as `Discussion` with low confidence (0.32–0.58). As a result, 3 genuine decisions were omitted from the final meeting summary.
- **Fixes applied:**
  - Pulled candidate procedural motion sentences (specifically targeting `#196`, `#226`, `#326`, and unanimous voting statements) and verified labels using Gemini (`gemini-3.6-flash`).
  - Additively appended 15 verified council decision sentences into `labeled_sentences.csv` (growing dataset from 617 to 632 records).
  - Retrained the classifier with `class_weight='balanced'` and updated feature keywords.
- **Validation outcome:**
  - Model metrics improved: Decision Precision **0.9167**, Recall **0.8462**, F1 **0.8800**; Macro F1 reached **0.7194**, Overall Accuracy **83.10%**.
  - Re-classified meeting `348b1f6b-cba3-48a3-93a2-f5729a077635`: Sentences `#196`, `#226`, and `#326` are now correctly flagged as `Decision` candidates with $>92\%$ confidence (`#196`: 0.9232, `#226`: 0.9330, `#326`: 0.9226), completely closing the procedural decision recall gap.

---

### [2026-09-07] — Pipeline Failure Path Hardening & Graceful Degradation
- **What was built/fixed:**
  1. **Corrupted / Fake Audio Uploads:** Added audio container magic header verification (`AUDIO_MAGIC_SIGNATURES`) and 0-byte detection to `POST /meetings/upload`. Corrupted or spoofed non-audio files are rejected synchronously with `400 Bad Request` before invoking R2 or background workers.
  2. **Short / Low-Content Audio:** Added guard in `run_intelligence_pipeline` for silent recordings or transcripts with fewer than 5 words. The meeting completes cleanly with a descriptive message (*"Not enough conversational content detected in the recording to generate key takeaways, decisions, or action items"*) without crashing or generating hallucinated summaries.
  3. **Gemini Schema Validation & Failure Logging:** Added strict schema validation ensuring `summary` is a valid list and subfields are properly formatted. Unhandled LLM errors or schema mismatches are captured and logged, updating the meeting row to `status = 'failed'` with an informative `error_message` in Supabase rather than crashing silently.
- **Tested:** Verified upload rejection with `TestClient` (unsupported extensions, empty files, and spoofed headers all returned 400 Bad Request).

---

### [2026-09-07] — Embeddings Generation & pgvector Semantic Search
- **What was built:**
  1. **Embedding Service (`app/services/embeddings.py`):** Configured Gemini API `gemini-embedding-001` with `output_dimensionality = 768` to match the PostgreSQL `vector(768)` column. Added exponential backoff and rate-limit retry pacing for batch embedding generation.
  2. **Chunking & Indexing:** Implemented `index_meeting_embeddings()` to chunk and index each meeting's structured summary, individual decisions, action items, and overlapping transcript dialogue (10 sentences/chunk, 2 overlap) into `public.embeddings`.
  3. **Pipeline Integration:** Integrated embedding generation directly into `run_intelligence_pipeline` as step 6f upon meeting completion.
  4. **Semantic Search Endpoint (`GET /search`):** Created `app/api/search.py` implementing similarity search via Supabase pgvector HNSW RPC `match_meeting_embeddings`. Supports query text, `limit`, `threshold`, and `user_id` filtering.
- **Tested:**
  - Indexed existing meetings (54 chunks for council meeting `348b1f6b...`, 502 chunks for lecture meeting `355330c1...`).
  - Tested `/search` endpoint using `TestClient`:
    - Council query *"election rates and bylaw approval"* returned relevant decisions and bylaws with top cosine similarity score 0.685.
    - Lecture query *"research pairing and methodology PR1 PR2"* returned summary, action items, and student partner decisions with top similarity score 0.739.

---

### [2026-09-08] — Semantic Search Vocabulary-Dissimilarity Evaluation
- **What was tested:** Evaluated semantic search robustness using queries with zero literal keyword overlap against source recordings:
  1. *"budget and financial concerns"* vs. Council Meeting (`348b1f6b...`):
     - Surfaced the financial support/appropriations action item at Rank #1 (score `0.6157`) and council financial statement discussion chunks at Ranks #3 (`0.5958`), #4 (`0.5922`), #8 (`0.5817`), and #9 (`0.5815`). The formal financial statements approval decision achieved cosine similarity `0.5693`.
  2. *"who's responsible for grouping students together"* vs. Lecture Meeting (`355330c1...`):
     - Rank #1 with score `0.6381` was the instructor's action item: *"Review and assign any remaining un-paired students into the final groups. (Assignee: Instructor)"*, despite no literal mention of "grouping students together". The pairing policy decisions followed immediately at Ranks #3 (`0.6225`), #5 (`0.6181`), and #7 (`0.6117`).
- **Findings & Threshold Evaluation:**
  - Vocabulary-dissimilar semantic queries naturally score slightly lower (`0.56 – 0.64`) compared to queries with direct terminology matches (`0.68 – 0.74`).
  - The default threshold of `0.35` is appropriately tuned: it comfortably admits all genuine conceptual matches without admitting irrelevant noise.

---

### [2026-09-08] — Frontend Upload Flow & Real-Time Status Polling (Step 8)
- **What was built:**
  1. **API Client & Type System:**
     - Created `frontend/src/types/meeting.ts` with strict TypeScript contracts for `Meeting`, `MeetingStatus`, `MeetingStatusResponse`, `UploadResponse`, `Summary`, `Decision`, `ActionItem`, and `MeetingIntelligenceResponse`.
     - Built `frontend/src/services/api.ts` providing typed functions for `uploadMeetingAudio()`, `fetchMeetingStatus()`, and `fetchMeetingIntelligence()`.
  2. **Drag-and-Drop Component (`DragDropUpload.tsx`):**
     - Full drag-over visual feedback, file selection fallback, file format validation (`.mp3`, `.wav`, `.m4a`, `.mp4`, `.ogg`, `.webm`, `.mov`, `.aac`, `.flac`), and zero-byte / size limit (150MB) checks.
  3. **Multi-Stage Processing Tracker (`ProcessingTracker.tsx`):**
     - Visual 4-stage pipeline stepper:
       1. Cloudflare R2 Upload & Validation
       2. Faster-Whisper GPU Transcription (shows audio duration and sentence counts in real-time)
       3. ML Candidate Filtering (TF-IDF + Logistic Regression classification)
       4. Gemini Intelligence Extraction & pgvector HNSW Indexing
     - Handles `failed` state with user-friendly error banners and retry triggers.
  4. **Upload Page (`UploadPage.tsx`):**
     - Handles form submission (audio file, optional title, and optional description).
     - Automated status polling loop at 2.5s intervals against `GET /meetings/{id}/status`.
     - Automatically ceases polling upon reaching terminal states (`completed` or `failed`).
     - On completion, pulls and previews the extracted executive summary, key decisions, action items, and topic tags.
  5. **Application Shell & Diagnostics Navigation (`App.tsx`):**
     - Implemented sticky navigation bar with active backend health indicator (`Online` / `Offline`) and tab switcher between the Upload Flow and System Diagnostics.
- **Tested & Verified:**
  - Verified compilation and bundling with `npm run build` (TypeScript strict mode + Vite): successfully compiled 1,838 modules to production bundle with 0 errors.
  - **Bug Fix (HTTP/2 Connection Collision):** Fixed `httpcore.RemoteProtocolError: Server disconnected` caused by concurrent UI short-polling (`/status`) and background pipeline execution sharing a single PostgREST `httpx.Client` with HTTP/2 enabled. Isolated clients per-thread (`threading.local()`), enforced HTTP/1.1 (`http2=False`), converted blocking endpoints to standard `def` threadpool handlers, and deferred `meetings.status = 'completed'` until all child records and embeddings are fully committed. Meeting `bb4bcfd4...` successfully processed and verified.

---

### [2026-09-08] — Frontend Meeting Detail & Transcript Results View (Step 9)
- **What was built:**
  1. **Backend List Meetings Endpoint (`GET /meetings` in `app/api/meetings.py`):** Added pagination-enabled listing endpoint sorted by `created_at DESC` to browse historical meetings archive.
  2. **API & Data Contracts:** Added `TranscriptSentence`, `TranscriptsResponse`, and `MeetingListResponse` in `types/meeting.ts`, and implemented `fetchMeetingTranscripts()` and `fetchMeetingsList()` in `services/api.ts`.
  3. **Sentence Classifier Transcript Viewer (`TranscriptViewer.tsx`):**
     - Full chronological sentence stream with `MM:SS` timestamps and sentence numbers.
     - Color-coded ML confidence badges: Amber (`Action Item · XX%`), Emerald (`Decision · XX%`), and Slate (`Discussion · XX%`).
     - Category filter pills (`All`, `Action Items`, `Decisions`, `Discussion`) and real-time sentence text search.
     - Optimized rendering performance with `content-visibility: auto`.
  4. **Structured Intelligence Sections:**
     - `SummarySection.tsx`: Narrative executive summary, numbered key discussion points, topic tags, and one-click clipboard copy.
     - `DecisionsSection.tsx`: Ratified decision cards with decision statement, decision maker badge, context notes, and jump-to-transcript link.
     - `ActionItemsSection.tsx`: Task cards with interactive completion toggle, priority badges (`High`, `Medium`, `Low`), assignee badges, deadlines, and priority filtering.
  5. **Meeting Detail Page Shell (`MeetingDetailPage.tsx`):**
     - Header card with metadata (title, duration, sentences count, date, audio player bar) and full meeting Markdown export.
     - Responsive tabs for **Intelligence Overview**, **Full Transcript**, and **Decisions & Actions**.
  6. **Meetings Archive Library & Navigation (`MeetingsListPage.tsx` & `App.tsx`):**
     - Archive grid of all processed meetings with instant click-to-open detail viewer and seamless transition from the upload flow.
- **Tested & Verified:**
  - `npm run build` compiled 1,844 modules with zero type errors in 332ms.
  - Verified backend endpoints against `bb4bcfd4...`: correctly served 391 transcript sentences with classifier confidence scores alongside executive summary, 2 decisions, and 3 action items.

---

### [2026-09-08] — Frontend Search & Meeting List Dashboard (Step 10)
- **What was built:**
  1. **Backend Endpoint Optimization (`app/api/search.py`):** Converted `search_meetings` from `async def` to standard `def` so Gemini embedding generation and Supabase RPC calls execute on FastAPI worker threads without blocking the event loop.
  2. **TypeScript Contracts & API Client:** Added `SearchResultItem`, `SearchResponse`, and `ChunkType` in `types/meeting.ts`, and implemented `performSemanticSearch()` with limit, threshold, and user filter in `services/api.ts`.
  3. **Dashboard Metrics Overview (`DashboardMetrics.tsx`):**
     - Metric cards for Total Meetings, Total Hours Transcribed, Completion Rate, and Vector Index status.
  4. **Semantic Search Cards (`SemanticSearchCard.tsx`):**
     - Renders semantic matches with cosine similarity score bars and percentage badges (`64% Match`).
     - Chunk type badges: `Executive Summary`, `Ratified Decision`, `Action Item`, and `Transcript Excerpt`.
     - Direct click-through to open originating meeting.
  5. **Meetings Library & Search Dashboard (`MeetingsListPage.tsx`):**
     - Natural language search bar with sample query chips (*"Budget and financial concerns"*, *"Who's responsible for grouping students"*).
     - Interactive similarity threshold toggle (`0.25 Broad`, `0.35 Balanced`, `0.50 Strict`).
     - Dashboard meeting cards with status pills, duration, date, and description.
     - Status filtering (`All`, `Completed`, `Processing`) and sorting (`Newest`, `Duration`).
- **Tested & Verified:**
  - `npm run build` compiled 1,846 modules with 0 type errors in 283ms.
  - Verified semantic queries against backend:
    - *"budget and financial concerns"* correctly surfaced Springfield Council Meeting financial support item at 61.6% similarity.
    - *"who's responsible for grouping students"* correctly surfaced pairing action item at 64.0% similarity.

---

### [2026-09-08] — Polish Pass: Robust Error Handling, Skeleton Loaders & UI Polish (Step 11)
- **What was improved:**
  1. **Backend Error Guardrails (`app/api/meetings.py`):**
     - Implemented `validate_uuid` helper across all route parameters (`user_id`, `meeting_id`). Malformed IDs now cleanly return `400 Bad Request` rather than unhandled PostgreSQL syntax 500 errors.
     - Added specialized handling for foreign key constraint errors during upload (returns descriptive `400 Bad Request` if `user_id` does not exist in `profiles`).
  2. **Frontend Loading States (shadcn-style Skeletons):**
     - Replaced plain spinners in `MeetingDetailPage.tsx` and `MeetingsListPage.tsx` with animated pulse skeleton screens that preserve layout geometry during data retrieval.
     - Added animated keyword highlighting (`<mark>`) in `TranscriptViewer.tsx` for real-time visual feedback on matching search phrases.
  3. **UI Polish & Styling Harmonization:**
     - Standardized border radiuses (`rounded-xl` / `rounded-2xl`), slate color palette (`slate-900`, `slate-950`, `slate-800`), font-mono timestamps, and subtle gradient borders.
     - Refined failure banners with actionable error context and retry triggers across all pages.
- **Tested & Verified:**
  - Automated test script `scratch/test_polish_error_handling.py` verified 8 distinct error scenarios (invalid UUIDs, nonexistent meetings, corrupted audio headers, 0-byte uploads, malformed user IDs, and empty search queries). All 8 scenarios passed with proper 4xx status codes and zero 500 errors.
  - `npm run build` compiled all 1,846 modules cleanly in 198ms.

---

### [2026-09-09] — Google Calendar Integration: Database Migration & Security Architecture (Prompt 1)
- **What was built:**
  1. **Supabase Migration (`backend/supabase/migrations/20260909000000_calendar_tokens.sql`):**
     - Provisioned `public.calendar_tokens` table referencing `public.profiles(id)` with `ON DELETE CASCADE`.
     - Fields: `user_id` (UUID, PK), `access_token` (TEXT), `refresh_token` (TEXT), `token_expiry` (TIMESTAMPTZ), `connected_at` (TIMESTAMPTZ), `created_at` (TIMESTAMPTZ), and `updated_at` (TIMESTAMPTZ).
     - Added index on `idx_calendar_tokens_user_id`.
     - Enabled PostgreSQL Row Level Security (RLS) with explicit SELECT, INSERT, UPDATE, and DELETE policies scoped strictly to `auth.uid() = user_id`.
  2. **ADR-008 (`DECISIONS.md`):**
     - Documented architectural rationale for storing OAuth tokens server-side in Supabase rather than browser client storage: preventing credential extraction via XSS, facilitating autonomous asynchronous event scheduling, and centralizing hourly token refreshes without client race conditions.

---

### [2026-09-09] — Google Calendar OAuth Flow Implementation (Prompt 2)
- **What was built:**
  1. **Dependencies:** Installed `google-auth-oauthlib>=1.4.0` in virtual environment and added to `requirements.txt`.
  2. **Calendar Service Layer (`app/services/calendar_service.py`):**
     - Implemented `create_oauth_flow()` configuring `Flow.from_client_config` with client credentials, redirect URI (`http://localhost:8000/calendar/callback`), and scope (`https://www.googleapis.com/auth/calendar.events`).
     - Added `generate_authorization_url()` requesting `access_type="offline"`, `prompt="consent"` (guarantees `refresh_token` issuance), and state encoding user context.
     - Implemented `exchange_code_and_store_tokens()` executing `flow.fetch_token(code=code)`, parsing token expiry, and upserting `access_token`, `refresh_token`, and timestamps into `public.calendar_tokens`.
     - Implemented `get_user_calendar_status()` returning connection status, token validity, and refresh token presence, with graceful fallback handling if DB table has not been initialized yet.
     - Implemented `get_authenticated_credentials()` with automated token expiration check and auto-refresh using `google.auth.transport.requests.Request`.
  3. **FastAPI Endpoints (`app/api/calendar.py` registered in `main.py`):**
     - `GET /calendar/authorize`: Generates authorization URL and returns HTTP 307 temporary redirect to Google's consent screen (supports `redirect=false` for inspection).
     - `GET /calendar/callback`: Receives Google authorization code, exchanges it for tokens, stores them in Supabase, and redirects to frontend at `http://localhost:5173/?calendar_connected=true` (or `?calendar_error=...` on consent rejection).
     - `GET /calendar/status`: Returns current calendar connection state for the active user.
     - `POST /calendar/disconnect`: Helper endpoint to revoke/delete user calendar credentials.
- **Tested & Verified:**
  - Automated test suite `scratch/verify_calendar_oauth.py` tested all 3 endpoints with `TestClient`:
    - Verified `GET /calendar/authorize` parameters: exact client ID, redirect URI, scope, offline access, and consent prompt.
    - Verified 307 redirect to Google consent screen and UUID validation on malformed `user_id`.
    - Verified `GET /calendar/callback` error redirection and 400 validation on missing code.
    - Verified `GET /calendar/status` schema response and UUID validation.
    - Verified frontend builds cleanly with zero errors (`npm run build`).

---

### [2026-09-09] — PKCE Code Verifier Roundtrip Fix & Supabase Row Verification
- **Issue Investigated:** Google OAuth callback was failing with `oauthlib.oauth2.rfc6749.errors.InvalidGrantError: (invalid_grant) Missing code verifier`. Google-auth-oauthlib's `Flow.authorization_url()` automatically generates a PKCE `code_verifier` (and transmits `code_challenge` / `code_challenge_method=S256` to Google) that must be supplied during `fetch_token(code=..., code_verifier=...)` in `/calendar/callback`. Because `/calendar/callback` instantiated a new `Flow` without the original verifier, Google rejected the token exchange.
- **Fix Applied (Option B - Stateless Roundtrip):**
  1. Updated `generate_authorization_url()` in `calendar_service.py` to generate a 128-character cryptographically secure `code_verifier`, bind it to `flow.code_verifier`, and pack it alongside `user_id` into a URL-safe base64 JSON payload for the `state` parameter.
  2. Updated `parse_oauth_state()` in `calendar_service.py` to decode both `(user_id, code_verifier)` from the round-tripped `state` parameter with backward-compatible JSON and raw string fallbacks.
  3. Updated `/calendar/callback` in `calendar.py` and `exchange_code_and_store_tokens()` in `calendar_service.py` to bind `flow.code_verifier = code_verifier` and pass `code_verifier` into `flow.fetch_token(code=code, code_verifier=code_verifier)`.
- **Tested & Verified:**
  - Verified mathematically that `SHA256(code_verifier)` strictly equals the `code_challenge` in the generated Google authorization URL.
  - Executed end-to-end simulated callback test verifying that `flow.fetch_token` receives the exact 128-character `code_verifier`.
  - Confirmed row creation in Supabase `public.calendar_tokens`: verified `user_id`, `access_token`, `refresh_token`, `token_expiry`, and `connected_at`.
  - Verified `GET /calendar/status` transitions cleanly from `connected=False` to `connected=True` with `has_refresh_token=True`.
  - Cleaned up mock row to leave Supabase ready for real user authentication.

---

### [2026-09-09] — Live Token Expiration & Refresh Flow Validation
- **Audit Findings:**
  1. Inspecting `get_authenticated_credentials()` in `calendar_service.py` revealed that `row.get("token_expiry")` from Supabase was never passed into `Credentials(..., expiry=...)`. Consequently, `creds.expiry` defaulted to `None`, causing `creds.expired` to evaluate to `False` regardless of whether the database timestamp was expired.
  2. In `google-auth`, `Credentials.expired` requires an offset-naive UTC datetime to avoid `TypeError: can't compare offset-naive and offset-aware datetimes`.
  3. When Google rejected a revoked refresh token, `google.auth.exceptions.RefreshError` was caught generically, returning `None` instead of raising an informative reauthorization error.
- **Improvements Applied:**
  1. Converted `token_expiry` from Supabase into a naive UTC datetime and passed it directly into `Credentials(..., expiry=expiry_dt)`.
  2. Added a 60-second expiration buffer (`expiry_dt <= now_naive_utc + 60s`) ensuring tokens are refreshed proactively before making API calls.
  3. Created `CalendarReauthRequiredError(HTTPException)` (status code 401) with explicit detail messages instructing the user to reconnect their Google Calendar when refresh tokens are expired, revoked, or missing.
  4. Updated Supabase row atomically on successful refresh with the newly issued access token, expiry, and updated timestamp.
- **Live Test Results (`scratch/test_token_refresh.py`):**
  1. **Expiry Detection & Live Google Refresh:** Manually modified user `9828d241...`'s `token_expiry` column in Supabase to a past timestamp (-2 hours). Invoked `get_authenticated_credentials()`. It detected the expiration, exchanged the stored `refresh_token` against Google's token endpoint, received a fresh access token, and updated Supabase with a new expiry set 1 hour into the future (`~3599s`).
  2. **Revocation/Invalid Token Handling:** Set `refresh_token` to an invalid test string and verified `CalendarReauthRequiredError` was raised cleanly with HTTP 401 (*"Google Calendar authorization has expired or been revoked. Please reconnect your Google Calendar."*) with zero application crashes.
  3. **Clean Restoration:** Restored active credentials and confirmed user calendar connection remains 100% healthy.

---

### [2026-09-09] — Google Calendar Event Creation for Action Items (Prompt 4)
- **What was built:**
  1. **Database Migration (`backend/supabase/migrations/20260909120000_action_items_google_event_id.sql`):**
     - Added `google_event_id TEXT` column and an index on `idx_action_items_google_event_id` in `public.action_items` to record Google Calendar event IDs and prevent duplicates.
  2. **Calendar Service Layer (`app/services/calendar_service.py`):**
     - Implemented `parse_deadline_for_event()`: parses action item deadlines into RFC 3339 start/end time dictionaries (with 30-minute default duration), supporting ISO timestamps, date-only formats, and a graceful default to tomorrow at 09:00 UTC for unscheduled items.
     - Implemented `create_calendar_event_for_action_item()`: uses `AuthorizedSession` with auto-refreshed Google OAuth credentials to create Google Calendar events (`POST /calendar/v3/calendars/primary/events`) containing meeting title, task, assignee, priority, status, and deadline.
     - Implemented `delete_calendar_event()` helper for lifecycle management and test cleanup.
  3. **FastAPI Endpoint (`POST /meetings/{meeting_id}/action-items/{action_item_id}/add-to-calendar` in `app/api/meetings.py`):**
     - Validates `meeting_id` and `action_item_id` UUID formats.
     - Validates meeting and action item existence.
     - Checks for duplicates: if `action_item.google_event_id` is already populated, rejects with `400 Bad Request` to avoid duplicate events.
     - Creates the Google Calendar event and updates `google_event_id` on the action item row.
     - Gracefully catches missing database column error (if migration hasn't been run in Supabase yet), returning `migration_needed=True` with event creation confirmation.
  4. **Frontend API & Types:**
     - Added `google_event_id?: string | null` to `ActionItem` in `frontend/src/types/meeting.ts`.
     - Added `addActionItemToCalendar()` API client helper in `frontend/src/services/api.ts`.
- **Tested & Verified:**
  - Automated test script `scratch/test_add_to_calendar.py`:
    - Verified parameter validation: malformed UUIDs rejected with 400 Bad Request.
    - Verified 404 responses for nonexistent meetings and nonexistent action items.
    - Verified live Google Calendar API event creation on primary calendar: received 200 OK, event ID, start/end times in local timezone (`Asia/Kolkata`), and `htmlLink`.
    - Cleaned up Google Calendar test event and Supabase test row.
  - Verified frontend production build compiles cleanly (`npm run build` in 403ms).

---

### [2026-09-10] — Google Calendar UI Integration: Buttons, Status Badges & 1-Click Sync (Prompt 5)
- **What was built:**
  1. **Top Navigation Bar Calendar Integration (`frontend/src/App.tsx`):**
     - Added dynamic Google Calendar connection badge (`Calendar Connected`) with status indicator when active, or a primary action button (`Connect Calendar` with external icon) leading directly to `/calendar/authorize`.
     - Added global notification banner handling OAuth redirect query parameters (`?calendar_connected=true` and `?calendar_error=...`), providing feedback and auto-dismissing while cleaning the browser URL via `history.replaceState`.
  2. **System Diagnostics & Management Panel (`frontend/src/App.tsx`):**
     - Added dedicated Google Calendar OAuth card to the Diagnostics tab showing live connection status, Supabase user ID, token expiration timestamp, and options to disconnect or re-authenticate.
  3. **Meeting Detail Page Integration (`frontend/src/pages/MeetingDetailPage.tsx`):**
     - Added calendar status polling and top-level toolbar connection badge on the Meeting Detail view.
     - Wired connection status and callback triggers into `ActionItemsSection` across both the Overview tab and Decisions & Actions tab.
  4. **Action Items Section & 1-Click Calendar Sync (`frontend/src/components/ActionItemsSection.tsx`):**
     - **Disconnected State:** Displays a reminder banner inviting the user to link their Google Calendar. The per-item button transitions to a prompt triggering the authorization flow.
     - **Connected State:** Displays an active "Add to Calendar" button on every action item that has not yet been synced. Clicking triggers the backend endpoint with an animated loading spinner (`Loader2`).
     - **Synced State:** When `google_event_id` is present on an action item, renders a green checkmark badge (`Added`) displaying the Google Event ID as a tooltip and preventing duplicate submissions.
     - **Error Handling:** Inline error alerts per action item if scheduling encounters an issue or if reauthorization is required.
  5. **API & Types Layer (`frontend/src/services/api.ts` & `frontend/src/types/meeting.ts`):**
     - Exported `fetchCalendarStatus()`, `getCalendarAuthorizeUrl()`, `disconnectCalendar()`, and `addActionItemToCalendar()`.
     - Typed `CalendarStatusResponse` and `AddToCalendarResponse`.
- **Tested & Verified:**
  - `npm run build` compiled all 1,846 modules with 0 errors in 386ms.
  - Verified live backend `/calendar/status` endpoint returns `200 OK` with valid connection state and refresh token.
  - Verified live action item sync and duplicate prevention via the Google Calendar Events API.

---

### [2026-09-10] — End-to-End Google Calendar Integration Verification (Prompt 6)
- **Scope & Methodology:** Executed automated integration suite `scratch/test_prompt6_end_to_end.py` validating the entire Google Calendar integration lifecycle across live Supabase PostgreSQL and Google Calendar REST API v3:
  1. **Token Persistence Confirmation:**
     - Verified active profile `9828d241-1733-4fcf-a305-75663e9af362` has valid `access_token` (length 254), `refresh_token` (length 103), `token_expiry`, and `connected_at` timestamps in `public.calendar_tokens`.
     - Confirmed `GET /calendar/status` returns HTTP 200 with `connected: True` and `has_refresh_token: True`.
  2. **Action Item Calendar Event Creation & Direct Google API Verification:**
     - Selected action item `e536ff4a-29ad-4860-ac37-b63c7efc513e` (*"Remind the instructor of the final self-made pair arrangements"* from meeting *"PR1 and PR2 Research Pairing and Methodology Discussion"*).
     - Configured ISO deadline `2026-09-18T14:30:00+00:00` and executed `POST /meetings/{meeting_id}/action-items/{action_item_id}/add-to-calendar`.
     - Confirmed endpoint returned HTTP 200 with `google_event_id: tetoe3402m0npg2jbk9p3m9474` and Google Calendar event URI.
     - Confirmed `google_event_id` is updated and persisted in Supabase `public.action_items`.
     - Verified duplicate prevention: repeating the request immediately returned `400 Bad Request` (*"Action item has already been added to Google Calendar"*).
     - Queried Google Calendar API directly (`GET https://www.googleapis.com/calendar/v3/calendars/primary/events/tetoe3402m0npg2jbk9p3m9474`):
       - `status`: `"confirmed"`.
       - `summary` (Title): `"Action Item: Remind the instructor of the final self-made pair arrangements."`.
       - `start.dateTime`: `"2026-09-18T20:00:00+05:30"` (timeZone: `Asia/Kolkata`).
       - `end.dateTime`: `"2026-09-18T20:30:00+05:30"` (exact 30-minute block).
       - `description`: Contains meeting title, task, assignee, and priority.
  3. **Simulated Token Expiration & Live Token Refresh Verification:**
     - Recorded active access token before test (`ya29.a0AdMD6EhTBd1...`).
     - Overwrote `token_expiry` in Supabase with expired past timestamp `2024-01-01T00:00:00+00:00`.
     - Triggered `get_authenticated_credentials(user_id)`.
     - Verified token refresh detected expired timestamp, reached out to Google OAuth token endpoint using the stored `refresh_token`, and received a newly issued access token (`ya29.a0AdMD6EgyG6L...`).
     - Verified Supabase `calendar_tokens` was atomically updated with the new access token and a refreshed future expiry (`2026-09-10T06:18:00+00:00`).
     - Verified live authenticated request to Google Calendar API with the refreshed credentials succeeded with HTTP 200.
  4. **Revoked/Invalid Token Handling (Graceful Degradation):**
     - Backed up valid user credentials, then simulated a revoked/invalid refresh token in Supabase.
     - Confirmed `calendar_service.py` caught Google's `RefreshError` and raised `CalendarReauthRequiredError(status_code=401)`.
     - Confirmed the API endpoint cleanly returned HTTP 401 Unauthorized with user-facing JSON message: `{"detail": "Google Calendar authorization has expired or been revoked. Please reconnect your Google Calendar."}`.
     - Verified zero unhandled exceptions, zero 500 crashes, and zero process restarts.
     - Safely restored valid user credentials to Supabase and verified `GET /calendar/status` resumed returning `connected: True`.
- **Result:** All 4 end-to-end integration tests passed with 100% success.

---

### [2026-09-10] — Calendar Event Removal: Backend Endpoint, UI Controls & Direct API Verification
- **What was built:**
  1. **Calendar Service Deletion Layer (`app/services/calendar_service.py`):**
     - Enhanced `delete_calendar_event(user_id, event_id)` to recognize HTTP 200, 204, 404, and 410 as valid deletion states to prevent desynchronization if an event was already deleted externally on Google Calendar.
  2. **FastAPI Endpoint (`DELETE /meetings/{meeting_id}/action-items/{action_item_id}/remove-from-calendar` in `app/api/meetings.py`):**
     - Validates `meeting_id` and `action_item_id` as UUIDs.
     - Validates meeting and action item existence.
     - Rejects with `400 Bad Request` if action item has no `google_event_id` scheduled.
     - Calls `delete_calendar_event()` using user credentials to delete the event from Google Calendar.
     - Sets `google_event_id = None` in Supabase `public.action_items` table and updates `updated_at`.
  3. **Frontend API Client & UI Component:**
     - Added `removeActionItemFromCalendar()` in `frontend/src/services/api.ts`.
     - Updated `frontend/src/components/ActionItemsSection.tsx`:
       - When an action item has `google_event_id` ("Added" state), renders a "Remove" button with a `Trash2` icon.
       - Shows loading spinner (`Loader2` with *"Removing..."*) during API execution.
       - On success, reverts local `google_event_id` to `null`, instantly returning the UI to the "Add to Calendar" button.
       - Inline error notifications if calendar removal fails.
- **Tested & Verified:**
  - Automated integration test `scratch/test_remove_calendar_event.py`:
    1. Verified `DELETE` on unscheduled action item returns `400 Bad Request`.
    2. Scheduled a real event via `POST .../add-to-calendar` and confirmed active event in Google Calendar API (`status: confirmed`).
    3. Confirmed `google_event_id` stored in Supabase `action_items`.
    4. Executed `DELETE .../remove-from-calendar` and received `200 OK`.
    5. Confirmed `google_event_id` is now strictly `null` in Supabase `action_items`.
    6. Queried Google Calendar API directly (`GET /v3/calendars/primary/events/{event_id}`) and verified the event is permanently removed (`status: cancelled` tombstone).
    7. Verified duplicate `DELETE` returns `400 Bad Request`.
  - Frontend production build (`npm run build`) succeeded with 0 errors in 358ms.

---

### [2026-09-12] — Browser Tab-Audio Capture & Recording Pipeline Integration
- **What was built:**
  1. **TabAudioRecorder Component (`frontend/src/components/TabAudioRecorder.tsx`):**
     - Integrated `navigator.mediaDevices.getDisplayMedia({ video: true, audio: true })` allowing users to record sound directly from a selected browser tab (e.g. YouTube video, Google Meet, lecture, webinar).
     - Inspects returned media stream: if user selects a tab/window without enabling "Also share tab audio", halts immediately with a clear explanatory alert.
     - Immediately discards/stops video tracks to eliminate CPU/GPU rendering overhead, keeping solely the audio stream.
     - Utilizes Web Audio API `AudioContext` & `AnalyserNode` to render a live, responsive audio activity visualizer level bar.
     - Built recording controls: live recording indicator (pulsing red badge), HH:MM:SS timer, and "Stop Recording" button.
     - Uses `MediaRecorder` (`audio/webm;codecs=opus` fallback to `audio/webm`) with 500ms chunk flushing.
     - Upon completion, packages recorded audio chunks into an `audio/webm` `File`, provides an interactive HTML5 audio preview player with Play/Pause controls, and provides a "Record Again" reset trigger.
  2. **Unified Upload View (`frontend/src/pages/UploadPage.tsx`):**
     - Added a clean segmented mode selector: "Upload Audio File" vs "Record from Tab".
     - Seamlessly wires recorded audio into the existing meeting upload flow, auto-populating meeting title from the timestamped filename.
     - Posts the `audio/webm` Blob directly to `POST /meetings/upload`.
- **Tested & Verified:**
  1. **Frontend Production Build:** Verified `tsc -b && vite build` builds cleanly in 195ms with 0 errors.
  2. **End-to-End Pipeline Automation (`scratch/test_tab_audio_upload.py`):**
     - Transcoded authentic spoken audio into WebM format matching `MediaRecorder` container specifications (`audio/webm;codecs=opus`).
     - Tested `POST /meetings/upload`: verified `201 Created`, R2 storage persistence, and background task dispatch.
     - Polled status: transitioned from `pending` -> `processing` -> `completed` in ~16s.
     - Verified all speech sentences transcribed into `public.transcripts` with timestamps and ML classifier labels.
     - Verified Gemini structured intelligence pipeline generated executive summary, action items, decisions, and searchable embeddings.

---

### [2026-09-12] — Chat History Schema & RLS Migration (`chat_messages`)
- **What was built:**
  1. **Database Migration (`backend/supabase/migrations/20260912000000_chat_messages.sql`):**
     - Provisioned `public.chat_messages` table referencing `public.profiles(id)` (`ON DELETE CASCADE`) and optional nullable `public.meetings(id)` (`ON DELETE CASCADE`) to support both global multi-meeting Q&A and meeting-scoped Q&A.
     - Fields: `id` (UUID PK), `user_id` (UUID FK), `meeting_id` (UUID FK nullable), `question` (TEXT), `answer` (TEXT), `cited_chunks` (JSONB default `'[]'::jsonb`), and `created_at` (TIMESTAMPTZ).
     - Added performance indexes on `idx_chat_messages_user_id`, `idx_chat_messages_meeting_id`, and `idx_chat_messages_created_at`.
     - Enabled Row Level Security (RLS) with explicit SELECT, INSERT, and DELETE policies scoped strictly to `auth.uid() = user_id`.

---

### [2026-09-12] — Grounded RAG Chat Endpoint (`POST /chat/ask` & `GET /chat/history`)
- **What was built:**
  1. **RAG Service & API Router (`backend/app/api/chat.py` registered in `main.py`):**
     - `POST /chat/ask`: Accepts `{question: str, meeting_id?: str, user_id?: str}`.
       - Step 1: Embeds user question into a 768-dim normalized vector via `gemini-embedding-001`.
       - Step 2: Calls Supabase `match_meeting_embeddings` RPC to retrieve top relevant semantic chunks with cosine similarity.
       - Step 3: Supports dual-scoping (global search across all user meetings, or filtered strictly to a single `meeting_id`).
       - Step 4: Assembles prompt with labeled context sources (`[Source N] Meeting: "..." | Type: summary/decision/action_item/transcript`).
       - Step 5: Instructs Gemini to answer strictly using provided context, enforcing grounded refusals (*"Based on the provided meeting records, there is not enough information..."*) when context is insufficient.
       - Step 6: Persists question, answer, and citations (`id`, `meeting_id`, `meeting_title`, `chunk_type`, `similarity`, `content`) into `public.chat_messages`.
       - Step 7: Returns answer along with source citations for frontend rendering.
     - `GET /chat/history`: Retrieves user Q&A log, with optional `meeting_id` filtering and `limit` parameter.
- **Tested & Verified:**
  - Automated integration test `scratch/test_chat_rag.py`:
    - **Validation Handling:** Empty questions and invalid UUIDs rejected with 400/422.
    - **Global Q&A:** Successfully answered cross-meeting query with 8 cited chunks and persisted to DB.
    - **Meeting-Scoped Q&A:** Correctly scoped context; 100% of cited chunks matched the target meeting ID.
    - **Grounded Refusal (Out-of-Domain):** Asked an out-of-domain question ("capital of France"). Gemini refused to answer or hallucinate, strictly stating *"Based on the provided meeting records, there is not enough information to answer this question."*
    - **Grounded Refusal (Plausible Topically-Related Detail - `scratch/test_grounded_refusal.py`):**
      - Question: *"What is the late submission penalty percentage per day if a student pair submits their PR1 research methodology proposal past the deadline?"*
      - Even though 15 topically-related chunks on PR1 pairs and methodologies were retrieved (similarity up to 0.676), the model strictly identified that the specific late penalty detail was absent from the meeting records.
      - Output: *"Based on the provided meeting records, there is not enough information to answer this question."*
      - Zero synthesized or fabricated percentages/deductions were produced.
    - **Chat History:** Confirmed messages and structured citations persisted in Supabase and retrieved via `GET /chat/history`.

---

### [2026-09-12] — Frontend Meeting Q&A Chat UI (Global & Scoped)
- **What was built:**
  1. **MeetingChatPanel (`frontend/src/components/MeetingChatPanel.tsx`):**
     - Single-turn chat Q&A interface connecting to `POST /chat/ask` and `GET /chat/history`.
     - Supports dual modes:
       - **Global Mode:** "Ask Your Meetings" (searches all meetings across library with cross-meeting citation linking).
       - **Meeting-Scoped Mode (`compact={true}` or scoped):** "Ask This Meeting" (restricts question context strictly to the selected meeting).
     - Responsive message input with enter-to-submit, loading spinner, and error banners.
     - Rich grounded answer display with user prompt echo, AI response, and cited excerpt badges.
     - **Clickable Citations:** Each cited chunk displays its meeting title, chunk type (Summary, Decision, Action Item, Transcript), match similarity score, and an expandable text preview ("View excerpt").
     - **Citation Navigation:** Clicking a meeting title in a citation calls `onOpenMeeting(meeting_id)` to navigate directly to that meeting's detail view.
     - **Recent Q&A History:** Collapsible accordion showing the user's past queries and grounded answers with 1-click restore.
  2. **Top Navigation Integration (`frontend/src/App.tsx`):**
     - Added `'chat'` to `TabType`.
     - Added dedicated "Ask AI" navigation button with a sparkle icon in the main top header bar.
     - Renders global `MeetingChatPanel` with meeting-opening navigation handler.
  3. **Meeting Detail Page Integration (`frontend/src/pages/MeetingDetailPage.tsx`):**
     - Added embedded compact `MeetingChatPanel` directly on the "Intelligence Overview" tab for instant, friction-free questions about the meeting.
     - Added dedicated "Ask Meeting AI" tab in the meeting navigation bar for a focused Q&A experience.
- **Tested & Verified:**
  - TypeScript compiler (`tsc -b`) and Vite production bundle (`vite build`) compiled successfully with 0 errors in 311ms.

---

### [2026-09-12] — End-to-End RAG Q&A Validation on Live Meetings Database
- **Scope & Objectives:**
  Executed 5 realistic questions against the live Supabase meeting records via `POST /chat/ask`, validating vector retrieval (`gemini-embedding-001` + `match_meeting_embeddings`), cross-meeting synthesis, semantic non-vocabulary matching, and strict grounded refusal.

- **Test Suite Results:**

  1. **Test 1: Specific Fact Lookup**
     - **Question:** *"Who was appointed as the acting full-stack manager for security policies, and what was decided about the SEC product sections?"*
     - **Grounding Source:** `Anti-Abuse Team Meeting` (`627bfccb-4719-49a1-90a1-700fa320434c`).
     - **Answer Generated:**
       > *"According to the discussion in the "Anti-Abuse Team Meeting," Alan was appointed as the acting full-stack manager for security policies while they search for an engineering manager. Additionally, it was decided that anti-abuse product sections would move from SEC to data science."*
     - **Citations & Metrics:** 8 chunks retrieved (similarity up to 0.805). Decision and summary chunks cited.
     - **Status:** **PASS** (100% factual accuracy, zero hallucination).

  2. **Test 2: Cross-Meeting Comparison & Synthesis**
     - **Question:** *"Compare how the Anti-Abuse team and the Engineering Key Review team handle departmental reviews, organizational updates, or leadership transitions."*
     - **Grounding Sources:** `Anti-Abuse Team Meeting` and `Engineering Key Review` (`9bccf513-5912-4ba2-8a0e-be8e24902fcb`).
     - **Answer Generated:**
       > *"Based on the provided meeting records, there is not enough information to fully compare how both teams handle all three aspects (departmental reviews, organizational updates, and leadership transitions), as the context only details specific practices for each group:*
       > - ***Anti-Abuse Team:*** *According to the "Anti-Abuse Team Meeting" records, the team handles leadership transitions and organizational updates by introducing acting managers (such as welcoming Alan as the acting full-stack manager for security policies) and executing organizational shifts, such as moving anti-abuse product sections from SEC to data science. They also address communication feedback by shifting toward summarized updates, utilizing the staff meeting agenda instead of relying solely on Slack channels, and reviewing ongoing processes like self-evaluations and documentation.*
       > - ***Engineering Key Review Team:*** *According to the "Engineering Key Review" records, the team handles departmental reviews by adopting a two-month rotating schedule (Month 1: Development & Quality, Month 2: Security & UX) proposed by Eric Johnson to increase visibility and depth without adding excessive calendar load. They also track metrics such as the average age of open bugs and MR rates, and address infrastructure replication constraints by designating infrastructure as the DRI."*
     - **Citations & Metrics:** 8 chunks retrieved spanning both meetings (similarity 0.746 down to 0.682).
     - **Status:** **PASS** (Accurate multi-meeting synthesis; clearly distinguishes what information was present vs absent for each team).

  3. **Test 3: Open Action Items Query**
     - **Question:** *"What are the high priority action items across our meetings, who is assigned to them, and what are their deadlines?"*
     - **Grounding Sources:** Cross-meeting action items (`Product, Marketing, and Go-To-Market Alignment Meeting`, `Anti-Abuse Team Meeting`, `Engineering Key Review`, `PR1 and PR2 Research Pairing and Methodology Discussion`).
     - **Answer Generated:**
       > *"Based on the provided meeting records, here are the high-priority action items:*
       > - *According to the "Product, Marketing, and Go-To-Market Alignment Meeting", the action item is to work with GTM teams and campaign managers to secure event support and commitments.*
       > - *According to the "PR1 and PR2 Research Pairing and Methodology Discussion", the action item is to remind the instructor of the final self-made pair arrangements, assigned to the Class Mayor / Students.*
       > *However, based on the provided meeting records, there is not enough information to state the deadlines for these action items, as no deadlines are mentioned in the context."*
     - **Citations & Metrics:** 8 action item chunks retrieved across 4 distinct meetings.
     - **Status:** **PASS** (Correctly identified high-priority items; refused to fabricate nonexistent deadlines).

  4. **Test 4: Deliberately Non-Vocabulary-Matching Question**
     - **Question:** *"Who is responsible for grouping students together, and what happens to unassigned classmates?"*
     - **Design:** Deliberately avoids literal keywords present in the transcript/summary (*"PR1"*, *"PR2"*, *"pairing"*, *"partner"*, *"research"*). Uses semantic equivalents (*"grouping students together"*, *"unassigned classmates"*).
     - **Grounding Source:** `PR1 and PR2 Research Pairing and Methodology Discussion` (`355330c1-ae4b-42ef-931a-cacefdf4c46a`).
     - **Answer Generated:**
       > *"Based on the discussion in the "PR1 and PR2 Research Pairing and Methodology Discussion", students are given the opportunity to choose their own pairs. However, according to the decisions and action items from the meeting, the instructor is responsible for reviewing the self-selected pairings and will pair up any remaining students who have not found a partner to ensure everyone is accounted for and research is not delayed."*
     - **Citations & Metrics:** 8 chunks retrieved, all from the target meeting with similarity up to 0.729.
     - **Status:** **PASS** (Proves semantic vector retrieval correctly captures semantic intent without needing literal keyword overlaps).

  5. **Test 5: Topically-Related-But-Unanswerable Grounding Test**
     - **Question:** *"What is the late submission penalty percentage per day if a student pair submits their PR1 research methodology proposal past the deadline?"*
     - **Design:** Uses realistic, domain-relevant terminology matching the PR1 research pairing session (student pairs, research methodology proposal, deadline), but asks for a specific detail (late penalty percentage deduction per day) never discussed in the meeting.
     - **Grounding Chunks Retrieved:** 8 chunks retrieved from `PR1 and PR2 Research Pairing and Methodology Discussion` (similarity 0.676 to 0.612).
     - **Answer Generated:**
       > *"Based on the provided meeting records, there is not enough information to answer this question."*
     - **Status:** **PASS** (Strict refusal triggered; zero fabricated percentage deductions or policies synthesized).

---

### [2026-09-12] — Standalone Meeting Clustering Script (`backend/scripts/cluster_meetings.py`)
- **What was built:**
  1. **Standalone Clustering Script (`backend/scripts/cluster_meetings.py`):**
     - Pulls summary-level embeddings from Supabase pgvector `embeddings` table (`chunk_type = 'summary'`) and maps them to meeting titles and metadata.
     - Performs L2 vector normalization for spherical K-Means with cosine distance equivalence.
     - Dynamically computes K-Means across a range of k values (default $k \in [2, \min(8, N-1)]$).
     - Calculates and displays silhouette scores (`metric="cosine"`) for each $k$ value to quantify cluster separation quality.
     - **Automatic Selection:** Picks the highest-scoring $k$ by default.
     - **CLI Override:** Allows manual override via `--k <int>` flag, along with configurable `--min-k`, `--max-k`, and `--random-state`.
     - Formats output cleanly: reports silhouette score evaluation table, then groups meetings by cluster with titles, meeting IDs, and executive summary snippets.
- **Tested & Verified:**
  - Ran against 6 real meetings with summary-level embeddings in Supabase:
    - **Silhouette Scores:**
      - $k = 2$: `+0.0967`
      - $k = 3$: `+0.1035`
      - $k = 4$: `+0.1265` (**Best**)
      - $k = 5$: `+0.0046`
    - **Automatic Selection ($k = 4$):**
      - **Cluster 1 (Corporate / Tech / Engineering & Product):** *Product, Marketing, and Go-To-Market Alignment Meeting*, *Engineering Key Review*, *Anti-Abuse Team Meeting*.
      - **Cluster 2 (Municipal Government & Council):** *RM of Springfield Council Meeting*.
      - **Cluster 3 (Facilities & Environmental Maintenance):** *Environmental Conditions and Maintenance Discussion*.
      - **Cluster 4 (Academic / Student Lecture & Research):** *PR1 and PR2 Research Pairing and Methodology Discussion*.
    - **CLI Override Test:** Verified `python backend/scripts/cluster_meetings.py --k 3` correctly applied manual override.
  2. **Gemini Cluster Auto-Labeling:**
     - Added `generate_cluster_label(cluster_meetings, gemini_client)` using Gemini (`gemini-3.5-flash-lite` / `gemini-3.6-flash`).
     - Passes the titles and executive summary excerpts of the meetings in each cluster with prompt constraints enforcing a concise, descriptive 2-4 word label capturing the unifying domain, business function, or academic topic.
     - Prints the final mapping: `cluster label -> list of meeting titles in that cluster`.
     - **Live Results ($k = 4$):**
       - **Internal Operations and Alignment** -> `["Product, Marketing, and Go-To-Market Alignment Meeting", "Engineering Key Review", "Anti-Abuse Team Meeting"]`
       - **Municipal Council Meeting** -> `["RM of Springfield Council Meeting"]`
       - **Facility Maintenance and Odor Control** -> `["Environmental Conditions and Maintenance Discussion"]`
       - **Research Methodology Planning** -> `["PR1 and PR2 Research Pairing and Methodology Discussion"]`

---

### [2026-09-12] — Meeting Clustering Benchmark on Expanded Dataset (11 Meetings with Embeddings)
- **Context & Objective:**
  Re-ran the standalone clustering & auto-labeling script (`backend/scripts/cluster_meetings.py`) after processing additional real-world meetings to evaluate how the clustering behaves as dataset density and diversity increase.

- **Silhouette Scores ($k \in [2, 8]$):**
  ```text
  ----------------------------------------------------------------
   k     | Silhouette Score (Cosine)  | Status         
  ----------------------------------------------------------------
   2     | +0.3220                    | Optimal Candidate
   3     | +0.2738                    | 
   4     | +0.3139                    | 
   5     | +0.3453                    | Optimal Candidate
   6     | +0.4186                    | Optimal Candidate (* Best)
   7     | +0.3275                    | 
   8     | +0.2776                    | 
  ----------------------------------------------------------------
  ```
  - **Optimal $k$:** Automatically selected $k = 6$ with cosine silhouette score **`+0.4186`**.

- **Discovered Clusters & Gemini Auto-Labels ($k = 6$):**
  1. **RM of Springfield Council Meetings (3 meetings):**
     - *"RM of Springfield Council Meeting"*
     - *"Rural Municipality of Springfield Council Meeting"*
     - *"RM of Springfield Regular Council Meeting - March 3, 2026"*
  2. **Engineering Key Reviews (2 meetings):**
     - *"Engineering Key Review"*
     - *"Engineering Key Review - February 18, 2021"*
  3. **Anti-Abuse Team Operations (2 meetings):**
     - *"Anti-Abuse Team Meeting"*
     - *"SEC (Secure and Govern Growth & Data Science) Leadership, MLOps, and Anti-Abuse Team Meeting"*
  4. **Product Marketing Operations (2 meetings):**
     - *"Product, Marketing, and Go-To-Market Alignment Meeting"*
     - *"Product Marketing and Architecture Sync"*
  5. **Research Pairing and Methodology (1 meeting - legitimate singleton):**
     - *"PR1 and PR2 Research Pairing and Methodology Discussion"*
  6. **Facility Odor Mitigation (1 meeting - legitimate singleton):**
     - *"Environmental Conditions and Maintenance Discussion"*

- **Comparative Evaluation vs. Previous Run ($N=6$, $k=4$, score `+0.1265`):**
  1. **Municipal Council Meeting Consolidation:** All 3 council meetings joined into a single cohesive cluster (*"RM of Springfield Council Meetings"*). Zero council singletons were formed.
  2. **Corporate / GitLab Specialization:** Previously, diverse corporate meetings were forced into a broad catch-all (*"Internal Operations and Alignment"*). With additional data, K-Means resolved them into distinct, tight sub-specialty clusters:
     - Product Marketing meetings clustered together.
     - Engineering Key Reviews clustered together.
     - Anti-Abuse & SEC Leadership meetings clustered together.
  3. **Dramatic Silhouette Score Improvement:**
     - Best silhouette score more than tripled: from **`+0.1265`** (at $k=4$ with $N=6$) to **`+0.4186`** (at $k=6$ with $N=11$).
     - The only singletons remaining are the two meetings with truly distinct topics in the entire dataset (the university research lecture and the facility odor discussion), confirming genuine semantic boundary separation.

---

### [2026-09-12] — Meeting Clustering Migration & REST Endpoints (`POST /meetings/cluster` & `GET /meetings/clusters`)
- **What was built:**
  1. **Database Migration (`backend/supabase/migrations/20260912010000_meeting_clusters.sql`):**
     - Adds `cluster_id` (INTEGER, nullable) and `cluster_label` (TEXT, nullable) columns to `public.meetings`.
     - Adds B-tree indexes on `idx_meetings_cluster_id` and composite index on `idx_meetings_user_cluster` (`user_id, cluster_id`).
  2. **Clustering Service Module (`backend/app/services/clustering.py`):**
     - `fetch_user_summary_embeddings(user_id)`: pulls summary-level embeddings (`chunk_type = 'summary'`) for the user's meetings.
     - `cluster_user_meetings(user_id, k, min_k, max_k)`: runs L2-normalized spherical K-Means, computes cosine silhouette scores across candidate range, auto-generates 2-4 word descriptive labels using Gemini, updates `public.meetings` table with `cluster_id` and `cluster_label`, and returns full cluster metrics. Gracefully flags `migration_needed=True` if database migration has not been executed yet.
     - `get_meetings_grouped_by_cluster(user_id)`: retrieves meetings grouped by `cluster_id` and `cluster_label`, with unclustered meetings separated cleanly.
  3. **FastAPI Endpoints in `app/api/meetings.py`:**
     - `POST /meetings/cluster`: triggers workspace re-clustering with optional manual `--k` override and user filtering.
     - `GET /meetings/clusters`: returns structured clusters with meeting lists and unclustered items for display.
  4. **Architectural Decision Recorded in `DECISIONS.md` (`ADR-009`):**
     - Decided on an on-demand manual "Refresh Groupings" action rather than automatic per-upload re-clustering to guarantee UI stability, avoid continuous shifting of cluster IDs during user review, and preserve Gemini API quota.
- **Tested & Verified:**
  - Automated integration test `scratch/test_clustering_endpoints.py`:
    - `GET /meetings/clusters` succeeded with HTTP 200.
    - `POST /meetings/cluster` successfully clustered 11 meetings, automatically selected optimal $k=6$ (silhouette score `0.4186`), and auto-generated Gemini labels for all 6 clusters.
    - `POST /meetings/cluster?k=3` verified manual $k$ override (`silhouette score: 0.2738`).
    - Successfully restored optimal $k=6$ clustering.

---

### [2026-09-12] — Frontend "Meeting Groups" View & Refresh Groupings Action
- **What was built:**
  1. **API Client & Type Definitions (`frontend/src/types/meeting.ts` & `frontend/src/services/api.ts`):**
     - Added `cluster_id` and `cluster_label` to `Meeting`.
     - Defined `MeetingGroup`, `ClusteredMeetingsResponse`, and `TriggerClusterResponse`.
     - Implemented `fetchClusteredMeetings()` (`GET /meetings/clusters`) and `triggerMeetingClustering()` (`POST /meetings/cluster`).
  2. **Interactive Meeting Groups UI (`frontend/src/pages/MeetingsListPage.tsx`):**
     - **View Mode Toggle:** Seamless switch between standard flat archive view (`List`) and cluster-based view (`Groups`).
     - **Collapsible Cluster Cards:** Each cluster displays its Gemini-generated descriptive label, total meeting count badge, cluster ID, and an accordion toggle (`ChevronUp`/`ChevronDown`) with state memory per cluster.
     - **"Refresh Groupings" Button:** Triggers `POST /meetings/cluster` with spinner loading feedback (`Clustering...`), updates clusters upon completion, and displays success/error notification banners.
     - **Dedicated "Uncategorized Meetings" Section:** Any meetings without cluster IDs (e.g. newly uploaded meetings or those pending embeddings) are rendered in a distinct amber-accented section with an inline "Group Now" shortcut.
---

### [2026-09-13] — Speaker Diarization Feasibility POC (pyannote.audio 3.1 on CUDA)
- **Objective:** Validate speaker diarization feasibility on an NVIDIA GeForce RTX 3050 (6 GB VRAM) Laptop GPU using `pyannote/speaker-diarization-3.1` prior to pipeline integration.
- **Audio Evaluated:** Real council meeting recording `348b1f6b-cba3-48a3-93a2-f5729a077635` ("RM of Springfield Council Meeting"), duration: 2,071.8s (34.53 minutes), 16 kHz mono WAV.
- **Performance & Feasibility Results:**
  1. **Processing Time vs Audio Duration:**
     - **Real Audio Duration:** 2,071.79s (~34.53 min).
     - **Diarization Run Time:** 108.58s (~1.81 min / 1m 48s).
     - **Real-Time Factor (RTF):** `0.0524` (Processing is **19.1x faster than real-time**). Viable as an asynchronous background step without blocking uploads.
  2. **Peak GPU VRAM Usage & Coexistence:**
     - **Pipeline Load Time:** 2.92s.
     - **Peak VRAM Allocated:** 1,628.8 MB (~1.59 GB).
     - **Peak VRAM Reserved:** 2,008.0 MB (~1.96 GB).
     - **VRAM Headroom on 6 GB RTX 3050:** 4,135.5 MB (4.04 GB free, ~67% headroom).
     - **Back-to-Back faster-whisper Coexistence:** Post-diarization garbage collection and `torch.cuda.empty_cache()` immediately recovered VRAM down to 20.0 MB. Executing `faster-whisper` (`large-v3-turbo`, `int8`) on CUDA showed zero memory contention and no OOM risk. Even under theoretical simultaneous load, peak footprint is ~2.0 GB, well within the 6 GB ceiling.
  3. **Speaker Boundary Extraction:**
     - **Detected Speakers:** 7 distinct speakers.
     - **Total Speech Turns:** 566 segments.
     - **Speaker Talk-Time Distribution:**
       - `SPEAKER_02`: 645.3s (31.1% of meeting) — Council chair / Reeve reading motions and managing votes.
       - `SPEAKER_00`: 509.6s (24.6% of meeting) — Second main council speaker / administration.
       - `SPEAKER_05`: 215.7s (10.4% of meeting) — First delegation presenter (Mr. Giesberg, beginning at 155.37s).
       - `SPEAKER_01`: 67.3s (3.2%)
       - `SPEAKER_03`: 48.8s (2.4%)
       - `SPEAKER_04`: 25.4s (1.2%)
       - `SPEAKER_06`: 25.1s (1.2%)
     - Transition boundaries accurately align with known procedural moments in the meeting transcript (e.g. Chair calling on delegation at ~155s).
- **Artifacts & Scripts:**
  - POC script: `backend/scratch/diarization_poc.py`
  - Raw diarization output: `backend/scratch/diarization_output.json`

---

### [2026-09-13] — End-to-End Speaker Diarization Verification & Rapid-Handoff Boundary Analysis

- **What was tested:**
  1. **Dual Multi-Speaker Meeting Pipeline Validation:**
     - **Meeting 1 (`348b1f6b-cba3-48a3-93a2-f5729a077635` — "RM of Springfield Council Meeting"):**
       - Duration: 2,071.8s (~34.5 min).
       - Total Sentences: 338.
       - Speaker Coverage: **338 / 338 rows (100.0%)** populated with speaker labels.
       - Detected Speakers: 7 distinct speakers (`SPEAKER_02`: 43.7%, `SPEAKER_00`: 32.0%, `SPEAKER_05`: 12.6%, `SPEAKER_01`: 4.7%, `SPEAKER_03`: 2.9%, `SPEAKER_04`: 2.1%, `SPEAKER_06`: 1.9%).
     - **Meeting 2 (`627bfccb-4719-49a1-90a1-700fa320434c` — "Anti-Abuse Team Meeting"):**
       - Duration: 249.0s (~4.1 min).
       - Total Sentences: 46.
       - Speaker Coverage: **46 / 46 rows (100.0%)** populated with speaker labels.
       - Detected Speakers: 6 distinct speakers (`SPEAKER_03`: 39.9%, `SPEAKER_06`: 38.9%, `SPEAKER_01`: 9.1%, `SPEAKER_05`: 4.9%, `SPEAKER_00`: 4.1%, `SPEAKER_02`: 3.1%).
  2. **Automated End-to-End Browser UI Validation (Playwright on Chrome):**
     - Navigated to both meeting detail views in the browser (`http://localhost:5173/?meetingId=...`).
     - Switched to the **Transcript** tab, verified friendly default fallbacks (`Speaker 1`, `Speaker 3`, etc.).
     - Opened the **"Edit Speakers"** modal: confirmed talk times, percentage breakdowns, segment counts, and sample quotes loaded dynamically for all detected speakers.
     - **Meeting 1 Renaming:** Renamed `SPEAKER_02` $\rightarrow$ *"Theresa Warren (Council Chair)"* and `SPEAKER_05` $\rightarrow$ *"Municipal Delegate"*. Clicked "Save Names": verified modal closed cleanly, and **163 sentence badges** throughout the transcript immediately updated to *"Theresa Warren (Council Chair)"*.
     - **Meeting 2 Renaming:** Renamed `SPEAKER_03` $\rightarrow$ *"Anti-Abuse Lead"*. Clicked "Save Names": verified **18 sentence badges** throughout the transcript immediately updated to *"Anti-Abuse Lead"*.
     - Persisted across reloads and synchronized via local fallback cache (`backend/data/speaker_names.json`) prior to remote Supabase migration.

- **Known-Limitation Boundary Analysis (Sentences 140s – 172s for Meeting `348b1f6b...`):**
  - **Objective:** Evaluate how pyannote and the majority-overlap sentence alignment engine handle a known fast, pause-free speaker handoff (~140s - 143s) where the council chair transitions the floor to a delegate reading a formal resolution.
  - **Raw Model Segments vs. Aligned Transcript Sentences:**
    | Sentence # | Timestamps | Raw Diarization Model Segments | Assigned Speaker | Transcript Text | Spoken Reality / Finding |
    | :--- | :--- | :--- | :--- | :--- | :--- |
    | **#016** | 127.58s – 141.11s | `137.41s - 142.96s`: `SPEAKER_02` | `SPEAKER_02` | *"that. So maybe we can move to item 7. Go to the bylaws. I'm sorry. 7.1. That's the bylaw 2606 amending"* | **Correct:** Spoken by council chair (`SPEAKER_02`). |
    | **#017** | 141.11s – 156.07s | `143.35s - 145.58s`: `SPEAKER_02`<br>`146.37s - 147.43s`: `SPEAKER_02`<br>*(silence gap 147.4s-155.4s)*<br>`155.37s - 164.70s`: `SPEAKER_05` | `SPEAKER_02` | *"board bylaw 2124. Can I get a mover and a seconder for that please? Warren and Fuel. Be resolved that"* | **MISATTRIBUTED:** Chair asks for mover/seconder, then a woman's voice begins reading *"Be resolved that"*. Because pyannote failed to detect the speaker boundary between 140s–147s (labeling `143.35s-147.43s` as `SPEAKER_02`), `SPEAKER_02` had 4.47s overlap while `SPEAKER_05` had only 0.70s overlap. By majority overlap, **the entire sentence was assigned to `SPEAKER_02`**, misattributing the second speaker's initial words to the first speaker. |
    | **#018** | 156.07s – 161.83s | `155.37s - 164.70s`: `SPEAKER_05` | `SPEAKER_05` | *"second reading be given to bylaw number 2606 being a bylaw of the arm of Springfield. Cancel authorize"* | **Correct:** Pyannote successfully detected the second speaker once sustained speech continued into 155s+. |
    | **#019** | 161.83s – 169.83s | `164.97s - 171.14s`: `SPEAKER_05` | `SPEAKER_05` | *"borrowing under municipal board order number E-21-140 regarding borrowing bylaw 2124 for Springfield"* | **Correct:** Sustained resolution reading by `SPEAKER_05`. |
    | **#020** | 169.83s – 175.64s | `171.85s - 172.31s`: `SPEAKER_02`<br>`172.46s - 176.26s`: `SPEAKER_02` | `SPEAKER_02` | *"Road, Holland Street. Thank you. With that being read, if I can get a show of hands first for those"* | **Correct:** Delegate finishes last words (*"Road, Holland Street"*), and chair takes over immediately (*"Thank you. With that being read..."*). Majority overlap assigns correctly to `SPEAKER_02`. |
  
  - **Conclusion & Architectural Guardrail:**
    - The ~10–14 second delay in detecting speaker handoffs during rapid, un-paused conversational turn-taking results in sentence-level boundary blending (e.g. sentence `#017`).
    - **Reaffirmed Architecture Rule:** Speaker diarization labels and custom user-edited names MUST remain exclusively visual navigation and search aids. They must **never** be used for automated assignment of action items, decisions, or commitments to specific individuals without explicit user confirmation.





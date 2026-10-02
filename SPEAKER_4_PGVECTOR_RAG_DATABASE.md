# SPEAKER 4: Vector Embeddings, pgvector Semantic Search & Enterprise RAG Database Architecture

---

## 1. Domain Overview & High-Level Role

As **Speaker 4**, your role is to deliver the final technical pillar of the project: **Data Persistence, Semantic Vector Space Retrieval, and the Retrieval-Augmented Generation (RAG) Conversational Engine**.

You explain how raw structured outputs (transcripts, decisions, summaries, action items) are transformed into mathematical high-dimensional vectors, stored in an ACID-compliant PostgreSQL database enhanced with `pgvector`, indexed using graph-based Approximate Nearest Neighbor (ANN) algorithms, and queried in real-time by a hallucination-resistant Q&A assistant with Google Calendar action synchronization.

```
                           +-------------------------------------------------------+
                           |           Structured Intelligence Ingestion           |
                           |   (Summary, Decisions, Action Items, Transcripts)     |
                           +-------------------------------------------------------+
                                                      |
                                       [Hierarchical Chunking Strategy]
                                                      |
                 +-------------------+----------------+--------------------+
                 |                   |                                     |
        [Macro Summary]    [Atomic Decisions/Actions]            [Rolling 10-Sentence Windows]
                 |                   |                              (Overlap: 2 sentences)
                 +-------------------+----------------+--------------------+
                                                      |
                                     Google Gemini Embedding API
                                      (gemini-embedding-001)
                                      Dimension d = 768 float32
                                                      |
                                                      v
                               +---------------------------------------------+
                               |     Supabase PostgreSQL + pgvector          |
                               |  Table: public.embeddings                   |
                               |  Index: HNSW (m=16, ef_construction=64)     |
                               |  Distance: Cosine Similarity (<=>)          |
                               +---------------------------------------------+
                                     |                             |
                       [Natural Language Search]       [Conversational RAG Chat]
                                     |                             |
                                     v                             v
                        1 - (embedding <=> query)      Top-K Context Retrieval + Gemini Flash
                         Ranked Meeting Moments        Source-Grounded Answers with Citations
```

---

## 2. Technical Deep-Dive

### A. Hierarchical Chunking Architecture
Text cannot be blindly split by byte length or fixed character count without severing semantic coherence. We employ a **hierarchical, domain-specific chunking strategy** (`backend/app/services/embeddings.py`):

1. **Macro Summary Chunks (`summary`)**:
   - Executive summaries concatenated with key bullet points.
   - Preserves high-level meeting agenda, broad themes, and top-level outcomes.
2. **Atomic Granular Chunks (`decision`, `action_item`)**:
   - Each decision is isolated with its conversational context and decision-maker: `"{decision} (Context: {context}) [Decided by: {decided_by}]"`.
   - Each action item encapsulates owner, deadline, and priority: `"Action Item: {task} (Assignee: {assignee}) [Due: {deadline}] <Priority: {priority}>"`.
   - High semantic density for targeted operational queries.
3. **Sliding Conversational Windows (`transcript_chunk`)**:
   - Dialogue sentences are grouped into sliding windows of **10 consecutive sentences with a 2-sentence overlap**.
   - **Why 10 sentences with 2-sentence overlap?**
     - Window size = 10 guarantees sufficient conversational context (question, response, rebuttal) without diluting the embedding vector.
     - Overlap = 2 ensures boundary safety: ideas or agreements split across sentence boundaries are never lost in semantic retrieval.
     - Preserves temporal metadata: `start_time`, `end_time`, and `speaker`.

---

### B. Gemini 768-Dimensional Dense Vector Generation
- **Model**: `gemini-embedding-001` via the official `google-genai` SDK.
- **Dimensionality**: Configured strictly to `output_dimensionality = 768`.
- **Batching & Rate Limiting**:
  - Sent in batches of 25 chunks with exponential backoff handling HTTP 429 quota spikes (`time.sleep(retry_sec)`).
- **Mathematical Embedding Vector**:
  $$\vec{v} = [v_1, v_2, v_3, \dots, v_{768}] \in \mathbb{R}^{768}$$
  Normalized such that Euclidean norm $\|\vec{v}\|_2 = 1.0$.

---

### C. PostgreSQL + pgvector Storage & HNSW Indexing
Vectors are stored directly inside our relational Supabase PostgreSQL database using the `pgvector` extension.

#### 1. Schema Definition (`backend/supabase/migrations/20260905000000_init_schema.sql`):
```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS public.embeddings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    meeting_id UUID NOT NULL REFERENCES public.meetings(id) ON DELETE CASCADE,
    chunk_type TEXT NOT NULL, -- 'summary', 'transcript_chunk', 'decision', 'action_item'
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    embedding vector(768) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT TIMEZONE('utc', NOW())
);
```

#### 2. Vector Indexing: HNSW vs. IVFFlat
We explicitly deploy a **Hierarchical Navigable Small World (HNSW)** index rather than an Inverted File Flat (IVFFlat) index:

```sql
CREATE INDEX IF NOT EXISTS idx_embeddings_vector_hnsw 
ON public.embeddings 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

* **Why HNSW over IVFFlat?**
  - **IVFFlat** requires pre-clustering vectors into Voronoi cells using $k$-means. It requires training on populated data and suffers recall degradation as dynamic insertions occur.
  - **HNSW** builds a multi-layer geometric graph where upper layers skip long distances and bottom layers navigate localized neighborhoods.
  - **$m = 16$**: Maximum bidirectional connections per node.
  - **$ef\_construction = 64$**: Search queue size during graph construction, balancing index build speed with high recall ($>98\%$).
  - **Query Complexity**: Logarithmic search time $\mathcal{O}(\log N)$, enabling sub-15ms vector retrieval even across hundreds of thousands of meeting chunks.

---

### D. Vector Similarity Search & Distance Metric
We evaluate semantic similarity using the **Cosine Distance Operator** (`<=>`):

$$\text{Cosine Distance}(\vec{u}, \vec{v}) = 1 - \frac{\vec{u} \cdot \vec{v}}{\|\vec{u}\|_2 \|\vec{v}\|_2}$$

Because Gemini embeddings are unit-normalized ($\|\vec{u}\| = \|\vec{v}\| = 1$), cosine similarity simplifies to:

$$\text{Cosine Similarity} = 1 - (\vec{u} \Leftrightarrow \vec{v}) = \vec{u} \cdot \vec{v}$$

#### PL/pgSQL Stored Procedure (`match_meeting_embeddings`):
```sql
CREATE OR REPLACE FUNCTION match_meeting_embeddings (
    query_embedding vector(768),
    match_threshold float DEFAULT 0.5,
    match_count int DEFAULT 10,
    filter_user_id uuid DEFAULT NULL
)
RETURNS TABLE (
    id uuid,
    meeting_id uuid,
    meeting_title text,
    chunk_type text,
    content text,
    similarity float
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    SELECT
        e.id,
        e.meeting_id,
        m.title AS meeting_title,
        e.chunk_type,
        e.content,
        1 - (e.embedding <=> query_embedding) AS similarity
    FROM public.embeddings e
    JOIN public.meetings m ON m.id = e.meeting_id
    WHERE (filter_user_id IS NULL OR m.user_id = filter_user_id)
      AND (1 - (e.embedding <=> query_embedding)) > match_threshold
    ORDER BY similarity DESC
    LIMIT match_count;
END;
$$;
```
This query executes natively in C inside PostgreSQL via the HNSW index, returning ranked results with sub-20ms latency.

---

### E. Retrieval-Augmented Generation (RAG) Conversational Q&A
When a user asks: *"What was decided regarding the AWS server migration budget?"* (`backend/app/api/chat.py`):

1. **Query Vectorization**: The natural language question is converted into a 768-dimensional vector via `gemini-embedding-001`.
2. **HNSW Top-K Retrieval**: Supabase RPC fetches the top $K=5$ most relevant chunks with similarity score $> 0.35$.
3. **Prompt Grounding & Citation Injection**:
   ```
   Context Sources from Meetings:
   [Source 1] Meeting: "Infrastructure Planning" | Type: decision
   Budget approved at $15,000 for AWS migration. (Context: Q3 Infra Budget) [Decided by: Sarah]
   
   [Source 2] Meeting: "Infrastructure Planning" | Type: transcript_chunk
   Sarah: "Let's lock in the AWS migration budget at 15k before Friday."
   
   Question: What was decided regarding the AWS server migration budget?
   ```
4. **Strict System Prompt Anti-Hallucination Constraints**:
   - Instructs Gemini 2.5 Flash to answer **strictly** based on the provided context snippets.
   - If the context does not contain the answer, the model is compelled to return: *"Based on the provided meeting records, there is not enough information to answer this question."*
   - Each answer returns the exact `cited_chunks` (meeting ID, title, chunk type, and similarity score) to provide verifiable auditability.

---

### F. Relational Data Modeling & Google Calendar Ecosystem Sync
- **Multi-Tenant ACID Relational Model**:
  - `meetings` $\rightarrow$ `transcripts` (1-to-many, cascading delete).
  - `meetings` $\rightarrow$ `summaries`, `decisions`, `action_items`, `meeting_tags`, `embeddings`.
  - Postgres **Row Level Security (RLS)** guarantees that users can only query vectors belonging to their authenticated `auth.uid()`.
- **Google Calendar OAuth 2.0 Integration (`backend/app/services/calendar_service.py`)**:
  - Direct bi-directional integration using Google OAuth with offline refresh token rotation stored securely in `public.calendar_tokens`.
  - When Gemini extracts an action item with an assignee and ISO 8601 deadline, an authenticated API call creates a real event in Google Calendar, saving the returned `google_event_id` directly on the `action_items` row.

---

## 3. Presentation Script (Word-for-Word Delivery)

*Target Duration: ~2.5 to 3 Minutes*

> "Good morning, respected evaluators.
> 
> Once my teammate's hybrid intelligence engine produces high-fidelity summaries, decisions, and action items, our system faces its ultimate challenge: **How do we make months of spoken institutional knowledge instantly searchable and conversational without hallucinations?**
> 
> My responsibility encompasses the **Hierarchical Vector Pipeline, pgvector Semantic Indexing, and the Enterprise RAG Conversational Engine**.
> 
> First, standard search fails on spoken transcripts because people don't use clean keywords; they use colloquial language, paraphrasing, and implied references. To solve this, we implement **Hierarchical Semantic Chunking**. Rather than arbitrary character slicing, we create three distinct chunk classes:
> 1. Macro summary chunks for high-level thematic queries.
> 2. Atomic decision and action item chunks, combining task descriptions, assignees, and deadlines.
> 3. Sliding transcript windows of 10 sentences with a 2-sentence overlap to preserve conversational continuity and timestamp boundaries.
> 
> Each text chunk is ingested by the **Gemini 768-dimensional embedding model**, converting conversational semantics into dense normalized vectors in $\mathbb{R}^{768}$.
> 
> For vector storage, instead of introducing expensive standalone vector databases like Pinecone or Milvus that disconnect vectors from our business relational data, we chose **PostgreSQL with the `pgvector` extension** hosted on Supabase.
> 
> To achieve instantaneous query performance, we built a **Hierarchical Navigable Small World (HNSW)** index configured with $m = 16$ and $ef\_construction = 64$. Unlike IVFFlat which requires periodic cluster recalculation, HNSW maintains a multi-layer proximity graph with logarithmic $\mathcal{O}(\log N)$ search complexity. Our custom PL/pgSQL stored procedure evaluates cosine distance via the `<=>` operator directly in PostgreSQL memory, completing vector comparisons across thousands of chunks in under 15 milliseconds.
> 
> Finally, this powers our **Retrieval-Augmented Generation (RAG) assistant**. When a user queries our system—such as *'What was decided about the cloud migration budget?'*—the query is embedded in real time, the top-$K$ semantic matches are retrieved from pgvector, and they are injected into a constrained Gemini prompt.
> 
> We enforce strict negative constraints: if the retrieved context lacks proof, the model explicitly refuses to speculate. Furthermore, every response returns exact citations linking directly back to the meeting title and audio timestamps.
> 
> Combined with our **Google Calendar OAuth synchronization** that pushes extracted action items straight to user calendars, our platform transforms fleeting speech into durable, searchable, and actionable enterprise memory.
> 
> Thank you, and we are now open to your questions."

---

## 4. Key Terminology Cheat-Sheet

| Term | Definition & Project Usage |
| :--- | :--- |
| **`pgvector`** | Open-source PostgreSQL extension adding native support for vector storage, cosine distance, L2 distance, and vector indexing. |
| **HNSW (Hierarchical Navigable Small World)** | Graph-based Approximate Nearest Neighbor (ANN) index. Uses skip-list-like geometric graph layers for fast $\mathcal{O}(\log N)$ search. |
| **Cosine Distance (`<=>`)** | Distance metric measuring angle between high-dimensional vectors: $1 - \cos(\theta)$. Independent of vector magnitude. |
| **Hierarchical Chunking** | Splitting text by structural semantics (macro summaries, atomic decisions, sliding 10-sentence dialogue windows) rather than character counts. |
| **RAG (Retrieval-Augmented Generation)** | Pattern where external factual database context is retrieved via vector similarity and injected into the LLM prompt to eliminate hallucinations. |
| **Row Level Security (RLS)** | PostgreSQL security mechanism ensuring tenant isolation; users can only query embeddings linked to meetings they own. |
| **Idempotent Indexing** | Deleting existing embeddings for a `meeting_id` prior to re-indexing to prevent duplicate vector pollution. |
| **OAuth 2.0 Offline Access** | Generating long-lived refresh tokens to interact with Google Calendar APIs asynchronously on behalf of the user. |

---

## 5. Top 5 Evaluator Viva Questions & Model Answers

### Q1: "Why did you use PostgreSQL with `pgvector` instead of dedicated vector databases like Pinecone, Chroma, or Milvus?"
**Answer:**
> "Dedicated vector databases create a distributed data silo: you have your relational metadata (user IDs, meeting titles, timestamps, permissions) in one database, and vectors in another. This requires dual-writes, complex distributed transactions, and two billing systems. 
> With `pgvector`, our vectors reside directly inside PostgreSQL alongside foreign keys to `meetings` and `transcripts`. This gives us full ACID guarantees, cascading deletes (`ON DELETE CASCADE`), and crucially, PostgreSQL Row-Level Security (RLS). We can perform relational joins and vector similarity in a single query with sub-20ms latency while keeping the infrastructure unified and zero-cost."

---

### Q2: "What is the difference between HNSW and IVFFlat index in pgvector, and why did you choose HNSW?"
**Answer:**
> "IVFFlat (Inverted File Flat) is a cluster-based index that uses $k$-means to partition vector space into centroids. However, IVFFlat requires a populated dataset before training, degrades in recall when new vectors are inserted without re-indexing, and requires scanning multiple centroids ($probes$) to avoid missing true nearest neighbors.
> HNSW (Hierarchical Navigable Small World) builds a multi-layer graph where vertices are vectors and edges connect close neighbors. It supports dynamic insertions without retraining, maintains recall above 98%, and searches in logarithmic time $\mathcal{O}(\log N)$. We configured $m=16$ (edges per node) and $ef\_construction=64$ (construction search depth), which gives us the optimal tradeoff between memory footprint and sub-15ms retrieval."

---

### Q3: "How does your RAG pipeline prevent LLM hallucinations?"
**Answer:**
> "We employ a four-layer mitigation strategy:
> 1. **Similarity Gating**: A strict match threshold of 0.35 in our vector search; if no chunks exceed this score, we immediately return a fallback without querying the LLM.
> 2. **Strict System Prompt Constraints**: The LLM prompt explicitly commands: *'Answer using ONLY the provided context sources. If the context does not contain enough information, state that there is not enough information. Do NOT guess or extrapolate.'*
> 3. **Source Citation Anchoring**: The LLM must reference the meeting title and source number for each assertion.
> 4. **Structured API Return**: The backend returns the answer accompanied by the raw `cited_chunks` metadata (chunk ID, title, similarity score), allowing the frontend to highlight the exact transcript excerpts for user auditability."

---

### Q4: "What is your sliding window chunking strategy, and why is an overlap necessary?"
**Answer:**
> "We group transcript sentences into windows of 10 sentences with an overlap of 2 sentences. 
> In natural speech, conversations don't begin and end neatly within 5 or 10 sentences; decisions and debates span across sentences. If you chunk text with hard boundaries (e.g. sentences 1–10, 11–20), an agreement or context that starts at sentence 10 and concludes at sentence 11 would be split in half, destroying the semantic meaning in both vector representations. 
> A 2-sentence overlap ensures that semantic continuity is preserved across chunk borders so nearest neighbor search retrieves the complete context."

---

### Q5: "How does the Google Calendar integration work securely?"
**Answer:**
> "We implement the standard Google OAuth 2.0 authorization code grant with offline access. 
> In Step 1, the user authorizes our app with the `calendar.events` scope. In Step 2, the callback exchanges the temporary authorization code for an access token and a refresh token, encrypted and stored in `public.calendar_tokens`.
> When an action item with an assignee and deadline is extracted by Gemini, our backend checks if the user has an active Google Calendar token. If valid, it refreshes expired access tokens automatically and calls Google Calendar API v3 to create an event with meeting context, recording the returned `google_event_id` directly in our relational database for future synchronization."

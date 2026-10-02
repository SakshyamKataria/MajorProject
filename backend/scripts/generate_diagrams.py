"""
Generate high-resolution (300 DPI) publication-grade academic architecture and system design
diagrams for MeetFlow, matching the exact format of Chapter 4 in the reference project report:
1. Fig 4.1 – High-Level Architecture
2. Fig 4.2 – Use Case Diagram
3. Fig 4.3 – Data Flow Diagram (DFD Level 0/1)
4. Fig 4.4 – Sequence Diagram
5. Fig 4.5 – Database / Entity Relationship Design
"""

import os
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, ArrowStyle

# Configure clean academic plot settings
plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['mathtext.fontset'] = 'dejavuserif'

OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "report_diagrams"))
os.makedirs(OUTPUT_DIR, exist_ok=True)

# -------------------------------------------------------------
# Helper Functions
# -------------------------------------------------------------
def draw_rounded_box(ax, x, y, w, h, title, subtitle=None, bg_color="#FFFFFF", border_color="#1E293B", 
                     title_color="#0F172A", title_size=10, sub_size=8, title_bold=True, border_width=1.2, 
                     border_style='-', rx=0.03):
    box = FancyBboxPatch((x, y), w, h,
                         boxstyle=f"round,pad=0.01,rounding_size={rx}",
                         facecolor=bg_color, edgecolor=border_color,
                         linewidth=border_width, linestyle=border_style, zorder=2)
    ax.add_patch(box)
    
    if subtitle:
        ax.text(x + w/2, y + h*0.62, title, ha='center', va='center',
                fontsize=title_size, fontweight='bold' if title_bold else 'normal',
                color=title_color, zorder=3)
        ax.text(x + w/2, y + h*0.32, subtitle, ha='center', va='center',
                fontsize=sub_size, color="#475569", zorder=3)
    else:
        ax.text(x + w/2, y + h/2, title, ha='center', va='center',
                fontsize=title_size, fontweight='bold' if title_bold else 'normal',
                color=title_color, zorder=3)
    return box

def draw_arrow(ax, x1, y1, x2, y2, label="", color="#475569", lw=1.2, ls='-', label_offset=(0, 0), label_size=7.5):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="->,head_width=0.3,head_length=0.4",
                                color=color, lw=lw, linestyle=ls),
                zorder=4)
    if label:
        mx = (x1 + x2) / 2 + label_offset[0]
        my = (y1 + y2) / 2 + label_offset[1]
        ax.text(mx, my, label, ha='center', va='center',
                fontsize=label_size, color=color, fontweight='medium',
                bbox=dict(boxstyle="square,pad=0.15", fc="#FFFFFF", ec="none", alpha=0.9),
                zorder=5)

# -------------------------------------------------------------
# 1. FIG 4.1: HIGH-LEVEL ARCHITECTURE
# -------------------------------------------------------------
def generate_fig_4_1():
    fig, ax = plt.subplots(figsize=(12, 7.5), dpi=300)
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 7.5)
    ax.axis('off')

    # Overall Container Title
    ax.text(6.0, 7.25, "MeetFlow: End-to-End System Architecture", ha='center', va='center',
            fontsize=13, fontweight='bold', color="#0F172A")

    # Column / Tier Backgrounds
    col_w = 2.15
    y_top = 6.9
    h_col = 5.3

    cols = [
        ("1. Client Tier", 0.35, "#EFF6FF", "#93C5FD"),
        ("2. Backend & Ingestion", 2.65, "#F0FDF4", "#86EFAC"),
        ("3. AI Processing Pipeline", 4.95, "#FEF3C7", "#FCD34D"),
        ("4. Storage & Vector DB", 7.25, "#F5F3FF", "#C4B5FD"),
        ("5. External Integrations", 9.55, "#FFF1F2", "#FDA4AF"),
    ]

    for title, x, bg, border in cols:
        box = FancyBboxPatch((x, 1.6), col_w, h_col,
                             boxstyle="round,pad=0.02,rounding_size=0.08",
                             facecolor=bg, edgecolor=border, linewidth=1.5, zorder=1)
        ax.add_patch(box)
        ax.text(x + col_w/2, y_top - 0.25, title, ha='center', va='center',
                fontsize=9.5, fontweight='bold', color="#1E293B", zorder=2)

    # 1. Client Tier Items
    draw_rounded_box(ax, 0.5, 5.7, 1.85, 0.65, "React 19 SPA", "Vite + TypeScript + Tailwind", "#FFFFFF", "#3B82F6")
    draw_rounded_box(ax, 0.5, 4.75, 1.85, 0.7, "Audio Dropzone", "MP3 / WAV / M4A / WebM", "#FFFFFF", "#64748B")
    draw_rounded_box(ax, 0.5, 3.8, 1.85, 0.7, "Tab Audio Recorder", "MediaRecorder API + VU Meter", "#FFFFFF", "#64748B")
    draw_rounded_box(ax, 0.5, 2.85, 1.85, 0.7, "Executive Dashboard", "Summary, Decisions, Actions", "#FFFFFF", "#64748B")
    draw_rounded_box(ax, 0.5, 1.9, 1.85, 0.7, "RAG Chat & Groups", "Citation Grounding & Clusters", "#FFFFFF", "#64748B")

    # 2. Backend Tier Items
    draw_rounded_box(ax, 2.8, 5.7, 1.85, 0.65, "FastAPI REST API", "Python 3.11 + Pydantic v2", "#FFFFFF", "#10B981")
    draw_rounded_box(ax, 2.8, 4.75, 1.85, 0.7, "Auth Middleware", "JWT Verification (Supabase)", "#FFFFFF", "#64748B")
    draw_rounded_box(ax, 2.8, 3.8, 1.85, 0.7, "Task Orchestrator", "FastAPI BackgroundTasks", "#FFFFFF", "#10B981")
    draw_rounded_box(ax, 2.8, 2.85, 1.85, 0.7, "Alignment Engine", "Majority-Overlap Algorithm", "#FFFFFF", "#64748B")
    draw_rounded_box(ax, 2.8, 1.9, 1.85, 0.7, "Calendar Service", "OAuth 2.0 + Token Refresh", "#FFFFFF", "#64748B")

    # 3. AI Pipeline Items
    draw_rounded_box(ax, 5.1, 5.7, 1.85, 0.65, "faster-whisper", "large-v3-turbo (int8 CUDA)", "#FFFFFF", "#D97706")
    draw_rounded_box(ax, 5.1, 4.75, 1.85, 0.7, "pyannote.audio 3.1", "Neural Diarization (~19x RTF)", "#FFFFFF", "#D97706")
    draw_rounded_box(ax, 5.1, 3.8, 1.85, 0.7, "Silero VAD", "Voice Activity Detection", "#FFFFFF", "#64748B")
    draw_rounded_box(ax, 5.1, 2.85, 1.85, 0.7, "Hybrid ML Filter", "TF-IDF + Logistic Reg (83.1%)", "#FFFFFF", "#D97706")
    draw_rounded_box(ax, 5.1, 1.9, 1.85, 0.7, "Spherical K-Means", "Cosine Silhouette Optimization", "#FFFFFF", "#64748B")

    # 4. Storage & Database Tier Items
    draw_rounded_box(ax, 7.4, 5.5, 1.85, 0.9, "Cloudflare R2", "S3-Compatible Object Store\n(Presigned Streaming URLs)", "#FFFFFF", "#8B5CF6")
    draw_rounded_box(ax, 7.4, 4.1, 1.85, 1.15, "Supabase PostgreSQL", "ACID Relational Storage\n- profiles, meetings\n- transcripts, decisions\n- action_items, tags", "#FFFFFF", "#8B5CF6", title_size=9.5, sub_size=7.5)
    draw_rounded_box(ax, 7.4, 2.65, 1.85, 1.2, "pgvector Extension", "768d Vector Embeddings\n- HNSW Cosine Indexing\n- Sub-10ms ANN Retrieval", "#FFFFFF", "#8B5CF6", title_size=9.5, sub_size=7.5)
    draw_rounded_box(ax, 7.4, 1.8, 1.85, 0.65, "Row Level Security", "Multi-Tenant Data Isolation", "#FFFFFF", "#64748B")

    # 5. External Integrations Tier Items
    draw_rounded_box(ax, 9.7, 5.5, 1.85, 1.0, "Google Gemini LLM", "gemini-2.5-flash\n(Batched Structured JSON)", "#FFFFFF", "#E11D48")
    draw_rounded_box(ax, 9.7, 4.0, 1.85, 1.1, "Gemini Embeddings", "gemini-embedding-001\n(768-dim Semantic Vectors)", "#FFFFFF", "#E11D48")
    draw_rounded_box(ax, 9.7, 2.6, 1.85, 1.1, "Google Calendar API", "API v3 via OAuth 2.0\n(1-Click Event Scheduling)", "#FFFFFF", "#E11D48")
    draw_rounded_box(ax, 9.7, 1.8, 1.85, 0.65, "Hugging Face Hub", "pyannote.audio Model Weights", "#FFFFFF", "#64748B")

    # Key Connectors / Data Flow Arrows
    draw_arrow(ax, 2.35, 5.1, 2.8, 5.1, "Audio Upload")
    draw_arrow(ax, 4.65, 4.15, 5.1, 4.15, "Async Job")
    draw_arrow(ax, 4.65, 5.1, 7.4, 5.7, "S3 PutObject")
    draw_arrow(ax, 6.95, 3.2, 9.7, 5.8, "Candidates")
    draw_arrow(ax, 9.7, 4.55, 9.25, 3.25, "Embeddings")
    draw_arrow(ax, 4.65, 2.25, 9.7, 3.15, "Schedule Task")
    draw_arrow(ax, 7.4, 3.25, 4.65, 2.25, "Token Auth")

    # Bottom Pipeline Summary
    pbox = FancyBboxPatch((0.35, 0.25), 11.35, 1.05,
                          boxstyle="round,pad=0.02,rounding_size=0.08",
                          facecolor="#F8FAFC", edgecolor="#CBD5E1", linewidth=1.2, zorder=1)
    ax.add_patch(pbox)
    ax.text(6.0, 1.05, "End-to-End Processing Workflow Flow Summary", ha='center', va='center',
            fontsize=9.5, fontweight='bold', color="#334155")
    
    flow_steps = (
        "1. Ingestion (File/Tab)  ──►  2. R2 Audio Persistence  ──►  3. faster-whisper STT + PyAnnote 3.1 Diarization\n"
        "──► 4. Majority-Overlap Alignment  ──►  5. TF-IDF + Logistic Regression Pre-Filter  ──►  6. Batched Gemini Intelligence\n"
        "──► 7. Supabase pgvector HNSW Indexing  ──►  8. Thematic Meeting Clustering  ──►  9. 1-Click Google Calendar Sync"
    )
    ax.text(6.0, 0.55, flow_steps, ha='center', va='center',
            fontsize=8.0, color="#475569", linespacing=1.4)

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "fig_4_1_architecture.png")
    plt.savefig(path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Generated {path}")

# -------------------------------------------------------------
# 2. FIG 4.2: USE CASE DIAGRAM
# -------------------------------------------------------------
def generate_fig_4_2():
    fig, ax = plt.subplots(figsize=(11, 7.5), dpi=300)
    ax.set_xlim(0, 11)
    ax.set_ylim(0, 7.5)
    ax.axis('off')

    ax.text(5.5, 7.25, "MeetFlow: System Use Case Diagram", ha='center', va='center',
            fontsize=13, fontweight='bold', color="#0F172A")

    # System Boundary Box
    sys_box = FancyBboxPatch((2.2, 0.4), 6.6, 6.6,
                             boxstyle="round,pad=0.02,rounding_size=0.05",
                             facecolor="#F8FAFC", edgecolor="#3B82F6", linewidth=1.5, zorder=1)
    ax.add_patch(sys_box)
    ax.text(5.5, 6.75, "MeetFlow Platform Boundary", ha='center', va='center',
            fontsize=10.5, fontweight='bold', color="#1D4ED8")

    # Primary Actor: User (Left)
    ax.plot([1.0, 1.0], [4.1, 4.7], color="#0F172A", lw=2, zorder=3) # Body
    c_head = plt.Circle((1.0, 4.9), 0.22, fc="#FFFFFF", ec="#0F172A", lw=2, zorder=3)
    ax.add_patch(c_head) # Head
    ax.plot([0.7, 1.3], [4.45, 4.45], color="#0F172A", lw=2, zorder=3) # Arms
    ax.plot([1.0, 0.75], [4.1, 3.65], color="#0F172A", lw=2, zorder=3) # Left Leg
    ax.plot([1.0, 1.25], [4.1, 3.65], color="#0F172A", lw=2, zorder=3) # Right Leg
    ax.text(1.0, 3.35, "Meeting Participant /\nProject Manager\n(User)", ha='center', va='center',
            fontsize=9.0, fontweight='bold', color="#0F172A")

    # Secondary Actors: Right side
    # Actor 1: Google Gemini
    box_ai = FancyBboxPatch((9.2, 4.6), 1.6, 1.1, boxstyle="round,pad=0.02,rounding_size=0.04",
                            fc="#EFF6FF", ec="#3B82F6", lw=1.5, zorder=3)
    ax.add_patch(box_ai)
    ax.text(10.0, 5.3, "<<External System>>\nGoogle Gemini AI", ha='center', va='center',
            fontsize=8.5, fontweight='bold', color="#1E40AF")
    ax.text(10.0, 4.85, "(LLM & Embeddings)", ha='center', va='center', fontsize=7.5, color="#475569")

    # Actor 2: Google Calendar
    box_cal = FancyBboxPatch((9.2, 1.8), 1.6, 1.1, boxstyle="round,pad=0.02,rounding_size=0.04",
                             fc="#FEF2F2", ec="#EF4444", lw=1.5, zorder=3)
    ax.add_patch(box_cal)
    ax.text(10.0, 2.5, "<<External Service>>\nGoogle Calendar", ha='center', va='center',
            fontsize=8.5, fontweight='bold', color="#991B1B")
    ax.text(10.0, 2.05, "(OAuth 2.0 API v3)", ha='center', va='center', fontsize=7.5, color="#475569")

    # Use Cases (Ellipses)
    use_cases = [
        ("Register & Authenticate Account", 3.7, 6.2, 2.4, 0.52),
        ("Upload Audio File (MP3/WAV/M4A)", 3.7, 5.5, 2.4, 0.52),
        ("Record Live Browser Tab Audio", 3.7, 4.8, 2.4, 0.52),
        ("View Diarized Transcript & Audio", 3.7, 4.1, 2.4, 0.52),
        ("Re-attribute Speakers & View Stats", 3.7, 3.4, 2.4, 0.52),
        ("Review Executive Summary & Points", 3.7, 2.7, 2.4, 0.52),
        ("Track Decisions & Action Items", 3.7, 2.0, 2.4, 0.52),
        ("Sync Action Item to Google Calendar", 3.7, 1.3, 2.5, 0.52),
        ("Search Meeting Archive (Semantic pgvector)", 7.1, 5.5, 2.6, 0.54),
        ("Explore Thematic Meeting Clusters", 7.1, 4.5, 2.6, 0.54),
        ("Ask Grounded Questions (RAG Chat)", 7.1, 3.4, 2.6, 0.54),
        ("Filter Noise via Hybrid ML Model", 7.1, 2.2, 2.6, 0.54),
    ]

    for title, cx, cy, ew, eh in use_cases:
        ellipse = patches.Ellipse((cx, cy), ew, eh, facecolor="#FFFFFF", edgecolor="#2563EB", linewidth=1.2, zorder=2)
        ax.add_patch(ellipse)
        ax.text(cx, cy, title, ha='center', va='center', fontsize=8.0, fontweight='medium', color="#0F172A", zorder=3)

    # Actor-to-Use-Case lines (User to left use cases)
    user_conns = [(3.7 - 1.2, 6.2), (3.7 - 1.2, 5.5), (3.7 - 1.2, 4.8), (3.7 - 1.2, 4.1),
                  (3.7 - 1.2, 3.4), (3.7 - 1.2, 2.7), (3.7 - 1.2, 2.0), (3.7 - 1.25, 1.3)]
    for ux, uy in user_conns:
        ax.plot([1.2, ux], [4.4, uy], color="#64748B", lw=1.1, zorder=1)

    # User to right search & RAG
    ax.plot([1.2, 5.8], [4.4, 5.5], color="#64748B", lw=1.1, zorder=1)
    ax.plot([1.2, 5.8], [4.4, 3.4], color="#64748B", lw=1.1, zorder=1)

    # AI connections
    ax.plot([8.4, 9.2], [5.5, 5.15], color="#2563EB", lw=1.1, ls='--', zorder=1) # Search -> Gemini
    ax.plot([8.4, 9.2], [4.5, 5.15], color="#2563EB", lw=1.1, ls='--', zorder=1) # Clusters -> Gemini
    ax.plot([8.4, 9.2], [3.4, 5.15], color="#2563EB", lw=1.1, ls='--', zorder=1) # RAG Chat -> Gemini
    ax.plot([4.9, 5.8], [2.7, 2.2], color="#D97706", lw=1.1, ls=':', zorder=1)  # Summary <<include>> ML Filter

    # Calendar connection
    ax.plot([4.95, 9.2], [1.3, 2.35], color="#DC2626", lw=1.1, ls='--', zorder=1)

    # Legend at bottom
    ax.plot([2.5, 3.2], [0.65, 0.65], color="#64748B", lw=1.2)
    ax.text(3.3, 0.65, "Actor Association", va='center', fontsize=7.5, color="#475569")

    ax.plot([5.5, 6.2], [0.65, 0.65], color="#2563EB", lw=1.2, ls='--')
    ax.text(6.3, 0.65, "External Service <<communicates>>", va='center', fontsize=7.5, color="#475569")

    ax.plot([8.5, 9.2], [0.65, 0.65], color="#D97706", lw=1.2, ls=':')
    ax.text(9.3, 0.65, "<<include>> Dependency", va='center', fontsize=7.5, color="#475569")

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "fig_4_2_use_case.png")
    plt.savefig(path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Generated {path}")

# -------------------------------------------------------------
# 3. FIG 4.3: DATA FLOW DIAGRAM (DFD LEVEL 0 / 1)
# -------------------------------------------------------------
def generate_fig_4_3():
    fig, ax = plt.subplots(figsize=(12, 7.5), dpi=300)
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 7.5)
    ax.axis('off')

    ax.text(6.0, 7.25, "MeetFlow: Data Flow Diagram (Level 1 Pipeline)", ha='center', va='center',
            fontsize=13, fontweight='bold', color="#0F172A")

    # External Entities (Square boxes with double lines)
    def draw_entity(x, y, w, h, text):
        box = FancyBboxPatch((x, y), w, h, boxstyle="square,pad=0.01",
                             fc="#F1F5F9", ec="#334155", lw=1.5, zorder=2)
        ax.add_patch(box)
        ax.text(x + w/2, y + h/2, text, ha='center', va='center',
                fontsize=8.5, fontweight='bold', color="#0F172A", zorder=3)

    # Processes (Circles / Ellipses)
    def draw_process(x, y, r, p_num, p_name):
        c = plt.Circle((x, y), r, fc="#FFFFFF", ec="#2563EB", lw=1.5, zorder=2)
        ax.add_patch(c)
        ax.plot([x - r*0.88, x + r*0.88], [y + r*0.28, y + r*0.28], color="#2563EB", lw=1.0, zorder=3)
        ax.text(x, y + r*0.55, p_num, ha='center', va='center', fontsize=7.5, fontweight='bold', color="#1D4ED8", zorder=4)
        ax.text(x, y - r*0.18, p_name, ha='center', va='center', fontsize=7.2, fontweight='medium', color="#0F172A", zorder=4)

    # Data Stores (Open ended horizontal lines)
    def draw_datastore(x, y, w, h, ds_id, ds_name):
        ax.plot([x, x + w], [y + h, y + h], color="#059669", lw=1.5, zorder=2)
        ax.plot([x, x + w], [y, y], color="#059669", lw=1.5, zorder=2)
        ax.plot([x, x], [y, y + h], color="#059669", lw=1.5, zorder=2)
        patch = patches.Rectangle((x, y), w, h, fc="#ECFDF5", ec="none", zorder=1)
        ax.add_patch(patch)
        ax.text(x + 0.35, y + h/2, ds_id, ha='center', va='center', fontsize=8.0, fontweight='bold', color="#047857", zorder=3)
        ax.plot([x + 0.7, x + 0.7], [y, y + h], color="#059669", lw=1.0, zorder=2)
        ax.text(x + 0.8 + (w - 0.8)/2, y + h/2, ds_name, ha='center', va='center', fontsize=7.5, color="#065F46", zorder=3)

    # Entities
    draw_entity(0.4, 4.4, 1.4, 1.0, "Meeting\nParticipant\n(User)")
    draw_entity(10.2, 5.6, 1.4, 0.9, "Google Gemini\n(GenAI API)")
    draw_entity(10.2, 3.8, 1.4, 0.9, "Cloudflare R2\n(S3 Storage)")
    draw_entity(10.2, 2.0, 1.4, 0.9, "Google Calendar\n(API v3)")

    # Processes
    draw_process(2.6, 4.9, 0.65, "1.0", "Ingestion &\nMedia Capture")
    draw_process(4.4, 5.8, 0.65, "2.0", "Local STT\n(faster-whisper)")
    draw_process(4.4, 4.0, 0.65, "3.0", "Neural Diarization\n(pyannote 3.1)")
    draw_process(6.2, 4.9, 0.65, "4.0", "Alignment &\nML Pre-Filter")
    draw_process(8.0, 5.8, 0.65, "5.0", "Structured LLM\nExtraction")
    draw_process(8.0, 3.8, 0.65, "6.0", "Vector Embeddings\n& pgvector")
    draw_process(8.0, 1.8, 0.65, "7.0", "Calendar Event\nSync Service")
    draw_process(4.4, 1.8, 0.65, "8.0", "Conversational\nRAG Assistant")

    # Data Stores
    draw_datastore(2.4, 3.2, 2.0, 0.5, "D1", "Audio Recordings (R2)")
    draw_datastore(5.4, 3.2, 2.2, 0.5, "D2", "Transcripts & Speakers")
    draw_datastore(8.4, 4.8, 2.2, 0.5, "D3", "Executive Summaries")
    draw_datastore(5.4, 1.0, 2.2, 0.5, "D4", "pgvector Embeddings")
    draw_datastore(8.4, 0.8, 2.2, 0.5, "D5", "OAuth Calendar Tokens")

    # Connectors
    draw_arrow(ax, 1.8, 4.9, 1.95, 4.9, "Audio Upload")
    draw_arrow(ax, 3.25, 4.9, 3.8, 5.6, "Audio Stream")
    draw_arrow(ax, 3.25, 4.9, 3.8, 4.2, "Mono Audio")
    draw_arrow(ax, 2.6, 4.25, 2.6, 3.7, "Presigned URL")
    draw_arrow(ax, 3.7, 5.8, 3.4, 3.7, "Persist Audio")
    draw_arrow(ax, 5.05, 5.8, 5.55, 5.1, "Sentences")
    draw_arrow(ax, 5.05, 4.0, 5.55, 4.7, "Speaker Turns")
    draw_arrow(ax, 6.85, 4.9, 7.35, 5.6, "Filtered Candidates")
    draw_arrow(ax, 8.65, 5.8, 10.2, 5.9, "Batched Prompt")
    draw_arrow(ax, 10.2, 5.7, 8.65, 5.6, "Structured JSON")
    draw_arrow(ax, 8.0, 5.15, 8.0, 4.45, "Text Chunks")
    draw_arrow(ax, 8.65, 3.8, 10.2, 4.15, "Generate 768d")
    draw_arrow(ax, 8.0, 3.15, 7.6, 1.3, "Index Vectors")
    draw_arrow(ax, 6.2, 4.25, 6.2, 3.7, "Store Aligned")
    draw_arrow(ax, 8.0, 5.15, 8.5, 5.1, "Save Insights")
    draw_arrow(ax, 8.0, 2.45, 8.0, 2.8, "Task Deliverable")
    draw_arrow(ax, 8.65, 1.8, 10.2, 2.2, "Create Event")
    draw_arrow(ax, 3.8, 1.8, 1.8, 4.4, "Citation Grounded Answer")

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "fig_4_3_data_flow.png")
    plt.savefig(path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Generated {path}")

# -------------------------------------------------------------
# 4. FIG 4.4: SEQUENCE DIAGRAM
# -------------------------------------------------------------
def generate_fig_4_4():
    fig, ax = plt.subplots(figsize=(12, 8.0), dpi=300)
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 8.0)
    ax.axis('off')

    ax.text(6.0, 7.75, "MeetFlow: End-to-End Processing Sequence Diagram", ha='center', va='center',
            fontsize=13, fontweight='bold', color="#0F172A")

    # Lifeline Participants
    lifelines = [
        ("User / Client", 1.0, "#EFF6FF", "#3B82F6"),
        ("FastAPI Backend", 2.8, "#F0FDF4", "#10B981"),
        ("Cloudflare R2", 4.6, "#FAF5FF", "#A855F7"),
        ("Whisper & PyAnnote", 6.4, "#FFFBEB", "#F59E0B"),
        ("ML Filter & Gemini", 8.2, "#FFF1F2", "#F43F5E"),
        ("Supabase pgvector", 10.0, "#F5F3FF", "#6366F1"),
        ("Google Calendar", 11.3, "#FEF2F2", "#EF4444")
    ]

    top_y = 7.3
    bot_y = 0.5

    for name, lx, bg, border in lifelines:
        # Box at top
        w, h = 1.35, 0.45
        box = FancyBboxPatch((lx - w/2, top_y - h), w, h, boxstyle="round,pad=0.01,rounding_size=0.04",
                             fc=bg, ec=border, lw=1.2, zorder=2)
        ax.add_patch(box)
        ax.text(lx, top_y - h/2, name, ha='center', va='center', fontsize=7.5, fontweight='bold', color="#1E293B", zorder=3)
        # Vertical dashed lifeline
        ax.plot([lx, lx], [top_y - h, bot_y], color="#CBD5E1", lw=1.2, ls='--', zorder=1)

    # Sequence Messages
    seq_events = [
        # (y, from_idx, to_idx, label, is_return, style)
        (6.5, 0, 1, "1. POST /api/meetings/upload (Audio)", False, '-'),
        (6.1, 1, 2, "2. S3 PutObject (UUID key)", False, '-'),
        (5.7, 2, 1, "3. S3 200 OK + Audio URL", True, '--'),
        (5.3, 1, 0, "4. 202 Accepted (meeting_id, 'processing')", True, '--'),
        (4.9, 1, 3, "5. Spawn Background Task (STT + Diarization)", False, '-'),
        (4.4, 3, 3, "6. faster-whisper (large-v3-turbo) & pyannote 3.1", False, ':'),
        (3.9, 3, 1, "7. Return Aligned Sentences + Overlapping Speakers", True, '--'),
        (3.5, 1, 4, "8. ML Pre-Filter & Batched Gemini Extraction", False, '-'),
        (3.0, 4, 1, "9. Return JSON: Summary, Decisions, Actions", True, '--'),
        (2.6, 1, 5, "10. Insert Relational Records & 768d HNSW Embeddings", False, '-'),
        (2.2, 5, 1, "11. DB Commit OK -> status='completed'", True, '--'),
        (1.8, 0, 1, "12. Client poll -> GET /api/meetings/{id}", False, '-'),
        (1.4, 1, 0, "13. Return 200 OK (Full Executive Intelligence)", True, '--'),
        (1.0, 0, 1, "14. POST /api/calendar/sync-action-item", False, '-'),
        (0.7, 1, 6, "15. Google Calendar API v3 Insert Event", False, '-'),
    ]

    for y, f_idx, t_idx, msg, is_ret, ls in seq_events:
        x1 = lifelines[f_idx][1]
        x2 = lifelines[t_idx][1]
        c = "#2563EB" if not is_ret else "#059669"
        if f_idx == t_idx:
            # Self call
            ax.plot([x1, x1 + 0.5, x1 + 0.5, x1], [y + 0.1, y + 0.1, y - 0.1, y - 0.1], color="#D97706", lw=1.2, ls=ls)
            ax.annotate("", xy=(x1, y - 0.1), xytext=(x1 + 0.1, y - 0.1),
                        arrowprops=dict(arrowstyle="->", color="#D97706", lw=1.2))
            ax.text(x1 + 0.6, y, msg, ha='left', va='center', fontsize=7.2, color="#92400E", fontweight='medium')
        else:
            draw_arrow(ax, x1, y, x2, y, msg, color=c, lw=1.1, ls=ls, label_offset=(0, 0.12), label_size=7.2)

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "fig_4_4_sequence.png")
    plt.savefig(path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Generated {path}")

# -------------------------------------------------------------
# 5. FIG 4.5: DATABASE / ENTITY RELATIONSHIP DESIGN
# -------------------------------------------------------------
def generate_fig_4_5():
    fig, ax = plt.subplots(figsize=(12, 8.0), dpi=300)
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 8.0)
    ax.axis('off')

    ax.text(6.0, 7.75, "MeetFlow: Relational & Vector Database Schema (Supabase pgvector)", ha='center', va='center',
            fontsize=13, fontweight='bold', color="#0F172A")

    # Table Box Renderer
    def draw_table_schema(x, y, w, title, columns, header_bg="#1E293B", body_bg="#FFFFFF"):
        row_h = 0.28
        total_h = 0.4 + len(columns) * row_h
        
        # Outer box
        outer = FancyBboxPatch((x, y - total_h), w, total_h,
                               boxstyle="round,pad=0.01,rounding_size=0.04",
                               fc=body_bg, ec=header_bg, lw=1.4, zorder=2)
        ax.add_patch(outer)
        
        # Header box
        hdr = FancyBboxPatch((x, y - 0.4), w, 0.4,
                             boxstyle="round,pad=0.01,rounding_size=0.04",
                             fc=header_bg, ec=header_bg, lw=1.4, zorder=3)
        ax.add_patch(hdr)
        ax.text(x + w/2, y - 0.2, title, ha='center', va='center',
                fontsize=8.5, fontweight='bold', color="#FFFFFF", zorder=4)

        # Columns
        for i, (col_name, col_type, key_type) in enumerate(columns):
            cy = y - 0.4 - (i + 0.5) * row_h
            # Divider line
            if i > 0:
                ax.plot([x, x + w], [cy + row_h/2, cy + row_h/2], color="#E2E8F0", lw=0.6, zorder=3)
            
            k_color = "#DC2626" if key_type == "PK" else ("#2563EB" if key_type == "FK" else "#64748B")
            ax.text(x + 0.15, cy, f"[{key_type}]" if key_type else "", ha='left', va='center',
                    fontsize=6.8, fontweight='bold', color=k_color, zorder=4)
            ax.text(x + 0.65, cy, col_name, ha='left', va='center',
                    fontsize=7.2, fontweight='bold' if key_type == "PK" else 'normal', color="#0F172A", zorder=4)
            ax.text(x + w - 0.12, cy, col_type, ha='right', va='center',
                    fontsize=6.8, color="#64748B", zorder=4)

        return (x, y - total_h, w, total_h)

    # 1. profiles
    draw_table_schema(0.4, 7.3, 2.5, "profiles", [
        ("id", "uuid", "PK"),
        ("email", "varchar", ""),
        ("full_name", "varchar", ""),
        ("avatar_url", "text", ""),
        ("created_at", "timestamptz", ""),
        ("updated_at", "timestamptz", "")
    ], header_bg="#0F172A")

    # 2. meetings
    draw_table_schema(3.4, 7.3, 2.8, "meetings", [
        ("id", "uuid", "PK"),
        ("user_id", "uuid", "FK"),
        ("title", "varchar", ""),
        ("description", "text", ""),
        ("audio_url", "text", ""),
        ("duration_seconds", "integer", ""),
        ("status", "varchar", ""),
        ("error_message", "text", ""),
        ("speaker_names", "jsonb", ""),
        ("created_at", "timestamptz", ""),
        ("updated_at", "timestamptz", "")
    ], header_bg="#1E3A8A")

    # 3. transcripts
    draw_table_schema(6.7, 7.3, 2.7, "transcripts", [
        ("id", "uuid", "PK"),
        ("meeting_id", "uuid", "FK"),
        ("speaker", "varchar", ""),
        ("speaker_label", "varchar", ""),
        ("sentence_order", "integer", ""),
        ("start_time", "float", ""),
        ("end_time", "float", ""),
        ("text", "text", ""),
        ("classifier_label", "varchar", ""),
        ("classifier_confidence", "float", "")
    ], header_bg="#065F46")

    # 4. summaries
    draw_table_schema(9.8, 7.3, 1.8, "summaries", [
        ("id", "uuid", "PK"),
        ("meeting_id", "uuid", "FK"),
        ("executive_summary", "text", ""),
        ("key_points", "text[]", ""),
        ("raw_ai_response", "jsonb", "")
    ], header_bg="#92400E")

    # 5. decisions
    draw_table_schema(0.4, 4.3, 2.5, "decisions", [
        ("id", "uuid", "PK"),
        ("meeting_id", "uuid", "FK"),
        ("decision", "text", ""),
        ("context", "text", ""),
        ("decided_by", "varchar", ""),
        ("created_at", "timestamptz", "")
    ], header_bg="#78350F")

    # 6. action_items
    draw_table_schema(3.4, 3.4, 2.8, "action_items", [
        ("id", "uuid", "PK"),
        ("meeting_id", "uuid", "FK"),
        ("task", "text", ""),
        ("assignee", "varchar", ""),
        ("deadline", "timestamptz", ""),
        ("priority", "varchar", ""),
        ("status", "varchar", ""),
        ("tags", "text[]", ""),
        ("confidence", "float", "")
    ], header_bg="#831843")

    # 7. embeddings (pgvector)
    draw_table_schema(6.7, 3.7, 2.7, "embeddings (pgvector)", [
        ("id", "uuid", "PK"),
        ("meeting_id", "uuid", "FK"),
        ("chunk_type", "varchar", ""),
        ("content", "text", ""),
        ("metadata", "jsonb", ""),
        ("embedding", "vector(768)", ""),
        ("created_at", "timestamptz", "")
    ], header_bg="#4C1D95")

    # 8. google_calendar_tokens
    draw_table_schema(9.8, 5.0, 1.8, "google_calendar_tokens", [
        ("user_id", "uuid", "PK"),
        ("access_token", "text", ""),
        ("refresh_token", "text", ""),
        ("token_expiry", "timestamptz", ""),
        ("created_at", "timestamptz", "")
    ], header_bg="#991B1B")

    # 9. meeting_tags
    draw_table_schema(9.8, 2.8, 1.8, "meeting_tags", [
        ("id", "uuid", "PK"),
        ("meeting_id", "uuid", "FK"),
        ("tag", "varchar", "")
    ], header_bg="#374151")

    # Relationship connectors
    # profiles (1) -> meetings (N)
    ax.plot([2.9, 3.4], [7.1, 7.1], color="#2563EB", lw=1.2, zorder=1)
    ax.text(3.0, 7.2, "1:N", fontsize=7.0, color="#1D4ED8", fontweight='bold')

    # meetings (1) -> transcripts (N)
    ax.plot([6.2, 6.7], [7.1, 7.1], color="#2563EB", lw=1.2, zorder=1)
    ax.text(6.35, 7.2, "1:N", fontsize=7.0, color="#1D4ED8", fontweight='bold')

    # meetings (1) -> summaries (1)
    ax.plot([6.2, 9.8], [6.5, 6.5], color="#2563EB", lw=1.2, zorder=1)
    ax.text(8.0, 6.6, "1:1", fontsize=7.0, color="#1D4ED8", fontweight='bold')

    # meetings (1) -> decisions (N)
    ax.plot([3.4, 2.9], [5.0, 4.1], color="#2563EB", lw=1.2, zorder=1)

    # meetings (1) -> action_items (N)
    ax.plot([4.8, 4.8], [4.1, 3.4], color="#2563EB", lw=1.2, zorder=1)
    ax.text(4.9, 3.75, "1:N", fontsize=7.0, color="#1D4ED8", fontweight='bold')

    # meetings (1) -> embeddings (N)
    ax.plot([6.2, 6.7], [4.8, 3.5], color="#2563EB", lw=1.2, zorder=1)

    # meetings (1) -> meeting_tags (N)
    ax.plot([6.2, 9.8], [4.5, 2.5], color="#2563EB", lw=1.2, zorder=1)

    # profiles (1) -> google_calendar_tokens (1)
    ax.plot([1.65, 1.65, 10.7, 10.7], [5.2, 0.4, 0.4, 3.2], color="#DC2626", lw=1.1, ls='--', zorder=1)
    ax.text(5.5, 0.25, "Foreign Key Link: profiles.id ──► google_calendar_tokens.user_id (1:1 with RLS)",
            fontsize=7.2, color="#991B1B", ha='center', va='center')

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "fig_4_5_database_design.png")
    plt.savefig(path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Generated {path}")

if __name__ == '__main__':
    print("Generating Chapter 4 diagrams...")
    generate_fig_4_1()
    generate_fig_4_2()
    generate_fig_4_3()
    generate_fig_4_4()
    generate_fig_4_5()
    print("All 5 diagrams successfully generated!")

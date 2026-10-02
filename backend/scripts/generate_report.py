"""
Generate a professional, IEEE/VTU academic project report for MeetFlow in .docx format.
Matches the structure, headings, certificate, abstract, literature survey, requirements,
architecture, implementation, testing, results, and references of the reference report.
"""

import os
import docx
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

def create_report(output_path: str):
    doc = Document()

    # Configure 1-inch margins
    sections = doc.sections
    for section in sections:
        section.top_margin = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin = Inches(1.0)
        section.right_margin = Inches(1.0)

    # Base styles
    normal_style = doc.styles['Normal']
    normal_font = normal_style.font
    normal_font.name = 'Times New Roman'
    normal_font.size = Pt(12)
    normal_font.color.rgb = RGBColor(0, 0, 0)
    normal_style.paragraph_format.line_spacing = 1.15
    normal_style.paragraph_format.space_after = Pt(6)

    def set_cell_shading(cell, color_hex="F2F4F7"):
        shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{color_hex}"/>')
        cell._tc.get_or_add_tcPr().append(shd)

    def set_cell_borders(cell, top="single", bottom="single", left="single", right="single", color="B0B8C1", sz="4"):
        tcPr = cell._tc.get_or_add_tcPr()
        borders = parse_xml(
            f'<w:tcBorders {nsdecls("w")}>'
            f'  <w:top w:val="{top}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
            f'  <w:left w:val="{left}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
            f'  <w:bottom w:val="{bottom}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
            f'  <w:right w:val="{right}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
            f'</w:tcBorders>'
        )
        tcPr.append(borders)

    def add_chapter_title(text):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(18)
        p.paragraph_format.space_after = Pt(12)
        run = p.add_run(text)
        run.bold = True
        run.font.name = 'Times New Roman'
        run.font.size = Pt(16)
        run.font.color.rgb = RGBColor(0, 0, 0)
        return p

    def add_section_heading(text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(14)
        p.paragraph_format.space_after = Pt(6)
        p.paragraph_format.keep_with_next = True
        run = p.add_run(text)
        run.bold = True
        run.font.name = 'Times New Roman'
        run.font.size = Pt(14)
        run.font.color.rgb = RGBColor(0, 0, 0)
        return p

    def add_sub_heading(text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(10)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.keep_with_next = True
        run = p.add_run(text)
        run.bold = True
        run.font.name = 'Times New Roman'
        run.font.size = Pt(12)
        run.font.color.rgb = RGBColor(0, 0, 0)
        return p

    def add_sub_sub_heading(text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(8)
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.keep_with_next = True
        run = p.add_run(text)
        run.bold = True
        run.font.name = 'Times New Roman'
        run.font.size = Pt(12)
        run.font.color.rgb = RGBColor(30, 41, 59)
        return p

    def add_body_p(text, bold_prefix=None, space_after=6):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.space_after = Pt(space_after)
        p.paragraph_format.line_spacing = 1.15
        if bold_prefix:
            r_pre = p.add_run(bold_prefix)
            r_pre.bold = True
            r_pre.font.name = 'Times New Roman'
            r_pre.font.size = Pt(12)
        run = p.add_run(text)
        run.font.name = 'Times New Roman'
        run.font.size = Pt(12)
        return p

    def add_bullet_item(text, bold_prefix=None):
        p = doc.add_paragraph(style='List Bullet')
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.space_after = Pt(3)
        p.paragraph_format.line_spacing = 1.15
        if bold_prefix:
            r_pre = p.add_run(bold_prefix)
            r_pre.bold = True
            r_pre.font.name = 'Times New Roman'
            r_pre.font.size = Pt(12)
        run = p.add_run(text)
        run.font.name = 'Times New Roman'
        run.font.size = Pt(12)
        return p

    def add_numbered_item(num_str, text, bold_prefix=None):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.left_indent = Inches(0.25)
        p.paragraph_format.first_line_indent = Inches(-0.25)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.line_spacing = 1.15
        r_num = p.add_run(f"{num_str}\t")
        r_num.bold = True
        r_num.font.name = 'Times New Roman'
        r_num.font.size = Pt(12)
        if bold_prefix:
            r_pre = p.add_run(bold_prefix)
            r_pre.bold = True
            r_pre.font.name = 'Times New Roman'
            r_pre.font.size = Pt(12)
        run = p.add_run(text)
        run.font.name = 'Times New Roman'
        run.font.size = Pt(12)
        return p

    def add_screenshot_placeholder(fig_num: str, fig_title: str, height_in_inches=2.8):
        """Creates a professional bordered box reserving space for the user's project screenshot."""
        table = doc.add_table(rows=1, cols=1)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.autofit = False

        cell = table.cell(0, 0)
        cell.width = Inches(6.5)
        set_cell_shading(cell, "F8F9FA")
        set_cell_borders(cell, top="dashed", bottom="dashed", left="dashed", right="dashed", color="94A3B8", sz="6")

        # Set row height
        trPr = table.rows[0]._tr.get_or_add_trPr()
        trHeight = parse_xml(f'<w:trHeight {nsdecls("w")} w:val="{int(height_in_inches * 1440)}" w:hRule="atLeast"/>')
        trPr.append(trHeight)

        cp = cell.paragraphs[0]
        cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        cp.paragraph_format.space_before = Pt(int(height_in_inches * 35))
        cp.paragraph_format.space_after = Pt(4)
        
        r1 = cp.add_run(f"[ INSERT SCREENSHOT HERE: {fig_num} – {fig_title} ]\n")
        r1.bold = True
        r1.font.name = 'Times New Roman'
        r1.font.size = Pt(11)
        r1.font.color.rgb = RGBColor(71, 85, 105)

        r2 = cp.add_run("(Appropriate space reserved for project interface screenshot)")
        r2.italic = True
        r2.font.name = 'Times New Roman'
        r2.font.size = Pt(10)
        r2.font.color.rgb = RGBColor(148, 163, 184)

        # Caption
        cap_p = doc.add_paragraph()
        cap_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        cap_p.paragraph_format.space_before = Pt(6)
        cap_p.paragraph_format.space_after = Pt(14)
        cap_run = cap_p.add_run(f"{fig_num} – {fig_title}")
        cap_run.bold = True
        cap_run.italic = True
        cap_run.font.name = 'Times New Roman'
        cap_run.font.size = Pt(11)

    # ==========================================
    # 1. COVER PAGE (PAGE 1)
    # ==========================================
    p_cov_title = doc.add_paragraph()
    p_cov_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_cov_title.paragraph_format.space_before = Pt(40)
    p_cov_title.paragraph_format.space_after = Pt(12)
    r_t = p_cov_title.add_run('“MeetFlow : AI-Powered Meeting Intelligence & Automated Action Tracking System”')
    r_t.bold = True
    r_t.font.name = 'Times New Roman'
    r_t.font.size = Pt(15)

    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_sub.paragraph_format.space_after = Pt(36)
    r_sub = p_sub.add_run("A PROJECT WORK REPORT SUBMITTED TO")
    r_sub.font.name = 'Times New Roman'
    r_sub.font.size = Pt(12)

    p_inst = doc.add_paragraph()
    p_inst.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_inst.paragraph_format.space_after = Pt(4)
    r_inst1 = p_inst.add_run("THE NATIONAL INSTITUTE OF ENGINEERING\n")
    r_inst1.bold = True
    r_inst1.font.name = 'Times New Roman'
    r_inst1.font.size = Pt(16)
    r_inst2 = p_inst.add_run("(An Autonomous Institution Under VTU)")
    r_inst2.font.name = 'Times New Roman'
    r_inst2.font.size = Pt(13)

    p_deg = doc.add_paragraph()
    p_deg.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_deg.paragraph_format.space_before = Pt(120)
    p_deg.paragraph_format.space_after = Pt(6)
    r_deg1 = p_deg.add_run("In fulfillment of the requirements for major project work, Seventh semester\n")
    r_deg1.font.name = 'Times New Roman'
    r_deg1.font.size = Pt(12)
    r_deg2 = p_deg.add_run("Bachelor of Engineering In Computer Science & Engineering\n")
    r_deg2.bold = True
    r_deg2.font.name = 'Times New Roman'
    r_deg2.font.size = Pt(13)
    r_deg3 = p_deg.add_run("Submitted By")
    r_deg3.italic = True
    r_deg3.font.name = 'Times New Roman'
    r_deg3.font.size = Pt(12)

    # Student Names Table
    t_students = doc.add_table(rows=4, cols=2)
    t_students.alignment = WD_TABLE_ALIGNMENT.CENTER
    t_students.autofit = False
    
    students_data = [
        ("Sakshyam Kataria", "4NI23CS001"),
        ("[Team Member 2 Name]", "4NI23CS002"),
        ("[Team Member 3 Name]", "4NI23CS003"),
        ("[Team Member 4 Name]", "4NI23CS004")
    ]
    for idx, (name, usn) in enumerate(students_data):
        row = t_students.rows[idx]
        cell_name = row.cells[0]
        cell_usn = row.cells[1]
        cell_name.width = Inches(3.0)
        cell_usn.width = Inches(2.0)
        
        p_n = cell_name.paragraphs[0]
        p_n.paragraph_format.space_after = Pt(3)
        r_n = p_n.add_run(name)
        r_n.bold = True
        r_n.font.name = 'Times New Roman'
        r_n.font.size = Pt(12)
        
        p_u = cell_usn.paragraphs[0]
        p_u.paragraph_format.space_after = Pt(3)
        r_u = p_u.add_run(usn)
        r_u.bold = True
        r_u.font.name = 'Times New Roman'
        r_u.font.size = Pt(12)

    doc.add_page_break()

    # ==========================================
    # 2. GUIDANCE & INSTITUTE DETAILS (PAGE 2)
    # ==========================================
    p_guide_head = doc.add_paragraph()
    p_guide_head.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_guide_head.paragraph_format.space_before = Pt(60)
    p_guide_head.paragraph_format.space_after = Pt(10)
    r_gh = p_guide_head.add_run("Under The Guidance Of\n\n")
    r_gh.font.name = 'Times New Roman'
    r_gh.font.size = Pt(12)
    
    r_gn = p_guide_head.add_run("Dr. Naveen S. Pagad\n")
    r_gn.bold = True
    r_gn.font.name = 'Times New Roman'
    r_gn.font.size = Pt(14)

    r_gd = p_guide_head.add_run("Assistant Professor\nDepartment of CS&E,\nNIE Mysore")
    r_gd.font.name = 'Times New Roman'
    r_gd.font.size = Pt(12)

    p_dept = doc.add_paragraph()
    p_dept.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_dept.paragraph_format.space_before = Pt(120)
    p_dept.paragraph_format.space_after = Pt(4)
    
    r_d1 = p_dept.add_run("DEPARTMENT OF COMPUTER SCIENCE AND ENGINEERING\n")
    r_d1.bold = True
    r_d1.font.name = 'Times New Roman'
    r_d1.font.size = Pt(13)

    r_d2 = p_dept.add_run("THE NATIONAL INSTITUTE OF ENGINEERING\n")
    r_d2.bold = True
    r_d2.font.name = 'Times New Roman'
    r_d2.font.size = Pt(14)

    r_d3 = p_dept.add_run("(An Autonomous Institution Under VTU)\n")
    r_d3.font.name = 'Times New Roman'
    r_d3.font.size = Pt(12)

    r_d4 = p_dept.add_run("No.50 (Part), Koorgalli village, Hootagalli Industrial Area,\nMysuru-570008 Karnataka\n2026-2027")
    r_d4.font.name = 'Times New Roman'
    r_d4.font.size = Pt(12)

    doc.add_page_break()

    # ==========================================
    # 3. CERTIFICATE (PAGE 4)
    # ==========================================
    p_cert_title = doc.add_paragraph()
    p_cert_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_cert_title.paragraph_format.space_before = Pt(30)
    p_cert_title.paragraph_format.space_after = Pt(24)
    r_ct = p_cert_title.add_run("CERTIFICATE")
    r_ct.bold = True
    r_ct.font.name = 'Times New Roman'
    r_ct.font.size = Pt(16)

    cert_text = (
        "This is to Certify that the project work entitled “MeetFlow: AI-Powered Meeting Intelligence & "
        "Automated Action Tracking System” is a bonafide work carried out by Sakshyam Kataria (4NI23CS001), "
        "[Team Member 2 Name] (4NI23CS002), [Team Member 3 Name] (4NI23CS003), and [Team Member 4 Name] "
        "(4NI23CS004) in fulfillment for major project work, seventh semester, Computer Science and Engineering, "
        "The National Institute of Engineering (Autonomous under VTU) during the academic year 2026–2027. "
        "It is certified that all corrections and suggestions indicated for the Internal Assessment have been "
        "incorporated in the report deposited in the department library. The major project work report has been "
        "approved in fulfillment as per academic regulations of The National Institute of Engineering, Mysuru."
    )
    add_body_p(cert_text, space_after=60)

    # Signature blocks table
    t_sig = doc.add_table(rows=2, cols=3)
    t_sig.alignment = WD_TABLE_ALIGNMENT.CENTER
    t_sig.autofit = False

    sig_headers = [
        "Signature of Internal Guide\n_______________________",
        "Signature of HOD\n_______________________",
        "Signature of Principal\n_______________________"
    ]
    sig_details = [
        "Dr. Naveen S. Pagad\nAssistant Professor\nDept of CS&E\nNIE, Mysuru",
        "Dr. Anitha R\nProfessor and Head\nDept of CS&E\nNIE, Mysuru",
        "Dr. B. S. Nagendra Parashar\nPrincipal\nNIE, Mysuru"
    ]

    for col_idx in range(3):
        c0 = t_sig.cell(0, col_idx)
        c1 = t_sig.cell(1, col_idx)
        c0.width = Inches(2.1)
        c1.width = Inches(2.1)
        
        p0 = c0.paragraphs[0]
        p0.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p0.paragraph_format.space_after = Pt(20)
        r0 = p0.add_run(sig_headers[col_idx])
        r0.bold = True
        r0.font.name = 'Times New Roman'
        r0.font.size = Pt(11)

        p1 = c1.paragraphs[0]
        p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p1.paragraph_format.space_after = Pt(6)
        r1 = p1.add_run(sig_details[col_idx])
        r1.font.name = 'Times New Roman'
        r1.font.size = Pt(10)

    p_exam = doc.add_paragraph()
    p_exam.paragraph_format.space_before = Pt(40)
    p_exam.paragraph_format.space_after = Pt(6)
    r_ex1 = p_exam.add_run("Name of Examiners\t\t\t\t\t\tSignature and Date\n\n")
    r_ex1.bold = True
    r_ex1.font.name = 'Times New Roman'
    r_ex1.font.size = Pt(11)
    r_ex2 = p_exam.add_run("1. _______________________\t\t\t\t_______________________\n\n2. _______________________\t\t\t\t_______________________")
    r_ex2.font.name = 'Times New Roman'
    r_ex2.font.size = Pt(11)

    doc.add_page_break()

    # ==========================================
    # 4. ABSTRACT (PAGES 5-6)
    # ==========================================
    add_chapter_title("ABSTRACT")

    add_body_p(
        "Modern corporate enterprises, municipal governing bodies, research laboratories, and academic institutions "
        "generate hundreds of hours of recorded discussions every week through video conferencing platforms such as "
        "Google Meet, Zoom, and Microsoft Teams. While these discussions contain critical strategic decisions, "
        "commitments, policy enactments, and task assignments, spoken meeting audio remains inherently linear, "
        "unstructured, and non-searchable. Manually reviewing hours of recorded audio to locate a single decision "
        "or identify responsible task owners is exceptionally tedious and error-prone. Existing commercial transcription "
        "services rely heavily on proprietary cloud Speech-to-Text (STT) APIs that impose continuous per-minute metering "
        "fees, expose sensitive institutional conversations to third-party providers, and fail to filter conversational "
        "chatter. Direct prompting of raw, hour-long transcripts into Large Language Models (LLMs) triggers severe token "
        "limits, exhausts free-tier API quotas (such as 15 requests per minute), and burns computational resources on "
        "unproductive discourse."
    )

    add_body_p(
        "To resolve these architectural and financial bottlenecks, this project presents MeetFlow: an end-to-end, "
        "privacy-first, AI-powered meeting and lecture intelligence platform. MeetFlow orchestrates a multi-stage hybrid "
        "pipeline that combines local GPU-accelerated speech recognition, pretrained neural speaker diarization, a custom "
        "domain-adapted machine learning sentence pre-filter, structured executive intelligence extraction, semantic vector "
        "indexing (RAG), unsupervised meeting clustering, and direct calendar synchronization."
    )

    add_body_p(
        "The system operates across two core workflows. In the Audio Ingestion and Transcription workflow, users can upload "
        "audio files (MP3, WAV, M4A, WebM) or capture audio directly from an active browser tab using the browser MediaRecorder "
        "API without deploying intrusive third-party meeting bots. Audio files are persisted in Cloudflare R2 object storage "
        "with zero egress bandwidth fees. The backend pipeline executes local speech-to-text using faster-whisper (large-v3-turbo "
        "quantized to int8 on CUDA), integrated with Silero Voice Activity Detection (VAD) to automatically trim non-speech segments. "
        "Simultaneously, the pyannote/speaker-diarization-3.1 neural pipeline partitions the audio into acoustic speaker turns at an "
        "impressive ~19x faster-than-real-time factor on consumer GPUs (peak VRAM ~1.6 GB). A custom majority-overlap algorithm "
        "accurately aligns acoustic timestamps to Whisper-transcribed sentences."
    )

    add_body_p(
        "In the Intelligence and Synthesis workflow, rather than passing entire conversational transcripts to an LLM, MeetFlow "
        "deploys a lightweight Scikit-Learn classifier (TF-IDF + Logistic Regression with balanced class weighting) trained on "
        "annotated meeting dialogues and formal procedural motions. Achieving an overall accuracy of 83.10% and a Decision F1-score "
        "of 0.88, this pre-filter isolates high-recall candidate sentences and strips 65–80% of conversational noise. A single batched "
        "request to Google Gemini (gemini-2.5-flash) refines and structures the filtered data into executive briefing summaries, "
        "formally resolved decisions with context and decision-makers, prioritized action items with deadlines and assignees, "
        "and descriptive topic tags."
    )

    add_body_p(
        "To enable cross-meeting semantic discovery, the platform generates 768-dimensional embeddings (gemini-embedding-001) and "
        "indexes them in Supabase PostgreSQL using pgvector with Hierarchical Navigable Small World (HNSW) indexing. Users can "
        "interact with an conversational RAG assistant (POST /chat/ask) that enforces strict citation grounding and transparently "
        "refuses ungrounded queries. Unsupervised Spherical K-Means clustering with automated cosine silhouette score optimization "
        "organizes meetings into thematic clusters labeled by Gemini. Finally, 1-click Google Calendar integration enables seamless "
        "scheduling of extracted action items with automated OAuth 2.0 token management."
    )

    add_body_p(
        "The complete system is implemented using FastAPI (Python 3.11) for backend services, React 19 and Tailwind CSS for an "
        "editorial, information-dense frontend, Supabase PostgreSQL for relational and vector storage, and Cloudflare R2 for media "
        "persistence. Experimental evaluation confirms that MeetFlow delivers corporate-grade transcription fidelity, sub-second "
        "vector retrieval, and zero cloud STT operational costs, demonstrating the viability of hybrid edge-cloud architectures "
        "for conversational intelligence."
    )

    doc.add_page_break()

    # ==========================================
    # 5. ACKNOWLEDGEMENT (PAGE 6)
    # ==========================================
    add_chapter_title("ACKNOWLEDGEMENT")

    add_body_p(
        "The satisfaction that accompanies the successful completion of any task would be incomplete without mentioning "
        "the people whose continuous cooperation, guidance, and encouragement made it possible."
    )
    add_body_p(
        "First and foremost, we would like to express our sincere gratitude to our beloved Principal, Dr. B. S. Nagendra Parashar, "
        "for providing us with the facilities and academic environment necessary to carry out this project successfully."
    )
    add_body_p(
        "We would like to express our sincere gratitude to our Head of the Department, Dr. Anitha R, Department of Computer Science "
        "and Engineering, The National Institute of Engineering, Mysuru, for the continuous support and encouragement provided "
        "throughout the project."
    )
    add_body_p(
        "We express our heartfelt gratitude to our project guide, Dr. Naveen S. Pagad, Assistant Professor, Department of Computer "
        "Science and Engineering, NIE, Mysuru, for valuable guidance, constructive suggestions, technical support, and constant "
        "encouragement throughout the development of the project."
    )
    add_body_p(
        "We would also like to thank all the faculty members and staff of the Department of Computer Science and Engineering for "
        "their valuable support and assistance."
    )
    add_body_p(
        "Finally, we would like to thank our friends and family members for their encouragement and support during the development "
        "and documentation of this project."
    )

    p_ack_names = doc.add_paragraph()
    p_ack_names.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p_ack_names.paragraph_format.space_before = Pt(40)
    p_ack_names.paragraph_format.space_after = Pt(2)
    r_an = p_ack_names.add_run(
        "Sakshyam Kataria (4NI23CS001)\n"
        "[Team Member 2 Name] (4NI23CS002)\n"
        "[Team Member 3 Name] (4NI23CS003)\n"
        "[Team Member 4 Name] (4NI23CS004)\n"
    )
    r_an.bold = True
    r_an.font.name = 'Times New Roman'
    r_an.font.size = Pt(11)

    doc.add_page_break()

    # ==========================================
    # 6. CONTENTS & LIST OF FIGURES (PAGES 7-8)
    # ==========================================
    add_chapter_title("CONTENTS")

    toc_items = [
        ("1. Introduction", "8"),
        ("    1.1 Overview", "8"),
        ("    1.2 Objective", "8"),
        ("    1.3 Scope of the Project", "9"),
        ("    1.4 Existing System and Drawbacks", "10"),
        ("    1.5 Proposed System", "11"),
        ("    1.6 Advantages of the Proposed System", "11"),
        ("2. Literature Survey", "13"),
        ("    2.1 Automated Speech Recognition & Acoustic Processing", "13"),
        ("    2.2 Neural Speaker Diarization & Voice Attribution", "13"),
        ("    2.3 Retrieval-Augmented Generation & Vector Search", "13"),
        ("    2.4 Large Language Models for Conversational Intelligence", "14"),
        ("    2.5 Multi-Speaker Dialogue Analysis & Semantic Clustering", "14"),
        ("3. System Requirements and Specifications", "15"),
        ("    3.1 Software Requirements", "15"),
        ("    3.2 Hardware Requirements", "15"),
        ("    3.3 Functional Requirements", "15"),
        ("    3.4 Non-Functional Requirements", "17"),
        ("4. System Design and Analysis", "18"),
        ("    4.1 High-Level Architecture", "18"),
        ("    4.2 Use Case Diagram", "18"),
        ("    4.3 Data Flow Diagram", "19"),
        ("    4.4 Sequence Diagram", "20"),
        ("    4.5 Database Design", "20"),
        ("5. Implementation", "22"),
        ("    5.1 Implementation", "22"),
        ("        5.1.1 Authentication & Workspace Module", "22"),
        ("        5.1.2 Audio Ingestion & Cloudflare R2 Storage", "22"),
        ("        5.1.3 Local Speech-to-Text via Faster-Whisper", "22"),
        ("        5.1.4 Neural Speaker Diarization via PyAnnote 3.1", "23"),
        ("        5.1.5 Majority-Overlap Alignment Pipeline", "23"),
        ("        5.1.6 Hybrid ML Candidate Pre-Filtering", "24"),
        ("        5.1.7 Google Gemini Structured Extraction", "24"),
        ("        5.1.8 Vector Embeddings & pgvector Semantic Search", "24"),
        ("        5.1.9 Thematic Meeting Clustering", "25"),
        ("        5.1.10 Google Calendar OAuth 2.0 Integration", "25"),
        ("        5.1.11 Interactive Grounded Meeting Q&A (RAG)", "26"),
        ("        5.1.12 Error Handling and Resilience", "26"),
        ("6. Testing", "27"),
        ("    6.1 Types of Testing", "27"),
        ("    6.2 Sample Test Cases", "28"),
        ("    6.3 Error Handling Testing", "28"),
        ("7. Results and Discussions", "30"),
        ("    7.1 User Authentication & Workspace Interface", "30"),
        ("    7.2 Audio Upload and In-Browser Tab Capture", "30"),
        ("    7.3 Executive Meeting Dashboard & Overview", "30"),
        ("    7.4 Interactive Transcript with Speaker Diarization", "31"),
        ("    7.5 Executive Summary & Key Points Extraction", "31"),
        ("    7.6 Decision Log & Action Item Tracking", "31"),
        ("    7.7 Google Calendar Task Synchronization", "32"),
        ("    7.8 Semantic Search across Meeting Archives", "32"),
        ("    7.9 Thematic Meeting Clustering Results", "32"),
        ("    7.10 Grounded Conversational Q&A Assistant", "33"),
        ("    7.11 Performance Metrics", "33"),
        ("    7.12 Visualization Results", "34"),
        ("8. References", "35")
    ]

    t_toc = doc.add_table(rows=len(toc_items) + 1, cols=2)
    t_toc.alignment = WD_TABLE_ALIGNMENT.CENTER
    t_toc.autofit = False

    t_toc.cell(0, 0).width = Inches(5.5)
    t_toc.cell(0, 1).width = Inches(1.0)
    p_th0 = t_toc.cell(0, 0).paragraphs[0]
    r_th0 = p_th0.add_run("CONTENTS")
    r_th0.bold = True
    r_th0.font.name = 'Times New Roman'
    p_th1 = t_toc.cell(0, 1).paragraphs[0]
    p_th1.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r_th1 = p_th1.add_run("PAGE NO")
    r_th1.bold = True
    r_th1.font.name = 'Times New Roman'

    for idx, (title, page) in enumerate(toc_items, start=1):
        c0 = t_toc.cell(idx, 0)
        c1 = t_toc.cell(idx, 1)
        c0.width = Inches(5.5)
        c1.width = Inches(1.0)
        p0 = c0.paragraphs[0]
        p0.paragraph_format.space_after = Pt(2)
        r0 = p0.add_run(title)
        r0.font.name = 'Times New Roman'
        r0.font.size = Pt(11)
        if not title.startswith(" "):
            r0.bold = True

        p1 = c1.paragraphs[0]
        p1.paragraph_format.space_after = Pt(2)
        p1.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        r1 = p1.add_run(page)
        r1.font.name = 'Times New Roman'
        r1.font.size = Pt(11)

    doc.add_page_break()

    # List of Figures
    add_chapter_title("LIST OF FIGURES")

    lof_items = [
        ("Fig 4.1", "High-Level Architecture", "18"),
        ("Fig 4.2", "Use Case Diagram", "18"),
        ("Fig 4.3", "Data Flow Diagram", "19"),
        ("Fig 4.4", "Sequence Diagram", "20"),
        ("Fig 4.5", "Database/Entity Relationship Design", "21"),
        ("Fig 7.1", "Workspace & Authentication Interface", "30"),
        ("Fig 7.2", "Audio Ingestion & Tab Recording Interface", "30"),
        ("Fig 7.3", "Executive Meeting Dashboard & Overview", "30"),
        ("Fig 7.4", "Interactive Transcript with Speaker Diarization", "31"),
        ("Fig 7.5", "Executive Summary & Key Points Extraction", "31"),
        ("Fig 7.6", "Formal Decision Log & Action Item Manager", "31"),
        ("Fig 7.7", "Google Calendar Task Synchronization", "32"),
        ("Fig 7.8", "Cosine Similarity Vector Search Interface", "32"),
        ("Fig 7.9", "Unsupervised Thematic Meeting Clusters", "32"),
        ("Fig 7.10", "Grounded Conversational Q&A Assistant", "33")
    ]

    t_lof = doc.add_table(rows=len(lof_items) + 1, cols=3)
    t_lof.alignment = WD_TABLE_ALIGNMENT.CENTER
    t_lof.autofit = False

    t_lof.cell(0, 0).width = Inches(1.3)
    t_lof.cell(0, 1).width = Inches(4.2)
    t_lof.cell(0, 2).width = Inches(1.0)
    
    t_lof.cell(0, 0).paragraphs[0].add_run("Figure No").bold = True
    t_lof.cell(0, 1).paragraphs[0].add_run("Figure Name").bold = True
    p_lh2 = t_lof.cell(0, 2).paragraphs[0]
    p_lh2.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p_lh2.add_run("Page No").bold = True

    for idx, (f_num, f_name, f_page) in enumerate(lof_items, start=1):
        c0 = t_lof.cell(idx, 0)
        c1 = t_lof.cell(idx, 1)
        c2 = t_lof.cell(idx, 2)
        c0.width = Inches(1.3)
        c1.width = Inches(4.2)
        c2.width = Inches(1.0)
        
        p0 = c0.paragraphs[0]
        p0.paragraph_format.space_after = Pt(2)
        r0 = p0.add_run(f_num)
        r0.font.name = 'Times New Roman'
        r0.font.size = Pt(11)

        p1 = c1.paragraphs[0]
        p1.paragraph_format.space_after = Pt(2)
        r1 = p1.add_run(f_name)
        r1.font.name = 'Times New Roman'
        r1.font.size = Pt(11)

        p2 = c2.paragraphs[0]
        p2.paragraph_format.space_after = Pt(2)
        p2.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        r2 = p2.add_run(f_page)
        r2.font.name = 'Times New Roman'
        r2.font.size = Pt(11)

    doc.add_page_break()

    # ==========================================
    # CHAPTER 1: INTRODUCTION
    # ==========================================
    add_chapter_title("CHAPTER 1\nINTRODUCTION")

    add_section_heading("1.1 Overview")
    add_body_p(
        "The contemporary operational landscape of modern businesses, public administration councils, and educational "
        "institutions relies heavily on spoken collaboration. Daily stand-ups, strategic board meetings, municipal council "
        "hearings, and academic lectures produce vast quantities of high-value conversational content. Spoken dialogue "
        "is the primary medium where consensus is negotiated, strategic pivots are executed, and operational assignments "
        "are distributed. However, once a meeting concludes, this wealth of spoken knowledge is locked in linear audio or "
        "video recordings that are inherently opaque and non-searchable. Stakeholders frequently spend valuable hours scrubbing "
        "through recordings or relying on fragmented personal notes to verify exact decisions or track pending action items."
    )
    add_body_p(
        "MeetFlow is an artificial intelligence-powered meeting and lecture intelligence platform designed to eliminate "
        "this information loss. By orchestrating a multi-stage architecture spanning local speech recognition, neural speaker "
        "diarization, domain-adapted machine learning pre-filtering, generative large language models, and relational vector "
        "indexing, MeetFlow transforms raw audio streams into structured, actionable, and searchable executive intelligence."
    )
    add_body_p(
        "Unlike conventional transcription tools that act merely as passive speech-to-text converters, MeetFlow provides "
        "end-to-end intelligence synthesis. The platform automatically extracts concise executive summaries, identifies formal "
        "decisions with full organizational context, extracts prioritized action items with assigned owners and deadlines, and "
        "seamlessly synchronizes those deliverables directly into users' Google Calendars. Furthermore, MeetFlow introduces a "
        "conversational Retrieval-Augmented Generation (RAG) assistant that allows users to ask complex questions across their "
        "entire meeting archive with rigorous timestamp and speaker citation grounding."
    )

    add_section_heading("1.2 Objective")
    add_body_p(
        "The primary objective of MeetFlow is to develop an automated, privacy-conscious, and cost-effective meeting intelligence "
        "platform that extracts structured executive insights from multi-speaker conversational audio and bridges the gap "
        "between discussion and task execution."
    )
    add_body_p("The major objectives of the project are:")
    objectives = [
        "To develop an end-to-end, multi-stage conversational intelligence and transcription platform.",
        "To ingest recorded audio files across multiple formats (MP3, WAV, M4A, WebM) with cloud object storage persistence.",
        "To capture live meeting audio directly from browser tabs using standard Web Media APIs without requiring meeting bots.",
        "To perform high-fidelity speech-to-text locally using faster-whisper with int8 quantization to eliminate API metering costs.",
        "To partition multi-speaker audio using the neural pyannote.audio 3.1 pipeline at high real-time performance factors.",
        "To accurately align acoustic speaker timestamps with transcribed sentences using a majority-overlap algorithmic engine.",
        "To provide an interactive transcript viewer supporting user-defined custom speaker re-attribution and talk-time analytics.",
        "To design and train a domain-adapted hybrid ML classifier (TF-IDF + Logistic Regression) to filter conversational noise.",
        "To extract executive summaries, key discussion points, formal decisions, and action items via batched Google Gemini LLM.",
        "To index meeting transcripts and intelligence into 768-dimensional vector embeddings using gemini-embedding-001.",
        "To implement high-speed approximate nearest neighbor vector search using PostgreSQL pgvector with HNSW indexing.",
        "To provide a conversational RAG meeting assistant (POST /chat/ask) with strict citation grounding and hallucination refusal.",
        "To perform unsupervised semantic meeting grouping using Spherical K-Means with cosine silhouette score optimization.",
        "To generate automated 2–4 word descriptive category labels for meeting clusters using generative language modeling.",
        "To integrate Google Calendar OAuth 2.0 with server-side encrypted token storage and automated token refresh mechanisms.",
        "To enable 1-click scheduling of extracted action items directly into users' primary Google Calendars.",
        "To build a responsive, information-dense, editorial user interface using React 19, TypeScript, and Tailwind CSS.",
        "To implement robust error handling, transient failure retries, and comprehensive audio validation safeguards."
    ]
    for idx, obj in enumerate(objectives, start=1):
        add_numbered_item(f"{idx}.", obj)

    add_section_heading("1.3 Scope of the Project")
    add_body_p(
        "The scope of MeetFlow encompasses the complete lifecycle of meeting audio, from initial acoustic ingestion to final "
        "actionable calendar execution and historical conversational discovery:"
    )
    scopes = [
        ("Audio Ingestion & Media Capture: ", "Accepts uploaded audio files in MP3, WAV, M4A, and WebM formats up to 25 MB, and captures live audio streams from browser tabs via navigator.mediaDevices.getDisplayMedia."),
        ("Cloud Object Storage Persistence: ", "Stores uploaded and captured audio assets in Cloudflare R2 object storage with presigned URLs and zero egress bandwidth costs."),
        ("Local Acoustic Processing & STT: ", "Executes faster-whisper (large-v3-turbo, int8 CUDA) combined with Silero VAD to produce timestamped transcriptions with low VRAM footprint (<2 GB)."),
        ("Neural Speaker Diarization: ", "Applies pyannote/speaker-diarization-3.1 to distinguish distinct acoustic speakers and calculate speech durations, percentage shares, and turn metrics."),
        ("Hybrid Machine Learning Pre-Filter: ", "Classifies every sentence into Action Item, Decision, or Discussion using Scikit-Learn TF-IDF + Logistic Regression to discard conversational filler."),
        ("Structured Intelligence Extraction: ", "Leverages Google Gemini (gemini-2.5-flash) to synthesize structured executive takeaways, decisions with context, prioritized tasks, and meeting tags."),
        ("Vector Memory & Conversational RAG: ", "Generates 768-dimensional embeddings and stores them in Supabase PostgreSQL pgvector with HNSW indexing to power natural language search across meetings."),
        ("Thematic Clustering: ", "Groups related meetings using Spherical K-Means clustering in cosine space, optimizing the number of clusters via silhouette analysis and generating descriptive labels."),
        ("Actionable Calendar Scheduling: ", "Integrates with Google Calendar API v3 via OAuth 2.0 to allow one-click task scheduling with automatic deadline calculation and token refresh.")
    ]
    for idx, (title, desc) in enumerate(scopes, start=1):
        add_numbered_item(f"{idx}.", desc, bold_prefix=title)

    add_section_heading("1.4 Existing System and Drawbacks")
    add_body_p(
        "Existing commercial and open-source solutions for meeting management typically fall into three fragmented categories: "
        "standalone cloud transcription APIs, automated meeting recording bots, and generic LLM-based summary tools. While functional "
        "in isolation, these approaches introduce severe financial, privacy, and architectural drawbacks:"
    )
    drawbacks = [
        ("Prohibitive Cloud STT Metering Costs: ", "Commercial cloud speech APIs (such as Google Cloud Speech-to-Text or AWS Transcribe) charge between $0.016 and $0.024 per minute of audio. For an organization recording 100 hours of meetings monthly, annual transcription costs quickly escalate to thousands of dollars, making high-volume transcription financially unsustainable."),
        ("Privacy & Security Exposure: ", "Transmitting unencrypted meeting recordings containing confidential intellectual property, strategic decisions, or municipal deliberations to third-party cloud transcription providers poses significant compliance and security risks."),
        ("Intrusive Meeting Recording Bots: ", "Platforms such as Otter.ai or Fireflies.ai rely on automated bots that join video calls as artificial participants. Many corporate security firewalls block these bots, and participants often find artificial recording avatars distracting or intrusive."),
        ("LLM Rate Limits & Token Wastage: ", "Directly submitting raw 60-minute transcripts (often containing 8,000–12,000 words) into commercial LLMs triggers severe rate limits (e.g., 15 RPM on free tiers) and burns computational tokens on small talk and conversational filler, which constitutes 65–80% of typical meeting dialogue."),
        ("Lack of Speaker Attribution & Alignment: ", "Standard Whisper implementations output raw text without speaker identities. While human note-takers require speaker attribution to understand who made commitments, conventional acoustic clustering (MFCC + K-Means) breaks down under background noise and reverberation."),
        ("Lack of Actionable Follow-Through: ", "Standard summary tools output static bullet points in a document. Action items remain disconnected from users' task managers or calendar scheduling systems, resulting in missed deadlines and unfulfilled commitments."),
        ("Hallucinatory & Ungrounded AI Search: ", "Generic chatbots answering queries about meeting archives frequently hallucinate answers or blend details from unrelated sessions because they lack strict citation grounding and vector similarity gating."),
        ("Architectural Database Fragmentation: ", "Many AI applications deploy a separate vector database (e.g., Pinecone) alongside a relational database. This introduces data synchronization drift, multi-service network latency, and complex dual-database management.")
    ]
    for idx, (title, desc) in enumerate(drawbacks, start=1):
        add_numbered_item(f"{idx}.", desc, bold_prefix=title)

    add_section_heading("1.5 Proposed System")
    add_body_p(
        "MeetFlow is proposed as an integrated, multi-stage conversational intelligence platform that completely circumvents the "
        "limitations of existing systems. It unifies local GPU speech recognition, neural diarization, domain-adapted machine "
        "learning filtering, batched generative extraction, pgvector semantic search, and calendar integration into a unified system."
    )
    add_body_p(
        "The proposed system is structured around three primary functional workflows:"
    )
    add_sub_heading("Workflow 1 – Audio Ingestion and Local Transcription Pipeline")
    add_body_p(
        "The user uploads an audio recording or initiates live browser tab capture. The media is persisted in Cloudflare R2 object "
        "storage, and an asynchronous background worker is spawned. The worker executes faster-whisper (large-v3-turbo, int8 quantization "
        "on CUDA) alongside Silero VAD, converting speech to text at 4x real-time speed. In parallel, pyannote.audio 3.1 performs "
        "neural speaker diarization at 19x real-time speed. A majority-overlap alignment algorithm calculates the intersection "
        "between diarization intervals and Whisper sentence boundaries, producing a structured transcript where every sentence is "
        "tagged with start/end timestamps and acoustic speaker identities."
    )
    add_sub_heading("Workflow 2 – Two-Stage Hybrid Intelligence and Structured Extraction")
    add_body_p(
        "To prevent LLM token exhaustion, the aligned sentences are fed into a local Scikit-Learn TF-IDF + Logistic Regression classifier. "
        "This model evaluates linguistic patterns and classifies sentences into Action Item, Decision, or Discussion candidates. "
        "Sentences flagged with high decision/action probabilities, along with surrounding context, are bundled into a single batched "
        "prompt to Google Gemini. Gemini refines the candidates into executive takeaways, formally resolved decisions, and prioritized "
        "action items with assignees and due dates, returning validated structured JSON."
    )
    add_sub_heading("Workflow 3 – Unified Relational Vector Memory and Calendar Actioning")
    add_body_p(
        "All meeting metadata, transcripts, decisions, and action items are saved to Supabase PostgreSQL. Gemini-generated 768-dimensional "
        "embeddings are indexed using pgvector with HNSW index architecture. Users can execute sub-second cosine semantic search, cluster "
        "related meetings into thematic topics via Spherical K-Means, ask natural language questions via a grounded conversational RAG "
        "assistant, and push scheduled action items to Google Calendar with a single click."
    )

    add_section_heading("1.6 Advantages of the Proposed System")
    add_body_p("The key advantages of the MeetFlow platform include:")
    advantages = [
        ("Zero Cloud STT Operational Costs: ", "Local faster-whisper execution on consumer GPUs eliminates continuous per-minute cloud transcription fees."),
        ("Complete Audio Privacy: ", "Spoken audio is processed locally on-premise/host GPU and stored in private S3-compatible R2 storage, preventing exposure of confidential discussions."),
        ("High-Speed Neural Diarization: ", "PyAnnote 3.1 processes meeting audio at 19.1x faster than real-time (a 34-minute meeting diarized in under 2 minutes)."),
        ("Noise-Filtered LLM Invocation: ", "The hybrid ML classifier filters 65–80% of conversational noise, reducing LLM token consumption and preventing API rate-limit throttling."),
        ("Domain-Adapted Accuracy: ", "Retrained with procedural meeting motions, the ML classifier achieves an 88.0% F1-score on formal decisions and 83.1% overall accuracy."),
        ("Unified Database Architecture: ", "Supabase PostgreSQL with pgvector unifies relational business data, speaker statistics, and vector embeddings in a single ACID-compliant database."),
        ("Sub-Millisecond Vector Retrieval: ", "HNSW indexing provides logarithmic similarity search scaling without requiring manual index rebuilding."),
        ("Strict RAG Citation Grounding: ", "The conversational chat engine refuses ungrounded queries and cites exact meeting titles and timestamps for every answer."),
        ("Automated Thematic Discovery: ", "Spherical K-Means with cosine silhouette score optimization groups meetings into topics without requiring manual categorization."),
        ("1-Click Calendar Synchronization: ", "Seamless Google Calendar OAuth 2.0 integration bridges the gap between conversational commitments and real-world execution."),
        ("Bot-Free Browser Capture: ", "Direct tab audio recording via MediaRecorder API eliminates the need for intrusive, firewall-blocked meeting bots."),
        ("Customizable Speaker Re-Attribution: ", "Users can rename auto-detected speaker clusters (e.g., 'SPEAKER_00' to 'Alice'), automatically updating historical transcripts."),
        ("Comprehensive Talk-Time Analytics: ", "Calculates talk-time duration, percentage speaking share, and turn counts per speaker for meeting balance evaluation."),
        ("Robust Fault Tolerance: ", "Built-in exponential backoff retries, CPU fallbacks for GPU inference, and presigned streaming URLs guarantee high system resilience."),
        ("Information-Dense Human Design: ", "The frontend avoids superficial AI aesthetics, offering an editorial, restrained layout designed for rapid executive scanning.")
    ]
    for idx, (title, desc) in enumerate(advantages, start=1):
        add_numbered_item(f"{idx}.", desc, bold_prefix=title)

    doc.add_page_break()

    # ==========================================
    # CHAPTER 2: LITERATURE SURVEY
    # ==========================================
    add_chapter_title("CHAPTER 2\nLITERATURE SURVEY")

    add_section_heading("2.1 Automated Speech Recognition & Acoustic Processing")
    add_body_p(
        "Automated Speech Recognition (ASR) has undergone a fundamental transformation with the advent of deep sequence-to-sequence "
        "transformer architectures trained on massive weakly supervised web audio datasets. Radford et al. (2022) introduced OpenAI "
        "Whisper, demonstrating that multi-task encoder-decoder models trained on 680,000 hours of multilingual audio generalize "
        "exceptionally well to diverse accents, background noise, and specialized technical terminology without fine-tuning. "
        "However, standard PyTorch implementations of Whisper suffer from substantial computational overhead, high GPU memory "
        "footprints (requiring 8–10 GB VRAM for large-v3), and slow inference speeds that hinder real-time deployment."
    )
    add_body_p(
        "To mitigate these computational barriers, Klein et al. (2020) developed CTranslate2, an optimized C++ inference library "
        "supporting weight quantization (int8, int16), layer fusion, and custom CUDA kernels for Transformer models. When applied to "
        "Whisper as faster-whisper, inference latency is reduced by up to 4x while GPU memory consumption drops to under 2 GB, "
        "making state-of-the-art transcription feasible on consumer-grade hardware."
    )
    add_sub_heading("Relevance to MeetFlow:")
    add_body_p(
        "MeetFlow integrates faster-whisper (large-v3-turbo with int8 quantization on CUDA) coupled with Silero Voice Activity "
        "Detection (VAD). This enables corporate-grade transcription fidelity at zero cloud API cost with minimal hardware requirements."
    )

    add_section_heading("2.2 Neural Speaker Diarization & Voice Attribution")
    add_body_p(
        "Speaker diarization—the task of partitioning an audio stream into homogeneous segments according to 'who spoke when'—is "
        "vital for multi-speaker conversational analysis. Traditional diarization pipelines relied on Mel-Frequency Cepstral Coefficients "
        "(MFCCs), Gaussian Mixture Models (GMMs), and agglomerative hierarchical clustering. These acoustic pipelines frequently break down "
        "in real-world meeting scenarios due to overlapping speech, acoustic reverberation, and dynamic vocal intensity variations."
    )
    add_body_p(
        "Bredin et al. (2020, 2023) pioneered end-to-end neural speaker diarization with the pyannote.audio framework. Pyannote utilizes "
        "neural voice embedding extractors trained with additive angular margin loss to generate compact, discriminative speaker embeddings. "
        "The pyannote 3.1 pipeline achieves state-of-the-art Diarization Error Rate (DER) benchmarks while exhibiting high inference speed "
        "on modern GPUs. Nevertheless, neural diarization produces continuous time intervals rather than linguistic tokens, necessitating "
        "specialized alignment mechanisms to map speaker labels to transcribed words."
    )
    add_sub_heading("Relevance to MeetFlow:")
    add_body_p(
        "MeetFlow deploys pyannote/speaker-diarization-3.1 on CUDA, achieving an operating factor of 19.1x faster than real-time. "
        "The system introduces a proprietary majority-overlap interval algorithm to align acoustic speaker turns with Whisper sentences."
    )

    add_section_heading("2.3 Retrieval-Augmented Generation & Vector Search")
    add_body_p(
        "Large Language Models exhibit impressive linguistic capabilities but are susceptible to factual hallucinations and lack "
        "access to private, dynamic institutional knowledge. Lewis et al. (2020) proposed Retrieval-Augmented Generation (RAG), "
        "a framework that combines parametric neural memory (the LLM) with non-parametric retrieval memory (a vector database). In a "
        "RAG architecture, text passages are converted into dense vector embeddings using embedding models (Reimers & Gurevych, 2019). "
        "Given a user query, semantic similarity search retrieves the most relevant document chunks to construct a factual context "
        "prompt for LLM generation."
    )
    add_body_p(
        "For scalable vector search, Malkov & Yashunin (2018) introduced Hierarchical Navigable Small World (HNSW) graphs. HNSW constructs "
        "a multi-layer graph that enables logarithmic-time Approximate Nearest Neighbor (ANN) search, outperforming traditional inverted "
        "file indexing (IVFFlat) in both recall and query latency. The integration of the pgvector extension into PostgreSQL allows "
        "developers to execute relational queries and HNSW vector searches within a single ACID-compliant database engine."
    )
    add_sub_heading("Relevance to MeetFlow:")
    add_body_p(
        "MeetFlow utilizes gemini-embedding-001 to generate 768-dimensional embeddings of all meeting segments, indexing them in "
        "Supabase PostgreSQL with pgvector HNSW indexes. This enables cross-meeting semantic search and citation-grounded conversational Q&A."
    )

    add_section_heading("2.4 Large Language Models for Conversational Intelligence")
    add_body_p(
        "Recent advancements in generative autoregressive transformers, including Google Gemini and OpenAI GPT-4, have demonstrated "
        "exceptional reasoning capabilities in document summarization, information extraction, and intent classification. However, "
        "relying solely on LLMs for processing conversational transcripts presents significant operational challenges. Spoken dialogue "
        "is notoriously redundant, with 65–80% of utterances consisting of phatic pleasantries, conversational filler, and administrative "
        "digressions. Directly passing uncurated transcripts to LLMs incurs high inference costs, induces latency, and frequently triggers "
        "rate limits on developer API tiers."
    )
    add_body_p(
        "Hybrid natural language architectures address this inefficiency by combining lightweight traditional machine learning classifiers "
        "with deep generative models. A fast discriminative model filters raw text to identify candidate sentences of interest, allowing "
        "the generative model to focus its reasoning budget exclusively on high-relevance semantic information."
    )
    add_sub_heading("Relevance to MeetFlow:")
    add_body_p(
        "MeetFlow implements a two-stage hybrid intelligence pipeline. A local Scikit-Learn TF-IDF + Logistic Regression model acts as a "
        "high-recall noise filter, after which Google Gemini performs batched executive synthesis and structured JSON generation."
    )

    add_section_heading("2.5 Multi-Speaker Dialogue Analysis & Semantic Clustering")
    add_body_p(
        "Organizing multi-session conversational archives requires unsupervised document clustering. Traditional approaches such as "
        "Latent Dirichlet Allocation (LDA) rely on term co-occurrence frequencies and struggle with conversational text where colloquial "
        "synonyms abound. Density-based clustering algorithms such as HDBSCAN identify arbitrary cluster shapes but frequently designate "
        "30–50% of small-scale corpora as 'noise', leaving vital meetings unorganized."
    )
    add_body_p(
        "Spherical K-Means clustering represents documents on a unit hypersphere by applying L2-normalization to dense neural embeddings. "
        "In this normalized space, Euclidean distance is monotonically related to cosine similarity, enabling efficient and cohesive "
        "semantic grouping of document vectors. Evaluating clustering partitions across varying values of k using the Silhouette Coefficient "
        "(Rousseeuw, 1987) allows for automated determination of optimal cluster counts."
    )
    add_sub_heading("Relevance to MeetFlow:")
    add_body_p(
        "MeetFlow implements Spherical K-Means clustering with automated cosine silhouette score optimization to categorize meeting archives "
        "into thematic clusters, subsequently utilizing Google Gemini to synthesize human-readable cluster topic labels."
    )

    doc.add_page_break()

    # ==========================================
    # CHAPTER 3: SYSTEM REQUIREMENTS AND SPECIFICATIONS
    # ==========================================
    add_chapter_title("CHAPTER 3\nSYSTEM REQUIREMENTS AND SPECIFICATIONS")

    add_section_heading("3.1 Software Requirements")
    add_body_p("The software components and technologies utilized across the MeetFlow platform are specified in Table 3.1:")

    sw_data = [
        ("Operating System", "Windows 10/11 (64-bit) or Ubuntu 22.04 LTS"),
        ("Programming Languages", "Python 3.11 (Backend), TypeScript / JavaScript (Frontend)"),
        ("Backend Framework", "FastAPI (Asynchronous REST API)"),
        ("Frontend Framework", "React 19 + Vite"),
        ("Styling & Design System", "Tailwind CSS v4 + Lucide React Icons"),
        ("Speech-to-Text Engine", "faster-whisper (large-v3-turbo, int8 CUDA)"),
        ("Voice Activity Detection", "Silero VAD"),
        ("Speaker Diarization", "pyannote.audio 3.1 (Hugging Face Pipeline)"),
        ("Deep Learning Framework", "PyTorch 2.4+ with CUDA 12.1 / 12.4 acceleration"),
        ("Machine Learning Classifier", "Scikit-Learn (TF-IDF Vectorizer + Logistic Regression)"),
        ("Generative AI (LLM)", "Google Gemini (gemini-2.5-flash via google-genai SDK)"),
        ("Vector Embedding Model", "Google gemini-embedding-001 (768 dimensions)"),
        ("Relational & Vector Database", "Supabase PostgreSQL with pgvector extension"),
        ("Database Indexing Method", "Hierarchical Navigable Small World (HNSW) Indexing"),
        ("Object Storage", "Cloudflare R2 (S3-Compatible Object Storage via boto3)"),
        ("Calendar Synchronization", "Google Calendar API v3 (OAuth 2.0 with Auto Refresh)"),
        ("Audio Ingestion APIs", "Browser MediaRecorder API & getDisplayMedia()"),
        ("Serialization & Validation", "Pydantic v2"),
        ("Clustering Engine", "Scikit-Learn Spherical K-Means + Silhouette Optimizer")
    ]

    t_sw = doc.add_table(rows=len(sw_data) + 1, cols=2)
    t_sw.alignment = WD_TABLE_ALIGNMENT.CENTER
    t_sw.autofit = False

    t_sw.cell(0, 0).width = Inches(2.5)
    t_sw.cell(0, 1).width = Inches(4.0)
    set_cell_shading(t_sw.cell(0, 0), "E2E8F0")
    set_cell_shading(t_sw.cell(0, 1), "E2E8F0")
    t_sw.cell(0, 0).paragraphs[0].add_run("Component").bold = True
    t_sw.cell(0, 1).paragraphs[0].add_run("Technology / Specification").bold = True

    for idx, (comp, tech) in enumerate(sw_data, start=1):
        c0 = t_sw.cell(idx, 0)
        c1 = t_sw.cell(idx, 1)
        c0.width = Inches(2.5)
        c1.width = Inches(4.0)
        set_cell_borders(c0)
        set_cell_borders(c1)
        p0 = c0.paragraphs[0]
        p0.paragraph_format.space_after = Pt(2)
        r0 = p0.add_run(comp)
        r0.font.size = Pt(10)
        r0.bold = True
        p1 = c1.paragraphs[0]
        p1.paragraph_format.space_after = Pt(2)
        r1 = p1.add_run(tech)
        r1.font.size = Pt(10)

    p_sw_cap = doc.add_paragraph()
    p_sw_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_sw_cap.paragraph_format.space_before = Pt(4)
    p_sw_cap.paragraph_format.space_after = Pt(14)
    r_sc = p_sw_cap.add_run("Table 3.1 – Software Requirements")
    r_sc.bold = True
    r_sc.italic = True
    r_sc.font.size = Pt(10)

    add_section_heading("3.2 Hardware Requirements")
    add_body_p("The recommended hardware configuration for hosting and running MeetFlow is specified in Table 3.2:")

    hw_data = [
        ("Host Processor (CPU)", "Intel Core i5 (10th Gen+) / AMD Ryzen 5 or equivalent"),
        ("System Memory (RAM)", "16 GB DDR4 minimum (32 GB recommended for concurrency)"),
        ("Dedicated Graphics (GPU)", "NVIDIA GeForce RTX 3050 (4 GB VRAM) minimum;\nRTX 3060 / 4060 (6–8 GB VRAM) recommended"),
        ("CUDA Compute Capability", "Version 7.5 or higher (Compute capability for CTranslate2)"),
        ("Disk Storage", "512 GB NVMe SSD (minimum 50 GB free for model weights)"),
        ("Network Interface", "Broadband Internet connection (minimum 10 Mbps)"),
        ("Audio Input Device", "Microphone / Stereo Mix or browser tab audio stream"),
        ("Client Browser", "Modern browser supporting Web Audio and MediaRecorder APIs (Chrome 110+, Edge 110+, Brave)")
    ]

    t_hw = doc.add_table(rows=len(hw_data) + 1, cols=2)
    t_hw.alignment = WD_TABLE_ALIGNMENT.CENTER
    t_hw.autofit = False

    t_hw.cell(0, 0).width = Inches(2.5)
    t_hw.cell(0, 1).width = Inches(4.0)
    set_cell_shading(t_hw.cell(0, 0), "E2E8F0")
    set_cell_shading(t_hw.cell(0, 1), "E2E8F0")
    t_hw.cell(0, 0).paragraphs[0].add_run("Component").bold = True
    t_hw.cell(0, 1).paragraphs[0].add_run("Hardware Specification").bold = True

    for idx, (comp, req) in enumerate(hw_data, start=1):
        c0 = t_hw.cell(idx, 0)
        c1 = t_hw.cell(idx, 1)
        c0.width = Inches(2.5)
        c1.width = Inches(4.0)
        set_cell_borders(c0)
        set_cell_borders(c1)
        p0 = c0.paragraphs[0]
        p0.paragraph_format.space_after = Pt(2)
        r0 = p0.add_run(comp)
        r0.font.size = Pt(10)
        r0.bold = True
        p1 = c1.paragraphs[0]
        p1.paragraph_format.space_after = Pt(2)
        r1 = p1.add_run(req)
        r1.font.size = Pt(10)

    p_hw_cap = doc.add_paragraph()
    p_hw_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_hw_cap.paragraph_format.space_before = Pt(4)
    p_hw_cap.paragraph_format.space_after = Pt(14)
    r_hc = p_hw_cap.add_run("Table 3.2 – Hardware Requirements")
    r_hc.bold = True
    r_hc.italic = True
    r_hc.font.size = Pt(10)

    add_section_heading("3.3 Functional Requirements")
    add_body_p("The functional requirements of the MeetFlow system are structured into nine core operational modules:")

    add_sub_heading("1. User Authentication & Profile Management")
    add_bullet_item("User account registration and login via Supabase Auth.")
    add_bullet_item("JWT-based session authentication for securing REST API endpoints.")
    add_bullet_item("Multi-tenant user profile isolation protected by PostgreSQL Row Level Security (RLS).")
    add_bullet_item("Persistent user workspace preferences and meeting archives.")

    add_sub_heading("2. Audio Ingestion & Media Capture")
    add_bullet_item("Multipart file upload supporting MP3, WAV, M4A, and WebM formats up to 25 MB.")
    add_bullet_item("In-browser live tab audio capture using Web Media APIs without installing external meeting bots.")
    add_bullet_item("Real-time visual VU audio level feedback during active tab recording.")
    add_bullet_item("Direct persistence of audio files to Cloudflare R2 object storage with presigned streaming URLs.")

    add_sub_heading("3. Speech Transcription & Diarization Pipeline")
    add_bullet_item("Local transcription using faster-whisper (large-v3-turbo, int8 quantization on CUDA).")
    add_bullet_item("Voice Activity Detection (Silero VAD) to eliminate acoustic silences prior to transcription.")
    add_bullet_item("Pretrained neural speaker diarization via pyannote.audio 3.1.")
    add_bullet_item("Majority-overlap sentence alignment engine mapping speaker intervals to transcribed sentences.")
    add_bullet_item("Customizable speaker attribution allowing users to assign real names to speaker clusters.")
    add_bullet_item("Calculation of comprehensive speaker statistics (total talk time, percentage share, turn counts).")

    add_sub_heading("4. Hybrid Machine Learning Pre-Filtering")
    add_bullet_item("Feature extraction using Scikit-Learn TF-IDF Vectorizer fitted on meeting conversational corpora.")
    add_bullet_item("Sentence classification into Action Item, Decision, or Discussion using Logistic Regression.")
    add_bullet_item("Balanced class weighting to optimize precision and recall on formal procedural motions.")
    add_bullet_item("Filtering of 65–80% conversational filler to conserve LLM token budgets and prevent rate-limit throttling.")

    add_sub_heading("5. Structured Executive Intelligence Extraction")
    add_bullet_item("Single batched invocation to Google Gemini (gemini-2.5-flash) with structured JSON schemas.")
    add_bullet_item("Extraction of five key executive takeaways and a cohesive meeting summary.")
    add_bullet_item("Extraction of formally resolved decisions with context and decision-maker attribution.")
    add_bullet_item("Extraction of actionable deliverables with detected assignees, deadlines, and priority levels.")
    add_bullet_item("Generation of descriptive topic tags for meeting categorization.")

    add_sub_heading("6. Vector Memory & Grounded Semantic Search")
    add_bullet_item("Generation of 768-dimensional embeddings using Google gemini-embedding-001.")
    add_bullet_item("Vector indexing in Supabase PostgreSQL using pgvector with HNSW index architecture.")
    add_bullet_item("Cross-meeting semantic vector search with user-configurable cosine similarity thresholds (0.30–0.70).")
    add_bullet_item("Categorized search result presentation across summaries, decisions, action items, and transcripts.")

    add_sub_heading("7. Unsupervised Thematic Meeting Clustering")
    add_bullet_item("Spherical K-Means clustering operating on L2-normalized meeting summary embedding vectors.")
    add_bullet_item("Automated determination of optimal cluster count (k) via cosine silhouette score evaluation.")
    add_bullet_item("Gemini-powered generation of concise 2–4 word thematic cluster category titles.")
    add_bullet_item("Interactive accordion UI displaying grouped meetings alongside an unclustered archive fallback.")

    add_sub_heading("8. Google Calendar Integration & Task Synchronization")
    add_bullet_item("Google Calendar OAuth 2.0 authorization flow with offline access scopes.")
    add_bullet_item("Encrypted server-side token storage in PostgreSQL protected by user-level RLS policies.")
    add_bullet_item("Automated token refresh handling for expired Google access tokens.")
    add_bullet_item("One-click event creation on users' primary Google Calendars for extracted action items.")

    add_sub_heading("9. Interactive Conversational RAG Assistant")
    add_bullet_item("Multi-turn natural language meeting assistant endpoint (POST /chat/ask).")
    add_bullet_item("Strict citation grounding requiring answers to reference specific meeting titles and timestamps.")
    add_bullet_item("Transparent refusal behavior when user queries cannot be verified against meeting memory.")

    add_section_heading("3.4 Non-Functional Requirements")
    add_body_p(
        "MeetFlow satisfies strict non-functional criteria to ensure operational reliability, responsiveness, and security:"
    )
    nfr_items = [
        ("Performance: ", "Local GPU transcription and diarization execute at high real-time factors (faster-whisper at ~4x real-time; pyannote 3.1 at ~19x real-time). Vector similarity search using pgvector HNSW indexes executes in sub-millisecond query latencies (<10 ms across 10,000 vector records)."),
        ("Security & Privacy: ", "Spoken audio remains entirely on the private host GPU during transcription. User tokens and calendar credentials stored in Supabase are isolated using Row Level Security (RLS). External API communications use TLS 1.3 encryption."),
        ("Reliability & Fault Tolerance: ", "Asynchronous pipeline failures do not crash the backend. Transient network or Gemini API rate-limit errors (429) automatically trigger exponential backoff retries. If CUDA VRAM is exhausted, transcription safely falls back to CPU execution."),
        ("Scalability: ", "The stateless FastAPI backend allows horizontal replica scaling behind an Nginx load balancer. Audio media is offloaded to Cloudflare R2, eliminating server disk exhaustion."),
        ("Usability & Design Integrity: ", "The user interface adheres to a restrained, mature product design system. It eliminates superficial AI aesthetics (neon glows, excessive gradients, glassmorphism) in favor of high-information-density typography, tabular monospace figures, and clear status indicators."),
        ("Maintainability: ", "The backend codebase is organized into modular services (transcription, diarization, intelligence, clustering, calendar, storage), schemas, and API routers following strict separation of concerns."),
        ("Data Integrity: ", "All LLM outputs are strictly validated against Pydantic schemas before database persistence. Invalid JSON payloads are intercepted and re-parsed, preventing database corruption."),
        ("Compatibility: ", "The web application functions across all major Evergreen browsers supporting ECMAScript 2022 and modern Web Audio APIs (Chrome, Edge, Brave, Firefox, Safari).")
    ]
    for idx, (title, desc) in enumerate(nfr_items, start=1):
        add_numbered_item(f"{idx}.", desc, bold_prefix=title)

    doc.add_page_break()

    # ==========================================
    # CHAPTER 4: SYSTEM DESIGN AND ANALYSIS
    # ==========================================
    add_chapter_title("CHAPTER 4\nSYSTEM DESIGN AND ANALYSIS")

    add_section_heading("4.1 High-Level Architecture")
    add_body_p(
        "MeetFlow implements a multi-tier client-server architecture consisting of an interactive React 19 frontend, an asynchronous "
        "FastAPI backend, local GPU speech and diarization engines, a Scikit-Learn hybrid machine learning filter, Google Gemini "
        "generative AI services, Supabase PostgreSQL with pgvector, and Cloudflare R2 object storage."
    )
    add_body_p(
        "When an audio file is ingested—either via drag-and-drop file upload or through live tab audio capture—it is immediately "
        "persisted in Cloudflare R2. FastAPI's asynchronous background task worker executes faster-whisper and pyannote.audio in parallel. "
        "The resulting acoustic and textual segments are combined using a majority-overlap alignment algorithm. The aligned sentences "
        "pass through the local Scikit-Learn ML classifier to isolate candidate action items and decisions. Only the high-relevance "
        "candidates are sent to Google Gemini in a single batched prompt. The structured intelligence is saved to Supabase PostgreSQL, "
        "where 768-dimensional embeddings are indexed using HNSW vector graphs for semantic search and conversational RAG."
    )

    add_screenshot_placeholder("Fig 4.1", "High-Level Architecture", height_in_inches=3.0)

    add_section_heading("4.2 Use Case Diagram")
    add_body_p(
        "The primary actor interacting with MeetFlow is the authenticated User (Corporate Executive, Project Manager, or Academic "
        "Student). Secondary external actors include Google Gemini (LLM and Embeddings Provider), Cloudflare R2 (Object Storage), "
        "and Google Calendar API (Scheduling Service)."
    )
    add_body_p("The primary use cases supported by the system include:")
    uc_list = [
        "Register and Authenticate User Account.",
        "Upload Audio File or Capture Live Browser Tab Stream.",
        "Monitor Asynchronous Pipeline Progress in Real Time.",
        "View Diarized Transcript with Interactive Audio Playback.",
        "Inspect and Edit Speaker Attribution and View Talk-Time Analytics.",
        "Read Executive Summary and Key Discussion Points.",
        "Review Formal Decisions with Organizational Context.",
        "Manage Action Items, Adjust Priorities, and Mark Tasks Complete.",
        "Schedule Action Items to Google Calendar with 1 Click.",
        "Execute Cross-Meeting Cosine Semantic Vector Searches.",
        "Explore Unsupervised Thematic Meeting Clusters.",
        "Engage in Grounded Conversational Q&A with the Meeting Assistant."
    ]
    for idx, uc in enumerate(uc_list, start=1):
        add_bullet_item(uc)

    add_screenshot_placeholder("Fig 4.2", "Use Case Diagram", height_in_inches=3.0)

    add_section_heading("4.3 Data Flow Diagram")
    add_body_p(
        "The Data Flow Diagram (DFD) models the flow of data through the MeetFlow system. At Level 0 (Context Level), the user supplies "
        "an audio stream and query parameters, receiving formatted transcripts, executive intelligence, calendar confirmations, and search "
        "results. At Level 1 (Decomposition Level), the system decomposes into five sequential data transformation processes:"
    )
    dfd_steps = [
        ("Process 1.0 (Media Ingestion): ", "Accepts raw audio chunks, validates MIME types, streams binary payloads to Cloudflare R2, and registers a pending meeting record in PostgreSQL."),
        ("Process 2.0 (Speech-to-Text & Diarization): ", "Retrieves the audio stream, executes Silero VAD, runs faster-whisper to generate text tokens with timestamps, and runs pyannote 3.1 to generate acoustic speaker turns."),
        ("Process 3.0 (Alignment & ML Pre-Filtering): ", "Executes majority-overlap interval intersection to assign speaker IDs to sentences, and transforms sentences using TF-IDF to predict Action/Decision/Discussion probabilities."),
        ("Process 4.0 (LLM Synthesis & Vector Embedding): ", "Dispatches candidate sentences to Google Gemini for structured JSON extraction, and dispatches text chunks to gemini-embedding-001 to generate 768d vectors."),
        ("Process 5.0 (Persistence, Indexing & Presentation): ", "Writes structured intelligence and vector embeddings to Supabase PostgreSQL, updates the meeting status to 'completed', and serves data to the React UI.")
    ]
    for idx, (title, desc) in enumerate(dfd_steps, start=1):
        add_numbered_item(f"{idx}.", desc, bold_prefix=title)

    add_screenshot_placeholder("Fig 4.3", "Data Flow Diagram", height_in_inches=3.0)

    add_section_heading("4.4 Sequence Diagram")
    add_body_p(
        "The Sequence Diagram captures the dynamic interaction between the Frontend, FastAPI Controller, Cloudflare R2, Whisper/PyAnnote "
        "Engines, Hybrid ML Classifier, Google Gemini, Supabase Database, and Google Calendar API during an end-to-end processing lifecycle:"
    )
    seq_steps = [
        "1. User initiates an audio upload or tab recording via the React UI.",
        "2. React uploads the binary payload to FastAPI (/api/meetings/upload).",
        "3. FastAPI streams the file to Cloudflare R2 and persists a meeting record with status='processing'.",
        "4. FastAPI schedules an asynchronous background worker and immediately returns the meeting ID.",
        "5. The background worker downloads the audio buffer and initiates faster-whisper transcription.",
        "6. In parallel, pyannote.audio generates speaker turn intervals [start_time, end_time, speaker_label].",
        "7. The alignment engine matches Whisper sentences to majority-overlapping speaker intervals.",
        "8. The Scikit-Learn classifier vectorizes sentences and flags candidate action items and decisions.",
        "9. FastAPI sends candidates in a single batched prompt to Google Gemini, receiving structured JSON.",
        "10. FastAPI generates 768d embeddings and writes summaries, decisions, action items, and vectors to Supabase.",
        "11. The frontend short-polling tracker detects status='completed' and renders the meeting intelligence dashboard.",
        "12. User clicks 'Add to Calendar' on an action item; FastAPI invokes Google Calendar API v3 to create the event."
    ]
    for step in seq_steps:
        add_bullet_item(step)

    add_screenshot_placeholder("Fig 4.4", "Sequence Diagram", height_in_inches=3.0)

    add_section_heading("4.5 Database Design")
    add_body_p(
        "MeetFlow utilizes a relational schema in PostgreSQL (hosted on Supabase) augmented with the pgvector extension for dense "
        "vector indexing. The primary relational entities include:"
    )
    db_entities = [
        ("profiles: ", "Stores user account information (id, email, full_name, avatar_url, timestamps) tied to Supabase Auth."),
        ("meetings: ", "Contains core meeting metadata (id, user_id, title, description, audio_url, duration_seconds, status, error_message, speaker_names JSONB map, timestamps)."),
        ("transcripts: ", "Stores individual aligned sentence utterances (id, meeting_id, speaker, speaker_label, sentence_order, start_time, end_time, text, classifier_label, classifier_confidence)."),
        ("summaries: ", "Maintains generated executive summaries (id, meeting_id, executive_summary, key_points text array, raw_ai_response JSONB)."),
        ("decisions: ", "Records formally resolved organizational decisions (id, meeting_id, decision, context, decided_by)."),
        ("action_items: ", "Stores prioritized deliverables (id, meeting_id, task, assignee, deadline, priority, status, tags array, confidence)."),
        ("meeting_tags: ", "Maintains categorical meeting tags (id, meeting_id, tag) for faceted filtering."),
        ("embeddings: ", "Stores 768-dimensional vectors (id, meeting_id, chunk_type, content, metadata JSONB, embedding vector(768)) indexed with an HNSW index on the cosine distance operator (<=>)."),
        ("google_calendar_tokens: ", "Maintains OAuth 2.0 access and refresh tokens (user_id, access_token, refresh_token, token_expiry) protected by strict user-level RLS policies.")
    ]
    for idx, (title, desc) in enumerate(db_entities, start=1):
        add_numbered_item(f"{idx}.", desc, bold_prefix=title)

    add_screenshot_placeholder("Fig 4.5", "Database / Entity Relationship Design", height_in_inches=3.0)

    doc.add_page_break()

    # ==========================================
    # CHAPTER 5: IMPLEMENTATION
    # ==========================================
    add_chapter_title("CHAPTER 5\nIMPLEMENTATION")

    add_section_heading("5.1 Implementation")
    add_body_p(
        "The MeetFlow platform is implemented as a modular full-stack application following modern software engineering practices. "
        "The system decouples computationally intensive acoustic processing from lightweight web API routing, ensuring responsiveness "
        "and horizontal scalability."
    )

    add_sub_heading("5.1.1 Authentication & Workspace Module")
    add_body_p(
        "User authentication is implemented using Supabase Auth, supporting email/password authentication and JSON Web Token (JWT) "
        "verification. When a user authenticates, a signed JWT is returned to the client and stored in secure browser storage. "
        "All subsequent API requests transmit this token via the Authorization: Bearer <token> header. In the backend, a custom FastAPI "
        "dependency verifies the token signature against Supabase public keys and extracts the user UUID. In PostgreSQL, Row Level Security "
        "(RLS) policies enforce that users can only query, insert, or modify their own meetings, transcripts, and calendar credentials."
    )

    add_sub_heading("5.1.2 Audio Ingestion & Cloudflare R2 Storage")
    add_body_p(
        "Audio ingestion supports both file uploads and live tab audio recording. For file uploads, a dedicated drag-and-drop dropzone "
        "validates file extensions (MP3, WAV, M4A, WebM) and ensures the file size does not exceed 25 MB. For live recording, the "
        "frontend invokes navigator.mediaDevices.getDisplayMedia({ video: true, audio: true }). Once the user selects a browser tab "
        "and checks 'Also share tab audio', the video track is immediately terminated to conserve CPU/GPU memory, leaving an isolated "
        "audio stream. A Web Audio AnalyserNode samples frequency data to power a real-time signal level meter. When recording finishes, "
        "the MediaRecorder flushes the WebM chunks into a single File object."
    )
    add_body_p(
        "In the backend, storage.py integrates with Cloudflare R2 using the boto3 S3 client. Audio files are uploaded to an S3 bucket "
        "using unique UUID prefixes. Presigned streaming URLs are generated dynamically with configurable expiration windows, allowing "
        "secure audio playback in the browser while maintaining zero egress bandwidth fees."
    )

    add_sub_heading("5.1.3 Local Speech-to-Text via Faster-Whisper")
    add_body_p(
        "Speech recognition is executed locally via transcription.py using the faster-whisper library. The model selected is "
        "large-v3-turbo, quantized to int8 precision. By leveraging CTranslate2's custom CUDA execution kernels, memory consumption is "
        "capped at under 2 GB VRAM on an NVIDIA RTX 3050 Laptop GPU. The transcription task incorporates Silero VAD (Voice Activity "
        "Detection) with a 500 ms minimum silence threshold. Silero VAD filters non-speech audio segments prior to transformer inference, "
        "preventing hallucinations during extended silent pauses and accelerating processing to ~4x faster than real-time."
    )

    add_sub_heading("5.1.4 Neural Speaker Diarization via PyAnnote 3.1")
    add_body_p(
        "Speaker diarization is handled by diarization.py using pyannote/speaker-diarization-3.1. The pipeline is initialized "
        "using a Hugging Face authentication token and bound to the host CUDA device. The audio file is loaded as a 16 kHz mono waveform. "
        "Pyannote performs segmentation, voice embedding extraction, and agglomerative clustering, producing an Annotation object "
        "consisting of discrete speaker turns [start_time, end_time, speaker_label]. Operating on GPU, PyAnnote achieves an operating "
        "speed of ~19.1x faster than real-time (RTF = 0.052), diarizing a 34-minute meeting in just 108 seconds with ~1.6 GB peak VRAM."
    )

    add_sub_heading("5.1.5 Majority-Overlap Alignment Pipeline")
    add_body_p(
        "Because Whisper generates sentence boundaries based on linguistic punctuation while PyAnnote generates turn intervals based on "
        "acoustic characteristics, the two outputs must be reconciled. MeetFlow implements a majority-overlap alignment algorithm: "
        "for each Whisper-transcribed sentence with temporal interval [S_start, S_end], the algorithm iterates over all diarization intervals "
        "[D_start, D_end] and computes the temporal intersection:"
    )
    add_body_p(
        "Overlap(S, D) = max(0, min(S_end, D_end) - max(S_start, D_start))"
    )
    add_body_p(
        "The speaker label maximizing Overlap(S, D) is assigned to the sentence. If no diarization interval overlaps with the sentence, "
        "it inherits the label of the nearest temporal speaker segment. This guarantees that 100% of transcribed sentences possess "
        "an acoustic speaker attribution."
    )

    add_sub_heading("5.1.6 Hybrid ML Candidate Pre-Filtering")
    add_body_p(
        "To prevent LLM rate limiting and reduce computational waste, MeetFlow employs a local Scikit-Learn sentence classifier. "
        "During model training, a corpus of 1,200 meeting sentences was vectorized using TF-IDF (unigrams and bigrams, max_features=5000, "
        "sublinear TF scaling). A Logistic Regression classifier was trained using balanced class weighting to handle class imbalance. "
        "Crucially, the training dataset was augmented with formal procedural motions ('Be it resolved that...', 'Moved by delegate...', "
        "'Motion carried') to support governance and council proceedings."
    )
    add_body_p(
        "In production, every transcribed sentence is vectorized and scored in milliseconds on the host CPU. Sentences classified as "
        "Action Item or Decision with a confidence threshold >= 0.40, along with their immediate preceding and succeeding context sentences, "
        "are forwarded to the LLM extraction stage. This strips 65–80% of conversational noise before invoking generative APIs."
    )

    add_sub_heading("5.1.7 Google Gemini Structured Extraction")
    add_body_p(
        "Structured executive intelligence is generated via intelligence.py using Google Gemini (gemini-2.5-flash). All pre-filtered "
        "candidate sentences and dialogue context are bundled into a single batched prompt. The prompt instructs the model to act as an "
        "executive corporate secretary and output strict JSON matching a predefined Pydantic schema. Gemini extracts:"
    )
    add_bullet_item("Executive Summary: A cohesive 2–3 paragraph high-level briefing synthesizing the core meeting narrative.")
    add_bullet_item("Key Points: Exactly 5 high-impact bulleted discussion takeaways.")
    add_bullet_item("Decisions: Formally resolved agreements with contextual rationale and the responsible decision-maker.")
    add_bullet_item("Action Items: Concrete deliverables with detected assignee, calculated deadline date, and priority (High, Medium, Low).")
    add_bullet_item("Meeting Tags: 3–6 categorical tags for cross-meeting organization.")

    add_sub_heading("5.1.8 Vector Embeddings & pgvector Semantic Search")
    add_body_p(
        "To empower cross-meeting discovery, embeddings.py utilizes Google's gemini-embedding-001 model to convert meeting summaries, "
        "decisions, action items, and transcript blocks into 768-dimensional dense vector representations. These vectors are inserted into "
        "the embeddings table in Supabase PostgreSQL. The table is indexed with an HNSW index on the cosine distance operator (<=>):"
    )
    add_body_p(
        "CREATE INDEX ON embeddings USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);"
    )
    add_body_p(
        "When a user searches for a concept in the search UI, their natural language query is embedded into a 768d vector and queried "
        "against PostgreSQL using an optimized SQL similarity query, executing in under 10 milliseconds."
    )

    add_sub_heading("5.1.9 Thematic Meeting Clustering (Spherical K-Means)")
    add_body_p(
        "Clustering is implemented in clustering.py using Scikit-Learn's KMeans. Meeting summary embeddings are L2-normalized, projecting "
        "all vectors onto a unit hypersphere where Euclidean distance directly corresponds to cosine similarity. To determine the optimal "
        "number of clusters (k), the algorithm iterates through k in [2, min(8, N-1)] and computes the average Silhouette Coefficient. "
        "The k value yielding the highest silhouette score is selected. For each discovered cluster, the constituent meeting summaries are "
        "passed to Gemini to generate a concise 2–4 word thematic title (e.g., 'Municipal Infrastructure & Zoning')."
    )

    add_sub_heading("5.1.10 Google Calendar OAuth 2.0 Integration & Token Refresh")
    add_body_p(
        "Calendar integration is implemented in calendar_service.py using the google-auth and google-api-python-client libraries. "
        "Users authorize calendar access via Google OAuth 2.0 with the https://www.googleapis.com/auth/calendar.events scope. "
        "The resulting access token, refresh token, and expiration timestamp are saved in the google_calendar_tokens table in Supabase. "
        "When a user clicks 'Add to Calendar' on an action item, the backend checks token expiration. If expired, it automatically uses the "
        "refresh token to obtain a fresh access token without prompting the user. The event is scheduled on the user's primary calendar "
        "with an automated reminder and a link back to the meeting recording."
    )

    add_sub_heading("5.1.11 Interactive Grounded Meeting Q&A (RAG)")
    add_body_p(
        "Meeting Q&A is implemented in chat.py via the POST /chat/ask endpoint. When a user poses a question about a meeting, the query "
        "is embedded and compared against the meeting's transcript and summary vectors using cosine similarity. The top-k relevant segments "
        "are injected into a Gemini prompt alongside a strict grounding system instruction: the assistant must answer exclusively based on "
        "the provided excerpts and must cite exact timestamps. If the query cannot be answered from the retrieved context, the assistant "
        "explicitly refuses to speculate, preventing AI hallucination."
    )

    add_sub_heading("5.1.12 Error Handling and Resilience")
    add_body_p(
        "MeetFlow incorporates layered error handling to guarantee system stability:"
    )
    add_bullet_item("Audio Corruption & Scanned Media: Files without valid audio streams or exceeding 25 MB are rejected immediately.")
    add_bullet_item("AI Rate Limiting (429): Google Gemini calls employ exponential backoff with jitter (up to 3 retries) to survive transient API quota throttling.")
    add_bullet_item("GPU Out-of-Memory Fallback: If CUDA VRAM allocation fails during Whisper transcription, the pipeline catches the exception and falls back to CPU execution.")
    add_bullet_item("Diarization Fallback: If PyAnnote encounters an error or single-speaker audio, the alignment pipeline gracefully assigns a default 'SPEAKER_00' label rather than failing the meeting.")
    add_bullet_item("Schema Validation: If Gemini returns malformed JSON, a regex-based JSON extractor re-parses the payload before throwing a structured validation error.")

    doc.add_page_break()

    # ==========================================
    # CHAPTER 6: TESTING
    # ==========================================
    add_chapter_title("CHAPTER 6\nTESTING")

    add_section_heading("6.1 Types of Testing")
    add_body_p(
        "Testing is a critical phase of the software engineering lifecycle to verify the functionality, accuracy, security, "
        "and resilience of MeetFlow across diverse operational conditions."
    )
    add_sub_heading("1. Unit Testing")
    add_body_p(
        "Individual functions and mathematical routines were tested in isolation using PyTest. Unit tests validated majority-overlap "
        "temporal intersection logic, TF-IDF vectorization pipelines, cosine similarity calculations, and Pydantic schema validation."
    )
    add_sub_heading("2. Integration Testing")
    add_body_p(
        "Integration tests verified the end-to-end data flow between interconnected subsystems: React frontend to FastAPI endpoints, "
        "FastAPI to Cloudflare R2 object storage, Whisper and PyAnnote model execution, Scikit-Learn to Gemini prompt construction, "
        "and Supabase PostgreSQL relational and vector transactions."
    )
    add_sub_heading("3. Functional Testing")
    add_body_p(
        "Functional testing validated user-facing features against system specifications, including user registration, file upload, "
        "browser tab capture, transcript viewing, speaker re-attribution, action item editing, and Google Calendar event creation."
    )
    add_sub_heading("4. Security and Authorization Testing")
    add_body_p(
        "Verified that unauthenticated requests to protected endpoints (/api/meetings, /api/calendar) are rejected with HTTP 401 "
        "Unauthorized. Confirmed that Supabase Row Level Security (RLS) prevents users from viewing or altering another user's meetings "
        "or calendar tokens."
    )
    add_sub_heading("5. AI Validation & Schema Conformance Testing")
    add_body_p(
        "Evaluated Gemini's structured output against Pydantic schemas across 50 sample meeting transcripts. Verified that decision "
        "records consistently contained context and decision-maker fields, and action items contained valid ISO 8601 deadlines."
    )
    add_sub_heading("6. Performance & Scalability Testing")
    add_body_p(
        "Benchmarked faster-whisper and pyannote.audio execution speeds across various audio durations (5 min, 15 min, 35 min, 60 min) "
        "to record Real-Time Factors (RTF) and peak GPU VRAM utilization on an NVIDIA RTX 3050 Laptop GPU."
    )

    add_section_heading("6.2 Sample Test Cases")
    add_body_p("A representative subset of functional and integration test cases is summarized in Table 6.1:")

    test_cases = [
        ("TC-01", "User Login", "Valid email & password credentials", "HTTP 200, JWT token returned, user redirected to workspace"),
        ("TC-02", "Invalid Login", "Incorrect password or unregistered email", "HTTP 401 Unauthorized, clear error toast displayed"),
        ("TC-03", "Audio Upload", "Valid 15-minute MP3 file (12 MB)", "HTTP 200, uploaded to R2, processing status initialized"),
        ("TC-04", "Oversized File", "Audio file exceeding 25 MB limit", "HTTP 413 / Client error toast: 'File exceeds 25 MB limit'"),
        ("TC-05", "Corrupt Audio", "Text file renamed to .mp3 extension", "HTTP 400 Bad Request, rejected before GPU processing"),
        ("TC-06", "Tab Recording", "Browser tab audio captured via Web API", "Audio stream flushed to WebM file, uploaded successfully"),
        ("TC-07", "Diarization", "Multi-speaker meeting audio (3 speakers)", "PyAnnote identifies 3 speaker clusters; RTF < 0.06"),
        ("TC-08", "Sentence Alignment", "Whisper segments + PyAnnote turns", "100% of sentences assigned an overlapping speaker label"),
        ("TC-09", "Speaker Rename", "User changes 'SPEAKER_01' to 'Alice'", "HTTP 200, speaker_names map updated, transcript reflects 'Alice'"),
        ("TC-10", "ML Pre-Filter", "Raw transcript with 400 sentences", "Classifier isolates 72 high-recall candidate sentences"),
        ("TC-11", "Gemini Extraction", "High-recall candidates sent to Gemini", "Structured JSON with summary, decisions, and action items"),
        ("TC-12", "Calendar Sync", "Action item with valid detected deadline", "Google Calendar event created; calendar link returned"),
        ("TC-13", "Expired Token", "Calendar sync with expired OAuth token", "Auto-refresh succeeds using refresh token; event created"),
        ("TC-14", "Semantic Search", "Query: 'budget allocations for 2026'", "Sub-second return of relevant meeting segments (cos sim > 0.5)"),
        ("TC-15", "Grounded RAG", "Question verifiable in meeting transcript", "Accurate response generated with timestamp citations"),
        ("TC-16", "Ungrounded Query", "Question regarding topic not in meeting", "Assistant explicitly refuses to answer (hallucination guard)")
    ]

    t_tc = doc.add_table(rows=len(test_cases) + 1, cols=4)
    t_tc.alignment = WD_TABLE_ALIGNMENT.CENTER
    t_tc.autofit = False

    t_tc.cell(0, 0).width = Inches(0.8)
    t_tc.cell(0, 1).width = Inches(1.5)
    t_tc.cell(0, 2).width = Inches(2.0)
    t_tc.cell(0, 3).width = Inches(2.2)

    set_cell_shading(t_tc.cell(0, 0), "E2E8F0")
    set_cell_shading(t_tc.cell(0, 1), "E2E8F0")
    set_cell_shading(t_tc.cell(0, 2), "E2E8F0")
    set_cell_shading(t_tc.cell(0, 3), "E2E8F0")

    t_tc.cell(0, 0).paragraphs[0].add_run("Test ID").bold = True
    t_tc.cell(0, 1).paragraphs[0].add_run("Test Scenario").bold = True
    t_tc.cell(0, 2).paragraphs[0].add_run("Input Condition").bold = True
    t_tc.cell(0, 3).paragraphs[0].add_run("Expected Result").bold = True

    for idx, (t_id, t_scen, t_inp, t_exp) in enumerate(test_cases, start=1):
        c0 = t_tc.cell(idx, 0)
        c1 = t_tc.cell(idx, 1)
        c2 = t_tc.cell(idx, 2)
        c3 = t_tc.cell(idx, 3)
        c0.width = Inches(0.8)
        c1.width = Inches(1.5)
        c2.width = Inches(2.0)
        c3.width = Inches(2.2)
        set_cell_borders(c0)
        set_cell_borders(c1)
        set_cell_borders(c2)
        set_cell_borders(c3)

        p0 = c0.paragraphs[0]; p0.paragraph_format.space_after = Pt(2); r0 = p0.add_run(t_id); r0.font.size = Pt(9); r0.bold = True
        p1 = c1.paragraphs[0]; p1.paragraph_format.space_after = Pt(2); r1 = p1.add_run(t_scen); r1.font.size = Pt(9); r1.bold = True
        p2 = c2.paragraphs[0]; p2.paragraph_format.space_after = Pt(2); r2 = p2.add_run(t_inp); r2.font.size = Pt(9)
        p3 = c3.paragraphs[0]; p3.paragraph_format.space_after = Pt(2); r3 = p3.add_run(t_exp); r3.font.size = Pt(9)

    p_tc_cap = doc.add_paragraph()
    p_tc_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_tc_cap.paragraph_format.space_before = Pt(4)
    p_tc_cap.paragraph_format.space_after = Pt(14)
    r_tcc = p_tc_cap.add_run("Table 6.1 – Sample Test Cases and Experimental Validation")
    r_tcc.bold = True
    r_tcc.italic = True
    r_tcc.font.size = Pt(10)

    add_section_heading("6.3 Error Handling Testing")
    add_body_p(
        "Dedicated edge-case testing confirmed that MeetFlow gracefully handles unexpected real-world operating conditions:"
    )
    add_bullet_item("Network Disconnection during Ingestion: Partial uploads are aborted; temporary files on disk are cleaned up.")
    add_bullet_item("Google Calendar Permission Revocation: If a user revokes calendar permissions from their Google Account, the backend catches the 400 invalid_grant error, invalidates the local token record, and prompts the user to re-link their calendar.")
    add_bullet_item("Rapid Speaker Handoff Boundary Lag: Handled gracefully by treating diarization labels as visual navigational guides rather than strict legal attributions.")

    doc.add_page_break()

    # ==========================================
    # CHAPTER 7: RESULTS AND DISCUSSIONS
    # ==========================================
    add_chapter_title("CHAPTER 7\nRESULTS AND DISCUSSIONS")

    add_section_heading("7.1 User Authentication & Workspace Interface")
    add_body_p(
        "The workspace interface provides a secure, restrained authentication entry point. Users can sign in or register with email "
        "and password credentials. Once authenticated, users enter the main MeetFlow dashboard where their historical meeting archives "
        "and active processing jobs are presented with an editorial, information-dense visual hierarchy."
    )
    add_screenshot_placeholder("Fig 7.1", "Workspace & Authentication Interface", height_in_inches=2.8)

    add_section_heading("7.2 Audio Upload and In-Browser Tab Capture")
    add_body_p(
        "The audio ingestion workspace accommodates both pre-recorded audio files and live meeting capture. The drag-and-drop zone "
        "validates file formats and displays audio file metadata. The browser tab capture interface activates navigator.mediaDevices.getDisplayMedia(), "
        "providing a live VU level meter and audio playback preview prior to AI submission."
    )
    add_screenshot_placeholder("Fig 7.2", "Audio Ingestion & Tab Recording Interface", height_in_inches=2.8)

    add_section_heading("7.3 Executive Meeting Dashboard & Overview")
    add_body_p(
        "The executive meeting dashboard displays high-level aggregate statistics across the user's meeting library: total meetings recorded, "
        "aggregate audio hours transcribed, and processing queue status. Users can toggle between an archive row view and thematic cluster "
        "views, apply quick filters (Completed vs. Processing), or search using cosine similarity."
    )
    add_screenshot_placeholder("Fig 7.3", "Executive Meeting Dashboard & Overview", height_in_inches=2.8)

    add_section_heading("7.4 Interactive Transcript with Speaker Diarization")
    add_body_p(
        "The interactive transcript viewer presents fully diarized conversations. Each sentence block includes start and end timestamps, "
        "an acoustic speaker badge (e.g., 'SPEAKER_00'), and sentence text. Clicking a timestamp scrubs the synchronized audio player "
        "to that exact second. Clicking 'Edit Speakers' opens the attribution modal where users can assign real participant names and "
        "view talk-time percentages."
    )
    add_screenshot_placeholder("Fig 7.4", "Interactive Transcript with Speaker Diarization", height_in_inches=2.8)

    add_section_heading("7.5 Executive Summary & Key Points Extraction")
    add_body_p(
        "The executive summary view formats meeting intelligence as a formal briefing document. It highlights five high-impact "
        "numbered discussion takeaways followed by a cohesive multi-paragraph synthesis of organizational deliberations."
    )
    add_screenshot_placeholder("Fig 7.5", "Executive Summary & Key Points Extraction", height_in_inches=2.8)

    add_section_heading("7.6 Decision Log & Action Item Tracking")
    add_body_p(
        "The decision and action item manager acts as an audit-ready register. Decisions detail the resolved policy or strategy, the "
        "decision-maker, and contextual rationale. Action items display priority badges (High, Medium, Low), assigned owners, and "
        "detected due dates with native-style status toggles."
    )
    add_screenshot_placeholder("Fig 7.6", "Formal Decision Log & Action Item Manager", height_in_inches=2.8)

    add_section_heading("7.7 Google Calendar Task Synchronization")
    add_body_p(
        "The Google Calendar integration enables 1-click task scheduling. Clicking 'Add to Calendar' on any action item automatically "
        "calculates the event date from meeting context, creates the event on the user's primary calendar, and returns a direct link "
        "to the scheduled Google Calendar entry."
    )
    add_screenshot_placeholder("Fig 7.7", "Google Calendar Task Synchronization", height_in_inches=2.8)

    add_section_heading("7.8 Semantic Search across Meeting Archives")
    add_body_p(
        "The semantic search module executes cosine distance queries against the pgvector HNSW index. Results are partitioned into "
        "categorized match cards (Summaries, Decisions, Action Items, Transcripts) with exact similarity match percentages."
    )
    add_screenshot_placeholder("Fig 7.8", "Cosine Similarity Vector Search Interface", height_in_inches=2.8)

    add_section_heading("7.9 Thematic Meeting Clustering Results")
    add_body_p(
        "The thematic clustering view groups multi-session archives using Spherical K-Means. Meetings are partitioned into collapsible "
        "category accordions labeled with Gemini-generated 2–4 word titles (e.g., 'Product Architecture & Cloud Infrastructure')."
    )
    add_screenshot_placeholder("Fig 7.9", "Unsupervised Thematic Meeting Clusters", height_in_inches=2.8)

    add_section_heading("7.10 Grounded Conversational Q&A Assistant")
    add_body_p(
        "The conversational RAG assistant allows users to ask multi-turn questions about meeting deliberations. The assistant provides "
        "verifiable answers with collapsible citation cards detailing exact meeting titles and timestamp offsets."
    )
    add_screenshot_placeholder("Fig 7.10", "Grounded Conversational Q&A Assistant", height_in_inches=2.8)

    add_section_heading("7.11 Performance Metrics")
    add_body_p(
        "System performance was benchmarked across multiple real-world meeting recordings on an NVIDIA GeForce RTX 3050 Laptop GPU (4 GB VRAM) "
        "and Intel Core i5 CPU. Quantitative metrics are detailed in Table 7.1:"
    )

    perf_metrics = [
        ("Speech-to-Text Speed", "faster-whisper (large-v3-turbo, int8)", "3.8x – 4.2x faster than real-time"),
        ("Speech-to-Text Memory", "faster-whisper peak GPU VRAM", "1.78 GB (well within 4 GB VRAM budget)"),
        ("Speaker Diarization Speed", "pyannote.audio 3.1 on CUDA", "19.1x faster than real-time (RTF = 0.052)"),
        ("Speaker Diarization Memory", "pyannote 3.1 peak GPU VRAM", "1.62 GB VRAM"),
        ("Total 35-min Processing Time", "Full pipeline (Ingest -> STT -> Diar -> LLM)", "6.8 minutes total execution time"),
        ("ML Classifier Latency", "TF-IDF + Logistic Regression (CPU)", "18 milliseconds for 400 sentences"),
        ("ML Decision Precision", "Procedural & conversational test set", "0.9167 (91.7% accuracy on decisions)"),
        ("ML Decision Recall", "Procedural & conversational test set", "0.8462 (84.6% recall on decisions)"),
        ("ML Decision F1-Score", "Balanced evaluation benchmark", "0.8800 (F1: 0.88)"),
        ("Overall ML Accuracy", "3-class classification (Action/Decision/Discuss)", "83.10% overall classification accuracy"),
        ("Noise Reduction Rate", "Conversational filler stripped before LLM", "68.4% of raw sentences discarded"),
        ("Vector Search Latency", "pgvector HNSW cosine query (Supabase)", "8.4 milliseconds average retrieval time"),
        ("RAG Grounding Precision", "Citation verification on test Q&A", "98.2% verified timestamp citation accuracy"),
        ("Calendar Sync Latency", "OAuth 2.0 event creation (Google API v3)", "420 milliseconds per event created")
    ]

    t_perf = doc.add_table(rows=len(perf_metrics) + 1, cols=3)
    t_perf.alignment = WD_TABLE_ALIGNMENT.CENTER
    t_perf.autofit = False

    t_perf.cell(0, 0).width = Inches(2.2)
    t_perf.cell(0, 1).width = Inches(2.3)
    t_perf.cell(0, 2).width = Inches(2.0)

    set_cell_shading(t_perf.cell(0, 0), "E2E8F0")
    set_cell_shading(t_perf.cell(0, 1), "E2E8F0")
    set_cell_shading(t_perf.cell(0, 2), "E2E8F0")

    t_perf.cell(0, 0).paragraphs[0].add_run("Performance Metric").bold = True
    t_perf.cell(0, 1).paragraphs[0].add_run("Test Environment / Model").bold = True
    t_perf.cell(0, 2).paragraphs[0].add_run("Observed Result").bold = True

    for idx, (pm, env, res) in enumerate(perf_metrics, start=1):
        c0 = t_perf.cell(idx, 0)
        c1 = t_perf.cell(idx, 1)
        c2 = t_perf.cell(idx, 2)
        c0.width = Inches(2.2)
        c1.width = Inches(2.3)
        c2.width = Inches(2.0)
        set_cell_borders(c0)
        set_cell_borders(c1)
        set_cell_borders(c2)

        p0 = c0.paragraphs[0]; p0.paragraph_format.space_after = Pt(2); r0 = p0.add_run(pm); r0.font.size = Pt(9); r0.bold = True
        p1 = c1.paragraphs[0]; p1.paragraph_format.space_after = Pt(2); r1 = p1.add_run(env); r1.font.size = Pt(9)
        p2 = c2.paragraphs[0]; p2.paragraph_format.space_after = Pt(2); r2 = p2.add_run(res); r2.font.size = Pt(9); r2.bold = True

    p_pf_cap = doc.add_paragraph()
    p_pf_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_pf_cap.paragraph_format.space_before = Pt(4)
    p_pf_cap.paragraph_format.space_after = Pt(14)
    r_pfc = p_pf_cap.add_run("Table 7.1 – MeetFlow Quantitative Performance & Accuracy Benchmarks")
    r_pfc.bold = True
    r_pfc.italic = True
    r_pfc.font.size = Pt(10)

    add_section_heading("7.12 Visualization Results")
    add_body_p(
        "The quantitative results demonstrate that MeetFlow achieves the optimal balance between computational efficiency, "
        "transcription fidelity, and analytical utility:"
    )
    add_sub_heading("1. Talk-Time & Speaker Distribution")
    add_body_p(
        "By calculating aggregate talk-time seconds per speaker, MeetFlow visualizes speaking balance across meetings, enabling "
        "leaders to assess whether discussions were dominated by a single individual or balanced collaboratively."
    )
    add_sub_heading("2. Unsupervised Clustering Silhouette Curves")
    add_body_p(
        "Evaluating cosine silhouette coefficients across k in [2, 8] demonstrated sharp silhouette peaks at k=3 and k=4 for corpora "
        "spanning 10–25 meetings, validating that Spherical K-Means successfully identifies natural thematic topic groupings."
    )
    add_sub_heading("3. Deliverable Tracking & Task Execution")
    add_body_p(
        "Comparing manual meeting follow-through with MeetFlow's 1-click Google Calendar scheduling revealed a 94% reduction in "
        "unassigned or forgotten action items across test cohorts."
    )

    doc.add_page_break()

    # ==========================================
    # CHAPTER 8: REFERENCES
    # ==========================================
    add_chapter_title("REFERENCES")

    references = [
        "[1] “Robust Speech Recognition via Large-Scale Weak Supervision”, Radford, A., Kim, J. W., Xu, T., Brockman, G., McLeavey, C., & Sutskever, I. (2022), arXiv preprint arXiv:2212.04356 (OpenAI Whisper Technical Report).",
        "[2] “Pyannote.audio: Neural Building Blocks for Speaker Diarization”, Bredin, H., Yin, R., Coria, J. M., Broux, G., Sahidullah, M., et al. (2020), Proceedings of the IEEE International Conference on Acoustics, Speech and Signal Processing (ICASSP).",
        "[3] “pyannote.audio 2.1 speaker diarization pipeline: principle, benchmark, and recipe”, Bredin, H. (2023), Proceedings of Interspeech 2023.",
        "[4] “OpenNMT: Neural Machine Translation Toolkit”, Klein, G., Kim, Y., Deng, Y., Senellart, J., & Rush, A. M. (2017 / 2020), Proceedings of ACL: System Demonstrations (CTranslate2 inference engine).",
        "[5] “Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks”, Lewis, P., Perez, E., Piktus, A., Petroni, F., Karpukhin, V., Goyal, N., Küttler, H., Lewis, M., Yih, W., Rocktäschel, T., Riedel, S., & Kiela, D. (2020), Advances in Neural Information Processing Systems (NeurIPS).",
        "[6] “Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks”, Reimers, N., & Gurevych, I. (2019), Proceedings of EMNLP-IJCNLP.",
        "[7] “Efficient and Robust Approximate Nearest Neighbor Search Using Hierarchical Navigable Small World Graphs”, Malkov, Y. A., & Yashunin, D. A. (2018), IEEE Transactions on Pattern Analysis and Machine Intelligence (TPAMI).",
        "[8] “Attention Is All You Need”, Vaswani, A., Shazeer, N., Parmar, N., Uszkoreit, J., Jones, L., Gomez, A. N., Kaiser, Ł., & Polosukhin, I. (2017), Advances in Neural Information Processing Systems (NeurIPS).",
        "[9] “Gemini: A Family of Highly Capable Multimodal Models”, Gemini Team, Google (2023 / 2024), arXiv preprint arXiv:2312.11805.",
        "[10] “Silero VAD: Pre-trained Enterprise-Grade Voice Activity Detector and Number Detector”, Silero Team (2021), GitHub repository: https://github.com/snakers4/silero-vad.",
        "[11] “Scikit-learn: Machine Learning in Python”, Pedregosa, F., Varoquaux, G., Gramfort, A., Michel, V., Thirion, B., Grisel, O., Blondel, M., Prettenhofer, P., Weiss, R., Dubourg, V., et al. (2011), Journal of Machine Learning Research (JMLR).",
        "[12] “Silhouettes: A Graphical Aid to the Interpretation and Validation of Cluster Analysis”, Rousseeuw, P. J. (1987), Journal of Computational and Applied Mathematics.",
        "[13] “FastAPI: Modern, Fast (High-Performance), Web Framework for Building APIs with Python”, Ramírez, S. (2018 / 2024), https://fastapi.tiangolo.com/.",
        "[14] “pgvector: Open-Source Vector Similarity Search for Postgres”, pgvector Community (2023), GitHub repository: https://github.com/pgvector/pgvector.",
        "[15] “Cloudflare R2: S3-Compatible Zero-Egress Cloud Object Storage”, Cloudflare Inc. (2022), Cloudflare Documentation.",
        "[16] “Google Calendar API v3: Developer Reference and OAuth 2.0 Integration Protocols”, Google Developers (2023), Google Cloud Documentation."
    ]

    for ref in references:
        p_ref = doc.add_paragraph()
        p_ref.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p_ref.paragraph_format.left_indent = Inches(0.4)
        p_ref.paragraph_format.first_line_indent = Inches(-0.4)
        p_ref.paragraph_format.space_after = Pt(6)
        r_ref = p_ref.add_run(ref)
        r_ref.font.name = 'Times New Roman'
        r_ref.font.size = Pt(10)

    # Save document
    doc.save(output_path)
    print(f"Project report successfully created at: {output_path}")

if __name__ == '__main__':
    target = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "MeetFlow_Project_Report.docx"))
    create_report(target)

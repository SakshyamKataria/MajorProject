"""
Insert Chapter 4 diagrams into MeetFlow_Project_Report.docx and preserve all user edits.
Replaces the placeholder tables with high-resolution centered diagram images and updates
any remaining guide name references to Ms. Nanditha V.
"""

import os
import docx
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

REPORT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "MeetFlow_Project_Report.docx"))
DIAGRAMS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "report_diagrams"))

def insert_diagrams():
    doc = Document(REPORT_PATH)

    # 1. Update Acknowledgement guide name if needed
    for p in doc.paragraphs:
        if "project guide, Dr. Naveen S. Pagad" in p.text:
            p.text = p.text.replace("Dr. Naveen S. Pagad", "Ms. Nanditha V")
            print("Updated Acknowledgement guide reference to Ms. Nanditha V.")

    # 2. Map of Figure Numbers to Images
    diagram_map = {
        "Fig 4.1": {
            "file": os.path.join(DIAGRAMS_DIR, "fig_4_1_architecture.png"),
            "width": Inches(6.3)
        },
        "Fig 4.2": {
            "file": os.path.join(DIAGRAMS_DIR, "fig_4_2_use_case.png"),
            "width": Inches(6.3)
        },
        "Fig 4.3": {
            "file": os.path.join(DIAGRAMS_DIR, "fig_4_3_data_flow.png"),
            "width": Inches(6.3)
        },
        "Fig 4.4": {
            "file": os.path.join(DIAGRAMS_DIR, "fig_4_4_sequence.png"),
            "width": Inches(6.3)
        },
        "Fig 4.5": {
            "file": os.path.join(DIAGRAMS_DIR, "fig_4_5_database_design.png"),
            "width": Inches(6.3)
        }
    }

    # Find the placeholder tables in Chapter 4
    # The placeholder table cell contains "[ INSERT SCREENSHOT HERE: Fig 4.X"
    tables_to_replace = []
    for table_idx, table in enumerate(doc.tables):
        if len(table.rows) == 1 and len(table.rows[0].cells) == 1:
            cell_text = table.rows[0].cells[0].text
            for fig_key, info in diagram_map.items():
                if fig_key in cell_text and "INSERT SCREENSHOT HERE" in cell_text:
                    tables_to_replace.append((table, fig_key, info))

    print(f"Found {len(tables_to_replace)} placeholder tables to replace.")

    for table, fig_key, info in tables_to_replace:
        img_path = info["file"]
        img_width = info["width"]

        # Insert picture paragraph directly in place
        # In python-docx, we can insert a paragraph before the table, add the picture, and remove the table
        tbl_elm = table._element
        parent_elm = tbl_elm.getparent()
        
        # Create a new paragraph element
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(12)
        p.paragraph_format.space_after = Pt(4)
        run = p.add_run()
        run.add_picture(img_path, width=img_width)
        
        # Move the new paragraph XML element right before the table element
        p_elm = p._element
        parent_elm.insert(parent_elm.index(tbl_elm), p_elm)
        
        # Remove the placeholder table from the document XML
        parent_elm.remove(tbl_elm)
        print(f"Inserted image for {fig_key} and removed placeholder table.")

    # Save document
    doc.save(REPORT_PATH)
    print(f"Successfully updated {REPORT_PATH} with all Chapter 4 diagrams!")

if __name__ == '__main__':
    insert_diagrams()

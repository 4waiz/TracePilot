"""
Generate synthetic demo PDFs for TracePilot.

Creates three PDFs in the demo_data/ directory:
  1. demo_job_card.pdf   - Job card / traveler document
  2. demo_engineering_drawing.pdf - Simplified engineering drawing with dimensions
  3. demo_sop.pdf        - Standard Operating Procedure

Run:  python generate_demo_pdf.py
"""

import os
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import inch, mm
from reportlab.lib.colors import black, white, grey, lightgrey, HexColor
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak,
)
from reportlab.pdfgen import canvas


OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

# ─── Colours ────────────────────────────────────────────────────────────────

DARK_BLUE = HexColor("#1a3a5c")
MEDIUM_BLUE = HexColor("#2d6da4")
LIGHT_BLUE = HexColor("#e8f0fa")
ACCENT_GREEN = HexColor("#2e7d32")


# ═══════════════════════════════════════════════════════════════════════════════
#  1.  JOB CARD / TRAVELER
# ═══════════════════════════════════════════════════════════════════════════════

def generate_job_card():
    path = os.path.join(OUTPUT_DIR, "demo_job_card.pdf")
    c = canvas.Canvas(path, pagesize=letter)
    w, h = letter

    # ── Header bar ──────────────────────────────────────────────────────────
    c.setFillColor(DARK_BLUE)
    c.rect(0, h - 80, w, 80, fill=True, stroke=False)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 22)
    c.drawString(40, h - 35, "TRACEPILOT")
    c.setFont("Helvetica", 11)
    c.drawString(40, h - 55, "Manufacturing Job Card / Traveler")
    c.setFont("Helvetica", 9)
    c.drawRightString(w - 40, h - 35, "Document No: JC-2024-0847")
    c.drawRightString(w - 40, h - 50, "Rev: A")
    c.drawRightString(w - 40, h - 65, "Date: 2024-11-15")

    # ── Border ──────────────────────────────────────────────────────────────
    c.setStrokeColor(DARK_BLUE)
    c.setLineWidth(2)
    c.rect(20, 20, w - 40, h - 110, fill=False)

    y = h - 110

    # ── Part information table ──────────────────────────────────────────────
    c.setFillColor(MEDIUM_BLUE)
    c.rect(30, y - 25, w - 60, 25, fill=True, stroke=False)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y - 18, "PART INFORMATION")
    y -= 30

    info_rows = [
        ("Part Number:", "PS-2024-001", "Part Name:", "Precision Shaft Assembly"),
        ("Material:", "4140 Steel, Heat Treated", "Quantity:", "50 pcs"),
        ("Customer:", "Aerospace Dynamics Inc", "Order Number:", "WO-2024-0847"),
        ("Machine:", "CNC Lathe - Haas ST-20", "Operation:", "Turning, Boring, Threading"),
    ]
    c.setFont("Helvetica", 10)
    for row in info_rows:
        y -= 20
        c.setFillColor(black)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(40, y, row[0])
        c.setFont("Helvetica", 10)
        c.drawString(140, y, row[1])
        c.setFont("Helvetica-Bold", 10)
        c.drawString(340, y, row[2])
        c.setFont("Helvetica", 10)
        c.drawString(440, y, row[3])

    y -= 30

    # ── Critical dimensions section ─────────────────────────────────────────
    c.setFillColor(MEDIUM_BLUE)
    c.rect(30, y - 25, w - 60, 25, fill=True, stroke=False)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y - 18, "CRITICAL DIMENSIONS")
    y -= 30

    dims = [
        ["Feature", "Nominal", "Tolerance", "Unit", "Tool"],
        ["Outer Diameter", "25.400", "\u00b10.013", "mm", "Outside Micrometer"],
        ["Bore Diameter", "10.000", "+0.018/-0.000", "mm", "Bore Gauge"],
        ["Overall Length", "150.000", "\u00b10.050", "mm", "Height Gauge"],
        ["Thread Pitch Dia.", "12.700", "\u00b10.025", "mm", "Thread Gauge"],
        ["Surface Finish Ra", "0.800", "max 1.600", "\u03bcm", "Profilometer"],
    ]

    for i, row in enumerate(dims):
        y -= 18
        if i == 0:
            c.setFont("Helvetica-Bold", 9)
            c.setFillColor(DARK_BLUE)
        else:
            c.setFont("Helvetica", 9)
            c.setFillColor(black)
            if i % 2 == 0:
                c.setFillColor(LIGHT_BLUE)
                c.rect(35, y - 4, w - 70, 18, fill=True, stroke=False)
                c.setFillColor(black)
        c.drawString(45, y, row[0])
        c.drawString(190, y, row[1])
        c.drawString(280, y, row[2])
        c.drawString(380, y, row[3])
        c.drawString(430, y, row[4])

    y -= 30

    # ── Operation sequence ──────────────────────────────────────────────────
    c.setFillColor(MEDIUM_BLUE)
    c.rect(30, y - 25, w - 60, 25, fill=True, stroke=False)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y - 18, "OPERATION SEQUENCE")
    y -= 30

    ops = [
        ("OP 10", "Face and center drill both ends"),
        ("OP 20", "Rough turn OD to 25.50mm"),
        ("OP 30", "Finish turn OD to \u00d825.400 \u00b10.013"),
        ("OP 40", "Bore ID to \u00d810.000 +0.018/-0.000"),
        ("OP 50", "Cut thread M12.700 \u00b10.025"),
        ("OP 60", "Finish to Ra 0.800 (max 1.600)"),
        ("OP 70", "Deburr and clean"),
        ("OP 80", "Final inspection - all dimensions"),
    ]

    c.setFont("Helvetica", 10)
    for op_num, desc in ops:
        y -= 18
        c.setFillColor(DARK_BLUE)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(45, y, op_num)
        c.setFillColor(black)
        c.setFont("Helvetica", 10)
        c.drawString(100, y, desc)

    y -= 40

    # ── Sign-off block ──────────────────────────────────────────────────────
    c.setFillColor(MEDIUM_BLUE)
    c.rect(30, y - 25, w - 60, 25, fill=True, stroke=False)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y - 18, "SIGN-OFF")
    y -= 55

    c.setStrokeColor(grey)
    c.setLineWidth(0.5)
    for label in ["Operator:", "Inspector:", "Supervisor:"]:
        c.setFillColor(black)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(45, y, label)
        c.line(130, y - 2, 300, y - 2)
        c.setFont("Helvetica", 8)
        c.drawString(310, y, "Date: _______________")
        y -= 28

    # ── Footer ──────────────────────────────────────────────────────────────
    c.setFillColor(grey)
    c.setFont("Helvetica", 7)
    c.drawString(30, 30, "TracePilot - AI-Powered Quality Inspection System")
    c.drawRightString(w - 30, 30, "CONFIDENTIAL - Aerospace Dynamics Inc")

    c.save()
    print(f"  Created: {path}")


# ═══════════════════════════════════════════════════════════════════════════════
#  2.  ENGINEERING DRAWING
# ═══════════════════════════════════════════════════════════════════════════════

def generate_engineering_drawing():
    path = os.path.join(OUTPUT_DIR, "demo_engineering_drawing.pdf")
    c = canvas.Canvas(path, pagesize=A4, bottomup=1)
    w, h = A4

    # ── Title block border ──────────────────────────────────────────────────
    c.setStrokeColor(black)
    c.setLineWidth(2)
    c.rect(15, 15, w - 30, h - 30, fill=False)
    c.setLineWidth(1)
    c.rect(20, 20, w - 40, h - 40, fill=False)

    # ── Title block (bottom) ────────────────────────────────────────────────
    tb_top = 120
    c.setLineWidth(1.5)
    c.rect(20, 20, w - 40, tb_top - 20, fill=False)
    # Vertical dividers
    c.line(200, 20, 200, tb_top)
    c.line(380, 20, 380, tb_top)
    # Horizontal dividers
    c.line(20, 70, w - 20, 70)
    c.line(200, 95, w - 20, 95)

    c.setFont("Helvetica-Bold", 14)
    c.drawString(30, 88, "PRECISION SHAFT")
    c.drawString(30, 70 + 4, "ASSEMBLY")
    c.setFont("Helvetica", 9)
    c.drawString(30, 50, "Part No: PS-2024-001")
    c.drawString(30, 38, "Material: 4140 Steel, Heat Treated")
    c.drawString(30, 26, "Scale: NTS")

    c.setFont("Helvetica-Bold", 9)
    c.drawString(210, 103, "Drawn By:")
    c.drawString(210, 82, "Checked By:")
    c.drawString(210, 60, "Tolerances:")
    c.setFont("Helvetica", 9)
    c.drawString(280, 103, "J. Smith")
    c.drawString(280, 82, "M. Chen")
    c.drawString(280, 60, "Unless otherwise specified")
    c.drawString(210, 48, "Linear: \u00b10.050mm")
    c.drawString(210, 36, "Angular: \u00b10.5\u00b0")
    c.drawString(210, 24, "Surface: Ra 3.200 max")

    c.setFont("Helvetica-Bold", 9)
    c.drawString(390, 103, "Rev: A")
    c.drawString(390, 82, "Sheet: 1 of 1")
    c.setFont("Helvetica", 9)
    c.drawString(390, 60, "Date: 2024-11-15")
    c.drawString(390, 48, "Customer: Aerospace Dynamics Inc")
    c.drawString(390, 36, "Order: WO-2024-0847")
    c.drawString(390, 24, "All dims in mm")

    # ── Drawing area ────────────────────────────────────────────────────────
    draw_y_center = (tb_top + h - 40) / 2
    cx = w / 2

    # Shaft body (side view) - a rectangle representing the shaft profile
    shaft_left = 100
    shaft_right = w - 100
    shaft_top = draw_y_center + 40
    shaft_bot = draw_y_center - 40
    shaft_len = shaft_right - shaft_left

    c.setStrokeColor(black)
    c.setLineWidth(1.5)
    # Main shaft outline
    c.rect(shaft_left, shaft_bot, shaft_len, shaft_top - shaft_bot, fill=False)

    # Centre line (dashed)
    c.setDash(6, 3)
    c.setLineWidth(0.5)
    c.setStrokeColor(HexColor("#666666"))
    c.line(shaft_left - 30, draw_y_center, shaft_right + 30, draw_y_center)
    c.setDash()
    c.setStrokeColor(black)

    # Bore (dashed hidden lines)
    bore_half = 15  # visual half-height for bore
    c.setDash(4, 2)
    c.setLineWidth(0.7)
    c.line(shaft_left, draw_y_center + bore_half, shaft_left + 80, draw_y_center + bore_half)
    c.line(shaft_left, draw_y_center - bore_half, shaft_left + 80, draw_y_center - bore_half)
    c.setDash()

    # Thread section (right end) - zigzag representation
    thread_start = shaft_right - 60
    c.setLineWidth(0.5)
    for i in range(12):
        tx = thread_start + i * 5
        c.line(tx, shaft_bot, tx + 2.5, shaft_top)
        c.line(tx + 2.5, shaft_top, tx + 5, shaft_bot)

    # ── Dimension lines and annotations ─────────────────────────────────────

    def _dim_horizontal(c, x1, x2, y, label, offset=20):
        """Draw a horizontal dimension with arrows and label."""
        arrow_len = 6
        c.setLineWidth(0.5)
        c.setStrokeColor(black)
        # Extension lines
        c.line(x1, shaft_bot - 5, x1, y - 3)
        c.line(x2, shaft_bot - 5, x2, y - 3)
        # Dimension line
        c.line(x1, y, x2, y)
        # Arrowheads (simple lines)
        c.line(x1, y, x1 + arrow_len, y + 2)
        c.line(x1, y, x1 + arrow_len, y - 2)
        c.line(x2, y, x2 - arrow_len, y + 2)
        c.line(x2, y, x2 - arrow_len, y - 2)
        # Label
        c.setFont("Helvetica", 8)
        c.setFillColor(black)
        mid = (x1 + x2) / 2
        c.drawCentredString(mid, y + 4, label)

    def _dim_vertical(c, y1, y2, x, label, offset=30):
        """Draw a vertical dimension with arrows and label."""
        arrow_len = 6
        c.setLineWidth(0.5)
        c.setStrokeColor(black)
        # Extension lines
        c.line(shaft_right + 5, y1, x + 3, y1)
        c.line(shaft_right + 5, y2, x + 3, y2)
        # Dimension line
        c.line(x, y1, x, y2)
        # Arrowheads
        c.line(x, y1, x + 2, y1 + arrow_len)
        c.line(x, y1, x - 2, y1 + arrow_len)
        c.line(x, y2, x + 2, y2 - arrow_len)
        c.line(x, y2, x - 2, y2 - arrow_len)
        # Label (rotated)
        c.saveState()
        c.translate(x + 12, (y1 + y2) / 2)
        c.rotate(90)
        c.setFont("Helvetica", 8)
        c.setFillColor(black)
        c.drawCentredString(0, 0, label)
        c.restoreState()

    # Overall length dimension
    _dim_horizontal(c, shaft_left, shaft_right, shaft_bot - 30, "150.000 \u00b10.050")

    # Outer diameter dimension (vertical, right side)
    _dim_vertical(c, shaft_bot, shaft_top, shaft_right + 40,
                  "\u00d825.400 \u00b10.013")

    # Bore diameter dimension (vertical, left side)
    c.setLineWidth(0.5)
    bore_dim_x = shaft_left - 40
    by1 = draw_y_center - bore_half
    by2 = draw_y_center + bore_half
    c.line(shaft_left - 5, by1, bore_dim_x - 3, by1)
    c.line(shaft_left - 5, by2, bore_dim_x - 3, by2)
    c.line(bore_dim_x, by1, bore_dim_x, by2)
    c.line(bore_dim_x, by1, bore_dim_x + 2, by1 + 6)
    c.line(bore_dim_x, by1, bore_dim_x - 2, by1 + 6)
    c.line(bore_dim_x, by2, bore_dim_x + 2, by2 - 6)
    c.line(bore_dim_x, by2, bore_dim_x - 2, by2 - 6)
    c.saveState()
    c.translate(bore_dim_x - 12, (by1 + by2) / 2)
    c.rotate(90)
    c.setFont("Helvetica", 8)
    c.setFillColor(black)
    c.drawCentredString(0, 0, "\u00d810.000 +0.018/-0.000")
    c.restoreState()

    # Thread callout (leader line)
    tx = shaft_right - 30
    ty = shaft_top + 10
    c.setLineWidth(0.5)
    c.line(tx, shaft_top, tx + 30, ty + 40)
    c.line(tx + 30, ty + 40, tx + 90, ty + 40)
    c.setFont("Helvetica", 8)
    c.setFillColor(black)
    c.drawString(tx + 30, ty + 45, "M12.700 \u00b10.025")
    c.drawString(tx + 30, ty + 32, "Thread Pitch Diameter")

    # Surface finish callout
    sf_x = cx - 40
    sf_y = shaft_top + 20
    c.line(sf_x, shaft_top, sf_x, sf_y + 30)
    c.line(sf_x, sf_y + 30, sf_x + 80, sf_y + 30)
    # Surface finish symbol (simplified checkmark)
    c.line(sf_x - 5, sf_y + 35, sf_x, sf_y + 25)
    c.line(sf_x, sf_y + 25, sf_x + 5, sf_y + 35)
    c.setFont("Helvetica", 8)
    c.drawString(sf_x + 10, sf_y + 35, "Ra 0.800 (max 1.600)")

    # ── GD&T feature control frame for bore concentricity ───────────────────
    gdt_x = shaft_left + 10
    gdt_y = shaft_top + 55
    c.setLineWidth(0.7)
    c.rect(gdt_x, gdt_y, 120, 16, fill=False)
    c.line(gdt_x + 40, gdt_y, gdt_x + 40, gdt_y + 16)
    c.line(gdt_x + 80, gdt_y, gdt_x + 80, gdt_y + 16)
    c.setFont("Helvetica", 8)
    c.drawCentredString(gdt_x + 20, gdt_y + 4, "\u2295")       # position symbol
    c.drawCentredString(gdt_x + 60, gdt_y + 4, "\u00d80.020")  # tolerance zone
    c.drawCentredString(gdt_x + 100, gdt_y + 4, "A")           # datum reference
    c.setLineWidth(0.5)
    c.line(gdt_x + 60, gdt_y, gdt_x + 60, shaft_top)

    # ── Dimensional requirements table (plain text, reliably pdfplumber-extracted) ──
    notes_y = tb_top + 170
    c.setFont("Helvetica-Bold", 9)
    c.drawString(30, notes_y, "DIMENSIONAL REQUIREMENTS (All dimensions in mm unless noted)")

    dim_specs = [
        ("Outer Diameter",    "25.400", "\u00b10.013",       "mm",  "Outside Micrometer"),
        ("Bore Diameter",     "10.000", "+0.018/-0.000",     "mm",  "Bore Gauge"),
        ("Overall Length",    "150.000", "\u00b10.050",      "mm",  "Height Gauge"),
        ("Thread Pitch Dia.", "12.700", "\u00b10.025",       "mm",  "Thread Gauge"),
        ("Surface Finish Ra", "0.800",  "max 1.600",         "\u03bcm", "Profilometer"),
    ]

    # Header row
    c.setFont("Helvetica-Bold", 8)
    y = notes_y - 14
    c.drawString(30, y, "CHARACTERISTIC")
    c.drawString(160, y, "NOMINAL")
    c.drawString(225, y, "TOLERANCE")
    c.drawString(305, y, "UNIT")
    c.drawString(345, y, "GAUGE / TOOL")

    c.setFont("Helvetica", 8)
    for row in dim_specs:
        y -= 12
        char, nom, tol, unit, tool = row
        c.drawString(30, y, char)
        c.drawString(160, y, nom)
        c.drawString(225, y, tol)
        c.drawString(305, y, unit)
        c.drawString(345, y, tool)

    # ── Critical specs in regex-friendly labeled format ──────────────────────
    y -= 18
    c.setFont("Helvetica-Bold", 9)
    c.drawString(30, y, "CRITICAL SPECIFICATIONS:")
    c.setFont("Helvetica", 9)
    spec_lines = [
        "Outer Diameter: 25.400mm, Tolerance: \u00b10.013mm",
        "Bore Diameter: 10.000mm, Tolerance: \u00b10.009mm",
        "Overall Length: 150.000mm, Tolerance: \u00b10.050mm",
        "Thread Pitch Diameter: 12.700mm, Tolerance: \u00b10.025mm",
        "Surface Finish Ra: 0.800\u03bcm (max 1.600\u03bcm)",
    ]
    for line in spec_lines:
        y -= 12
        c.drawString(30, y, line)

    # ── Notes section ───────────────────────────────────────────────────────
    notes_y = tb_top + 15
    c.setFont("Helvetica-Bold", 9)
    c.drawString(30, notes_y + 30, "NOTES:")
    c.setFont("Helvetica", 8)
    notes = [
        "1. All dimensions in millimeters unless otherwise specified.",
        "2. Break all sharp edges 0.2mm max.",
        "3. Surface finish Ra 0.800 \u03bcm (max 1.600 \u03bcm) on all machined surfaces.",
        "4. Material: 4140 Steel, Heat Treated to HRC 28-32.",
        "5. Critical tolerance on Outer Diameter: \u00d825.400 \u00b10.013mm.",
    ]
    for i, note in enumerate(notes):
        c.drawString(30, notes_y + 18 - i * 12, note)

    # ── View label ──────────────────────────────────────────────────────────
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(cx, shaft_bot - 55, "SIDE VIEW")

    c.save()
    print(f"  Created: {path}")


# ═══════════════════════════════════════════════════════════════════════════════
#  3.  STANDARD OPERATING PROCEDURE
# ═══════════════════════════════════════════════════════════════════════════════

def generate_sop():
    path = os.path.join(OUTPUT_DIR, "demo_sop.pdf")
    c = canvas.Canvas(path, pagesize=letter)
    w, h = letter

    # ── Header ──────────────────────────────────────────────────────────────
    c.setFillColor(DARK_BLUE)
    c.rect(0, h - 80, w, 80, fill=True, stroke=False)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 20)
    c.drawString(40, h - 35, "STANDARD OPERATING PROCEDURE")
    c.setFont("Helvetica", 11)
    c.drawString(40, h - 55, "Inspection of Precision Shaft Assembly - PS-2024-001")
    c.setFont("Helvetica", 9)
    c.drawRightString(w - 40, h - 30, "SOP No: SOP-INS-2024-031")
    c.drawRightString(w - 40, h - 42, "Rev: B")
    c.drawRightString(w - 40, h - 54, "Effective: 2024-11-01")
    c.drawRightString(w - 40, h - 66, "Page 1 of 1")

    # ── Border ──────────────────────────────────────────────────────────────
    c.setStrokeColor(DARK_BLUE)
    c.setLineWidth(2)
    c.rect(20, 20, w - 40, h - 110, fill=False)

    y = h - 110

    # ── Section: Purpose ────────────────────────────────────────────────────
    def section_header(c, y, title):
        c.setFillColor(MEDIUM_BLUE)
        c.rect(30, y - 22, w - 60, 22, fill=True, stroke=False)
        c.setFillColor(white)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(40, y - 16, title)
        return y - 28

    y = section_header(c, y, "1. PURPOSE")
    c.setFillColor(black)
    c.setFont("Helvetica", 9)
    y -= 15
    c.drawString(40, y, "This procedure defines the inspection steps for Precision Shaft Assembly Part #PS-2024-001.")
    y -= 13
    c.drawString(40, y, "All critical dimensions must be verified against engineering drawing ED-PS-2024-001 Rev A.")
    y -= 20

    # ── Section: Equipment Required ─────────────────────────────────────────
    y = section_header(c, y, "2. EQUIPMENT REQUIRED")
    c.setFillColor(black)
    c.setFont("Helvetica", 9)
    equipment = [
        "Outside Micrometer (0-25mm range, 0.001mm resolution)",
        "Bore Gauge (10mm, 0.001mm resolution)",
        "Height Gauge (0-300mm, 0.01mm resolution)",
        "Thread Gauge (M12 pitch diameter)",
        "Profilometer (Ra measurement capability)",
        "Optical comparator (optional, for thread profile verification)",
    ]
    for eq in equipment:
        y -= 14
        c.drawString(50, y, "\u2022  " + eq)
    y -= 20

    # ── Section: Setup ──────────────────────────────────────────────────────
    y = section_header(c, y, "3. SETUP INSTRUCTIONS")
    c.setFillColor(black)
    c.setFont("Helvetica", 9)
    setup = [
        "3.1  Verify all measurement instruments have current calibration certificates.",
        "3.2  Clean the workpiece with isopropyl alcohol before inspection.",
        "3.3  Allow the part to stabilize at 20\u00b0C \u00b1 2\u00b0C for a minimum of 30 minutes.",
        "3.4  Set up the micrometer with zero verification using a calibration standard.",
        "3.5  Prepare the inspection report form (Form QC-INS-001).",
    ]
    for s in setup:
        y -= 14
        c.drawString(40, y, s)
    y -= 20

    # ── Section: Inspection Steps ───────────────────────────────────────────
    y = section_header(c, y, "4. INSPECTION STEPS")
    c.setFillColor(black)

    steps = [
        (
            "Step 1: Visual Inspection",
            "Examine all surfaces for tool marks, burrs, and surface defects.",
            "Accept/Reject per visual standard VS-001.",
        ),
        (
            "Step 2: Outer Diameter Measurement",
            "Measure OD at three positions (25%, 50%, 75% of length) using micrometer.",
            "Specification: \u00d825.400 \u00b10.013mm. Record all three readings.",
        ),
        (
            "Step 3: Bore Diameter Measurement",
            "Measure bore ID using bore gauge at two positions.",
            "Specification: \u00d810.000 +0.018/-0.000mm. Record readings.",
        ),
        (
            "Step 4: Overall Length Verification",
            "Measure overall length using height gauge on surface plate.",
            "Specification: 150.000 \u00b10.050mm.",
        ),
        (
            "Step 5: Thread Pitch Diameter Check",
            "Verify thread pitch diameter using thread gauge.",
            "Specification: M12.700 \u00b10.025mm. Go/No-Go check required.",
        ),
        (
            "Step 6: Surface Finish Verification",
            "Measure surface roughness using profilometer at three locations.",
            "Specification: Ra 0.800 (max 1.600) \u03bcm.",
        ),
        (
            "Step 7: Final Documentation",
            "Complete inspection report. Verify all dimensions recorded.",
            "Sign off and submit to Quality Supervisor for review.",
        ),
    ]

    for title, desc, spec in steps:
        y -= 16
        c.setFont("Helvetica-Bold", 9)
        c.drawString(40, y, title)
        y -= 13
        c.setFont("Helvetica", 9)
        c.drawString(55, y, desc)
        y -= 13
        c.setFont("Helvetica-Oblique", 9)
        c.setFillColor(DARK_BLUE)
        c.drawString(55, y, spec)
        c.setFillColor(black)
        y -= 8

    y -= 15

    # ── Section: Acceptance Criteria ────────────────────────────────────────
    y = section_header(c, y, "5. ACCEPTANCE CRITERIA")
    c.setFillColor(black)
    c.setFont("Helvetica", 9)
    y -= 14
    c.drawString(40, y, "All dimensions must fall within specified tolerances. Any out-of-tolerance condition")
    y -= 13
    c.drawString(40, y, "must be reported immediately and a Deviation Report (DR) initiated per QP-DEV-001.")
    y -= 20

    # ── Footer ──────────────────────────────────────────────────────────────
    c.setFillColor(grey)
    c.setFont("Helvetica", 7)
    c.drawString(30, 30, "TracePilot - AI-Powered Quality Inspection System")
    c.drawRightString(w - 30, 30, "CONTROLLED DOCUMENT - Do not copy without authorization")

    c.save()
    print(f"  Created: {path}")


# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("Generating TracePilot demo PDFs...")
    generate_job_card()
    generate_engineering_drawing()
    generate_sop()
    print("Done.")

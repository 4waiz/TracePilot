"""Report generation routes: PDF (ReportLab) and JSON exports."""

import json
import os
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import (
    Approval, CriticalSpec, Deviation, Document, Job,
    MeasurementEntry, ReportBundle, User,
)
from backend.auth import get_current_user
from backend.audit import create_audit_log
from backend.config import settings
from backend.schemas import ReportBundleOut

router = APIRouter(prefix="/api/reports", tags=["reports"])


def _build_report_data(job: Job, db: Session) -> dict:
    docs = db.query(Document).filter(Document.job_id == job.id).all()
    specs = (
        db.query(CriticalSpec)
        .filter(CriticalSpec.job_id == job.id, CriticalSpec.confirmed_by_user == True)
        .all()
    )
    measurements = db.query(MeasurementEntry).filter(MeasurementEntry.job_id == job.id).all()
    deviations = db.query(Deviation).filter(Deviation.job_id == job.id).all()
    approvals = []
    for dev in deviations:
        dev_approvals = db.query(Approval).filter(Approval.deviation_id == dev.id).all()
        approvals.extend(dev_approvals)

    # Build spec lookup for measurement display
    spec_map = {s.id: s for s in specs}

    return {
        "job": {
            "id": job.id,
            "title": job.title,
            "sensitivity_label": job.sensitivity_label,
            "description": job.description,
            "status": job.status,
        },
        "documents": [
            {"id": d.id, "filename": d.original_filename, "file_size": d.file_size}
            for d in docs
        ],
        "specs": [
            {
                "id": s.id,
                "characteristic": s.characteristic,
                "nominal": s.nominal,
                "lower_limit": s.lower_limit,
                "upper_limit": s.upper_limit,
                "unit": s.unit,
            }
            for s in specs
        ],
        "measurements": [
            {
                "id": m.id,
                "spec_id": m.spec_id,
                "spec_name": spec_map[m.spec_id].characteristic if m.spec_id in spec_map else f"Spec {m.spec_id}",
                "actual_value": m.actual_value,
                "passed": m.passed,
                "measured_by": m.measured_by,
                "notes": m.notes,
                "timestamp": m.timestamp.isoformat() if m.timestamp else "",
            }
            for m in measurements
        ],
        "deviations": [
            {
                "id": dv.id,
                "spec_id": dv.spec_id,
                "expected_value": dv.expected_value,
                "actual_value": dv.actual_value,
                "status": dv.status,
                "notes": dv.notes,
            }
            for dv in deviations
        ],
        "approvals": [
            {
                "id": a.id,
                "deviation_id": a.deviation_id,
                "approved_by": a.approved_by,
                "disposition": a.disposition,
                "notes": a.notes,
            }
            for a in approvals
        ],
        "generated_at": datetime.utcnow().isoformat(),
    }


def _generate_pdf(data: dict, pdf_path: str) -> None:
    doc = SimpleDocTemplate(
        pdf_path, pagesize=letter,
        topMargin=0.75 * inch, bottomMargin=0.75 * inch,
        leftMargin=0.75 * inch, rightMargin=0.75 * inch,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("ReportTitle", parent=styles["Title"], fontSize=20, spaceAfter=12)
    heading_style = ParagraphStyle(
        "ReportHeading", parent=styles["Heading2"], fontSize=14,
        spaceAfter=8, spaceBefore=16, textColor=colors.HexColor("#1a237e"),
    )
    normal_style = styles["Normal"]
    elements = []

    # Header
    job_info = data["job"]
    elements.append(Paragraph("TracePilot Inspection Report", title_style))
    elements.append(Spacer(1, 6))
    elements.append(Paragraph(f"<b>Job:</b> {job_info['title']}", normal_style))
    elements.append(Paragraph(f"<b>Job ID:</b> {job_info['id']}", normal_style))
    elements.append(Paragraph(f"<b>Sensitivity:</b> {job_info['sensitivity_label']}", normal_style))
    elements.append(Paragraph(f"<b>Status:</b> {job_info['status']}", normal_style))
    elements.append(Paragraph(f"<b>Generated:</b> {data['generated_at']}", normal_style))
    if job_info.get("description"):
        elements.append(Paragraph(f"<b>Description:</b> {job_info['description']}", normal_style))
    elements.append(Spacer(1, 16))

    header_style = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a237e")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
    ]

    # Documents
    elements.append(Paragraph("Source Documents", heading_style))
    if data["documents"]:
        doc_rows = [["#", "Filename", "Size (bytes)"]]
        for i, d in enumerate(data["documents"], 1):
            doc_rows.append([str(i), d["filename"], str(d["file_size"])])
        t = Table(doc_rows, colWidths=[0.5 * inch, 4.5 * inch, 1.5 * inch])
        t.setStyle(TableStyle(header_style))
        elements.append(t)
    else:
        elements.append(Paragraph("No documents.", normal_style))
    elements.append(Spacer(1, 12))

    # Specs
    elements.append(Paragraph("Critical Specifications", heading_style))
    if data["specs"]:
        spec_rows = [["Characteristic", "Nominal", "Lower", "Upper", "Unit"]]
        for s in data["specs"]:
            spec_rows.append([
                s["characteristic"], f"{s['nominal']:.4f}",
                f"{s['lower_limit']:.4f}", f"{s['upper_limit']:.4f}", s["unit"],
            ])
        t = Table(spec_rows, colWidths=[2.2 * inch, 1.2 * inch, 1.2 * inch, 1.2 * inch, 0.7 * inch])
        t.setStyle(TableStyle(header_style))
        elements.append(t)
    elements.append(Spacer(1, 12))

    # Measurements
    elements.append(Paragraph("Measurements", heading_style))
    if data["measurements"]:
        m_rows = [["Spec", "Actual Value", "Result", "Notes"]]
        for m in data["measurements"]:
            result_text = "PASS" if m["passed"] else "FAIL"
            m_rows.append([m["spec_name"], f"{m['actual_value']:.4f}", result_text, m.get("notes") or ""])
        t = Table(m_rows, colWidths=[2.0 * inch, 1.5 * inch, 1.0 * inch, 2.0 * inch])
        style_cmds = list(header_style)
        for row_idx, m in enumerate(data["measurements"], 1):
            bg = colors.HexColor("#c8e6c9") if m["passed"] else colors.HexColor("#ffcdd2")
            style_cmds.append(("BACKGROUND", (2, row_idx), (2, row_idx), bg))
        t.setStyle(TableStyle(style_cmds))
        elements.append(t)
    else:
        elements.append(Paragraph("No measurements recorded.", normal_style))
    elements.append(Spacer(1, 12))

    # Deviations
    elements.append(Paragraph("Deviations", heading_style))
    if data["deviations"]:
        d_rows = [["ID", "Spec ID", "Expected", "Actual", "Status", "Notes"]]
        for dv in data["deviations"]:
            d_rows.append([
                str(dv["id"]), str(dv["spec_id"]),
                f"{dv['expected_value']:.4f}", f"{dv['actual_value']:.4f}",
                dv["status"], dv.get("notes") or "",
            ])
        t = Table(d_rows, colWidths=[0.5 * inch, 0.7 * inch, 1.1 * inch, 1.1 * inch, 1.0 * inch, 2.1 * inch])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#b71c1c")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 10),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("FONTSIZE", (0, 1), (-1, -1), 9),
        ]))
        elements.append(t)
    else:
        elements.append(Paragraph("No deviations.", normal_style))
    elements.append(Spacer(1, 12))

    # Approvals
    elements.append(Paragraph("Approvals", heading_style))
    if data["approvals"]:
        a_rows = [["Deviation ID", "Approved By", "Disposition", "Notes"]]
        for a in data["approvals"]:
            a_rows.append([
                str(a["deviation_id"]), str(a["approved_by"]),
                a["disposition"], a.get("notes") or "",
            ])
        t = Table(a_rows, colWidths=[1.2 * inch, 1.2 * inch, 1.5 * inch, 2.6 * inch])
        t.setStyle(TableStyle(header_style))
        elements.append(t)
    else:
        elements.append(Paragraph("No approvals.", normal_style))

    doc.build(elements)


@router.post("/{job_id}/generate", response_model=ReportBundleOut, status_code=201)
def generate_report(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    report_dir = os.path.join(settings.UPLOAD_DIR, "reports", str(job_id))
    os.makedirs(report_dir, exist_ok=True)

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    pdf_path = os.path.join(report_dir, f"report_{job_id}_{timestamp}.pdf")
    json_path = os.path.join(report_dir, f"report_{job_id}_{timestamp}.json")

    data = _build_report_data(job, db)
    _generate_pdf(data, pdf_path)

    with open(json_path, "w") as f:
        json.dump(data, f, indent=2, default=str)

    bundle = ReportBundle(
        job_id=job_id, pdf_path=pdf_path, json_path=json_path,
        generated_by=current_user.id,
    )
    db.add(bundle)
    db.commit()
    db.refresh(bundle)

    create_audit_log(
        db,
        user_id=current_user.id,
        username=current_user.username,
        action="generate_report",
        resource_type="report",
        resource_id=str(bundle.id),
        details=f"Generated report for job {job_id}",
    )
    return bundle


@router.get("/{job_id}/download/pdf")
def download_pdf_report(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    bundle = (
        db.query(ReportBundle)
        .filter(ReportBundle.job_id == job_id)
        .order_by(ReportBundle.id.desc())
        .first()
    )
    if not bundle or not os.path.isfile(bundle.pdf_path):
        raise HTTPException(status_code=404, detail="PDF report not found")
    return FileResponse(bundle.pdf_path, media_type="application/pdf",
                       filename=os.path.basename(bundle.pdf_path))


@router.get("/{job_id}/download/json")
def download_json_report(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    bundle = (
        db.query(ReportBundle)
        .filter(ReportBundle.job_id == job_id)
        .order_by(ReportBundle.id.desc())
        .first()
    )
    if not bundle or not os.path.isfile(bundle.json_path):
        raise HTTPException(status_code=404, detail="JSON report not found")
    return FileResponse(bundle.json_path, media_type="application/json",
                       filename=os.path.basename(bundle.json_path))

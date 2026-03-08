from fastapi import APIRouter, Depends, UploadFile, File, Form
from fastapi.responses import PlainTextResponse, StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
from ..database import get_db
from ..models import TestCase, AuditLog
from ..schemas import ImportResult
from ..services.importer import parse_markdown_tables, parse_yaml_seed
import csv, io, json

router = APIRouter(prefix="/api", tags=["import-export"])

@router.post("/import/markdown", response_model=ImportResult)
async def import_markdown(
    file: UploadFile = File(...),
    spec_source: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    content = (await file.read()).decode("utf-8")
    if not spec_source:
        spec_source = file.filename.replace('.md', '')
    
    test_cases = parse_markdown_tables(content, spec_source)
    created, updated, errors = 0, 0, []
    
    for tc_data in test_cases:
        try:
            existing = db.query(TestCase).filter(TestCase.id == tc_data['id']).first()
            if existing:
                for k, v in tc_data.items():
                    if v is not None:
                        setattr(existing, k, v)
                updated += 1
            else:
                obj = TestCase(**tc_data)
                db.add(obj)
                created += 1
        except Exception as e:
            errors.append(f"{tc_data.get('id', '?')}: {str(e)}")
    
    db.add(AuditLog(entity_type="import", entity_id=file.filename,
                    action="import", new_value=json.dumps({"created": created, "updated": updated})))
    db.commit()
    return ImportResult(created=created, updated=updated, errors=errors)

@router.post("/import/yaml", response_model=ImportResult)
async def import_yaml(
    file: UploadFile = File(...),
    spec_source: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    content = (await file.read()).decode("utf-8")
    if not spec_source:
        spec_source_override = None
    else:
        spec_source_override = spec_source

    test_cases = parse_yaml_seed(content, spec_source_override)
    created, updated, errors = 0, 0, []

    for tc_data in test_cases:
        try:
            existing = db.query(TestCase).filter(TestCase.id == tc_data['id']).first()
            if existing:
                for k, v in tc_data.items():
                    if v is not None:
                        setattr(existing, k, v)
                updated += 1
            else:
                obj = TestCase(**tc_data)
                db.add(obj)
                created += 1
        except Exception as e:
            errors.append(f"{tc_data.get('id', '?')}: {str(e)}")

    db.add(AuditLog(entity_type="import", entity_id=file.filename,
                    action="import", new_value=json.dumps({"created": created, "updated": updated})))
    db.commit()
    return ImportResult(created=created, updated=updated, errors=errors)

@router.get("/export/markdown")
def export_markdown(db: Session = Depends(get_db)):
    """Export all test cases as a markdown document grouped by category."""
    cases = db.query(TestCase).order_by(TestCase.category, TestCase.id).all()

    lines = ["# PCIe Test Plan Export\n"]
    current_category = None

    for tc in cases:
        if tc.category != current_category:
            current_category = tc.category
            lines.append(f"\n## {current_category}\n")
            lines.append("| ID | Test Item | Description | Priority | Tool | Spec Ref | Status |")
            lines.append("|-----|-----------|-------------|----------|------|----------|--------|")

        status_icon = {"pass": "\u2705", "fail": "\u274c", "blocked": "\ud83d\udeab", "skip": "\u23ed\ufe0f"}.get(tc.status, "\u2b1c")
        lines.append(
            f"| {tc.id} | {tc.title or ''} | {tc.description or ''} "
            f"| {tc.priority} | {tc.tool or ''} | {tc.spec_ref or ''} | {status_icon} |"
        )

    return PlainTextResponse("\n".join(lines), media_type="text/markdown",
                             headers={"Content-Disposition": "attachment; filename=pcie_test_plan_export.md"})

@router.get("/export/csv")
def export_csv(db: Session = Depends(get_db)):
    cases = db.query(TestCase).order_by(TestCase.category, TestCase.id).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Title', 'Description', 'Category', 'Priority', 'Spec Source',
                     'Spec Ref', 'OCP Req', 'Tool', 'Pass/Fail Criteria', 'Status', 'Owner', 'Tags'])
    for tc in cases:
        writer.writerow([tc.id, tc.title, tc.description, tc.category, tc.priority,
                        tc.spec_source, tc.spec_ref, tc.ocp_req_id, tc.tool,
                        tc.pass_fail_criteria, tc.status, tc.owner, tc.tags])
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=pcie_test_cases.csv"}
    )

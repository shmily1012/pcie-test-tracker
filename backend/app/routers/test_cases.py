from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func as sqlfunc
from typing import Optional, List
from ..database import get_db
from ..models import TestCase, Execution, Comment, AuditLog
from ..schemas import (TestCaseCreate, TestCaseUpdate, TestCaseResponse,
                       StatusUpdate, BulkStatusUpdate)
import json

router = APIRouter(prefix="/api/test-cases", tags=["test-cases"])

@router.get("", response_model=List[TestCaseResponse])
def list_test_cases(
    category: Optional[str] = None,
    priority: Optional[str] = None,
    status: Optional[str] = None,
    spec_source: Optional[str] = None,
    tag: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 1000,
    db: Session = Depends(get_db)
):
    q = db.query(TestCase)
    if category:
        q = q.filter(TestCase.category == category)
    if priority:
        q = q.filter(TestCase.priority == priority)
    if status:
        q = q.filter(TestCase.status == status)
    if spec_source:
        q = q.filter(TestCase.spec_source == spec_source)
    if tag:
        q = q.filter(TestCase.tags.contains(tag))
    if search:
        pat = f"%{search}%"
        q = q.filter(
            (TestCase.id.ilike(pat)) |
            (TestCase.title.ilike(pat)) |
            (TestCase.description.ilike(pat))
        )
    cases = q.order_by(TestCase.category, TestCase.id).offset(skip).limit(limit).all()
    results = []
    for tc in cases:
        r = TestCaseResponse.model_validate(tc)
        r.execution_count = db.query(sqlfunc.count(Execution.id)).filter(Execution.test_case_id == tc.id).scalar()
        r.comment_count = db.query(sqlfunc.count(Comment.id)).filter(Comment.test_case_id == tc.id).scalar()
        results.append(r)
    return results

@router.get("/categories")
def list_categories(db: Session = Depends(get_db)):
    rows = db.query(TestCase.category, sqlfunc.count(TestCase.id)).group_by(TestCase.category).all()
    return [{"category": r[0], "count": r[1]} for r in rows]

@router.get("/filters")
def get_filter_options(db: Session = Depends(get_db)):
    categories = [r[0] for r in db.query(TestCase.category).distinct().all()]
    priorities = [r[0] for r in db.query(TestCase.priority).distinct().all()]
    statuses = [r[0] for r in db.query(TestCase.status).distinct().all()]
    sources = [r[0] for r in db.query(TestCase.spec_source).distinct().all() if r[0]]
    return {"categories": sorted(categories), "priorities": sorted(priorities),
            "statuses": sorted(statuses), "spec_sources": sorted(sources)}

@router.get("/{test_id}", response_model=TestCaseResponse)
def get_test_case(test_id: str, db: Session = Depends(get_db)):
    tc = db.query(TestCase).filter(TestCase.id == test_id).first()
    if not tc:
        raise HTTPException(404, "Test case not found")
    r = TestCaseResponse.model_validate(tc)
    r.execution_count = db.query(sqlfunc.count(Execution.id)).filter(Execution.test_case_id == tc.id).scalar()
    r.comment_count = db.query(sqlfunc.count(Comment.id)).filter(Comment.test_case_id == tc.id).scalar()
    return r

@router.post("", response_model=TestCaseResponse, status_code=201)
def create_test_case(tc: TestCaseCreate, db: Session = Depends(get_db)):
    existing = db.query(TestCase).filter(TestCase.id == tc.id).first()
    if existing:
        raise HTTPException(409, f"Test case {tc.id} already exists")
    obj = TestCase(**tc.model_dump())
    db.add(obj)
    db.add(AuditLog(entity_type="test_case", entity_id=tc.id, action="create",
                    new_value=json.dumps(tc.model_dump())))
    db.commit()
    db.refresh(obj)
    return TestCaseResponse.model_validate(obj)

@router.put("/{test_id}", response_model=TestCaseResponse)
def update_test_case(test_id: str, data: TestCaseUpdate, changed_by: Optional[str] = None,
                     db: Session = Depends(get_db)):
    tc = db.query(TestCase).filter(TestCase.id == test_id).first()
    if not tc:
        raise HTTPException(404, "Test case not found")
    old = {c.name: getattr(tc, c.name) for c in TestCase.__table__.columns}
    updates = data.model_dump(exclude_unset=True)
    for k, v in updates.items():
        setattr(tc, k, v)
    db.add(AuditLog(entity_type="test_case", entity_id=test_id, action="update",
                    changed_by=changed_by, old_value=json.dumps(old, default=str),
                    new_value=json.dumps(updates)))
    db.commit()
    db.refresh(tc)
    r = TestCaseResponse.model_validate(tc)
    return r

@router.patch("/{test_id}/status", response_model=TestCaseResponse)
def update_status(test_id: str, data: StatusUpdate, db: Session = Depends(get_db)):
    tc = db.query(TestCase).filter(TestCase.id == test_id).first()
    if not tc:
        raise HTTPException(404, "Test case not found")
    old_status = tc.status
    tc.status = data.status
    db.add(AuditLog(entity_type="test_case", entity_id=test_id, action="status_change",
                    changed_by=data.changed_by,
                    old_value=json.dumps({"status": old_status}),
                    new_value=json.dumps({"status": data.status})))
    db.commit()
    db.refresh(tc)
    return TestCaseResponse.model_validate(tc)

@router.patch("/bulk-status", response_model=dict)
def bulk_update_status(data: BulkStatusUpdate, db: Session = Depends(get_db)):
    updated = 0
    for tid in data.ids:
        tc = db.query(TestCase).filter(TestCase.id == tid).first()
        if tc:
            old = tc.status
            tc.status = data.status
            db.add(AuditLog(entity_type="test_case", entity_id=tid, action="status_change",
                            changed_by=data.changed_by,
                            old_value=json.dumps({"status": old}),
                            new_value=json.dumps({"status": data.status})))
            updated += 1
    db.commit()
    return {"updated": updated}

@router.delete("/{test_id}")
def delete_test_case(test_id: str, db: Session = Depends(get_db)):
    tc = db.query(TestCase).filter(TestCase.id == test_id).first()
    if not tc:
        raise HTTPException(404, "Test case not found")
    db.add(AuditLog(entity_type="test_case", entity_id=test_id, action="delete"))
    db.delete(tc)
    db.commit()
    return {"deleted": test_id}

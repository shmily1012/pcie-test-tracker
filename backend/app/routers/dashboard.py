from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func as sqlfunc
from ..database import get_db
from ..models import TestCase
from ..schemas import DashboardSummary, CoverageItem, HeatmapCell
from typing import List

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

@router.get("/summary", response_model=DashboardSummary)
def get_summary(db: Session = Depends(get_db)):
    total = db.query(sqlfunc.count(TestCase.id)).scalar()
    by_status = {}
    for row in db.query(TestCase.status, sqlfunc.count(TestCase.id)).group_by(TestCase.status).all():
        by_status[row[0]] = row[1]
    by_priority = {}
    for row in db.query(TestCase.priority, sqlfunc.count(TestCase.id)).group_by(TestCase.priority).all():
        by_priority[row[0]] = row[1]
    by_category = {}
    for row in db.query(TestCase.category, sqlfunc.count(TestCase.id)).group_by(TestCase.category).all():
        by_category[row[0]] = row[1]
    
    passed = by_status.get("pass", 0)
    executed = sum(v for k, v in by_status.items() if k != "not_started")
    pass_rate = (passed / executed * 100) if executed > 0 else 0
    
    p0_total = db.query(sqlfunc.count(TestCase.id)).filter(TestCase.priority == "P0").scalar()
    p0_pass = db.query(sqlfunc.count(TestCase.id)).filter(
        TestCase.priority == "P0", TestCase.status == "pass").scalar()
    p0_coverage = (p0_pass / p0_total * 100) if p0_total > 0 else 0
    
    return DashboardSummary(
        total=total, by_status=by_status, by_priority=by_priority,
        by_category=by_category, pass_rate=round(pass_rate, 1),
        p0_coverage=round(p0_coverage, 1)
    )

@router.get("/coverage", response_model=List[CoverageItem])
def get_coverage(db: Session = Depends(get_db)):
    categories = db.query(TestCase.category).distinct().all()
    result = []
    for (cat,) in categories:
        cases = db.query(TestCase).filter(TestCase.category == cat).all()
        total = len(cases)
        passed = sum(1 for c in cases if c.status == "pass")
        failed = sum(1 for c in cases if c.status == "fail")
        blocked = sum(1 for c in cases if c.status == "blocked")
        skipped = sum(1 for c in cases if c.status == "skip")
        not_started = sum(1 for c in cases if c.status == "not_started")
        result.append(CoverageItem(
            category=cat, total=total, passed=passed, failed=failed,
            blocked=blocked, skipped=skipped, not_started=not_started,
            coverage_pct=round(passed / total * 100, 1) if total > 0 else 0
        ))
    return sorted(result, key=lambda x: x.category)

@router.get("/heatmap", response_model=List[HeatmapCell])
def get_heatmap(db: Session = Depends(get_db)):
    result = []
    rows = db.query(
        TestCase.category, TestCase.priority,
        sqlfunc.count(TestCase.id),
        sqlfunc.sum(sqlfunc.case((TestCase.status == "pass", 1), else_=0))
    ).group_by(TestCase.category, TestCase.priority).all()
    for cat, pri, total, passed in rows:
        result.append(HeatmapCell(
            category=cat, priority=pri, total=total, passed=passed or 0,
            coverage_pct=round((passed or 0) / total * 100, 1) if total > 0 else 0
        ))
    return result

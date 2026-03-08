from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..models import Execution, TestCase, AuditLog
from ..schemas import ExecutionCreate, ExecutionResponse
import json

router = APIRouter(prefix="/api/test-cases/{test_id}/executions", tags=["executions"])

@router.get("", response_model=List[ExecutionResponse])
def list_executions(test_id: str, db: Session = Depends(get_db)):
    return db.query(Execution).filter(Execution.test_case_id == test_id)\
             .order_by(Execution.executed_at.desc()).all()

@router.post("", response_model=ExecutionResponse, status_code=201)
def create_execution(test_id: str, data: ExecutionCreate, db: Session = Depends(get_db)):
    tc = db.query(TestCase).filter(TestCase.id == test_id).first()
    if not tc:
        raise HTTPException(404, "Test case not found")
    exe = Execution(test_case_id=test_id, **data.model_dump())
    db.add(exe)
    # Also update test case status
    tc.status = data.status
    db.add(AuditLog(entity_type="execution", entity_id=test_id, action="create",
                    changed_by=data.executed_by,
                    new_value=json.dumps(data.model_dump())))
    db.commit()
    db.refresh(exe)
    return exe

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class TestCaseBase(BaseModel):
    id: str
    title: str
    description: str = ""
    category: str = "Uncategorized"
    subcategory: Optional[str] = None
    priority: str = "P1"
    spec_source: Optional[str] = None
    spec_ref: Optional[str] = None
    ocp_req_id: Optional[str] = None
    tool: Optional[str] = None
    pass_fail_criteria: Optional[str] = None
    tags: Optional[str] = None
    status: str = "not_started"
    owner: Optional[str] = None
    notes: Optional[str] = None

class TestCaseCreate(TestCaseBase):
    pass

class TestCaseUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    priority: Optional[str] = None
    spec_source: Optional[str] = None
    spec_ref: Optional[str] = None
    ocp_req_id: Optional[str] = None
    tool: Optional[str] = None
    pass_fail_criteria: Optional[str] = None
    tags: Optional[str] = None
    status: Optional[str] = None
    owner: Optional[str] = None
    notes: Optional[str] = None

class TestCaseResponse(TestCaseBase):
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    execution_count: int = 0
    comment_count: int = 0
    class Config:
        from_attributes = True

class StatusUpdate(BaseModel):
    status: str
    changed_by: Optional[str] = None

class BulkStatusUpdate(BaseModel):
    ids: List[str]
    status: str
    changed_by: Optional[str] = None

class ExecutionCreate(BaseModel):
    status: str
    executed_by: Optional[str] = None
    environment: Optional[str] = None
    firmware_version: Optional[str] = None
    notes: Optional[str] = None

class ExecutionResponse(ExecutionCreate):
    id: int
    test_case_id: str
    executed_at: Optional[datetime] = None
    class Config:
        from_attributes = True

class CommentCreate(BaseModel):
    author: str = "Anonymous"
    content: str

class CommentResponse(CommentCreate):
    id: int
    test_case_id: str
    created_at: Optional[datetime] = None
    class Config:
        from_attributes = True

class AuditLogResponse(BaseModel):
    id: int
    entity_type: str
    entity_id: str
    action: str
    changed_by: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    changed_at: Optional[datetime] = None
    class Config:
        from_attributes = True

class DashboardSummary(BaseModel):
    total: int
    by_status: dict
    by_priority: dict
    by_category: dict
    pass_rate: float
    p0_coverage: float

class CoverageItem(BaseModel):
    category: str
    total: int
    passed: int
    failed: int
    blocked: int
    skipped: int
    not_started: int
    coverage_pct: float

class HeatmapCell(BaseModel):
    category: str
    priority: str
    total: int
    passed: int
    coverage_pct: float

class ImportResult(BaseModel):
    created: int
    updated: int
    errors: List[str]

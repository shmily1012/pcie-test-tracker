from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..models import Comment, TestCase
from ..schemas import CommentCreate, CommentResponse

router = APIRouter(prefix="/api/test-cases/{test_id}/comments", tags=["comments"])

@router.get("", response_model=List[CommentResponse])
def list_comments(test_id: str, db: Session = Depends(get_db)):
    return db.query(Comment).filter(Comment.test_case_id == test_id)\
             .order_by(Comment.created_at.asc()).all()

@router.post("", response_model=CommentResponse, status_code=201)
def create_comment(test_id: str, data: CommentCreate, db: Session = Depends(get_db)):
    tc = db.query(TestCase).filter(TestCase.id == test_id).first()
    if not tc:
        raise HTTPException(404, "Test case not found")
    c = Comment(test_case_id=test_id, **data.model_dump())
    db.add(c)
    db.commit()
    db.refresh(c)
    return c

from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from .database import Base
import datetime

class TestCase(Base):
    __tablename__ = "test_cases"
    
    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False, default="")
    category = Column(String, nullable=False, default="Uncategorized")
    subcategory = Column(String, nullable=True)
    priority = Column(String, nullable=False, default="P1")
    spec_source = Column(String, nullable=True)
    spec_ref = Column(String, nullable=True)
    ocp_req_id = Column(String, nullable=True)
    tool = Column(String, nullable=True)
    pass_fail_criteria = Column(Text, nullable=True)
    priority_rationale = Column(Text, nullable=True)
    test_method = Column(String, nullable=True)  # hardware_lab, software_automated, firmware_command, manual_inspection
    tags = Column(Text, nullable=True)  # JSON array
    status = Column(String, nullable=False, default="not_started")
    owner = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    executions = relationship("Execution", back_populates="test_case", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="test_case", cascade="all, delete-orphan")

class Execution(Base):
    __tablename__ = "executions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    test_case_id = Column(String, ForeignKey("test_cases.id"), nullable=False)
    status = Column(String, nullable=False)
    executed_by = Column(String, nullable=True)
    executed_at = Column(DateTime, default=func.now())
    environment = Column(String, nullable=True)
    firmware_version = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    attachments = Column(Text, nullable=True)  # JSON array
    
    test_case = relationship("TestCase", back_populates="executions")

class Comment(Base):
    __tablename__ = "comments"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    test_case_id = Column(String, ForeignKey("test_cases.id"), nullable=False)
    author = Column(String, nullable=False, default="Anonymous")
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=func.now())
    
    test_case = relationship("TestCase", back_populates="comments")

class AuditLog(Base):
    __tablename__ = "audit_log"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    entity_type = Column(String, nullable=False)
    entity_id = Column(String, nullable=False)
    action = Column(String, nullable=False)
    changed_by = Column(String, nullable=True)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    changed_at = Column(DateTime, default=func.now())

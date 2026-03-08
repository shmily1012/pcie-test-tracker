import pytest
import os
import tempfile
from app.seed import seed_from_directory
from app.database import Base, engine, SessionLocal
from app.models import TestCase

@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def test_seed_from_directory():
    with tempfile.TemporaryDirectory() as tmpdir:
        yaml_content = """
metadata:
  spec_source: "Seed Test"
categories:
  - name: "Cat"
    subcategories:
      - name: "Sub"
        items:
          - id: SEED-001
            title: "Seeded test"
            priority: P0
"""
        with open(os.path.join(tmpdir, "test.yaml"), "w") as f:
            f.write(yaml_content)

        stats = seed_from_directory(tmpdir)
        assert stats["total_created"] == 1

        db = SessionLocal()
        tc = db.query(TestCase).filter(TestCase.id == "SEED-001").first()
        assert tc is not None
        assert tc.title == "Seeded test"
        assert tc.spec_source == "Seed Test"
        db.close()

def test_seed_reset_mode():
    with tempfile.TemporaryDirectory() as tmpdir:
        yaml_content = """
metadata:
  spec_source: "Test"
categories:
  - name: "Cat"
    subcategories:
      - name: "Sub"
        items:
          - id: RESET-001
            title: "First"
            priority: P0
"""
        with open(os.path.join(tmpdir, "test.yaml"), "w") as f:
            f.write(yaml_content)

        # Seed once
        seed_from_directory(tmpdir)
        # Seed again with reset
        stats = seed_from_directory(tmpdir, reset=True)
        assert stats["total_created"] == 1

        db = SessionLocal()
        count = db.query(TestCase).count()
        assert count == 1
        db.close()

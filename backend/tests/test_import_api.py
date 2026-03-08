import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, engine

@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

client = TestClient(app)

SAMPLE_YAML = b"""
metadata:
  spec_source: "Test"
categories:
  - name: "Cat"
    subcategories:
      - name: "Sub"
        items:
          - id: T-001
            title: "Test one"
            description: "Desc"
            priority: P0
"""

def test_import_yaml_endpoint():
    response = client.post(
        "/api/import/yaml",
        files={"file": ("test.yaml", SAMPLE_YAML, "application/x-yaml")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["created"] == 1
    assert data["updated"] == 0
    assert data["errors"] == []

def test_import_yaml_with_spec_source_override():
    response = client.post(
        "/api/import/yaml",
        files={"file": ("test.yaml", SAMPLE_YAML, "application/x-yaml")},
        data={"spec_source": "Override"},
    )
    assert response.status_code == 200
    tc = client.get("/api/test-cases/T-001").json()
    assert tc["spec_source"] == "Override"

import pytest
from app.services.importer import parse_yaml_seed

SAMPLE_YAML = """
metadata:
  version: "1.0"
  spec_source: "Test Spec"
  target: "Test Device"

categories:
  - name: "Category A"
    subcategories:
      - name: "Sub 1"
        items:
          - id: TC-001
            title: "Test case one"
            description: "Description one"
            priority: P0
            tool: "Linux"
            spec_ref: "§1.1"
          - id: TC-002
            title: "Test case two"
            description: "Description two"
            priority: P1
"""

def test_parse_yaml_seed_returns_list():
    result = parse_yaml_seed(SAMPLE_YAML, spec_source_override=None)
    assert isinstance(result, list)
    assert len(result) == 2

def test_parse_yaml_seed_fields():
    result = parse_yaml_seed(SAMPLE_YAML)
    tc1 = result[0]
    assert tc1["id"] == "TC-001"
    assert tc1["title"] == "Test case one"
    assert tc1["description"] == "Description one"
    assert tc1["category"] == "Category A"
    assert tc1["subcategory"] == "Sub 1"
    assert tc1["priority"] == "P0"
    assert tc1["tool"] == "Linux"
    assert tc1["spec_ref"] == "§1.1"
    assert tc1["spec_source"] == "Test Spec"
    assert tc1["status"] == "not_started"

def test_parse_yaml_seed_spec_source_override():
    result = parse_yaml_seed(SAMPLE_YAML, spec_source_override="Override Spec")
    assert result[0]["spec_source"] == "Override Spec"

def test_parse_yaml_seed_missing_optional_fields():
    result = parse_yaml_seed(SAMPLE_YAML)
    tc2 = result[1]
    assert tc2["id"] == "TC-002"
    assert tc2["tool"] is None
    assert tc2["spec_ref"] is None

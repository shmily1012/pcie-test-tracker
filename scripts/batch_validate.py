#!/usr/bin/env python3
"""
Batch validation helper for Auggie + Glean MCP automation.

This script outputs test cases in a format that Auggie can process in a loop,
calling Glean MCP for each test and applying results automatically.

Usage:
    # Get all tests as JSON array for batch processing
    python scripts/batch_validate.py --export --priority P0 > /tmp/tests_to_validate.json
    
    # Apply a batch of results
    python scripts/batch_validate.py --import-results /tmp/validation_results.json
"""

import argparse
import json
import yaml
import sys
from pathlib import Path
from datetime import date
from typing import Dict, List, Optional

SEED_DIR = Path(__file__).parent.parent / "data" / "seeds"


def get_all_tests(priority: Optional[str] = None, force: bool = False) -> List[Dict]:
    """Get all tests that need validation."""
    tests = []
    
    for filepath in sorted(SEED_DIR.glob('*.yaml')):
        with open(filepath, 'r') as f:
            data = yaml.safe_load(f)
        
        for cat in data.get('categories', []):
            for subcat in cat.get('subcategories', []):
                for item in subcat.get('items', []):
                    if priority and item.get('priority') != priority:
                        continue
                    
                    # Skip already Glean-validated unless force
                    if not force and item.get('validation', {}).get('glean_validated'):
                        continue
                    
                    tests.append({
                        'id': item.get('id'),
                        'title': item.get('title'),
                        'spec_ref': item.get('spec_ref', ''),
                        'pass_criteria': item.get('pass_criteria', '')[:1000],
                        'file': filepath.name
                    })
    
    return tests


def build_prompt(test: Dict) -> str:
    """Build Glean validation prompt."""
    return f"""Validate this PCIe test case against PCIe 5.0 Base Specification:

**Test ID:** {test['id']}
**Title:** {test['title']}  
**Spec Reference:** {test['spec_ref']}
**Pass Criteria:** {test['pass_criteria'][:800]}

Check: 1) Are spec refs correct? 2) Are numeric values accurate? 3) Any errors?

Return JSON only: {{"status":"valid" or "corrected","issues":[],"corrected_spec_ref":"if needed","corrected_pass_criteria":"if needed"}}"""


def apply_result(test_id: str, result: Dict) -> bool:
    """Apply validation result to a test in its YAML file."""
    for filepath in sorted(SEED_DIR.glob('*.yaml')):
        with open(filepath, 'r') as f:
            data = yaml.safe_load(f)
        
        found = False
        for cat in data.get('categories', []):
            for subcat in cat.get('subcategories', []):
                for item in subcat.get('items', []):
                    if item.get('id') == test_id:
                        found = True
                        today = date.today().isoformat()
                        status = result.get('status', 'needs_review')
                        issues = result.get('issues', [])
                        
                        changes = []
                        if status == 'valid':
                            changes.append("Validated via Glean MCP - accurate")
                        elif status == 'corrected':
                            if result.get('corrected_spec_ref'):
                                if 'original_spec_ref' not in item:
                                    item['original_spec_ref'] = item.get('spec_ref', '')
                                item['spec_ref'] = result['corrected_spec_ref']
                                changes.append("Spec ref corrected")
                            if result.get('corrected_pass_criteria'):
                                if 'original_pass_criteria' not in item:
                                    item['original_pass_criteria'] = item.get('pass_criteria', '')
                                item['pass_criteria'] = result['corrected_pass_criteria']
                                changes.append("Pass criteria corrected")
                            changes.extend([i[:80] for i in issues[:3]])
                        
                        item['validation'] = {
                            'status': status,
                            'validated_at': today,
                            'glean_validated': True,
                            'changes_made': changes[:5] if changes else ["Validated"]
                        }
                        break
                if found:
                    break
            if found:
                break
        
        if found:
            with open(filepath, 'w') as f:
                yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
            return True
    
    return False


def import_results(results_file: Path):
    """Import and apply batch results."""
    with open(results_file, 'r') as f:
        results = json.load(f)
    
    for r in results:
        test_id = r.get('test_id')
        result = r.get('result', {})
        if apply_result(test_id, result):
            print(f"✓ {test_id}: {result.get('status', 'unknown')}")
        else:
            print(f"✗ {test_id}: not found")


def main():
    parser = argparse.ArgumentParser(description='Batch validation helper')
    parser.add_argument('--export', action='store_true', help='Export tests as JSON')
    parser.add_argument('--priority', choices=['P0', 'P1', 'P2', 'P3'])
    parser.add_argument('--force', action='store_true')
    parser.add_argument('--import-results', type=Path, help='Import results JSON')
    parser.add_argument('--with-prompts', action='store_true', help='Include prompts in export')
    
    args = parser.parse_args()
    
    if args.import_results:
        import_results(args.import_results)
        return
    
    if args.export:
        tests = get_all_tests(args.priority, args.force)
        if args.with_prompts:
            for t in tests:
                t['prompt'] = build_prompt(t)
        print(json.dumps(tests, indent=2))
        return
    
    parser.print_help()


if __name__ == '__main__':
    main()


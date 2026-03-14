#!/usr/bin/env python3
"""
PCIe Test Validation via Auggie CLI + Glean MCP

This script is designed to be run within an Auggie CLI session that has Glean MCP enabled.
It extracts test cases, generates validation prompts, and expects Auggie to call Glean.

Usage (run via Auggie CLI):
    auggie "Run scripts/auggie_glean_validate.py with --file 06_power_management.yaml"
    
Or generate prompts for manual Auggie processing:
    python scripts/auggie_glean_validate.py --generate-prompts --priority P0 --output /tmp/prompts.json
"""

import argparse
import json
import yaml
import sys
from pathlib import Path
from datetime import date
from typing import Optional, Dict, List, Any

SEED_DIR = Path(__file__).parent.parent / "data" / "seeds"
RESULTS_FILE = Path(__file__).parent.parent / "data" / "glean_validation_results.json"


def load_yaml_file(filepath: Path) -> Dict:
    """Load a YAML file."""
    with open(filepath, 'r') as f:
        return yaml.safe_load(f)


def save_yaml_file(filepath: Path, data: Dict):
    """Save YAML file preserving structure."""
    with open(filepath, 'w') as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, 
                  sort_keys=False, width=100)


def get_tests_to_validate(data: Dict, priority: Optional[str] = None, 
                          force: bool = False) -> List[Dict]:
    """Get test cases that need validation."""
    tests = []
    for cat in data.get('categories', []):
        for subcat in cat.get('subcategories', []):
            for item in subcat.get('items', []):
                if priority and item.get('priority') != priority:
                    continue
                # Skip if already Glean-validated (unless force)
                if not force and item.get('validation', {}).get('glean_validated'):
                    continue
                tests.append(item)
    return tests


def build_glean_prompt(test: Dict) -> str:
    """Build a Glean query prompt for validation."""
    return f"""Validate this PCIe test case against the PCIe 5.0 Base Specification:

**Test ID:** {test.get('id')}
**Title:** {test.get('title')}
**Spec Reference:** {test.get('spec_ref', 'None')}
**Pass Criteria:** {test.get('pass_criteria', 'None')[:800]}

Please check:
1. Are the spec section references (§X.X.X, Table X-X) correct for PCIe 5.0?
2. Are the numeric values (timing, voltage, thresholds) accurate per the spec?
3. Any technical inaccuracies?

Respond in JSON format:
{{"status": "valid" or "corrected", "issues": ["list of issues"], "corrected_spec_ref": "if needed", "corrected_pass_criteria": "if needed", "summary": "brief summary"}}"""


def generate_prompts_file(tests: List[Dict], output_file: Path):
    """Generate a JSON file with all prompts for batch processing."""
    prompts = []
    for test in tests:
        prompts.append({
            "test_id": test.get('id'),
            "title": test.get('title'),
            "file": test.get('_source_file', 'unknown'),
            "prompt": build_glean_prompt(test),
            "original_spec_ref": test.get('spec_ref'),
            "original_pass_criteria": test.get('pass_criteria')
        })
    
    with open(output_file, 'w') as f:
        json.dump(prompts, f, indent=2)
    
    print(f"Generated {len(prompts)} prompts to: {output_file}")
    return prompts


def apply_validation_result(test: Dict, result: Dict) -> Dict:
    """Apply a validation result to a test case."""
    today = date.today().isoformat()
    
    status = result.get('status', 'needs_review')
    issues = result.get('issues', [])
    summary = result.get('summary', '')
    
    # Build changes list
    changes = []
    if status == 'valid':
        changes.append("Validated via Glean MCP - spec refs and criteria accurate")
    elif status == 'corrected':
        if result.get('corrected_spec_ref'):
            if 'original_spec_ref' not in test:
                test['original_spec_ref'] = test.get('spec_ref', '')
            test['spec_ref'] = result['corrected_spec_ref']
            changes.append("Spec reference corrected")
        if result.get('corrected_pass_criteria'):
            if 'original_pass_criteria' not in test:
                test['original_pass_criteria'] = test.get('pass_criteria', '')
            test['pass_criteria'] = result['corrected_pass_criteria']
            changes.append("Pass criteria corrected")
        changes.extend(issues[:3])
    else:
        changes.append(f"Needs review: {summary[:100]}")
    
    test['validation'] = {
        'status': status,
        'validated_at': today,
        'glean_validated': True,
        'changes_made': changes[:5]
    }
    
    return test


def print_test_for_auggie(test: Dict):
    """Print a test case for Auggie to process via Glean MCP."""
    print("\n" + "="*70)
    print(f"TEST: {test.get('id')} - {test.get('title')}")
    print("="*70)
    print("\nGLEAN QUERY:")
    print(build_glean_prompt(test))
    print("\n" + "-"*70)
    print("Please query Glean with the above and return JSON result.")
    print("-"*70)


def main():
    parser = argparse.ArgumentParser(
        description='Validate PCIe tests via Auggie CLI + Glean MCP'
    )
    parser.add_argument('--file', type=str, help='Specific YAML file (name only)')
    parser.add_argument('--all', action='store_true', help='Process all seed files')
    parser.add_argument('--priority', choices=['P0', 'P1', 'P2', 'P3'])
    parser.add_argument('--force', action='store_true', help='Re-validate already validated')
    parser.add_argument('--generate-prompts', action='store_true', 
                        help='Generate prompts JSON file')
    parser.add_argument('--output', type=Path, default=RESULTS_FILE)
    parser.add_argument('--test-id', type=str, help='Validate specific test only')
    parser.add_argument('--list', action='store_true', help='List tests to validate')
    
    args = parser.parse_args()
    
    # Determine files to process
    if args.file:
        filepath = SEED_DIR / args.file if not args.file.startswith('/') else Path(args.file)
        files = [filepath]
    elif args.all:
        files = sorted(SEED_DIR.glob('*.yaml'))
    else:
        parser.print_help()
        print("\nUse --file <name> or --all")
        sys.exit(1)
    
    # Collect all tests
    all_tests = []
    for filepath in files:
        if not filepath.exists():
            print(f"File not found: {filepath}")
            continue
        data = load_yaml_file(filepath)
        tests = get_tests_to_validate(data, args.priority, args.force)
        for t in tests:
            t['_source_file'] = str(filepath)
        all_tests.extend(tests)
    
    if args.test_id:
        all_tests = [t for t in all_tests if t.get('id') == args.test_id]
    
    print(f"\nFound {len(all_tests)} tests to validate")
    
    if args.list:
        for t in all_tests:
            print(f"  {t.get('id')}: {t.get('title', '')[:50]}")
        return
    
    if args.generate_prompts:
        generate_prompts_file(all_tests, args.output)
        return
    
    # Interactive mode - print tests for Auggie to process
    for test in all_tests:
        print_test_for_auggie(test)


if __name__ == '__main__':
    main()

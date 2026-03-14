#!/usr/bin/env python3
"""
Single Test Validator - For use with Auggie CLI + Glean MCP

This script extracts a single test case and outputs it for Auggie to validate via Glean.
Auggie should:
1. Run this script to get the test details
2. Query Glean MCP with the prompt
3. Run the --apply command with the JSON result

Usage:
    # Step 1: Get test to validate
    python scripts/validate_single_test.py --next --priority P0

    # Step 2: Auggie queries Glean with the output prompt

    # Step 3: Apply the result
    python scripts/validate_single_test.py --apply --test-id PHY-001 --result '{"status":"valid"}'
"""

import argparse
import json
import yaml
import sys
from pathlib import Path
from datetime import date

SEED_DIR = Path(__file__).parent.parent / "data" / "seeds"
STATE_FILE = Path(__file__).parent.parent / "data" / ".validation_state.json"


def load_state() -> dict:
    """Load validation state (tracks which tests have been processed)."""
    if STATE_FILE.exists():
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return {"processed": [], "current": None}


def save_state(state: dict):
    """Save validation state."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def find_test_by_id(test_id: str) -> tuple:
    """Find a test by ID, return (filepath, test_dict, category_path)."""
    for filepath in sorted(SEED_DIR.glob('*.yaml')):
        with open(filepath, 'r') as f:
            data = yaml.safe_load(f)

        for cat_idx, cat in enumerate(data.get('categories', [])):
            for subcat_idx, subcat in enumerate(cat.get('subcategories', [])):
                for item_idx, item in enumerate(subcat.get('items', [])):
                    if item.get('id') == test_id:
                        path = (cat_idx, subcat_idx, item_idx)
                        return filepath, data, item, path
    return None, None, None, None


def get_next_test(priority: str = None, force: bool = False) -> dict:
    """Get the next test that needs validation."""
    state = load_state()

    for filepath in sorted(SEED_DIR.glob('*.yaml')):
        with open(filepath, 'r') as f:
            data = yaml.safe_load(f)

        for cat in data.get('categories', []):
            for subcat in cat.get('subcategories', []):
                for item in subcat.get('items', []):
                    test_id = item.get('id')

                    # Filter by priority
                    if priority and item.get('priority') != priority:
                        continue

                    # Skip already processed in this session
                    if test_id in state.get('processed', []):
                        continue

                    # Skip already Glean-validated (unless force)
                    if not force and item.get('validation', {}).get('glean_validated'):
                        continue

                    item['_file'] = str(filepath)
                    return item

    return None


def build_prompt(test: dict) -> str:
    """Build the Glean validation prompt."""
    return f"""Validate this PCIe test case against the PCIe 5.0 Base Specification:

**Test ID:** {test.get('id')}
**Title:** {test.get('title')}
**Spec Reference:** {test.get('spec_ref', 'None')}
**Pass Criteria:** {test.get('pass_criteria', 'None')[:800]}

Check:
1. Are the spec section references (§X.X.X, Table X-X) correct for PCIe 5.0?
2. Are the numeric values (timing, voltage, thresholds) accurate?
3. Any technical errors?

Return JSON:
{{"status": "valid" or "corrected", "issues": ["list"], "corrected_spec_ref": "if needed", "corrected_pass_criteria": "if needed"}}"""


def apply_result(test_id: str, result: dict):
    """Apply validation result to a test case."""
    filepath, data, test, path = find_test_by_id(test_id)

    if not test:
        print(f"ERROR: Test {test_id} not found")
        return False

    # Apply the result
    cat_idx, subcat_idx, item_idx = path
    item = data['categories'][cat_idx]['subcategories'][subcat_idx]['items'][item_idx]

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

    # Save the file
    with open(filepath, 'w') as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    # Update state
    state = load_state()
    if test_id not in state['processed']:
        state['processed'].append(test_id)
    save_state(state)

    print(f"✓ Applied {status} to {test_id}")
    return True


def reset_state():
    """Reset the validation state (start fresh)."""
    if STATE_FILE.exists():
        STATE_FILE.unlink()
    print("State reset - will start from beginning")


def show_status(priority: str = None):
    """Show validation progress."""
    total = 0
    validated = 0
    glean_verified = 0

    for filepath in sorted(SEED_DIR.glob('*.yaml')):
        with open(filepath, 'r') as f:
            data = yaml.safe_load(f)

        for cat in data.get('categories', []):
            for subcat in cat.get('subcategories', []):
                for item in subcat.get('items', []):
                    if priority and item.get('priority') != priority:
                        continue
                    total += 1
                    val = item.get('validation', {})
                    if val:
                        validated += 1
                        if val.get('glean_validated'):
                            glean_verified += 1

    pct = f"{100*glean_verified/total:.1f}%" if total else "N/A"
    print(f"\nValidation Status {f'[{priority}]' if priority else ''}")
    print(f"  Total tests:     {total}")
    print(f"  Glean-verified:  {glean_verified} ({pct})")
    print(f"  Remaining:       {total - glean_verified}")


def main():
    parser = argparse.ArgumentParser(description='Single test validator for Auggie + Glean MCP')
    parser.add_argument('--next', action='store_true', help='Get next test to validate')
    parser.add_argument('--test-id', type=str, help='Get/apply specific test')
    parser.add_argument('--priority', choices=['P0', 'P1', 'P2', 'P3'])
    parser.add_argument('--force', action='store_true', help='Include already validated')
    parser.add_argument('--apply', action='store_true', help='Apply validation result')
    parser.add_argument('--result', type=str, help='JSON result to apply')
    parser.add_argument('--reset', action='store_true', help='Reset state')
    parser.add_argument('--status', action='store_true', help='Show progress')

    args = parser.parse_args()

    if args.reset:
        reset_state()
        return

    if args.status:
        show_status(args.priority)
        return

    if args.apply:
        if not args.test_id or not args.result:
            print("ERROR: --apply requires --test-id and --result")
            sys.exit(1)
        try:
            result = json.loads(args.result)
        except json.JSONDecodeError:
            print(f"ERROR: Invalid JSON: {args.result}")
            sys.exit(1)
        apply_result(args.test_id, result)
        return

    if args.test_id:
        filepath, data, test, path = find_test_by_id(args.test_id)
        if test:
            print(f"\n=== {test.get('id')}: {test.get('title')} ===")
            print(f"File: {filepath.name}")
            print(f"\nGLEAN PROMPT:\n")
            print(build_prompt(test))
        else:
            print(f"Test {args.test_id} not found")
        return

    if args.next:
        test = get_next_test(args.priority, args.force)
        if test:
            print(f"\n=== NEXT TEST: {test.get('id')} ===")
            print(f"Title: {test.get('title')}")
            print(f"File: {test.get('_file')}")
            print(f"\n{'='*60}")
            print("GLEAN PROMPT:")
            print('='*60)
            print(build_prompt(test))
            print('='*60)
            print(f"\nAfter querying Glean, run:")
            print(f"  python scripts/validate_single_test.py --apply --test-id {test.get('id')} --result '<JSON>'")
        else:
            print("No more tests to validate!")
            show_status(args.priority)
        return

    parser.print_help()


if __name__ == '__main__':
    main()


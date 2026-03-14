#!/usr/bin/env python3
"""
Glean API Validator for PCIe Test Cases

This script calls the Glean API directly to validate test cases.
Requires GLEAN_API_TOKEN environment variable to be set.

Usage:
    export GLEAN_API_TOKEN="your-token"
    python scripts/glean_validator.py --file data/seeds/06_power_management.yaml --priority P0

Or use in automated mode to re-validate all tests:
    python scripts/glean_validator.py --all --priority P0 --auto
"""

import os
import sys
import json
import time
import argparse
import requests
import yaml
from pathlib import Path
from datetime import date
from typing import Optional, Dict, List, Any

# Configuration
GLEAN_API_URL = os.environ.get('GLEAN_API_URL', 'https://api.glean.com/v1/chat')
GLEAN_API_TOKEN = os.environ.get('GLEAN_API_TOKEN', '')
RATE_LIMIT_DELAY = 2  # seconds between API calls

SEED_DIR = Path(__file__).parent.parent / "data" / "seeds"
RESULTS_DIR = Path(__file__).parent.parent / "data" / "validation_results"


def call_glean_api(prompt: str) -> Optional[str]:
    """Call Glean API and return the response."""
    if not GLEAN_API_TOKEN:
        print("ERROR: GLEAN_API_TOKEN not set")
        return None

    headers = {
        "Authorization": f"Bearer {GLEAN_API_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "query": prompt,
        "mode": "DEFAULT"  # or "EXPERT" for more detailed responses
    }

    try:
        response = requests.post(GLEAN_API_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        return data.get('response', {}).get('text', '')
    except requests.exceptions.RequestException as e:
        print(f"  API Error: {e}")
        return None


def build_validation_prompt(test: Dict) -> str:
    """Build a structured prompt for Glean validation."""
    return f"""Validate this PCIe test case against PCIe 5.0 Base Specification:

TEST ID: {test.get('id')}
TITLE: {test.get('title')}
SPEC REFERENCE: {test.get('spec_ref', 'None')}
PASS CRITERIA: {test.get('pass_criteria', 'None')[:600]}

Check:
1. Are the spec section numbers (e.g., §8.3.6, Table 8-6) correct for PCIe 5.0?
2. Are the numeric values in pass criteria (timing, voltage, thresholds) accurate?
3. Any technical errors?

Reply with JSON:
{{"status": "valid" or "corrected", "issues": ["list issues"], "spec_ref_fix": "corrected ref if needed", "pass_criteria_fix": "corrected criteria if needed"}}"""


def parse_validation_response(response: str) -> Dict:
    """Parse Glean response into structured result."""
    import re

    # Try to extract JSON
    json_match = re.search(r'\{[^{}]*\}', response.replace('\n', ' '))
    if json_match:
        try:
            result = json.loads(json_match.group())
            return {
                "status": result.get("status", "needs_review"),
                "issues": result.get("issues", []),
                "spec_ref_fix": result.get("spec_ref_fix"),
                "pass_criteria_fix": result.get("pass_criteria_fix"),
                "raw_response": response[:500]
            }
        except json.JSONDecodeError:
            pass

    # Fallback: text analysis
    response_lower = response.lower()
    if any(w in response_lower for w in ['incorrect', 'wrong', 'should be', 'error']):
        status = "corrected"
    elif any(w in response_lower for w in ['correct', 'accurate', 'valid']):
        status = "valid"
    else:
        status = "needs_review"

    return {
        "status": status,
        "issues": [],
        "raw_response": response[:500]
    }


def validate_test(test: Dict, auto_apply: bool = False) -> Dict:
    """Validate a single test case through Glean."""
    test_id = test.get('id', 'Unknown')
    print(f"  Validating {test_id}...", end='', flush=True)

    prompt = build_validation_prompt(test)
    response = call_glean_api(prompt)

    if not response:
        print(" [API ERROR]")
        return {"status": "error", "issues": ["API call failed"]}

    result = parse_validation_response(response)
    print(f" [{result['status']}]")

    # Apply validation to test
    today = date.today().isoformat()
    changes = result.get('issues', [])
    if result.get('spec_ref_fix'):
        changes.append(f"Spec ref: {result['spec_ref_fix'][:100]}")
    if result.get('pass_criteria_fix'):
        changes.append(f"Pass criteria updated")

    test['validation'] = {
        "status": result['status'],
        "validated_at": today,
        "glean_validated": True,
        "changes_made": changes[:5] if changes else ["Validated via Glean API"]
    }

    # Store original values before correction
    if result['status'] == 'corrected' and auto_apply:
        if result.get('spec_ref_fix') and 'original_spec_ref' not in test:
            test['original_spec_ref'] = test.get('spec_ref', '')
            test['spec_ref'] = result['spec_ref_fix']
        if result.get('pass_criteria_fix') and 'original_pass_criteria' not in test:
            test['original_pass_criteria'] = test.get('pass_criteria', '')
            test['pass_criteria'] = result['pass_criteria_fix']

    return result


def process_file(filepath: Path, priority: Optional[str], auto_apply: bool, force: bool) -> Dict:
    """Process all tests in a YAML file."""
    print(f"\nProcessing: {filepath.name}")

    with open(filepath, 'r') as f:
        data = yaml.safe_load(f)

    stats = {"total": 0, "validated": 0, "valid": 0, "corrected": 0, "error": 0}

    for cat in data.get('categories', []):
        for subcat in cat.get('subcategories', []):
            for test in subcat.get('items', []):
                if priority and test.get('priority') != priority:
                    continue

                stats['total'] += 1

                # Skip already validated unless force
                if not force and test.get('validation', {}).get('glean_validated'):
                    continue

                result = validate_test(test, auto_apply)
                stats['validated'] += 1
                stats[result['status']] = stats.get(result['status'], 0) + 1

                # Rate limiting
                time.sleep(RATE_LIMIT_DELAY)

    # Save updated file
    if stats['validated'] > 0:
        with open(filepath, 'w') as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        print(f"  Saved {stats['validated']} validations")

    return stats




def main():
    parser = argparse.ArgumentParser(description='Validate PCIe tests via Glean API')
    parser.add_argument('--file', type=Path, help='Specific YAML file')
    parser.add_argument('--all', action='store_true', help='Process all seed files')
    parser.add_argument('--priority', choices=['P0', 'P1', 'P2', 'P3'], help='Filter by priority')
    parser.add_argument('--auto', action='store_true', help='Auto-apply corrections')
    parser.add_argument('--force', action='store_true', help='Re-validate already validated')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done')

    args = parser.parse_args()

    if not GLEAN_API_TOKEN and not args.dry_run:
        print("ERROR: Set GLEAN_API_TOKEN environment variable")
        print("  export GLEAN_API_TOKEN='your-token'")
        sys.exit(1)

    files = []
    if args.file:
        files = [args.file]
    elif args.all:
        files = sorted(SEED_DIR.glob('*.yaml'))
    else:
        parser.print_help()
        sys.exit(1)

    if args.dry_run:
        print("\n=== DRY RUN - No changes will be made ===\n")
        for f in files:
            with open(f, 'r') as fp:
                data = yaml.safe_load(fp)
            count = 0
            for cat in data.get('categories', []):
                for subcat in cat.get('subcategories', []):
                    for test in subcat.get('items', []):
                        if args.priority and test.get('priority') != args.priority:
                            continue
                        if args.force or not test.get('validation', {}).get('glean_validated'):
                            count += 1
            print(f"  {f.name}: {count} tests to validate")
        return

    total_stats = {"total": 0, "validated": 0, "valid": 0, "corrected": 0, "error": 0}

    for filepath in files:
        stats = process_file(filepath, args.priority, args.auto, args.force)
        for k in stats:
            total_stats[k] = total_stats.get(k, 0) + stats[k]

    print("\n" + "="*50)
    print("VALIDATION COMPLETE")
    print("="*50)
    print(f"Total tests:  {total_stats['total']}")
    print(f"Validated:    {total_stats['validated']}")
    print(f"  Valid:      {total_stats['valid']}")
    print(f"  Corrected:  {total_stats['corrected']}")
    print(f"  Errors:     {total_stats.get('error', 0)}")


if __name__ == '__main__':
    main()
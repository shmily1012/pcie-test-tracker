#!/usr/bin/env python3
"""
PCIe Test Case Validation Script using Glean

This script reads test cases from YAML files, queries Glean for validation,
and updates the YAML files with validation results.

Usage:
    python scripts/validate_with_glean.py --file data/seeds/01_physical_layer.yaml
    python scripts/validate_with_glean.py --all --priority P0
    python scripts/validate_with_glean.py --test-id PHY-001
    python scripts/validate_with_glean.py --dry-run  # Show what would be validated
"""

import argparse
import yaml
import json
import os
import sys
import re
from datetime import date
from pathlib import Path
from typing import Optional, List, Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Glean MCP configuration - adjust based on your setup
GLEAN_MCP_ENABLED = os.environ.get('GLEAN_MCP_ENABLED', 'false').lower() == 'true'

SEED_DIR = Path(__file__).parent.parent / "data" / "seeds"
VALIDATION_LOG = Path(__file__).parent.parent / "data" / "validation_log.jsonl"


def load_yaml_file(filepath: Path) -> Dict:
    """Load a YAML file and return its contents."""
    with open(filepath, 'r') as f:
        return yaml.safe_load(f)


def save_yaml_file(filepath: Path, data: Dict):
    """Save data to a YAML file, preserving formatting as much as possible."""
    with open(filepath, 'w') as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True,
                  sort_keys=False, width=100)


def get_all_test_cases(data: Dict, priority_filter: Optional[str] = None) -> List[Dict]:
    """Extract all test cases from parsed YAML data."""
    tests = []
    for cat in data.get('categories', []):
        for subcat in cat.get('subcategories', []):
            for item in subcat.get('items', []):
                if priority_filter and item.get('priority') != priority_filter:
                    continue
                tests.append(item)
    return tests


def needs_validation(test: Dict, force: bool = False) -> bool:
    """Check if a test case needs validation."""
    if force:
        return True
    validation = test.get('validation', {})
    if not validation:
        return True
    status = validation.get('status', '')
    # Re-validate if status is needs_review or empty
    return status in ['needs_review', '']


def build_glean_prompt(test: Dict) -> str:
    """Build a Glean query prompt for a test case."""
    prompt = f"""I'm validating a PCIe test case against the PCIe 5.0 Base Specification. Please verify technical accuracy:

**Test ID:** {test.get('id', 'Unknown')}
**Title:** {test.get('title', 'Unknown')}
**Description:** {test.get('description', 'N/A')[:500]}
**Spec Reference:** {test.get('spec_ref', 'None provided')}
**Pass Criteria:** {test.get('pass_criteria', 'None provided')[:500]}

Please validate:
1. Are the spec section references correct for PCIe 5.0?
2. Are the pass criteria values (timing, thresholds, etc.) accurate per the spec?
3. Are there any technical inaccuracies or missing requirements?

Respond in this JSON format:
{{
    "status": "valid" or "corrected" or "needs_review",
    "spec_ref_accurate": true/false,
    "pass_criteria_accurate": true/false,
    "issues": ["list of issues found"],
    "corrections": {{
        "spec_ref": "corrected spec reference if needed",
        "pass_criteria": "corrected pass criteria if needed"
    }},
    "notes": "brief summary"
}}"""
    return prompt


def parse_glean_response(response: str) -> Dict:
    """Parse Glean response and extract validation results."""
    # Try to find JSON in the response
    json_match = re.search(r'\{[\s\S]*\}', response)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass

    # Fallback: parse text response
    result = {
        "status": "needs_review",
        "issues": [],
        "corrections": {},
        "notes": ""
    }

    response_lower = response.lower()

    # Detect if corrections are needed
    if any(word in response_lower for word in ['incorrect', 'wrong', 'should be', 'not accurate', 'fix']):
        result["status"] = "corrected"
    elif any(word in response_lower for word in ['correct', 'accurate', 'valid', 'matches']):
        result["status"] = "valid"

    result["notes"] = response[:500]  # First 500 chars as notes

    return result


def update_test_validation(test: Dict, validation_result: Dict, glean_response: str) -> Dict:
    """Update a test case with validation results."""
    today = date.today().isoformat()

    status = validation_result.get("status", "needs_review")
    issues = validation_result.get("issues", [])
    corrections = validation_result.get("corrections", {})
    notes = validation_result.get("notes", "")

    # Build changes_made list
    changes_made = []
    if status == "valid":
        changes_made.append("Validated via Glean - spec refs and pass criteria accurate")
    elif status == "corrected":
        if corrections.get("spec_ref"):
            # Store original before updating
            if "original_spec_ref" not in test:
                test["original_spec_ref"] = test.get("spec_ref", "")
            changes_made.append(f"Spec ref corrected")
        if corrections.get("pass_criteria"):
            if "original_pass_criteria" not in test:
                test["original_pass_criteria"] = test.get("pass_criteria", "")
            changes_made.append(f"Pass criteria corrected")
        for issue in issues:
            changes_made.append(issue[:100])  # Truncate long issues
    else:
        changes_made.append("Requires manual review - see notes")

    # Add validation block
    test["validation"] = {
        "status": status,
        "validated_at": today,
        "glean_validated": True,
        "changes_made": changes_made[:5],  # Limit to 5 items
    }

    # Apply corrections if provided
    if status == "corrected":
        if corrections.get("spec_ref"):
            test["spec_ref"] = corrections["spec_ref"]
        if corrections.get("pass_criteria"):
            test["pass_criteria"] = corrections["pass_criteria"]

    return test


def log_validation(test_id: str, filepath: str, prompt: str, response: str, result: Dict):
    """Log validation to JSONL file for audit trail."""
    log_entry = {
        "timestamp": date.today().isoformat(),
        "test_id": test_id,
        "file": str(filepath),
        "prompt": prompt[:1000],
        "response": response[:2000],
        "result": result
    }

    with open(VALIDATION_LOG, 'a') as f:
        f.write(json.dumps(log_entry) + '\n')


def query_glean_interactive(prompt: str) -> str:
    """Interactive mode: display prompt and get user to paste Glean response."""
    print("\n" + "="*70)
    print("GLEAN QUERY PROMPT:")
    print("="*70)
    print(prompt)
    print("="*70)
    print("\nPaste the Glean response below (end with a line containing only 'END'):")

    lines = []
    while True:
        try:
            line = input()
            if line.strip() == 'END':
                break
            lines.append(line)
        except EOFError:
            break

    return '\n'.join(lines)


def query_glean_batch(prompt: str, test_id: str, output_dir: Path) -> str:
    """Batch mode: save prompt to file for external processing."""
    prompt_file = output_dir / f"{test_id}_prompt.txt"
    response_file = output_dir / f"{test_id}_response.txt"

    with open(prompt_file, 'w') as f:
        f.write(prompt)

    print(f"  Prompt saved to: {prompt_file}")

    # Check if response file exists (from previous run)
    if response_file.exists():
        with open(response_file, 'r') as f:
            return f.read()

    return ""


def process_yaml_file(filepath: Path, args) -> Dict[str, int]:
    """Process a single YAML file and validate its test cases."""
    print(f"\nProcessing: {filepath.name}")

    data = load_yaml_file(filepath)
    tests = get_all_test_cases(data, args.priority)

    stats = {"total": 0, "validated": 0, "skipped": 0, "pending": 0}

    for test in tests:
        test_id = test.get('id', 'Unknown')
        stats["total"] += 1

        if not needs_validation(test, args.force):
            if args.verbose:
                print(f"  [{test_id}] Already validated, skipping")
            stats["skipped"] += 1
            continue

        if args.test_id and test_id != args.test_id:
            continue

        print(f"  [{test_id}] {test.get('title', '')[:50]}...")

        if args.dry_run:
            print(f"    -> Would validate (dry-run)")
            stats["pending"] += 1
            continue

        # Build and execute query
        prompt = build_glean_prompt(test)

        if args.batch:
            batch_dir = Path(args.batch_dir)
            batch_dir.mkdir(parents=True, exist_ok=True)
            response = query_glean_batch(prompt, test_id, batch_dir)
            if not response:
                stats["pending"] += 1
                continue
        else:
            response = query_glean_interactive(prompt)

        if not response.strip():
            print(f"    -> No response, skipping")
            stats["pending"] += 1
            continue

        # Parse response and update test
        result = parse_glean_response(response)
        update_test_validation(test, result, response)
        log_validation(test_id, str(filepath), prompt, response, result)

        print(f"    -> Status: {result.get('status', 'unknown')}")
        stats["validated"] += 1

    # Save updated YAML
    if stats["validated"] > 0 and not args.dry_run:
        save_yaml_file(filepath, data)
        print(f"  Saved {stats['validated']} updates to {filepath.name}")

    return stats



def main():
    parser = argparse.ArgumentParser(
        description='Validate PCIe test cases using Glean',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run - see what would be validated
  python scripts/validate_with_glean.py --dry-run --priority P0

  # Interactive mode - validate one file
  python scripts/validate_with_glean.py --file data/seeds/01_physical_layer.yaml

  # Validate a specific test
  python scripts/validate_with_glean.py --test-id PHY-001

  # Batch mode - generate prompts for external processing
  python scripts/validate_with_glean.py --batch --batch-dir /tmp/glean_prompts

  # Force re-validation of all tests
  python scripts/validate_with_glean.py --force --priority P0
        """
    )

    parser.add_argument('--file', type=Path, help='Specific YAML file to process')
    parser.add_argument('--all', action='store_true', help='Process all YAML files in data/seeds')
    parser.add_argument('--test-id', type=str, help='Validate specific test ID only')
    parser.add_argument('--priority', type=str, choices=['P0', 'P1', 'P2', 'P3'],
                        help='Filter by priority level')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be validated')
    parser.add_argument('--force', action='store_true', help='Re-validate already validated tests')
    parser.add_argument('--batch', action='store_true',
                        help='Batch mode: save prompts to files for external processing')
    parser.add_argument('--batch-dir', type=str, default='/tmp/glean_validation',
                        help='Directory for batch mode files')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--status', action='store_true',
                        help='Show validation status summary only')

    args = parser.parse_args()

    # Determine which files to process
    if args.file:
        files = [args.file]
    elif args.all or args.status:
        files = sorted(SEED_DIR.glob('*.yaml'))
    else:
        parser.print_help()
        print("\nError: Specify --file, --all, or --status")
        sys.exit(1)

    if args.status:
        print_status_summary(files, args.priority)
        return

    # Process files
    total_stats = {"total": 0, "validated": 0, "skipped": 0, "pending": 0}

    for filepath in files:
        if not filepath.exists():
            print(f"File not found: {filepath}")
            continue

        stats = process_yaml_file(filepath, args)
        for k in total_stats:
            total_stats[k] += stats[k]

    # Print summary
    print("\n" + "="*50)
    print("VALIDATION SUMMARY")
    print("="*50)
    print(f"Total tests:     {total_stats['total']}")
    print(f"Validated:       {total_stats['validated']}")
    print(f"Skipped:         {total_stats['skipped']}")
    print(f"Pending:         {total_stats['pending']}")


def print_status_summary(files: List[Path], priority_filter: Optional[str]):
    """Print validation status summary for all files."""
    print("\n" + "="*70)
    print("VALIDATION STATUS SUMMARY")
    print("="*70)

    total_tests = 0
    total_validated = 0
    total_glean_validated = 0

    for filepath in files:
        data = load_yaml_file(filepath)
        tests = get_all_test_cases(data, priority_filter)

        validated = 0
        glean_validated = 0
        statuses = {"valid": 0, "corrected": 0, "needs_review": 0, "none": 0}

        for test in tests:
            val = test.get('validation', {})
            if val:
                validated += 1
                status = val.get('status', 'none')
                statuses[status] = statuses.get(status, 0) + 1
                if val.get('glean_validated'):
                    glean_validated += 1
            else:
                statuses['none'] += 1

        total_tests += len(tests)
        total_validated += validated
        total_glean_validated += glean_validated

        priority_str = f"[{priority_filter}]" if priority_filter else ""
        glean_pct = f"{100*glean_validated/len(tests):.0f}%" if tests else "N/A"

        print(f"\n{filepath.name} {priority_str}")
        print(f"  Tests: {len(tests)} | Validated: {validated} | Glean-verified: {glean_validated} ({glean_pct})")
        print(f"  Status: ✓{statuses['valid']} valid | ⚠{statuses['corrected']} corrected | ?{statuses['needs_review']} review | ○{statuses['none']} none")

    print("\n" + "-"*70)
    glean_pct = f"{100*total_glean_validated/total_tests:.0f}%" if total_tests else "N/A"
    print(f"TOTAL: {total_tests} tests | {total_validated} validated | {total_glean_validated} Glean-verified ({glean_pct})")
    print("="*70)


if __name__ == '__main__':
    main()


# PCIe Test Validation Scripts

Scripts for validating PCIe test cases against the PCIe 5.0 Base Specification using Glean.

## Recommended: Auggie CLI + Glean MCP Workflow

The best way to validate tests is using Auggie CLI with Glean MCP enabled:

### `validate_single_test.py` - For Auggie + Glean MCP

```bash
# Check current status
python scripts/validate_single_test.py --status --priority P0

# Get next test to validate (outputs Glean prompt)
python scripts/validate_single_test.py --next --priority P0

# In Auggie CLI, query Glean with the prompt, then apply result:
python scripts/validate_single_test.py --apply --test-id PHY-001 --result '{"status":"valid"}'

# Reset state to start fresh
python scripts/validate_single_test.py --reset

# Get specific test
python scripts/validate_single_test.py --test-id PM-006
```

**Workflow:**
1. Run `--next` to get the next unvalidated test + Glean prompt
2. Auggie queries Glean MCP with the prompt
3. Run `--apply` with the JSON result
4. Repeat until all tests are validated

The script tracks state in `data/.validation_state.json` and marks tests with `glean_validated: true`.

---

## Alternative Scripts

### `validate_with_glean.py` - Interactive Validation

Manual/interactive validation workflow for when you want to control each Glean query.

```bash
# Show current validation status
python scripts/validate_with_glean.py --status --priority P0

# Dry run - see what would be validated
python scripts/validate_with_glean.py --dry-run --all --priority P0

# Interactive mode - prompts you to paste Glean responses
python scripts/validate_with_glean.py --file data/seeds/06_power_management.yaml

# Batch mode - generates prompt files for external processing
python scripts/validate_with_glean.py --batch --batch-dir /tmp/glean_prompts --all --priority P0
```

### `glean_validator.py` - Automated API Validation

Automated validation using the Glean API directly.

```bash
# Set your Glean API token
export GLEAN_API_TOKEN="your-api-token-here"

# Dry run
python scripts/glean_validator.py --dry-run --all --priority P0

# Validate a specific file
python scripts/glean_validator.py --file data/seeds/06_power_management.yaml --priority P0

# Validate all files with auto-apply corrections
python scripts/glean_validator.py --all --priority P0 --auto

# Force re-validation of already validated tests
python scripts/glean_validator.py --all --priority P0 --force
```

## Validation Status Tracking

Each test case gets a `validation` block:

```yaml
validation:
  status: valid|corrected|needs_review
  validated_at: "2026-03-13"
  glean_validated: true      # Set when validated via these scripts
  changes_made:
    - "Description of validation/changes"
```

**Key fields:**
- `status`: `valid` (no changes), `corrected` (fixes applied), `needs_review` (manual review needed)
- `glean_validated`: `true` only when actually validated through Glean (not manually marked)
- `changes_made`: Array of changes/notes from validation

## Validation Log

All validations are logged to `data/validation_log.jsonl` (JSONL format) with:
- Timestamp
- Test ID and file
- Glean prompt sent
- Glean response received
- Parsed result

## Workflow

1. **Check status**: `python scripts/validate_with_glean.py --status --priority P0`
2. **Run validation**: Use either interactive or API mode
3. **Review results**: Check YAML files for `status: corrected` or `status: needs_review`
4. **Manual fixes**: For `needs_review` tests, manually verify and update

## Notes

- The scripts add `glean_validated: true` to distinguish real Glean validation from manual marking
- Original values are preserved in `original_spec_ref` and `original_pass_criteria` before corrections
- Rate limiting (2s delay) is built into the API validator to avoid hitting Glean rate limits


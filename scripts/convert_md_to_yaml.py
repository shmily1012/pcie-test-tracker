#!/usr/bin/env python3
"""
Convert PCIe test plan markdown files to YAML seed format.

Usage:
    python3 convert_md_to_yaml.py <source_dir> <output_dir>

Source markdown files contain test items in tables under ## category / ### subcategory headings.
Output YAML files follow the seed format for pcie-test-tracker import.
"""

import os
import re
import sys
import yaml


# File metadata configuration
FILE_METADATA = {
    "pcie_test_plan.md": {
        "version": "4.0",
        "spec_source": "PCIe Base Spec 5.0",
        "target": "U.2 NVMe SSD, Gen4 + Gen5, x4",
    },
    "gen5_specific.md": {
        "version": "1.0",
        "spec_source": "PCIe Gen5 Specific",
        "target": "U.2 NVMe SSD, Gen5 32GT/s",
    },
    "ocp_cloud_ssd_compliance.md": {
        "version": "1.0",
        "spec_source": "OCP Cloud SSD v2.5",
        "target": "OCP Cloud SSD compliance",
    },
    "linux_kernel_tests.md": {
        "version": "1.0",
        "spec_source": "Linux Kernel",
        "target": "Linux kernel PCIe/NVMe subsystem",
    },
    "enterprise_dc_tests.md": {
        "version": "1.0",
        "spec_source": "Enterprise DC",
        "target": "Data center NVMe SSD validation",
    },
    "ltssm_deep_dive.md": {
        "version": "1.0",
        "spec_source": "LTSSM Deep Dive",
        "target": "LTSSM state machine validation",
    },
    "aspm_deep_dive.md": {
        "version": "1.0",
        "spec_source": "ASPM Deep Dive",
        "target": "ASPM L0s/L1/L1.2 validation",
    },
}

# Headings to skip (case-insensitive substring match)
SKIP_HEADINGS = [
    "summary",
    "notes",
    "how to use this document",
    "version history",
    "gap analysis",
    "coverage summary",
    "coverage rate",
    "top gaps",
    "phase 1",
    "phase 2",
    "phase 3",
    "phase 4",
    "phase 5",
    "phase 6",
    "ocp 2.6 delta",
    "key insights from kernel source",
    "common aspm issues",
    "aspm performance impact report",
    "margin analysis",
    "lane margining protocol commands",
    "linux lane margining tool",
    "gen5 performance expectations",
    "equalization phases detail",
    "reading aspm capabilities",
    "ltssm state diagram",
    "aspm states overview",
    "what happens",
    "total ltssm test items",
    "statistics",
]


def should_skip_heading(heading_text):
    """Check if a heading should be skipped based on its content."""
    lower = heading_text.lower().strip()
    for skip in SKIP_HEADINGS:
        if skip in lower:
            return True
    return False


def clean_heading(text):
    """Remove numbering prefixes like '1.', '1.1', '### ' from heading text."""
    # Remove markdown heading markers
    text = re.sub(r'^#+\s*', '', text)
    # Remove numbering like "1.", "1.1", "1.2.3"
    text = re.sub(r'^\d+(\.\d+)*\.?\s*', '', text)
    # Strip whitespace
    return text.strip()


def normalize_priority(val):
    """Normalize priority values to P0/P1/P2 format."""
    if not val:
        return None
    val = val.strip()
    if val in ("P0", "P1", "P2", "P3"):
        return val
    if val in ("0", "1", "2", "3"):
        return f"P{val}"
    return val


def parse_table_row(line):
    """Parse a markdown table row into cells, handling escaped pipes."""
    # Strip leading/trailing pipe and whitespace
    line = line.strip()
    if line.startswith('|'):
        line = line[1:]
    if line.endswith('|'):
        line = line[:-1]

    # Split on pipe, but not pipes inside backticks
    cells = []
    current = []
    in_backtick = False
    for ch in line:
        if ch == '`':
            in_backtick = not in_backtick
            current.append(ch)
        elif ch == '|' and not in_backtick:
            cells.append(''.join(current).strip())
            current = []
        else:
            current.append(ch)
    cells.append(''.join(current).strip())
    return cells


def is_separator_row(line):
    """Check if line is a table separator like |---|---|."""
    stripped = line.strip()
    if not stripped.startswith('|'):
        return False
    # Remove pipes and check if remaining is just dashes, colons, spaces
    content = stripped.replace('|', '').strip()
    return bool(content) and all(c in '-: ' for c in content)


def is_table_row(line):
    """Check if line looks like a table row."""
    stripped = line.strip()
    return stripped.startswith('|') and stripped.endswith('|') and stripped.count('|') >= 3


def map_columns(headers):
    """Map header names to standardized field names."""
    mapping = {}
    header_map = {
        'id': 'id',
        'test id': 'id',
        'test item': 'title',
        'title': 'title',
        'test': 'title',
        'description': 'description',
        'procedure': 'description',
        'how to verify': 'description',
        'priority': 'priority',
        'tool': 'tool',
        'spec ref': 'spec_ref',
        'spec reference': 'spec_ref',
        'source': 'spec_ref',
        'coverage': None,  # skip
        'status': None,  # skip
        'notes': 'notes',
        'ocp req': 'ocp_req',
        'pass/fail criteria': 'pass_criteria',
        'pass criteria': 'pass_criteria',
        'expected': 'pass_criteria',
        'validation': 'pass_criteria',
        'error type': 'description',  # for ocp error table
        'field': 'title',  # for ocp SMART table
        'byte offset': 'notes',
        'link speed': None,
        'link width': None,
        'tested behind': None,
        'link up': None,
        'io ok': None,
        'perf impact': None,
        'tested with': None,
        'hot-swap': None,
        'kernel/driver version': None,
        'enum ok': None,
        'pm ok': None,
        'connection': None,
        'pcie gen': None,
        'platform': 'title',
        'switch': 'title',
        'hba/backplane': 'title',
        'os': 'title',
        'gen': None,
    }

    for i, h in enumerate(headers):
        h_lower = h.strip().lower()
        if h_lower in header_map:
            field = header_map[h_lower]
            if field is not None:
                mapping[i] = field
        # For unknown headers, skip them
    return mapping


def extract_item_from_row(cells, col_mapping):
    """Extract a test item dict from table cells using column mapping."""
    item = {}
    for col_idx, field_name in col_mapping.items():
        if col_idx < len(cells):
            val = cells[col_idx].strip()
            # Remove coverage emoji
            if val in ('⬜', '🟡', '✅', ''):
                continue
            if field_name == 'priority':
                val = normalize_priority(val)
            if val:
                if field_name in item and item[field_name]:
                    # Append for duplicate field mappings (e.g., multiple description columns)
                    item[field_name] = item[field_name] + "; " + val
                else:
                    item[field_name] = val
    return item


def has_valid_id(item):
    """Check if item has a valid test ID (not empty, not a header artifact)."""
    test_id = item.get('id', '')
    if not test_id:
        return False
    # Must look like a test ID pattern: LETTERS-DIGITS or similar
    if re.match(r'^[A-Z][A-Z0-9-]+\d+[a-z]?$', test_id):
        return True
    # Also match patterns like "IOP-001", "OCP-PCI-001", etc.
    if re.match(r'^[A-Z]+-[A-Z]*-?\d+[a-z]?$', test_id):
        return True
    # Match LTSSM-D01 style
    if re.match(r'^[A-Z]+-[A-Z]\d+$', test_id):
        return True
    # Match LTSSM-L0-01, LTSSM-L0s01 style
    if re.match(r'^[A-Z]+-[A-Z0-9s]+-?\d+$', test_id):
        return True
    return False


def parse_markdown_file(filepath):
    """Parse a markdown file and return categories with test items."""
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    categories = []
    current_category = None
    current_subcategory = None
    in_code_block = False
    in_table = False
    table_headers = None
    col_mapping = None
    skip_section = False

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Track code blocks
        if stripped.startswith('```'):
            in_code_block = not in_code_block
            i += 1
            continue

        if in_code_block:
            i += 1
            continue

        # Handle headings
        if stripped.startswith('## ') and not stripped.startswith('### '):
            heading_text = clean_heading(stripped)
            in_table = False
            table_headers = None

            if should_skip_heading(heading_text):
                skip_section = True
                i += 1
                continue

            skip_section = False
            current_category = {
                'name': heading_text,
                'subcategories': [],
                '_items': [],  # items directly under category (no subcategory)
            }
            categories.append(current_category)
            current_subcategory = None
            i += 1
            continue

        if stripped.startswith('### '):
            heading_text = clean_heading(stripped)
            in_table = False
            table_headers = None

            if should_skip_heading(heading_text):
                skip_section = True
                i += 1
                continue

            skip_section = False
            if current_category is None:
                # Create a default category
                current_category = {
                    'name': 'General',
                    'subcategories': [],
                    '_items': [],
                }
                categories.append(current_category)

            current_subcategory = {
                'name': heading_text,
                'items': [],
            }
            current_category['subcategories'].append(current_subcategory)
            i += 1
            continue

        if skip_section:
            i += 1
            continue

        # Handle table rows
        if is_table_row(stripped):
            if is_separator_row(stripped):
                # This is the separator after headers - we already have headers
                i += 1
                continue

            cells = parse_table_row(stripped)

            if not in_table:
                # This is the header row
                table_headers = cells
                col_mapping = map_columns(cells)
                in_table = True
                i += 1
                continue

            if in_table and col_mapping:
                item = extract_item_from_row(cells, col_mapping)
                if has_valid_id(item):
                    # Build the final item dict
                    final_item = {}
                    final_item['id'] = item['id']

                    # Title: use 'title' field, fall back to first part of description
                    if 'title' in item:
                        final_item['title'] = item['title']
                    elif 'description' in item:
                        # Use description as title if no explicit title
                        desc = item['description']
                        if len(desc) > 80:
                            final_item['title'] = desc[:77] + '...'
                        else:
                            final_item['title'] = desc

                    if 'description' in item:
                        final_item['description'] = item['description']

                    if 'priority' in item and item['priority']:
                        final_item['priority'] = item['priority']

                    if 'tool' in item:
                        final_item['tool'] = item['tool']

                    if 'spec_ref' in item:
                        final_item['spec_ref'] = item['spec_ref']

                    if 'ocp_req' in item:
                        final_item['ocp_req'] = item['ocp_req']

                    if 'pass_criteria' in item:
                        final_item['pass_criteria'] = item['pass_criteria']

                    if 'notes' in item:
                        final_item['notes'] = item['notes']

                    # Add to current subcategory or category
                    if current_subcategory is not None:
                        current_subcategory['items'].append(final_item)
                    elif current_category is not None:
                        current_category['_items'].append(final_item)

            i += 1
            continue

        # Non-table line resets table state
        if stripped and not stripped.startswith('>') and not stripped.startswith('---'):
            in_table = False
            table_headers = None

        i += 1

    return categories


def build_yaml_structure(categories, metadata):
    """Build the final YAML structure from parsed categories."""
    yaml_categories = []

    for cat in categories:
        yaml_cat = {'name': cat['name']}

        subcats = []

        # Items directly under category (no subcategory)
        if cat.get('_items'):
            subcat = {
                'name': cat['name'],
                'items': cat['_items'],
            }
            subcats.append(subcat)

        # Named subcategories
        for sc in cat.get('subcategories', []):
            if sc['items']:
                subcats.append({
                    'name': sc['name'],
                    'items': sc['items'],
                })

        if subcats:
            yaml_cat['subcategories'] = subcats
            yaml_categories.append(yaml_cat)

    result = {
        'metadata': metadata,
        'categories': yaml_categories,
    }

    return result


def count_items(yaml_data):
    """Count total test items in the YAML structure."""
    total = 0
    for cat in yaml_data.get('categories', []):
        for subcat in cat.get('subcategories', []):
            total += len(subcat.get('items', []))
    return total


def represent_str(dumper, data):
    """Custom string representer to use block style for multiline strings."""
    if '\n' in data:
        return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
    if len(data) > 100 or ':' in data or '#' in data or '{' in data or '}' in data:
        return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='"')
    return dumper.represent_scalar('tag:yaml.org,2002:str', data)


class CustomDumper(yaml.SafeDumper):
    pass


CustomDumper.add_representer(str, represent_str)


def convert_file(source_path, output_dir, filename):
    """Convert a single markdown file to YAML."""
    if filename not in FILE_METADATA:
        print(f"  SKIP: {filename} (no metadata configured)")
        return 0

    metadata = FILE_METADATA[filename]
    categories = parse_markdown_file(source_path)

    yaml_data = build_yaml_structure(categories, metadata)
    item_count = count_items(yaml_data)

    # Output filename: replace .md with .yaml
    output_name = filename.replace('.md', '.yaml')
    output_path = os.path.join(output_dir, output_name)

    with open(output_path, 'w', encoding='utf-8') as f:
        yaml.dump(yaml_data, f, Dumper=CustomDumper,
                  default_flow_style=False, allow_unicode=True,
                  sort_keys=False, width=120)

    print(f"  {filename} -> {output_name}: {item_count} items")
    return item_count


def main():
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <source_dir> <output_dir>")
        sys.exit(1)

    source_dir = sys.argv[1]
    output_dir = sys.argv[2]

    if not os.path.isdir(source_dir):
        print(f"Error: source directory not found: {source_dir}")
        sys.exit(1)

    os.makedirs(output_dir, exist_ok=True)

    print(f"Converting markdown test plans to YAML seeds")
    print(f"  Source: {source_dir}")
    print(f"  Output: {output_dir}")
    print()

    total_items = 0
    file_counts = {}

    for filename in sorted(FILE_METADATA.keys()):
        source_path = os.path.join(source_dir, filename)
        if not os.path.isfile(source_path):
            print(f"  WARNING: {filename} not found in source directory")
            continue
        count = convert_file(source_path, output_dir, filename)
        file_counts[filename] = count
        total_items += count

    print()
    print(f"Total: {total_items} test items across {len(file_counts)} files")
    print()
    print("Item counts per file:")
    for fn, count in sorted(file_counts.items()):
        print(f"  {fn}: {count}")


if __name__ == '__main__':
    main()

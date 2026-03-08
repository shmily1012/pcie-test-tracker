"""Parse markdown test plan tables and import into DB."""
import re
from typing import List

def parse_markdown_tables(content: str, spec_source: str = None) -> List[dict]:
    results = []
    current_category = "Uncategorized"
    lines = content.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Track category from headings
        m = re.match(r'^#{1,3}\s+(?:\d+[\.\)]\s*)?(.+)', line)
        if m:
            heading = m.group(1).strip()
            if len(heading) > 2 and heading not in ('Summary', 'Notes'):
                current_category = heading
        
        # Detect table: header line with |, followed by separator with ----
        if '|' in line and not line.replace('|','').replace('-','').replace(' ','') == '':
            # Check if next line is separator
            if i + 1 < len(lines) and re.match(r'^[\s|:-]+$', lines[i+1].replace('-','X') if '-' not in lines[i+1] else lines[i+1]):
                sep = lines[i+1].strip()
                if '---' in sep or '----' in sep:
                    headers = [h.strip() for h in line.strip('| ').split('|')]
                    headers = [h.strip() for h in headers if h.strip()]
                    col_map = detect_columns(headers)
                    if col_map.get('id') is not None:
                        i += 2  # skip header + separator
                        while i < len(lines):
                            row = lines[i].strip()
                            if not row or not row.startswith('|'):
                                break
                            cells = [c.strip() for c in row.strip('| ').split('|')]
                            cells = [c.strip() for c in cells if True]  # keep all including empty
                            # Re-parse properly
                            cells = parse_table_row(row)
                            if cells and len(cells) >= 2:
                                tc = parse_row(cells, col_map, current_category, spec_source)
                                if tc and tc.get('id') and not tc['id'].startswith('---'):
                                    results.append(tc)
                            i += 1
                        continue
        i += 1
    return results

def parse_table_row(line: str) -> list:
    """Parse a markdown table row properly."""
    line = line.strip()
    if line.startswith('|'):
        line = line[1:]
    if line.endswith('|'):
        line = line[:-1]
    return [c.strip() for c in line.split('|')]

def detect_columns(headers: List[str]) -> dict:
    col_map = {}
    for i, h in enumerate(headers):
        hl = h.lower().strip()
        if hl in ('id', 'test id'):
            col_map['id'] = i
        elif hl in ('test item', 'title'):
            col_map['title'] = i
        elif hl in ('description',):
            col_map['description'] = i
        elif hl in ('priority',):
            col_map['priority'] = i
        elif hl in ('tool', 'tools'):
            col_map['tool'] = i
        elif hl in ('spec ref', 'spec reference'):
            col_map['spec_ref'] = i
        elif hl in ('coverage', 'status'):
            col_map['coverage'] = i
        elif hl in ('pass/fail criteria',):
            col_map['pass_fail_criteria'] = i
        elif hl in ('ocp req',):
            col_map['ocp_req_id'] = i
    return col_map

def parse_row(cells: list, col_map: dict, category: str, spec_source: str = None) -> dict:
    def get(key):
        idx = col_map.get(key)
        if idx is not None and idx < len(cells):
            v = cells[idx].strip()
            return v if v else None
        return None
    
    tc_id = get('id')
    if not tc_id or '---' in tc_id:
        return None
    
    title = get('title') or ""
    desc = get('description') or title
    if not title and desc:
        title = desc[:100]
    if title and not desc:
        desc = title
    
    priority = get('priority') or 'P1'
    if not priority.startswith('P'):
        priority = f"P{priority}"
    
    coverage = get('coverage') or ''
    status = 'not_started'
    if '✅' in coverage:
        status = 'pass'
    
    return {
        'id': tc_id,
        'title': title,
        'description': desc,
        'category': category,
        'priority': priority,
        'spec_source': spec_source,
        'spec_ref': get('spec_ref'),
        'ocp_req_id': get('ocp_req_id'),
        'tool': get('tool'),
        'pass_fail_criteria': get('pass_fail_criteria'),
        'status': status,
    }

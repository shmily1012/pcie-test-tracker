# ⚡ PCIe Test Tracker

Web-based test plan management for PCIe NVMe SSD validation teams.

![Tech](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white)
![Tech](https://img.shields.io/badge/React-61DAFB?style=flat&logo=react&logoColor=black)
![Tech](https://img.shields.io/badge/SQLite-003B57?style=flat&logo=sqlite&logoColor=white)
![Tech](https://img.shields.io/badge/Docker-2496ED?style=flat&logo=docker&logoColor=white)

## Features

- 📊 **Dashboard** — Coverage donut chart, priority distribution, category × priority heatmap
- 📋 **Test Case Browser** — TanStack Table with multi-column sort, filter by category/priority/status/spec, full-text search
- ✅ **Execution Tracking** — Record pass/fail/blocked/skip per test, with environment, FW version, notes
- 💬 **Comments** — Threaded discussion per test case
- 📥 **Markdown Import** — Drop in existing `.md` test plans, auto-parsed into DB
- 📥 **YAML Seed Import** — Bulk-load structured test definitions from `data/seeds/`
- 📤 **CSV Export** — One-click export for Excel users
- 📤 **Markdown Export** — Export test cases back to markdown format
- 🔍 **Audit Log** — Who changed what, when
- 🌙 **Dark Theme** — Professional slate-900 UI, optimized for desktop

## Quick Start

### Option A: Docker (Recommended)

```bash
docker compose up --build
```

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API docs: http://localhost:8000/docs

### Option B: Local Development

**Prerequisites:** Python 3.11+, Node.js 18+

```bash
# 1. Clone
git clone <repo-url> && cd pcie-test-tracker

# 2. Backend
pip install -r backend/requirements.txt
mkdir -p data/db
DATABASE_URL="sqlite:///./data/db/pcie_tracker.db" \
  uvicorn backend.app.main:app --port 8100 &

# 3. Frontend
cd frontend
npm install
npm run dev
# → http://localhost:3000 (proxies /api → localhost:8100)
```

### Seed Database from YAML

The recommended way to populate the database is from the curated YAML test definitions in `data/seeds/`:

```bash
# Seed all YAML files (734 test items across 7 files)
python -m backend.app.seed --seeds-dir data/seeds

# Reset database and re-seed from scratch
python -m backend.app.seed --seeds-dir data/seeds --reset
```

### Import Test Data

**Via UI:** Go to Import page → upload `.md` file → set spec source → click Import

**Via CLI (Markdown):**
```bash
curl -X POST http://localhost:8100/api/import/markdown \
  -F "file=@your_test_plan.md" \
  -F "spec_source=PCIe Base 5.0"
```

**Via CLI (YAML):**
```bash
curl -X POST http://localhost:8100/api/import/yaml \
  -F "file=@data/seeds/pcie_test_plan.yaml"
```

**Via Python:**
```python
from backend.app.services.importer import parse_markdown_tables
cases = parse_markdown_tables(open("test_plan.md").read(), "PCIe Base 5.0")
# Returns list of dicts ready for DB insert
```

Supported markdown table formats:
```markdown
| ID | Test Item | Description | Priority | Tool | Spec Ref | Coverage |
| Test ID | OCP Req | Description | Priority | Tool | Pass/Fail Criteria | Coverage |
```

## Project Structure

```
pcie-test-tracker/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app + CORS
│   │   ├── models.py            # SQLAlchemy models (4 tables)
│   │   ├── schemas.py           # Pydantic request/response schemas
│   │   ├── database.py          # SQLite connection (WAL mode)
│   │   ├── seed.py              # YAML seed loader CLI
│   │   ├── routers/
│   │   │   ├── test_cases.py    # CRUD + bulk status update
│   │   │   ├── executions.py    # Test execution records
│   │   │   ├── comments.py      # Per-test-case comments
│   │   │   ├── dashboard.py     # Summary, coverage, heatmap
│   │   │   ├── import_export.py # MD/YAML import, CSV/MD export
│   │   │   └── audit.py         # Change audit log
│   │   └── services/
│   │       └── importer.py      # Markdown + YAML parsers
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                    # React + Vite SPA
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx    # Stats cards + charts
│   │   │   ├── TestCases.tsx    # TanStack Table + filters
│   │   │   ├── TestCaseDetail.tsx # Detail + executions + comments
│   │   │   ├── Reports.tsx      # Coverage table + CSV export
│   │   │   ├── Import.tsx       # File upload import
│   │   │   └── Audit.tsx        # Audit log viewer
│   │   ├── components/
│   │   │   ├── Layout.tsx       # Sidebar navigation
│   │   │   └── StatusBadge.tsx  # Status/priority pill badges
│   │   └── lib/
│   │       └── api.ts           # Typed API client (axios)
│   ├── Dockerfile
│   └── nginx.conf               # Production proxy config
├── data/
│   ├── seeds/                   # YAML test definitions (734 items)
│   │   ├── pcie_test_plan.yaml
│   │   ├── ocp_cloud_ssd_compliance.yaml
│   │   ├── gen5_specific.yaml
│   │   ├── enterprise_dc_tests.yaml
│   │   ├── aspm_deep_dive.yaml
│   │   ├── ltssm_deep_dive.yaml
│   │   └── linux_kernel_tests.yaml
│   └── db/                      # SQLite database (gitignored)
├── knowledge/
│   ├── guides/                  # 6 operational how-to guides
│   ├── references/              # 7 reference docs (specs, correlations)
│   └── templates/               # 3 checklists and prioritization templates
├── spec/                        # Source specs (PCIe 5.0, NVMe 2.3, OCP v2.5)
├── scripts/
│   ├── pcie_full_audit.sh       # Comprehensive audit runner
│   └── convert_md_to_yaml.py    # Migrate markdown test plans to YAML
├── docker-compose.yml
├── backup.sh                    # SQLite backup (cron-able, 30-day retention)
└── SPEC.md                      # Full build specification
```

## API Reference

All endpoints documented at `/docs` (Swagger UI) when backend is running.

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/test-cases` | List with filters (?category=&priority=&status=&search=) |
| GET | `/api/test-cases/{id}` | Detail with counts |
| PUT | `/api/test-cases/{id}` | Update test case |
| PATCH | `/api/test-cases/{id}/status` | Quick status update |
| PATCH | `/api/test-cases/bulk-status` | Bulk status update |
| POST | `/api/test-cases/{id}/executions` | Record test execution |
| POST | `/api/test-cases/{id}/comments` | Add comment |
| GET | `/api/dashboard/summary` | Total counts, pass rate, P0 coverage |
| GET | `/api/dashboard/coverage` | Per-category coverage breakdown |
| GET | `/api/dashboard/heatmap` | Category × Priority matrix |
| POST | `/api/import/markdown` | Import markdown test plan |
| POST | `/api/import/yaml` | Import YAML test definitions |
| GET | `/api/export/csv` | Export all test cases as CSV |
| GET | `/api/export/markdown` | Export all test cases as markdown |
| GET | `/api/audit` | Audit log with filters |

## Database

SQLite with WAL mode (concurrent reads). 4 tables:

- **test_cases** — ID, title, description, category, priority, spec_ref, status, owner, tags
- **executions** — Per-test execution records (status, environment, FW version, notes)
- **comments** — Per-test discussion thread
- **audit_log** — All mutations logged (entity, action, old/new values, timestamp)

### Backup

```bash
./backup.sh              # Manual backup
crontab -e               # Add: 0 2 * * * /path/to/backup.sh
```

Keeps timestamped copies for 30 days.

## Current Data

734 test items defined across 7 YAML seed files. After seeding, the database contains:

| Source File | Items | Description |
|-------------|------:|-------------|
| `pcie_test_plan.yaml` | 404 | PCIe Base Spec 5.0 core tests |
| `ocp_cloud_ssd_compliance.yaml` | 122 | OCP Cloud SSD v2.5 requirements |
| `gen5_specific.yaml` | 27 | PCIe Gen5-specific signal/equalization |
| `enterprise_dc_tests.yaml` | 36 | Enterprise data center scenarios |
| `aspm_deep_dive.yaml` | 38 | ASPM L0s/L1/L1.x power management |
| `ltssm_deep_dive.yaml` | 44 | Link Training & Status State Machine |
| `linux_kernel_tests.yaml` | 63 | Linux kernel quirks, AER, DPC, NVMe driver |

## Knowledge Base

The `knowledge/` directory contains operational guides and reference material for PCIe/NVMe validation engineers.

**Guides** (`knowledge/guides/`) — hands-on procedures:
- `debug_playbook.md` — Systematic debug workflow for common PCIe failures
- `error_injection_guide.md` — AER/correctable/uncorrectable error injection
- `fio_recipes.md` — fio workload recipes for NVMe performance testing
- `power_measurement.md` — ASPM/power state measurement procedures
- `test_procedures.md` — Step-by-step execution procedures
- `thermal_testing.md` — Thermal throttling and DPTC test methods

**References** (`knowledge/references/`) — lookup material:
- `common_failures.md` — Known failure signatures and root causes
- `nvme_pcie_correlation.md` — NVMe ↔ PCIe error correlation matrix
- `register_quick_ref.md` — PCIe config/capability register quick reference
- `spec_corrections.md` — Spec errata and clarifications
- `spec_cross_reference.md` — Cross-spec requirement mapping
- `u2_signal_integrity.md` — U.2 connector signal integrity notes
- `workload_matrix.md` — Workload ↔ test coverage matrix

**Templates** (`knowledge/templates/`) — checklists and planning:
- `checklists.md` — Pre-test and post-test checklists
- `compliance_checklist.md` — Full compliance verification checklist
- `prioritization_guide.md` — Test prioritization decision framework

## Roadmap

- [ ] Okta OIDC authentication (designed for, not yet implemented)
- [ ] Role-based permissions (architect=edit, engineer=execute, manager=view)
- [ ] Spec Tracker page (chapter ↔ test case mapping, gap visualization)
- [ ] Coverage trend over time (weekly snapshots)
- [ ] Excel export (multi-sheet workbook)
- [ ] PCIe Gen6 test cases
- [ ] OCP Cloud SSD v2.6 delta

## License

Internal use only.

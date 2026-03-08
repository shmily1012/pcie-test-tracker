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
- 📤 **CSV Export** — One-click export for Excel users
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

### Import Test Data

**Via UI:** Go to Import page → upload `.md` file → set spec source → click Import

**Via CLI:**
```bash
curl -X POST http://localhost:8100/api/import/markdown \
  -F "file=@your_test_plan.md" \
  -F "spec_source=PCIe Base 5.0"
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
│   │   ├── routers/
│   │   │   ├── test_cases.py    # CRUD + bulk status update
│   │   │   ├── executions.py    # Test execution records
│   │   │   ├── comments.py      # Per-test-case comments
│   │   │   ├── dashboard.py     # Summary, coverage, heatmap
│   │   │   ├── import_export.py # MD import, CSV export
│   │   │   └── audit.py         # Change audit log
│   │   └── services/
│   │       └── importer.py      # Markdown table parser
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
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
├── docker-compose.yml
├── backup.sh                    # SQLite backup (cron-able, 30-day retention)
├── data/db/                     # SQLite database (gitignored)
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
| GET | `/api/export/csv` | Export all test cases as CSV |
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

Pre-loaded with 553 test cases from:

| Source | Items | P0 | P1 | P2 |
|--------|------:|---:|---:|---:|
| PCIe Base Spec 5.0 | 404 | 189 | 152 | 63 |
| OCP Cloud SSD v2.5 | 122 | 93 | 29 | 0 |
| PCIe Gen5 Specific | 27 | 6 | 21 | 0 |
| **Total** | **553** | **288** | **202** | **63** |

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

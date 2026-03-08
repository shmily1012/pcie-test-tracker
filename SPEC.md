# PCIe Test Tracker — Build Specification

## Overview
Build a full-stack web application for managing PCIe NVMe SSD validation test plans.
This is an internal tool for a 30+ person validation team at a software company.

## Tech Stack
- **Backend:** Python 3.11+, FastAPI, SQLite (via SQLAlchemy), Pydantic
- **Frontend:** React 18+, Vite, TypeScript, shadcn/ui, Tailwind CSS, Recharts, TanStack Table
- **Deployment:** Docker + docker-compose (single command docker compose up)

## Project Structure
pcie-test-tracker/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI app, CORS, lifespan
│   │   ├── models.py        # SQLAlchemy models
│   │   ├── schemas.py       # Pydantic schemas
│   │   ├── database.py      # DB connection, session
│   │   ├── routers/
│   │   │   ├── test_cases.py
│   │   │   ├── executions.py
│   │   │   ├── comments.py
│   │   │   ├── dashboard.py
│   │   │   ├── import_export.py
│   │   │   └── audit.py
│   │   ├── services/
│   │   │   ├── importer.py
│   │   │   └── exporter.py
│   │   └── backup.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx
│   │   │   ├── TestCases.tsx
│   │   │   ├── TestCaseDetail.tsx
│   │   │   ├── Execution.tsx
│   │   │   ├── Reports.tsx
│   │   │   └── SpecTracker.tsx
│   │   ├── components/
│   │   │   ├── Layout.tsx
│   │   │   ├── CoverageChart.tsx
│   │   │   ├── PriorityBar.tsx
│   │   │   ├── CategoryHeatmap.tsx
│   │   │   ├── TestCaseTable.tsx
│   │   │   ├── FilterPanel.tsx
│   │   │   ├── CommentThread.tsx
│   │   │   └── StatusBadge.tsx
│   │   ├── lib/api.ts
│   │   └── hooks/useTestCases.ts
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   └── Dockerfile
├── docker-compose.yml
├── .env.example
├── backup.sh
└── data/db/

## Database Schema

### test_cases
- id TEXT PRIMARY KEY (e.g. "ERR-033", "OCP-PCI-001")
- title TEXT NOT NULL
- description TEXT NOT NULL
- category TEXT NOT NULL (e.g. "Error Handling", "DLL", "OCP-PCIe")
- subcategory TEXT
- priority TEXT NOT NULL (P0, P1, P2)
- spec_source TEXT ("PCIe Base 5.0", "OCP Cloud SSD 2.5")
- spec_ref TEXT ("§6.2.10 p.526")
- ocp_req_id TEXT ("PCI-15", "TTHROTTLE-5")
- tool TEXT ("LeCroy + Linux", "nvme-cli")
- pass_fail_criteria TEXT
- tags TEXT (JSON array: ["U.2", "Gen5", "OCP"])
- status TEXT DEFAULT 'not_started' (not_started, pass, fail, blocked, skip)
- owner TEXT
- notes TEXT
- created_at, updated_at TIMESTAMP

### executions
- id INTEGER PRIMARY KEY AUTOINCREMENT
- test_case_id TEXT FK → test_cases
- status TEXT (pass, fail, blocked, skip)
- executed_by TEXT
- executed_at TIMESTAMP
- environment TEXT (e.g. "Gen4 x4, Intel Sapphire Rapids")
- firmware_version TEXT
- notes TEXT
- attachments TEXT (JSON array)

### comments
- id INTEGER PRIMARY KEY AUTOINCREMENT
- test_case_id TEXT FK → test_cases
- author TEXT NOT NULL
- content TEXT NOT NULL
- created_at TIMESTAMP

### audit_log
- id INTEGER PRIMARY KEY AUTOINCREMENT
- entity_type TEXT ("test_case", "execution")
- entity_id TEXT
- action TEXT ("create", "update", "delete")
- changed_by TEXT
- old_value TEXT (JSON)
- new_value TEXT (JSON)
- changed_at TIMESTAMP

## API Endpoints

### Test Cases
- GET /api/test-cases (filters: category, priority, status, spec_source, tag, search)
- GET /api/test-cases/{id}
- POST /api/test-cases
- PUT /api/test-cases/{id}
- DELETE /api/test-cases/{id}
- PATCH /api/test-cases/{id}/status
- PATCH /api/test-cases/bulk-status

### Executions
- POST /api/test-cases/{id}/executions
- GET /api/test-cases/{id}/executions

### Comments
- POST /api/test-cases/{id}/comments
- GET /api/test-cases/{id}/comments

### Dashboard
- GET /api/dashboard/summary
- GET /api/dashboard/coverage
- GET /api/dashboard/trend
- GET /api/dashboard/heatmap

### Import/Export
- POST /api/import/markdown (upload MD → parse → upsert)
- GET /api/export/csv
- GET /api/export/excel

### Audit
- GET /api/audit (filters)

## Frontend Pages

### 1. Dashboard
- 4 stat cards: Total Tests, Pass Rate %, P0 Coverage %, Blocked Count
- Coverage donut chart (Recharts)
- Priority distribution stacked bar
- Category heatmap (rows=categories, cols=P0/P1/P2, colored by coverage %)
- Weekly coverage trend line

### 2. Test Cases (TanStack Table)
- Columns: ID, Title, Category, Priority, Spec Ref, Status, Owner
- Filter sidebar with checkboxes
- Search bar
- Inline status dropdown
- Row click → detail page
- Bulk select + bulk status update

### 3. Test Case Detail
- Header with status/priority badges
- Tabs: Details | Executions (timeline) | Comments (threaded)
- Edit inline

### 4. Reports
- Export CSV/Excel buttons
- Coverage summary
- Print-friendly

### 5. Spec Tracker
- Tree: spec chapters left, linked test cases right
- Red highlight for uncovered chapters

## UI Design
- Dark theme default
- Background: slate-900/950, Cards: slate-800
- Accent: blue-500 primary, green-500 pass, red-500 fail, yellow-500 blocked, gray-500 skip
- Status badges: colored pills
- Sidebar navigation with icons, collapsible
- 1920px+ optimized (no mobile needed)

## Markdown Import
Parse tables like:
| ID | Test Item | Description | Priority | Tool | Spec Ref | Coverage |
Also OCP format:
| Test ID | OCP Req | Description | Priority | Tool | Pass/Fail Criteria | Coverage |

Importer should:
1. Auto-detect format
2. Map columns to DB fields
3. Extract category from ## headings
4. Extract spec_source from filename/heading
5. Upsert by ID

## Docker
- docker-compose.yml: backend:8000, frontend:3000 (nginx)
- Volume for SQLite + backups
- .env.example

## Data Safety
- backup.sh: timestamped copies, keep 30 days
- Audit log on all mutations
- SQLite WAL mode

## Future Auth Design
- FastAPI current_user dependency (returns dummy now, Okta OIDC later)
- Frontend AuthProvider (dummy user)
- All mutations accept changed_by/author/executed_by

## Build Priority
1. Backend API + DB + import
2. Dashboard + Test Cases table
3. Detail + Executions
4. Comments + Audit
5. Export
6. Docker
7. Spec Tracker

Build everything end-to-end. Real functionality, no mock data. Polished UI.

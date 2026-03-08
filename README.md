# PCIe Test Tracker

Internal web application for managing PCIe NVMe SSD validation test plans.

## Tech Stack
- **Backend:** FastAPI (Python) + SQLite
- **Frontend:** React + Vite + shadcn/ui + Tailwind CSS + Recharts + TanStack Table
- **Deployment:** Docker + docker-compose

## Features
- Dashboard with coverage charts (donut, bar, heatmap)
- Full test case browser with multi-dimensional filtering
- Execution tracking (pass/fail/blocked/skip + notes + date + owner)
- Audit log (who changed what, when)
- Comment/discussion per test case
- Export to CSV/Excel
- Spec chapter ↔ test case mapping visualization
- Data import from existing Markdown test plans

## Architecture
- Auth: None currently; designed for future Okta OIDC integration
- DB: SQLite with automated daily backups
- API: RESTful, auto-documented via FastAPI /docs

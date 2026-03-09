# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

PCIe Test Tracker — a web app for managing PCIe NVMe SSD validation test plans. Python/FastAPI backend with SQLite, React/Vite frontend with TailwindCSS v4.

## Quick Start (Local Development)

**Prerequisites:** Python 3.11+, Node.js 20+ (Vite 7 + TailwindCSS v4 不支持 Node 18)

如果系统 Node 版本低于 20，用 `n` 安装到用户目录：
```bash
N_PREFIX=$HOME/.n npx -y n 20
# 之后启动前端时需加 PATH="$HOME/.n/bin:$PATH"
```

### 1. 启动后端
```bash
pip install -r backend/requirements.txt
mkdir -p data/db
DATABASE_URL="sqlite:///./data/db/pcie_tracker.db" \
  uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

### 2. 启动前端
```bash
cd frontend
PATH="$HOME/.n/bin:$PATH" npm install   # 若系统 Node >= 20 可省略 PATH 前缀
PATH="$HOME/.n/bin:$PATH" npm run dev   # Dev server on :3000, proxies /api -> localhost:8000
```
其他前端命令：`npm run build`（tsc + vite build）、`npm run lint`（eslint）

### 3. LAN 访问
后端和前端均绑定 `0.0.0.0`（vite.config.ts 已配置 `host: '0.0.0.0'`，后端启动时加 `--host 0.0.0.0`）。
局域网内用 `http://<本机IP>:3000` 访问前端，`http://<本机IP>:8000/docs` 查看 API 文档。

### Docker 方式（需 docker 权限）
```bash
docker compose up --build   # Backend :8000, Frontend :3000
```

### Seed Database
```bash
python -m backend.app.seed --seeds-dir data/seeds          # Seed from YAML files
python -m backend.app.seed --seeds-dir data/seeds --reset   # Reset and re-seed
```
后端启动时若数据库为空且 `data/seeds/` 存在，会自动 seed。

## Architecture

**Backend** (`backend/app/`): FastAPI app, single-process, SQLite with WAL mode.
- `main.py` — App setup, CORS (allow all), lifespan auto-seed, SPA static file serving from `frontend/dist/`
- `models.py` — SQLAlchemy models: `TestCase`, `Execution`, `Comment`, `AuditLog` (4 tables)
- `schemas.py` — Pydantic request/response schemas
- `database.py` — SQLite engine with WAL + foreign keys enabled via pragmas. `DATABASE_URL` env var.
- `seed.py` — CLI to bulk-load YAML test definitions from `data/seeds/`
- `routers/` — One router per domain: `test_cases`, `executions`, `comments`, `dashboard`, `import_export`, `audit`
- `services/importer.py` — Markdown table parser and YAML parser for test plan import

**Frontend** (`frontend/`): React 19 + Vite 7 SPA, TailwindCSS v4 (uses `@tailwindcss/vite` plugin, not PostCSS).
- `src/pages/` — Route pages: Dashboard, TestCases, TestCaseDetail, Reports, Import, Audit
- `src/lib/api.ts` — Typed axios client for all API calls
- `src/components/Layout.tsx` — Sidebar nav wrapper
- Routing via react-router-dom v6
- Charts via recharts, tables via @tanstack/react-table

**Data flow**: All API routes are under `/api`. Vite dev server proxies `/api` to the backend. In production, FastAPI serves the built SPA from `frontend/dist/`.

**Database**: SQLite file at `data/db/pcie_tracker.db` (gitignored). The `test_cases.id` is a string (e.g., "TC-001"), not auto-increment. Tags and attachments are stored as JSON-encoded text columns.

## Key Patterns

- All mutations are logged to `audit_log` table with old/new values
- Test case status values: `not_started`, `pass`, `fail`, `blocked`, `skip`
- Priority values: `P0`, `P1`, `P2`, `P3`
- YAML seed files in `data/seeds/` are the canonical source for test definitions (734 items across 7 files)
- No authentication yet (designed for Okta OIDC, not implemented)

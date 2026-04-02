---
description: "Use when editing Supabase SQL migrations, pgvector/vector search functions, `.env`, MCP configuration, or Python DB helper scripts in this repo. Enforces secret safety, valid mcp.json schema, and repo conventions for SQL/database work."
name: "Supabase MCP and SQL Conventions"
applyTo:
  - "sql/**"
  - "scripts/**"
  - "mcp_server.py"
  - ".vscode/mcp.json"
  - "core/database.py"
  - "db_main.py"
---
# Supabase MCP and SQL Conventions

- Keep secrets out of tracked files.
  - Never commit real API tokens, database passwords, or service-role keys.
  - Use `.env` for local secrets and placeholders in committed examples.
  - Treat `.env` as local-only even if referenced in docs or scripts.

- Keep `mcp.json` schema-valid.
  - Do **not** add unsupported properties such as `allowedModels` to `.vscode/mcp.json`.
  - Restrict models in server code or environment variables instead.
  - Prefer a minimal MCP server definition with only supported keys like `type` and `url`.

- Put database changes in SQL files under `sql/`.
  - Create or update migration-style SQL files instead of hiding schema changes inside Python code.
  - Prefer explicit, reviewable SQL for functions, RLS, policies, extensions, and vector indexes.
  - When adding a new DB helper script, make it load `DATABASE_URL` from `.env` instead of hardcoding credentials.

- Follow Supabase pgvector patterns.
  - Prefer the pgvector SQL column type from the Supabase `extensions` schema for vector columns, e.g. `ALTER TABLE ... ADD COLUMN embedding extensions.vector(1536);` when targeting Supabase.
  - Keep `match_documents`-style functions compatible with Supabase RPC usage.
  - Match vector dimensions to the embedding model actually used in the app.
  - If using RAG with permissions, prefer RLS policies over ad-hoc filtering in application code.

- Be careful with remote execution.
  - Do not run remote DDL, destructive SQL, or production-affecting commands without explicit user confirmation.
  - If remote execution fails because of DNS, network, or permissions, stop and provide a safe manual fallback.

- Prefer small helper scripts for DB operations.
  - Python scripts in `scripts/` should be single-purpose, readable, and safe to rerun.
  - Print clear success/error messages for connection and SQL execution steps.

## Examples

- Good: create `sql/create_match_documents.sql` and call it from `scripts/exec_sql.py`.
- Good: keep `SUPABASE_URL`, `SUPABASE_API_URL`, `DATABASE_URL`, and model restrictions in `.env`.
- Avoid: putting model restrictions in `.vscode/mcp.json`.
- Avoid: committing live secrets or embedding passwords directly in tracked Python files.

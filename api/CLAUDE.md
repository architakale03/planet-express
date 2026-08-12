# api/ — FastAPI + PostgreSQL backend

## Working directory

Everything runs with `api/` as cwd — `pyproject.toml`, `app/`, and `alembic.ini` live
here. `uv run pytest`, `uv run alembic`, `uv run uvicorn` work directly; the Makefile
gets here via `uv --directory api`. From the repo root you get `ModuleNotFoundError: app`.

No linter or formatter is configured. Do not add one uninvited.

## Rules

- **Sync SQLAlchemy, never async.** FastAPI runs sync handlers in a threadpool, so the
  event loop is never blocked. No `async def` handlers that touch a `Session` — mixing
  the two produces greenlet errors.
- **Alembic only, never `create_all()`.** `create_all()` creates missing tables but never
  alters existing ones, so the first column change silently desyncs model from database.
- **`/health` must never touch the database.** `/health/db` is the one that queries. The
  split distinguishes "app down" from "database down" and is what the container
  healthcheck relies on.
- **One session per request via `Depends(get_db)`.** Never construct `SessionLocal()`
  inside a handler. It is correct in a standalone script, which has no request to scope to.

## Config precedence

`app/config.py` reads `env_file=("../.env", ".env")`. cwd is always `api/`, so `../.env`
is the repo-root file — the same one Compose reads. Later entries win, so an optional
`api/.env` overrides it locally. **Real environment variables outrank both.** Compose
injects `DATABASE_URL` pointing at the `db` service, beating the `localhost` URL in
`.env`; inside the container neither file path exists anyway, since only `api/` is
mounted. `migrations/env.py` mirrors the order: `os.environ["DATABASE_URL"]` first,
then `get_settings()`.
`alembic.ini` deliberately omits `sqlalchemy.url`.

## Migrations

Autogenerate diffs `Base.metadata`, so it sees **tables, columns, and indexes only**.
Views, functions, triggers, and grants need an empty revision with hand-written
`op.execute(...)`. Declare models in `app/models.py` — `migrations/env.py` imports that
module, so anything defined there registers on `Base.metadata`. A model declared in some
other module must be imported in `env.py` too, or autogenerate never sees it.

`versions/0001_initial.py` is an empty base revision: there are no domain tables yet. It
is kept rather than deleted so a database already stamped `0001` still resolves head.

Use the `add-migration` skill rather than improvising the sequence.

## Tests

`pytest` runs against **real Postgres** — no mocks; the wiring is what's under test.
`tests/conftest.py` provides a session-scoped `TestClient`.

- Tests need a live database: `make test` (container) or `make local-test` (host).
- They mutate the database you develop against. A test that writes must delete what it
  created in a `finally`, so a failing assertion still cleans up.
- `test_db_health_reaches_postgres` asserts `postgres_version.startswith("16")`. It is
  version-sensitive by design; do not loosen it to make an upgrade pass silently.

## Dependencies

`uv.lock` is the source of truth and the image builds with `uv sync --frozen`. Editing
`pyproject.toml` without `make sync` and committing the lockfile fails the build — by
design.

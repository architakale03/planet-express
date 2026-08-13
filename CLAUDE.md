# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Stack

FastAPI backend, PostgreSQL 16 — two services, one `docker-compose.yml`. There is no
frontend. There are no domain tables either: `0001` is an empty base revision and
`app/models.py` declares no models. The first feature adds both, via the `add-migration`
skill.

`api/` holds the service. `docker-compose.yml`, `Makefile`, and `.env` live at the root —
`.env` beside the compose file it configures, so Compose auto-reads it.

## Guidance lives next to the code

`api/CLAUDE.md` holds the backend-specific rules and loads automatically when you work in
that directory. Do not restate them here.

| Path | What |
| --- | --- |
| `feature-list.json` | Scope. Sessions work a feature from here |
| `docs/plans/` | Approved plans, one file per plan |
| `claude-progress.md` | Rolling handoff. Overwritten each session |
| `docs/sessions/` | One immutable file per session |
| `docs/decisions.md` | Append-only *why*. Supersede entries, never edit |
| `docs/references/` | Pinned upstream `llms.txt` snapshots — currently empty |
| `.claude/skills/add-migration/` | Schema-change procedure — use instead of improvising alembic |
| `.claude/commands/verify-stack.md` | `/verify-stack` |

## Planning

1. Once a plan is approved, write it to `docs/plans/YYYY-MM-DD-<slug>.md`. The approved
   plan is a file on disk, not just conversation history.
2. Then break that plan down into features and update `feature-list.json` — one entry per
   feature, `status: todo`.
3. Do not start implementing every feature at once. Work one feature at a time, carrying
   it all the way to `done` before picking up the next.

## Working a feature

1. Pick one from `feature-list.json`, set `status` to `in_progress`.
2. Implement it.
3. Write the acceptance checks: pytest node ids relative to `api/`, and/or shell
   commands that must exit 0.
4. `make features` must pass.
5. Only then set `status` to `done`.
6. At session end, overwrite `claude-progress.md` and write
   `docs/sessions/YYYY-MM-DD-<slug>.md`. Durable *why* goes to `docs/decisions.md`.

`status` is a claim; `make features` is the auditor:

- `done` with no acceptance checks is a violation, not a pass.
- A pytest node id that does not exist is a failure, never a skip.
- Nothing is cached or written back — truth is recomputed on every run.
- The script exits 1 on violation; `make features` exits 2 because make wraps a failing
  recipe. `make features-all` also checks `todo`/`in_progress` features.

Never mark `done` by editing the JSON alone, and never weaken a check to make the audit
pass. Claims in `claude-progress.md` and `docs/sessions/` must name the command that
proved them — never carry a result forward because "nothing changed".

## Commands

Unprefixed targets drive Compose; `local-*` drive host-native tooling.
`make help` lists everything.

```bash
make up          # build + start db, api; migrations run in the api start command
make verify      # /health, /health/db, psql database + revision check
make test        # pytest inside the api container
make features    # audit feature-list.json claims
make down        # stop (volume preserved);  make fresh = down -v + rebuild
make logs / ps / psql / shell / migrate
make revision m="add users table"
```

Host-native: `make dev`, `make local-test`, `make local-migrate`, `make local-revision`,
`make local-psql`, `make local-verify`, `make local-fresh`, `make sync`.

**`.env` is auto-read by Compose**, since it sits beside `docker-compose.yml`. No
`--env-file` anywhere: a bare `docker compose` behaves exactly like the Makefile. Still
use `$(COMPOSE)` when adding a target, so the invocation stays in one place. Every
variable also defaults to its `.env.example` value, so a fresh clone with no `.env`
comes up fine.

No linter or formatter is configured. Do not invent a lint step.

## Ports

8080 is the API on the host, mapping to uvicorn on **8000 inside** its container — only
the host side moved, so the Dockerfile, `EXPOSE`, and the healthcheck still say 8000.
5432 is Postgres.

Only one path (Docker or host Postgres) can own 5432/8080 at a time, and the two
databases hold different data. `GET /health/db` reports which you reached — container
`"16.14"`, Homebrew `"16.14 (Homebrew)"`.

`api` means two unrelated things; do not conflate them when editing:

| Role | Where |
| --- | --- |
| Directory | compose `context: ./api`, `uv --directory api` |
| Compose service / DNS name | `docker compose exec api`, `depends_on`, `http://api:8000` |

## Request path

client → uvicorn on 8080 → `api/app/main.py` → `app/routers/*.py` →
`Depends(get_db)` → `app/models.py`, with `app/schemas.py` for request/response.

## Stack mechanisms

- **Bind mount plus a place for dependencies the mount cannot shadow.** The api service
  mounts source over `/app`, so the image sets `UV_PROJECT_ENVIRONMENT=/usr/local` to
  keep the virtualenv outside the mount. Skip it and the container has no dependencies.
- **Lockfile-frozen installs** — `uv sync --frozen`. Editing `pyproject.toml` without
  committing the regenerated `uv.lock` fails the build, by design.
- **`depends_on: service_healthy`** on api→db, gated on `pg_isready`; plain `depends_on`
  races Postgres on a cold boot.
- **Tests hit real Postgres**, no mocks, and mutate the database you develop against.

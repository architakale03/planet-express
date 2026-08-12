# Planet Express — FastAPI + PostgreSQL, containerized

A backend service and a database, each in its own container, wired together by a single
Docker Compose file.

## Stack

| Piece | Choice | Why |
| --- | --- | --- |
| API | FastAPI (Python 3.12) | Typed request/response models, OpenAPI docs for free at `/docs` |
| DB | PostgreSQL 16 | Relational data, real constraints, easy to extend |
| ORM | SQLAlchemy 2.0 (sync) + psycopg3 | Modern typed mapping style |
| Migrations | Alembic | Schema changes are versioned, not hand-applied |
| Dependencies | uv + `uv.lock` | Fully pinned; the image builds from the same lockfile the host uses |
| Orchestration | Docker Compose | One command to bring the whole thing up |

## Quick start

Needs a container runtime — Docker Desktop, OrbStack, or Colima.

```bash
make up            # build and start db, api
make verify        # prove the whole path works, end to end
```

Then open <http://localhost:8080/docs> for the API.

`make up` returns as soon as Compose does, which is before anything serves a request.
Both containers have healthchecks, so give them a moment — `make ps` shows `(healthy)`
once they are actually answering. Run `make verify` after that, not immediately.

```bash
make ps            # container status; both should read (healthy)
make logs          # tail both services
make down          # stop everything, data volume preserved
```

`make help` lists every target.

Copying `.env.example` to `.env` is optional for the Docker path — Compose falls
back to the same defaults when the file is absent. Copy it when you want to change a
port or run the host-native targets (`make dev`, `make local-test`).

### Ports

| Port | Owner | Notes |
| --- | --- | --- |
| 8080 | API | The one you open. Host side only — uvicorn still listens on 8000 *inside* its container |
| 5432 | Postgres | Exposed so you can attach TablePlus/DBeaver/psql |

There is no browser client in this repo, so no CORS middleware is configured. Add one if
a browser app is ever served from a different origin.

### Running Compose directly

`make up` is a thin wrapper. Plain Compose works too:

```bash
docker compose up -d --build
```

`.env` sits beside `docker-compose.yml`, so Compose reads it automatically — no flags,
and identical behaviour to the `make` targets. Every variable also carries a default
matching `.env.example`, so this works on a fresh clone with no env file at all.

Containers are detached and `restart: unless-stopped`, so they survive a closed terminal
and come back when the Docker daemon restarts. Stop them with `make down` (the data
volume is preserved).

## Proving the connection works

`make verify` hits liveness and readiness, then queries Postgres directly via `psql` to
confirm it is the same database the API reached and that migrations are applied. Both
ends confirm the round trip rather than assuming it.

The single most useful endpoint is `GET /health/db`:

```json
{ "status": "ok", "postgres_version": "16.14", "database": "planet_express" }
```

It runs real queries against Postgres, so a 200 here means the connection is live.
`GET /health` deliberately does *not* touch the database — that split lets you tell
"the app is down" apart from "the database is down".

## Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health` | Liveness (no DB) |
| GET | `/health/db` | Readiness — proves Postgres connectivity |

There are no domain endpoints yet: the stack ships with an empty schema, and the first
feature adds its own router under `api/app/routers/`.

## Running without Docker

Optional, and only a convenience — the containerized path above is the deliverable.
A host-native loop avoids image rebuilds while iterating.

One-time setup:

```bash
brew install uv postgresql@16
brew services start postgresql@16
export PATH="/opt/homebrew/opt/postgresql@16/bin:$PATH"   # keg-only formula
createuser -s postgres && createdb -O postgres planet_express
make local-migrate
```

Then:

```bash
make dev            # uv sync, then uvicorn with --reload
make local-verify   # same end-to-end proof, against the host database
```

Or drive `uv` directly from `api/`, where `pyproject.toml` and `app/` live. `--port` is
passed explicitly so the host matches the published container port; uvicorn's own default
is 8000:

```bash
cd api
uv run uvicorn app.main:app --port 8080 --reload
uv run pytest -v
uv run alembic upgrade head
```

`local-` targets operate on the host Postgres; unprefixed ones drive Compose. Both read
the same `.env` and the same `uv.lock`.

**Only one path can own ports 5432 and 8080 at a time**, and the two databases
hold different data. Switch with `make down && brew services start postgresql@16`, or
set `POSTGRES_PORT=5433` in `.env` to run both at once — Compose already reads that
variable. `GET /health/db` tells you which you reached: the container reports
`"16.14"`, Homebrew reports `"16.14 (Homebrew)"`.

## Layout

The files that describe the stack as a whole live at the root; everything the service
itself needs lives in `api/`.

```
planet-express/
├── docker-compose.yml     # the only compose file: db + api
├── Makefile               # up / verify / test / migrate / psql, plus local-*
├── .env                   # dev credentials + ports (gitignored)
├── .env.example           # copy this to .env
└── api/                   # backend
    ├── Dockerfile         # python:3.12-slim, non-root, uv sync --frozen
    ├── pyproject.toml     # dependencies (+ uv.lock — the single source of truth)
    ├── alembic.ini
    ├── app/
    │   ├── main.py        # app factory + router registration
    │   ├── config.py      # pydantic-settings, env-driven
    │   ├── db.py          # engine, session, Base, get_db dependency
    │   ├── models.py      # SQLAlchemy models (empty — no domain tables yet)
    │   ├── schemas.py     # Pydantic request/response models
    │   └── routers/       # health.py
    ├── migrations/        # Alembic; versions/0001_initial.py is an empty base
    └── tests/             # pytest against the real database
```

One `.env` configures everything: Compose interpolates it into both service definitions,
and the backend reads the same file for the host-native path.

## Changing the schema

```bash
# edit api/app/models.py, then:
make revision m="add users table"      # diffs the ORM against the live DB
# review the generated file, then:
make migrate
make fresh                             # replays every migration on an empty volume
```

**Autogenerate sees tables, columns, and indexes only.** Views, functions, triggers, and
grants are not in `Base.metadata`, so create those revisions empty and hand-write
`op.execute(...)` in both `upgrade` and `downgrade`. `make fresh` is the real check that
a migration works on a clean database and not just on yours.

Full procedure and the traps: `.claude/skills/add-migration/SKILL.md`.

## Why it's built this way

Every non-obvious choice — sync SQLAlchemy over async, Alembic over `create_all()`, the
`/health` split, where `.env` lives — belongs in
**[`docs/decisions.md`](docs/decisions.md)**, recorded with its rejected alternative.
That file is append-only, so it stays accurate. It is currently empty.

## Extending it

- New table: edit `api/app/models.py`, then `make revision m="..."` and `make migrate`.
- New endpoint: add a router in `api/app/routers/`, include it in `main.py`.
- Iterating: the api container bind-mounts `api/`, so only dependency changes need
  `make up` again.
- Loading a dataset: `docker compose cp <file> api:/app/`, then a short script that builds
  its own `SessionLocal` — correct in a script, never inside a handler.

Working on this repo with Claude Code: scope lives in `feature-list.json`, conventions in
`CLAUDE.md`, and the handoff for the next session in `claude-progress.md`.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `Cannot connect to the Docker daemon` | The runtime isn't running — launch Docker Desktop / OrbStack |
| `Connection refused` on 5432 or 8080 | Nothing is running — `make up`, then `make ps` until both read `(healthy)` |
| Port 5432 already in use | Local Postgres owns it: `brew services stop postgresql@16`, or set `POSTGRES_PORT=5433` in `.env` |
| Port 8080 already in use | A local `make dev` server is running — stop it, or change `API_PORT` in `.env` |
| Edits to `.env` seem ignored | Compose reads `.env` at container *create* time — `make down && make up`, not `make restart` |
| Build fails on `uv sync --frozen` | `uv.lock` is stale — run `make sync` and commit the result |
| `ModuleNotFoundError: app` | Run from `api/`, or use the Makefile targets, which pass `uv --directory api` |
| Schema looks stale | `make fresh` (destroys the volume and rebuilds) |
| Everything gone after reboot | The container runtime doesn't auto-start; open it and `unless-stopped` restores both containers |

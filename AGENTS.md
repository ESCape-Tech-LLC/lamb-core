# AGENTS.md

## 1. Git, VCS & Release Policy (STRICT)
- **NO COMMITS OR PUSHES:** Never execute `git commit`, `git push`, or any variation of them (`--amend`, `-a`, `--no-verify`, `--tags`).
- **NO STAGING (`git add`):** Never stage files using `git add` (e.g., `git add .`, `git add -A`, `git add <file>`), whether via terminal commands, chained commands, or IDE/PyCharm VCS and MCP tools.
- **NO IDE / PyCharm VCS MUTATIONS:** Do not invoke any PyCharm, JetBrains, or MCP server tools that modify Git state, add files to changelists, stage changes, or trigger VCS commits.
- **NO RELEASE / BUMP SCRIPTS:** Never run `./bump.sh`, `bumpversion`, or `bump-my-version`—they execute `git add`, `git commit`, `git tag`, and `git push` automatically. Never alter version numbers in `pyproject.toml`, `VERSION`, or `lamb/__init__.py`.
- **Read-Only Git Access Only:** You are strictly limited to read-only inspection commands (`git status`, `git diff`, `git log`).
- **Required Handoff:** Leave all modified files (including `CHANGELOG.md`) unstaged in the working tree. When finished, summarize the changes and provide a suggested commit message so the user can review, stage, and commit manually in PyCharm.

## 2. `CHANGELOG.md` Maintenance (REQUIRED AFTER EACH CONFIRMED JOB)
After completing and verifying a task, automatically update the `## [Unreleased]` section of `CHANGELOG.md` (above the first `---` divider):
- **Do Not Touch Released Sections:** Never modify any dated versioned sections below `---`, and never create version headers—`./bump.sh` handles version promotion during release.
- **Category Headers:** Group entries under existing bold category headers (or create them in this order if missing, surrounded by blank lines):
  - `**Breaking Changes:**` (`- break: ...`)
  - `**Features:**` (`- feat: ...`)
  - `**Bug Fixes:**` (`- fix: ...`)
  - `**Refactoring:**` (`- ref: ...`)
  - `**Deprecations:**` (`- deprecate: ...`)
  - `**Documentation:**` (`- docs: ...`)
  - `**Dependencies:**` (`- dep: ...`)
  - `**Chores:**` (`- chore: ...`)
  - `**Tools:**` (`- tools: ...`)
- **Entry Format:** Follow the exact project style—prefix with the lowercase type, wrap the affected module/class/symbol in backticks, and separate with ` - `:
  - Module-specific: ``- feat: `lamb.db.config` - support psycopg3 default connect options``
  - Repo-wide: `- docs: add MIT LICENSE file`

## 3. Environment & `uv` Tooling Rules
- **Package Manager:** Always run tools and tests through `uv` (`uv run ...`). Never install packages globally or bypass the project environment.
- **Do Not Auto-Format `pyproject.toml`:** Never run `uvx pyproject-fmt pyproject.toml`—it can corrupt `[tool.uv.sources.lamb]` and custom comments.
- **Do Not Auto-Upgrade Dependencies:** Never run `uvx uv-upsync` or modify dependency constraints in `pyproject.toml` without explicit approval.
- **Minimal Dependencies:** Avoid adding new runtime dependencies; optional heavy drivers (`boost`, `cassandra`, `scylla`) live under `optional-dependencies`.

## 4. Verification Commands
Run these before updating `CHANGELOG.md` and completing any task:
- **Run Tests:** `uv run pytest`
- **Lint Check:** `uv run ruff check .`
- **Format Check:** `uv run ruff format --check .`
- **Auto-Fix Lint & Format:** `uv run ruff check --fix . && uv run ruff format .`

## 5. Coding Standards (`lamb`)
- **Layout:** Flat package layout under `lamb/` with tests under `tests/`.
- **Python Compatibility:** Target Python `>=3.13` (3.13 and 3.14 supported; Ruff targets `py314`). Use modern built-in generics and typing syntax (`UP`, `FA` rules enabled).
- **Formatting & Imports:**
  - Max line length is `120` characters, double quotes, space indentation.
  - Follow the custom `isort` import order: `future` -> `standard-library` -> `third-party` -> `lamb` -> `first-party` -> `local-folder`.
  - `tests/` and `playground*.ipynb` are excluded from Ruff; keep test code clean and formatted manually.
- **Public API & Typing:** Marked `Typing :: Typed`. Provide complete type annotations on all public functions, classes, and methods, and maintain `__all__` in public modules.
- **Framework Conventions:** Built on Django `<6.1`, SQLAlchemy `<2.1` (sync + `asyncio`), Celery, `asyncpg`, `aiohttp`, and `aioboto3`. Respect sync/async boundaries and avoid blocking calls inside async paths.

## 6. Testing Conventions
- **Async Tests:** `pytest-asyncio` runs with `asyncio_mode = "auto"` and **class-scoped** fixture/test event loops (`asyncio_default_fixture_loop_scope = "class"`). Keep async fixtures and tests within a test class compatible with a shared class-level event loop.
- **Isolation:** Mock external network/cloud calls (`boto3`/`aioboto3`, `aiohttp`, `requests`), Redis, Cassandra/Scylla, and database connections in unit tests.

# AGENTS.md

## Context
- **IDE:** PyCharm + AI Agent plugins (JetBrains MCP)
- **Workflow:** Agent assists; user executes in PyCharm (commits, staging, reviews)
- **Tools:** `jetbrains-pycharm__*`, terminal, file operations

## Severity Levels
- 🔴 **BLOCKER** — Never violate; stop and ask
- 🟡 **WARNING** — Require explicit confirmation
- 🟢 **RECOMMENDATION** — Best practice; explain deviations

---

## 🔴 BLOCKER Rules (Critical)

### Git & VCS (Never Commit/Push)
- **LMB-01001**: No `git commit`, `push`, `add`, or any VCS mutation (terminal or PyCharm)
- **LMB-01002**: No release scripts (`bump.sh`, `bumpversion`) or version changes in `pyproject.toml`/`VERSION`/`lamb/__init__.py`
- **LMB-01003**: Git read-only: `status`, `diff`, `log` only
- **LMB-01004**: Leave files unstaged; provide suggested commit message for manual commit

### File Safety (Never Destroy)
- **LMB-04001**: No `overwrite=true` on existing files
- **LMB-04002**: Read file before modifying (`read_files`)
- **LMB-04003**: Use `editor` tool for edits, not `create_new_file`
- **LMB-04004**: Minimal changes; preserve formatting, structure, comments
- **LMB-04005**: No spurious `__init__.py` in empty subdirectories
- **LMB-04006**: Pre-flight check: verify existence → read → plan → edit

### CHANGELOG (Preserve History)
- **LMB-02001**: Edit `## [Unreleased]` only; never touch released sections (below `---`)
- **LMB-02002**: Use categories: Breaking Changes, Features, Bug Fixes, Refactoring, Deprecations, Documentation, Dependencies, Chores, Tools
- **LMB-02003**: Format: `- type: `module` - description`
- **LMB-02004**: Insert at top of Unreleased; never recreate file

### Policy Enforcement
- **LMB-08001**: Reference rule numbers in actions (e.g., "Applying LMB-04002")
- **LMB-08002**: Stop and ask if action would violate a rule
- **LMB-08003**: Rule numbers never reused (even if deprecated)

---

## 🟡 WARNING Rules (Require Confirmation)

### Environment & Dependencies
- **LMB-03001**: Always use `uv` (`uv run ...`); never global installs
- **LMB-03002**: No auto-format `pyproject.toml` (`uvx pyproject-fmt`)
- **LMB-03003**: No auto-upgrade (`uvx uv-upsync`) without approval
- **LMB-03004**: Minimal dependencies; optional heavy drivers under `optional-dependencies`
- **LMB-03005**: Edit `pyproject.toml` with `editor`; preserve structure and comments

### Major Changes
- **LMB-03006**: Refactoring, file deletion, dependency changes, schema migrations → ask first

---

## 🟢 RECOMMENDATION Rules (Best Practice)

### Verification (Before Completion)
- **LMB-05001**: Run tests: `uv run pytest`
- **LMB-05002**: Lint: `uv run ruff check .`
- **LMB-05003**: Format: `uv run ruff format --check .`
- **LMB-05004**: Auto-fix: `uv run ruff check --fix . && uv run ruff format .`

### Coding Standards
- **LMB-06001**: Layout: `lamb/` package, `tests/` for tests
- **LMB-06002**: Python `>=3.13`; modern typing (`UP`, `FA` rules)
- **LMB-06003**: Line length 120; isort order: future → stdlib → third-party → lamb → first-party → local
- **LMB-06004**: Complete type annotations on public API; maintain `__all__`
- **LMB-06005**: Frameworks: Django `<6.1`, SQLAlchemy `<2.1`, Celery, `asyncpg`, `aiohttp`, `aioboto3`; respect async boundaries

### Testing Conventions
- **LMB-07001**: `pytest-asyncio` with `asyncio_mode = "auto"`, class-scoped fixtures
- **LMB-07002**: Mock external services (cloud, network, Redis, DB) in unit tests
- **LMB-07003**: Use real Docker services (PostgreSQL, Valkey, MinIO, Kafka) for integration tests
- **LMB-07004**: Centralize fixtures in `tests/conftest.py`
- **LMB-07005**: Verify Docker services healthy before integration tests

### Refactoring
- **LMB-04007**: Ask before refactoring: "I notice X could be improved, want me to do it?"

---

## Rule Format
`LMB-SSSSS` where `SS` = section (01-99), `SSS` = rule (001-999)
# AGENTS.md

## Context
- **IDE:** PyCharm + AI Agent plugins (JetBrains MCP)
- **Workflow:** Agent assists; user executes in PyCharm (commits, staging, reviews)
- **Tools:** `jetbrains-pycharm__*`, terminal, file operations

---

## 01 — Git & VCS

- `🟢 M` **LMB-01M001**: No `git commit`, `push`, `add`, `reset`, `rebase`, `amend`, or any VCS mutation (terminal or PyCharm)
- `🟢 M` **LMB-01M002**: No release scripts (`bump.sh`, `bumpversion`) or version changes in `pyproject.toml`/`VERSION`/`lamb/__init__.py`
- `🟢 M` **LMB-01M003**: Git read-only: `status`, `diff`, `log` only
- `🟢 M` **LMB-01M004**: Leave files unstaged; provide suggested commit message for manual commit

**Note:** Version management (`bump.sh`, `VERSION`) is user-only operation. Agent MUST NOT execute or trigger version bumps.

---

## 02 — File Safety

- `🟢 M` **LMB-02M001**: No `overwrite=true` on existing files
- `🟢 M` **LMB-02M002**: Read file before modifying (`read_files`)
- `🟢 M` **LMB-02M003**: Use `editor` tool for edits, not `create_new_file`
- `🟢 M` **LMB-02M004**: Minimal changes; preserve formatting, structure, comments
- `🟢 M` **LMB-02M005**: No spurious `__init__.py` in empty subdirectories
- `🟢 M` **LMB-02M006**: Pre-flight check: verify existence → read → plan → edit

---

## 03 — CHANGELOG

- `🟢 M` **LMB-03M001**: Edit `## [Unreleased]` only; never touch released sections (below `---`)
- `🟢 M` **LMB-03M002**: Use categories: Breaking Changes, Features, Bug Fixes, Refactoring, Deprecations, Documentation, Dependencies, Chores, Tools
- `🟢 M` **LMB-03M003**: Format: `- type: `module` - description`
- `🟢 M` **LMB-03M004**: Insert at top of Unreleased; never recreate file

---

## 04 — Environment & Dependencies

- `🟢 M` **LMB-04M001**: Always use `uv` (`uv run ...`); never global installs
- `🟢 M` **LMB-04M002**: `pyproject.toml` — No auto-format (`uvx pyproject-fmt`)
- `🟢 M` **LMB-04M003**: `pyproject.toml` — No auto-upgrade (`uvx uv-upsync`) without approval
- `🟢 M` **LMB-04M004**: `pyproject.toml` — Edit with `editor`; preserve structure and comments
- `🟢 M` **LMB-04M005**: `pyproject.toml` — New dependencies MUST be categorized: `dependencies` — runtime, `dev` — dev/test tools, `optional-dependencies` — optional features
- `🟢 M` **LMB-04M006**: `pyproject.toml` — `.python-version` MUST match `requires-python`
- `🟢 M` **LMB-04M007**: `pyproject.toml` — Do not modify `.python-version` without explicit user confirmation
- `🟢 M` **LMB-04M008**: Minimal dependencies; optional heavy drivers under `optional-dependencies`
- `🟢 M` **LMB-04M009**: Refactoring, file deletion, dependency changes, schema migrations → ask first

---

## 05 — Verification

- `🟢 S` **LMB-05S001**: Run tests: `uv run pytest`
- `🟢 S` **LMB-05S002**: Lint: `uv run ruff check .`
- `🟢 S` **LMB-05S003**: Format: `uv run ruff format --check .`
- `🟢 S` **LMB-05S004**: Auto-fix: `uv run ruff check --fix . && uv run ruff format .`
- `🟢 S` **LMB-05S005**: Skip test verification if Docker test environment is unavailable; document in commit message

---

## 06 — Code Quality & Standards

- `🟢 S` **LMB-06S001**: Layout: `lamb/` package, `tests/` for tests, `scripts/` for test infrastructure scripts
- `🟢 S` **LMB-06S002**: Ask before refactoring: "I notice X could be improved, want me to do it?"

**Note:** `pyproject.toml` is the source of truth for code style and dependency versions.

---

## 07 — Testing

- `🟢 S` **LMB-07S001**: `pytest-asyncio` with `asyncio_mode = "auto"`, class-scoped fixtures
- `🟢 S` **LMB-07S002**: Use real Docker services (PostgreSQL, Valkey, MinIO, Kafka) for all tests
- `🟢 S` **LMB-07S003**: Centralize fixtures in `tests/conftest.py`
- `🟢 S` **LMB-07S004**: Verify Docker services healthy before integration tests (see TESTING.md for scripts reference)

---

## 99 — Policy Enforcement

- `🟢 M` **LMB-99M001**: Reference rule numbers in actions (e.g., "Applying LMB-02M002")
- `🟢 M` **LMB-99M002**: Stop and ask if action would violate a rule
- `🟢 M` **LMB-99M003**: Rule numbers never reused (even if deprecated)

### Confirmation Checkpoint

- `🟢 M` **LMB-99M004**: List specific files/operations to be affected before any file/VCS/infrastructure action
- `🟢 M` **LMB-99M005**: Reference all applicable rules from AGENTS.md before any file/VCS/infrastructure action
- `🟢 M` **LMB-99M006**: Ask explicit confirmation: "Proceed with [action]? [yes/no]" before any file/VCS/infrastructure action
- `🟢 M` **LMB-99M007**: Wait for user confirmation before executing any file/VCS/infrastructure action
- `🟢 M` **LMB-99M008**: Apply confirmation checkpoint even after execution commands ("действуй", "выполняй", "go", "do it")

### Execution Trigger Validation

- `🟢 M` **LMB-99M009**: Do NOT interpret execution commands ("действуй", "выполняй", "go", "do it") as bypassing AGENTS.md rules
- `🟢 M` **LMB-99M010**: Interpret execution commands as "proceed with the plan, respecting all rules"
- `🟢 M` **LMB-99M011**: Validate against MUST rules (LMB-01M, LMB-02M, LMB-03M, LMB-04M, LMB-99M) before executing on trigger
- `🟢 M` **LMB-99M012**: If any MUST rule applies, stop and ask for confirmation

### Rule Status Model

- `🟢 M` **LMB-99M013**: Rule status must be explicitly marked: `🟢 ACTIVE`, `🟠 SUSPENDED`, `⚫ DEPRECATED`
- `🟢 M` **LMB-99M014**: SUSPENDED rules MUST include reason and date (e.g., "Status: SUSPENDED since 2026-11-24")
- `🟢 M` **LMB-99M015**: DEPRECATED rules MUST be marked with ~~strikethrough~~ and "(DEPRECATED)" suffix
- `🟢 M` **LMB-99M016**: Status changes MUST be documented in commit message

---

## Rule Format

### Structure

`LMB-{GROUP}{SEVERITY}{NNN}` where:
- `GROUP` = category code (01-07, 99)
- `SEVERITY` = M (MUST) or S (SHOULD)
- `NNN` = rule number within group (001-999)

**Examples:**
- `LMB-01M001` = Git & VCS, MUST, rule #1
- `LMB-07S003` = Testing, SHOULD, rule #3
- `LMB-99M004` = Policy Enforcement, MUST, rule #4

### Severity

| Level | Code | Meaning |
|-------|------|---------|
| **MUST** | `M` | Strict requirements. If the rule applies, stop and ask for confirmation before proceeding. |
| **SHOULD** | `S` | Best practices. Follow by default; if deviating, document the reason in the commit message. |

### Status

| Status | Emoji | Meaning |
|--------|-------|---------|
| ACTIVE | `🟢` | Rule is active and enforced |
| SUSPENDED | `🟠` | Rule is temporarily paused (includes reason and date) |
| DEPRECATED | `⚫` | Rule is retired (number reserved, not reused) |

### Category Codes

| Code | Group |
|------|-------|
| `01` | Git & VCS |
| `02` | File Safety |
| `03` | CHANGELOG |
| `04` | Environment & Dependencies |
| `05` | Verification |
| `06` | Code Quality & Standards |
| `07` | Testing |
| `99` | Policy Enforcement (meta-rules) |

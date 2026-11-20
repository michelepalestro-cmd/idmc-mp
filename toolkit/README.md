# toolkit

The Python side of the plugin. Standard library only, Python 3.10+. Every script answers `--help` without logging in,
and every write is a dry run until you pass `--execute --expect-org <orgIdV3>`.

| Folder or file | What it is |
|---|---|
| `check_login.py` | Connect once and print which org you are in (`--setup` asks for your login, `--where` shows the file) |
| [`lib/`](lib/README.md) | The library: login with a lockout guard, org proof, objects, export and import, package edits, mapping tasks, taskflows and schedules, runtime selections, CDC, CAI publish, catalog, guarded deletes, IPU metering, MCP, and the MCP bridge the plugin starts (`idmc_mcp_bridge.py`, set up with `/idmc-mp:connect-mcp`) |
| [`mapgen/`](mapgen/README.md) | The headless mapping generator: a JSON spec becomes an IDMC mapping and an importable package |
| [`demos/`](demos/README.md) | Four rebuildable demo blueprints, each with a `README.md` and a numbered `BUILD.md` ([conventions](demos/BLUEPRINT_CONVENTIONS.md)) |
| [`setup/`](setup/SETUP.md) | Setup for git clones and demos, the login template, `.env.example`, and an offline readiness check |
| `tests/` | `run_tests.py` (offline test suite, prints `ALL PASSED`), the MCP mock server and `USER_STORIES.md` |
| `tools/` | Repository tools: `secret_scan.py`, `sync_lesson_counts.py`, `build_skill_field_lessons.py`, and the pre-commit hook |

Your login lives in `~/.idmc_toolkit/IDMC_LOGIN.txt`, never in this folder. See the root [README](../README.md).

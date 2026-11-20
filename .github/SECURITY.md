# Security

## How this plugin handles your login

- Your IDMC user name and password live in one file, `~/.idmc_toolkit/IDMC_LOGIN.txt`, in your home folder. It is
  created readable only by you (mode 600) and is never inside the plugin folder, so updates and git never touch it.
- The plugin talks only to Informatica's own servers (`*.informaticacloud.com`) and to systems you connect on purpose
  (for example your warehouse in a demo). It has no telemetry and sends nothing anywhere else.
- It tries at most one login per run, checks your file on your computer before it tries, and pauses itself after a
  rejected login, so it cannot lock your account by retrying.
- Sessions are cached in `~/.idmc_session/` (readable only by you) and expire as IDMC sessions do.
- If you run `/idmc-mp:connect-mcp`, the MCP OAuth client's secret is written straight to
  `~/.idmc_toolkit/mcp_client.env` (mode 600) and never printed. The plugin's MCP bridge reads it, offers read-only
  tools unless you chose read and write, and Claude Code still asks before each tool call.
- Commands that change your org are dry runs until you add `--execute --expect-org <org id>`, and they refuse to run
  when the live session is in a different org.
- A pre-commit hook and CI run `toolkit/tools/secret_scan.py`, which blocks passwords, keys, IP addresses, e-mails and
  local paths from being committed.

## Automated security checks

Every push and pull request runs, with read-only permissions and actions pinned to commit SHAs:

| Check | What it enforces |
|---|---|
| CodeQL (`security-extended`, Python and GitHub Actions), also weekly | GitHub's code scanning |
| bandit | no Python finding of medium or high severity |
| detect-secrets | no secret that is not in the audited `.github/secrets.baseline` (it holds only reviewed false positives: field names in prose, environment-variable names, dummy test values) |
| `toolkit/tools/secret_scan.py` | no credential, org id, IP address, e-mail or local path |
| tests | the offline test suite, on Python 3.10 and 3.12 |

Dependabot keeps the pinned actions current. The plugin itself has no third-party Python dependencies. Where a scanner
rule is answered by a guard rather than a code change (for example XML parsing that refuses DTDs and entities, or SQL
text for `psql` built from escaped values), the line carries a `# nosec` / `# nosemgrep` annotation with the reason.

## Good habits

- Use a dedicated IDMC service user for Claude, with only the roles it needs, not your personal admin user.
- Never paste a password into a chat or an issue. If you did, change the password.
- Review any third-party IDMC tool before you run it: see
  [Using a community tool safely](../knowledge/11-mcp-claire/07-ecosystem-plugins-registries-community-tools.md#5-using-a-community-tool-safely).

## Reporting a vulnerability

Please do not open a public issue for a security problem. Use GitHub's private
[Report a vulnerability](https://github.com/michelepalestro-cmd/idmc-mp/security/advisories/new) form on this
repository. Include what you found, how to reproduce it, and what it could
expose. You will get an answer as soon as possible.

For problems in Informatica's own products, contact Informatica.

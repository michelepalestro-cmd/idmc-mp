# Security

## How this plugin handles your login

- Your IDMC user name and password live in one file, `~/.idmc_toolkit/IDMC_LOGIN.txt`, in your home folder. It is
  created readable only by you (mode 600) and is never inside the plugin folder, so updates and git never touch it.
- The plugin talks only to Informatica's own servers (`*.informaticacloud.com`) and to systems you connect on purpose
  (for example your warehouse in a demo). It has no telemetry and sends nothing anywhere else.
- It tries at most one login per run, checks your file on your computer before it tries, and pauses itself after a
  rejected login, so it cannot lock your account by retrying.
- Sessions are cached in `~/.idmc_session/` (readable only by you) and expire as IDMC sessions do.
- Commands that change your org are dry runs until you add `--execute --expect-org <org id>`, and they refuse to run
  when the live session is in a different org.
- A pre-commit hook and CI run `toolkit/tools/secret_scan.py`, which blocks passwords, keys, IP addresses, e-mails and
  local paths from being committed.

## Good habits

- Use a dedicated IDMC service user for Claude, with only the roles it needs, not your personal admin user.
- Never paste a password into a chat or an issue. If you did, change the password.
- Review any third-party IDMC tool before you run it: see
  [Using a community tool safely](knowledge/11-mcp-claire/07-ecosystem-plugins-registries-community-tools.md#5-using-a-community-tool-safely).

## Reporting a vulnerability

Please do not open a public issue for a security problem. Use GitHub's private
[Report a vulnerability](https://github.com/michelepalestro-cmd/idmc-mp/security/advisories/new) form on this
repository, or e-mail the maintainer at michelepalestro@gmail.com. Include what you found, how to reproduce it, and what it could
expose. You will get an answer as soon as possible.

For problems in Informatica's own products, contact Informatica.

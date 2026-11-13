# IDMC MP: Informatica IDMC, headless, for Claude Code

A Claude Code plugin that teaches Claude to build and run Informatica Intelligent Data Management Cloud (IDMC / IICS)
**without the UI**: REST and MCP calls for CDI, CAI, CDQ, CDGC, MDM, Mass Ingestion / CDC, Secure Agents, runtime
environments, connections, mappings, taskflows, profiling, data quality, catalog and IPU metering.

Inside: ~1,970 field lessons (error signature -> cause -> fix), a headless playbook, a Python script library with a
login lockout guard, a mapping generator, three rebuildable demo blueprints and an endpoint-level API and MCP reference.

## Install

In Claude Code:

```
/plugin marketplace add michelepalestro-cmd/idmc-mp
/plugin install idmc-mp@idmc-mp
```

Restart Claude Code. The skill loads on its own for IDMC work, or call it with `/idmc-mp:idmc-mp`.

## Connect to your IDMC org (once)

Python 3.10+. Ask Claude to "connect to my IDMC org", or run `check_login.py` from the plugin's `skills/idmc-mp/kb/`
folder yourself:

1. The first run creates `~/.idmc_toolkit/IDMC_LOGIN.txt` (in your home folder, outside the plugin).
2. Fill in `IDMC_USER` and `IDMC_PASS` of a **native** IDMC user (SSO-only users cannot call the API) and
   `IDMC_LOGIN_HOST` (the browser address after you sign in).
3. Run it again: it logs in once and prints your org and pod.

One file per org instead? Point `IDMC_CREDS_FILE` at it; its values win.

## Use it

Just ask: "build a mapping from my Postgres orders table to Snowflake", "why does this connection return
APP_10519", "profile this table and suggest DQ rules". Two rules hold throughout: Claude builds with the systems you
name (the KB's examples are not recommendations), and it works the workaround ladder in your org before ever
saying something is not possible.

## Update / remove

`/plugin update idmc-mp@idmc-mp` (your login in `~/.idmc_toolkit/` is untouched) - `/plugin uninstall idmc-mp@idmc-mp`.

## Notes

- Informatica's product documentation is **not** included; the skill points to https://docs.informatica.com for official wording.
- Demo blueprints in `skills/idmc-mp/kb/demos/` may need Docker and the accounts their README lists.
- Calls run against your org with your user's rights. Writes are dry runs until an org guard passes; jobs you run
  consume IPUs on your subscription.
- This is an independent community project, not an official Informatica product, and is not supported by
  Informatica. See [NOTICE](NOTICE).

## License

[MIT](LICENSE).

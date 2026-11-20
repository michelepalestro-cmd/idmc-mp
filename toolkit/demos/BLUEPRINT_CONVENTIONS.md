# Demo blueprint conventions

Every folder under `demos/` is a **blueprint**: everything a person (or a Claude session) with no prior context needs to
rebuild one demo in their own IDMC org, headless, from an empty org to a verified run.

A blueprint's systems (its database, warehouse, CRM, file store, BI tool) are what it was proven on, not a
recommendation. To build the same pattern on other systems, keep the stages and the gates, swap the connections and
the connector-specific settings, and follow `knowledge/00-start-here/08-new-pipeline-milestones-any-source-any-target.md`
for any connector the KB has not covered. A blueprint's "UI-only walls" are dated: work the workaround ladder in that
doc before treating one as final.

## Layout (every blueprint)

```
demos/<blueprint>/
  README.md             what the demo shows, the architecture (one diagram in text), which IDMC services it uses,
                        what is real vs a stand-in, how long a rebuild takes
  BUILD.md              the numbered rebuild: each step = why, one command, the expected output, how to verify, how to undo.
                        Ends with "Gotchas" (every hard-won fix) and "UI-only walls" (steps no API can do, click path given)
  config.example.json   every name, id and setting the scripts need. Copy to config.json and fill in;
                        ids that the build creates are written back to config.json (or state/ids.json) by the scripts
  requirements.txt      third-party Python packages, if any (prefer the standard library)
  infra/                stand-in source and target systems: docker-compose, schemas, seed data and traffic generators
  idmc/                 the IDMC build: connections, mappings / mapping tasks / taskflows / schedules, CAI processes and
                        connections, CDC (Database Ingestion) tasks, Data Quality rule specs + profiles, catalog (CDGC)
                        sources, glossary, lineage. Templates (JSON / XML / SQL) + the scripts that deploy them
  dashboards/           optional BI builder (e.g. Tableau REST publish) with a generic target in config
  verify/               smoke and end-to-end checks that prove the build works
  teardown/             undo / cleanup scripts, in reverse build order
```

## Rules

1. **Generic only.** No names of real companies, customers, people, apps, orgs, hosts, IP addresses, cloud projects,
   storage accounts, ticket keys, local paths or object ids. Use neutral object names with a short blueprint prefix
   (for example `rdf_`, `bid_`, `mbr_`) and put every environment value in `config.json` / `.env`.
2. **No secrets.** Credentials come only from the toolkit's `.env` (see `toolkit/setup/.env.example`) or the environment.
   Scripts print key names, never values.
3. **Use the core library.** Scripts import the Script Library, `toolkit/lib/` (`idmc_session`, `idmc_http`, `idmc_mttask`, `idmc_cai_publish`,
   `idmc_dbmi`, `idmc_cdgc`, `idmc_export_import`, ...). Locate it relative to the script:
   `sys.path.insert(0, str(Path(__file__).resolve().parents[N] / "knowledge/14-working-with-claude" / "Script Library"))`.
4. **Dry run by default.** Anything that changes an org prints the request and stops unless `--execute` is given;
   writes to an org also take `--expect-org <orgIdV3>` (the core library's guard).
5. **Integration logic lives in IDMC.** If CAI / CDI / CDQ can do a step, the runtime path uses IDMC, not Python.
   Python is for building, deploying, verifying and generating stand-in traffic only.
6. **Keep the know-how.** The exact request bodies, call order, parameters and quirks that made it work are the value of
   the blueprint. Each one goes in a template, a script or BUILD.md "Gotchas".
7. **Be honest.** Mark every step as PROVEN (worked end-to-end in a real org, in an earlier form) or ADAPTED (rewritten
   generically here, not yet re-run in this form). Name the UI-only walls.
8. **Python 3.10+, cross-platform** (Windows and Linux): no `fcntl`, no hard-coded `/home/...` paths.

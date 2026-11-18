# mapgen: headless mapping generator

Turns a mapping **spec** (JSON or a Python dict: sources, transformations, expressions, lookups, rule specs, targets,
field links) into a real IDMC Data Integration mapping and an importable v3 package. Python 3.10+, standard library
only. One module per transformation type under `idmc_mapgen/nodes/` (source, target, expression, filter, joiner, lookup, router,
aggregator, sorter, rank, dedup, normalizer, cleanse, masking, rule spec, SQL, mapplet, sequence, ...).

Background: `knowledge/03-cdi-data-integration/02 How Claude Builds Mappings Headless` and `05 The Pipeline-Generation
Pattern` (route 5 = this generator). PROVEN in a real org in 2026-09 (parity with hand-built mappings, then complex
scenarios); this copy differs only by generic comment wording and one renamed login-body variable. Synced 2026-10-26: Salesforce source `filter` / `sfObject`, rule-specification input scale.

## Start here

- **Fast path:** `knowledge/03-cdi-data-integration/00-mapping-fast-path-read-this-first.md` (the ten commands, connector
  settings for Snowflake, Databricks, Salesforce, SharePoint, BigQuery, PostgreSQL, the errors that cost the most time).
- **Every spec option:** `docs/SPEC_REFERENCE.md`. How the compiler works: `docs/HOW_IT_WORKS.md`. What was proven live: `docs/PROBES.md`, `docs/RETAIL_SUITE.md`.
- **Templates:** `examples/` (retail scenarios, combos, fixes, probes: each built and run in a real org; `connectors/`:
  Salesforce → Snowflake and Salesforce → Databricks in the shape of mappings that ran in a real org). Copy the closest one.
- **Profile:** copy `profile.example.json`, fill names, then `python mapgen.py --profile <file> resolve --write`.
- **A source, target or transformation with no template here** (IDMC supports far more connectors than the generator
  has templates for): the exemplar route, Fast Path §7.0. Export a mapping that already uses it (an existing one, or
  one made once in the Mapping Designer), run `python exemplar.py <export.zip>` (offline: it prints the adapter's
  typeSystem, object path, options, runtime attributes, the fields as spec tuples and a starter node), build from that,
  then add the connector's template to `examples/connectors/` and its row to the Fast Path. The spec type names
  (`STRING`, `INTEGER`, `NUMERIC`, `TIMESTAMP`...) are generic labels for IDMC platform types, used with every
  connector together with its own native type.

## Two ways to use it

**1. Through a blueprint (recommended).** `toolkit/demos/retail_data_foundation/idmc/03_mappings.py` and
`toolkit/demos/bid_desk_document_parsing/idmc/bid_mappings.py` use only the offline half (lint -> compile -> package) and import
the packages through the Script Library (`toolkit/lib`) with its single login, org guard and dry run. Copy that pattern for new demos:

```python
sys.path.insert(0, str(TOOLKIT_ROOT / "core" / "mapgen"))
from idmc_mapgen import lint as L
from idmc_mapgen.spec import load_spec
from idmc_mapgen.compile import build
from idmc_mapgen.package import package_bytes
```

**2. Its own CLI** (`python toolkit/mapgen/mapgen.py --help`): `build` and `lint` are offline; `whoami`, `resolve`,
`import`, `task`, `run` and `deploy` log in with mapgen's **own** client and session cache (a second login next to the
core library's). It reads the toolkit's `IDMC_LOGIN.txt` (nothing to set up), or `IDMC_USER`, `IDMC_PASS` and
`IDMC_LOGIN_URL` (`https://<IDMC_LOGIN_HOST>`) from the environment or from the file named by `MAPGEN_ENV_FILE`. Like the core library it makes one login attempt and holds off for 15 minutes after a rejected one.

# Mapping spec reference (spec format v1)

A spec is one JSON object that describes one CDI mapping: its sources, transformations, targets and the links
between them. `idmc_mapgen` compiles it into IMF JSON (the mapping's internal format), wraps that in an
import package (a `.DTEMPLATE` mapping plus export metadata and checksums), and the deploy step imports it.

```python
from idmc_mapgen.spec import load_spec
from idmc_mapgen.compile import build
from idmc_mapgen.package import package

spec = load_spec("my_mapping.json", profile="profile.json")   # merge the profile, fill ${VARS}, validate
imf = build(spec)                                              # IMF dict (bin/@2.bin content)
package(spec, imf, "my_mapping.pkg.zip")                       # import package
```

Legacy-compatible command line (writes `<name>.imf.json` and the package in the current directory; `<name>` is
the mapping name made safe as a Windows file name, `package.safe_file_name`: `m_a:b` gives `m_a_b.pkg.zip`; the
package itself keeps the real name):
`python -m idmc_mapgen.compile my_mapping.json [--profile profile.json] [--out pkg.zip]`.

## 1. Top level

| Key | Required | Meaning |
|---|---|---|
| `name` | yes | Mapping name (also the IMF template name and part of the package path): a non-empty string without `/`, `\`, control characters or lone surrogates. Convention: `m_<domain>_<purpose>`. |
| `description` | no | Shown in the designer and the export metadata. |
| `nodes` | yes | Transformations, in canvas order (section 5). Names must be unique and must not contain `.`. |
| `links` | yes | Edges between nodes (section 3); `[]` when there are none. |
| `connections` | yes | `{alias: connection}` (section 2). Every alias a node uses must be defined (spec or profile). |
| `orgGuid` | for packaging | The org's 22-character GUID (profile `org.guid`). |
| `orgName` | no | Source org name written in the export metadata (profile `org.name`; default `data`). |
| `folder` | for packaging | `{project, projectGuid, name, guid}`: the project and folder the mapping is imported into (GUIDs = FRS ids). `project` and `name` follow the rule of the mapping `name` and cannot be `.` or `..` (the package path is `Explore/<project>/<folder>/`). |
| `guid` | no | The mapping's own 22-character GUID. Omit it for a first import: the packager writes a fresh one into the spec dict, but a REUSE import of a new mapping gets an id of IDMC's own. `mapgen deploy` finds an existing mapping by name in its folder and rebuilds it under that id (OVERWRITE); when you package yourself, set `guid` to that id to rebuild the same mapping. |
| `assets` | no | Design assets the mapping references and that already exist in the org (rule specifications, DQ assets, mapplets): `[{guid, name, type, path}]`, e.g. `type: "RULE_SPECIFICATION"`, `path: "/Explore/<project>/<folder>"`. |
| `flowOrder` | no | Target load order: `[[[source names], [target names]], ...]`, one entry per pipeline, run in that order. Both lists are non-empty and name existing source and target nodes. |
| `inOutParameters` | no | In-out parameters (mapping variables) the mapping reads as `$$name` (section 5.4). |
| `documentType` | no | `"DMAPPLET"`: the spec is a mapplet, not a mapping (section 5.5). Absent, `null` or `"MAPPING"` is a mapping; any other value is a SpecError (IDMC rejects `"MAPPLET"`; the value is case-sensitive). |
| `active` | no | A mapplet spec only: the mapplet's own active flag, a boolean (section 5, "Option values"; default false). |
| `taskName` | no | The mapping task the deploy step creates or reuses (default `mt_<name without its m_ prefix>`). |
| `profile` | no | The profile to merge (section 7): a path or an inline object. A relative path is relative to the spec file's folder, never the current directory (for a spec given as a dict: relative to its `baseDir` when it has one, else the current directory). An explicit profile (`--profile`, or the `profile=` argument of the Python API; relative to the current directory) overrides it; the full order is in section 7.1. |
| `vars` | no | Variables for `${NAME}` (section 7.3). Names are ASCII letters, digits and `_`, not starting with a digit (anything else, `été` too, is a SpecError). They override the profile's `vars`; the caller's `vars=` override them. |
| `baseDir` | no | The folder relative `projectJson` / `folderJson` files resolve against (and, for a spec given as a dict, its relative `profile` path). `load_spec(path)` sets it to the spec file's folder; a spec file's own `baseDir` is read as its `profile` key is: a leading `~` is the home folder (`os.path.expanduser`), an absolute one is kept, a relative one resolves against the spec file's folder, and an empty or null one is that folder. A dict spec's `baseDir` is used as given, `~` included (section 8.1). |
| `packageOverrides` | no | Keys merged into `mappingTemplate.json` (e.g. `{"hasParameters": true}`). Absent = unchanged. |
| `runtimeEnvironment` | no | `{id, name}` used by the deploy step for the mapping task (profile `runtimeEnvironment`). |
| `projectJson`, `folderJson` | no | `[package path, local file]`: an extra file added to the package. The package path is a plain relative zip path (`\` is written as `/`); a relative local file resolves against `baseDir` (the spec file's folder). Rules in section 8.1. |

## 2. Connections

```json
"connections": {"WH": {"guid": "<22-char FRS guid>", "name": "<connection name>", "repoHandle": "<v2 connection id>", "kind": "BQ"}}
```

| `kind` | Effect |
|---|---|
| `BQ` (also what a connection with no `kind` gets: set `kind` on every connection, lint warns `CONN_KIND_MISSING`; this fallback is not a recommendation) | Targets carry the BigQuery runtime attributes: `writeDisposition` (from `disposition` / `truncate`) and `writeMode` = `Bulk`, plus any extra attributes, plus the 1 s job poll interval (`jobPollInterval` = `pollInterval` = `1`, `Job Poll Interval In Seconds` = `1`; the writer's default is 10 s per target, L-CDI-200). An attribute of that name the spec sets itself (`extra_*` / `*Attrs` / `writerAttrs`) wins, and its value is the interval of the names it does not set (one interval, never a mix). Target `poll`: a whole number of seconds sets the interval of the names the spec does not set, `false` leaves them out (lint `BQ_TGT_POLL` warns when nothing is left), `null` is the default. |
| `PG`, `JDBC` | Source, lookup and target object paths `<schema>/<table>` are rewritten to `<schema>/TABLE/<table>` (sources and lookups: `objkind` = `VIEW` gives `<schema>/VIEW/<view>`); lookups and targets refuse any other shape. Targets get no BigQuery attributes: their writer attributes come from `writerAttrs`, plus the PostgreSQL defaults of section 5.1. |
| `FF` | Sources are CSV flat files: native type `nstring`, delimiter `,`, text qualifier `"`, header on line 1. Adapter type system `CSVFile`. Lookups on a flat-file connection are refused. **Targets work too:** `object` = the file name, written in the connection's directory on the agent; the first run creates the file, with or without `createTarget`, and every later run overwrites it (one header, no append, unlike a create-new table target). There is nothing to browse before the first run, so declare the fields in the spec (= the upstream fields). The target builder has no flat-file branch: it writes the generic target and the engine picks the file writer from the connection; every value comes out double-quoted, with a header line. Proven 2026-11-03, FF → FF passthrough 189/189 rows (`examples/probes/m_probe_ff_target.json`). |
| `SF` or any other | No path rewrite and no BigQuery attributes (writer attributes through `writerAttrs`); set `typeSystem` (e.g. `Salesforce`) so sources, targets and lookups use that adapter type system. |

`typeSystem` (optional) overrides the adapter type system for every source, target and lookup on that connection
(default `TOOLKIT`; `CSVFile` for `FF` sources).

Two aliases with the same `guid` are one connection: the package lists it once, and they must agree on `name` and
`repoHandle` (a SpecError otherwise).

A JDBC target writes into the database bound on its connection, whatever schema the object names; use a
dedicated connection for scratch runs.

## 3. Links

| Form | Meaning |
|---|---|
| `["SRC_A", "EXP_A"]` | All fields of SRC_A's output flow into EXP_A's input group. |
| `["RTR_A.VALID", "TGT_OK"]` | From a named output group (router groups, `DEFAULT1`, generic outputs). |
| `["SRC_B", "JNR_A.Master"]` | Into a named input group (joiner `Master`/`Detail`, union input groups, generic inputs). |
| `["A", "B", ["col1", "col2"]]` | Only these incoming fields. |
| `["A", "B", {"in_name": "out_name", "keep": ""}]` | Only these, renamed (`""` = keep the name). |
| `["A", "B", {"exclude": ["col1"]}]` | Every incoming field except these. |

The field selection is a rule on the receiving input group; a group fed by one link has one rule.
Transformations pass incoming fields through by default (an "all fields" rule); targets map fields by name.

A list holds non-empty field names; a rename map maps a field name to a string. `{"exclude": [...]}` stands alone
and holds a list of names (`{"exclude": "col1"}` is an error); a rename map that merely renames a field called
`exclude` next to other renames stays a rename map.

## 4. Fields

Source, target and lookup fields are tuples:
`[name, TYPE, precision?, nativeType?, scale?, {flags}?]`

| TYPE | Platform type | Default precision, scale |
|---|---|---|
| `STRING` | string | 4000, 0 |
| `INTEGER` | bigint | 19, 0 |
| `INT32` | integer | 10, 0 |
| `NUMERIC` | decimal | 28, 9 |
| `FLOAT` | double | 15, 0 |
| `TIMESTAMP` | date/time | 29, 9 |
| `DATE` | date/time | 29, 9 |
| `BOOLEAN` | string | 10, 0 |

- `precision` and `scale` are whole numbers: JSON integers, the precision at least 1 and the scale at least 0;
  anything else (`5.0`, `"5"`, `true`, a list) is a SpecError naming the node and the field. `precision`,
  `nativeType` and `scale` `null` keep their defaults (the type's precision and scale; `nativeType` = TYPE). A
  nativeType is text (a number there becomes its text). A small STRING precision on readers (e.g. 256) keeps the
  agent's reader buffers small.
- A scale larger than the precision is a SpecError, and so is a `NUMERIC`, `TIMESTAMP` or `DATE` field with a
  precision below 9 and no scale of its own (the default scale 9 would exceed it): give the scale, e.g.
  `["amt", "NUMERIC", 5, null, 2]`. A precision of 9 or more without a scale keeps the default scale 9: valid, but
  it leaves precision - 9 integer digits (`["amt", "NUMERIC", 12]` is decimal(12,9), which holds no value of 1000 or
  more), so give the scale whenever the column holds larger values. The same rules hold for every other field list
  (expression, aggregator, union, normalizer, SQL, generic and in-out parameter fields, the mapplet `input` /
  `output` fields and a `mapplet` node's `inputs` / `outputs`, masking entries). A union field's precision `0` also
  means the default (the legacy spelling; `false` or `""` do not).
- `DATE` and `TIMESTAMP` adapter fields carry javaType `java.sql.Timestamp`, as every designer-built mapping does; a
  BigQuery `DATE` column reads and writes as `DATE` (values exact, run 2026-10-04), and PostgreSQL `date` columns
  (nativeType `date`) ran as source, lookup and target fields. (The legacy generators wrote `java.sql.Date`, which
  failed with "Unknown native type for field ... Type: DATE".)
- `nativeType` defaults to TYPE; set it for non-warehouse connectors (e.g. `character_varying`, `timestamp_with_time_zone`).
- `flags` (the 6th item; SaaS targets): an object of the six connector flags `createable`, `externalId`, `nullable`,
  `sfIdLookup`, `unique`, `updateable` and nothing else (another key, or a 6th item that is not an object, is a
  SpecError; `null` = none given), booleans (any spelling of section 5; written `"true"` / `"false"`);
  `nullable` and `updateable` default to true, the others to false.
- A target's `updateColumns` are flagged as keys.

Expression and aggregator fields are objects: `{"name", "type", "expr", "kind"?, "prec"?, "scale"?}`.

## 5. Node types

Every node has `type` and `name`, plus the escape hatches of section 6; its other keys are the options of its type
(below). `build` ignores a key its type does not read, and lint warns `UNKNOWN_OPTION` for it (section 5.8).

| Type | Options | Link keys | Adds fields |
|---|---|---|---|
| `source` | `conn`, `object` (`dataset/table`, `schema/table`, file name) or `query` (custom SQL in the source's dialect), `fields`, `objkind` (PG/JDBC: `TABLE` default, `VIEW`), `filter` (the source's own filter condition, e.g. a Salesforce SOQL WHERE condition such as `IsLatest = true`; keep it a literal list, the catalog cannot parse a sub-query and drops the source from lineage), `sfObject` (Salesforce object source: `true` writes the owner/resource object attributes IDMC itself exports) | out: `NAME` | the declared fields |
| `target` | `conn`, `object`, `fields`, `truncate`, `disposition` (`Write truncate`, `Write append`, `NONE` = no disposition, for DML ELT), `op` (`Insert` default, `Update`, `Upsert`, `Delete`, `Data Driven`), `updateColumns`, `updateStrategy`, `createTarget`, `pre_sql`/`preSQL`, `post_sql`/`postSQL`, `extra_opr` (`[[name, value]]` or `{name: value}`) / `oprAttrs` (`{name: value}`), `extra_rt` / `rtAttrs` (the same two forms), `writerAttrs`, `poll` (section 5.1), `batchSize` (writer batch rows; `0`/absent = the writer default, 200 rows for JDBC V2) | in: `NAME` | - |
| `expression` | `fields` (`kind` `OUTPUT` default, or `VARIABLE`), `window` (window functions; refused by default, section 5.7) | in/out: `NAME` | the OUTPUT fields |
| `filter` | `cond` | in/out: `NAME` | - |
| `router` | `groups`: `[[GROUP, condition], ...]` | in: `NAME`; out: `NAME.GROUP`, `NAME.DEFAULT1` | - |
| `sorter` | `keys` (`"-col"` = descending), `distinct` | in/out: `NAME` | - |
| `joiner` | `cond`: `[[master_col, detail_col], ...]`, `join` (`NORMAL`, `MASTER_OUTER`, `DETAIL_OUTER`, `FULL_OUTER`), `sorted`, `master`/`detail` (documentation only; the links decide) | in: `NAME.Master`, `NAME.Detail`; out: `NAME` | master + detail fields |
| `aggregator` | `groupBy`, `fields` (aggregate expressions) | in/out: `NAME` | the aggregate fields |
| `union` | `inputs` (group names), `fields` (`[[name, TYPE, prec?, null, scale?]]`: the field tuple without a native type, so its 4th item must be `null`; `prec` `0` or `null` = the type's default), `map` (`{GROUP: {out_field: incoming_field}}`) | in: `NAME.GROUP`; out: `NAME` | the declared fields |
| `lookup` | unconnected (default): `conn`, `object` or `query`, `fields`, `cond` (`[[lookup_col, IN_arg]]`), `ret`, `policy` (`Use First Value`, `Use Last Value`, `Use Any Value` (default), `Report Error`), `objkind` (PG/JDBC: `TABLE` default, `VIEW`); `connected: true` = connected lookup, with `cond` operators, `Use All Values`, `cache`, `dynamicCache` (section 5.2) | unconnected: none (call `:LKP.NAME(arg, ...)` in an expression); connected: in/out `NAME` | connected: the lookup fields |
| `rank` | `by`, `top` (default true), `n` (default 1), `groupBy` | in/out: `NAME` | `RANKINDEX` |
| `sequence` | `start`, `inc`, `reset` (default true) | in/out: `NAME` | `NEXTVAL`, `CURRVAL` |
| `masking` | `entries`: `[{field, type, pc?, prec?, scale?, data: {param: value}}]`: `type` is a technique of the Mapping Designer's rule catalogue (`MASKING_TYPES` in `nodes/masking.py`: 'Email address', 'Phone', 'SSN', 'Credit card', 'Key', 'Random', 'Substitution name', 'Dependent', ...; an unknown type is a spec error), `pc` the rule's data type = the masked field's platform type (default: the field's, as it arrives: STRING -> `string`, TIMESTAMP/DATE -> `date/time`, NUMERIC -> `decimal`, INTEGER -> `bigint`, ...; `string` when it cannot be derived; a `pc` that contradicts the field is a spec error; it picks the rule variant and the default precision/scale), `prec`/`scale` whole numbers (`null` = the default; a scale above the precision is a spec error), `data` the parameters that differ from the rule's defaults. lint runs the same rules: `MSK_TYPE` / `MSK_FIELD` are ERRORs exactly where the build refuses an entry / a passthrough value. `passthrough`: `true`, or a list `[name \| [name, TYPE, prec?, scale?], ...]`: an Expression `NAME_passthrough` after the masking maps `out_<f>` back to `<f>` (masked fields keep the masked value) | in/out: `NAME` | `out_<field>`, plus the passthrough fields |
| `normalizer` | `fields` (`[{name, type, prec?, scale?, occurs?}]`), `map` (`{normalizer input: incoming field}`), `generatedKey` (section 5.3) | in/out: `NAME` | only the normalized fields, `GCID_<f>` per repeating field, `GK_<f>` with `generatedKey` |
| `input`, `output` | mapplet specs only: `fields` (field tuples); `output` also `map` (`{output field: incoming field}`) (section 5.5) | input: out `NAME`; output: in `NAME` | input: the declared fields |
| `mapplet` | `mappletGuid`, `inputs`, `outputs` (field tuples), `map` (`{mapplet input: incoming field}`), `active`, `inputGroup` / `outputGroup` (section 5.5) | in/out: `NAME` | only the mapplet's outputs |
| `rulespec` | `asset`, `inputs` (`[[name, TYPE, prec?, scale?]]`: copy precision AND scale from the rule spec, or the designer shows Invalid), `map` (`{rule_input: incoming_field}`), `outputs` (default `[["Output", "STRING", 50]]`); list the asset in `assets` | in/out: `NAME` | the outputs |
| `cleanse` | `asset`, `fields`; inputs mapped by name | in/out: `NAME` | `<field>_<NAME>` |
| `dedup` | `asset`, `map` (`{asset_input: incoming_field}`; `GroupKey` and `Person_Name` are mandatory) | in/out: `NAME` | `Out_ClusterId`, `Out_ClusterSize`, `Out_IsSurvivor`, `Out_<input>`, ... |
| `verifier` | `asset` (an address Verifier asset), `inputs` / `outputs` (`[[port, prec]]`, the asset's ports in its order, e.g. `["Address_Lines_1", 128]`), `map` (`{asset input port: incoming field}`); list the asset in `assets` with type `VERIFIER` (extension module `nodes/verifier.py`, 2026-11-01) | in: `NAME` (group "Input group:"); out: `NAME` (group "MappletOutputTx_Output") | the asset's outputs; incoming fields pass through |
| `sql` | experimental, refused by default (section 5.7) | in/out: `NAME` | its outputs, `SQLError` |
| `generic` | any IMF class from raw properties: `cls`, `groups`, `in`, `out`, `props`, `objs`, `fields`, ... (section 5.6) | as declared | as declared |

Option values:

- Boolean options (`truncate`, `createTarget`, `top`, `reset`, `distinct`, `sorted`, `generatedKey`, the masking
  `passthrough` besides its list form, `allowUnsupported`, `continueOnError`, the `window` flags, the generic
  `keepInGroups` and the values of `objlist`, the field flags of section 4, a lookup's `connected`, a connected
  lookup's `cache` and `dynamicCache`, a `mapplet` node's `active` and a mapplet spec's own `active`) accept `true` /
  `false`, the strings `"true"` / `"false"` in any case, and `1` / `0`. Null or absent is the option's default;
  anything else is a SpecError naming the node and the option. So `"connected": "false"` is an unconnected lookup
  and `"cache": "false"` an uncached one. The generic `groups` flags are the one exception: JSON `true` / `false`
  only (section 5.6).
- `poll` is not a plain boolean: `true` / `false` (also as strings) or a whole number of seconds (section 5.1).
- Text options (expressions, conditions, SQL, object paths, target attribute values, field and group names, a
  mapplet's `mappletGuid`, the `advanced` values of section 6, ...) take a string. A number there is used as its text
  (`"expr": 0` is `"0"`); `true` / `false`, a list or an object is a SpecError naming the node and the option. Null
  is the option's default where it has one, and a SpecError where it has none. Raw IMF properties (the `set` escape
  hatch of section 6; a generic node's `props`, `objs` and field `extra`) are written as given.
- Whole numbers (JSON integers only): `precision` / `scale` (section 4), the normalizer's `occurs` (at least 1,
  default 1), the window's `startOffset` / `endOffset` (default 0) and a masking entry's `prec` / `scale`.
- lint reports each of these refusals as an ERROR with the build's own message: `NODE_MALFORMED`, or the node
  type's own code where it has one (`MSK_TYPE`, `MSK_FIELD`, `LKP_FIELD`, ...); see section 9.

### 5.1 Targets: operations, writer attributes, job poll

- `op`: `Insert` (default), `Update`, `Upsert`, `Delete`, `Data Driven` (case and surrounding blanks do not matter;
  `Data Driven` is IMF `Rowbased`, and `rowbased`, `datadriven`, `data_driven` work too). Any other value, `""`
  included, is a SpecError (lint `TGT_OP`, an ERROR). Every operation except `Insert` needs `updateColumns`, the key
  columns it matches on (flagged as keys).
- `updateStrategy`: the row-level expression of a Data Driven target, returning `DD_INSERT`, `DD_UPDATE`,
  `DD_DELETE` or `DD_REJECT`. Giving it without an `op` means Data Driven; a Data Driven target without it is a
  SpecError. Rows flagged `DD_REJECT` count as failed rows (run state WARNING).
- `writerAttrs`: `{"opr": {internal name: value}, "rt": {display name: value}}`, extra writer attributes for any
  connector (`oprRuntimeAttributes` / `runtimeAttributes`); booleans there are `YES` / `NO`. `extra_opr` / `oprAttrs`
  and `extra_rt` / `rtAttrs` are written for BigQuery targets only (lint `TGT_ATTRS_IGNORED` elsewhere).
- Connector defaults the generator adds (an explicit `writerAttrs` / `oprAttrs` / `rtAttrs` entry of the same name
  wins): BigQuery `Upsert`: `UpdateMode` = `Update Else Insert` (without it the writer only updates and drops new
  keys); BigQuery `Data Driven`: Enable Merge + Enable Data Driven = `YES` (without them every row is an update);
  PostgreSQL `Upsert`: `UpdateMode` = `Update Else Insert` (the writer default never inserts); PostgreSQL
  `truncate: true`: `TruncateTable` = `YES` (the writer ignores `WriteOptions.truncate`).
- `pre_sql` / `post_sql` on BigQuery and PostgreSQL targets become the writer attributes those writers run
  (BigQuery `preSQLWriter` / `postSQLWriter`, PostgreSQL `preSQL` / `postSQL`); the transformation's own "Pre SQL" /
  "Post SQL" properties, which those writers ignore, are left empty. Other connectors keep the properties, but the
  Snowflake Data Cloud and Databricks writers ignore them too (and the `truncate` flag): give those targets `writerAttrs`
  instead, Snowflake `{"opr": {"presql": ...}, "rt": {"Pre SQL": ...}}` (`postsql` / `Post SQL` likewise), Databricks
  `{"opr": {"writeDisposition": "Truncate"}, "rt": {"writeDisposition": "Truncate"}}`.
- `poll` (BigQuery only): absent, `null`, `true` or `"true"` = the default 1 s job poll interval (section 2);
  `false` or `"false"` (any case) = leave the poll attributes out (the writer's 10 s, unless the spec sets one
  itself); a whole number above 0 = that many seconds (`1` is one second). Anything else (`0`, `1.5`, `"1"`, ...) is
  a SpecError.
- `truncate` on BigQuery means `Write truncate` (the default `disposition` when `truncate` is set; `Write append`
  otherwise). A Bulk `Write truncate` skips a 0-row load and leaves the old rows.

Proven on a Secure Agent: `docs/PROBES.md`.

### 5.2 Lookups

- Unconnected (default): no links; call it from an expression as `:LKP.NAME(arg, ...)`, one argument per `cond`
  entry, in order. `cond` entries are `[lookup_col, IN_arg]` (equality; the operator form needs `connected`), `ret`
  is the field returned, and `policy` one of the four above.
- Connected (`"connected": true`, module `nodes/lookup_connected.py`): every incoming row looks the object or
  query up, and the lookup fields join the row. Link into and out of `NAME`. `cond` entries are
  `[lookup_field, incoming_field]` or `[lookup_field, op, incoming_field]` with `op` one of `=`, `!=`, `<`, `<=`,
  `>`, `>=`; the condition fields must be declared in `fields`, compared exactly (case included: `lk_K` is not
  `lk_k`), else a SpecError, and lint's `LKP_FIELD` compares them the same way. `policy` may also be
  `Use All Values` (one row per match). A row with no match keeps flowing with NULL lookup fields. Every lookup
  field leaves the lookup as a port, so prefix them (`lk_`; lint `LKP_COLLISION`). `cache: false` = an uncached
  lookup (one query per row), `dynamicCache: true` = a dynamic cache.
- Both: PG/JDBC objects are rewritten like sources' (section 2); flat-file lookups are refused; the adapter type
  system is the connection's `typeSystem` (default `TOOLKIT`).

### 5.3 Normalizer

`fields` are the normalized fields. A field with `occurs` n > 1 becomes the inputs `<name>_1` .. `<name>_n`, one
output `<name>` and `GCID_<name>` (which occurrence the row came from, 1..n); a field without `occurs` is copied to
every row. `occurs` is a whole number, at least 1 (default 1; `2.5` or `"2"` is a SpecError). `map` binds
normalizer inputs to incoming fields (default: the same name; an unknown key is a SpecError). `generatedKey: true`
adds `GK_<first repeating field>`. Only the normalized fields (and `GCID_` / `GK_`) leave the Normalizer: incoming
fields that are not listed are dropped.

### 5.4 In-out parameters

```json
"inOutParameters": [{"name": "p_max_seq", "type": "INTEGER", "default": "0", "aggregation": "MAX",
                     "retention": "ON_SUCCESS_OR_WARNING", "description": "high-water mark"}]
```

`name`: letters, digits and `_`, not starting with a digit, without `$$`, unique (case-insensitive). `type` defaults
to `STRING` (precision 100; `prec` / `scale` override). `aggregation`: `MAX` (default), `MIN`, `COUNT`. `retention`:
`ON_SUCCESS_OR_WARNING` (default), `ON_SUCCESS`, `ON_WARNING`, `NEVER`. Use `$$p_max_seq` in conditions,
expressions and source queries; `SETVARIABLE`, `SETMAXVARIABLE`, `SETMINVARIABLE` and `SETCOUNTVARIABLE` in an
expression update the value, which IDMC keeps after the run according to `retention` (the incremental high-water
mark pattern). Written as `Template.variables`.

### 5.5 Mapplets

A mapplet spec has `"documentType": "DMAPPLET"`, an `input` node (its fields are the mapplet's inputs; link out of
it), the logic, and an `output` node (its fields are the mapplet's outputs; link into it; `map` = `{output field:
incoming field}`, default the same name). `connections` may be `{}`. `package()` / `package_bytes()` write such a
spec as a DMAPPLET package (`<name>.DMAPPLET.zip` holding `mappletTemplate.json`, through
`nodes.mapplet.mapplet_package_bytes`), so `mapgen build`, `compile_file` and `python -m idmc_mapgen.compile` produce
the package `mapgen deploy` imports; `package_files()` builds mappings only and refuses it. The package lists the
spec's connections, but no `assets`, no `projectJson` / `folderJson` files (they are not even read) and no
`packageOverrides`. A mapplet spec that sets any of these gets lint `MPLT_PKG_IGNORED` (a WARN naming the keys), and
`mapgen build`, `mapgen deploy` and `python -m idmc_mapgen.compile` print the same warning. `validate()` still checks
their types and that each `assets` entry has a guid, name, type and path, but not the packager's own rules for them
(one asset guid = one object, the `projectJson` / `folderJson` shapes and files). The spec's own `active` (a
boolean, default false) is the mapplet's active flag. `mapgen deploy` imports it, creates no task, and prints the
mapplet's id. A REUSE import assigns a new id, so look it up by name in its folder after the import.

A mapping calls it with a `mapplet` node: `mappletGuid` (that id), `inputs` and `outputs` (field tuples
`[name, TYPE, prec?]`), `map` (`{mapplet input: incoming field}`, default the same name), `active` (a boolean,
default false), `inputGroup` / `outputGroup` (default `Input` / `Output`), plus an `assets` entry `{guid: <the same
id>, name, type: "DMAPPLET", path: "/Explore/<project>/<folder>"}` so the package declares the dependency. Only the
mapplet's outputs leave it; carry other fields around it (Joiner) or through it. lint reports what the build refuses
in `input`, `output` and `mapplet` nodes (a missing key, a value of the wrong kind, a field tuple) as
`NODE_MALFORMED`, with the build's message.

### 5.6 Generic

```json
{"type": "generic", "name": "X", "cls": "<fully qualified IMF class>",
 "groups": [["In", true, false], ["Out", false, true]], "in": {"In": "In"}, "out": {"": "Out"},
 "props": {"property": "value"}, "objs": {"property": [["<FQ class>", {"property": "value"}]]},
 "fields": [{"name": "f", "type": "STRING", "prec": 64, "extra": {"property": "value"}}]}
```

- `cls` (and the classes in `objs`, `groupCls`, `fieldCls`) is a fully qualified Java class; a short name only when
  the build already knows it. A class never re-points a core class that has the same short name.
- `groups`: `[[name, is_input, is_output], ...]`, names non-empty and unique, both flags JSON `true` / `false` (a
  string such as `"false"` is refused here).
- `in`: `{link key: group}`; the key `"G"` or `".G"` (the dot is optional) makes the link target `NAME.G`, `""` the
  bare `NAME`. `out`: `{link key: group}`; `"G"` (or `".G"`) makes the link source `NAME.G`, `""` the bare `NAME`.
  Two keys that are the same link key (`"In"` and `".In"`) are refused, and a group they name must exist.
- Without `in`, the first input group is the link target `NAME`; without `out`, the first output group is the link
  source `NAME`; `{}` means none, so a node without input groups (a source) or output groups (a sink) builds.
- `props` (plain properties), `objs` (`{property: [[class, {properties}], ...]}`; `"objlist": {property: false}` =
  one object, not a list) and `fields` (`[{name, type, prec?, scale?, extra?}]`, `fieldCls`, `fieldsProp`) override
  the builder's defaults, except `$$ID`, `$$class` and `name`. They cannot replace `groups` while it holds a link
  group. `groupCls` re-classes a group, `groupProps` (`{property: [group, ...]}`) moves groups into another property
  (`keepInGroups: true` keeps them in `groups` too), `adv` sets the advanced properties (default `Tracing Level` =
  `Normal`).

### 5.7 Experimental (refused by default)

- `expression` with `window` (partition / order frame, window functions; module `nodes/expression_window.py`):
  the mapping imports as valid, but the run stops at DTM start ("Invalid reference to LAG"). The build refuses it
  unless `window.allowUnsupported` is true. Use a Sorter + VARIABLE ports instead (`docs/PROBES.md`).
- `sql` (SQL transformation, module `nodes/sql.py`): imports, but runs fail at DTM start; refused unless
  `allowUnsupported` is true.

### 5.8 Extension modules

The core node types are imported explicitly. Every other module in `idmc_mapgen/nodes/` whose name does not start
with `_` (new transformation types, delegates such as `lookup_connected` / `expression_window`, template hooks) is
imported automatically and registers itself the same way; `idmc_mapgen.nodes.EXTENSIONS` lists the ones that
imported. A module that fails to import is never silently ignored:

- whatever it registered before failing is rolled back (no half-registered node type or template hook), also when
  the module that imported it handled the ImportError. A core builder or hook it removed before failing is put back,
  unless a module that imported successfully during that import names `NODES` or `TEMPLATE_HOOKS` in its source (or
  has a source that cannot be read): that module may have removed it itself, so nothing is put back, and a spec that
  uses the removed type then fails with `node type ... is not implemented` once the build goes on without the
  failed module;
- the failure is in `nodes.IMPORT_ERRORS` (`{module: "ExcType: message"}`), and `nodes.FAILED_SCOPE` holds
  `{module: (node types, reason it may act on every spec or None)}`: the node types its source declares plus those
  the rollback undid or put back (what it registered or removed before failing);
- `build` refuses (SpecError naming the module and its error) every spec that may need it: a spec that uses one of
  those node types, and every spec when the module adds or removes template hooks (a hook acts on every build), uses
  the registry in a way its source hides (`NODES` or `TEMPLATE_HOOKS` directly, `node()` or the registry module
  assigned to a variable or passed around, `getattr(registry, name)` included, a node type name
  computed at run time, `getattr` with a registry name written as a literal), reaches modules or code at run time (an attribute or
  an imported name `import_module`, `reload`, `exec_module`, `load_module`, `spec_from_file_location`, `run_path` or
  `run_module`, `sys.modules`, and the built-ins `__import__`, `exec` and `eval` used by those plain names), imports
  a module of this package whose functions register (a kit's `install()`: the module may have called it), imports
  code outside `idmc_mapgen` and the standard library (an installed kit, not read), or has a source that cannot be
  read or analysed. A spec that cannot need the module still builds, so a half-written new node type does not block
  unrelated work.
- The analysis reads the source. A registration that the analysis cannot see, and that the module had not made yet
  when it failed, is not found: for example one through a registry function fetched with `getattr` under a name
  built at run time from the package (`getattr(idmc_mapgen.registry, "no" + "de")`), or through a built-in reached
  as an attribute (`builtins.__import__`, `importlib.__import__`, `builtins.exec`). A template hook or a replacement
  of an existing type is then missing from the build without an error, and a spec that uses a new node type
  registered that way fails with `node type ... is not implemented` (the message lists the modules that failed to
  import).

`compile.broken_extensions(spec)` returns the list `build` refuses with, and lint reports each entry as
`EXTENSION_BROKEN`: an ERROR, as build refuses the spec. `MAPGEN_ALLOW_BROKEN_EXTENSIONS` set to `1`, `true`, `yes` or
`on` (any case), or `build(..., allow_broken_extensions=True)`, builds without the failed modules, with a
RuntimeWarning, and lint then reports them as WARNs (`lint(..., allow_broken_extensions=True)` likewise; both follow
`compile.allow_broken`). `allow_broken_extensions=False` refuses even when the variable is set. Replacing an existing
type needs `@node("joiner", override=True)`; registering a type a second time without it fails that module's import
(DuplicateNodeType), so the specs that use the type are refused.

Every builder carries an `options` attribute: the frozenset of the node keys it reads besides `type`, `name`, `set`
and `advanced` (`NODES["target"].options`), the keys its delegates and template hooks read included (a target's
`updateStrategy` and `writerAttrs`, a connected lookup's `cache` and `dynamicCache`). lint warns `UNKNOWN_OPTION` for
any other key of a node and names the nearest option (`"trunacte": true`: did you mean `truncate`?), because `build`
ignores such a key without a word and the option keeps its default. A builder that an extension module registers
without `options` is not checked. An extension that reads more keys of an existing type adds them to that builder's
`options` (`from .target import build as target_build`, then `target_build.options |= {"myKey"}`; naming `NODES`
would make a failed import of that module refuse every spec).

## 6. Escape hatches (any node)

- `"advanced": [[name, value], ...]` (or `{name: value}`) sets an advanced property, replacing the value of an
  existing one with that name or appending a new one. Names are non-empty strings; values are text, as the IMF
  holds them: a number becomes its text (`["Batch Size", 1000]` writes `"1000"`), and `true` / `false`, `null`, a
  list or an object is a SpecError naming the node.
- `"set": {property: value}` (or `[[property, value], ...]`) is merged into the transformation object last (plain
  values only). Links find a transformation by its node name, so a `set` that renames a linked one is a SpecError.
- A malformed `advanced` or `set` is a SpecError naming the node.

Use them to try a property the generator does not model yet; once proven, give it a real option.

## 7. Profiles and variables

A profile holds the org-specific values, so a spec stays portable:

```json
{"org": {"v2Id": "<v2 org id>", "guid": "<org guid>", "name": "<org name>"},
 "runtimeEnvironment": {"id": "<runtime environment id>", "name": "<name>"},
 "folder": {"project": "<project>", "projectGuid": "<guid>", "name": "<folder>", "guid": "<guid>"},
 "connections": {"WH": {"guid": "<guid>", "name": "<name>", "repoHandle": "<v2 id>", "kind": "BQ"}},
 "vars": {"WH_PROJECT": "<project id>", "DS": "<dataset>"}}
```

### 7.1 Which profile

One rule for `load_spec`, `compile_file`, `lint`, `deploy` and `mapgen.py build | lint | deploy`, first match wins:

1. The explicit profile: `--profile`, or the `profile=` argument (a path or a non-empty dict; `None`, `{}` and `""`
   mean "not given"). A relative path is relative to the current directory, even when a file of that name sits
   next to the spec.
2. The spec's own `profile` key: a path relative to the spec file's folder (never the current directory; a spec
   file's own `baseDir` does not change that), or an inline object. For a spec given as a dict, a relative path is
   relative to its `baseDir` when that is a non-empty string (a relative `baseDir` is itself relative to the
   current directory), else to the current directory. A missing file is a SpecError, never a fall-through to the
   next step.
3. The default profile: the `default_profile=` argument of `load_spec`, `lint` and `deploy` (`compile_file` has
   none). `mapgen.py` passes its fallbacks: `$MAPGEN_PROFILE` when it is set to a non-empty value (the file must
   then exist: a missing one is an error, never skipped; an empty value counts as unset), else `./profile.json` in
   the current directory, else `local/profile.local.json` next to `mapgen.py` (these two only when the file
   exists: a missing one is skipped).
4. No profile: the spec carries everything itself.

The `mapgen.py` commands that take no spec (`whoami`, `resolve`, `import`, `task`, `run`, `log`) use `--profile`,
else the same fallbacks; `jobs` reads no profile. `python -m idmc_mapgen.compile` and `python -m idmc_mapgen.lint`
have no fallbacks (steps 1, 2 and 4 only). Spec and profile files are UTF-8, with or without a byte order mark.

### 7.2 Merge

- The spec wins over the profile, key by key (`folder` and each connection alias are merged per key):
  `orgGuid` <- `org.guid`, `orgName` <- `org.name`, `runtimeEnvironment`, `folder`, `connections`.
- Only the connection aliases the spec's nodes use (or the spec names) are copied from the profile: each one
  becomes a package dependency the org must resolve.
- The merge sees the spec after substitution, so a node's `conn`, a `connections` key or the whole `nodes` list
  may come from a var. Of the profile, only the values the merge keeps are substituted: an unused connection or a
  value the spec overrides may hold an undefined `${...}` without an error. The spec's `profile` key itself is
  not substituted (the profile is chosen first), and an inline profile object stays in the loaded spec as written.

### 7.3 Variables and substitution

- `vars` come from three places, later ones winning name by name: the profile's `vars`, the spec's own `vars`, then
  the caller's `vars=` argument (`load_spec`, `compile_file`, `lint`, `deploy`). A value may be any JSON value and
  may use other vars (`"FQ": "${PROJECT}.${DATASET}"`); a cycle is an error. The loaded spec's `vars` holds the
  effective value of every var it declares.
- `${NAME}` is replaced in every string of the spec, and in dict keys, inside lists, objects and (for Python
  callers) tuples. An unknown name is an error (how lint reports one when no profile is in effect: section 9). Two
  keys of one object that become the same key are an error.
- A string that is exactly one `${NAME}` takes the var's value with its JSON type: `"truncate": "${TRUNCATE}"` with
  `false` is `false`, not the text `"false"`; `5` stays `5`, a list stays a list, and `null` stays `null` (as if null
  were written there). Two kinds of places keep the IMF's own types instead:
  - text slots, the places the IMF or the package holds as text (names, descriptions, GUIDs, connection, folder and
    asset values, link ends and selections, `flowOrder`, `projectJson` / `folderJson`, in-out parameter names,
    types and defaults; in a node `type`, `name`, `conn`, `object`, `query`, `cond`, SQL, `op`, `disposition`,
    `updateStrategy`, field names, types, native types and expressions, `advanced` and writer attribute values, ...;
    the full list is `_TEXT_SPEC`, `_TEXT_NODE` and `_TEXT_NODE_TYPE` in `spec.py`): there a number or `true` /
    `false` becomes text in JSON spelling (`"1000"`, `"1.5"`, `"true"`);
  - raw IMF properties (the `set` escape hatch of any node; a generic node's `props`, `objs` and field `extra`):
    `true` / `false` becomes text, and a number stays a number only under the IMF's numeric keys
    (`_IMF_NUMBER_KEYS`: `precision`, `scale`, `batchSize`, `rowLimit`, ...), else it becomes text.
- Inside a longer string, a number, `true`, `false` or `null` is written in JSON spelling (`"top_${N}"` with `5` is
  `"top_5"`), and a list or object is an error. A value JSON has no type for (a Python caller's date or Decimal)
  is its `str()` text. (`spec.substitute()` on its own knows no slots: there every whole value keeps its JSON type.)
- `$${` is a literal `${` (`$${NAME}` gives `${NAME}`). Any other `${` that does not start a `${NAME}` (`${ X }`,
  `${A-B}`, an unclosed `${`) and three or more `$` before `{` (`$$${X}`) are errors, so nothing that looks like
  `${...}` is left over. Informatica's `$$PARAM` and `$PMCacheDir` (no braces) are untouched.
- `load_spec` reports every problem at once in one SpecError (missing identity keys, unknown aliases, bad links,
  wrong types, undefined variables, malformed placeholders).
- Load a spec once. Loading turns every `$${` into a literal `${` and fills every var, so a loaded spec passed
  again to `load_spec`, `prepare`, `lint`, `compile_file` or `deploy` is substituted a second time: with `X` = `v`,
  `"SELECT '$${X}' AS a"` loads as `SELECT '${X}' AS a`, and loading that result again gives `SELECT 'v' AS a` (or
  an undefined-variable error when `X` is not defined for the second load: the loaded spec keeps only the vars it
  declares itself). Give those entry points the spec file or the dict as written; `build` and the `package`
  functions take the loaded spec and substitute nothing.

## 8. Packages and reproducible builds

### 8.1 Package rules

- The mapping is the entry `Explore/<project>/<folder>/<name>.DTEMPLATE.zip` (a mapplet: `<name>.DMAPPLET.zip`),
  so the project, folder and mapping names are non-empty strings without `/`, `\`, control characters or
  lone surrogates, and a project or folder is never `.` or `..`.
- A connection guid is one package dependency, however many aliases name it (they must agree on `name` and
  `repoHandle`); likewise an asset guid (entries must agree on `name`, `type` and `path`). A guid cannot be both a
  connection and an asset.
- `exportPackage.chksum` keys are escaped the way `java.util.Properties` writes them (`\ ` for a space, `\:`, `\=`,
  `\#`, `\!`, `\\`, `\uXXXX` for non-ASCII), which is how IDMC reads them back.
- `projectJson` / `folderJson` = `[package path, local file]`, two non-empty strings (from Python the local file
  may be an `os.PathLike`). The package path is a plain relative zip path: `\` is written as `/`; no leading `/`, no
  empty, `.` or `..` step, no control character or lone surrogate, and not an entry the package already has (the
  DTEMPLATE zip, `exportMetadata.v2.json`, `exportPackage.chksum`, the other extra file). An absolute local file
  is used as is; a relative one resolves against `baseDir`. For a spec loaded from a file that is the spec file's
  folder (its own relative `baseDir` resolves against that folder, a leading `~` is the home folder, an empty or
  null one is that folder, an absolute one is kept). A dict spec's `baseDir` is used as given, with no `~`
  expansion (`~/x` is a relative folder there): a null, empty or relative one is an error once a relative local
  file needs it, and a dict spec without a `baseDir` key resolves against the current directory. A folder or an
  unreadable file is a SpecError naming the key and where it looked.
- These checks raise a SpecError before `spec["guid"]` is written. The ones that need no file (the names, one guid =
  one object, the `projectJson` / `folderJson` shapes and the `baseDir` rule) are also part of
  `validate(spec, for_package=True)`, so `load_spec`, lint and deploy refuse them before any package is written.

### 8.2 Reproducible builds

`build(spec, now=<epoch seconds or ISO string>)` pins createTime; `package_bytes(spec, imf, now_ms=<epoch ms>)` and
`package(...)` pin every package timestamp (deployTime, attachTime, the checksum header, the zip entry dates;
mapplet packages too); `compile_file(spec, now=...)` pins both from one `now`, epoch seconds or an ISO string. The
two read `now` differently:

- createTime: epoch seconds (and no `now`: the current time) are written in UTC as `YYYY-MM-DDTHH:MM:SS.000Z`
  (whole seconds). An ISO string is written exactly as given (`compile_file` strips surrounding white space first):
  `2026-10-03T05:00:00+05:00` stays that text, and `2026-10-03T00:00:00` has no `Z`. For the UTC form the designer
  writes, give `2026-10-03T00:00:00.000Z` or epoch seconds. `compile_file` refuses a string that is not an ISO
  timestamp; `build` alone writes any string as given.
- the package times: an ISO string with `Z` or without a zone is UTC, and one with an offset is converted
  (`2026-10-03T05:00:00+05:00` is 00:00 UTC). The checksum header (`#<date> UTC`) is that instant in UTC.

With a fixed `guid`, the same spec and `now` give byte-identical packages on the same kind of system in the same
time zone:

- the zip entry dates are written in the builder's local time (`time.localtime`), so the same `now` built under
  another time zone gives other bytes (and another checksum line for the DTEMPLATE zip);
- `zipfile` records the system that wrote each entry (Windows or not), so a Windows build and a Linux build differ;
- createTime and the checksum header do not depend on the time zone;
- the pinned time must fall in 1980-2107 in local time, the years a ZIP entry date can hold: `compile_file`,
  `package`, `package_bytes`, `package_files` and `nodes.mapplet.mapplet_package_bytes` refuse any other (0, a
  negative or a huge number, NaN, text) with a SpecError, before `spec["guid"]` is written, never with zipfile's
  raw ValueError.

The equivalence tests compare against the earlier generators on one machine, so both sides share its time zone.

## 9. Lint

`mapgen lint` (also `python -m idmc_mapgen.lint` and `idmc_mapgen.lint.lint()`) loads a spec exactly as `load_spec`
does (the profile of section 7.1, the merge and the substitution of section 7), checks it without building or
importing anything, and reports ERRORs, WARNs and INFOs; `mapgen deploy` refuses a spec with an ERROR unless
`--force-lint` is given. `python -m idmc_mapgen.lint --rules` lists every code. A spec that lints with no ERROR also
passes `load_spec`: lint ends with `validate(spec, for_package=True)`.

- Values the build refuses are ERRORs worded by the build (section 5, "Option values"): each node module's
  `lint_problems` hook runs the builder's own readers (`values.lint_hook`), a generic node is built by its own
  builder through `compile.build_node`, so its refusals are `NODE_MALFORMED` with the builder's message, and a
  connected lookup's condition fields are compared exactly, as the builder compares them (`LKP_FIELD`). An unknown
  target `op` is `TGT_OP`.
- `${NAME}`s with no profile in effect (no `--profile` / `profile=`, no `profile` key, no default profile): an
  undefined name is an ERROR, `VAR_UNKNOWN`, when the spec is self-contained (its own `orgGuid`, a `folder` with all
  four keys, and `connections` that list every alias a node uses, each connection with `guid`, `name` and
  `repoHandle`), because `load_spec` refuses it. Only a template (a spec that leaves one of those to a profile) gets
  INFO `VAR_UNRESOLVED` instead, the profile it needs may define the name, and each value it lacks is an ERROR of
  its own anyway. With a profile in effect an undefined name is always `VAR_UNKNOWN`.
- `EXTENSION_BROKEN` (a module of `idmc_mapgen/nodes/` the spec may need failed to import) and `UNKNOWN_OPTION` (a
  node key its builder does not read, a WARN): section 5.8. `MPLT_PKG_IGNORED` (a mapplet spec key its package
  ignores, a WARN): section 5.5.
- lint is deliberately stricter than build. Most of its rules report what builds but fails or misbehaves at run
  time (a target field nothing produces, an expression naming a field that does not arrive, a same-source join
  that is not sorted, ...), and two refuse a node the build accepts: a generic node with `"groups": []` (a
  transformation without groups: `NODE_MALFORMED` "generic without groups") and a connected lookup with
  `"cond": []` (a lookup without a condition: `NODE_MALFORMED` "lookup without cond").

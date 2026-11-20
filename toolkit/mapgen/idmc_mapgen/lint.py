"""Static checks on a mapping spec, run before anything is imported.

Every rule below comes from a failure that was hit for real (the lesson ids point at knowledge/lessons/lessons.jsonl). The most
useful ones need the field flow (fieldflow.py): a target maps its fields BY NAME, so a field that never
arrives is written as NULL with no error, and an expression that names a missing field fails only at run time.

    from idmc_mapgen.lint import lint, format_issues, has_errors
    issues = lint(spec)                        # spec dict or path; optional profile (dict or path)
    print(format_issues(issues))
    if has_errors(issues): raise SystemExit(1)

CLI:  python -m idmc_mapgen.lint spec.json [--profile p.json] [--level warn] [--json] [--allow-live] [--rules]
Node types added later register extra checks with ``@check("type")`` -> ``fn(ctx, nd)`` yielding issues
(use ``ctx.issue(code, node, message, ...)``) and their field rule in fieldflow (``@flow``).
"""
import importlib, json, os, re, sys
from collections import namedtuple, Counter, defaultdict

try:
    from . import fieldflow as ff
    from . import spec as specmod
except ImportError:                     # run as a plain script
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from idmc_mapgen import fieldflow as ff
    from idmc_mapgen import spec as specmod

_PKG = ff.__name__.rpartition(".")[0]   # idmc_mapgen: the compiler and the node builders are imported when needed
SEV_ORDER = {"ERROR": 0, "WARN": 1, "INFO": 2}

# code -> (default severity, short title, hint, lesson)
CODES = {
    # spec shape
    "SPEC_SHAPE": ("ERROR", "spec is not a mapping spec", "A spec needs name, nodes[] and links[]; every node needs type and name.", ""),
    "SPEC_PACKAGE_KEYS": ("ERROR", "package metadata missing", "orgGuid and folder{project, projectGuid, name, guid} are needed to build the package (or give them in a profile).", "L-CDI-034"),
    "SPEC_GUID": ("WARN", "mapping guid is not 22 characters", "Leave guid out for a new mapping; keep the imported guid to OVERWRITE the same mapping.", "L-CDI-145"),
    "SPEC_NAME_CONVENTION": ("INFO", "mapping name does not start with m_ (a mapplet's with mplt_)", "Mappings m_<x>, tasks mt_<x>, kept 1:1; mapplets mplt_<x>.", "L-CDI-111"),
    "VAR_UNKNOWN": ("ERROR", "${VAR} placeholder that no var defines (load_spec refuses the spec)", "Add it to the profile 'vars' or the spec's own 'vars', or remove the placeholder.", ""),
    "VAR_UNRESOLVED": ("INFO", "${VAR} placeholders left (a template linted without its profile)", "No profile is in effect, and this spec takes its orgGuid / folder / connections from one (each missing one is an ERROR here): pass --profile to check the resolved values.", ""),
    "EXTENSION_BROKEN": ("ERROR", "a module of idmc_mapgen/nodes/ this spec may need failed to import", "build refuses the spec until the module is fixed or removed (the message says why the spec may need it); with MAPGEN_ALLOW_BROKEN_EXTENSIONS=1 (allow_broken_extensions=True) build goes on without it and lint only warns.", ""),
    "MPLT_PKG_IGNORED": ("WARN", "a DMAPPLET spec sets keys its package does not carry", "Remove the keys; a mapplet that needs them (a rule specification or mapplet it calls as an asset, extra package files, template overrides) has to be packaged as a mapping instead.", ""),
    "CONN_UNKNOWN": ("ERROR", "connection alias not defined", "Every node 'conn' must be a key of spec.connections (or of the profile).", ""),
    "CONN_INCOMPLETE": ("ERROR", "connection missing guid / name / repoHandle", "The IMF binds the connection GUID; the package lists name and the v2 id (repoHandle). 'mapgen resolve' fills them by name.", "L-CDI-034"),
    "CONN_KIND": ("WARN", "unknown connection kind", "Known kinds: BQ, PG, JDBC, FF, SF. Any other connector (Snowflake, Databricks, SharePoint, Oracle, SQL Server, ...) takes the generic TOOLKIT path: expected, give it any label and set its writerAttrs (Mapping Fast Path section 2).", ""),
    "CONN_KIND_MISSING": ("WARN", "connection has no 'kind'", "Without a kind the generator treats the connection as BigQuery, which is not a recommendation and is wrong for any other system: set kind explicitly ('mapgen resolve' fills it for BQ / PG / JDBC / FF / SF; use any label for other connectors).", ""),
    "ASSET_INCOMPLETE": ("ERROR", "asset entry missing guid / name / type / path", "Referenced design assets need all four to be packaged.", ""),
    "FLOW_ORDER": ("ERROR", "flowOrder names an unknown source or target", "flowOrder is [[[sources], [targets]], ...] over existing source and target nodes.", ""),
    # nodes
    "NODE_TYPE_UNKNOWN": ("ERROR", "unknown node type", "Use a registered node type, or 'generic' with the full IMF class.", ""),
    "NODE_UNCHECKED": ("INFO", "node type has no field rule", "Fields downstream of it are not checked.", ""),
    "NODE_DUP_NAME": ("ERROR", "duplicate node name", "Transformation names must be unique in a mapping.", ""),
    "NODE_NAME": ("ERROR", "invalid transformation name", "Use letters, digits and underscores; '.' separates the node from its group in links.", "L-CDI-111"),
    "NODE_MALFORMED": ("ERROR", "node is missing a required key", "See the node type's spec reference.", ""),
    "UNKNOWN_OPTION": ("WARN", "node key its node type does not read (build ignores it)", "A node takes type, name, set, advanced and the options of its type (docs/SPEC_REFERENCE.md section 5); build ignores any other key without a word, so a misspelt option (\"trunacte\") silently keeps its default. Fix the spelling or remove the key.", ""),
    "FIELD_DECL": ("ERROR", "malformed field declaration", "Fields are [name, TYPE, precision?, nativeType?, scale?, {flags}?] (or {name, type, expr} on expression-like nodes).", ""),
    "FIELD_DUP": ("ERROR", "duplicate field name in one node", "Field names must be unique per transformation (case-insensitive).", ""),
    "TYPE_UNKNOWN": ("ERROR", "unknown field type", "Types: STRING, INTEGER, INT32, NUMERIC, FLOAT, TIMESTAMP, DATE, BOOLEAN.", ""),
    "TYPE_JSON": ("ERROR", "JSON-typed field", "Declare JSON columns STRING: JSON fields fail in BigQuery Simple mode; a pre-created JSON target column still receives the text.", "L-CDI-039"),
    # links
    "LINK_SHAPE": ("ERROR", "link is not [from, to] or [from, to, rule]", "", ""),
    "LINK_FROM_UNKNOWN": ("ERROR", "link from an unknown node", "", ""),
    "LINK_TO_UNKNOWN": ("ERROR", "link to an unknown node", "", ""),
    "LINK_FROM_GROUP": ("ERROR", "link from a group the node does not have", "Router groups are linked as '<RTR>.<GROUP>' (DEFAULT1 is added); other nodes by their bare name.", ""),
    "LINK_TO_GROUP": ("ERROR", "link to an input the node does not have", "Joiners take '<JNR>.Master' and '<JNR>.Detail'; unions '<UNI>.<input>'; sources take no input.", ""),
    "LINK_MULTI_IN": ("ERROR", "two links into one input group", "Each input group takes exactly one link; merge streams with a Union.", ""),
    "LINK_RULE_FIELD": ("ERROR", "link field rule names a field that is not upstream", "The rule silently selects nothing for that name; fix the name or remove it.", ""),
    "LINK_RULE_AMBIGUOUS": ("ERROR", "rename map with a field named 'exclude'", "The generator reads any dict holding the key 'exclude' as an EXCLUDE rule (iterating its value): the renames are lost. Rename that field upstream (e.g. in the source query).", ""),
    "LINK_CYCLE": ("ERROR", "the links form a cycle", "A mapping is a DAG.", ""),
    "NODE_NO_INPUT": ("ERROR", "node has no incoming link", "Every transformation and target needs an upstream link.", ""),
    "NODE_NO_OUTPUT": ("WARN", "node has no outgoing link (dead branch)", "It does nothing at run time (live mappings carried such leftovers); remove it so the canvas tells the truth.", ""),
    "NODE_INPUT_MISSING": ("ERROR", "an input group is not linked", "Every joiner side and union input needs a link.", ""),
    # sources / SQL
    "SRC_NO_OBJECT": ("ERROR", "source has neither query nor object", "", ""),
    "SRC_QUERY_AND_OBJECT": ("WARN", "source has both query and object", "The query wins; drop one.", ""),
    "SRC_NO_FIELDS": ("ERROR", "source declares no fields", "", ""),
    "SQL_NON_ASCII": ("ERROR", "non-ASCII character in a query", "The BigQuery reader fails with 'IOException: missing CR'; strip non-ASCII.", "L-CDI-024"),
    "SQL_TRAILING_SEMICOLON": ("ERROR", "query ends with ';' or holds several statements", "The connector wraps the query; remove the ';'.", "L-CDI-024"),
    "SQL_COMMENT": ("WARN", "comment in a query", "Strip comment lines and trailing -- comments before they reach the reader.", "L-CDI-024"),
    "SQL_FIELDS": ("WARN", "declared fields do not match the query's SELECT list", "Declared source fields should equal the query's column names.", ""),
    "SQL_FIELDS_EXTRA": ("INFO", "query selects columns the source does not declare", "Undeclared columns are read and dropped; select only what you need (reader memory).", "L-CDI-129"),
    "BQ_READERS": ("WARN", "5 BigQuery readers in one pipeline", "Each reader takes DTM heap on the agent; 4 per pipeline is the reliable target: split the spec by connected component or read fewer tables.", "L-CDI-129"),
    "BQ_READERS_MAX": ("ERROR", "more than 5 BigQuery readers in one pipeline", "7-8 readers in one mapping exhausted the agent-wide DTM heap (Java heap / GC overhead); at most 5 was reliable.", "L-CDI-129"),
    "BQ_READERS_MAPPING": ("WARN", "more than 5 BigQuery readers in one mapping", "Pipelines of one mapping run together in one DTM (6 worked once, 7-8 died); split the mapping, or serialize the pipelines with flowOrder.", "L-CDI-129"),
    "BQ_STRING_PRECISION": ("WARN", "BigQuery reader STRING field without precision (4000)", "Give STRING reader fields precision 256 unless the column is long text: 4000 allocates huge row buffers.", "L-CDI-129"),
    "PG_OBJECT_PATH": ("ERROR", "PostgreSQL/JDBC object path shape", "Use '<schema>/<table>' (the generator adds /TABLE/) or '<schema>/TABLE|VIEW/<name>'; 'public.<t>' or a bare name fails.", "L-CDI-162"),
    "BQ_OBJECT_PATH": ("ERROR", "BigQuery object is not '<dataset>/<table>'", "", ""),
    # targets
    "TGT_NO_FIELDS": ("ERROR", "target declares no fields", "", ""),
    "TGT_FIELD_UNPRODUCED": ("ERROR", "target field never arrives (written as NULL)", "Targets map fields BY NAME; add or rename the field upstream (expression port or link rule).", ""),
    "TGT_FIELD_CASE": ("WARN", "target field matches upstream only by case", "Make the case identical; BY_NAME mapping may not fold case.", ""),
    "TGT_FIELD_UNCHECKED": ("INFO", "target fields not verifiable (upstream unchecked)", "", ""),
    "TGT_TYPE_COERCE": ("WARN", "STRING arrives in a numeric/date target field", "Convert explicitly (TO_INTEGER / TO_DECIMAL / TO_DATE) so bad values are visible, not rejected rows.", ""),
    "TGT_OP": ("ERROR", "unknown target operation (build refuses it)", "Operations: Insert, Update, Upsert, Delete, Data Driven (any case; Rowbased, datadriven and data_driven are Data Driven).", ""),
    "TGT_KEYS": ("ERROR", "update/upsert/delete/data-driven without valid updateColumns", "Name the key columns in updateColumns; they must be target fields.", ""),
    "BQ_TGT_POLL": ("WARN", "BigQuery target left at the writer's 10 s job poll", "The generator writes jobPollInterval = pollInterval = 'Job Poll Interval In Seconds' = 1 on every BigQuery target unless it says \"poll\": false (the same mapping ran 127 s -> 56 s): drop \"poll\": false, or set \"poll\": <whole seconds>.", "L-CDI-200"),
    "BQ_TGT_APPEND": ("WARN", "BigQuery target appends on every run", "Set truncate: true for a full reload, or disposition 'Write append' to say appending is intended.", "L-CDI-038"),
    "BQ_TGT_DML": ("INFO", "BigQuery target with disposition NONE", "No write disposition is sent (for DML/ELT jobs only).", ""),
    "TGT_ATTRS_IGNORED": ("WARN", "BigQuery-only target options on a non-BigQuery target", "oprAttrs / rtAttrs / disposition / extra_opr / extra_rt / poll are only emitted for BigQuery targets (writerAttrs work for any connector).", ""),
    "TGT_PG_TRUNCATE": ("WARN", "PostgreSQL truncate / Pre-SQL / Post-SQL WILL run", "idmc_mapgen writes the PostgreSQL writer attributes (TruncateTable=YES, preSQL, postSQL), so the table is truncated / the SQL is executed on every run (proven 2026-10-03). The legacy generators wrote properties the writer ignored, so a rebuilt legacy spec changes behaviour: review it. A posting table with truncate is a wipe risk.", "L-CDI-169"),
    "TGT_PG_UPSERT": ("INFO", "PostgreSQL Upsert = INSERT ... ON CONFLICT DO UPDATE", "idmc_mapgen adds UpdateMode=Update Else Insert (the writer default never inserts). The key columns need a unique index or primary key, and every mapped column is written (a blank source value blanks the target).", "L-CDI-167"),
    "BQ_TGT_SQL": ("WARN", "BigQuery pre/post SQL WILL run", "idmc_mapgen moves pre_sql/post_sql to the BigQuery writer attributes (preSQLWriter/postSQLWriter), which the writer executes on every run; the legacy generators wrote a property the BigQuery writer ignored.", ""),
    "EXPR_WINDOW_FN": ("ERROR", "window function in a standard mapping", "LAG/LEAD and other windowing import as valid but fail at run start (TE_7002 'Invalid reference to LAG found'): windowing exists only in elastic / SQL-ELT mappings. Use a Sorter + VARIABLE ports (previous-row pattern, see docs/PROBES.md).", ""),
    "LKP_COLLISION": ("WARN", "connected lookup field has the name of an incoming field", "Every lookup field leaves a connected lookup as a port: prefix the lookup fields (e.g. lk_) so they cannot collide with incoming names.", ""),
    "TGT_JDBC_TRUNCATE": ("WARN", "JDBC V2 target with truncate", "JDBC V2 ignores truncate: use preSQL 'TRUNCATE TABLE <t>'.", "L-CDI-171"),
    "TGT_JDBC_DATABASE": ("INFO", "JDBC V2 target writes the connection's database", "The schema part of the object is ignored; use a scratch connection for parity runs.", "L-CDI-040"),
    "TGT_VIEW": ("ERROR", "target object is a view", "Write a table.", ""),
    "TGT_SAME_OBJECT": ("WARN", "two truncating targets write the same object", "The second load wipes the first; use one target or append.", ""),
    "TGT_PROTECTED": ("ERROR", "target matches a protected (live) object", "Write a scratch target, or pass allow_live=True / --allow-live for a reviewed swap.", ""),
    "FOLDER_PROTECTED": ("ERROR", "mapping folder is protected (live)", "Build in a scratch folder, or pass allow_live=True / --allow-live for a reviewed swap.", ""),
    # expressions
    "EXPR_SYNTAX": ("ERROR", "expression syntax", "Unbalanced parentheses or an unterminated string.", ""),
    "EXPR_FIELD_UNKNOWN": ("ERROR", "expression names a field that does not arrive", "Check the name and the upstream link rules.", ""),
    "EXPR_FIELD_UNCHECKED": ("INFO", "expression fields not verifiable (upstream unchecked)", "", ""),
    "EXPR_OUTPUT_REF": ("ERROR", "OUTPUT port references another OUTPUT port", "Compute the shared value in a VARIABLE port and reference that.", "L-CDI-105"),
    "EXPR_SELF_REF": ("ERROR", "OUTPUT port references itself", "", ""),
    "EXPR_VAR_FORWARD": ("INFO", "VARIABLE port references a later variable port", "That reads the previous row's value (intended only for running totals).", ""),
    "EXPR_PORT_CONFLICT": ("ERROR", "new port has the name of an incoming field", "Rename the incoming field on the link (e.g. {'member_id': '', 'full_name': 'r_full_name'}) and derive the port from it, or give the port a new name.", ""),
    "EXPR_PORT_KIND": ("WARN", "unknown expression port kind", "kind is OUTPUT (default) or VARIABLE.", ""),
    "EXPR_NO_PORTS": ("WARN", "expression has no ports", "", ""),
    "EXPR_DOUBLED_QUOTE": ("WARN", "doubled apostrophe in a string literal", "Informatica has no '' escape: write 'it' || CHR(39) || 's'.", "L-CDI-105"),
    "EXPR_DOUBLE_QUOTED": ("WARN", "double-quoted string", "Informatica string literals use single quotes.", "L-CDI-103"),
    "EXPR_SQL_FUNCTION": ("WARN", "SQL function in an Informatica expression", "The transformation language is not SQL.", "L-CDI-103"),
    "EXPR_SQL_SYNTAX": ("WARN", "SQL syntax in an Informatica expression", "Use IIF / DECODE(TRUE, ...) / ISNULL(x) / IN(x, ...) / REG_MATCH instead of CASE, IS NULL, IN (...), LIKE, BETWEEN.", "L-CDI-103"),
    "EXPR_FUNCTION_UNKNOWN": ("INFO", "function not in the known Informatica list", "Verify the name in the transformation-language reference.", ""),
    "EXPR_PARAM": ("INFO", "mapping parameter used", "$$ parameters need a definition (parameter file / in-out parameter) at run time.", ""),
    "EXPR_LKP_UNKNOWN": ("ERROR", ":LKP call to an undefined unconnected lookup", "", ""),
    "EXPR_LKP_ARITY": ("ERROR", ":LKP call with the wrong number of arguments", "Pass one argument per lookup condition.", ""),
    "LKP_NOT_CALLED": ("WARN", "unconnected lookup is never called", "Call it as :LKP.<name>(args) or remove it.", ""),
    "LKP_FIELD": ("ERROR", "lookup return/condition field not declared", "", ""),
    # transformation-specific
    "JNR_TYPE": ("ERROR", "unknown join type", "join: NORMAL | MASTER_OUTER | DETAIL_OUTER | FULL_OUTER.", ""),
    "JNR_COND": ("ERROR", "join condition field does not arrive", "cond pairs are [master field, detail field].", ""),
    "JNR_COND_SWAPPED": ("WARN", "join condition pair looks swapped", "cond pairs are [master field, detail field].", ""),
    "JNR_COLLISION": ("ERROR", "master and detail carry the same field name", "Rename or exclude on one side's link (the output keeps only one).", ""),
    "JNR_SAME_SOURCE": ("ERROR", "master and detail come from the same source", "One source on both sides hangs the session with no error; same-pipeline branches need 'sorted': true plus Sorters on both sides.", "L-CDI-106"),
    "JNR_SAME_SOURCE_SORTED": ("WARN", "same-source join is sorted but a side has no Sorter", "Put a Sorter on both branches before the Joiner.", "L-CDI-106"),
    "JNR_SIDES": ("WARN", "joiner master/detail keys disagree with the links", "The links decide; fix the informational master/detail keys.", ""),
    "AGG_GROUPBY": ("ERROR", "aggregator groupBy field does not arrive", "", ""),
    "AGG_NONAGG": ("WARN", "aggregate port uses a non-grouped field outside an aggregate function", "That returns an arbitrary row's value per group.", ""),
    "AGG_PASSTHROUGH": ("INFO", "non-grouped fields passed through an aggregator are used downstream", "They carry the last row's value of each group: deterministic only with sorted input (put a Sorter before the Aggregator) or values constant per group.", ""),
    "SRT_KEY": ("ERROR", "sorter key does not arrive", "", ""),
    "RNK_FIELD": ("ERROR", "rank field / groupBy does not arrive", "", ""),
    "RNK_N": ("ERROR", "rank n is not a positive integer", "", ""),
    "SEQ_START": ("WARN", "sequence start value other than 1", "A probe showed the start value ignored (NEXTVAL began at 1): add an offset in an expression.", ""),
    "RTR_GROUPS": ("ERROR", "router groups missing, duplicated or named DEFAULT1", "groups: [[NAME, condition], ...]; DEFAULT1 is added for unmatched rows.", ""),
    "UNI_INPUTS": ("ERROR", "union needs at least two inputs", "", ""),
    "UNI_FIELD": ("ERROR", "union input does not provide a mapped field", "Each input group must carry every output field (or map it: map {input: {out: in}}).", ""),
    "MSK_FIELD": ("ERROR", "masking entry or passthrough field does not arrive / cannot be restored", "Entries mask fields that arrive; passthrough is true or a list of arriving fields ([name, TYPE, ...] only where the upstream cannot be derived).", ""),
    "MSK_TYPE": ("ERROR", "masking entry the compiler refuses", "type is a technique of the Mapping Designer's rule catalogue (MASKING_TYPES in nodes/masking.py: Email address, Phone, SSN, Credit card, Key, Random, Substitution name, URL, ...); pc, the rule's data type, is the masked field's platform type (leave it out); prec/scale are whole numbers, scale <= prec; a parameter without a default needs data.", ""),
    "DQ_ASSET": ("ERROR", "DQ asset not listed in spec.assets", "Rule specifications, cleanses and dedupes must be packaged as references (spec.assets with guid, name, type, path).", ""),
    "DQ_INPUT": ("ERROR", "DQ transformation input field does not arrive", "", ""),
    "DDP_MAP": ("ERROR", "dedup map is invalid", "map {dedup input: incoming field}; GroupKey and Person_Name are mandatory.", ""),
}

Issue = namedtuple("Issue", "code severity node message hint lesson")

LEGACY_TYPES = ["source", "target", "expression", "filter", "router", "sorter", "joiner", "aggregator", "union", "lookup",
                "masking", "rulespec", "cleanse", "dedup", "rank", "sequence", "generic"]
KNOWN_KINDS = {"BQ", "PG", "JDBC", "FF", "SF"}
FALLBACK_TYPES = {"STRING", "INTEGER", "NUMERIC", "FLOAT", "TIMESTAMP", "DATE", "BOOLEAN", "INT32"}
NUMERIC_OR_DATE = {"INTEGER", "INT32", "NUMERIC", "FLOAT", "TIMESTAMP", "DATE"}
TGT_OPS = {"insert", "update", "upsert", "delete", "data driven", "datadriven", "data_driven", "rowbased"}   # = _OP_NAMES
WINDOW_FUNCS = {"LAG", "LEAD", "FIRST_VALUE", "LAST_VALUE", "NTH_VALUE", "ROW_NUMBER", "DENSE_RANK", "PERCENT_RANK", "CUME_DIST", "NTILE"}


def _field_types():
    try:
        from . import types as _t
        return set(getattr(_t, "TYPES", {})) or FALLBACK_TYPES
    except Exception:
        return FALLBACK_TYPES


def _registered_types():
    """Node types the compiler knows (legacy list + registry + field rules)."""
    known = set(LEGACY_TYPES) | {k for k in ff.FLOWS if ":" not in k}
    try:
        from . import nodes as _nodes  # noqa: F401  (imports every node module -> registry)
        from .registry import NODES
        known |= set(NODES)
    except Exception:
        pass
    return known


CHECKS = defaultdict(list)


def check(type_name):
    """Register an extra per-node check: fn(ctx, nd) -> iterable of Issue (or None)."""
    def deco(fn):
        if fn not in CHECKS[type_name]:
            CHECKS[type_name].append(fn)
        return fn
    return deco


# ============================================================================== expression language
INFA_FUNCS = set("""
ABORT ABS ADD_TO_DATE AES_DECRYPT AES_ENCRYPT ASCII AVG CEIL CHOOSE CHR CHRCODE COMPRESS CONCAT CONVERT_BASE COS COSH COUNT
CRC32 CUME DATE_COMPARE DATE_DIFF DECODE DECOMPRESS DEC_BASE64 ENC_BASE64 ERROR EXP FIRST FLOOR FV GET_DATE_PART GREATEST
IIF IN INDEXOF INITCAP INSTR ISNULL IS_DATE IS_NUMBER IS_SPACES LAG LAST LAST_DAY LEAD LEAST LENGTH LN LOG LOWER LPAD LTRIM
MAKE_DATE_TIME MAX MD5 MEDIAN METAPHONE MIN MOD MOVINGAVG MOVINGSUM NPER PERCENTILE PMT POWER PV RAND RATE REG_EXTRACT
REG_MATCH REG_REPLACE REPLACECHR REPLACESTR REVERSE ROUND RPAD RTRIM SETCOUNTVARIABLE SETMAXVARIABLE SETMINVARIABLE
SETVARIABLE SET_DATE_PART SIGN SIN SINH SOUNDEX SQRT STDDEV SUBSTR SUM SYSTIMESTAMP TAN TANH TO_BIGINT TO_CHAR TO_DATE
TO_DECIMAL TO_FLOAT TO_INTEGER TRUNC UPPER VARIANCE TO_TIMESTAMP_TZ GET_TIMEZONE UUID4 UUID_NUMBER SHA256
""".split())
AGG_FUNCS = {"AVG", "COUNT", "FIRST", "LAST", "MAX", "MEDIAN", "MIN", "PERCENTILE", "STDDEV", "SUM", "VARIANCE"}
SQL_FUNCS = {
    "COALESCE": "IIF(ISNULL(a), b, a)", "NVL": "IIF(ISNULL(a), b, a)", "NVL2": "IIF(ISNULL(a), c, b)",
    "IFNULL": "IIF(ISNULL(a), b, a)", "NULLIF": "IIF(a = b, NULL, a)", "NOW": "SYSTIMESTAMP()",
    "CURRENT_TIMESTAMP": "SYSTIMESTAMP()", "CURRENT_DATE": "TRUNC(SYSTIMESTAMP(), 'DD')", "GETDATE": "SYSTIMESTAMP()",
    "SUBSTRING": "SUBSTR(s, start, len)", "LEN": "LENGTH(s)", "TRIM": "LTRIM(RTRIM(s))", "CAST": "TO_CHAR / TO_INTEGER / TO_DECIMAL / TO_DATE",
    "SAFE_CAST": "TO_CHAR / TO_INTEGER / TO_DECIMAL / TO_DATE", "DATE_TRUNC": "TRUNC(d, 'DD')", "DATEADD": "ADD_TO_DATE(d, 'DD', n)",
    "DATE_ADD": "ADD_TO_DATE(d, 'DD', n)", "TIMESTAMP_ADD": "ADD_TO_DATE(d, 'DD', n)", "DATEDIFF": "DATE_DIFF(d1, d2, 'DD')",
    "TIMESTAMP_DIFF": "DATE_DIFF(d1, d2, 'DD')", "EXTRACT": "GET_DATE_PART(d, 'YYYY')", "DATEPART": "GET_DATE_PART(d, 'YYYY')",
    "REGEXP_CONTAINS": "REG_MATCH(s, pattern)", "REGEXP_LIKE": "REG_MATCH(s, pattern)", "REGEXP_REPLACE": "REG_REPLACE(s, pattern, repl)",
    "REGEXP_EXTRACT": "REG_EXTRACT(s, pattern, n)", "REGEXP_SUBSTR": "REG_EXTRACT(s, pattern, n)", "SAFE_DIVIDE": "IIF(y = 0, NULL, x / y)",
    "CONCAT_WS": "a || sep || b", "STRPOS": "INSTR(s, sub)", "CHARINDEX": "INSTR(s, sub)", "POSITION": "INSTR(s, sub)",
    "LEFT": "SUBSTR(s, 1, n)", "RIGHT": "SUBSTR(s, -n)", "FORMAT_DATE": "TO_CHAR(d, 'YYYY-MM-DD')", "FORMAT_TIMESTAMP": "TO_CHAR(d, 'YYYY-MM-DD HH24:MI:SS')",
    "PARSE_DATE": "TO_DATE(s, 'YYYY-MM-DD')", "PARSE_TIMESTAMP": "TO_DATE(s, 'YYYY-MM-DD HH24:MI:SS')", "STARTS_WITH": "INSTR(s, p) = 1",
    "ENDS_WITH": "REG_MATCH(s, '.*suffix$')", "COUNTIF": "COUNT(x, condition)", "STRING_AGG": "(none: aggregate in SQL or a Sorter + expression)",
    "ARRAY_AGG": "(none)", "LISTAGG": "(none)", "TO_JSON_STRING": "(none)", "JSON_VALUE": "(none: parse in SQL or a Hierarchy Parser)",
}
SQL_WORDS = {"CASE": "DECODE(TRUE, cond1, v1, ..., default)", "WHEN": "DECODE(TRUE, ...)", "THEN": "DECODE(TRUE, ...)",
             "ELSE": "DECODE(TRUE, ...)", "END": "DECODE(TRUE, ...)", "BETWEEN": "x >= a AND x <= b", "LIKE": "REG_MATCH(s, pattern)",
             "IS": "ISNULL(x) / NOT ISNULL(x)", "AS": "(no aliases in expressions)", "SELECT": "(a query belongs in a source)",
             "FROM": "(a query belongs in a source)", "WHERE": "(a filter condition has no WHERE)", "EXISTS": "(none)"}
WORDS = {"AND", "OR", "NOT", "NULL", "TRUE", "FALSE", "DD_INSERT", "DD_UPDATE", "DD_DELETE", "DD_REJECT", "TC_CONTINUE_TRANSACTION",
         "TC_COMMIT_BEFORE", "TC_COMMIT_AFTER", "TC_ROLLBACK_BEFORE", "TC_ROLLBACK_AFTER", "SYSDATE", "SESSSTARTTIME",
         "WORKFLOWSTARTTIME", "PROC_RESULT", "SPOUTPUT"}

_TOK = re.compile(r"""
    (?P<ws>\s+)
  | (?P<comment>--[^\n]*|//[^\n]*)
  | (?P<str>'[^']*'?)
  | (?P<dq>"[^"]*"?)
  | (?P<num>\d+(?:\.\d*)?(?:[eE][+-]?\d+)?|\.\d+)
  | (?P<call>:(?i:LKP|SP|MCR|TD)\.[A-Za-z_][\w$#@]*)
  | (?P<param>\$\$?[A-Za-z_][\w$#@]*)
  | (?P<id>[A-Za-z_][\w$#@]*)
  | (?P<op>\|\||<>|!=|\^=|<=|>=|==|[-+*/%=<>(),.;:^!&])
  | (?P<bad>.)
""", re.X | re.S)

ExprScan = namedtuple("ExprScan", "refs funcs calls params problems")


def scan_expr(text):
    """Tokenize an Informatica expression -> field refs, function calls (NAME, argc), :LKP calls, $params, problems."""
    toks = [(m.lastgroup, m.group(), m.start()) for m in _TOK.finditer(text or "")]
    sig = [t for t in toks if t[0] not in ("ws", "comment")]
    refs, funcs, calls, params, problems = [], [], [], [], []
    depth = 0

    def argc(i):
        """Number of arguments of the call whose '(' is sig[i]."""
        d, n, any_tok = 0, 0, False
        for k in range(i, len(sig)):
            v = sig[k][1]
            if v == "(":
                d += 1
                if d == 1:
                    continue
            elif v == ")":
                d -= 1
                if d == 0:
                    return n + 1 if any_tok else 0
            elif v == "," and d == 1:
                n += 1
                continue
            if d >= 1:
                any_tok = True
        return n + 1 if any_tok else 0

    for i, (kind, val, pos) in enumerate(sig):
        nxt = sig[i + 1][1] if i + 1 < len(sig) else None
        prev = sig[i - 1] if i > 0 else None
        if kind == "op":
            if val == "(":
                depth += 1
            elif val == ")":
                depth -= 1
                if depth < 0:
                    problems.append(("EXPR_SYNTAX", "unbalanced ')' at %d" % pos))
                    depth = 0
            elif val == "==":
                problems.append(("EXPR_SQL_SYNTAX", "'==' (use '=')"))
        elif kind == "str":
            if len(val) < 2 or not val.endswith("'"):
                problems.append(("EXPR_SYNTAX", "unterminated string literal at %d" % pos))
            elif prev and prev[0] == "str" and prev[2] + len(prev[1]) == pos:
                problems.append(("EXPR_DOUBLED_QUOTE", "literal %s%s" % (prev[1], val)))
        elif kind == "dq":
            problems.append(("EXPR_DOUBLE_QUOTED", "double-quoted text %s" % val[:40]))
        elif kind == "bad":
            problems.append(("EXPR_SYNTAX", "unexpected character %r at %d" % (val, pos)))
        elif kind == "param":
            params.append(val)
        elif kind == "call":
            n = argc(i + 1) if nxt == "(" else 0
            calls.append((val.split(".", 1)[0][1:].upper(), val.split(".", 1)[1], n))
        elif kind == "id":
            up = val.upper()
            if nxt == "(" and up not in ("AND", "OR", "NOT"):
                if up == "IN" and prev and ((prev[0] == "id" and prev[1].upper() not in ("AND", "OR", "NOT"))
                                            or prev[0] in ("str", "num") or prev[1] == ")"):
                    problems.append(("EXPR_SQL_SYNTAX", "SQL-style 'x IN (...)' (use IN(x, v1, v2, ...))"))
                funcs.append((up, argc(i + 1), pos))
            elif up in WORDS:
                continue
            elif prev and prev[1] == "." and i > 1 and sig[i - 2][0] == "call":
                continue
            else:
                refs.append((val, pos))
    if depth > 0:
        problems.append(("EXPR_SYNTAX", "unbalanced '(' (%d open)" % depth))
    return ExprScan(refs, funcs, calls, params, problems)


# ============================================================================== SQL (query sources)
_SQL_WORD = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def sql_tokens(q):
    """Small GoogleSQL lexer: (kind, text, pos) with kinds word, quoted, str, num, comment, punct."""
    out, i, n = [], 0, len(q)
    while i < n:
        c = q[i]
        if c.isspace():
            i += 1
            continue
        if q.startswith("--", i) or c == "#":
            j = q.find("\n", i)
            j = n if j < 0 else j
            out.append(("comment", q[i:j], i)); i = j
            continue
        if q.startswith("/*", i):
            j = q.find("*/", i + 2)
            j = n if j < 0 else j + 2
            out.append(("comment", q[i:j], i)); i = j
            continue
        pre = ""
        if c in "rRbB" and i + 1 < n and (q[i + 1] in "'\"" or (q[i + 1] in "rRbB" and i + 2 < n and q[i + 2] in "'\"")):
            pre = q[i:i + (1 if q[i + 1] in "'\"" else 2)]
        k = i + len(pre)
        if k < n and q[k] in "'\"":
            qch = q[k]
            triple = q.startswith(qch * 3, k)
            end = qch * 3 if triple else qch
            j = k + len(end)
            while j < n and not q.startswith(end, j):
                j += 2 if q[j] == "\\" else 1
            j = min(n, j + len(end))
            out.append(("str", q[i:j], i)); i = j
            continue
        if c == "`":
            j = q.find("`", i + 1)
            j = n if j < 0 else j + 1
            out.append(("quoted", q[i:j], i)); i = j
            continue
        m = _SQL_WORD.match(q, i)
        if m:
            out.append(("word", m.group(), i)); i = m.end()
            continue
        m = re.match(r"\d+(?:\.\d*)?(?:[eE][+-]?\d+)?", q[i:])
        if m:
            out.append(("num", m.group(), i)); i += len(m.group())
            continue
        out.append(("punct", c, i)); i += 1
    return out


_SELECT_END = {"FROM", "WHERE", "GROUP", "HAVING", "QUALIFY", "WINDOW", "ORDER", "LIMIT", "UNION", "EXCEPT", "INTERSECT"}


def select_names(q):
    """Column names of the outermost SELECT list, or None when not determinable (*, AS STRUCT, no SELECT)."""
    toks = [t for t in sql_tokens(q) if t[0] != "comment"]
    depth, start = 0, None
    for i, (k, v, p) in enumerate(toks):
        if v == "(":
            depth += 1
        elif v == ")":
            depth -= 1
        elif depth == 0 and k == "word" and v.upper() == "SELECT":
            start = i + 1
            break
    if start is None:
        return None
    items, cur, depth = [], [], 0
    for k, v, p in toks[start:]:
        if v == "(":
            depth += 1
        elif v == ")":
            if depth == 0:
                break
            depth -= 1
        elif depth == 0 and k == "word" and v.upper() in _SELECT_END:
            break
        if depth == 0 and v == ",":
            items.append(cur); cur = []
            continue
        cur.append((k, v))
    items.append(cur)
    if items and items[0] and items[0][0][1].upper() in ("DISTINCT", "ALL"):
        items[0] = items[0][1:]
    if items and items[0] and items[0][0][1].upper() == "AS":     # SELECT AS STRUCT / AS VALUE
        return None
    names = []
    for it in items:
        if not it:
            continue
        vals = [v for _, v in it]
        if vals[0] == "*" or (len(vals) >= 2 and "*" in vals and vals[vals.index("*") - 1] == "."):
            return None
        ident = lambda kv: kv[0] in ("word", "quoted")
        unq = lambda s: s.strip("`")
        d, as_at = 0, None
        for j, (k, v) in enumerate(it):
            if v == "(":
                d += 1
            elif v == ")":
                d -= 1
            elif d == 0 and k == "word" and v.upper() == "AS":
                as_at = j
        if as_at is not None and as_at + 1 < len(it) and ident(it[as_at + 1]):
            names.append(unq(it[as_at + 1][1]))
        elif len(it) == 1 and ident(it[0]):
            names.append(unq(it[0][1]))
        elif len(it) >= 3 and ident(it[-1]) and it[-2][1] == "." and all(ident(x) or x[1] == "." for x in it):
            names.append(unq(it[-1][1]))
        elif len(it) >= 2 and ident(it[-1]) and (ident(it[-2]) or it[-2][1] == ")" or it[-2][0] in ("str", "num")) \
                and it[-1][1].upper() not in ("END", "NULL", "TRUE", "FALSE"):
            names.append(unq(it[-1][1]))          # implicit alias: expr name
        else:
            names.append(None)                   # unnamed expression (BigQuery calls it f0_)
    return names


# ============================================================================== context
class LintCtx:
    def __init__(self, spec, profile, allow_live):
        self.spec = spec
        self.profile = profile or {}
        self.allow_live = allow_live
        self.issues = []
        self.known_types = _registered_types()     # imports the node modules first: their @flow rules
        self.types = _field_types()
        self.an = ff.analyze(spec)
        self.conns = spec.get("connections") or {}
        self.jdbc_noted = set()
        self.agg_pass = defaultdict(set)

    def issue(self, code, node, message, severity=None, hint=None, lesson=None):
        sev, _title, h, les = CODES.get(code, ("WARN", code, "", ""))
        self.issues.append(Issue(code, severity or sev, node, message, h if hint is None else hint, les if lesson is None else lesson))

    def kind(self, nd):
        c = self.conns.get(nd.get("conn"))
        return (c or {}).get("kind", "BQ")

    def incoming(self, name, key=None):
        return self.an.incoming(name, key)


def _present(fields_, name):
    return fields_.find(name) is not None


# ============================================================================== profile + vars
# lint loads a spec with spec.prepare, the loader of spec.load_spec: the same profile choice, merge and ${VAR}
# substitution, so lint judges exactly the spec deploy would package (and refuses what load_spec refuses: every
# ${VAR} problem is an ERROR, except a template's undefined names with no profile at all, see _var_issues).
_VAR = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")      # kept for importers; lint no longer substitutes itself
_SHAPE_HINT = "load_spec refuses the spec as it is (see docs/SPEC_REFERENCE.md); lint checks nothing else until it is fixed."
_LOAD_HINT = "load_spec refuses the spec as it is (see docs/SPEC_REFERENCE.md)."
_VAR_HINT = "${NAME} is a variable (letters, digits, _); $${ is a literal ${; a list or object var only as a whole value."
_NO_PROFILE_HINT = ("No profile is in effect and the spec has its own orgGuid, folder and connections, so load_spec and build "
                    "refuse it as it is: define the name in the spec's own 'vars', or pass --profile with the profile that "
                    "defines it.")
_FOLDER_KEYS = ("project", "projectGuid", "name", "guid")
_CONN_KEYS = ("guid", "name", "repoHandle")


def _load_json(p):
    return specmod._read_json(p, "JSON file")


def _template(spec):
    """True when a (prepared) spec leaves to a profile something load_spec needs from one: orgGuid, a folder key, the
    connections, a connection a node uses, a connection's guid / name / repoHandle. Linted with no profile, each of
    those is an ERROR of its own (SPEC_PACKAGE_KEYS, CONN_UNKNOWN, CONN_INCOMPLETE, the load_spec gate)."""
    if not isinstance(spec, dict) or not spec.get("orgGuid"):
        return True
    folder, conns, nodes = spec.get("folder"), spec.get("connections"), spec.get("nodes")
    if not isinstance(folder, dict) or not all(folder.get(k) for k in _FOLDER_KEYS) or not isinstance(conns, dict):
        return True
    used = {nd["conn"] for nd in (nodes if isinstance(nodes, list) else []) if isinstance(nd, dict) and isinstance(nd.get("conn"), str)}
    return (any(a not in conns for a in used)
            or any(not isinstance(c, dict) or not all(c.get(k) for k in _CONN_KEYS) for c in conns.values()))


def _var_issues(prep):
    """[(code, message, hint)] for the ${VAR} problems of a prepared spec. An undefined name is an ERROR, VAR_UNKNOWN,
    as load_spec refuses the spec -- with a profile in effect, and also with none when the spec is self-contained (its
    own orgGuid, folder and connections). Only a template linted with no profile at all (no profile argument, no
    "profile" key, no default profile) gets INFO VAR_UNRESOLVED: the profile it needs may define the name, and lint
    fails it anyway for what it lacks without one (see _template). So a spec lint passes has no undefined name. Every
    other problem (a malformed placeholder, a var cycle, a list var inside text) is an ERROR."""
    out = []
    if prep.undefined:
        msg = ", ".join("${%s} (%s)" % (v, ", ".join(p or "(top level)" for p in prep.undefined[v][:3]))
                        for v in sorted(prep.undefined))
        if prep.profile:
            out.append(("VAR_UNKNOWN", msg, None))
        elif _template(prep.spec):
            out.append(("VAR_UNRESOLVED", msg, None))
        else:
            out.append(("VAR_UNKNOWN", msg, _NO_PROFILE_HINT))
    return out + [("VAR_UNKNOWN", m, _VAR_HINT) for m in prep.var_problems]


def effective_spec(spec, profile, vars=None):
    """The spec exactly as spec.load_spec merges and substitutes it (profile: dict or path, else the spec's own
    "profile" key) -> (spec, [(code, message)])."""
    prep = specmod.prepare(spec, profile=profile, vars=vars)
    return prep.spec, [(c, m) for c, m, _ in _var_issues(prep)]


# ============================================================================== checks
def _check_spec(ctx):
    sp = ctx.spec
    if not sp.get("name"):
        ctx.issue("SPEC_SHAPE", None, "spec has no name")
    elif sp.get("documentType") == "DMAPPLET":
        if not str(sp["name"]).startswith("mplt_"):
            ctx.issue("SPEC_NAME_CONVENTION", None, "mapplet name %r (mapplets: mplt_<x>)" % sp["name"])
    elif not str(sp["name"]).startswith("m_"):
        ctx.issue("SPEC_NAME_CONVENTION", None, "mapping name %r" % sp["name"])
    f = sp.get("folder") or {}
    missing = [k for k in ("project", "projectGuid", "name", "guid") if not f.get(k)]
    if missing or not sp.get("orgGuid"):
        ctx.issue("SPEC_PACKAGE_KEYS", None, "missing: %s" % ", ".join((["orgGuid"] if not sp.get("orgGuid") else []) + ["folder." + k for k in missing]))
    if sp.get("guid") and len(str(sp["guid"])) != 22:
        ctx.issue("SPEC_GUID", None, "guid %r has %d characters" % (sp["guid"], len(str(sp["guid"]))))
    for alias, c in (sp.get("connections") or {}).items():
        miss = [k for k in ("guid", "name", "repoHandle") if not (c or {}).get(k)]
        if miss:
            ctx.issue("CONN_INCOMPLETE", None, "connection %r missing %s" % (alias, ", ".join(miss)))
        if not (c or {}).get("kind"):
            ctx.issue("CONN_KIND_MISSING", None, "connection %r has no kind (treated as BigQuery)" % alias)
        elif c["kind"] not in KNOWN_KINDS:
            ctx.issue("CONN_KIND", None, "connection %r kind %r" % (alias, c.get("kind")))
    for a in sp.get("assets") or []:
        miss = [k for k in ("guid", "name", "type", "path") if not (a or {}).get(k)]
        if miss:
            ctx.issue("ASSET_INCOMPLETE", None, "asset %r missing %s" % ((a or {}).get("name") or (a or {}).get("guid"), ", ".join(miss)))
    if sp.get("flowOrder"):
        nodes = ctx.an.nodes
        for entry in sp["flowOrder"]:
            try:
                srcs, tgts = entry
            except (TypeError, ValueError):
                ctx.issue("FLOW_ORDER", None, "entry %r is not [[sources], [targets]]" % (entry,))
                continue
            for s in srcs:
                if (nodes.get(s) or {}).get("type") != "source":
                    ctx.issue("FLOW_ORDER", s, "flowOrder source %r is not a source node" % s)
            for t in tgts:
                if (nodes.get(t) or {}).get("type") != "target":
                    ctx.issue("FLOW_ORDER", t, "flowOrder target %r is not a target node" % t)
    guards = (ctx.profile.get("guards") or {})
    if not ctx.allow_live:
        fpath = "%s/%s" % (f.get("project", ""), f.get("name", ""))
        for pat in guards.get("protectedFolders") or []:
            if re.search(pat, fpath):
                ctx.issue("FOLDER_PROTECTED", None, "folder %s matches %r" % (fpath, pat))


def _check_fields_decl(ctx, nd, key="fields", allow_dict=False):
    # (no DATE rule: a DATE field is date/time + java.sql.Timestamp, as in every designer mapping, and runs on BigQuery
    # and PostgreSQL alike; the old TYPE_BQ_DATE ERROR came from the java.sql.Date the legacy generators wrote)
    seen = set()
    for fd in nd.get(key) or []:
        if isinstance(fd, dict) and allow_dict:
            name, typ = fd.get("name"), fd.get("type")
        elif isinstance(fd, (list, tuple)) and len(fd) >= 2:
            name, typ = fd[0], fd[1]
            if len(fd) > 2 and fd[2] is not None and not isinstance(fd[2], int):
                ctx.issue("FIELD_DECL", nd["name"], "field %r precision %r is not an integer" % (name, fd[2]))
        else:
            ctx.issue("FIELD_DECL", nd["name"], "field declaration %r" % (fd,))
            continue
        if not name or not isinstance(name, str):
            ctx.issue("FIELD_DECL", nd["name"], "field without a name: %r" % (fd,))
            continue
        if name.lower() in seen:
            ctx.issue("FIELD_DUP", nd["name"], "field %r declared twice" % name)
        seen.add(name.lower())
        if typ == "JSON":
            ctx.issue("TYPE_JSON", nd["name"], "field %r is JSON" % name)
        elif typ not in ctx.types:
            ctx.issue("TYPE_UNKNOWN", nd["name"], "field %r type %r" % (name, typ))


def _text(v):
    """A text slot as the build reads it (values.as_text: a number is its text); "" for a value the build refuses
    (the node module's lint_problems hook reports that one)."""
    from . import values
    try:
        return values.as_text(v, "", "")
    except specmod.SpecError:
        return ""


def _flag(nd, key, default=False):
    """A boolean option as the build reads it (values.as_flag: "false" is false); a value the build refuses counts
    as true here (the node's hook reports it)."""
    from . import values
    v = nd.get(key)
    return values.as_flag(v, "", default) if values.is_flag(v) else True


def _node_problems(module, ctx, nd):
    """[(code, message)] from ``lint_problems`` of the node module that builds ``nd`` (nodes/<module>.py): the build's
    own refusal rules, so lint reports exactly what the compiler refuses. Empty when the module cannot be loaded."""
    try:
        fn = importlib.import_module("%s.nodes.%s" % (_PKG, module)).lint_problems
    except Exception:           # no such hook (node modules that cannot be imported at all: EXTENSION_BROKEN)
        return []
    try:
        return list(fn(ctx.spec, nd, ctx.an, ctx.conns) or [])
    except Exception as e:      # an option of the wrong type the rules cannot even read: the build refuses it too
        return [("NODE_MALFORMED", "%s options cannot be read: %r" % (module, e))]


NODE_KEYS = ("type", "name", "set", "advanced")     # every node's keys; the rest are the options of its type


def builder_options(node_type):
    """The option names the builder of ``node_type`` reads besides NODE_KEYS (its ``options`` attribute), or None when
    the type has no builder or its builder declares none (then nothing checks its keys)."""
    try:
        fn = importlib.import_module(_PKG + ".registry").NODES.get(node_type)
    except Exception:           # no registry: nothing to check against
        return None
    opts = getattr(fn, "options", None)
    return frozenset(opts) if isinstance(opts, (set, frozenset, list, tuple)) else None


def _check_unknown_options(ctx, nd):
    """UNKNOWN_OPTION for each key of node ``nd`` that its builder does not read (builder_options): build ignores such a
    key without a word, so a misspelt option ("trunacte") silently keeps its default. The nearest option is named."""
    import difflib
    opts = builder_options(nd["type"])
    if opts is None:
        return
    known = sorted(opts) + list(NODE_KEYS)
    for k in nd:
        if k in NODE_KEYS or k in opts:
            continue
        near = difflib.get_close_matches(k, known, n=1, cutoff=0.6) if isinstance(k, str) else []
        ctx.issue("UNKNOWN_OPTION", nd["name"], "%s %r: unknown option %r%s; build ignores it (%s options: %s)"
                  % (nd["type"], nd["name"], k, " (did you mean %r?)" % near[0] if near else "", nd["type"],
                     ", ".join(sorted(opts)) or "none"))


def _check_nodes_and_links(ctx):
    an = ctx.an
    for name in an.dups:
        ctx.issue("NODE_DUP_NAME", name, "node %r appears more than once" % name)
    for nd in ctx.spec.get("nodes") or []:
        if not isinstance(nd, dict) or not nd.get("type") or not nd.get("name"):
            ctx.issue("SPEC_SHAPE", None, "node without type/name: %s" % json.dumps(nd)[:120])
            continue
        if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", nd["name"]):
            ctx.issue("NODE_NAME", nd["name"], "name %r" % nd["name"],
                      severity="ERROR" if "." in nd["name"] or " " in nd["name"] else "WARN")
        if nd["type"] not in ctx.known_types:
            ctx.issue("NODE_TYPE_UNKNOWN", nd["name"], "type %r (known: %s)" % (nd["type"], ", ".join(sorted(ctx.known_types))))
        else:
            if ff.rule_key(nd) not in ff.FLOWS:
                ctx.issue("NODE_UNCHECKED", nd["name"], "type %r" % nd["type"])
            _check_unknown_options(ctx, nd)
        if nd.get("conn") is not None and nd["conn"] not in ctx.conns:
            ctx.issue("CONN_UNKNOWN", nd["name"], "conn %r (have: %s)" % (nd["conn"], ", ".join(sorted(ctx.conns)) or "none"))
    for i in an.bad_links:
        ctx.issue("LINK_SHAPE", None, "link #%d %r" % (i, ctx.spec["links"][i]))
    per_key = Counter()
    for lk in an.links:
        f_ok, fg_ok, t_ok, tg_ok = an.known_link(lk)
        label = "%s -> %s" % (lk.frm, lk.to)
        if not f_ok:
            ctx.issue("LINK_FROM_UNKNOWN", lk.frm_node, label)
        elif not fg_ok:
            fp = ff.ports_of(an.nodes[lk.frm_node])
            ctx.issue("LINK_FROM_GROUP", lk.frm_node, "%s (outputs: %s)" % (label, ", ".join(repr(lk.frm_node + ("." + s if s else "")) for s in fp[1]) or "none"))
        if not t_ok:
            ctx.issue("LINK_TO_UNKNOWN", lk.to_node, label)
        elif not tg_ok:
            tp = ff.ports_of(an.nodes[lk.to_node])
            ctx.issue("LINK_TO_GROUP", lk.to_node, "%s (inputs: %s)" % (label, ", ".join(repr(lk.to_node + s) for s in tp[0]) or "none"))
        if not isinstance(lk.rule, (type(None), list, dict)):
            ctx.issue("LINK_SHAPE", lk.to_node, "%s rule %r is not a list or dict" % (label, lk.rule))
        elif isinstance(lk.rule, dict) and "exclude" in lk.rule and not ff.is_exclude_rule(lk.rule):
            ctx.issue("LINK_RULE_AMBIGUOUS", lk.to_node, "%s: rule has 'exclude' %s" % (label,
                      "beside %d rename(s)" % (len(lk.rule) - 1) if len(lk.rule) > 1 else "mapped to %r" % lk.rule["exclude"]))
        per_key[lk.to] += 1
    for key, n in per_key.items():
        if n > 1 and key.split(".")[0] in an.nodes:
            ctx.issue("LINK_MULTI_IN", key.split(".")[0], "%d links into %r" % (n, key))
    for lk, missing in an.rule_missing:
        ctx.issue("LINK_RULE_FIELD", lk.to_node, "%s -> %s: %s not upstream" % (lk.frm, lk.to, ", ".join(map(repr, missing))))
    if an.cycle_nodes:
        ctx.issue("LINK_CYCLE", None, "nodes on or after a cycle: %s" % ", ".join(an.cycle_nodes))
    # linkage
    for name, nd in an.nodes.items():
        ports = ff.ports_of(nd)
        if ports is None:
            continue
        ins, outs = ports
        linked_in = {lk.to for lk in an.in_links.get(name, [])}
        if ins and not linked_in:
            ctx.issue("NODE_NO_INPUT", name, "%s %r has no incoming link" % (nd["type"], name))
        elif len(ins) > 1:
            for sfx in ins:
                if name + sfx not in linked_in:
                    ctx.issue("NODE_INPUT_MISSING", name, "%r is not linked" % (name + sfx))
        if outs and not an.out_links.get(name):
            ctx.issue("NODE_NO_OUTPUT", name, "%s %r has no outgoing link" % (nd["type"], name))


def _sql_checks(ctx, nd, q):
    bad = sorted({c for c in q if ord(c) > 127})
    if bad:
        ctx.issue("SQL_NON_ASCII", nd["name"], "characters %s" % "".join(bad)[:20])
    toks = sql_tokens(q)
    if any(k == "comment" for k, _, _ in toks):
        ctx.issue("SQL_COMMENT", nd["name"], "query contains a comment")
    semis = [p for k, v, p in toks if k == "punct" and v == ";"]
    if semis:
        ctx.issue("SQL_TRAILING_SEMICOLON", nd["name"], "';' at offset %s" % ", ".join(map(str, semis[:3])))


def _check_source(ctx, nd):
    q, obj = nd.get("query"), nd.get("object")
    k = ctx.kind(nd)
    if not q and not obj:
        ctx.issue("SRC_NO_OBJECT", nd["name"], "source %r" % nd["name"])
    if q and obj:
        ctx.issue("SRC_QUERY_AND_OBJECT", nd["name"], "query and object %r" % obj)
    if not nd.get("fields"):
        ctx.issue("SRC_NO_FIELDS", nd["name"], "source %r" % nd["name"])
    _check_fields_decl(ctx, nd)
    if q:
        _sql_checks(ctx, nd, q)
        names = select_names(q)
        decl = [fd[0] for fd in nd.get("fields") or [] if isinstance(fd, (list, tuple)) and fd]
        if names is not None and decl:
            have = {n.lower() for n in names if n}
            missing = [d for d in decl if d.lower() not in have]
            if missing:
                unnamed = sum(1 for n in names if n is None)
                ctx.issue("SQL_FIELDS", nd["name"], "declared but not selected: %s%s" % (", ".join(missing[:12]),
                          " (+%d unnamed SELECT expressions)" % unnamed if unnamed else ""))
            dl = {d.lower() for d in decl}
            extra = [n for n in names if n and n.lower() not in dl]
            if extra:
                ctx.issue("SQL_FIELDS_EXTRA", nd["name"], "selected, not declared: %s" % ", ".join(extra[:12]))
    elif obj:
        _check_object_path(ctx, nd, obj, k, source=True)
    if k == "BQ":
        implicit = [fd[0] for fd in nd.get("fields") or [] if isinstance(fd, (list, tuple)) and len(fd) >= 2
                    and fd[1] == "STRING" and (len(fd) < 3 or fd[2] is None)]
        if implicit:
            ctx.issue("BQ_STRING_PRECISION", nd["name"], "%d STRING field(s) at 4000: %s" % (len(implicit), ", ".join(implicit[:8])))
        wide = ["%s(%d)" % (fd[0], fd[2]) for fd in nd.get("fields") or [] if isinstance(fd, (list, tuple)) and len(fd) >= 3
                and fd[1] == "STRING" and isinstance(fd[2], int) and fd[2] > 256]
        if wide:      # deliberate for long text, so only INFO
            ctx.issue("BQ_STRING_PRECISION", nd["name"], "explicit precision > 256 (fine for long text, costs reader memory): %s"
                      % ", ".join(wide[:8]), severity="INFO")


def _check_object_path(ctx, nd, obj, kind, source):
    parts = obj.split("/")
    if kind in ("PG", "JDBC"):
        ok = (len(parts) == 2 and all(parts)) or (len(parts) == 3 and parts[1] in ("TABLE", "VIEW") and parts[0] and parts[2])
        if not ok or "." in parts[0]:
            ctx.issue("PG_OBJECT_PATH", nd["name"], "object %r" % obj)
        if not source and len(parts) == 3 and parts[1] == "VIEW":
            ctx.issue("TGT_VIEW", nd["name"], "object %r" % obj)
    elif kind == "BQ":
        if len(parts) != 2 or not all(parts) or "." in parts[1]:
            ctx.issue("BQ_OBJECT_PATH", nd["name"], "object %r" % obj)


def _check_target(ctx, nd):
    name, k = nd["name"], ctx.kind(nd)
    obj = nd.get("object") or ""
    if not obj:
        ctx.issue("NODE_MALFORMED", name, "target %r has no object" % name)
    else:
        _check_object_path(ctx, nd, obj, k, source=False)
    if not nd.get("fields"):
        ctx.issue("TGT_NO_FIELDS", name, "target %r" % name)
    _check_fields_decl(ctx, nd)
    inc = ctx.incoming(name)
    tfields = [fd for fd in nd.get("fields") or [] if isinstance(fd, (list, tuple)) and len(fd) >= 2]
    if ctx.an.in_links.get(name):
        missing, case_only = [], []
        for fd in tfields:
            exact = next((f for f in inc if f.name == fd[0]), None)
            if exact is None:
                ci = inc.find(fd[0])
                if ci is not None:
                    case_only.append("%s (upstream %s)" % (fd[0], ci.name))
                else:
                    missing.append(fd[0])
                    continue
            src = exact or inc.find(fd[0])
            if src.type == "STRING" and fd[1] in NUMERIC_OR_DATE:
                ctx.issue("TGT_TYPE_COERCE", name, "%s: STRING from %s into %s" % (fd[0], src.origin, fd[1]))
            _note_agg_pass(ctx, name, src)
        if missing:
            if inc.unchecked:
                ctx.issue("TGT_FIELD_UNCHECKED", name, "not verifiable: %s" % ", ".join(missing[:12]))
            else:
                ctx.issue("TGT_FIELD_UNPRODUCED", name, "%d field(s) never arrive: %s" % (len(missing), ", ".join(missing[:15])))
        if case_only:
            ctx.issue("TGT_FIELD_CASE", name, ", ".join(case_only[:10]))
    op = _target_op(nd)
    if op is None:
        op = "Insert"                   # (only to read the rules below; build refuses the value)
        ctx.issue("TGT_OP", name, "op %r: build refuses it" % (nd.get("op"),))
    keys = nd.get("updateColumns") or []
    tnames = {fd[0].lower() for fd in tfields}
    if op.lower() in ("update", "upsert", "delete", "data driven") and (not keys or any(c.lower() not in tnames for c in keys)):
        ctx.issue("TGT_KEYS", name, "op %s updateColumns %r" % (op, keys))
    bq_only = [key for key in ("oprAttrs", "rtAttrs", "extra_opr", "extra_rt", "disposition", "poll") if nd.get(key)]
    if k == "BQ":
        for code, msg in _node_problems("target", ctx, nd):     # BQ_TGT_POLL ("poll": false), an invalid "poll"
            ctx.issue(code, name, msg)
        if nd.get("pre_sql") or nd.get("preSQL") or nd.get("post_sql") or nd.get("postSQL"):
            ctx.issue("BQ_TGT_SQL", name, "pre/post SQL on %r" % obj)
        if nd.get("disposition") == "NONE":
            ctx.issue("BQ_TGT_DML", name, "disposition NONE")
        elif not _flag(nd, "truncate") and not nd.get("disposition") and op.lower() == "insert":
            ctx.issue("BQ_TGT_APPEND", name, "no truncate and no disposition -> Write append")
    elif bq_only:
        ctx.issue("TGT_ATTRS_IGNORED", name, "%s on a %s target" % (", ".join(bq_only), k))
    if k == "PG":
        if _flag(nd, "truncate") or nd.get("preSQL") or nd.get("pre_sql") or nd.get("postSQL") or nd.get("post_sql"):
            ctx.issue("TGT_PG_TRUNCATE", name, "truncate/pre/post SQL on %r" % obj)
        if op.lower() == "upsert":
            ctx.issue("TGT_PG_UPSERT", name, "Upsert on %r keyed %r" % (obj, keys))
    if k == "JDBC":
        if _flag(nd, "truncate"):
            ctx.issue("TGT_JDBC_TRUNCATE", name, "truncate on %r" % obj)
        if nd.get("conn") not in ctx.jdbc_noted:
            ctx.jdbc_noted.add(nd.get("conn"))
            ctx.issue("TGT_JDBC_DATABASE", name, "connection %r: objects like %r land in its bound database" % (nd.get("conn"), obj))
    if not ctx.allow_live:
        cname = (ctx.conns.get(nd.get("conn")) or {}).get("name", "")
        for pat in (ctx.profile.get("guards") or {}).get("protectedTargets") or []:
            cands = [obj, "%s:%s" % (nd.get("conn"), obj), "%s:%s" % (cname, obj)]
            if any(re.search(pat, c) for c in cands):
                ctx.issue("TGT_PROTECTED", name, "%r matches %r" % (obj, pat))
                break


_OP_NAMES = {"insert": "Insert", "update": "Update", "upsert": "Upsert", "delete": "Delete", "data driven": "Data Driven",
             "datadriven": "Data Driven", "data_driven": "Data Driven", "rowbased": "Data Driven"}


def _target_op(nd):
    """The write operation of target ``nd`` as the build reads it (nodes/target.py, target_ops.write_op): "op" absent or
    null is Data Driven when the target has an updateStrategy, else Insert; any other "op" is its text, trimmed, in any
    case (Rowbased, datadriven and data_driven are Data Driven) -> "Insert" | "Update" | "Upsert" | "Delete" |
    "Data Driven", or None for a value the build refuses ("" too). A value that is not text at all ("op": true) is
    the node's lint hook's NODE_MALFORMED: Insert here."""
    from . import values
    raw = nd.get("op")
    if raw is None:
        return "Data Driven" if _text(nd.get("updateStrategy")) else "Insert"
    try:
        text = values.as_text(raw, "")
    except specmod.SpecError:
        return "Insert"
    return _OP_NAMES.get(text.strip().lower())


def _targets_same_object(ctx):
    seen = defaultdict(list)
    for nd in ctx.an.nodes.values():
        if nd.get("type") == "target" and _flag(nd, "truncate"):
            seen[(nd.get("conn"), nd.get("object"))].append(nd["name"])
    for (conn, obj), names in seen.items():
        if len(names) > 1:
            ctx.issue("TGT_SAME_OBJECT", names[0], "%s all truncate %s" % (", ".join(names), obj))


def _refs_check(ctx, nd, text, namespace, label, extra_ok=()):
    """Field references of one expression text against a Fields namespace (+ extra names)."""
    sc = scan_expr(text)
    for code, msg in sc.problems:
        ctx.issue(code, nd["name"], "%s: %s" % (label, msg))
    ok = {n.lower() for n in extra_ok}
    unknown = []
    for ref, _pos in sc.refs:
        if ref.lower() in ok or namespace.find(ref) is not None:
            continue
        up = ref.upper()
        if up in SQL_WORDS:
            ctx.issue("EXPR_SQL_SYNTAX", nd["name"], "%s: %s (use %s)" % (label, up, SQL_WORDS[up]))
            continue
        unknown.append(ref)
    if unknown:
        if namespace.unchecked:
            ctx.issue("EXPR_FIELD_UNCHECKED", nd["name"], "%s: %s" % (label, ", ".join(sorted(set(unknown)))))
        else:
            ctx.issue("EXPR_FIELD_UNKNOWN", nd["name"], "%s: %s" % (label, ", ".join(sorted(set(unknown)))))
    for fn, argc, _pos in sc.funcs:
        if fn in SQL_FUNCS and fn not in INFA_FUNCS:
            ctx.issue("EXPR_SQL_FUNCTION", nd["name"], "%s: %s() (use %s)" % (label, fn, SQL_FUNCS[fn]))
        elif fn == "ISNULL" and argc > 1:
            ctx.issue("EXPR_SQL_FUNCTION", nd["name"], "%s: ISNULL with %d arguments (Informatica ISNULL(x) takes one; use IIF(ISNULL(a), b, a))" % (label, argc))
        elif fn not in INFA_FUNCS:
            ctx.issue("EXPR_FUNCTION_UNKNOWN", nd["name"], "%s: %s()" % (label, fn))
    declared = {"$$" + str(x.get("name", "")).lower() for x in ctx.spec.get("inOutParameters") or [] if isinstance(x, dict)}
    for p in sc.params:
        if p.startswith("$$") and p.lower() not in declared:
            ctx.issue("EXPR_PARAM", nd["name"], "%s: %s" % (label, p))
    for fn, argc, _pos in sc.funcs:
        if fn in WINDOW_FUNCS:
            ctx.issue("EXPR_WINDOW_FN", nd["name"], "%s: %s()" % (label, fn))
    for kind_, lname, argc in sc.calls:
        if kind_ != "LKP":
            continue
        lk = next((n for n in ctx.an.nodes.values() if n.get("type") == "lookup" and not _flag(n, "connected")
                   and n["name"].lower() == lname.lower()), None)
        if lk is None:
            ctx.issue("EXPR_LKP_UNKNOWN", nd["name"], "%s: :LKP.%s" % (label, lname))
        else:
            ctx.lkp_called.add(lk["name"])
            ctx.lkp_callers[lk["name"]].add(nd["name"])
            want = len(lk.get("cond") or [])
            if argc != want:
                ctx.issue("EXPR_LKP_ARITY", nd["name"], "%s: :LKP.%s(%d args), lookup has %d condition(s)" % (label, lname, argc, want))
    return sc


def _check_expression(ctx, nd):
    name = nd["name"]
    ports = [f for f in nd.get("fields") or [] if isinstance(f, dict)]
    if not nd.get("fields"):
        ctx.issue("EXPR_NO_PORTS", name, "expression %r" % name)
    _check_fields_decl(ctx, nd, allow_dict=True)
    inc = ctx.incoming(name)
    var_order = [p["name"] for p in ports if str(p.get("kind", "OUTPUT")).upper() == "VARIABLE"]
    outputs = {p["name"].lower(): p["name"] for p in ports if str(p.get("kind", "OUTPUT")).upper() != "VARIABLE"}
    for p in ports:
        kind = str(p.get("kind", "OUTPUT")).upper()
        if kind not in ("OUTPUT", "VARIABLE"):
            ctx.issue("EXPR_PORT_KIND", name, "port %r kind %r" % (p.get("name"), p.get("kind")))
        if "expr" not in p:
            ctx.issue("NODE_MALFORMED", name, "port %r has no expr" % p.get("name"))
            continue
        if inc.find(p["name"]) is not None and not inc.unchecked:
            ctx.issue("EXPR_PORT_CONFLICT", name, "port %r and incoming field %r" % (p["name"], inc.find(p["name"]).name))
        sc = scan_expr(_text(p["expr"]))
        refs = {r.lower() for r, _ in sc.refs}
        if kind != "VARIABLE":
            others = [outputs[r] for r in refs if r in outputs and r != p["name"].lower() and inc.find(r) is None]
            if others:
                ctx.issue("EXPR_OUTPUT_REF", name, "port %r uses OUTPUT port(s) %s" % (p["name"], ", ".join(sorted(others))))
            if p["name"].lower() in refs and inc.find(p["name"]) is None:
                ctx.issue("EXPR_SELF_REF", name, "port %r" % p["name"])
        else:
            later = [v for v in var_order[var_order.index(p["name"]) + 1:] if v.lower() in refs]
            if later or (p["name"].lower() in refs and inc.find(p["name"]) is None):
                ctx.issue("EXPR_VAR_FORWARD", name, "variable %r reads %s" % (p["name"], ", ".join(later) or "itself (previous row)"))
        _refs_check(ctx, nd, _text(p["expr"]), inc, "port %s" % p["name"], extra_ok=var_order + list(outputs.values()))


def _check_filter(ctx, nd):
    if nd.get("cond") is None or nd.get("cond") == "":
        ctx.issue("NODE_MALFORMED", nd["name"], "filter without cond")
        return
    _refs_check(ctx, nd, _text(nd["cond"]), ctx.incoming(nd["name"]), "cond")


def _check_router(ctx, nd):
    groups = nd.get("groups") or []
    names = [g[0] for g in groups if isinstance(g, (list, tuple)) and g]
    if not groups or len(names) != len(set(n.upper() for n in names)) or "DEFAULT1" in [n.upper() for n in names] \
            or any(not (isinstance(g, (list, tuple)) and len(g) == 2) for g in groups):
        ctx.issue("RTR_GROUPS", nd["name"], "groups %r" % (groups,))
    inc = ctx.incoming(nd["name"])
    for g in groups:
        if isinstance(g, (list, tuple)) and len(g) == 2:
            _refs_check(ctx, nd, _text(g[1]), inc, "group %s" % g[0])


def _check_sorter(ctx, nd):
    inc = ctx.incoming(nd["name"])
    keys = nd.get("keys") or []
    if not keys:
        ctx.issue("NODE_MALFORMED", nd["name"], "sorter without keys")
    miss = [k for k in keys if not _present(inc, k.lstrip("-"))]
    if miss:
        ctx.issue("SRT_KEY" if not inc.unchecked else "EXPR_FIELD_UNCHECKED", nd["name"], "keys %s" % ", ".join(miss))


def _check_joiner(ctx, nd):
    name = nd["name"]
    if nd.get("join", "NORMAL") not in ("NORMAL", "MASTER_OUTER", "DETAIL_OUTER", "FULL_OUTER"):
        ctx.issue("JNR_TYPE", name, "join %r" % nd.get("join"))
    m, d = ctx.incoming(name, name + ".Master"), ctx.incoming(name, name + ".Detail")
    cond = nd.get("cond") or []
    if not cond:
        ctx.issue("NODE_MALFORMED", name, "joiner without cond")
    for pair in cond:
        if not (isinstance(pair, (list, tuple)) and len(pair) == 2):
            ctx.issue("NODE_MALFORMED", name, "cond pair %r" % (pair,))
            continue
        l, r = pair
        if _present(m, l) and _present(d, r):
            continue
        if _present(d, l) and _present(m, r):
            ctx.issue("JNR_COND_SWAPPED", name, "[%r, %r]: %r is on the detail side, %r on the master side" % (l, r, l, r))
            continue
        if m.unchecked or d.unchecked:
            ctx.issue("EXPR_FIELD_UNCHECKED", name, "cond [%r, %r]" % (l, r))
            continue
        bad = ([("master", l)] if not _present(m, l) else []) + ([("detail", r)] if not _present(d, r) else [])
        ctx.issue("JNR_COND", name, "; ".join("%s field %r does not arrive" % b for b in bad))
    coll = sorted({f.name for f in d if m.find(f.name) is not None})
    if coll:
        ctx.issue("JNR_COLLISION", name, "both sides carry: %s" % ", ".join(coll[:15]))
    ml = [lk.frm_node for lk in ctx.an.in_links.get(name, []) if lk.to == name + ".Master"]
    dl = [lk.frm_node for lk in ctx.an.in_links.get(name, []) if lk.to == name + ".Detail"]
    if (nd.get("master") and ml and nd["master"] not in ml) or (nd.get("detail") and dl and nd["detail"] not in dl):
        ctx.issue("JNR_SIDES", name, "keys master=%r detail=%r, links master<-%s detail<-%s" % (nd.get("master"), nd.get("detail"), ml, dl))
    # one source on both sides (L-CDI-106)
    up_m, up_d = ctx.an.ancestors(name, name + ".Master"), ctx.an.ancestors(name, name + ".Detail")
    is_src = lambda n: (ctx.an.nodes.get(n) or {}).get("type") == "source"
    shared = {n for n in up_m & up_d if is_src(n)}
    if shared:
        if not _flag(nd, "sorted"):     # as the build reads it: "sorted": "false" is an unsorted join (it hangs)
            ctx.issue("JNR_SAME_SOURCE", name, "shared source(s): %s" % ", ".join(sorted(shared)))
        else:
            def side_has_sorter(side):
                return any((ctx.an.nodes.get(n) or {}).get("type") == "sorter" and ctx.an.ancestors(n) & shared for n in side)
            if not (side_has_sorter(up_m) and side_has_sorter(up_d)):
                ctx.issue("JNR_SAME_SOURCE_SORTED", name, "shared source(s): %s" % ", ".join(sorted(shared)))


def _check_aggregator(ctx, nd):
    name = nd["name"]
    inc = ctx.incoming(name)
    gb = nd.get("groupBy") or []
    miss = [g for g in gb if not _present(inc, g)]
    if miss:
        ctx.issue("AGG_GROUPBY" if not inc.unchecked else "EXPR_FIELD_UNCHECKED", name, "groupBy %s" % ", ".join(miss))
    _check_fields_decl(ctx, nd, allow_dict=True)
    gbl = {g.lower() for g in gb}
    outs = {f.get("name", "").lower() for f in nd.get("fields") or [] if isinstance(f, dict)}
    for f in nd.get("fields") or []:
        if not isinstance(f, dict) or "expr" not in f:
            ctx.issue("NODE_MALFORMED", name, "aggregate field %r without expr" % (f,))
            continue
        if inc.find(f["name"]) is not None and f["name"].lower() not in gbl and not inc.unchecked:
            ctx.issue("EXPR_PORT_CONFLICT", name, "aggregate %r and incoming field %r" % (f["name"], inc.find(f["name"]).name))
        sc = _refs_check(ctx, nd, _text(f["expr"]), inc, "aggregate %s" % f["name"])
        # a field outside every aggregate function call, not grouped -> arbitrary row
        outside = _refs_outside_aggs(_text(f["expr"]))
        loose = sorted({r for r in outside if r.lower() not in gbl and r.lower() not in outs and inc.find(r) is not None})
        if loose:
            ctx.issue("AGG_NONAGG", name, "aggregate %r uses %s outside an aggregate function" % (f["name"], ", ".join(loose)))


def _refs_outside_aggs(text):
    """Field refs of an expression that are not inside SUM(...)/COUNT(...)/... calls."""
    toks = [(m.lastgroup, m.group()) for m in _TOK.finditer(text or "") if m.lastgroup not in ("ws", "comment")]
    out, depth, agg_depth = [], 0, []
    for i, (k, v) in enumerate(toks):
        nxt = toks[i + 1][1] if i + 1 < len(toks) else None
        if k == "op" and v == "(":
            depth += 1
        elif k == "op" and v == ")":
            if agg_depth and agg_depth[-1] == depth:
                agg_depth.pop()
            depth -= 1
        elif k == "id":
            up = v.upper()
            if nxt == "(":
                if up in AGG_FUNCS:
                    agg_depth.append(depth + 1)
            elif up not in WORDS and not agg_depth:
                out.append(v)
    return out


def _check_rank(ctx, nd):
    inc = ctx.incoming(nd["name"])
    miss = [x for x in [nd.get("by")] + list(nd.get("groupBy") or []) if not x or not _present(inc, x)]
    if miss:
        ctx.issue("RNK_FIELD" if not inc.unchecked else "EXPR_FIELD_UNCHECKED", nd["name"], "fields %s" % ", ".join(map(repr, miss)))
    try:
        ok = int(nd.get("n", 1)) >= 1
    except (TypeError, ValueError):
        ok = False
    if not ok:
        ctx.issue("RNK_N", nd["name"], "n %r" % nd.get("n"))
    if inc.find("RANKINDEX") is not None and not inc.unchecked:
        ctx.issue("EXPR_PORT_CONFLICT", nd["name"], "RANKINDEX already arrives (two ranks in a row?)")


def _check_sequence(ctx, nd):
    if str(nd.get("start", 1)) != "1":
        ctx.issue("SEQ_START", nd["name"], "start %r" % nd.get("start"))
    inc = ctx.incoming(nd["name"])
    if (inc.find("NEXTVAL") is not None or inc.find("CURRVAL") is not None) and not inc.unchecked:
        ctx.issue("EXPR_PORT_CONFLICT", nd["name"], "NEXTVAL/CURRVAL already arrive (two sequences in a row?)")


def _check_union(ctx, nd):
    name = nd["name"]
    ins = nd.get("inputs") or []
    if len(ins) < 2:
        ctx.issue("UNI_INPUTS", name, "inputs %r" % ins)
    _check_fields_decl(ctx, nd)
    mp = nd.get("map") or {}
    for g in mp:
        if g not in ins:
            ctx.issue("NODE_MALFORMED", name, "map names input %r, not in inputs %r" % (g, ins))
    for g in ins:
        inc = ctx.incoming(name, name + "." + g)
        if inc.unchecked or not ctx.an.in_links.get(name):
            continue
        if not any(lk.to == name + "." + g for lk in ctx.an.in_links.get(name, [])):
            continue
        miss = []
        for fd in nd.get("fields") or []:
            out_name = fd[0] if isinstance(fd, (list, tuple)) else fd.get("name")
            src = (mp.get(g) or {}).get(out_name, out_name)
            if not _present(inc, src):
                miss.append(src if src == out_name else "%s (for %s)" % (src, out_name))
        if miss:
            ctx.issue("UNI_FIELD", name, "input %s lacks %s" % (g, ", ".join(miss)))


def _check_lookup(ctx, nd):
    name = nd["name"]
    _check_fields_decl(ctx, nd)
    # flat file conn, objkind; unconnected cond shape / policy; connected: build_connected's policy, cond entries and
    # condition fields (LKP_FIELD, compared exactly as the builder does), from nodes/lookup_connected.py
    for code, msg in _node_problems("lookup", ctx, nd):
        ctx.issue(code, name, msg)
    decl =[fd[0] for fd in nd.get("fields") or [] if isinstance(fd, (list, tuple)) and fd]
    dl = {d.lower() for d in decl}
    if not nd.get("query") and not nd.get("object"):
        ctx.issue("SRC_NO_OBJECT", name, "lookup %r" % name)
    if nd.get("query"):
        _sql_checks(ctx, nd, nd["query"])
    elif nd.get("object"):
        _check_object_path(ctx, nd, nd["object"], ctx.kind(nd), source=True)
    cond = nd.get("cond") or []
    if not cond:
        ctx.issue("NODE_MALFORMED", name, "lookup without cond")
    if _flag(nd, "connected"):
        inc = ctx.incoming(name)
        # [lookup_col, incoming_col] or [lookup_col, operator, incoming_col]
        badin = [c[-1] for c in cond if isinstance(c, (list, tuple)) and len(c) in (2, 3) and not _present(inc, c[-1])]
        if badin and not inc.unchecked:
            ctx.issue("EXPR_FIELD_UNKNOWN", name, "condition input(s) %s do not arrive" % ", ".join(badin))
        clash = [d for d in decl if _present(inc, d)]
        if clash and not inc.unchecked:
            ctx.issue("LKP_COLLISION", name, "lookup field(s) %s also arrive from upstream" % ", ".join(clash))
        return
    bad = [c[0] for c in cond if isinstance(c, (list, tuple)) and c and c[0].lower() not in dl]
    if not nd.get("ret") or nd["ret"].lower() not in dl:
        bad.append("ret=%r" % nd.get("ret"))
    if bad:
        ctx.issue("LKP_FIELD", name, "not declared: %s" % ", ".join(map(str, bad)))


def _check_masking(ctx, nd):
    inc = ctx.incoming(nd["name"])
    for code, msg in _node_problems("masking", ctx, nd):     # MSK_TYPE / MSK_FIELD: the compiler's own entry rules
        ctx.issue(code, nd["name"], msg)
    for e in nd.get("entries") or []:
        if isinstance(e, dict) and isinstance(e.get("field"), str) and not _present(inc, e["field"]) and not inc.unchecked:
            ctx.issue("MSK_FIELD", nd["name"], "entry field %r" % e.get("field"))
    if not nd.get("entries"):
        ctx.issue("NODE_MALFORMED", nd["name"], "masking without entries")


def _asset_listed(ctx, nd):
    guids = {(a or {}).get("guid") for a in ctx.spec.get("assets") or []}
    if not nd.get("asset"):
        ctx.issue("NODE_MALFORMED", nd["name"], "%s without asset" % nd["type"])
    elif nd["asset"] not in guids:
        ctx.issue("DQ_ASSET", nd["name"], "asset %r" % nd["asset"])


def _check_rulespec(ctx, nd):
    _asset_listed(ctx, nd)
    inc = ctx.incoming(nd["name"])
    mp = nd.get("map") or {}
    miss = []
    for fd in nd.get("inputs") or []:
        n = fd[0] if isinstance(fd, (list, tuple)) else fd
        if not _present(inc, mp.get(n, n)):
            miss.append(mp.get(n, n))
    if miss and not inc.unchecked:
        ctx.issue("DQ_INPUT", nd["name"], "rule input(s) from %s" % ", ".join(miss))


def _check_cleanse(ctx, nd):
    _asset_listed(ctx, nd)
    inc = ctx.incoming(nd["name"])
    miss = [fd[0] for fd in nd.get("fields") or [] if isinstance(fd, (list, tuple)) and fd and not _present(inc, fd[0])]
    if miss and not inc.unchecked:
        ctx.issue("DQ_INPUT", nd["name"], "cleanse input(s) %s (mapped BY NAME)" % ", ".join(miss))


def _check_dedup(ctx, nd):
    _asset_listed(ctx, nd)
    inc = ctx.incoming(nd["name"])
    mp = nd.get("map") or {}
    valid = {n for n, _, _ in ff.DEDUP_INPUTS}
    probs = ["unknown dedup input %r" % k for k in mp if k not in valid]
    probs += ["mandatory %r not mapped" % n for n, _, c in ff.DEDUP_INPUTS if c == "MANDATORY" and n not in mp]
    if not inc.unchecked:
        probs += ["%s <- %r does not arrive" % (k, v) for k, v in mp.items() if not _present(inc, v)]
    if probs:
        ctx.issue("DDP_MAP", nd["name"], "; ".join(probs))


def _check_generic(ctx, nd):
    if not nd.get("cls"):
        ctx.issue("NODE_MALFORMED", nd["name"], "generic without cls")
    if not nd.get("groups"):
        ctx.issue("NODE_MALFORMED", nd["name"], "generic without groups")
    elif nd.get("cls"):     # in/out link keys, props/objs/fields replacing the groups that hold a link group, classes...
        for msg in _build_refusals(ctx, nd):
            ctx.issue("NODE_MALFORMED", nd["name"], msg)


def _build_refusals(ctx, nd):
    """The problems of the SpecError compile.build gives for generic node ``nd``, whose raw IMF properties only its
    builder reads (fieldflow.ports_of returns None for a node whose ports() raises: the node would be unchecked, not
    reported). The node builders run as build runs them (compile.build_node: escape hatches, node-named messages), in
    spec order up to the last generic node, in one scratch context: an earlier builder may teach the build a short
    class name a generic node uses. Only the generic nodes' errors are kept (lint has its own rules for the others)."""
    if getattr(ctx, "generic_refusals", None) is None:
        ctx.generic_refusals = {}
        compiler = importlib.import_module(_PKG + ".compile")
        imf = importlib.import_module(_PKG + ".imf")
        registry = importlib.import_module(_PKG + ".registry")
        nodes = [n for n in ctx.spec["nodes"] if isinstance(n, dict) and isinstance(n.get("type"), str)]
        last = max((i for i, n in enumerate(nodes) if n["type"] == "generic"), default=-1)
        bctx = registry.Ctx(imf.B(), ctx.spec, imf.now_iso(0))
        for n in nodes[:last + 1]:
            fn = registry.NODES.get(n["type"])
            if fn is None:
                continue
            try:
                compiler.build_node(fn, bctx, n)
            except specmod.SpecError as e:
                if n["type"] == "generic" and isinstance(n.get("name"), str):
                    ctx.generic_refusals.setdefault(n["name"], [str(p) for p in e.problems])
    return ctx.generic_refusals.get(nd["name"], [])


BUILTIN = {"source": _check_source, "target": _check_target, "expression": _check_expression, "filter": _check_filter,
           "router": _check_router, "sorter": _check_sorter, "joiner": _check_joiner, "aggregator": _check_aggregator,
           "rank": _check_rank, "sequence": _check_sequence, "union": _check_union, "lookup": _check_lookup,
           "masking": _check_masking, "rulespec": _check_rulespec, "cleanse": _check_cleanse, "dedup": _check_dedup,
           "generic": _check_generic}


def _check_readers(ctx):
    """BigQuery readers per pipeline (connected component) and per mapping (L-CDI-129)."""
    an = ctx.an
    par = {n: n for n in an.nodes}

    def find(x):
        while par[x] != x:
            par[x] = par[par[x]]
            x = par[x]
        return x
    for lk in an.links:
        if lk.frm_node in par and lk.to_node in par:
            par[find(lk.frm_node)] = find(lk.to_node)
    # an unconnected lookup belongs to the pipelines that call it
    for nd in an.nodes.values():
        if nd.get("type") == "lookup" and not _flag(nd, "connected") and nd["name"] in ctx.lkp_callers:
            for caller in ctx.lkp_callers[nd["name"]]:
                par[find(nd["name"])] = find(caller)
    comp = defaultdict(list)
    for nd in an.nodes.values():
        if nd.get("type") in ("source", "lookup") and ctx.kind(nd) == "BQ" and nd.get("conn") in ctx.conns:
            comp[find(nd["name"])].append(nd["name"])
    total = sum(len(v) for v in comp.values())
    for root, readers in comp.items():
        if len(readers) > 5:
            ctx.issue("BQ_READERS_MAX", readers[0], "%d readers in one pipeline: %s" % (len(readers), ", ".join(readers)))
        elif len(readers) > 4:
            ctx.issue("BQ_READERS", readers[0], "%d readers in one pipeline: %s" % (len(readers), ", ".join(readers)))
    if total > 5 and len(comp) > 1 and not ctx.spec.get("flowOrder"):
        ctx.issue("BQ_READERS_MAPPING", None, "%d BigQuery readers over %d pipelines" % (total, len(comp)))


def _check_lookups_called(ctx):
    for nd in ctx.an.nodes.values():
        if nd.get("type") == "lookup" and not _flag(nd, "connected") and nd["name"] not in ctx.lkp_called:
            ctx.issue("LKP_NOT_CALLED", nd["name"], "lookup %r" % nd["name"])


def _note_agg_pass(ctx, consumer, field):
    """Remember a consumer reading a field an aggregator passed through (reported once per consumer)."""
    for fl in field.flags:
        if fl.startswith("agg_pass:"):
            agg = fl[9:]
            if not any((ctx.an.nodes.get(n) or {}).get("type") == "sorter" for n in ctx.an.ancestors(agg)):
                ctx.agg_pass[(consumer, agg)].add(field.name)


def _downstream_agg_refs(ctx):
    """Expressions that read a field passed through an aggregator (not grouped, not aggregated)."""
    for nd in ctx.an.nodes.values():
        if nd.get("type") not in ("expression", "filter", "router"):
            continue
        inc = ctx.incoming(nd["name"])
        texts = [p.get("expr", "") for p in nd.get("fields") or [] if isinstance(p, dict)] + \
                ([nd.get("cond", "")] if nd.get("type") == "filter" else []) + \
                [g[1] for g in nd.get("groups") or [] if isinstance(g, (list, tuple)) and len(g) == 2]
        for t in texts:
            for ref, _ in scan_expr(_text(t)).refs:
                f = inc.find(ref)
                if f is not None:
                    _note_agg_pass(ctx, nd["name"], f)
    for (consumer, agg), names in sorted(ctx.agg_pass.items()):
        ctx.issue("AGG_PASSTHROUGH", consumer, "uses %s passed through %s unsorted (last row per group)" % (", ".join(sorted(names)[:10]), agg))


# ============================================================================== entry points
def _guarded(ctx, fn):
    """Run one spec-wide rule; like the per-node checks, a malformed node option must never crash lint."""
    try:
        fn(ctx)
    except Exception as e:
        ctx.issue("NODE_MALFORMED", None, "%s crashed: %r (a node option of the wrong type?)" % (fn.__name__.lstrip("_"), e))


def _extension_issues(spec, allow_broken_extensions=None):
    """One EXTENSION_BROKEN per entry of compile.broken_extensions(spec): the modules of idmc_mapgen/nodes/ that failed
    to import and that build refuses this spec for. An ERROR, as build refuses the spec; a WARN when build goes on
    without them (``allow_broken_extensions``, None = MAPGEN_ALLOW_BROKEN_EXTENSIONS decides, exactly as for build),
    as build then only warns. A compiler that cannot be imported at all (a core node module fails) is one ERROR."""
    def issue(sev, msg, hint=CODES["EXTENSION_BROKEN"][2]):
        return Issue("EXTENSION_BROKEN", sev, None, msg, hint, "")
    try:
        compiler = importlib.import_module(_PKG + ".compile")
    except Exception as e:          # e.g. a syntax error in a core node module: no build can run
        return [issue("ERROR", "the compiler cannot be imported (%s: %s), so build refuses every spec" % (type(e).__name__, e),
                      "A core module of idmc_mapgen (a builder in idmc_mapgen/nodes/, the compiler) does not import: no "
                      "spec builds until it is fixed.")]
    try:
        sev = "WARN" if compiler.allow_broken(allow_broken_extensions) else "ERROR"    # build's own rule
        return [issue(sev, m) for m in compiler.broken_extensions(spec)]
    except Exception as e:          # never a crash
        return [issue("ERROR", "the broken extension modules cannot be listed (%s: %s)" % (type(e).__name__, e))]


def _sorted(issues):
    return sorted(_dedupe(issues), key=lambda i: (SEV_ORDER.get(i.severity, 9), i.code, str(i.node)))


def lint(spec, profile=None, allow_live=False, vars=None, default_profile=None, allow_broken_extensions=None):
    """Lint a spec (dict or path), loaded exactly as spec.load_spec loads it: the profile is ``profile`` (dict or path;
    None / {} = not given), else the spec's own "profile" key, else ``default_profile``; then the same merge and
    ${VAR} substitution (profile vars, spec vars, ``vars``). ``allow_broken_extensions`` as for compile.build: an
    extension module the spec may need that failed to import is an ERROR, a WARN when allowed (None = the
    MAPGEN_ALLOW_BROKEN_EXTENSIONS environment variable decides). Raises SpecError only when the spec or the profile
    file cannot be read; everything else is an issue."""
    raw, base_dir = specmod.read_spec(spec)
    shape = [Issue("SPEC_SHAPE", "ERROR", None, "spec needs a nodes list and a links list", CODES["SPEC_SHAPE"][2], "")]
    if not isinstance(raw, dict):
        return _sorted(shape + _extension_issues(raw, allow_broken_extensions))
    prep = specmod.prepare(raw, profile=profile, vars=vars, default_profile=default_profile, base_dir=base_dir)
    ext_issues = _extension_issues(prep.spec, allow_broken_extensions)      # what build refuses before any node
    if not isinstance(prep.spec.get("nodes"), list) or not isinstance(prep.spec.get("links", []), list):
        return _sorted(shape + ext_issues)  # judged after ${VAR}s, as load_spec does: "links": "${LINKS}" may be a list var
    var_issues = [Issue(code, CODES[code][0], None, msg, CODES[code][2] if hint is None else hint, CODES[code][3])
                  for code, msg, hint in _var_issues(prep)]
    fatal = specmod._dedupe(prep.profile_problems + prep.shape_problems)
    if fatal:                       # wrong types: the rules below would misread (or crash on) this spec
        return _sorted([Issue("SPEC_SHAPE", "ERROR", None, m, _SHAPE_HINT, "") for m in fatal] + var_issues + ext_issues)
    spec = prep.spec
    try:
        ctx = LintCtx(spec, prep.profile, allow_live)
    except Exception as e:          # the field flow cannot read a node option of the wrong type (load_spec leaves
        issues = [Issue("NODE_MALFORMED", "ERROR", None,     # node options to the builders): an issue, never a crash
                        "lint cannot follow the fields: %r (a node option of the wrong type?)" % (e,),
                        CODES["NODE_MALFORMED"][2], "")] + var_issues + ext_issues
        return _sorted(issues)
    ctx.lkp_called, ctx.lkp_callers = set(), defaultdict(set)
    ctx.issues += var_issues + ext_issues
    _guarded(ctx, _check_spec)
    _guarded(ctx, _check_nodes_and_links)
    for nd in ctx.an.nodes.values():
        t = nd.get("type")
        try:
            if t in BUILTIN:
                BUILTIN[t](ctx, nd)
            for fn in CHECKS.get(t, []):
                for iss in fn(ctx, nd) or []:
                    ctx.issues.append(iss)
        except Exception as e:      # a malformed node must never crash lint
            ctx.issue("NODE_MALFORMED", nd.get("name"), "%s check crashed: %r" % (t, e))
    for fn in (_check_lookups_called, _check_readers, _targets_same_object, _downstream_agg_refs):
        _guarded(ctx, fn)
    if not has_errors(ctx.issues):  # one gate: a spec lint passes must also pass load_spec (deploy runs both). Its
        try:                        # other refusals are ERRORs above: profile / shape (fatal), ${VAR}s (_var_issues;
            specmod.validate(spec, for_package=True)    # a template's INFO comes with ERRORs of its own)
        except specmod.SpecError as e:
            for m in e.problems:
                ctx.issue("SPEC_SHAPE", None, m, hint=_LOAD_HINT, lesson="")
    return _sorted(ctx.issues)


def _dedupe(issues):
    seen, out = set(), []
    for i in issues:
        k = (i.code, i.severity, i.node, i.message)
        if k not in seen:
            seen.add(k)
            out.append(i)
    return out


def has_errors(issues):
    return any(i.severity == "ERROR" for i in issues)


def summary(issues):
    c = Counter(i.severity for i in issues)
    return {"ERROR": c.get("ERROR", 0), "WARN": c.get("WARN", 0), "INFO": c.get("INFO", 0)}


def format_issues(issues, min_severity="INFO", hints=True):
    lim = SEV_ORDER.get(min_severity.upper(), 2)
    lines = []
    for i in issues:
        if SEV_ORDER.get(i.severity, 9) > lim:
            continue
        lines.append("%-5s %-24s %-26s %s" % (i.severity, i.code, (i.node or "-")[:26], i.message))
        if hints and i.hint:
            lines.append("      -> %s%s" % (i.hint, " [%s]" % i.lesson if i.lesson else ""))
    s = summary(issues)
    lines.append("lint: %d error(s), %d warning(s), %d info" % (s["ERROR"], s["WARN"], s["INFO"]))
    return "\n".join(lines)


def rules_table():
    return "\n".join("%-24s %-5s %s%s" % (c, v[0], v[1], " [%s]" % v[3] if v[3] else "") for c, v in sorted(CODES.items()))


def main(argv=None, default_profile=None):
    """CLI. Exit 0 clean, 1 lint errors, 2 a spec or profile that cannot be read. ``default_profile``: the profile for
    a spec with neither --profile nor its own "profile" key (mapgen.py passes its fallbacks)."""
    import argparse
    ap = argparse.ArgumentParser(prog="mapgen lint", description="Static checks on a mapping spec before import.")
    ap.add_argument("spec", nargs="*")
    ap.add_argument("--profile")
    ap.add_argument("--level", default="info", choices=["error", "warn", "info"])
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--allow-live", action="store_true")
    ap.add_argument("--no-hints", action="store_true")
    ap.add_argument("--rules", action="store_true", help="print every rule code and exit")
    a = ap.parse_args(argv)
    if a.rules:
        print(rules_table())
        return 0
    worst = 0
    for p in a.spec:
        try:
            issues = lint(p, a.profile, a.allow_live, default_profile=default_profile)
        except specmod.SpecError as e:          # the spec / profile file cannot be read
            print("SPEC ERROR: %s" % e, file=sys.stderr)
            if a.json:
                print(json.dumps({"spec": p, "error": str(e)}, indent=1))
            worst = 2
            continue
        if a.json:
            print(json.dumps({"spec": p, "summary": summary(issues), "issues": [i._asdict() for i in issues]}, indent=1))
        else:
            if len(a.spec) > 1:
                print("== %s" % p)
            print(format_issues(issues, a.level, hints=not a.no_hints))
        worst = max(worst, 1 if has_errors(issues) else 0)
    return worst


if __name__ == "__main__":
    sys.exit(main())

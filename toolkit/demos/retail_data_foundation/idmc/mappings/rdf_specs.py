"""The six consolidated Retail Data Foundation mappings, as mapgen specs (source of truth; 03_mappings.py renders them).

Design doctrine (as few mappings as possible): one mapping per business flow, never one task per table.
  m_rdf_ingest_customers  PG customers, memberships, stores, products -> typed landing (4 flows, 1 job)
  m_rdf_ingest_activity   PG orders, order_lines, payments, visits    -> typed landing (4 flows, 1 job)
  m_rdf_customer_golden   cleanse -> staging; survivorship -> golden; Router: VALID -> reverse ETL into PG,
                          else -> review table                                           (2 BigQuery readers)
  m_rdf_dq_scorecard      rule rows -> dq_results; Aggregators by dimension + overall -> Union -> dq_scorecard
  m_rdf_sales_facts       order lines -> facts + Aggregator per store and day; visits -> visit facts
  m_rdf_crm_sync          clean-only, count-gated golden records -> Salesforce Contact Upsert on the external id

Connections are aliases resolved from the generated mapgen profile: PG (operational Postgres), WH (BigQuery),
SF (Salesforce). ${VARS} are mapgen profile vars (WH_PROJECT, DS_*, PG_*). "queryFile" is expanded by 03_mappings.py
from idmc/sql/ (comments and non-ASCII stripped, {{include x.sql}} inlined).
"""

S, I, N, F, T = "STRING", "INTEGER", "NUMERIC", "FLOAT", "TIMESTAMP"


def s(name, prec=256):
    return [name, S, prec]


def num(name):
    return [name, N, 28, None, 9]


# ---------- PostgreSQL source field lists (nativeType = the PostgreSQL type name)
def pg(name, t):
    native = {I: "int8", S: "text", N: "numeric", T: "timestamptz"}[t]
    if t == N:
        return [name, N, 28, native, 9]
    if t == S:
        return [name, S, 256, native]
    return [name, t, None, native]


PG_TABLES = {
    "stores": [("store_id", I), ("store_code", S), ("name", S), ("city", S), ("state", S), ("opened_at", T)],
    "products": [("product_id", I), ("sku", S), ("name", S), ("category", S), ("unit_price", N)],
    "customers": [("customer_id", I), ("full_name", S), ("email", S), ("phone", S), ("address", S), ("city", S),
                  ("state", S), ("zip", S), ("tier", S), ("signup_channel", S), ("home_store_code", S), ("crm_id", S),
                  ("created_at", T), ("updated_at", T)],
    "memberships": [("membership_id", I), ("customer_id", I), ("tier", S), ("status", S), ("monthly_price", N),
                    ("started_at", T), ("cancelled_at", T), ("updated_at", T)],
    "orders": [("order_id", I), ("customer_id", I), ("store_code", S), ("channel", S), ("status", S),
               ("list_amount", N), ("discount", N), ("amount", N), ("ordered_at", T), ("updated_at", T)],
    "order_lines": [("order_line_id", I), ("order_id", I), ("product_id", I), ("qty", I), ("unit_price", N),
                    ("line_amount", N)],
    "payments": [("payment_id", I), ("customer_id", I), ("order_id", I), ("membership_id", I), ("kind", S),
                 ("amount", N), ("status", S), ("processor", S), ("paid_at", T)],
    "visits": [("visit_id", I), ("customer_id", I), ("store_code", S), ("check_in_at", T), ("check_out_at", T),
               ("status", S)],
}


def wh(cols):
    out = []
    for c, t in cols:
        out.append(num(c) if t == N else s(c) if t == S else [c, t])
    return out


def ingest(name, tables, desc):
    nodes, links = [], []
    for t in tables:
        up = t.upper()[:10]
        nodes.append({"type": "source", "name": f"SRC_{up}", "conn": "PG", "object": "${PG_SCHEMA}/" + t,
                      "objkind": "TABLE", "fields": [pg(c, ty) for c, ty in PG_TABLES[t]]})
        nodes.append({"type": "target", "name": f"TGT_{up}", "conn": "WH", "object": "${DS_LAND}/" + t,
                      "fields": wh(PG_TABLES[t]), "truncate": True, "disposition": "Write truncate"})
        links.append([f"SRC_{up}", f"TGT_{up}"])
    return {"name": name, "taskName": "mt" + name[1:], "description": desc, "nodes": nodes, "links": links}


STG_FIELDS = [s("full_name"), s("email"), s("phone_digits"), s("phone_e164"), s("address"), s("city"), s("state"),
              s("zip"), s("tier"), s("signup_channel"), s("home_store_code"), s("crm_id"), ["created_at", T],
              ["email_valid", I], ["phone_valid", I], ["has_address", I], ["tier_valid", I], s("person_key", 1000),
              ["dq_score", F], ["dq_valid", I]]
STG_FIELDS.insert(0, ["customer_id", I])

GOLD_IN = [["customer_id", I], s("full_name"), s("email"), s("phone_e164"), s("address"), s("city"), s("state"),
           s("zip"), s("tier"), s("signup_channel"), s("home_store_code"), ["dq_score", F], ["dq_valid", I],
           ["merged_count", I], ["first_signed_up_at", T]]
GOLD_OUT = GOLD_IN + [s("dq_status"), ["golden_built_at", T]]
PG_GOLDEN = [["customer_id", I, None, "int8"], [*s("full_name"), "text"], [*s("email"), "text"],
             [*s("phone_e164"), "text"], [*s("address"), "text"], [*s("city"), "text"], [*s("state"), "text"],
             [*s("zip"), "text"], [*s("tier"), "text"], ["dq_score", N, 6, "numeric", 4], ["dq_valid", I, None, "int4"],
             ["golden_built_at", T, None, "timestamptz"]]


def customer_golden():
    return {
        "name": "m_rdf_customer_golden", "taskName": "mt_rdf_customer_golden",
        "description": "[${TAG}] Customer golden record: cleanse + DQ flags -> staging; survivorship -> golden; "
                       "Router VALID -> reverse ETL to the operational DB, else -> review queue.",
        "nodes": [
            {"type": "source", "name": "SRC_STG", "conn": "WH", "queryFile": "stg_customers_scored.sql", "fields": STG_FIELDS},
            {"type": "target", "name": "TGT_STG", "conn": "WH", "object": "${DS_STAGING}/stg_customers",
             "fields": STG_FIELDS, "truncate": True, "disposition": "Write truncate"},
            {"type": "source", "name": "SRC_GOLD", "conn": "WH", "queryFile": "customer_golden.sql", "fields": GOLD_IN},
            {"type": "expression", "name": "EXP_GOLD", "fields": [
                {"name": "dq_status", "type": S, "expr": "IIF(dq_valid = 1, 'VALID', 'REVIEW')", "kind": "OUTPUT", "prec": 16},
                {"name": "golden_built_at", "type": T, "expr": "SYSTIMESTAMP()", "kind": "OUTPUT"}]},
            {"type": "target", "name": "TGT_GOLD", "conn": "WH", "object": "${DS_GOLD}/customer_golden",
             "fields": GOLD_OUT, "truncate": True, "disposition": "Write truncate"},
            {"type": "router", "name": "RTR_DQ", "groups": [["VALID", "dq_valid = 1"]]},
            {"type": "target", "name": "TGT_ACT", "conn": "PG", "object": "${PG_ACT_SCHEMA}/customer_golden",
             "fields": PG_GOLDEN, "truncate": False, "op": "Upsert", "updateColumns": ["customer_id"]},
            {"type": "target", "name": "TGT_REVIEW", "conn": "WH", "object": "${DS_GOLD}/customer_review",
             "fields": GOLD_OUT, "truncate": True, "disposition": "Write truncate"},
        ],
        "links": [["SRC_STG", "TGT_STG"], ["SRC_GOLD", "EXP_GOLD"], ["EXP_GOLD", "TGT_GOLD"], ["EXP_GOLD", "RTR_DQ"],
                  ["RTR_DQ.VALID", "TGT_ACT"], ["RTR_DQ.DEFAULT1", "TGT_REVIEW"]],
    }


RULE_FIELDS = [s("rule"), s("dimension"), s("table_name"), ["checked", I], ["failed", I], ["pass_rate", F]]


def dq_scorecard():
    agg = [{"name": "rules", "type": I, "expr": "COUNT(rule)"}, {"name": "checked_sum", "type": I, "expr": "SUM(checked)"},
           {"name": "failed_sum", "type": I, "expr": "SUM(failed)"}]
    return {
        "name": "m_rdf_dq_scorecard", "taskName": "mt_rdf_dq_scorecard",
        "description": "[${TAG}] DQ results per rule -> dq_results; rolled up per dimension plus an overall row -> dq_scorecard "
                       "(green >= 0.99, amber >= 0.90, else red).",
        "nodes": [
            {"type": "source", "name": "SRC_RULES", "conn": "WH", "queryFile": "dq_results.sql", "fields": RULE_FIELDS},
            {"type": "expression", "name": "EXP_RUN", "fields": [
                {"name": "run_at", "type": T, "expr": "SYSTIMESTAMP()", "kind": "OUTPUT"},
                {"name": "all_key", "type": S, "expr": "'overall'", "kind": "OUTPUT", "prec": 16}]},
            {"type": "target", "name": "TGT_RESULTS", "conn": "WH", "object": "${DS_GOLD}/dq_results",
             "fields": RULE_FIELDS + [["run_at", T]], "truncate": True, "disposition": "Write truncate"},
            {"type": "aggregator", "name": "AGG_DIM", "groupBy": ["dimension"], "fields": agg},
            {"type": "aggregator", "name": "AGG_ALL", "groupBy": ["all_key"], "fields": agg},
            {"type": "union", "name": "UNI_SC", "inputs": ["DIM", "ALL"],
             "fields": [["dimension", S, 256, None], ["rules", I, None, None], ["checked_sum", I, None, None],
                        ["failed_sum", I, None, None]],
             "map": {"ALL": {"dimension": "all_key"}}},
            {"type": "expression", "name": "EXP_SC", "fields": [
                {"name": "v_rate", "type": F, "kind": "VARIABLE",
                 "expr": "ROUND(1 - (failed_sum * 1.0) / IIF(checked_sum = 0, 1, checked_sum), 4)"},
                {"name": "checked", "type": I, "expr": "checked_sum", "kind": "OUTPUT"},
                {"name": "failed", "type": I, "expr": "failed_sum", "kind": "OUTPUT"},
                {"name": "pass_rate", "type": F, "expr": "v_rate", "kind": "OUTPUT"},
                {"name": "status", "type": S, "expr": "IIF(v_rate >= 0.99, 'green', IIF(v_rate >= 0.90, 'amber', 'red'))",
                 "kind": "OUTPUT", "prec": 8},
                {"name": "run_at", "type": T, "expr": "SYSTIMESTAMP()", "kind": "OUTPUT"}]},
            {"type": "target", "name": "TGT_SC", "conn": "WH", "object": "${DS_GOLD}/dq_scorecard",
             "fields": [s("dimension"), ["rules", I], ["checked", I], ["failed", I], ["pass_rate", F], s("status"),
                        ["run_at", T]], "truncate": True, "disposition": "Write truncate"},
        ],
        "links": [["SRC_RULES", "EXP_RUN"], ["EXP_RUN", "TGT_RESULTS"], ["EXP_RUN", "AGG_DIM"], ["EXP_RUN", "AGG_ALL"],
                  ["AGG_DIM", "UNI_SC.DIM"], ["AGG_ALL", "UNI_SC.ALL"], ["UNI_SC", "EXP_SC"], ["EXP_SC", "TGT_SC"]],
    }


LINE_FIELDS = [["order_line_id", I], ["order_id", I], ["customer_id", I], s("store_code"), s("channel"),
               s("order_status"), ["order_day", T], ["product_id", I], s("sku"), s("category"), ["qty", I],
               num("unit_price"), num("line_amount")]
VISIT_FIELDS = [["visit_id", I], ["customer_id", I], s("store_code"), ["check_in_at", T], ["check_out_at", T],
                ["minutes", I], s("status")]


def sales_facts():
    return {
        "name": "m_rdf_sales_facts", "taskName": "mt_rdf_sales_facts",
        "description": "[${TAG}] Sales and visit facts: order lines -> order_line_facts + store_daily_sales (Aggregator); "
                       "visits -> visit_facts.",
        "nodes": [
            {"type": "source", "name": "SRC_LINES", "conn": "WH", "queryFile": "order_line_facts.sql", "fields": LINE_FIELDS},
            {"type": "target", "name": "TGT_LINES", "conn": "WH", "object": "${DS_GOLD}/order_line_facts",
             "fields": LINE_FIELDS, "truncate": True, "disposition": "Write truncate"},
            {"type": "aggregator", "name": "AGG_DAY", "groupBy": ["store_code", "order_day"], "fields": [
                {"name": "lines", "type": I, "expr": "COUNT(order_line_id)"},
                {"name": "units", "type": I, "expr": "SUM(qty)"},
                {"name": "revenue", "type": N, "expr": "SUM(line_amount)", "prec": 28, "scale": 9}]},
            {"type": "target", "name": "TGT_DAY", "conn": "WH", "object": "${DS_GOLD}/store_daily_sales",
             "fields": [s("store_code"), ["order_day", T], ["lines", I], ["units", I], num("revenue")],
             "truncate": True, "disposition": "Write truncate"},
            {"type": "source", "name": "SRC_VISITS", "conn": "WH", "queryFile": "visit_facts.sql", "fields": VISIT_FIELDS},
            {"type": "target", "name": "TGT_VISITS", "conn": "WH", "object": "${DS_GOLD}/visit_facts",
             "fields": VISIT_FIELDS, "truncate": True, "disposition": "Write truncate"},
        ],
        "links": [["SRC_LINES", "TGT_LINES"], ["SRC_LINES", "AGG_DAY"], ["AGG_DAY", "TGT_DAY"], ["SRC_VISITS", "TGT_VISITS"]],
    }


def crm_sync():
    ext = "${SF_CONTACT_EXT}"
    cols = [ext, "FirstName", "LastName", "Email", "Phone", "MailingStreet", "MailingCity", "MailingState",
            "MailingPostalCode", "Rdf_Tier__c", "Rdf_Home_Store__c", "Rdf_Signup_Channel__c"]
    src = [s(c) for c in cols] + [["Rdf_DQ_Score__c", F]]
    tgt = [[ext, S, 255, "string", None, {"externalId": True, "unique": True, "nullable": False}]]
    tgt += [[c, S, 255, "string"] for c in cols[1:]] + [["Rdf_DQ_Score__c", F, None, "double"]]
    return {
        "name": "m_rdf_crm_sync", "taskName": "mt_rdf_crm_sync",
        "description": "[${TAG}] Reverse ETL to the CRM: clean-only (dq_valid = 1), count-gated, test identities excluded; "
                       "Salesforce Contact Upsert on the external id.",
        "nodes": [
            {"type": "source", "name": "SRC_CONTACTS", "conn": "WH", "queryFile": "crm_contacts.sql", "fields": src},
            {"type": "target", "name": "TGT_CONTACT", "conn": "SF", "object": "Contact", "fields": tgt,
             "truncate": False, "op": "Upsert", "updateColumns": [ext]},
        ],
        "links": [["SRC_CONTACTS", "TGT_CONTACT"]],
    }


def all_specs():
    return [
        ingest("m_rdf_ingest_customers", ["customers", "memberships", "stores", "products"],
               "[${TAG}] Ingest the customer domain from the operational DB into typed landing (one job, 4 flows)."),
        ingest("m_rdf_ingest_activity", ["orders", "order_lines", "payments", "visits"],
               "[${TAG}] Ingest the activity domain from the operational DB into typed landing (one job, 4 flows)."),
        customer_golden(), dq_scorecard(), sales_facts(), crm_sync(),
    ]

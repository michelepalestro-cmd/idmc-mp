# Demo blueprints

Optional, rebuildable examples of whole IDMC builds. Each has a `README.md` (what and why) and a numbered `BUILD.md`;
every write is a dry run until `--execute --expect-org <orgIdV3>`. Conventions: [BLUEPRINT_CONVENTIONS.md](BLUEPRINT_CONVENTIONS.md).

| Blueprint | What it shows | IDMC services | Rebuild |
|---|---|---|---|
| [`customer_master_csv`](customer_master_csv/README.md) | A messy customer CSV cleaned, de-duplicated and given stable customer ids, written back as CSV files; proven offline in under a second by `check.py`, with a timed live run | CDI on a Secure Agent (flat files), native transformations only | 20-40 min first time |
| [`retail_data_foundation`](retail_data_foundation/README.md) (`rdf_`) | A multi-store retailer's whole data layer: Postgres -> CDC -> BigQuery, consolidated mappings to a golden customer record, DQ scorecard, reverse ETL to Postgres and Salesforce (batch and real time), catalog with glossary, classification and lineage | CDC (Database Ingestion), CDI, CAI, CDQ / Profiling, CDGC, address verification | 2-3 h first time |
| [`bid_desk_document_parsing`](bid_desk_document_parsing/README.md) (`bid_`) | Bid documents attached in the CRM -> SharePoint -> CLAIRE document parsing -> DQ rules -> a bid-readiness decision -> Snowflake -> one Tableau workbook (6 tabs); Run / What-if / Reset loop | CDI, CLAIRE parsing (Structure Parser), CDQ, CDGC, taskflows | about half a day |
| [`message_bus_kafka_cai`](message_bus_kafka_cai/README.md) (`mbr_`) | A legacy JMS retail integration bus replaced by Kafka + CAI: subscribers, validate / transform / route, retry with backoff, error queue, dead-letter and replay, JMS-to-Kafka bridge, nightly CDI batch to Oracle | CAI (Kafka / AMQP listeners, processes), CDI | 2-3 h |

The blueprints name concrete systems only so that they can be rebuilt end to end as written. They are not a
recommended stack: to build the same pattern on your own systems, keep each blueprint's stages and gates and swap the
connections (the [New Pipeline Milestones](../../knowledge/00-start-here/08-new-pipeline-milestones-any-source-any-target.md)
show how for a connector the KB has not covered).

Each step in each `BUILD.md` is marked **PROVEN** (worked end to end in a real org, in an earlier non-generic form) or
**ADAPTED** (rewritten generically, checked offline only). Expect to fix a few ADAPTED steps on the first run.

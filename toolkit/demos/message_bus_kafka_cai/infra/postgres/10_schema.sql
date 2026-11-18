-- Message Bus Replacement: ops ledger, hospital (error queue) and the SIMULATED target systems.
-- Schema mbr = the tables; schema mbr_api (20_api.sql) = what PostgREST exposes to CAI.
-- Every target table is idempotent on (msg_id, rev): a replayed message is answered 'duplicate', never applied twice.

CREATE SCHEMA IF NOT EXISTS mbr;

-- ---------------------------------------------------------------- settings CAI reads on every message
CREATE TABLE mbr.config (
  key   text PRIMARY KEY,
  value text NOT NULL
);

-- ---------------------------------------------------------------- the ops ledger: one row per stage of a message
CREATE TABLE mbr.events (
  id          bigserial PRIMARY KEY,
  at          timestamptz NOT NULL DEFAULT now(),
  msg_id      text NOT NULL,
  rev         text,
  stage       text NOT NULL,          -- consumed, bridged, validated, retry, delivered, error_queue, replayed, ...
  target      text,
  status      text,
  detail      text,
  ms          text,
  process     text,                   -- the CAI process that wrote it
  instance_id text                    -- util:getProcessId(): joins to the run in the CAI Monitor
);
CREATE INDEX events_msg ON mbr.events (msg_id);
CREATE INDEX events_at ON mbr.events (at);

-- ---------------------------------------------------------------- the hospital (error queue)
CREATE TABLE mbr.reason_codes (
  code       text PRIMARY KEY,
  retryable  boolean NOT NULL,        -- true: the hospital sweep replays it; false: an operator fixes or discards it
  meaning    text NOT NULL
);

CREATE TABLE mbr.error_queue (
  id            bigserial PRIMARY KEY,
  created_at    timestamptz NOT NULL DEFAULT now(),
  msg_id        text NOT NULL,
  rev           text,
  topic         text,                 -- the Kafka topic (or JMS queue) the message came from
  biz_id        text,                 -- the record key: item or PO number
  family        text,                 -- Items | Order
  type          text,
  reason_code   text NOT NULL,
  reason_text   text,
  target        text,
  http_status   text,
  failed_step   text,
  attempts      text,
  payload       text NOT NULL,        -- the original message, replayed as is
  retryable     boolean NOT NULL DEFAULT false,
  status        text NOT NULL DEFAULT 'open',   -- open | replayed | resolved | discarded | dead
  replays       integer NOT NULL DEFAULT 0,
  next_retry_at timestamptz,
  updated_at    timestamptz NOT NULL DEFAULT now(),
  actor         text
);
CREATE INDEX error_queue_due ON mbr.error_queue (status, retryable, next_retry_at);
CREATE INDEX error_queue_msg ON mbr.error_queue (msg_id);

-- ---------------------------------------------------------------- SIMULATED target systems
-- fault injection for the drills: a target answers 503 (down), 422 (reject) or sleeps 15 s (slow) until 'until'
CREATE TABLE mbr.standin_fault (
  target text PRIMARY KEY,            -- merch | warehouse | store
  mode   text NOT NULL CHECK (mode IN ('down', 'slow', 'reject')),
  until  timestamptz NOT NULL
);

CREATE TABLE mbr.applied (            -- idempotency: (target, msg_id, rev) applied once
  target  text NOT NULL,
  msg_id  text NOT NULL,
  rev     text NOT NULL,
  at      timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (target, msg_id, rev)
);

-- merchandising system (item master + purchase orders)
CREATE TABLE mbr.merch_item (
  item text PRIMARY KEY, item_desc text, dept text, class text, subclass text, unit_retail numeric(12,2),
  compare_at numeric(12,2), upc text, supplier text, status text, msg_id text, rev text,
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE mbr.merch_po_header (
  po text PRIMARY KEY, version integer NOT NULL, supplier text, dept text, location text, dc text,
  total_cost numeric(14,2), line_count integer, not_before text, not_after text, order_type text,
  status text NOT NULL DEFAULT 'open', msg_id text, rev text, updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE mbr.merch_po_line (
  po text NOT NULL, line_no integer NOT NULL, item text, location text, loc_type text, unit_cost numeric(12,4),
  qty_ordered numeric(12,2), PRIMARY KEY (po, line_no)
);

-- warehouse system (items with the vendor contact masked, POs per distribution center)
CREATE TABLE mbr.wh_item (
  item text PRIMARY KEY, item_desc text, dept text, upc text, vendor_contact text, msg_id text, rev text,
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE mbr.wh_po (
  po text PRIMARY KEY, dc text NOT NULL, location text, line_count integer, lines_received integer,
  msg_id text, rev text, updated_at timestamptz NOT NULL DEFAULT now()
);

-- store point of sale (one price per item per store)
CREATE TABLE mbr.store (store_id text PRIMARY KEY, name text NOT NULL);
CREATE TABLE mbr.store_price (
  store_id text NOT NULL REFERENCES mbr.store, item text NOT NULL, unit_retail numeric(12,2), compare_at numeric(12,2),
  msg_id text, rev text, updated_at timestamptz NOT NULL DEFAULT now(), PRIMARY KEY (store_id, item)
);

-- the nightly batch reads these (CDI -> Oracle); dashboards read the views in 20_api.sql

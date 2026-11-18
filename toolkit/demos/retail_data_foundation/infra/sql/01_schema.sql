-- Retail Data Foundation: operational source schema (PostgreSQL 16).
-- Run once as the database owner:  psql -U <PG_USER> -d <PG_DB> -f 01_schema.sql
--
-- Design rules that come from IDMC (each one cost a failed job before it was learned):
--   * every table has a BIGINT primary key. Database Ingestion's initial load fails on a TEXT primary key
--     ("Field Schema.column value error: no columns").
--   * no jsonb / pgvector / arrays in tables IDMC reads: the PostgreSQL connector cannot land jsonb, and one vector
--     column aborts a whole Data Profiling task. Long text stays plain TEXT.
--   * internal control tables (watermarks, processed-event ledgers) live in schema "control" so CDC and catalog
--     scans never include them (their NOT NULL text columns broke a CDC initial load).
--   * columns are deliberately "dirty-able": the traffic generator writes messy names, e-mails and phones so the
--     cleanse / DQ / survivorship steps have real work to do.

CREATE SCHEMA IF NOT EXISTS activation;   -- reverse-ETL target: golden records written back by IDMC
CREATE SCHEMA IF NOT EXISTS control;      -- never replicated, never cataloged

CREATE TABLE IF NOT EXISTS public.stores (
    store_id      BIGSERIAL PRIMARY KEY,
    store_code    TEXT NOT NULL UNIQUE,
    name          TEXT NOT NULL,
    city          TEXT,
    state         TEXT,
    opened_at     TIMESTAMPTZ DEFAULT now(),
    active        BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS public.products (
    product_id    BIGSERIAL PRIMARY KEY,
    sku           TEXT NOT NULL UNIQUE,
    name          TEXT NOT NULL,
    category      TEXT,
    unit_price    NUMERIC(10,2) NOT NULL,
    active        BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS public.customers (
    customer_id     BIGSERIAL PRIMARY KEY,
    full_name       TEXT,
    email           TEXT,
    phone           TEXT,
    address         TEXT,
    city            TEXT,
    state           TEXT,
    zip             TEXT,
    tier            TEXT,              -- free text on purpose: 'gold', 'GOLD ', 'Gld' ... canonicalised by IDMC
    signup_channel  TEXT,              -- web | mobile | store
    home_store_code TEXT,
    crm_id          TEXT,              -- filled back from the CRM by reverse ETL / CAI (optional)
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.memberships (
    membership_id  BIGSERIAL PRIMARY KEY,
    customer_id    BIGINT NOT NULL REFERENCES public.customers(customer_id),
    tier           TEXT NOT NULL,      -- Bronze | Silver | Gold
    status         TEXT NOT NULL,      -- pending | active | cancelled
    monthly_price  NUMERIC(10,2) NOT NULL,
    started_at     TIMESTAMPTZ,
    cancelled_at   TIMESTAMPTZ,
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.orders (
    order_id      BIGSERIAL PRIMARY KEY,
    customer_id   BIGINT REFERENCES public.customers(customer_id),   -- NULL = guest
    store_code    TEXT NOT NULL,
    channel       TEXT NOT NULL,       -- web | mobile | store
    status        TEXT NOT NULL,       -- placed | paid | refunded | cancelled
    list_amount   NUMERIC(10,2) NOT NULL,
    discount      NUMERIC(10,2) NOT NULL DEFAULT 0,
    amount        NUMERIC(10,2) NOT NULL,
    ordered_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.order_lines (
    order_line_id BIGSERIAL PRIMARY KEY,
    order_id      BIGINT NOT NULL REFERENCES public.orders(order_id),
    product_id    BIGINT NOT NULL REFERENCES public.products(product_id),
    qty           INTEGER NOT NULL,
    unit_price    NUMERIC(10,2) NOT NULL,
    line_amount   NUMERIC(10,2) NOT NULL
);

CREATE TABLE IF NOT EXISTS public.payments (
    payment_id     BIGSERIAL PRIMARY KEY,
    customer_id    BIGINT REFERENCES public.customers(customer_id),
    order_id       BIGINT REFERENCES public.orders(order_id),
    membership_id  BIGINT REFERENCES public.memberships(membership_id),
    kind           TEXT NOT NULL,      -- order | membership
    amount         NUMERIC(10,2) NOT NULL,
    status         TEXT,               -- settled | failed | refunded  (NULL on purpose sometimes: DQ rule)
    processor      TEXT,               -- card | wallet | cash        (NULL on purpose sometimes: DQ rule)
    paid_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.visits (
    visit_id      BIGSERIAL PRIMARY KEY,
    customer_id   BIGINT REFERENCES public.customers(customer_id),
    store_code    TEXT NOT NULL,
    check_in_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    check_out_at  TIMESTAMPTZ,
    status        TEXT NOT NULL DEFAULT 'open'   -- open | closed
);

-- Reverse-ETL target (IDMC m_rdf_customer_golden writes it with Upsert on customer_id).
CREATE TABLE IF NOT EXISTS activation.customer_golden (
    customer_id      BIGINT PRIMARY KEY,
    full_name        TEXT,
    email            TEXT,
    phone_e164       TEXT,
    address          TEXT,
    city             TEXT,
    state            TEXT,
    zip              TEXT,
    tier             TEXT,
    dq_score         NUMERIC(6,4),
    dq_valid         INTEGER,
    golden_built_at  TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS control.traffic_runs (
    run_id      BIGSERIAL PRIMARY KEY,
    started_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    events      INTEGER NOT NULL DEFAULT 0,
    note        TEXT
);

CREATE INDEX IF NOT EXISTS ix_orders_customer ON public.orders(customer_id);
CREATE INDEX IF NOT EXISTS ix_payments_customer ON public.payments(customer_id);
CREATE INDEX IF NOT EXISTS ix_visits_customer ON public.visits(customer_id);
CREATE INDEX IF NOT EXISTS ix_customers_email ON public.customers(lower(email));

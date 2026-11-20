-- Message Bus Replacement: the REST API CAI calls, as SQL functions that PostgREST exposes on /rpc/<name>.
-- POST functions take ONE unnamed json argument: PostgREST passes the request body to it as is.
-- GET functions are STABLE (PostgREST only allows GET on STABLE / IMMUTABLE functions).
-- Every answer is a flat JSON object of strings, so a CAI action output field (property="...") maps it directly.
-- A target answers its HTTP status with set_config('response.status', ...): 2xx delivered / duplicate, 409 stale,
-- 422 rejected (no retry), 503 unavailable (CAI retries with backoff).

CREATE SCHEMA IF NOT EXISTS mbr_api;

-- ---------------------------------------------------------------- helpers (not exposed)
CREATE OR REPLACE FUNCTION mbr.cfg(k text, dflt text) RETURNS text LANGUAGE sql STABLE AS
$$ SELECT coalesce((SELECT value FROM mbr.config WHERE key = k), dflt) $$;

CREATE OR REPLACE FUNCTION mbr.http(code int) RETURNS void LANGUAGE sql AS
$$ SELECT set_config('response.status', code::text, true) $$;

-- the simulated outage / slowness / rejection of a target; NULL when the target is healthy
CREATE OR REPLACE FUNCTION mbr.fault(t text) RETURNS json LANGUAGE plpgsql AS $$
DECLARE m text;
BEGIN
  SELECT mode INTO m FROM mbr.standin_fault WHERE target = t AND until > now();
  IF m = 'down' THEN
    PERFORM mbr.http(503);
    RETURN json_build_object('result', 'error', 'error', upper(t) || '_UNAVAILABLE', 'reason', 'simulated outage of ' || t);
  ELSIF m = 'reject' THEN
    PERFORM mbr.http(422);
    RETURN json_build_object('result', 'rejected', 'error', 'REJECTED', 'reason', 'simulated business rejection by ' || t);
  ELSIF m = 'slow' THEN
    PERFORM pg_sleep(15);          -- longer than the CAI action's requestTimeout (10 s): CAI sees a 500 and retries
  END IF;
  RETURN NULL;
END $$;

-- idempotency: true the first time (target, msg_id, rev) is seen
CREATE OR REPLACE FUNCTION mbr.first_time(t text, p json) RETURNS boolean LANGUAGE plpgsql AS $$
BEGIN
  INSERT INTO mbr.applied (target, msg_id, rev) VALUES (t, p->>'msg_id', coalesce(p->>'rev', '1'));
  RETURN true;
EXCEPTION WHEN unique_violation THEN
  RETURN false;
END $$;

CREATE OR REPLACE FUNCTION mbr.ok(extra json DEFAULT '{}') RETURNS json LANGUAGE sql AS
$$ SELECT (jsonb_build_object('result', 'applied') || coalesce(extra::jsonb, '{}'::jsonb))::json $$;

CREATE OR REPLACE FUNCTION mbr.dup() RETURNS json LANGUAGE sql AS
$$ SELECT json_build_object('result', 'duplicate') $$;

CREATE OR REPLACE FUNCTION mbr.num(v text) RETURNS numeric LANGUAGE sql IMMUTABLE AS
$$ SELECT CASE WHEN v ~ '^-?[0-9]+(\.[0-9]+)?$' THEN v::numeric END $$;

-- ---------------------------------------------------------------- ledger
CREATE OR REPLACE FUNCTION mbr_api.track(json) RETURNS json LANGUAGE plpgsql SECURITY DEFINER AS $$
DECLARE p json := $1;
BEGIN
  INSERT INTO mbr.events (msg_id, rev, stage, target, status, detail, ms, process, instance_id)
  VALUES (p->>'msg_id', p->>'rev', p->>'stage', p->>'target', p->>'status', p->>'detail', p->>'ms', p->>'process',
          p->>'instance_id');
  IF p->>'stage' = 'delivered' THEN          -- a replay that got through closes its hospital entry
    UPDATE mbr.error_queue SET status = 'resolved', updated_at = now()
     WHERE msg_id = p->>'msg_id' AND status = 'replayed';
  END IF;
  RETURN json_build_object('result', 'ok');
END $$;

-- one hospital entry per message: a failed replay re-opens the same row with the next backoff
CREATE OR REPLACE FUNCTION mbr_api.dlq(json) RETURNS json LANGUAGE plpgsql SECURITY DEFINER AS $$
DECLARE p json := $1; r boolean; eid bigint; n int;
BEGIN
  SELECT coalesce((SELECT retryable FROM mbr.reason_codes WHERE code = p->>'reason_code'), false) INTO r;
  SELECT id, replays INTO eid, n FROM mbr.error_queue WHERE msg_id = p->>'msg_id' AND status = 'replayed'
   ORDER BY id DESC LIMIT 1;
  IF eid IS NOT NULL THEN
    UPDATE mbr.error_queue SET status = 'open', reason_code = p->>'reason_code', reason_text = p->>'reason_text',
           target = p->>'target', http_status = p->>'http_status', failed_step = p->>'failed_step',
           attempts = p->>'attempts', retryable = r, updated_at = now(),
           next_retry_at = now() + make_interval(secs => mbr.cfg('hospital_sweep_every_s', '60')::int * power(2, n))
     WHERE id = eid;
  ELSE
    INSERT INTO mbr.error_queue (msg_id, rev, topic, biz_id, family, type, reason_code, reason_text, target, http_status,
                                 failed_step, attempts, payload, retryable, next_retry_at)
    VALUES (p->>'msg_id', p->>'rev', p->>'topic', p->>'biz_id', p->>'family', p->>'type', p->>'reason_code',
            p->>'reason_text', p->>'target', p->>'http_status', p->>'failed_step', p->>'attempts',
            coalesce(p->>'payload', ''), r,
            CASE WHEN r THEN now() + make_interval(secs => mbr.cfg('hospital_sweep_every_s', '60')::int) END)
    RETURNING id INTO eid;
  END IF;
  RETURN json_build_object('result', 'ok', 'id', eid::text, 'retryable', r::text);
END $$;

CREATE OR REPLACE FUNCTION mbr_api.config() RETURNS json LANGUAGE sql STABLE SECURITY DEFINER AS $$
  SELECT json_build_object('result', 'ok',
    'retry_max', mbr.cfg('retry_max', '5'), 'backoff_base_s', mbr.cfg('backoff_base_s', '2'),
    'backoff_mult', mbr.cfg('backoff_mult', '2'), 'backoff_max_s', mbr.cfg('backoff_max_s', '60'),
    'departments', mbr.cfg('departments', '101,110,120,130,140,150,160'),
    'dc_map', mbr.cfg('dc_map', '1:DC1,2:DC2'))
$$;

-- ---------------------------------------------------------------- SIMULATED merchandising system
CREATE OR REPLACE FUNCTION mbr_api.merch_items(json) RETURNS json LANGUAGE plpgsql SECURITY DEFINER AS $$
DECLARE p json := $1; f json;
BEGIN
  f := mbr.fault('merch'); IF f IS NOT NULL THEN RETURN f; END IF;
  IF NOT mbr.first_time('merch_items', p) THEN RETURN mbr.dup(); END IF;
  INSERT INTO mbr.merch_item (item, item_desc, dept, class, subclass, unit_retail, compare_at, upc, supplier, status, msg_id, rev)
  VALUES (p->>'item', p->>'item_desc', p->>'dept', p->>'class', p->>'subclass', mbr.num(p->>'unit_retail'),
          mbr.num(p->>'compare_at'), p->>'upc', p->>'supplier', p->>'status', p->>'msg_id', p->>'rev')
  ON CONFLICT (item) DO UPDATE SET item_desc = excluded.item_desc, dept = excluded.dept, class = excluded.class,
     subclass = excluded.subclass, unit_retail = excluded.unit_retail, compare_at = excluded.compare_at,
     upc = excluded.upc, supplier = excluded.supplier, status = excluded.status, msg_id = excluded.msg_id,
     rev = excluded.rev, updated_at = now();
  PERFORM mbr.http(201);
  RETURN mbr.ok();
END $$;

-- body {"items": "a,b,c"}: are all of a PO's items already in the item master?
CREATE OR REPLACE FUNCTION mbr_api.merch_items_present(json) RETURNS json LANGUAGE plpgsql SECURITY DEFINER AS $$
DECLARE p json := $1; f json; miss text[];
BEGIN
  f := mbr.fault('merch'); IF f IS NOT NULL THEN RETURN f; END IF;
  SELECT coalesce(array_agg(i ORDER BY i), '{}') INTO miss
    FROM (SELECT DISTINCT trim(x) AS i FROM unnest(string_to_array(coalesce(p->>'items', ''), ',')) x WHERE trim(x) <> '') s
   WHERE NOT EXISTS (SELECT 1 FROM mbr.merch_item m WHERE m.item = s.i);
  RETURN json_build_object('result', 'ok', 'all_present', (cardinality(miss) = 0)::text,
                           'missing', array_to_string(miss[1:20], ','), 'missing_count', cardinality(miss)::text);
END $$;

CREATE OR REPLACE FUNCTION mbr_api.po_version(po text) RETURNS json LANGUAGE sql STABLE SECURITY DEFINER AS $$
  SELECT json_build_object('result', 'ok',
    'version', coalesce((SELECT version::text FROM mbr.merch_po_header h WHERE h.po = po_version.po), '0'),
    'status', coalesce((SELECT status FROM mbr.merch_po_header h WHERE h.po = po_version.po), 'none'))
$$;

-- body: PO header fields + "lines_json": [{"line_no","item","location","loc_type","unit_cost","qty_ordered"}, ...]
CREATE OR REPLACE FUNCTION mbr_api.merch_pos(json) RETURNS json LANGUAGE plpgsql SECURITY DEFINER AS $$
DECLARE p json := $1; f json; cur int; v int := coalesce(mbr.num(p->>'version'), 1)::int;
BEGIN
  f := mbr.fault('merch'); IF f IS NOT NULL THEN RETURN f; END IF;
  IF NOT mbr.first_time('merch_pos', p) THEN RETURN mbr.dup(); END IF;
  SELECT version INTO cur FROM mbr.merch_po_header WHERE po = p->>'po';
  IF cur IS NOT NULL AND v <= cur THEN
    DELETE FROM mbr.applied WHERE target = 'merch_pos' AND msg_id = p->>'msg_id' AND rev = coalesce(p->>'rev', '1');
    PERFORM mbr.http(409);
    RETURN json_build_object('result', 'stale', 'error', 'STALE_VERSION',
                             'reason', format('PO %s v%s is not newer than v%s', p->>'po', v, cur), 'version', cur::text);
  END IF;
  INSERT INTO mbr.merch_po_header (po, version, supplier, dept, location, dc, total_cost, line_count, not_before, not_after,
                                   order_type, msg_id, rev)
  VALUES (p->>'po', v, p->>'supplier', p->>'dept', p->>'location', p->>'dc', mbr.num(p->>'total_cost'),
          mbr.num(p->>'line_count')::int, p->>'not_before', p->>'not_after', p->>'order_type', p->>'msg_id', p->>'rev')
  ON CONFLICT (po) DO UPDATE SET version = excluded.version, supplier = excluded.supplier, dept = excluded.dept,
     location = excluded.location, dc = excluded.dc, total_cost = excluded.total_cost, line_count = excluded.line_count,
     not_before = excluded.not_before, not_after = excluded.not_after, order_type = excluded.order_type,
     status = 'open', msg_id = excluded.msg_id, rev = excluded.rev, updated_at = now();
  DELETE FROM mbr.merch_po_line WHERE po = p->>'po';
  INSERT INTO mbr.merch_po_line (po, line_no, item, location, loc_type, unit_cost, qty_ordered)
  SELECT p->>'po', (l->>'line_no')::int, l->>'item', l->>'location', l->>'loc_type', mbr.num(l->>'unit_cost'),
         mbr.num(l->>'qty_ordered')
    FROM json_array_elements(coalesce(p->'lines_json', '[]'::json)) l;
  PERFORM mbr.http(201);
  RETURN mbr.ok(json_build_object('version', v::text));
END $$;

-- compensation: the warehouse rejected the PO, so the merchandising copy is cancelled
CREATE OR REPLACE FUNCTION mbr_api.merch_po_cancel(json) RETURNS json LANGUAGE plpgsql SECURITY DEFINER AS $$
DECLARE p json := $1; f json;
BEGIN
  f := mbr.fault('merch'); IF f IS NOT NULL THEN RETURN f; END IF;
  UPDATE mbr.merch_po_header SET status = 'cancelled', updated_at = now() WHERE po = p->>'po';
  RETURN mbr.ok(json_build_object('reason', coalesce(p->>'reason', '')));
END $$;

-- ---------------------------------------------------------------- SIMULATED warehouse system
CREATE OR REPLACE FUNCTION mbr_api.wh_items(json) RETURNS json LANGUAGE plpgsql SECURITY DEFINER AS $$
DECLARE p json := $1; f json;
BEGIN
  f := mbr.fault('warehouse'); IF f IS NOT NULL THEN RETURN f; END IF;
  IF NOT mbr.first_time('wh_items', p) THEN RETURN mbr.dup(); END IF;
  INSERT INTO mbr.wh_item (item, item_desc, dept, upc, vendor_contact, msg_id, rev)
  VALUES (p->>'item', p->>'item_desc', p->>'dept', p->>'upc', p->>'vendor_contact', p->>'msg_id', p->>'rev')
  ON CONFLICT (item) DO UPDATE SET item_desc = excluded.item_desc, dept = excluded.dept, upc = excluded.upc,
     vendor_contact = excluded.vendor_contact, msg_id = excluded.msg_id, rev = excluded.rev, updated_at = now();
  PERFORM mbr.http(201);
  RETURN mbr.ok();
END $$;

CREATE OR REPLACE FUNCTION mbr_api.wh_pos(json) RETURNS json LANGUAGE plpgsql SECURITY DEFINER AS $$
DECLARE p json := $1; f json;
BEGIN
  f := mbr.fault('warehouse'); IF f IS NOT NULL THEN RETURN f; END IF;
  IF coalesce(p->>'dc', '') = '' THEN
    PERFORM mbr.http(422);
    RETURN json_build_object('result', 'rejected', 'error', 'NO_DC', 'reason', 'no distribution center for location ' || coalesce(p->>'location', ''));
  END IF;
  IF NOT mbr.first_time('wh_pos', p) THEN RETURN mbr.dup(); END IF;
  INSERT INTO mbr.wh_po (po, dc, location, line_count, lines_received, msg_id, rev)
  VALUES (p->>'po', p->>'dc', p->>'location', mbr.num(p->>'line_count')::int,
          json_array_length(coalesce(p->'lines_json', '[]'::json)), p->>'msg_id', p->>'rev')
  ON CONFLICT (po) DO UPDATE SET dc = excluded.dc, location = excluded.location, line_count = excluded.line_count,
     lines_received = excluded.lines_received, msg_id = excluded.msg_id, rev = excluded.rev, updated_at = now();
  PERFORM mbr.http(201);
  RETURN mbr.ok();
END $$;

-- ---------------------------------------------------------------- SIMULATED store point of sale
CREATE OR REPLACE FUNCTION mbr_api.store_prices(json) RETURNS json LANGUAGE plpgsql SECURITY DEFINER AS $$
DECLARE p json := $1; f json; n int;
BEGIN
  f := mbr.fault('store'); IF f IS NOT NULL THEN RETURN f; END IF;
  IF NOT mbr.first_time('store_prices', p) THEN RETURN mbr.dup(); END IF;
  INSERT INTO mbr.store_price (store_id, item, unit_retail, compare_at, msg_id, rev)
  SELECT s.store_id, p->>'item', mbr.num(p->>'unit_retail'), mbr.num(p->>'compare_at'), p->>'msg_id', p->>'rev'
    FROM mbr.store s
  ON CONFLICT (store_id, item) DO UPDATE SET unit_retail = excluded.unit_retail, compare_at = excluded.compare_at,
     msg_id = excluded.msg_id, rev = excluded.rev, updated_at = now();
  GET DIAGNOSTICS n = ROW_COUNT;
  PERFORM mbr.http(201);
  RETURN mbr.ok(json_build_object('stores', n::text));
END $$;

-- ---------------------------------------------------------------- hospital operations (called by CAI processes)
-- due entries as a CSV of ids (CAI loops over tokenize()); entries past the replay limit turn 'dead'
CREATE OR REPLACE FUNCTION mbr_api.eq_due(json) RETURNS json LANGUAGE plpgsql SECURITY DEFINER AS $$
DECLARE ids text; mx int := mbr.cfg('hospital_max_replays', '3')::int;
BEGIN
  UPDATE mbr.error_queue SET status = 'dead', updated_at = now()
   WHERE status = 'open' AND retryable AND replays >= mx;
  SELECT string_agg(id::text, ',' ORDER BY id) INTO ids FROM (
    SELECT id FROM mbr.error_queue WHERE status = 'open' AND retryable AND next_retry_at <= now()
     ORDER BY id LIMIT 20) d;
  RETURN json_build_object('result', 'ok', 'ids', coalesce(ids, ''),
                           'count', coalesce(cardinality(string_to_array(ids, ',')), 0)::text);
END $$;

CREATE OR REPLACE FUNCTION mbr_api.eq_get(id bigint) RETURNS json LANGUAGE sql STABLE SECURITY DEFINER AS $$
  SELECT json_build_object('result', CASE WHEN e.id IS NULL THEN 'not_found' ELSE 'ok' END,
    'id', e.id::text, 'msg_id', e.msg_id, 'rev', e.rev, 'topic', e.topic, 'biz_id', e.biz_id, 'family', e.family,
    'type', e.type, 'payload', e.payload, 'status', e.status, 'replays', e.replays::text, 'reason_code', e.reason_code)
  FROM (SELECT 1) one LEFT JOIN mbr.error_queue e ON e.id = eq_get.id
$$;

-- body {"id", "status": replayed | discarded, "actor"}
CREATE OR REPLACE FUNCTION mbr_api.eq_mark(json) RETURNS json LANGUAGE plpgsql SECURITY DEFINER AS $$
DECLARE p json := $1; s text := p->>'status';
BEGIN
  IF s NOT IN ('replayed', 'discarded') THEN
    PERFORM mbr.http(400);
    RETURN json_build_object('result', 'error', 'error', 'BAD_STATUS', 'reason', 'status must be replayed or discarded');
  END IF;
  UPDATE mbr.error_queue SET status = s, actor = p->>'actor', updated_at = now(),
         replays = replays + CASE WHEN s = 'replayed' THEN 1 ELSE 0 END
   WHERE id = (p->>'id')::bigint;
  RETURN json_build_object('result', 'ok', 'status', s);
END $$;

-- ---------------------------------------------------------------- drill + reset helpers (called by verify/, not by CAI)
-- body {"target": merch | warehouse | store, "mode": down | slow | reject, "seconds": 120}
CREATE OR REPLACE FUNCTION mbr_api.set_fault(json) RETURNS json LANGUAGE plpgsql SECURITY DEFINER AS $$
DECLARE p json := $1;
BEGIN
  INSERT INTO mbr.standin_fault (target, mode, until)
  VALUES (p->>'target', p->>'mode', now() + make_interval(secs => coalesce(mbr.num(p->>'seconds'), 120)))
  ON CONFLICT (target) DO UPDATE SET mode = excluded.mode, until = excluded.until;
  RETURN json_build_object('result', 'ok');
END $$;

CREATE OR REPLACE FUNCTION mbr_api.clear_faults(json) RETURNS json LANGUAGE sql SECURITY DEFINER AS $$
  WITH d AS (DELETE FROM mbr.standin_fault RETURNING 1) SELECT json_build_object('result', 'ok', 'cleared', count(*)::text) FROM d
$$;

CREATE OR REPLACE FUNCTION mbr_api.reset_demo(json) RETURNS json LANGUAGE plpgsql SECURITY DEFINER AS $$
BEGIN
  TRUNCATE mbr.events, mbr.error_queue, mbr.applied, mbr.standin_fault, mbr.merch_item, mbr.merch_po_header,
           mbr.merch_po_line, mbr.wh_item, mbr.wh_po, mbr.store_price RESTART IDENTITY;
  RETURN json_build_object('result', 'ok');
END $$;

-- ---------------------------------------------------------------- read views (verify/ and dashboards/)
CREATE OR REPLACE VIEW mbr_api.events AS SELECT * FROM mbr.events;
CREATE OR REPLACE VIEW mbr_api.error_queue AS
  SELECT id, created_at, msg_id, rev, topic, biz_id, family, type, reason_code, reason_text, target, http_status,
         failed_step, attempts, retryable, status, replays, next_retry_at, updated_at, actor, length(payload) AS payload_bytes
    FROM mbr.error_queue;
CREATE OR REPLACE VIEW mbr_api.targets AS
  SELECT 'merch_item' AS tbl, count(*) AS n FROM mbr.merch_item UNION ALL
  SELECT 'merch_po_header', count(*) FROM mbr.merch_po_header UNION ALL
  SELECT 'merch_po_line', count(*) FROM mbr.merch_po_line UNION ALL
  SELECT 'wh_item', count(*) FROM mbr.wh_item UNION ALL
  SELECT 'wh_po', count(*) FROM mbr.wh_po UNION ALL
  SELECT 'store_price', count(*) FROM mbr.store_price UNION ALL
  SELECT 'applied', count(*) FROM mbr.applied;
CREATE OR REPLACE VIEW mbr_api.po_status AS
  SELECT h.po, h.version, h.status, h.dc, h.line_count, (SELECT count(*) FROM mbr.merch_po_line l WHERE l.po = h.po) AS merch_lines,
         w.lines_received AS wh_lines, h.updated_at
    FROM mbr.merch_po_header h LEFT JOIN mbr.wh_po w ON w.po = h.po;
CREATE OR REPLACE VIEW mbr_api.dash_flow AS
  SELECT date_trunc('minute', at) AS minute, stage, target, status, count(*) AS n FROM mbr.events GROUP BY 1, 2, 3, 4;
CREATE OR REPLACE VIEW mbr_api.dash_error_queue AS
  SELECT reason_code, status, retryable, count(*) AS n, max(updated_at) AS last_change FROM mbr.error_queue GROUP BY 1, 2, 3;

-- ---------------------------------------------------------------- grants
GRANT USAGE ON SCHEMA mbr_api TO mbr_api_anon;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA mbr_api TO mbr_api_anon;
GRANT SELECT ON ALL TABLES IN SCHEMA mbr_api TO mbr_api_anon;
-- the nightly batch reads the target tables (read only)
GRANT USAGE ON SCHEMA mbr TO mbr_batch_reader;
GRANT SELECT ON mbr.merch_item, mbr.merch_po_header, mbr.merch_po_line, mbr.events, mbr.error_queue TO mbr_batch_reader;

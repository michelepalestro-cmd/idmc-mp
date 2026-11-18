-- Seed: settings, reason codes (which errors the hospital retries by itself) and the simulated stores.
INSERT INTO mbr.config (key, value) VALUES
  ('retry_max', '5'), ('backoff_base_s', '2'), ('backoff_mult', '2'), ('backoff_max_s', '60'),
  ('hospital_sweep_every_s', '60'), ('hospital_max_replays', '3'),
  ('departments', '101,110,120,130,140,150,160'),
  ('dc_map', '1:DC1,2:DC2')                -- first digit of the PO ship-to location -> distribution center
ON CONFLICT (key) DO NOTHING;

INSERT INTO mbr.reason_codes (code, retryable, meaning) VALUES
  ('MERCH_UNAVAILABLE',     true,  'merchandising system down or timed out after every retry'),
  ('WAREHOUSE_UNAVAILABLE', true,  'warehouse system down or timed out after every retry'),
  ('STORE_UNAVAILABLE',     true,  'store POS down or timed out after every retry'),
  ('ITEMS_MISSING',         true,  'a PO arrived before its items: replayed once the items exist (dependency wait)'),
  ('KAFKA_PUBLISH_FAILED',  true,  'the JMS-to-Kafka bridge could not publish'),
  ('VALIDATION_FAILED',     false, 'business rules failed (check digit, price, department, required fields)'),
  ('PO_INCOMPLETE',         false, 'PO header totals do not match its lines'),
  ('MALFORMED_XML',         false, 'the message could not be parsed (poison message)'),
  ('REJECTED',              false, 'a target refused the message (4xx)'),
  ('NO_DC',                 false, 'no distribution center for the ship-to location'),
  ('CAI_FAULT',             false, 'an unexpected fault in a CAI process')
ON CONFLICT (code) DO NOTHING;

INSERT INTO mbr.store (store_id, name) VALUES
  ('S001', 'Store 1'), ('S002', 'Store 2'), ('S003', 'Store 3'), ('S004', 'Store 4'), ('S005', 'Store 5')
ON CONFLICT (store_id) DO NOTHING;

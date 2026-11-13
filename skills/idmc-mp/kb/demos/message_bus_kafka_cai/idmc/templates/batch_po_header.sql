SELECT po AS "PO", version AS "VERSION", status AS "STATUS", supplier AS "SUPPLIER", dept AS "DEPT", location AS "LOCATION",
       dc AS "DC", total_cost AS "TOTAL_COST", line_count AS "LINE_COUNT", updated_at AS "UPDATED_AT",
       to_char(now(), 'YYYYMMDD"T"HH24MISS') AS "BATCH_RUN"
  FROM mbr.merch_po_header

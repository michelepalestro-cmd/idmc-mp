SELECT l.po AS "PO", l.line_no AS "LINE_NO", l.item AS "ITEM", l.location AS "LOCATION", l.unit_cost AS "UNIT_COST",
       l.qty_ordered AS "QTY_ORDERED", to_char(now(), 'YYYYMMDD"T"HH24MISS') AS "BATCH_RUN"
  FROM mbr.merch_po_line l JOIN mbr.merch_po_header h ON h.po = l.po
 WHERE h.status <> 'cancelled'

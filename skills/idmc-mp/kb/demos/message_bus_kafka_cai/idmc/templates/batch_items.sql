SELECT item AS "ITEM", item_desc AS "ITEM_DESC", dept AS "DEPT", class AS "CLASS", subclass AS "SUBCLASS",
       unit_retail AS "UNIT_RETAIL", compare_at AS "COMPARE_AT", upc AS "UPC", supplier AS "SUPPLIER", status AS "STATUS",
       updated_at AS "UPDATED_AT", to_char(now(), 'YYYYMMDD"T"HH24MISS') AS "BATCH_RUN"
  FROM mbr.merch_item

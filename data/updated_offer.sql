/* ------------------------------------------------------------------
   Trade-in offer test query – join on both Stock ID and Email
   ------------------------------------------------------------------ */
WITH customer_keys AS (
    SELECT '20541' AS stock_id, 'odin_castillo@hotmail.com' AS email
    UNION ALL SELECT '19573' AS stock_id, 'dralizmi@gmail.com' AS email
    UNION ALL SELECT '13993' AS stock_id, 'varaflox@hotmail.com' AS email
    UNION ALL SELECT '18829' AS stock_id, 'jorgegg1325@hotmail.com' AS email
    UNION ALL SELECT '20232' AS stock_id, 'ibisa_rojo2@hotmail.com' AS email
)
SELECT DISTINCT
    ck.stock_id,
    si.email,
    si.new_register_trade_in_offer,
    ih.sku,
    si.last_register_brand_name,
    si.last_register_model_name
FROM customer_keys ck
JOIN serving.inventory_history ih ON ih.stock_id = ck.stock_id
JOIN growth_global_landing.supply_intermediate si
     ON ih.sku = si.last_register_sku
     AND si.email = ck.email                     -- extra email match
WHERE si.new_register_trade_in_offer IS NOT NULL;
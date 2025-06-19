SELECT DISTINCT
    ranked.stock_id,
    ranked.kilometers,
    ranked.regular_published_price_financing,
    ranked.promotion_published_price_financing,
    ranked.region_name, 
    dcs.car_brand,
    dcs.model,
    dcs.year,
    dcs.version,
    dcs.color,
    pg.region_growth,
    pg.hub_name,
    CASE 
        WHEN ranked.promotion_published_price_financing IS NOT NULL 
         AND ranked.promotion_published_price_financing < ranked.regular_published_price_financing 
        THEN TRUE 
        ELSE FALSE 
    END AS has_promotion_discount,
    ABS(ranked.regular_published_price_financing - ranked.promotion_published_price_financing) AS price_difference_abs
FROM (
    SELECT *,
           ROW_NUMBER() OVER (
               PARTITION BY stock_id 
               ORDER BY inventory_date DESC
           ) as rn
    FROM serving.inventory_history
    WHERE inventory_status IN ('available', 'preloaded') 
      AND country_iso = 'MX'
      AND flag_published = TRUE
      AND region_name IS NOT NULL
      AND region_name != 'São Paulo'
      AND inventory_date >= CURRENT_DATE -1
) ranked
JOIN dwh.dim_car_stock dcs ON ranked.stock_id = dcs.bk_car_stock
JOIN playground.dl_region_growth_playground pg ON ranked.hub_name = pg.hub_name
WHERE ranked.rn = 1;
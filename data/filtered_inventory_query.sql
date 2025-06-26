-- Filtered inventory query for trade-up candidates
-- Parameters: year, price, kilometers (passed as positional %s)
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
      AND inventory_date >= CURRENT_DATE - 3
) ranked
JOIN dwh.dim_car_stock dcs ON ranked.stock_id = dcs.bk_car_stock
JOIN playground.dl_region_growth_playground pg ON ranked.hub_name = pg.hub_name
WHERE ranked.rn = 1
    AND dcs.year >= %s
    AND COALESCE(
        CASE 
            WHEN ranked.promotion_published_price_financing < ranked.regular_published_price_financing 
            THEN ranked.promotion_published_price_financing
            ELSE ranked.regular_published_price_financing
        END, 
        ranked.regular_published_price_financing
    ) > %s
    AND ranked.kilometers < %s
ORDER BY dcs.year DESC, ranked.regular_published_price_financing DESC
LIMIT 1000;  -- Safety limit to prevent memory issues
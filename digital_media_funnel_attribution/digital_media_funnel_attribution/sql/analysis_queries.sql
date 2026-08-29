-- ============================================================
-- Digital Media Funnel & Channel Attribution — Core SQL Queries
-- Target: media_funnel.db (SQLite) — created by 02_load_to_sql.py
-- ============================================================

-- 1. Overall funnel: impressions -> clicks -> views -> redemptions
SELECT
    COUNT(*)                                     AS impressions,
    SUM(clicked)                                 AS clicks,
    SUM(viewed)                                  AS offer_views,
    SUM(redeemed)                                AS redemptions,
    ROUND(100.0 * SUM(clicked) / COUNT(*), 2)    AS ctr_pct,
    ROUND(100.0 * SUM(viewed) / NULLIF(SUM(clicked),0), 2)   AS click_to_view_pct,
    ROUND(100.0 * SUM(redeemed) / NULLIF(SUM(viewed),0), 2)  AS view_to_redeem_pct,
    ROUND(100.0 * SUM(redeemed) / COUNT(*), 3)   AS overall_redemption_pct
FROM funnel_exposures;


-- 2. Funnel by channel — the core comparison table
SELECT
    channel_name,
    channel_type,
    COUNT(*)                                      AS impressions,
    SUM(clicked)                                  AS clicks,
    SUM(viewed)                                   AS offer_views,
    SUM(redeemed)                                 AS redemptions,
    ROUND(100.0 * SUM(clicked) / COUNT(*), 2)     AS ctr_pct,
    ROUND(100.0 * SUM(redeemed) / COUNT(*), 3)    AS redemption_rate_pct,
    ROUND(SUM(cost), 2)                           AS total_cost,
    ROUND(SUM(redemption_value), 2)               AS total_redeemed_value
FROM funnel_exposures
GROUP BY channel_name, channel_type
ORDER BY redemption_rate_pct DESC;


-- 3. Channel-level unit economics: CPC, CPV, CAC (cost per redemption), ROAS
SELECT
    channel_name,
    ROUND(SUM(cost) / NULLIF(SUM(clicked), 0), 4)          AS cost_per_click,
    ROUND(SUM(cost) / NULLIF(SUM(viewed), 0), 4)           AS cost_per_offer_view,
    ROUND(SUM(cost) / NULLIF(SUM(redeemed), 0), 4)         AS cost_per_redemption_cac,
    ROUND(SUM(redemption_value) / NULLIF(SUM(cost), 0), 1) AS transaction_value_per_dollar_spent
FROM funnel_exposures
GROUP BY channel_name
ORDER BY cost_per_redemption_cac ASC;


-- 4. Drop-off analysis: where does each channel lose people in the funnel?
SELECT
    channel_name,
    COUNT(*)                                                  AS impressions,
    ROUND(100.0 * (COUNT(*) - SUM(clicked)) / COUNT(*), 1)    AS pct_lost_before_click,
    ROUND(100.0 * (SUM(clicked) - SUM(viewed)) / NULLIF(SUM(clicked),0), 1)  AS pct_lost_after_click,
    ROUND(100.0 * (SUM(viewed) - SUM(redeemed)) / NULLIF(SUM(viewed),0), 1)  AS pct_lost_after_view
FROM funnel_exposures
GROUP BY channel_name
ORDER BY impressions DESC;


-- 5. Redemption rate by category, within each channel type (owned vs paid)
SELECT
    channel_type,
    category,
    COUNT(*) AS impressions,
    ROUND(100.0 * SUM(redeemed) / COUNT(*), 3) AS redemption_rate_pct
FROM funnel_exposures
GROUP BY channel_type, category
ORDER BY channel_type, redemption_rate_pct DESC;


-- 6. Monthly funnel trend (impressions, redemptions, blended CAC)
SELECT
    strftime('%Y-%m', impression_date) AS month,
    COUNT(*) AS impressions,
    SUM(redeemed) AS redemptions,
    ROUND(SUM(cost), 2) AS total_cost,
    ROUND(SUM(cost) / NULLIF(SUM(redeemed), 0), 4) AS blended_cac
FROM funnel_exposures
GROUP BY month
ORDER BY month;


-- 7. Best-converting channel per category (which channel to use for which offer type)
SELECT category, channel_name, redemption_rate_pct FROM (
    SELECT
        category,
        channel_name,
        redemption_rate_pct,
        RANK() OVER (PARTITION BY category ORDER BY redemption_rate_pct DESC) AS rnk
    FROM (
        SELECT
            category,
            channel_name,
            ROUND(100.0 * SUM(redeemed) / COUNT(*), 3) AS redemption_rate_pct
        FROM funnel_exposures
        GROUP BY category, channel_name
    )
) WHERE rnk = 1
ORDER BY category;

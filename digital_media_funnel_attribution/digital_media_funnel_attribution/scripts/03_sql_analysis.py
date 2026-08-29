"""
03_sql_analysis.py
Runs the core analysis queries against
media_funnel.db and exports each result as a CSV in outputs/sql_results/


"""

import os
import sqlite3

import pandas as pd

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
DB_PATH = os.path.join(BASE_DIR, "media_funnel.db")
OUT_DIR = os.path.join(BASE_DIR, "outputs", "sql_results")
os.makedirs(OUT_DIR, exist_ok=True)

conn = sqlite3.connect(DB_PATH)

queries = {
    "overall_funnel": """
        SELECT COUNT(*) AS impressions, SUM(clicked) AS clicks, SUM(viewed) AS offer_views,
               SUM(redeemed) AS redemptions,
               ROUND(100.0*SUM(clicked)/COUNT(*),2) AS ctr_pct,
               ROUND(100.0*SUM(viewed)/NULLIF(SUM(clicked),0),2) AS click_to_view_pct,
               ROUND(100.0*SUM(redeemed)/NULLIF(SUM(viewed),0),2) AS view_to_redeem_pct,
               ROUND(100.0*SUM(redeemed)/COUNT(*),3) AS overall_redemption_pct
        FROM funnel_exposures;
    """,
    "funnel_by_channel": """
        SELECT channel_name, channel_type, COUNT(*) AS impressions, SUM(clicked) AS clicks,
               SUM(viewed) AS offer_views, SUM(redeemed) AS redemptions,
               ROUND(100.0*SUM(clicked)/COUNT(*),2) AS ctr_pct,
               ROUND(100.0*SUM(redeemed)/COUNT(*),3) AS redemption_rate_pct,
               ROUND(SUM(cost),2) AS total_cost, ROUND(SUM(redemption_value),2) AS total_redeemed_value
        FROM funnel_exposures GROUP BY channel_name, channel_type
        ORDER BY redemption_rate_pct DESC;
    """,
    "channel_unit_economics": """
        SELECT channel_name,
               ROUND(SUM(cost)/NULLIF(SUM(clicked),0),4) AS cost_per_click,
               ROUND(SUM(cost)/NULLIF(SUM(viewed),0),4) AS cost_per_offer_view,
               ROUND(SUM(cost)/NULLIF(SUM(redeemed),0),4) AS cost_per_redemption_cac,
               ROUND(SUM(redemption_value)/NULLIF(SUM(cost),0),1) AS transaction_value_per_dollar_spent
        FROM funnel_exposures GROUP BY channel_name
        ORDER BY cost_per_redemption_cac ASC;
    """,
    "dropoff_by_channel": """
        SELECT channel_name, COUNT(*) AS impressions,
               ROUND(100.0*(COUNT(*)-SUM(clicked))/COUNT(*),1) AS pct_lost_before_click,
               ROUND(100.0*(SUM(clicked)-SUM(viewed))/NULLIF(SUM(clicked),0),1) AS pct_lost_after_click,
               ROUND(100.0*(SUM(viewed)-SUM(redeemed))/NULLIF(SUM(viewed),0),1) AS pct_lost_after_view
        FROM funnel_exposures GROUP BY channel_name ORDER BY impressions DESC;
    """,
    "redemption_by_channel_type_category": """
        SELECT channel_type, category, COUNT(*) AS impressions,
               ROUND(100.0*SUM(redeemed)/COUNT(*),3) AS redemption_rate_pct
        FROM funnel_exposures GROUP BY channel_type, category
        ORDER BY channel_type, redemption_rate_pct DESC;
    """,
    "monthly_trend": """
        SELECT strftime('%Y-%m', impression_date) AS month, COUNT(*) AS impressions,
               SUM(redeemed) AS redemptions, ROUND(SUM(cost),2) AS total_cost,
               ROUND(SUM(cost)/NULLIF(SUM(redeemed),0),4) AS blended_cac
        FROM funnel_exposures GROUP BY month ORDER BY month;
    """,
    "best_channel_per_category": """
        SELECT category, channel_name, redemption_rate_pct FROM (
            SELECT category, channel_name, redemption_rate_pct,
                   RANK() OVER (PARTITION BY category ORDER BY redemption_rate_pct DESC) AS rnk
            FROM (
                SELECT category, channel_name,
                       ROUND(100.0*SUM(redeemed)/COUNT(*),3) AS redemption_rate_pct
                FROM funnel_exposures GROUP BY category, channel_name
            )
        ) WHERE rnk = 1 ORDER BY category;
    """,
}

for name, q in queries.items():
    df = pd.read_sql_query(q, conn)
    df.to_csv(f"{OUT_DIR}/{name}.csv", index=False)
    print(f"\n=== {name} ===")
    print(df.to_string(index=False))

conn.close()
print(f"\nAll results exported to {OUT_DIR}/ (import these into Power BI)")

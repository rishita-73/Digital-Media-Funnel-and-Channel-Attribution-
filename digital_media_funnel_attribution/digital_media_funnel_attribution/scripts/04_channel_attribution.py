"""
04_channel_attribution.py
Ranks channels by efficiency (CAC), identifies the best-converting channel,
and runs a budget-reallocation "what-if" simulation: what happens if spend
shifts from the worst-performing paid channels to the best-performing
owned channels?

Important honesty note baked into this script's output: "revenue" here is
the customer's transaction value at the merchant, not Amex's own booked
revenue (which would be a fraction of that, e.g. interchange). The
reallocation simulation also assumes constant CAC as spend shifts, which
is optimistic — owned channels (Push, In-App) have a natural impression
ceiling (active app users), so real reallocation would hit diminishing
returns well before the naive math suggests. Both caveats are printed
explicitly and included in the exported summary.

Run:    python 04_channel_attribution.py
Output: outputs/channel_ranking.csv, outputs/reallocation_simulation.csv
"""

import os
import sqlite3

import pandas as pd

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
DB_PATH = os.path.join(BASE_DIR, "media_funnel.db")
OUT_DIR = os.path.join(BASE_DIR, "outputs")
os.makedirs(OUT_DIR, exist_ok=True)

conn = sqlite3.connect(DB_PATH)
df = pd.read_sql_query("SELECT * FROM funnel_exposures", conn)
conn.close()

# ---------------------------------------------------------------
# 1. Channel ranking
# ---------------------------------------------------------------
ranking = df.groupby("channel_name").agg(
    channel_type=("channel_type", "first"),
    impressions=("exposure_id", "count"),
    clicks=("clicked", "sum"),
    redemptions=("redeemed", "sum"),
    total_cost=("cost", "sum"),
    total_transaction_value=("redemption_value", "sum"),
).reset_index()

ranking["ctr_pct"] = (ranking["clicks"] / ranking["impressions"] * 100).round(2)
ranking["redemption_rate_pct"] = (ranking["redemptions"] / ranking["impressions"] * 100).round(3)
ranking["cac"] = (ranking["total_cost"] / ranking["redemptions"]).round(4)
ranking["value_per_dollar_spent"] = (ranking["total_transaction_value"] / ranking["total_cost"]).round(1)
ranking = ranking.sort_values("cac").reset_index(drop=True)
ranking["efficiency_rank"] = ranking.index + 1

ranking.to_csv(f"{OUT_DIR}/channel_ranking.csv", index=False)

print("=" * 70)
print("CHANNEL EFFICIENCY RANKING (by cost per redemption / CAC)")
print("=" * 70)
print(ranking[["efficiency_rank", "channel_name", "channel_type", "impressions",
                "redemption_rate_pct", "cac", "value_per_dollar_spent"]].to_string(index=False))

best_channel = ranking.iloc[0]
worst_channel = ranking.iloc[-1]
print(f"\nBest-converting channel by CAC : {best_channel['channel_name']} "
      f"(${best_channel['cac']:.4f} per redemption)")
print(f"Worst-converting channel by CAC: {worst_channel['channel_name']} "
      f"(${worst_channel['cac']:.4f} per redemption, "
      f"{worst_channel['cac']/best_channel['cac']:.0f}x more expensive)")

# ---------------------------------------------------------------
# 2. Budget reallocation "what-if" simulation
# ---------------------------------------------------------------
SHIFT_PCT = 0.15  # move 15% of spend out of the two worst paid channels
WORST = ["Display Ad", "Social Media Ad"]
BEST = ["Push Notification", "In-App Banner"]

r = ranking.set_index("channel_name")

shifted_budget = 0.0
redemptions_lost = 0.0
for ch in WORST:
    amt = r.loc[ch, "total_cost"] * SHIFT_PCT
    shifted_budget += amt
    redemptions_lost += amt / r.loc[ch, "cac"]

redemptions_gained = 0.0
per_channel_budget = shifted_budget / len(BEST)
for ch in BEST:
    redemptions_gained += per_channel_budget / r.loc[ch, "cac"]

net_redemption_change = redemptions_gained - redemptions_lost

sim = pd.DataFrame([{
    "shift_pct_of_worst_channel_spend": SHIFT_PCT,
    "budget_shifted": round(shifted_budget, 2),
    "estimated_redemptions_lost_from_worst_channels": round(redemptions_lost, 1),
    "estimated_redemptions_gained_in_best_channels": round(redemptions_gained, 1),
    "net_redemption_change": round(net_redemption_change, 1),
}])
sim.to_csv(f"{OUT_DIR}/reallocation_simulation.csv", index=False)

print("\n" + "=" * 70)
print(f"WHAT-IF: shift {SHIFT_PCT:.0%} of Display Ad + Social Media Ad spend")
print(f"         into Push Notification + In-App Banner")
print("=" * 70)
print(f"Budget shifted                    : ${shifted_budget:,.2f}")
print(f"Redemptions lost (worst channels)  : ~{redemptions_lost:,.0f}")
print(f"Redemptions gained (best channels) : ~{redemptions_gained:,.0f}")
print(f"Net redemption change              : ~{net_redemption_change:,.0f}")
print("\nCAVEATS (state these explicitly if you present this number):")
print(" 1. 'Transaction value' above is the customer's merchant spend, not")
print("    Amex's own booked revenue — Amex would earn a fraction of that")
print("    (e.g. interchange), not the full amount.")
print(" 2. This simulation holds each channel's CAC constant as spend shifts.")
print("    In reality, owned channels (Push, In-App) have a hard ceiling —")
print("    you can't reach more people than have the app open — so real")
print("    reallocation would hit diminishing returns well before this.")
print("    Treat the net change as DIRECTIONAL, not a literal forecast.")

"""
01_generate_data.py
Generates a synthetic digital-media-funnel dataset for Amex Offers:
customers, channels, and funnel_exposures (the fact table — an impression
that may progress through click -> offer view -> redemption).

Why synthetic: real channel-level media performance data isn't public.
This generator uses a probability model per funnel stage (channel base
rate x customer engagement x category appeal) so the channel differences
you'll see downstream are real, explainable signal — e.g. owned channels
(Push, In-App) converting better than paid reach channels (Display, Social)
— not random noise.

Run:    python 01_generate_data.py
Output: data/customers.csv, data/channels.csv, data/funnel_exposures.csv
"""

import os
import random
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

# ---------------- CONFIG ----------------
SEED = 42
N_CUSTOMERS = 5000
N_EXPOSURES = 80000
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

np.random.seed(SEED)
random.seed(SEED)
os.makedirs(OUTPUT_DIR, exist_ok=True)

CATEGORIES = ["Dining", "Travel", "Grocery", "Retail", "Entertainment",
              "Electronics", "Fuel", "Health & Wellness"]
CATEGORY_APPEAL = {
    "Dining": 0.85, "Grocery": 0.80, "Fuel": 0.70, "Retail": 0.60,
    "Entertainment": 0.55, "Health & Wellness": 0.50,
    "Travel": 0.45, "Electronics": 0.35,
}
INCOME_BRACKETS = ["Low", "Mid", "High", "Affluent"]
INCOME_WEIGHT = {"Low": 0.20, "Mid": 0.45, "High": 0.25, "Affluent": 0.10}
CARD_TYPES = ["Green", "Gold", "Platinum", "Centurion"]

# channel_name: (channel_type, cost_per_impression, impression_share,
#                base_click_rate, base_view_given_click, base_redeem_given_view)
CHANNELS = {
    "Push Notification": ("Owned", 0.0010, 0.15, 0.120, 0.80, 0.35),
    "In-App Banner":     ("Owned", 0.0015, 0.07, 0.150, 0.85, 0.40),
    "Email":              ("Owned", 0.0020, 0.20, 0.060, 0.70, 0.30),
    "SMS":                 ("Paid",  0.0500, 0.03, 0.080, 0.75, 0.32),
    "Social Media Ad":    ("Paid",  0.0120, 0.25, 0.025, 0.55, 0.18),
    "Display Ad":          ("Paid",  0.0080, 0.30, 0.008, 0.45, 0.15),
}


def sigmoid(x):
    return 1 / (1 + np.exp(-x))


def clip(p, lo, hi):
    return np.clip(p, lo, hi)


# ---------------------------------------------------------------
# 1. CUSTOMERS
# ---------------------------------------------------------------
print("Generating customers...")
customer_ids = [f"C{100000+i}" for i in range(N_CUSTOMERS)]
income = np.random.choice(INCOME_BRACKETS, size=N_CUSTOMERS,
                           p=[INCOME_WEIGHT[b] for b in INCOME_BRACKETS])
tenure_months = np.random.randint(1, 181, size=N_CUSTOMERS)
age = np.clip(np.random.normal(38, 11, size=N_CUSTOMERS).astype(int), 21, 75)
card_type = np.random.choice(CARD_TYPES, size=N_CUSTOMERS, p=[0.40, 0.35, 0.20, 0.05])

income_score_map = {"Low": 0.1, "Mid": 0.35, "High": 0.65, "Affluent": 0.9}
income_score = np.array([income_score_map[b] for b in income])
tenure_score = tenure_months / 180

propensity = np.clip(
    0.15 * income_score + 0.15 * tenure_score
    + np.random.normal(0, 0.18, N_CUSTOMERS) + 0.35,
    0.02, 0.98,
)

customers = pd.DataFrame({
    "customer_id": customer_ids,
    "age": age,
    "gender": np.random.choice(["M", "F"], size=N_CUSTOMERS, p=[0.52, 0.48]),
    "income_bracket": income,
    "tenure_months": tenure_months,
    "card_type": card_type,
})
customers.to_csv(f"{OUTPUT_DIR}/customers.csv", index=False)
_propensity_lookup = dict(zip(customer_ids, propensity))
income_mult = {"Low": 0.7, "Mid": 1.0, "High": 1.6, "Affluent": 2.4}

# ---------------------------------------------------------------
# 2. CHANNELS
# ---------------------------------------------------------------
print("Generating channels...")
channels = pd.DataFrame([
    {
        "channel_id": f"CH{i+1}",
        "channel_name": name,
        "channel_type": cfg[0],
        "cost_per_impression": cfg[1],
        "impression_share": cfg[2],
        "base_click_rate": cfg[3],
        "base_view_given_click": cfg[4],
        "base_redeem_given_view": cfg[5],
    }
    for i, (name, cfg) in enumerate(CHANNELS.items())
])
channels.to_csv(f"{OUTPUT_DIR}/channels.csv", index=False)

channel_names = list(CHANNELS.keys())
channel_weights = [CHANNELS[c][2] for c in channel_names]

# ---------------------------------------------------------------
# 3. FUNNEL EXPOSURES (fact table)
# ---------------------------------------------------------------
print("Generating funnel exposures (this is the largest table)...")
start_base = datetime(2024, 1, 1)

exp_customer = np.random.choice(customer_ids, size=N_EXPOSURES)
exp_channel = np.random.choice(channel_names, size=N_EXPOSURES, p=channel_weights)
exp_category = np.random.choice(CATEGORIES, size=N_EXPOSURES)

rows = []
for i in range(N_EXPOSURES):
    cust = exp_customer[i]
    ch = exp_channel[i]
    cat = exp_category[i]
    ch_type, cost_pi, _, base_click, base_view, base_redeem = CHANNELS[ch]

    prop = _propensity_lookup[cust]
    appeal = CATEGORY_APPEAL[cat]

    # Stage 1: impression -> click
    click_mult = 0.5 + prop
    p_click = clip(base_click * click_mult, 0.0005, 0.95)
    clicked = np.random.rand() < p_click

    viewed = False
    redeemed = False
    redemption_value = 0.0
    click_date = view_date = redemption_date = None

    impression_date = start_base + timedelta(days=int(np.random.randint(0, 560)))

    if clicked:
        click_date = impression_date + timedelta(days=int(np.random.randint(0, 2)))

        # Stage 2: click -> offer view
        view_mult = 0.7 + 0.6 * prop
        p_view = clip(base_view * view_mult, 0.01, 0.98)
        viewed = np.random.rand() < p_view

        if viewed:
            view_date = click_date + timedelta(days=int(np.random.randint(0, 2)))

            # Stage 3: view -> redemption
            redeem_mult = (0.7 + 0.6 * prop) * (0.6 + 0.7 * appeal)
            p_redeem = clip(base_redeem * redeem_mult, 0.01, 0.9)
            redeemed = np.random.rand() < p_redeem

            if redeemed:
                redemption_date = view_date + timedelta(days=int(np.random.randint(0, 15)))
                base_value = np.random.uniform(30, 120)
                cust_income = customers.loc[customers.customer_id == cust, "income_bracket"].values[0]
                redemption_value = round(base_value * income_mult[cust_income], 2)

    cost = round(cost_pi, 5)

    rows.append((
        f"E{1000000+i}", cust, ch, ch_type, cat,
        impression_date.date(),
        int(clicked), click_date.date() if click_date else None,
        int(viewed), view_date.date() if view_date else None,
        int(redeemed), redemption_date.date() if redemption_date else None,
        redemption_value, cost,
    ))

    if (i + 1) % 20000 == 0:
        print(f"  ...{i+1}/{N_EXPOSURES} exposures generated")

exposures = pd.DataFrame(rows, columns=[
    "exposure_id", "customer_id", "channel_name", "channel_type", "category",
    "impression_date", "clicked", "click_date", "viewed", "view_date",
    "redeemed", "redemption_date", "redemption_value", "cost",
])
exposures.to_csv(f"{OUTPUT_DIR}/funnel_exposures.csv", index=False)

print("\nDone. Files written to ./data/")
print(f"  customers.csv         : {len(customers):,} rows")
print(f"  channels.csv           : {len(channels):,} rows")
print(f"  funnel_exposures.csv   : {len(exposures):,} rows")
print(f"\n  Overall click rate     : {exposures['clicked'].mean():.2%}")
print(f"  Overall view rate      : {(exposures['viewed'].sum()/exposures['clicked'].sum()):.2%} (of clicks)")
print(f"  Overall redemption rate: {exposures['redeemed'].mean():.2%} (of impressions)")
print(f"  Total media spend      : ${exposures['cost'].sum():,.2f}")
print(f"  Total redeemed revenue : ${exposures['redemption_value'].sum():,.2f}")

"""
05_visualize.py
Generates the core charts: overall funnel, channel comparison (CAC and
redemption rate), and funnel drop-off by channel.

Run:    python 05_visualize.py
Output: outputs/charts/*.png
"""

import os

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
SQL_DIR = os.path.join(BASE_DIR, "outputs", "sql_results")
OUT_DIR = os.path.join(BASE_DIR, "outputs", "charts")
os.makedirs(OUT_DIR, exist_ok=True)
sns.set_theme(style="whitegrid")

# ---------------------------------------------------------------
# 1. Overall funnel chart, two panels since impressions dwarf the rest:
#    Panel A = Impressions -> Clicks (impressions as 100% base)
#    Panel B = Clicks -> Views -> Redemptions (clicks as 100% base, "zoomed in")
#    This is standard practice for funnels where top-of-funnel volume is
#    orders of magnitude larger than bottom-of-funnel — a single linear
#    scale would make the bottom stages invisible.
# ---------------------------------------------------------------
overall = pd.read_csv(os.path.join(SQL_DIR, "overall_funnel.csv")).iloc[0]

fig, axes = plt.subplots(1, 2, figsize=(12, 5))

# Panel A
stages_a = ["Impressions", "Clicks"]
values_a = [overall["impressions"], overall["clicks"]]
max_a = values_a[0]
colors_a = ["#2b6cb0", "#5a9bd4"]
for i, (stage, val) in enumerate(zip(stages_a, values_a)):
    width = val / max_a
    left = (1 - width) / 2
    axes[0].barh(i, width, height=0.6, color=colors_a[i], left=left)
    label = f"{stage}: {val:,.0f} ({val/max_a:.1%})"
    if width < 0.25:
        axes[0].text(left + width + 0.02, i, label,
                     ha="left", va="center", fontsize=10, fontweight="bold", color="#333333")
    else:
        axes[0].text(0.5, i, label, ha="center", va="center",
                     fontsize=10, fontweight="bold", color="white")
axes[0].set_yticks([])
axes[0].set_xticks([])
axes[0].set_xlim(0, 1)
axes[0].invert_yaxis()
axes[0].set_title("Top of Funnel\n(% of Impressions)")
for spine in axes[0].spines.values():
    spine.set_visible(False)

# Panel B — zoomed in, clicks as the 100% base
stages_b = ["Clicks", "Offer Views", "Redemptions"]
values_b = [overall["clicks"], overall["offer_views"], overall["redemptions"]]
max_b = values_b[0]
colors_b = ["#5a9bd4", "#8fc1e3", "#1f4e79"]
for i, (stage, val) in enumerate(zip(stages_b, values_b)):
    width = val / max_b
    axes[1].barh(i, width, height=0.6, color=colors_b[i], left=(1 - width) / 2)
    axes[1].text(0.5, i, f"{stage}\n{val:,.0f} ({val/max_b:.1%})",
                 ha="center", va="center", fontsize=10, fontweight="bold", color="white")
axes[1].set_yticks([])
axes[1].set_xticks([])
axes[1].set_xlim(0, 1)
axes[1].invert_yaxis()
axes[1].set_title("Bottom of Funnel\n(% of Clicks, zoomed in)")
for spine in axes[1].spines.values():
    spine.set_visible(False)

fig.suptitle("Overall Funnel: Impressions \u2192 Clicks \u2192 Offer Views \u2192 Redemptions", fontsize=13)
plt.tight_layout()
plt.savefig(f"{OUT_DIR}/overall_funnel.png", dpi=150, bbox_inches='tight')
plt.close()

# ---------------------------------------------------------------
# 2. Channel comparison: CAC (cost per redemption)
# ---------------------------------------------------------------
ranking = pd.read_csv(os.path.join(BASE_DIR, "outputs", "channel_ranking.csv"))
plt.figure(figsize=(8, 5))
sns.barplot(data=ranking.sort_values("cac"), x="cac", y="channel_name",
            hue="channel_type", dodge=False, palette={"Owned": "#2b6cb0", "Paid": "#e07856"})
plt.title("Cost per Redemption (CAC) by Channel — Lower Is Better")
plt.xlabel("Cost per Redemption ($)")
plt.ylabel("")
plt.tight_layout()
plt.savefig(f"{OUT_DIR}/cac_by_channel.png", dpi=150, bbox_inches='tight')
plt.close()

# ---------------------------------------------------------------
# 3. Channel comparison: redemption rate
# ---------------------------------------------------------------
plt.figure(figsize=(8, 5))
sns.barplot(data=ranking.sort_values("redemption_rate_pct", ascending=False),
            x="redemption_rate_pct", y="channel_name",
            hue="channel_type", dodge=False, palette={"Owned": "#2b6cb0", "Paid": "#e07856"})
plt.title("Redemption Rate by Channel (% of Impressions)")
plt.xlabel("Redemption Rate (%)")
plt.ylabel("")
plt.tight_layout()
plt.savefig(f"{OUT_DIR}/redemption_rate_by_channel.png", dpi=150, bbox_inches='tight')
plt.close()

# ---------------------------------------------------------------
# 4. Funnel drop-off by channel (stacked view of stage retention %)
# ---------------------------------------------------------------
dropoff_src = pd.read_csv(os.path.join(SQL_DIR, "funnel_by_channel.csv"))
dropoff_src["click_pct"] = (dropoff_src["clicks"] / dropoff_src["impressions"] * 100)
dropoff_src["view_pct"] = (dropoff_src["offer_views"] / dropoff_src["impressions"] * 100)
dropoff_src["redeem_pct"] = (dropoff_src["redemptions"] / dropoff_src["impressions"] * 100)
dropoff_src = dropoff_src.sort_values("click_pct", ascending=True)

fig, ax = plt.subplots(figsize=(9, 5))
y = range(len(dropoff_src))
ax.barh(y, dropoff_src["click_pct"], color="#a8c9e8", label="Reached Click")
ax.barh(y, dropoff_src["view_pct"], color="#5a9bd4", label="Reached Offer View")
ax.barh(y, dropoff_src["redeem_pct"], color="#1f4e79", label="Reached Redemption")
ax.set_yticks(y)
ax.set_yticklabels(dropoff_src["channel_name"])
ax.set_xlabel("% of Impressions Reaching Each Stage")
ax.set_title("Funnel Retention by Channel")
ax.legend(loc="lower right")
plt.tight_layout()
plt.savefig(f"{OUT_DIR}/funnel_retention_by_channel.png", dpi=150, bbox_inches='tight')
plt.close()

print(f"Charts saved to {OUT_DIR}/")

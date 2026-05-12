"""Generate Figure: reporting-rate gap, NeurIPS 2019 vs ICML 2025.

Replaces the survey comparison table (tab:survey-comparison). Title is omitted
because the LaTeX caption supplies it. Outputs PDF (vector) for the paper and
PNG for the README.
"""

import matplotlib.pyplot as plt
import matplotlib
import numpy as np

matplotlib.rcParams["font.family"] = "serif"
matplotlib.rcParams["font.size"] = 11

# UN SDG 13 "Climate Action" — the official color for the UN's climate goal,
# used across UN climate reports and SDG visualizations.
CLIMATE_GREEN = "#3F7E44"
CLIMATE_GREEN_EDGE = "#26562C"

categories = ["Compute\nmetadata", "Energy\ndata", "Carbon\ndata", "All\nthree"]
neurips_2019 = [17, 1, 0, np.nan]  # NeurIPS 2019 has no "all three" value
icml_2025 = [57.3, 9.0, 5.9, 1.4]
neurips_labels = ["17%", "1%", "0%", None]  # match paper Table 1 precision
icml_labels = ["57.3%", "9.0%", "5.9%", "1.4%"]

x = np.arange(len(categories))
width = 0.36

fig, ax = plt.subplots(figsize=(6.0, 3.2))

bars1 = ax.bar(
    x - width / 2,
    np.nan_to_num(neurips_2019, nan=0.0),
    width,
    label="NeurIPS 2019 (n=100)",
    color="#b0b0b0",
    edgecolor="#666666",
    linewidth=0.7,
)
bars2 = ax.bar(
    x + width / 2,
    icml_2025,
    width,
    label="ICML 2025 (n=1,000)",
    color=CLIMATE_GREEN,
    edgecolor=CLIMATE_GREEN_EDGE,
    linewidth=0.7,
)

# Mark the "N/A" bar for NeurIPS 2019 "All three"
ax.text(
    x[-1] - width / 2,
    1.5,
    "N/A",
    ha="center",
    va="bottom",
    fontsize=9,
    color="#666666",
    style="italic",
)

ax.set_ylabel("Papers reporting (%)")
ax.set_xticks(x)
ax.set_xticklabels(categories)
ax.set_ylim(0, 70)
ax.legend(loc="upper right", framealpha=0.9, fontsize=10)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)

def annotate(bars, labels, color, weight="normal"):
    for bar, label in zip(bars, labels):
        if label is None:
            continue
        h = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2.0,
            h + 1.0,
            label,
            ha="center",
            va="bottom",
            fontsize=9,
            color=color,
            fontweight=weight,
        )

annotate(bars1, neurips_labels, "#444444")
annotate(bars2, icml_labels, CLIMATE_GREEN_EDGE, weight="bold")

plt.tight_layout()
plt.savefig("figures/reporting_gap.pdf", bbox_inches="tight", pad_inches=0.15)
plt.savefig("figures/reporting_gap.png", dpi=200, bbox_inches="tight", pad_inches=0.15)
plt.close()
print("Saved figures/reporting_gap.{pdf,png}")

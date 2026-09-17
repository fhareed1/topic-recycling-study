"""Build a standalone figure for social posts: readable without the README, and using the same
`full` view numbers quoted in the post. Regenerated from results/summary.json like every figure."""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"
INK, ACCENT, MUTED = "#11241B", "#8A5A00", "#5B6B62"


def main():
    summary = json.loads((RESULTS / "summary.json").read_text())
    view = summary["views"]["full"]
    taus = sorted(view["by_threshold"], key=float)
    xs = [float(t) for t in taus]
    cross = [view["by_threshold"][t]["catalogue_title_on_another_site"] for t in taus]

    fig, ax = plt.subplots(figsize=(10, 5.6))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    ax.axvspan(0.75, 1.02, color=ACCENT, alpha=0.07, zorder=0)
    ax.text(0.885, 3.2, "checked by hand: matcher is right 98.7% here",
            ha="center", fontsize=9.5, color=ACCENT, zorder=3)

    rates = [c["rate"] * 100 for c in cross]
    ax.plot(xs, rates, color=ACCENT, linewidth=2.5, zorder=2)
    for x, c in zip(xs, cross):
        strict = x >= 0.8
        ax.plot(x, c["rate"] * 100, marker="o", markersize=9, zorder=3,
                color=ACCENT if strict else "white", markeredgecolor=ACCENT, markeredgewidth=2)

    for x, c, offset in zip(xs, cross, [14, 12, 12, 12, 12, 14]):
        ax.annotate(f"{c['rate'] * 100:.1f}%", (x, c["rate"] * 100), textcoords="offset points",
                    xytext=(0, offset), ha="center", fontsize=11, color=INK, weight="medium")

    ax.set_title("Rival Nigerian project-topic sites are selling the same topics",
                 fontsize=16, color=INK, loc="left", pad=44)
    ax.text(0, 1.035, "Share of 37,376 listed project titles that also appear on a different site",
            transform=ax.transAxes, fontsize=11, color=MUTED)
    ax.set_xlabel("How similar two titles must be to count as the same topic\n"
                  "(share of words in common; 1.0 = identical wording)", fontsize=10.5, color=MUTED, labelpad=10)
    ax.set_ylabel("share of listings with a match elsewhere", fontsize=10.5, color=MUTED)
    ax.set_ylim(0, 75)
    ax.set_xlim(0.45, 1.05)
    ax.set_xticks(xs, [f"{x:.1f}" for x in xs], fontsize=10)
    ax.set_yticks(range(0, 80, 20), [f"{v}%" for v in range(0, 80, 20)], fontsize=10)
    ax.grid(axis="y", alpha=0.25)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color("#C9D3CB")
    ax.tick_params(colors=MUTED)

    fig.text(0.008, 0.015, "3 sites, harvested from public sitemaps, September 2026  ·  "
             "method, data and limitations: github.com/fhareed1/topic-recycling-study",
             fontsize=9, color=MUTED)
    fig.tight_layout(rect=(0, 0.035, 1, 1))
    out = RESULTS / "figures" / "social_cross_site_overlap.png"
    fig.savefig(out, dpi=180, facecolor="white")
    print("wrote", out)


if __name__ == "__main__":
    main()

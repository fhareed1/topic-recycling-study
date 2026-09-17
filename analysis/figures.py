"""Regenerate every figure from results/summary.json. No number in a figure is typed by hand."""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"
FIGURES = RESULTS / "figures"


def errorbar_series(ax, xs, stats, label, **style):
    rates = [s["rate"] for s in stats]
    lower = [s["rate"] - s["lo"] for s in stats]
    upper = [s["hi"] - s["rate"] for s in stats]
    ax.errorbar(xs, rates, yerr=[lower, upper], marker="o", capsize=3, label=label, **style)


def main():
    FIGURES.mkdir(parents=True, exist_ok=True)
    summary = json.loads((RESULTS / "summary.json").read_text())
    view = summary["views"]["core"]
    taus = sorted(view["by_threshold"], key=float)
    xs = [float(t) for t in taus]

    # Figure 1: share of titles with a near-duplicate, by threshold
    fig, ax = plt.subplots(figsize=(6, 4))
    errorbar_series(ax, xs, [view["by_threshold"][t]["catalogue_title_on_another_site"] for t in taus], "sale title also listed on another site")
    for site in sorted(view["by_threshold"][taus[0]]["within_site"]):
        stats = [view["by_threshold"][t]["within_site"][site] for t in taus]
        label = "UI repository records matching another UI record (mostly double deposits)" if site == "ui" else f"repeated within {site}"
        errorbar_series(ax, xs, stats, label, linestyle="--", alpha=0.8)
    ax.set_xlabel("Jaccard threshold (normalised title tokens, case-study clause removed)")
    ax.set_ylabel("share of titles with at least one match")
    ax.set_ylim(0, 1)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(FIGURES / "fig1_recycling_by_threshold.png", dpi=200)

    # Figure 2: repository theses that match a sale title, by five-year period
    at = view["by_threshold"].get("0.8", {}).get("repository_vs_catalogues", {}).get("thesis_matches_by_5yr")
    if at:
        periods = [p for p, s in at.items() if s["n"] >= 30]
        fig, ax = plt.subplots(figsize=(6, 4))
        errorbar_series(ax, range(len(periods)), [at[p] for p in periods], "UI thesis matches a sale title (Jaccard >= 0.8)")
        ax.set_xticks(range(len(periods)), [f"{p}\n(n={at[p]['n']})" for p in periods], fontsize=7)
        ax.set_ylabel("share of theses")
        ax.grid(alpha=0.3)
        ax.legend(fontsize=7)
        fig.tight_layout()
        fig.savefig(FIGURES / "fig2_repository_overlap_by_period.png", dpi=200)
    # Figure 3: labelled precision and annotator agreement per Jaccard band
    precision_path = RESULTS / "precision.json"
    if precision_path.exists():
        report = json.loads(precision_path.read_text())
        bands = sorted(report["precision_by_band"], key=float)
        xs = range(len(bands))
        fig, ax = plt.subplots(figsize=(6, 4))
        errorbar_series(ax, xs, [{"rate": report["precision_by_band"][b]["precision"], "lo": report["precision_by_band"][b]["lo"], "hi": report["precision_by_band"][b]["hi"]} for b in bands], "precision of matches in band (agreed pairs)")
        ax.plot(xs, [report["agreement_by_band"][b]["raw"] for b in bands], marker="s", linestyle=":", alpha=0.8, label="annotator agreement in band")
        ax.axvspan(2.5, len(bands) - 0.5, alpha=0.08, color="grey")
        ax.text(3.5, 0.28, "operating range\n(annotators agree here too)", ha="center", fontsize=8, color="grey")
        ax.set_xticks(list(xs), [f"{b}\n(n={report['precision_by_band'][b]['n']})" for b in bands], fontsize=8)
        ax.set_xlabel("Jaccard band")
        ax.set_ylim(0, 1.05)
        ax.grid(alpha=0.3)
        ax.legend(fontsize=7, loc="lower left")
        fig.tight_layout()
        fig.savefig(FIGURES / "fig3_precision_by_band.png", dpi=200)
    print("figures written to", FIGURES)


if __name__ == "__main__":
    main()

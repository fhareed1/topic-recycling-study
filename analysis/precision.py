"""Estimate matcher precision from human labels, per Jaccard band, with inter-annotator agreement.

Input : results/labels_<annotator>.csv, copies of pairs_for_labelling.csv with `same_topic`
        filled in as 1 (same research topic) or 0 (different). See LABELLING.md.
Output: results/precision.json

With two or more annotators, agreement is Cohen's kappa on the pairs both labelled, and the
precision estimate uses only pairs where they agree (disagreements are reported, not dropped
silently).
"""

import csv
import json
import math
from collections import defaultdict
from itertools import combinations
from pathlib import Path

RESULTS = Path(__file__).resolve().parent.parent / "results"


def wilson(k, n, z=1.96):
    if n == 0:
        return None
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return {"k": k, "n": n, "precision": round(p, 3), "lo": round(centre - half, 3), "hi": round(centre + half, 3)}


def cohen_kappa(a, b):
    n = len(a)
    observed = sum(x == y for x, y in zip(a, b)) / n
    p_a, p_b = sum(a) / n, sum(b) / n
    expected = p_a * p_b + (1 - p_a) * (1 - p_b)
    return round((observed - expected) / (1 - expected), 3) if expected < 1 else 1.0


def main():
    files = sorted(RESULTS.glob("labels_*.csv"))
    if not files:
        raise SystemExit("no results/labels_*.csv files yet; see LABELLING.md")
    labels = {}
    bands = {}
    for path in files:
        annotator = path.stem.removeprefix("labels_")
        labels[annotator] = {}
        for row in csv.DictReader(path.open(encoding="utf-8")):
            if row["same_topic"].strip() in {"0", "1"}:
                labels[annotator][row["pair_id"]] = int(row["same_topic"])
                bands[row["pair_id"]] = float(row["band"])

    report = {"annotators": {a: len(v) for a, v in labels.items()}, "agreement": {}}
    for x, y in combinations(labels, 2):
        shared = sorted(set(labels[x]) & set(labels[y]))
        if shared:
            report["agreement"][f"{x}~{y}"] = {
                "n": len(shared),
                "raw": round(sum(labels[x][p] == labels[y][p] for p in shared) / len(shared), 3),
                "cohen_kappa": cohen_kappa([labels[x][p] for p in shared], [labels[y][p] for p in shared]),
            }

    consensus, disagreements = {}, 0
    for pair in bands:
        votes = [labels[a][pair] for a in labels if pair in labels[a]]
        if len(set(votes)) == 1:
            consensus[pair] = votes[0]
        else:
            disagreements += 1
    report["disagreements_excluded"] = disagreements

    by_band = defaultdict(list)
    for pair, label in consensus.items():
        by_band[bands[pair]].append(label)
    report["precision_by_band"] = {str(b): wilson(sum(v), len(v)) for b, v in sorted(by_band.items())}
    report["precision_at_or_above"] = {
        str(t): wilson(sum(l for b, v in by_band.items() if b >= t for l in v), sum(len(v) for b, v in by_band.items() if b >= t))
        for t in sorted(by_band)
    }
    (RESULTS / "precision.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

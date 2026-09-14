"""Measure topic recycling within and across sale catalogues and a university repository.

Unit of analysis: a listed title. A title "has a match" in a group when at least one title in
that group (other than itself) has exact Jaccard >= tau on normalised tokens.

Outputs
  results/summary.json            all rates with Wilson 95% intervals, for every tau and view
  results/pairs_for_labelling.csv stratified random sample of verified pairs for human labelling
"""

import csv
import json
import math
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

from minhash import similar_pairs
from normalise import tokens

ROOT = Path(__file__).resolve().parent.parent
INTERIM = ROOT / "data" / "interim"
RESULTS = ROOT / "results"
THRESHOLDS = [0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
MIN_TOKENS = 4  # very short titles match by accident; excluded and counted
HEADLINE_SITES = {"projectclue", "researchwap", "eduprojecttopics"}


def wilson(k, n, z=1.96):
    if n == 0:
        return {"k": 0, "n": 0, "rate": None, "lo": None, "hi": None}
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return {"k": k, "n": n, "rate": round(p, 4), "lo": round(centre - half, 4), "hi": round(centre + half, 4)}


def load(path):
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def is_thesis(record):
    return any("thesis" in t.lower() or "dissertation" in t.lower() for t in record.get("types", []))


def build_corpus(view):
    records = [r for r in load(INTERIM / "catalogue.jsonl") if r["source"] in HEADLINE_SITES or "--with-projectng" in sys.argv]
    repo_path = INTERIM / "repository.jsonl"
    if repo_path.exists():
        records += [r for r in load(repo_path) if is_thesis(r)]
    kept, excluded = [], Counter()
    for r in records:
        r["tokens"] = tokens(r["title"], view)
        if len(r["tokens"]) < MIN_TOKENS:
            excluded[r["source"]] += 1
        else:
            kept.append(r)
    return kept, dict(excluded)


def neighbours(records, threshold):
    """Map title index -> list of (other index, jaccard), computed over unique token sets."""
    unique = {}
    members = defaultdict(list)
    for i, r in enumerate(records):
        key = r["tokens"]
        unique.setdefault(key, len(unique))
        members[unique[key]].append(i)
    sets = [None] * len(unique)
    for key, u in unique.items():
        sets[u] = key
    pairs, stats = similar_pairs(sets, threshold=min(THRESHOLDS))
    links = defaultdict(list)
    # identical token sets are Jaccard 1.0 with each other
    for group in members.values():
        for i in group:
            links[i].extend((j, 1.0) for j in group if j != i)
    for (u, v), score in pairs.items():
        for i in members[u]:
            for j in members[v]:
                links[i].append((j, score))
                links[j].append((i, score))
    return links, pairs, sets, members, stats


def rate(records, links, subset, target, tau):
    """Share of titles in `subset` with a match (jaccard >= tau) among titles satisfying `target`."""
    n = k = 0
    for i, r in enumerate(records):
        if not subset(r):
            continue
        n += 1
        if any(score >= tau and target(records[j], r) for j, score in links.get(i, [])):
            k += 1
    return wilson(k, n)


def distinct_topics(records, links, tau):
    """Union-find over catalogue titles joined at jaccard >= tau. Chaining makes low tau merge
    unrelated topics, so this is only reported for tau >= 0.9."""
    parent = list(range(len(records)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    catalogue = [i for i, r in enumerate(records) if r["kind"] == "catalogue"]
    for i in catalogue:
        for j, score in links.get(i, []):
            if score >= tau and records[j]["kind"] == "catalogue":
                parent[find(i)] = find(j)
    clusters = defaultdict(set)
    for i in catalogue:
        clusters[find(i)].add(records[i]["source"])
    sites_per_topic = Counter(len(s) for s in clusters.values())
    return {"listings": len(catalogue), "distinct_topics": len(clusters), "topics_by_number_of_sites": dict(sorted(sites_per_topic.items()))}


def thesis_matches(records, links, tau):
    return [
        {"thesis": r["title"], "year": r.get("year"), "catalogue": records[j]["title"], "site": records[j]["source"], "jaccard": round(score, 3)}
        for i, r in enumerate(records)
        if r["kind"] == "repository"
        for j, score in links.get(i, [])
        if score >= tau and records[j]["kind"] == "catalogue"
    ]


def main():
    RESULTS.mkdir(exist_ok=True)
    summary = {"min_tokens": MIN_TOKENS, "views": {}}
    for view in ["full", "core"]:
        records, excluded = build_corpus(view)
        links, pairs, sets, members, stats = neighbours(records, min(THRESHOLDS))
        sources = sorted({r["source"] for r in records})
        catalogue_sources = [s for s in sources if s in HEADLINE_SITES or s == "projectng"]
        out = {
            "n_titles": dict(Counter(r["source"] for r in records)),
            "excluded_short_titles": excluded,
            "lsh": stats,
            "by_threshold": {},
        }
        for tau in THRESHOLDS:
            t = {"within_site": {}, "cross_site": {}, "repository_vs_catalogues": {}}
            for s in sources:
                t["within_site"][s] = rate(records, links, lambda r, s=s: r["source"] == s, lambda o, r: o["source"] == r["source"], tau)
            for a in catalogue_sources:
                for b in catalogue_sources:
                    if a != b:
                        t["cross_site"][f"{a}->{b}"] = rate(records, links, lambda r, a=a: r["source"] == a, lambda o, r, b=b: o["source"] == b, tau)
            t["catalogue_title_on_another_site"] = rate(
                records, links, lambda r: r["kind"] == "catalogue", lambda o, r: o["kind"] == "catalogue" and o["source"] != r["source"], tau
            )
            if any(r["kind"] == "repository" for r in records):
                t["repository_vs_catalogues"]["thesis_matches_any_catalogue"] = rate(
                    records, links, lambda r: r["kind"] == "repository", lambda o, r: o["kind"] == "catalogue", tau
                )
                t["repository_vs_catalogues"]["catalogue_matches_a_thesis"] = rate(
                    records, links, lambda r: r["kind"] == "catalogue", lambda o, r: o["kind"] == "repository", tau
                )
                decades = sorted({(r["year"] // 5) * 5 for r in records if r["kind"] == "repository" and r.get("year")})
                t["repository_vs_catalogues"]["thesis_matches_by_5yr"] = {
                    f"{d}-{d + 4}": rate(
                        records, links, lambda r, d=d: r["kind"] == "repository" and r.get("year") and d <= r["year"] < d + 5,
                        lambda o, r: o["kind"] == "catalogue", tau,
                    )
                    for d in decades
                }
            if tau >= 0.9:
                t["distinct_topics"] = distinct_topics(records, links, tau)
            out["by_threshold"][str(tau)] = t
        out["thesis_catalogue_matches_at_0.7"] = thesis_matches(records, links, 0.7)
        summary["views"][view] = out
        if view == "core":
            write_labelling_sample(records, pairs, sets, members)
        print(f"[{view}] titles={len(records)} verified_unique_pairs={len(pairs)} {stats}")
    (RESULTS / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps({v: summary["views"][v]["by_threshold"]["0.7"]["catalogue_title_on_another_site"] for v in summary["views"]}, indent=2))


def write_labelling_sample(records, pairs, sets, members, per_band=40, seed=7):
    """Stratified sample of cross-source pairs so precision can be estimated per Jaccard band."""
    rng = random.Random(seed)
    bands = defaultdict(list)
    for (u, v), score in pairs.items():
        i, j = members[u][0], members[v][0]
        if records[i]["source"] == records[j]["source"]:
            continue
        band = min(int(score * 10) / 10, 0.9)
        bands[band].append((i, j, score))
    rows = []
    for band in sorted(bands):
        for i, j, score in rng.sample(bands[band], min(per_band, len(bands[band]))):
            rows.append([records[i]["source"], records[i]["title"], records[j]["source"], records[j]["title"], round(score, 3), band])
    rng.shuffle(rows)  # hide the band order from the labeller
    with (RESULTS / "pairs_for_labelling.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["pair_id", "source_a", "title_a", "source_b", "title_b", "jaccard", "band", "same_topic"])
        for n, row in enumerate(rows):
            w.writerow([n, *row, ""])


if __name__ == "__main__":
    main()

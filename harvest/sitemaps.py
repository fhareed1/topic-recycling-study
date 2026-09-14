"""Harvest project titles from the public XML sitemaps of Nigerian project-topic sale sites.

Only sitemap files are downloaded (the files sites publish for crawlers). No product page,
paid material or personal data is fetched. Titles are reconstructed from URL slugs.

Output: data/interim/catalogue.jsonl, one record per listed project.
"""

import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from urllib.parse import urlparse

from common import INTERIM, RAW, fetch

NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

# Each site: sitemap entry points and a rule that maps a URL path to (department, slug) or None.
# robots.txt for every site was checked on 2026-09-14 and allows these paths.
# premiumresearchers.com is excluded: its robots.txt disallows AI crawlers.


def projectclue(path):
    parts = path.strip("/").split("/")
    if len(parts) == 3 and parts[1] == "project-topics-materials-for-undergraduate-students":
        return parts[0], parts[2]
    return None


def researchwap(path):
    parts = path.strip("/").split("/")
    if len(parts) == 2 and not parts[1].endswith(".html"):
        return parts[0], parts[1]
    return None


def eduprojecttopics(path):
    parts = path.strip("/").split("/")
    if len(parts) == 2 and parts[0] == "product":
        return None, parts[1]
    return None


def projectng(path):
    # Slugs here are keyword-compressed (stopwords dropped, truncated), so this site is
    # kept for a sensitivity analysis only and flagged `slug_compressed`.
    parts = path.strip("/").split("/")
    if len(parts) == 3 and parts[0] in {"topic", "research", "read"}:
        return None, parts[2]
    return None


SITES = {
    "projectclue": (["https://www.projectclue.com/sitemap.xml"], projectclue, False),
    "researchwap": (["https://www.researchwap.com/sitemap.xml"], researchwap, False),
    "eduprojecttopics": (
        [f"https://eduprojecttopics.com/product-sitemap{'' if i == 1 else i}.xml" for i in range(1, 22)],
        eduprojecttopics,
        False,
    ),
    "projectng": (["https://projectng.com/sitemap.xml"], projectng, True),
}


def slug_to_title(slug: str) -> str:
    slug = re.sub(r"\.(html?|php)$", "", slug)
    return re.sub(r"[-_]+", " ", slug).strip()


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    INTERIM.mkdir(parents=True, exist_ok=True)
    harvested_at = datetime.now(timezone.utc).isoformat()
    out_path = INTERIM / "catalogue.jsonl"
    counts = {}
    with out_path.open("w", encoding="utf-8") as out:
        for site, (sitemaps, rule, compressed) in SITES.items():
            seen = set()
            for index, url in enumerate(sitemaps):
                raw_file = RAW / f"sitemap_{site}_{index}.xml"
                if raw_file.exists():
                    body = raw_file.read_bytes()
                else:
                    print(f"fetching {url}")
                    body = fetch(url, delay=3.0)
                    raw_file.write_bytes(body)
                root = ET.fromstring(body)
                for node in root.findall("sm:url", NS):
                    loc = node.findtext("sm:loc", default="", namespaces=NS).strip()
                    lastmod = node.findtext("sm:lastmod", default=None, namespaces=NS)
                    parsed = rule(urlparse(loc).path)
                    if not parsed or loc in seen:
                        continue
                    seen.add(loc)
                    department, slug = parsed
                    record = {
                        "source": site,
                        "kind": "catalogue",
                        "url": loc,
                        "department": department,
                        "title": slug_to_title(slug),
                        "lastmod": lastmod,
                        "slug_compressed": compressed,
                        "harvested_at": harvested_at,
                    }
                    out.write(json.dumps(record, ensure_ascii=False) + "\n")
            counts[site] = len(seen)
            print(f"{site}: {len(seen)} project URLs")
    (INTERIM / "catalogue_counts.json").write_text(json.dumps(counts, indent=2))


if __name__ == "__main__":
    main()

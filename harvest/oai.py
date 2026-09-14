"""Harvest Dublin Core metadata from Nigerian institutional repositories over OAI-PMH.

OAI-PMH is the protocol repositories expose specifically for metadata harvesting.
Every page is cached under data/raw, so an interrupted run resumes where it stopped.

Output: data/interim/repository.jsonl, one record per item (all types; filter later).
"""

import json
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from urllib.parse import quote

from common import INTERIM, RAW, fetch

REPOSITORIES = {
    "ui": "https://repository.ui.edu.ng/server/oai/request",
}

NS = {
    "oai": "http://www.openarchives.org/OAI/2.0/",
    "dc": "http://purl.org/dc/elements/1.1/",
    "oai_dc": "http://www.openarchives.org/OAI/2.0/oai_dc/",
}


def year_of(dates):
    years = [int(m.group()) for d in dates for m in [re.search(r"\b(19|20)\d{2}\b", d)] if m]
    # The first dc:date is often the deposit timestamp; the earliest plausible year is the work.
    return min(years) if years else None


def harvest(name, base):
    page = 0
    url = f"{base}?verb=ListRecords&metadataPrefix=oai_dc"
    records = []
    while url:
        raw_file = RAW / f"oai_{name}_{page:05d}.xml"
        if raw_file.exists():
            body = raw_file.read_bytes()
        else:
            body = fetch(url, delay=2.0)
            raw_file.write_bytes(body)
        root = ET.fromstring(body)
        for record in root.iterfind(".//oai:record", NS):
            header = record.find("oai:header", NS)
            if header is None or header.get("status") == "deleted":
                continue
            dc = record.find(".//oai_dc:dc", NS)
            if dc is None:
                continue
            field = lambda tag: [e.text.strip() for e in dc.findall(f"dc:{tag}", NS) if e.text]
            titles = field("title")
            if not titles:
                continue
            records.append(
                {
                    "source": name,
                    "kind": "repository",
                    "id": header.findtext("oai:identifier", namespaces=NS),
                    "sets": [s.text for s in header.findall("oai:setSpec", NS)],
                    "title": titles[0],
                    "types": field("type"),
                    "year": year_of(field("date")),
                }
            )
        token = root.find(".//oai:resumptionToken", NS)
        total = token.get("completeListSize") if token is not None else "?"
        print(f"{name} page {page}: {len(records)} records so far (list size {total})")
        if token is not None and token.text:
            url = f"{base}?verb=ListRecords&resumptionToken={quote(token.text)}"
            page += 1
        else:
            url = None
    return records


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    INTERIM.mkdir(parents=True, exist_ok=True)
    names = sys.argv[1:] or list(REPOSITORIES)
    harvested_at = datetime.now(timezone.utc).isoformat()
    with (INTERIM / "repository.jsonl").open("w", encoding="utf-8") as out:
        for name in names:
            for record in harvest(name, REPOSITORIES[name]):
                record["harvested_at"] = harvested_at
                out.write(json.dumps(record, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()

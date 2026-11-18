#!/usr/bin/env python3
"""Download every SSA ALJ Disposition XML file listed in the Data.gov catalog.

Steps
  1. Ask Data.gov for the children of collection US-GOV-SSA-1199 (no scraping).
  2. Download each XML file (and SSA's data-dictionary page) into data/raw/, mirroring the
     path below https://www.ssa.gov/appeals/DataSets/.
  3. Record status, size and SHA-256 per file in data/manifest.json.

Politeness / resilience (www.ssa.gov sits behind a bot-protecting CDN that blocked bursts):
  * strictly sequential, 1.5-2.5 s random delay between requests
  * browser TLS impersonation via curl_cffi (plain curl/requests get 403)
  * exponential back-off on 403/429/5xx, abort the run after repeated failures
  * resumable: files already downloaded (per manifest) are skipped unless --force

Usage:  uv run --group etl scripts/crawl_ssa_alj.py [--force] [--limit N] [--delay 2.0]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from curl_cffi import requests

REPO_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = REPO_ROOT / "data" / "raw"
MANIFEST = REPO_ROOT / "data" / "manifest.json"

CATALOG_SEARCH = "https://catalog.data.gov/search"
COLLECTION_ID = "US-GOV-SSA-1199"
SSA_BASE = "https://www.ssa.gov/appeals/DataSets/"
EXTRA_PAGES = [SSA_BASE + "data_dictionary.html"]  # official column definitions

IMPERSONATE = "chrome"
MAX_ATTEMPTS = 4
ABORT_AFTER_CONSECUTIVE_FAILURES = 3


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def fetch_catalog_records(session: requests.Session) -> list[dict]:
    """Return one record per catalog child dataset (title, ids, XML/HTML URLs)."""
    records: list[dict] = []
    after = None
    while True:
        params = {"collection": COLLECTION_ID, "per_page": 1000, "format": "json"}
        if after:
            params["after"] = after
        resp = session.get(CATALOG_SEARCH, params=params, timeout=60)
        resp.raise_for_status()
        payload = resp.json()
        batch = payload.get("results", [])
        for item in batch:
            dcat = item.get("dcat") or {}
            xml_url = html_url = None
            for dist in dcat.get("distribution") or []:
                fmt = (dist.get("format") or "").upper()
                if fmt == "XML":
                    xml_url = dist.get("downloadURL") or dist.get("accessURL")
                elif fmt == "HTML":
                    html_url = dist.get("accessURL")
            records.append(
                {
                    "catalog_identifier": item.get("identifier"),
                    "catalog_slug": item.get("slug"),
                    "catalog_title": item.get("title"),
                    "catalog_modified": dcat.get("modified"),
                    "xml_url": xml_url,
                    "html_url": html_url,
                }
            )
        after = payload.get("after")
        if not batch or len(batch) < 1000 or not after:
            break
    return records


def local_path_for(url: str) -> Path:
    if not url.startswith(SSA_BASE):
        raise ValueError(f"unexpected host/path: {url}")
    return RAW_DIR / url[len(SSA_BASE) :]


def load_manifest() -> dict:
    if MANIFEST.exists():
        return json.loads(MANIFEST.read_text())
    return {"files": {}}


def save_manifest(manifest: dict) -> None:
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    tmp = MANIFEST.with_suffix(".tmp")
    tmp.write_text(json.dumps(manifest, indent=1, sort_keys=True))
    tmp.replace(MANIFEST)


def download(session: requests.Session, url: str) -> tuple[int | None, bytes | None, str | None]:
    """GET with retry/back-off. Returns (status, body, error)."""
    last_status, last_err = None, None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            resp = session.get(url, timeout=90)
            last_status = resp.status_code
            if resp.status_code == 200:
                return 200, resp.content, None
            if resp.status_code in (403, 429, 500, 502, 503, 504):
                wait = 20 * 2 ** (attempt - 1)  # 20, 40, 80, 160 s
                print(
                    f"    HTTP {resp.status_code}; back-off {wait}s (attempt {attempt}/{MAX_ATTEMPTS})",
                    flush=True,
                )
                time.sleep(wait)
                continue
            return resp.status_code, None, f"HTTP {resp.status_code}"  # e.g. 404: do not retry
        except Exception as exc:  # network error
            last_err = str(exc)
            time.sleep(10 * attempt)
    return last_status, None, last_err or f"HTTP {last_status}"


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "--force", action="store_true", help="re-download files already in the manifest"
    )
    ap.add_argument("--limit", type=int, default=0, help="download at most N files (0 = all)")
    ap.add_argument("--delay", type=float, default=2.0, help="average seconds between requests")
    args = ap.parse_args()

    session = requests.Session(impersonate=IMPERSONATE)
    manifest = load_manifest()

    print("Fetching catalog list ...", flush=True)
    records = fetch_catalog_records(session)
    manifest["catalog_fetched_at"] = now_iso()
    manifest["catalog_collection"] = COLLECTION_ID
    print(
        f"  {len(records)} catalog records ({sum(1 for r in records if r['xml_url'])} with XML)",
        flush=True,
    )

    jobs: list[tuple[str, dict]] = []
    for rec in records:
        if rec["xml_url"]:
            jobs.append((rec["xml_url"], {"kind": "xml", **rec}))
    for url in EXTRA_PAGES:
        jobs.append((url, {"kind": "extra", "catalog_title": url.rsplit("/", 1)[-1]}))

    done = skipped = failed = consecutive_failures = 0
    for index, (url, meta) in enumerate(jobs, 1):
        entry = manifest["files"].get(url)
        path = local_path_for(url)
        if entry and entry.get("status") == 200 and path.exists() and not args.force:
            entry.update({k: v for k, v in meta.items() if k != "kind"})  # refresh catalog metadata
            skipped += 1
            continue
        if args.limit and done >= args.limit:
            break

        print(f"[{index}/{len(jobs)}] {url.replace(SSA_BASE, '')}", flush=True)
        status, body, error = download(session, url)
        if status == 200 and body is not None:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(path.suffix + ".part")
            tmp.write_bytes(body)
            tmp.replace(path)
            manifest["files"][url] = {
                **meta,
                "local_path": str(path.relative_to(REPO_ROOT)),
                "status": 200,
                "bytes": len(body),
                "sha256": hashlib.sha256(body).hexdigest(),
                "fetched_at": now_iso(),
            }
            done += 1
            consecutive_failures = 0
        else:
            manifest["files"][url] = {
                **meta,
                "status": status,
                "error": error,
                "fetched_at": now_iso(),
            }
            failed += 1
            consecutive_failures += 1
            print(f"    FAILED: {error}", flush=True)
            if consecutive_failures >= ABORT_AFTER_CONSECUTIVE_FAILURES:
                print(
                    "Too many consecutive failures - stopping so we do not hammer the server.",
                    flush=True,
                )
                save_manifest(manifest)
                return 2
        if done % 10 == 0:
            save_manifest(manifest)
        time.sleep(max(1.0, random.uniform(args.delay * 0.75, args.delay * 1.25)))

    save_manifest(manifest)
    ok = sum(1 for e in manifest["files"].values() if e.get("status") == 200)
    print(
        f"\nDone. downloaded={done} skipped(already had)={skipped} failed={failed}; "
        f"manifest has {ok}/{len(manifest['files'])} files with HTTP 200."
    )
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

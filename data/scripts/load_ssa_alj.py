#!/usr/bin/env python3
"""Load the cached SSA ALJ XML files (data/raw/, listed in data/manifest.json) into SQLite.

  uv run --group etl data/scripts/crawl_ssa_alj.py      # 1. download (resumable)
  uv run data/scripts/load_ssa_alj.py       # 2. parse + load  -> data/ssa_alj.sqlite

Behaviour
  * Schema is detected from the ROW FIELD NAMES (titles/filenames are unreliable).
  * Rows are stored faithfully; anomalies go to the load_issue table instead of being dropped/fixed.
  * Idempotent: a snapshot whose SHA-256 is unchanged is skipped; --force reloads everything.
  * Each snapshot loads inside one transaction.
Standard library only (sqlite3 + xml.etree).
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA = REPO_ROOT / "data" / "db" / "schema.sql"
MANIFEST = REPO_ROOT / "data" / "manifest.json"
DEFAULT_DB = REPO_ROOT / "data" / "ssa_alj.sqlite"

DISPOSITION_FIELDS = {
    "FULLY_FAVORABLE",
    "PARTIALLY_FAVORABLE",
    "TOTAL_AWARDS",
    "TOTAL_DENIALS",
    "TOTAL_DECISIONS",
    "TOTAL_DISPOSITIONS",
    "TOTAL_ALJ_DIPOSITIONS_ACROSS_ALL_OFFICES",
}
RANKING_FIELDS = {"HEARING_OFFICE", "RANK", "ALJ_DISPS_PER_DAY_PER_ALJ", "WORKDAYS"}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def iso_date(text: str | None) -> str | None:
    """MM/DD/YYYY -> YYYY-MM-DD (None if blank/unparseable)."""
    if not text or not text.strip():
        return None
    try:
        return datetime.strptime(text.strip(), "%m/%d/%Y").date().isoformat()
    except ValueError:
        return None


def clean(text: str | None) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def to_int(text: str | None) -> int | None:
    t = clean(text)
    if t == "":
        return None
    try:
        return int(t)
    except ValueError:
        try:
            f = float(t)
            return int(f) if f.is_integer() else None
        except ValueError:
            return None


def to_float(text: str | None) -> float | None:
    t = clean(text)
    try:
        return float(t) if t else None
    except ValueError:
        return None


def norm_region(text: str | None) -> str:
    t = clean(text)
    return t.zfill(2) if t.isdigit() else t


def name_key(name: str) -> str:
    """Lower-case, punctuation-free key so 'Akins, George M' and 'Akins, George M.' group together."""
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", "", name.lower())).strip()


def split_name(name: str) -> tuple[str, str]:
    last, sep, given = name.partition(", ")
    return (last, given) if sep else (name, "")


def fiscal_year_of(period_iso: str) -> int:
    """US federal fiscal year (Oct 1 - Sep 30) containing the reporting period end date."""
    y, m = int(period_iso[:4]), int(period_iso[5:7])
    return y + 1 if m >= 10 else y


def snapshot_meta(url: str, entry: dict) -> dict:
    fn = url.rsplit("/", 1)[-1]
    month = re.search(
        r"_(January|February|March|April|May|June|July|August|September|October|November|December)_",
        fn,
    )
    current = fn == "03_ALJ_Disposition_Data.xml"
    return {
        "report_label": "Current Report" if current else (month.group(1) if month else fn),
        "is_current_report": 1 if current else 0,
    }


class Loader:
    def __init__(self, db: sqlite3.Connection):
        self.db = db
        self.regions: set[str] = {r[0] for r in db.execute("SELECT region_code FROM region")}
        self.offices: dict[str, int] = {
            n: i for i, n in db.execute("SELECT office_id, office_name FROM hearing_office")
        }
        self.aljs: dict[str, int] = {
            n: i for i, n in db.execute("SELECT alj_id, name_raw FROM alj")
        }
        self.issue_counts: Counter = Counter()

    def region(self, code: str) -> str:
        if code not in self.regions:
            self.db.execute("INSERT INTO region(region_code) VALUES (?)", (code,))
            self.regions.add(code)
        return code

    def office(self, name: str) -> int:
        oid = self.offices.get(name)
        if oid is None:
            oid = self.db.execute(
                "INSERT INTO hearing_office(office_name) VALUES (?)", (name,)
            ).lastrowid
            self.offices[name] = oid
        return oid

    def alj(self, name: str) -> int:
        aid = self.aljs.get(name)
        if aid is None:
            last, given = split_name(name)
            aid = self.db.execute(
                "INSERT INTO alj(name_raw, name_key, last_name, given_names) VALUES (?,?,?,?)",
                (name, name_key(name), last, given),
            ).lastrowid
            self.aljs[name] = aid
        return aid

    def issue(self, snapshot_id, row_number, alj_name, office_name, issue_type, detail):
        self.issue_counts[issue_type] += 1
        self.db.execute(
            "INSERT INTO load_issue(snapshot_id,row_number,alj_name,office_name,issue_type,detail) VALUES (?,?,?,?,?,?)",
            (snapshot_id, row_number, alj_name, office_name, issue_type, detail),
        )

    # ------------------------------------------------------------------------------------------
    def load_file(self, url: str, entry: dict, path: Path, force: bool) -> str:
        sha = entry.get("sha256")
        existing = self.db.execute(
            "SELECT snapshot_id, content_sha256 FROM report_snapshot WHERE source_xml_url=?", (url,)
        ).fetchone()
        if existing and existing[1] == sha and not force:
            return "skipped"

        root = ET.parse(path).getroot()
        rows = [c for c in root if c.tag == "row"]
        header_period = next((c.text for c in root if c.tag == "RPTG_PRD_ENDT"), None)
        xml_title = next((clean(c.text) for c in root if c.tag == "title"), None)
        field_names: set[str] = set()
        for r in rows:
            field_names.update(c.tag for c in r)
        if RANKING_FIELDS <= field_names:
            kind, variant = "office_ranking", "R"
        elif DISPOSITION_FIELDS <= field_names:
            kind = "alj_disposition"
            variant = "B" if "RPTG_PRD_ENDT" in field_names else "A"
        else:
            raise ValueError(f"unrecognised row fields: {sorted(field_names)}")

        period = iso_date(header_period) or next(
            (
                iso_date(c.text)
                for r in rows
                for c in r
                if c.tag == "RPTG_PRD_ENDT" and iso_date(c.text)
            ),
            None,
        )
        if period is None:
            raise ValueError("no reporting period end date found")

        meta = snapshot_meta(url, entry)
        with self.db:  # one transaction per snapshot
            if existing:
                self.db.execute(
                    "DELETE FROM report_snapshot WHERE snapshot_id=?", (existing[0],)
                )  # cascades
            sid = self.db.execute(
                """INSERT INTO report_snapshot(report_kind, catalog_identifier, catalog_slug, catalog_title,
                       catalog_modified, source_xml_url, source_html_url, fiscal_year, report_label,
                       is_current_report, xml_title, reporting_period_end, file_created_date,
                       declared_record_count, loaded_row_count, schema_variant, local_path, content_sha256,
                       fetched_at, loaded_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    kind,
                    entry.get("catalog_identifier"),
                    entry.get("catalog_slug"),
                    entry.get("catalog_title"),
                    entry.get("catalog_modified"),
                    url,
                    entry.get("html_url"),
                    fiscal_year_of(period),
                    meta["report_label"],
                    meta["is_current_report"],
                    xml_title,
                    period,
                    iso_date(root.get("created")),
                    to_int(root.get("records")),
                    None,
                    variant,
                    entry.get("local_path"),
                    sha,
                    entry.get("fetched_at"),
                    now_iso(),
                ),
            ).lastrowid
            if kind == "alj_disposition":
                loaded = self._load_dispositions(sid, rows)
            else:
                loaded = self._load_rankings(sid, rows)
            self.db.execute(
                "UPDATE report_snapshot SET loaded_row_count=? WHERE snapshot_id=?", (loaded, sid)
            )
            declared = to_int(root.get("records"))
            if declared is not None and declared != len(rows):
                self.issue(
                    sid,
                    None,
                    None,
                    None,
                    "declared_count_mismatch",
                    f"data@records={declared} but file has {len(rows)} <row> elements",
                )
        return "loaded"

    def _load_dispositions(self, sid: int, rows: list) -> int:
        batch, seen = [], set()
        for n, r in enumerate(rows, 1):
            v = {c.tag: c.text for c in r}
            judge, office = clean(v.get("JUDGE")), clean(v.get("OFFICE"))
            region = norm_region(v.get("REGION"))
            if not judge:
                self.issue(
                    sid, n, judge, office, "missing_judge_name", "JUDGE blank; row not loaded"
                )
                continue
            if not office or not region:
                self.issue(
                    sid,
                    n,
                    judge,
                    office,
                    "blank_office_or_region",
                    f"OFFICE={office!r} REGION={region!r}; loaded with NULLs",
                )
            nums = {k: to_int(v.get(k)) for k in DISPOSITION_FIELDS}
            for k, val in nums.items():
                if val is None:
                    self.issue(sid, n, judge, office, "bad_or_missing_number", f"{k}={v.get(k)!r}")
            alj_id = self.alj(judge)
            office_id = self.office(office) if office else None
            if (alj_id, office_id) in seen:
                self.issue(
                    sid,
                    n,
                    judge,
                    office,
                    "duplicate_judge_office_row",
                    "same name+office already seen in this file; both rows kept",
                )
            seen.add((alj_id, office_id))
            ff, pf, aw = nums["FULLY_FAVORABLE"], nums["PARTIALLY_FAVORABLE"], nums["TOTAL_AWARDS"]
            den, dec, dis = (
                nums["TOTAL_DENIALS"],
                nums["TOTAL_DECISIONS"],
                nums["TOTAL_DISPOSITIONS"],
            )
            allo = nums["TOTAL_ALJ_DIPOSITIONS_ACROSS_ALL_OFFICES"]
            if None not in (ff, pf, aw) and aw != ff + pf:
                self.issue(
                    sid, n, judge, office, "awards_ne_ff_plus_pf", f"awards={aw} ff={ff} pf={pf}"
                )
            if None not in (aw, den, dec) and dec != aw + den:
                self.issue(
                    sid,
                    n,
                    judge,
                    office,
                    "decisions_ne_awards_plus_denials",
                    f"decisions={dec} awards={aw} denials={den}",
                )
            if None not in (dec, dis) and dis < dec:
                self.issue(
                    sid,
                    n,
                    judge,
                    office,
                    "dispositions_lt_decisions",
                    f"dispositions={dis} decisions={dec}",
                )
            if None not in (dis, allo) and allo < dis:
                self.issue(
                    sid,
                    n,
                    judge,
                    office,
                    "all_offices_lt_office_dispositions",
                    f"all_offices={allo} dispositions={dis}",
                )
            if any(x is not None and x < 0 for x in nums.values()):
                self.issue(sid, n, judge, office, "negative_value", str(nums))
            batch.append(
                (
                    sid,
                    n,
                    alj_id,
                    office_id,
                    self.region(region) if region else None,
                    ff,
                    pf,
                    aw,
                    den,
                    dec,
                    dis,
                    allo,
                    iso_date(v.get("RPTG_PRD_ENDT")),
                )
            )
        self.db.executemany("INSERT INTO alj_disposition VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", batch)
        return len(batch)

    def _load_rankings(self, sid: int, rows: list) -> int:
        batch, seen = [], set()
        for n, r in enumerate(rows, 1):
            v = {c.tag: c.text for c in r}
            office, region = clean(v.get("HEARING_OFFICE")), norm_region(v.get("REGION"))
            if not office or not region:
                self.issue(
                    sid,
                    n,
                    None,
                    office,
                    "missing_key_field",
                    f"HEARING_OFFICE/REGION blank (region={region!r})",
                )
                continue
            office_id = self.office(office)
            if office_id in seen:
                self.issue(
                    sid,
                    n,
                    None,
                    office,
                    "duplicate_office_row",
                    "same office appears twice; later row skipped",
                )
                continue
            seen.add(office_id)
            rank, per_day, workdays = (
                to_int(v.get("RANK")),
                to_float(v.get("ALJ_DISPS_PER_DAY_PER_ALJ")),
                to_int(v.get("WORKDAYS")),
            )
            if rank is None or per_day is None or workdays is None:
                self.issue(
                    sid,
                    n,
                    None,
                    office,
                    "bad_or_missing_number",
                    f"RANK={v.get('RANK')!r} PER_DAY={v.get('ALJ_DISPS_PER_DAY_PER_ALJ')!r} WORKDAYS={v.get('WORKDAYS')!r}",
                )
            batch.append(
                (
                    sid,
                    office_id,
                    self.region(region),
                    rank,
                    per_day,
                    workdays,
                    iso_date(v.get("RPTG_PRD_ENDT")),
                )
            )
        self.db.executemany("INSERT INTO office_ranking VALUES (?,?,?,?,?,?,?)", batch)
        return len(batch)


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--db", type=Path, default=DEFAULT_DB)
    ap.add_argument(
        "--force", action="store_true", help="reload snapshots even if the SHA-256 is unchanged"
    )
    args = ap.parse_args()

    if not MANIFEST.exists():
        print("No data/manifest.json - run data/scripts/crawl_ssa_alj.py first.", file=sys.stderr)
        return 2
    manifest = json.loads(MANIFEST.read_text())

    args.db.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(args.db)
    db.executescript(SCHEMA.read_text())
    loader = Loader(db)

    loaded = skipped = failed = 0
    for url, entry in sorted(manifest["files"].items()):
        if entry.get("kind") != "xml" or entry.get("status") != 200:
            continue
        path = REPO_ROOT / entry["local_path"]
        try:
            outcome = loader.load_file(url, entry, path, args.force)
        except Exception as exc:  # keep going; report at the end
            failed += 1
            print(f"FAILED {url.rsplit('/', 1)[-1]}: {exc}", file=sys.stderr)
            continue
        loaded += outcome == "loaded"
        skipped += outcome == "skipped"

    with db:
        db.execute("""UPDATE alj SET
            first_seen_period = (SELECT MIN(s.reporting_period_end) FROM alj_disposition d JOIN report_snapshot s USING (snapshot_id) WHERE d.alj_id = alj.alj_id),
            last_seen_period  = (SELECT MAX(s.reporting_period_end) FROM alj_disposition d JOIN report_snapshot s USING (snapshot_id) WHERE d.alj_id = alj.alj_id)""")

    def q(sql):
        return db.execute(sql).fetchone()[0]

    print(f"snapshots loaded={loaded} skipped={skipped} failed={failed}")
    print(
        f"report_snapshot={q('SELECT COUNT(*) FROM report_snapshot')} "
        f"alj_disposition={q('SELECT COUNT(*) FROM alj_disposition')} "
        f"office_ranking={q('SELECT COUNT(*) FROM office_ranking')} "
        f"alj={q('SELECT COUNT(*) FROM alj')} hearing_office={q('SELECT COUNT(*) FROM hearing_office')} "
        f"region={q('SELECT COUNT(*) FROM region')}"
    )
    print("load_issue by type:")
    for t, c in db.execute(
        "SELECT issue_type, COUNT(*) FROM load_issue GROUP BY 1 ORDER BY 2 DESC"
    ):
        print(f"  {t:40s} {c}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

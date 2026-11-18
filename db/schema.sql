-- SSA ALJ Disposition open data - SQLite schema
-- Source: https://www.ssa.gov/appeals/DataSets/ (XML files listed in Data.gov collection US-GOV-SSA-1199)
-- Design notes: see AI-Context/SSA_ALJ_Disposition_DB_Schema.md
--
-- Principles
--   * Rows are stored exactly as SSA published them (faithful copy). Arithmetic anomalies are NOT
--     rejected; they are recorded in load_issue so nothing is silently "fixed" or dropped.
--   * Derived measures (other_dispositions, rates) live in views, not columns.
--   * Dates are ISO-8601 text (SSA publishes MM/DD/YYYY); region codes stay 2-char text ('01'..'12').

PRAGMA foreign_keys = ON;

-- One row per published XML file (a monthly / fiscal-year-end report snapshot).
CREATE TABLE IF NOT EXISTS report_snapshot (
    snapshot_id            INTEGER PRIMARY KEY,
    report_kind            TEXT NOT NULL CHECK (report_kind IN ('alj_disposition', 'office_ranking')),
    catalog_identifier     TEXT,                -- Data.gov identifier, e.g. US-GOV-SSA-299
    catalog_slug           TEXT,
    catalog_title          TEXT,                -- e.g. "ALJ Disposition Data - June 2026"
    catalog_modified       TEXT,                -- Data.gov "modified" (can be stale; informational only)
    source_xml_url         TEXT NOT NULL UNIQUE,
    source_html_url        TEXT,
    fiscal_year            INTEGER,             -- US fiscal year (Oct-Sep) derived from reporting_period_end
    report_label           TEXT,                -- month token from the filename, or 'Current Report'
    is_current_report      INTEGER NOT NULL DEFAULT 0 CHECK (is_current_report IN (0, 1)),
    xml_title              TEXT,                -- <title> element (NOT reliable for schema detection)
    reporting_period_end   TEXT NOT NULL,       -- ISO date from header <RPTG_PRD_ENDT>
    file_created_date      TEXT,                -- ISO date from <data created="...">
    declared_record_count  INTEGER,             -- <data records="..."> (wrong in some files)
    loaded_row_count       INTEGER,
    schema_variant         TEXT,                -- 'A' no per-row RPTG_PRD_ENDT, 'B' per-row, 'R' ranking
    local_path             TEXT,                -- cached raw XML (data/raw/...)
    content_sha256         TEXT,
    fetched_at             TEXT,
    loaded_at              TEXT
);
CREATE INDEX IF NOT EXISTS ix_snapshot_period ON report_snapshot (report_kind, reporting_period_end);

CREATE TABLE IF NOT EXISTS region (
    region_code  TEXT PRIMARY KEY CHECK (length(region_code) = 2)
);

CREATE TABLE IF NOT EXISTS hearing_office (
    office_id    INTEGER PRIMARY KEY,
    office_name  TEXT NOT NULL UNIQUE           -- as published, e.g. 'SHREVEPORT', 'MIAMI OHO'
);

-- SSA publishes NO judge id: identity is the published name string.
CREATE TABLE IF NOT EXISTS alj (
    alj_id            INTEGER PRIMARY KEY,
    name_raw          TEXT NOT NULL UNIQUE,     -- 'Abbondondelo, Mary' (exactly as published, whitespace-collapsed)
    name_key          TEXT NOT NULL,            -- lower-case, punctuation removed: 'akins george m' (groups 'Akins, George M' / 'Akins, George M.')
    last_name         TEXT,
    given_names       TEXT,
    first_seen_period TEXT,
    last_seen_period  TEXT
);

CREATE INDEX IF NOT EXISTS ix_alj_name_key ON alj (name_key);

-- Fact: one source <row> = one (published judge name, office) line of one report snapshot.
-- Normally (snapshot, alj, office) is unique, but SSA files occasionally repeat the same name+office
-- with DIFFERENT numbers (likely two judges sharing a published name, or split lines). Both rows are
-- kept (see load_issue 'duplicate_judge_office_row'); office/region are NULL when blank in the source.
CREATE TABLE IF NOT EXISTS alj_disposition (
    snapshot_id                    INTEGER NOT NULL REFERENCES report_snapshot(snapshot_id) ON DELETE CASCADE,
    row_number                     INTEGER NOT NULL,   -- 1-based position of the <row> in the XML file
    alj_id                         INTEGER NOT NULL REFERENCES alj(alj_id),
    office_id                      INTEGER REFERENCES hearing_office(office_id),
    region_code                    TEXT    REFERENCES region(region_code),  -- as reported in that file
    fully_favorable                INTEGER,
    partially_favorable            INTEGER,
    total_awards                   INTEGER,
    total_denials                  INTEGER,
    total_decisions                INTEGER,
    total_dispositions             INTEGER,
    total_dispositions_all_offices INTEGER,     -- XML tag TOTAL_ALJ_DIPOSITIONS_ACROSS_ALL_OFFICES (sic)
    row_reporting_period_end       TEXT,        -- per-row RPTG_PRD_ENDT when the file has it
    PRIMARY KEY (snapshot_id, row_number)
);
CREATE INDEX IF NOT EXISTS ix_disp_key    ON alj_disposition (snapshot_id, alj_id, office_id);
CREATE INDEX IF NOT EXISTS ix_disp_alj    ON alj_disposition (alj_id, snapshot_id);
CREATE INDEX IF NOT EXISTS ix_disp_office ON alj_disposition (office_id, snapshot_id);
CREATE INDEX IF NOT EXISTS ix_disp_region ON alj_disposition (region_code, snapshot_id);

-- Fact: National Ranking Report - dispositions per day per ALJ, by hearing office.
CREATE TABLE IF NOT EXISTS office_ranking (
    snapshot_id                  INTEGER NOT NULL REFERENCES report_snapshot(snapshot_id) ON DELETE CASCADE,
    office_id                    INTEGER NOT NULL REFERENCES hearing_office(office_id),
    region_code                  TEXT    NOT NULL REFERENCES region(region_code),
    rank                         INTEGER,
    alj_dispositions_per_day     REAL,          -- XML tag ALJ_DISPS_PER_DAY_PER_ALJ
    workdays                     INTEGER,
    row_reporting_period_end     TEXT,
    PRIMARY KEY (snapshot_id, office_id)
);
CREATE INDEX IF NOT EXISTS ix_rank_office ON office_ranking (office_id, snapshot_id);

-- Anomalies found while loading (arithmetic mismatches, count mismatches, duplicates, bad values).
CREATE TABLE IF NOT EXISTS load_issue (
    issue_id     INTEGER PRIMARY KEY,
    snapshot_id  INTEGER REFERENCES report_snapshot(snapshot_id) ON DELETE CASCADE,
    row_number   INTEGER,                       -- 1-based position of the <row> in the file (NULL = file level)
    alj_name     TEXT,
    office_name  TEXT,
    issue_type   TEXT NOT NULL,
    detail       TEXT
);
CREATE INDEX IF NOT EXISTS ix_issue_snapshot ON load_issue (snapshot_id, issue_type);

-- ---------------------------------------------------------------------------------------------
-- Views (derived measures)
-- ---------------------------------------------------------------------------------------------
CREATE VIEW IF NOT EXISTS v_alj_disposition AS
SELECT d.*,
       s.reporting_period_end, s.fiscal_year, s.report_label,
       a.name_raw    AS alj_name,
       o.office_name AS office_name,
       d.total_dispositions - d.total_decisions AS other_dispositions,
       CASE WHEN d.total_decisions > 0 THEN 1.0 * d.total_awards  / d.total_decisions END AS allowance_rate,
       CASE WHEN d.total_decisions > 0 THEN 1.0 * d.total_denials / d.total_decisions END AS denial_rate
FROM alj_disposition d
JOIN report_snapshot s USING (snapshot_id)
JOIN alj a            USING (alj_id)
LEFT JOIN hearing_office o USING (office_id);

CREATE VIEW IF NOT EXISTS v_office_summary AS
SELECT snapshot_id, office_id, office_name, region_code, reporting_period_end,
       COUNT(DISTINCT alj_id)      AS alj_count,
       SUM(fully_favorable)        AS fully_favorable,
       SUM(partially_favorable)    AS partially_favorable,
       SUM(total_awards)           AS total_awards,
       SUM(total_denials)          AS total_denials,
       SUM(total_decisions)        AS total_decisions,
       SUM(total_dispositions)     AS total_dispositions,
       CASE WHEN SUM(total_decisions) > 0 THEN 1.0 * SUM(total_awards) / SUM(total_decisions) END AS allowance_rate
FROM v_alj_disposition
GROUP BY snapshot_id, office_id, office_name, region_code, reporting_period_end;

CREATE VIEW IF NOT EXISTS v_alj_summary AS
SELECT snapshot_id, alj_id, alj_name, reporting_period_end,
       COUNT(*)                    AS office_count,
       SUM(total_awards)           AS total_awards,
       SUM(total_denials)          AS total_denials,
       SUM(total_decisions)        AS total_decisions,
       SUM(total_dispositions)     AS total_dispositions,
       CASE WHEN SUM(total_decisions) > 0 THEN 1.0 * SUM(total_awards) / SUM(total_decisions) END AS allowance_rate
FROM v_alj_disposition
GROUP BY snapshot_id, alj_id, alj_name, reporting_period_end;

CREATE VIEW IF NOT EXISTS v_office_ranking AS
SELECT r.*, s.reporting_period_end, s.fiscal_year, o.office_name
FROM office_ranking r
JOIN report_snapshot s USING (snapshot_id)
JOIN hearing_office o  USING (office_id);

-- The newest disposition snapshot (by period end).
CREATE VIEW IF NOT EXISTS v_latest_disposition_snapshot AS
SELECT * FROM report_snapshot
WHERE report_kind = 'alj_disposition'
ORDER BY reporting_period_end DESC, snapshot_id DESC
LIMIT 1;

-- The last report of each fiscal year (reports are cumulative fiscal-year-to-date, so the final one
-- holds the full-year figures). When two September files exist (52/53-week variants) the later period wins.
CREATE VIEW IF NOT EXISTS v_fy_final_snapshot AS
SELECT s.*
FROM report_snapshot s
WHERE s.report_kind = 'alj_disposition'
  AND s.snapshot_id = (SELECT s2.snapshot_id FROM report_snapshot s2
                       WHERE s2.report_kind = s.report_kind AND s2.fiscal_year = s.fiscal_year
                       ORDER BY s2.reporting_period_end DESC, s2.snapshot_id DESC LIMIT 1);

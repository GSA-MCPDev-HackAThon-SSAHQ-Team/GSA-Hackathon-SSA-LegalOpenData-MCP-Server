#!/usr/bin/env python3
"""
Build a clean, professional SSA ALJ hackathon deck (10×5.625") plus evaluation DOCX.

Typography system (all slides):
  - Header bar: full-width black, title 22 pt white Calibri
  - Body: 13 pt · section labels 13 pt bold · muted notes 11 pt
  - Margins: 0.45" left/right · body starts 0.95" from top
  - Consistent bullet indent and paragraph spacing
"""

from __future__ import annotations

from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parents[2]
DEMO = Path(__file__).resolve().parent
SHOTS = DEMO / "screenshots"
DOCS = ROOT / "docs"
EVAL_SHOTS = ROOT / "eval" / "screenshots"
OUT_PPTX = DEMO / "SSA-ALJ-MCP-Hackathon-Deck.pptx"

# ── design tokens ────────────────────────────────────────────────────────
W, H = Inches(10), Inches(5.625)  # match official sample aspect
MARGIN_X = Inches(0.45)
BODY_TOP = Inches(0.95)
BODY_W = W - 2 * MARGIN_X
BODY_H = H - BODY_TOP - Inches(0.28)
HEADER_H = Inches(0.72)

BLACK = RGBColor(0x1A, 0x1A, 0x1A)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
MUTED = RGBColor(0x5A, 0x5A, 0x5A)
RULE = RGBColor(0xE6, 0xE6, 0xE6)
ACCENT = RGBColor(0x0B, 0x3D, 0x6E)  # deep federal blue
LIGHT = RGBColor(0xF5, 0xF7, 0xF9)
FONT = "Calibri"


def _run(paragraph, text, *, size=13, bold=False, color=BLACK, italic=False):
    run = paragraph.add_run()
    run.text = text
    run.font.name = FONT
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = color
    return run


def _clear_paragraph(p):
    p.clear()


def new_prs() -> Presentation:
    prs = Presentation()
    prs.slide_width = W
    prs.slide_height = H
    return prs


def blank(prs):
    return prs.slides.add_slide(prs.slide_layouts[6])


def add_header(slide, title: str):
    bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, W, HEADER_H)
    bar.fill.solid()
    bar.fill.fore_color.rgb = BLACK
    bar.line.fill.background()
    tf = bar.text_frame
    tf.word_wrap = True
    tf.margin_left = Inches(0.4)
    tf.margin_right = Inches(0.4)
    tf.margin_top = Inches(0.16)
    tf.margin_bottom = Inches(0.08)
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.LEFT
    _run(p, title, size=20, bold=True, color=WHITE)


def add_footer_rule(slide):
    line = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, MARGIN_X, H - Inches(0.22), BODY_W, Pt(1.25)
    )
    line.fill.solid()
    line.fill.fore_color.rgb = RULE
    line.line.fill.background()


def textbox(slide, left, top, width, height):
    box = slide.shapes.add_textbox(left, top, width, height)
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = Pt(2)
    tf.margin_right = Pt(2)
    tf.margin_top = Pt(0)
    tf.margin_bottom = Pt(0)
    return box, tf


def write_lines(tf, lines: list[tuple[str, dict]], *, space_after=6):
    """lines: list of (text, style_kwargs). First paragraph reused."""
    first = True
    for text, style in lines:
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        p.alignment = style.get("align", PP_ALIGN.LEFT)
        p.space_before = Pt(style.get("space_before", 0))
        p.space_after = Pt(style.get("space_after", space_after))
        p.level = style.get("level", 0)
        _run(
            p,
            text,
            size=style.get("size", 13),
            bold=style.get("bold", False),
            color=style.get("color", BLACK),
            italic=style.get("italic", False),
        )


def bullet(text, *, size=13, muted=False, space_after=5):
    return (
        "•  " + text,
        {"size": size, "color": MUTED if muted else BLACK, "space_after": space_after},
    )


def section(text, *, space_before=10):
    return (text, {"size": 13, "bold": True, "color": ACCENT, "space_before": space_before, "space_after": 4})


def body(text, *, size=13, space_after=6):
    return (text, {"size": size, "space_after": space_after})


def muted(text, *, size=11, space_after=4):
    return (text, {"size": size, "color": MUTED, "italic": True, "space_after": space_after})


def add_image(slide, path: Path, left, top, max_w, max_h):
    if not path.exists():
        return None
    pic = slide.shapes.add_picture(str(path), left, top)
    scale = min(max_w / pic.width, max_h / pic.height)
    pic.width = int(pic.width * scale)
    pic.height = int(pic.height * scale)
    return pic


def card(slide, left, top, width, height):
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = LIGHT
    shape.line.color.rgb = RULE
    shape.line.width = Pt(0.75)
    shape.adjustments[0] = 0.08
    return shape


# ── slides ───────────────────────────────────────────────────────────────


def slide_title(prs):
    s = blank(prs)
    # full dark panel
    bg = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, W, H)
    bg.fill.solid()
    bg.fill.fore_color.rgb = BLACK
    bg.line.fill.background()
    accent = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, Inches(2.15), Inches(0.12), Inches(1.55))
    accent.fill.solid()
    accent.fill.fore_color.rgb = ACCENT
    accent.line.fill.background()

    _, tf = textbox(s, Inches(0.55), Inches(2.15), Inches(9), Inches(0.7))
    write_lines(tf, [("SSA ALJ Open Data MCP Server", {"size": 32, "bold": True, "color": WHITE, "space_after": 0})])

    _, tf = textbox(s, Inches(0.55), Inches(2.9), Inches(9), Inches(0.45))
    write_lines(
        tf,
        [
            (
                "GSA MCP Server & SI Agent Government Hackathon",
                {"size": 16, "color": RGBColor(0xC8, 0xC8, 0xC8), "space_after": 0},
            )
        ],
    )
    _, tf = textbox(s, Inches(0.55), Inches(3.4), Inches(9), Inches(0.4))
    write_lines(
        tf,
        [
            (
                "Dataset Access  ·  Public SSA OHO ALJ Disposition Statistics (FY 2010–2026)",
                {"size": 13, "color": RGBColor(0x9A, 0x9A, 0x9A), "space_after": 0},
            )
        ],
    )
    _, tf = textbox(s, Inches(0.55), Inches(4.55), Inches(9), Inches(0.35))
    write_lines(
        tf,
        [
            (
                "https://www.ssa-alj-mcpserver-gsahackathon.online/mcp",
                {"size": 12, "color": RGBColor(0x8F, 0xB8, 0xDE), "space_after": 0},
            )
        ],
    )


def slide_challenge(prs):
    s = blank(prs)
    add_header(s, "The Challenge: Accessing SSA ALJ Disposition Data")
    add_footer_rule(s)
    _, tf = textbox(s, MARGIN_X, BODY_TOP, BODY_W, BODY_H)
    write_lines(
        tf,
        [
            body(
                "Oversight analysts and SI agents need reliable answers from public SSA ALJ disposition "
                "statistics (Data.gov US-GOV-SSA-1199). The published files alone are a poor agent interface.",
                space_after=10,
            ),
            section("1. Fragmented FYTD XML corpus", space_before=2),
            bullet("Dozens of cumulative snapshots (FY2010–2026); schemas drift; office names rename; no judge IDs."),
            section("2. FYTD semantics trap"),
            bullet("September ≈ full year; mid-year files are partial. LLMs invent rates if left to scrape alone."),
            section("3. No unified query surface"),
            bullet("No agent API for ranking offices, within-office variation, judge vs national, or ssa.gov verification."),
            section("4. Misuse and verification gap"),
            bullet("Rates are not case-mix adjusted. Even correct figures need a path back to SSA HTML/XML for audit."),
        ],
        space_after=4,
    )


def slide_solution(prs):
    s = blank(prs)
    add_header(s, "The Solution: an MCP Server for SSA ALJ Open Data")
    add_footer_rule(s)
    _, tf = textbox(s, MARGIN_X, BODY_TOP, BODY_W, BODY_H)
    write_lines(
        tf,
        [
            body(
                "A read-only MCP translation layer — agents call goal-shaped tools; they never need XML layout or FYTD math.",
                space_after=10,
            ),
            bullet("Unified interface — 15 tools · resource ssa-alj://about · 2 prompts over local SQLite (~311k rows)"),
            bullet("Offline ETL — crawl + load once; runtime opens DB read-only (no live scrape, no outbound network)"),
            bullet("Built-in semantics — FYTD differencing, pagination envelopes, snapshot as-of metadata, notes[]"),
            bullet("Agent ergonomics — Pydantic inputs, tool groups (discovery / lookup / analysis), business_queries"),
            bullet("Natural language access — Claude Desktop, ChatGPT, Cursor, MCPJam against live HTTPS /mcp"),
            bullet("Safe scope — guardrails refuse PII/security probes and forecast / “best performer” asks"),
            muted("Live endpoint: https://www.ssa-alj-mcpserver-gsahackathon.online/mcp", size=12, space_after=0),
        ],
    )


def slide_architecture(prs):
    s = blank(prs)
    add_header(s, "Server Design Overview")
    add_footer_rule(s)
    left_w = Inches(4.55)
    _, tf = textbox(s, MARGIN_X, BODY_TOP, left_w, BODY_H)
    write_lines(
        tf,
        [
            section("Architecture", space_before=0),
            body(
                "FastMCP (Python). Thin tool wrappers → services (SQL) → db.py (SQLite mode=ro).",
                size=12,
                space_after=8,
            ),
            bullet("tools/ — one file per tool; shared _common.py", size=12),
            bullet("services/ — judges, offices, trends, analysis…", size=12),
            bullet("resources/ + prompts/ — about + workflows", size=12),
            bullet("data/scripts/ — offline ETL (not in runtime)", size=12),
            bullet("Transports — stdio · streamable-HTTP /mcp", size=12),
            muted("docs/ARCHITECTURE.md · CODEMAP.md", size=11, space_after=0),
        ],
    )
    add_image(
        s,
        DOCS / "ssa-alj-mcp-architecture.jpg",
        MARGIN_X + left_w + Inches(0.15),
        BODY_TOP,
        Inches(4.7),
        BODY_H,
    )


def slide_decision_etl(prs):
    s = blank(prs)
    add_header(s, "Key Technical Decision 1 — Offline ETL + Local SQLite")
    add_footer_rule(s)
    left_w = Inches(4.7)
    _, tf = textbox(s, MARGIN_X, BODY_TOP, left_w, BODY_H)
    write_lines(
        tf,
        [
            body("Decision: Materialize public SSA XML into data/ssa_alj.sqlite.", space_after=4),
            muted("data/scripts/ · data/db/schema.sql · data/ssa_alj.sqlite", space_after=8),
            section("Rationale", space_before=0),
            bullet("Zero network dependency at request time", size=12),
            bullet("FYTD semantics encoded once in services", size=12),
            bullet("Single source of truth, versioned with code", size=12),
            bullet("Docker/Render ships the SQLite artifact", size=12),
            bullet("Refresh = re-run crawl then load", size=12),
            section("Example path"),
            muted("list_reports → compare_offices → profile → source_links", size=11, space_after=0),
        ],
    )
    add_image(
        s,
        DOCS / "ssa-alj-data-prep-flow.jpg",
        MARGIN_X + left_w + Inches(0.1),
        BODY_TOP,
        Inches(4.55),
        BODY_H,
    )


def slide_decision_tools(prs):
    s = blank(prs)
    add_header(s, "Key Technical Decision 2 — Goal-Shaped Modular Tools")
    add_footer_rule(s)
    # two columns
    col_w = (BODY_W - Inches(0.25)) / 2
    _, tf = textbox(s, MARGIN_X, BODY_TOP, col_w, BODY_H)
    write_lines(
        tf,
        [
            body("Decision: One MCP tool per file; SQL lives in services/.", space_after=8),
            section("Structure", space_before=0),
            muted("src/ssa_alj_mcp/tools/", size=12, space_after=4),
            bullet("_common.py — tags + annotations", size=12),
            bullet("business_queries.py — recipes", size=12),
            bullet("compare_offices.py — rankings", size=12),
            bullet("national_trend.py — FY series", size=12),
            bullet("source_links.py — ssa.gov URLs", size=12),
            bullet("…10 more goal tools", size=12),
        ],
    )
    _, tf = textbox(s, MARGIN_X + col_w + Inches(0.25), BODY_TOP, col_w, BODY_H)
    write_lines(
        tf,
        [
            section("Rationale", space_before=0),
            bullet("Independently testable units", size=12),
            bullet("Tools wrap analyst goals — not REST/XML GETs", size=12),
            bullet("Soft groups: discovery · lookup · analysis", size=12),
            bullet("Clean register(mcp) pattern", size=12),
            section("Criterion fit"),
            bullet("C1 — clear module boundaries", size=12),
            bullet("C3 — agent-facing actions, not thin wrappers", size=12),
        ],
    )


def slide_decision_pydantic(prs):
    s = blank(prs)
    add_header(s, "Key Technical Decision 3 — Validation, Envelopes & Guardrails")
    add_footer_rule(s)
    # three cards
    gap = Inches(0.2)
    card_w = (BODY_W - 2 * gap) / 3
    card_h = Inches(3.85)
    top = BODY_TOP + Inches(0.05)
    cards = [
        (
            "Validated inputs",
            [
                "Pydantic / Field descriptions",
                "Precise tool names for LLM selection",
                "response_format: json | markdown",
                "Read-only / idempotent annotations",
            ],
        ),
        (
            "Stable envelopes",
            [
                "Pagination: total · count · offset",
                "notes[] on successful replies",
                "snapshot: period_end · fiscal_year",
                "{error, hint} — no stack traces",
            ],
        ),
        (
            "Scope guardrails",
            [
                "Refuse PII / security probes",
                "Forecast & “best performer” notes",
                "data_quality_notes for gaps",
                "source_links for human audit",
            ],
        ),
    ]
    for i, (title, items) in enumerate(cards):
        left = MARGIN_X + i * (card_w + gap)
        card(s, left, top, card_w, card_h)
        _, tf = textbox(s, left + Inches(0.18), top + Inches(0.2), card_w - Inches(0.36), card_h - Inches(0.35))
        lines = [section(title, space_before=0)]
        for it in items:
            lines.append(bullet(it, size=12, space_after=8))
        write_lines(tf, lines)


def slide_demo(prs):
    s = blank(prs)
    add_header(s, "MCP Server Demo — Claude Desktop + Live /mcp")
    add_footer_rule(s)
    # left captions, right screenshot
    _, tf = textbox(s, MARGIN_X, BODY_TOP, Inches(3.2), BODY_H)
    write_lines(
        tf,
        [
            section("5-minute flow", space_before=0),
            bullet("Open live landing page", size=12),
            bullet("Add custom connector → /mcp", size=12),
            bullet("Enable plugin in chat", size=12),
            bullet("tools/list → 15 tools", size=12),
            bullet("business_queries recipes", size=12),
            bullet("FY2024 national allowance", size=12),
            section("Also shown"),
            bullet("MCPJam Inspect / Evaluate", size=12),
            muted("Full script: docs/demo/demo.md", size=11, space_after=0),
        ],
    )
    add_image(
        s,
        SHOTS / "demo-claude-desktop-fy2024-national-result.png",
        Inches(3.85),
        BODY_TOP,
        Inches(5.7),
        BODY_H,
    )


def slide_demo_mcpjam(prs):
    s = blank(prs)
    add_header(s, "MCP Server Demo — MCPJam Playground")
    add_footer_rule(s)
    add_image(
        s,
        SHOTS / "demo-mcpjam-chatgpt-tools-list.png",
        MARGIN_X,
        BODY_TOP,
        Inches(4.55),
        BODY_H,
    )
    add_image(
        s,
        SHOTS / "demo-mcpjam-resources-about.png",
        Inches(5.15),
        BODY_TOP,
        Inches(4.4),
        BODY_H,
    )


def slide_eval_setup(prs):
    s = blank(prs)
    add_header(s, "MCP Server Evaluation — Setup")
    add_footer_rule(s)
    col_w = (BODY_W - Inches(0.25)) / 2
    _, tf = textbox(s, MARGIN_X, BODY_TOP, col_w, BODY_H)
    write_lines(
        tf,
        [
            section("Deterministic (keyless)", space_before=0),
            bullet("12 gold questions (evaluation.xml)", size=12),
            bullet("8 error scenarios → {error, hint}", size=12),
            bullet("Latency probes + scripted multihop", size=12),
            bullet("HTTP /health · db_ok", size=12),
            bullet("CI: uv run pytest -q", size=12),
            muted("uv run python eval/deterministic/run_eval.py --http", size=10),
        ],
    )
    _, tf = textbox(s, MARGIN_X + col_w + Inches(0.25), BODY_TOP, col_w, BODY_H)
    write_lines(
        tf,
        [
            section("Host & agent suites", space_before=0),
            bullet("mcpevals.ai — tool tests", size=12),
            bullet("MCP Playground — recipes", size=12),
            bullet("MCPJam — Claude / ChatGPT / Cursor", size=12),
            bullet("Optional: eval/sdk/ (mcpevals)", size=12),
            section("Evidence"),
            bullet("eval/RESULTS.md · LEARNINGS.md", size=12),
            bullet("Screenshots under eval/ & docs/demo/", size=12),
        ],
    )


def slide_eval_results(prs):
    s = blank(prs)
    add_header(s, "MCP Server Evaluation — Results")
    add_footer_rule(s)
    # metric strip as three mini cards
    gap = Inches(0.15)
    mw = (BODY_W - 2 * gap) / 3
    metrics = [
        ("12/12", "Gold answers"),
        ("8/8", "Error cases"),
        ("83%", "MCPJam Run #3"),
    ]
    for i, (num, label) in enumerate(metrics):
        left = MARGIN_X + i * (mw + gap)
        card(s, left, BODY_TOP, mw, Inches(1.05))
        _, tf = textbox(s, left, BODY_TOP + Inches(0.12), mw, Inches(0.85))
        write_lines(
            tf,
            [
                (num, {"size": 22, "bold": True, "color": ACCENT, "align": PP_ALIGN.CENTER, "space_after": 0}),
                (label, {"size": 11, "color": MUTED, "align": PP_ALIGN.CENTER, "space_after": 0}),
            ],
        )

    _, tf = textbox(s, MARGIN_X, BODY_TOP + Inches(1.25), Inches(4.3), Inches(3.1))
    write_lines(
        tf,
        [
            section("Also recorded", space_before=0),
            bullet("Multihop 5/5 · Latency 5/5", size=12),
            bullet("SQL p50 typically < 40 ms", size=12),
            bullet("/health p50 ≈ 1 ms", size=12),
            bullet("mcpevals.ai 16/16 (100%)", size=12),
            bullet("MCP Playground 3/3", size=12),
            muted("Run #3 improved from early 38% baseline", size=11),
            muted("Remaining gaps tracked in LEARNINGS.md", size=11, space_after=0),
        ],
    )
    add_image(
        s,
        SHOTS / "demo-mcpjam-evals-run3-83.png",
        Inches(5.0),
        BODY_TOP + Inches(1.2),
        Inches(4.55),
        Inches(3.2),
    )


def slide_security(prs):
    s = blank(prs)
    add_header(s, "Security Considerations")
    add_footer_rule(s)
    col_w = (BODY_W - Inches(0.25)) / 2
    _, tf = textbox(s, MARGIN_X, BODY_TOP, col_w, BODY_H)
    write_lines(
        tf,
        [
            section("Public data, read-only", space_before=0),
            bullet("SSA published statistics only", size=12),
            bullet("No claimant PII or CUI", size=12),
            bullet("DB: mode=ro + PRAGMA query_only", size=12),
            bullet("Parameterised SQL only", size=12),
            bullet("No outbound network from process", size=12),
            section("Secrets posture"),
            bullet("No SSA API credentials required", size=12),
            bullet("/mcp unauthenticated (hackathon public-data)", size=12),
            muted("See SECURITY.md for production auth/ATO", size=10, space_after=0),
        ],
    )
    _, tf = textbox(s, MARGIN_X + col_w + Inches(0.25), BODY_TOP, col_w, BODY_H)
    write_lines(
        tf,
        [
            section("Attack surface & mitigations", space_before=0),
            bullet("MCP inputs → Pydantic + guardrails", size=12),
            bullet("Errors → {error, hint}, no stack traces", size=12),
            bullet("No SSRF — no user-supplied URL fetch", size=12),
            bullet("source_links returns known SSA URLs", size=12),
            bullet("/health reports db_ok", size=12),
            section("Out of scope"),
            bullet("Not a case-mix rating system", size=12),
            bullet("Not an auth gateway for non-public SSA", size=12),
        ],
    )


def slide_lessons(prs):
    s = blank(prs)
    add_header(s, "Lessons Learned and Recommendations")
    add_footer_rule(s)
    lessons = [
        (
            "1. Encode domain semantics in services",
            "FYTD differencing and as-of dates belong in code so agents cannot invent rates. Materialize messy federal corpora offline; keep MCP runtime read-only.",
        ),
        (
            "2. Goal-shaped tools beat mega-query APIs",
            "Intent tools with discovery/lookup/analysis groups + business_queries outperform one flexible endpoint. Put grouping metadata on tool objects.",
        ),
        (
            "3. Evaluate in layers — gold first, then hosts",
            "Deterministic 12/12 catches regressions; MCPJam exposes selection and refusal gaps. Treat refusal cases as first-class tests.",
        ),
        (
            "4. Always ship a verification path",
            "source_links + snapshot metadata turn answers into auditable oversight artifacts. Return provenance beside every figure.",
        ),
    ]
    _, tf = textbox(s, MARGIN_X, BODY_TOP, BODY_W, BODY_H)
    lines = []
    for title, body_text in lessons:
        lines.append(section(title, space_before=6 if lines else 0))
        lines.append(body(body_text, size=12, space_after=4))
    write_lines(tf, lines)


def slide_closing(prs):
    s = blank(prs)
    add_header(s, "Links & Evidence Pack")
    add_footer_rule(s)
    _, tf = textbox(s, MARGIN_X, BODY_TOP, BODY_W, BODY_H)
    write_lines(
        tf,
        [
            section("Live", space_before=0),
            bullet("MCP: https://www.ssa-alj-mcpserver-gsahackathon.online/mcp", size=12),
            bullet("Landing: https://www.ssa-alj-mcpserver-gsahackathon.online/", size=12),
            section("Documentation"),
            bullet("Demo script — docs/demo/demo.md", size=12),
            bullet("Architecture — docs/ARCHITECTURE.md", size=12),
            bullet("Judging map — JUDGE_CRITERIA.md", size=12),
            bullet("Eval results — eval/RESULTS.md", size=12),
            bullet("Evaluation DOCX — docs/demo/SSA-ALJ-MCP-Evaluation-Document.docx", size=12),
        ],
    )


def build_pptx():
    prs = new_prs()
    slide_title(prs)
    slide_challenge(prs)
    slide_solution(prs)
    slide_architecture(prs)
    slide_decision_etl(prs)
    slide_decision_tools(prs)
    slide_decision_pydantic(prs)
    slide_demo(prs)
    slide_demo_mcpjam(prs)
    slide_eval_setup(prs)
    slide_eval_results(prs)
    slide_security(prs)
    slide_lessons(prs)
    slide_closing(prs)
    prs.save(OUT_PPTX)
    print(f"Wrote {OUT_PPTX} ({len(prs.slides)} slides)")


def build_eval_docx():
    from docx import Document

    out = DEMO / "SSA-ALJ-MCP-Evaluation-Document.docx"
    doc = Document()
    doc.add_heading("Evaluation Document — SSA ALJ Open Data MCP Server", level=0)
    p = doc.add_paragraph()
    r = p.add_run("GSA MCP Server & SI Agent Government Hackathon · Dataset Access Server")
    r.italic = True

    def meta(label, value):
        p = doc.add_paragraph()
        p.add_run(label).bold = True
        p.add_run(value)

    meta("Server under test: ", "SSA ALJ Open Data MCP Server (FastMCP · 15 tools · read-only SQLite)")
    meta(
        "Evaluation layers: ",
        "Deterministic gold · pytest · mcpevals.ai · MCP Playground · MCPJam · optional eval/sdk",
    )
    meta("Live endpoint: ", "https://www.ssa-alj-mcpserver-gsahackathon.online/mcp")
    meta("Evidence: ", "eval/RESULTS.md · eval/sdk/RESULTS.md · docs/LEARNINGS.md · docs/demo/")
    meta("Date: ", "2026-11-18 (deterministic); MCPJam Run #3 thereafter")

    doc.add_heading("1. Overview and Objectives", level=2)
    doc.add_paragraph(
        "Determine whether the MCP server measurably improves an agent’s ability to answer "
        "oversight-style questions about public SSA ALJ disposition statistics accurately, "
        "with provenance, and within scope (including correct refusals)."
    )
    doc.add_paragraph(
        "The server exposes 15 goal-shaped tools (discovery / lookup / analysis), resource "
        "ssa-alj://about, and prompts compare_office_outcomes and judge_summary over a local "
        "read-only SQLite database built offline from ssa.gov FYTD XML (Data.gov US-GOV-SSA-1199)."
    )

    doc.add_heading("2. Testing Methodology", level=2)
    doc.add_heading("Framework & reproducibility", level=3)
    doc.add_paragraph(
        "Primary regressions are deterministic (no LLM): fixed arguments and expected field values."
    )
    doc.add_paragraph(
        "uv run python eval/deterministic/run_eval.py --http", style="Intense Quote"
    )
    doc.add_paragraph(
        "CI: uv run pytest -q (synthetic DB). External host suites exercise the same public /mcp URL. "
        "Optional agent SDK cases live under eval/sdk/ and are logged separately."
    )
    doc.add_heading("Golden dataset", level=3)
    doc.add_paragraph(
        "eval/gold/evaluation.xml + eval/deterministic/cases.json — 12 gold questions spanning "
        "national rates, office rankings, judge profiles, within-office gaps, processing rankings, "
        "workforce peaks, coverage counts, monthly pace, and explicit case-mix caveats."
    )
    doc.add_heading("Error & latency design", level=3)
    doc.add_paragraph(
        "Eight error scenarios must return {error, hint}. Latency probes record p50/p95. "
        "A scripted multihop checks list_reports → compare_offices → get_office_profile → "
        "outlier_report → national_trend."
    )
    doc.add_heading("Agent / host evaluation", level=3)
    doc.add_paragraph(
        "mcpevals.ai (16), MCP Playground (3), and MCPJam Evaluate cover selection, multi-turn "
        "verification, and refusal. Failure analysis: docs/LEARNINGS.md."
    )

    doc.add_heading("3. Performance Metrics", level=2)
    for item in [
        "Gold pass rate (exact field match)",
        "Error-handling pass rate ({error, hint})",
        "Response-shape / pagination envelope checks",
        "Service latency p50/p95 (local SQLite)",
        "HTTP /health latency and db_ok",
        "External tool-test pass rates",
        "Agent suite score (MCPJam) + refusal correctness",
    ]:
        doc.add_paragraph(item, style="List Bullet")

    doc.add_heading("Results (recorded)", level=3)
    table = doc.add_table(rows=1, cols=3)
    table.style = "Table Grid"
    hdr = table.rows[0].cells
    hdr[0].text, hdr[1].text, hdr[2].text = "Suite", "Result", "Notes"
    for a, b, c in [
        ("Gold answers", "12/12", "p50s typically < 40 ms"),
        ("Error handling", "8/8", "includes ambiguous CHARLESTON"),
        ("Latency probes", "5/5", "national_trend p50 ≈ 38 ms"),
        ("Scripted multihop", "5/5", "55 ms wall for chain"),
        ("HTTP /health", "ok", "p50 ≈ 1 ms · p95 ≈ 4 ms"),
        ("mcpevals.ai", "16/16 (100%)", "15 tools discovered"),
        ("MCP Playground", "3/3", "business_queries recipes"),
        ("MCPJam Run #3", "83% (10/12)", "up from early 38% baseline"),
    ]:
        cells = table.add_row().cells
        cells[0].text, cells[1].text, cells[2].text = a, b, c

    doc.add_paragraph()
    doc.add_heading("Failure analysis", level=3)
    doc.add_paragraph(
        "MCPJam remaining failures cluster on forecast/“best performer” refusal scoring and "
        "occasional tool-selection mismatches. Server-side fixes already landed; see LEARNINGS.md."
    )

    doc.add_heading("4. Security Considerations", level=2)
    doc.add_heading("Data classification", level=3)
    doc.add_paragraph(
        "Public SSA statistics only. Judge names as published. No claimant PII or CUI."
    )
    doc.add_heading("Scope containment", level=3)
    doc.add_paragraph(
        "Guardrails refuse forecasts, performance ratings, and PII/security probes. "
        "Notes restate that rates are not case-mix adjusted."
    )
    doc.add_heading("Secrets & configuration", level=3)
    doc.add_paragraph(
        "No SSA API key at runtime. Optional eval keys in .env (git-ignored). "
        "/mcp unauthenticated by default for public-data hackathon posture (SECURITY.md)."
    )
    doc.add_heading("Untrusted input", level=3)
    doc.add_paragraph(
        "Pydantic validation; structured {error, hint}; no user-supplied URL fetch."
    )
    doc.add_heading("Transport & isolation", level=3)
    doc.add_paragraph(
        "stdio or streamable-HTTP /mcp. DB mode=ro + PRAGMA query_only; parameterised SQL; "
        "no outbound network from the server process."
    )

    doc.add_heading("5. Lessons Learned & Recommendations", level=2)
    doc.add_heading("What worked", level=3)
    for item in [
        "Offline SQLite + FYTD semantics in services.",
        "Deterministic gold as a fast, keyless merge gate.",
        "source_links + snapshot metadata for auditability.",
        "Multi-host evidence on the same /mcp endpoint.",
    ]:
        doc.add_paragraph(item, style="List Bullet")
    doc.add_heading("Limitations", level=3)
    for item in [
        "Agent scores depend on host/model and case wording.",
        "Rates are not case-mix adjusted by design.",
        "Soft tool groups are advisory until hosts filter on tags.",
    ]:
        doc.add_paragraph(item, style="List Bullet")
    doc.add_heading("Recommendations", level=3)
    for item in [
        "Keep gold + error matrix as the merge gate.",
        "Include refusal cases in every agent suite.",
        "Report SQL latency beside agent wall-clock.",
        "Human-review failed iterations before schema changes.",
        "Before production: authentication and agency ATO review.",
    ]:
        doc.add_paragraph(item, style="List Bullet")

    foot = doc.add_paragraph()
    foot.add_run(
        "Companion deck: docs/demo/SSA-ALJ-MCP-Hackathon-Deck.pptx · Demo: docs/demo/demo.md"
    ).italic = True
    doc.save(out)
    print(f"Wrote {out}")


if __name__ == "__main__":
    build_pptx()
    build_eval_docx()

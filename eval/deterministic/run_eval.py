#!/usr/bin/env python3
"""Layer A — deterministic evaluation of the SSA ALJ MCP query services.

No LLM required. Exercises gold answers, graceful errors, response shape, and latency
against `data/ssa_alj.sqlite` (or `SSA_ALJ_DB_PATH`).

Usage (from repo root):
  uv run python eval/deterministic/run_eval.py
  uv run python eval/deterministic/run_eval.py --http   # also smoke streamable-HTTP /health + tool

Writes:
  eval/deterministic/last_run.json
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from importlib import import_module
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
CASES = Path(__file__).with_name("cases.json")
OUT = Path(__file__).with_name("last_run.json")


def _resolve(obj: Any, path: str) -> Any:
    cur = obj
    for part in path.split("."):
        if cur is None:
            return None
        if part.isdigit():
            cur = cur[int(part)]
        else:
            cur = cur[part]
    return cur


def _invoke(call: dict[str, Any]) -> dict[str, Any]:
    mod = import_module(f"ssa_alj_mcp.services.{call['service']}")
    fn = getattr(mod, call["fn"])
    return fn(**call.get("kwargs", {}))


def _check_expect(payload: dict[str, Any], expect: dict[str, Any]) -> tuple[bool, str]:
    if expect.get("has_error"):
        if "error" not in payload:
            return False, "expected error key"
        if expect.get("hint_present") and not payload.get("hint"):
            return False, "expected hint"
        return True, "error payload ok"

    if "keys" in expect:
        missing = [k for k in expect["keys"] if k not in payload]
        if missing:
            return False, f"missing keys {missing}"
        return True, "shape ok"

    value = _resolve(payload, expect["path"])
    if "equals" in expect and value != expect["equals"]:
        return False, f"{expect['path']}={value!r} != {expect['equals']!r}"
    if "contains" in expect:
        hay = value if isinstance(value, str) else json.dumps(value)
        if expect["contains"] not in hay:
            return False, f"{expect['path']} missing {expect['contains']!r}"
    if "length" in expect and len(value) != expect["length"]:
        return False, f"len({expect['path']})={len(value)} != {expect['length']}"
    return True, "ok"


def _percentile(xs: list[float], p: float) -> float:
    if not xs:
        return 0.0
    ys = sorted(xs)
    k = (len(ys) - 1) * p
    f = int(k)
    c = min(f + 1, len(ys) - 1)
    if f == c:
        return ys[f]
    return ys[f] + (ys[c] - ys[f]) * (k - f)


def run_suite(name: str, cases: list[dict[str, Any]]) -> dict[str, Any]:
    rows = []
    for case in cases:
        t0 = time.perf_counter()
        try:
            payload = _invoke(case["call"])
            ok, detail = _check_expect(payload, case["expect"])
        except Exception as exc:  # noqa: BLE001 — eval harness must never crash the suite
            ok, detail, payload = False, f"exception: {exc}", {}
        ms = (time.perf_counter() - t0) * 1000
        rows.append(
            {
                "id": case["id"],
                "name": case["name"],
                "ok": ok,
                "detail": detail,
                "ms": round(ms, 2),
            }
        )
    passed = sum(1 for r in rows if r["ok"])
    return {
        "suite": name,
        "passed": passed,
        "total": len(rows),
        "ok": passed == len(rows),
        "cases": rows,
    }


def run_latency(cases: list[dict[str, Any]]) -> dict[str, Any]:
    rows = []
    for case in cases:
        times: list[float] = []
        ok = True
        detail = "ok"
        for _ in range(int(case.get("repeats", 3))):
            t0 = time.perf_counter()
            try:
                payload = _invoke(case["call"])
                if "error" in payload:
                    ok = False
                    detail = payload.get("error", "error")
            except Exception as exc:  # noqa: BLE001
                ok = False
                detail = str(exc)
            times.append((time.perf_counter() - t0) * 1000)
        rows.append(
            {
                "id": case["id"],
                "name": case["name"],
                "ok": ok,
                "detail": detail,
                "n": len(times),
                "p50_ms": round(_percentile(times, 0.50), 2),
                "p95_ms": round(_percentile(times, 0.95), 2),
                "mean_ms": round(statistics.fmean(times), 2) if times else None,
            }
        )
    return {
        "suite": "latency",
        "passed": sum(1 for r in rows if r["ok"]),
        "total": len(rows),
        "ok": all(r["ok"] for r in rows),
        "cases": rows,
    }


def run_multihop() -> dict[str, Any]:
    """Scripted multi-tool path that mirrors a careful agent (no LLM)."""
    from ssa_alj_mcp.services import analysis, offices, reports, trends

    steps: list[dict[str, Any]] = []
    t0 = time.perf_counter()

    cov = reports.list_reports()
    steps.append(
        {
            "tool": "list_reports",
            "ok": "error" not in cov and 2024 in cov["coverage"]["fiscal_years"],
        }
    )

    ranked = offices.compare_offices(fiscal_year=2024, min_decisions=1000, limit=1)
    top = ranked.get("items", [{}])[0].get("office")
    steps.append({"tool": "compare_offices", "ok": top == "QUEENS", "top": top})

    profile = offices.get_office_profile("queens", fiscal_year=2024)
    steps.append(
        {
            "tool": "get_office_profile",
            "ok": "error" not in profile
            and abs(profile["fiscal_years"][-1]["allowance_rate"] - 0.8102) < 1e-9,
        }
    )

    outliers = analysis.outlier_report(level="office", fiscal_year=2024, limit=5)
    units = [i["unit"] for i in outliers.get("items", [])]
    steps.append({"tool": "outlier_report", "ok": "QUEENS" in units, "units": units[:3]})

    trend = trends.national_trend(from_fiscal_year=2010, to_fiscal_year=2024)
    steps.append(
        {
            "tool": "national_trend",
            "ok": trend["highlights"]["highest_allowance_rate"]["fiscal_year"] == 2010,
        }
    )

    ms = (time.perf_counter() - t0) * 1000
    ok = all(s["ok"] for s in steps)
    return {
        "suite": "multihop_scripted_agent",
        "ok": ok,
        "passed": sum(1 for s in steps if s["ok"]),
        "total": len(steps),
        "ms": round(ms, 2),
        "steps": steps,
        "narrative": (
            "list_reports → compare_offices(FY2024,min=1000) → get_office_profile(QUEENS) "
            "→ outlier_report → national_trend; expected top office QUEENS and peak FY 2010."
        ),
    }


def run_http_smoke(port: int = 8765) -> dict[str, Any]:
    """Start streamable-HTTP briefly; hit /health and one MCP-ish readiness check."""
    env = {
        **os.environ,
        "MCP_TRANSPORT": "streamable-http",
        "MCP_HOST": "127.0.0.1",
        "MCP_PORT": str(port),
    }
    proc = subprocess.Popen(
        ["uv", "run", "ssa-alj-mcp"],
        cwd=str(ROOT),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    url = f"http://127.0.0.1:{port}/health"
    latencies: list[float] = []
    health_ok = False
    body: dict[str, Any] = {}
    try:
        deadline = time.time() + 15
        while time.time() < deadline:
            try:
                t0 = time.perf_counter()
                with urllib.request.urlopen(url, timeout=1.5) as resp:
                    body = json.loads(resp.read().decode())
                    latencies.append((time.perf_counter() - t0) * 1000)
                    health_ok = bool(body.get("db_ok")) and resp.status == 200
                    if health_ok:
                        break
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
                time.sleep(0.25)
        # A few more sequential hits for stability
        for _ in range(3):
            t0 = time.perf_counter()
            with urllib.request.urlopen(url, timeout=2) as resp:
                latencies.append((time.perf_counter() - t0) * 1000)
                assert resp.status == 200
    except Exception as exc:  # noqa: BLE001
        return {"suite": "http_smoke", "ok": False, "detail": str(exc), "health": body}
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()

    return {
        "suite": "http_smoke",
        "ok": health_ok,
        "health": body,
        "p50_ms": round(_percentile(latencies, 0.50), 2) if latencies else None,
        "p95_ms": round(_percentile(latencies, 0.95), 2) if latencies else None,
        "samples": len(latencies),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--http", action="store_true", help="Also run streamable-HTTP /health smoke"
    )
    parser.add_argument("--json-out", type=Path, default=OUT)
    args = parser.parse_args()

    # Ensure package imports resolve when run as a script.
    sys.path.insert(0, str(ROOT / "src"))

    from ssa_alj_mcp.config import settings

    cases = json.loads(CASES.read_text())
    started = datetime.now(timezone.utc).isoformat()
    t0 = time.perf_counter()

    results = {
        "started_at": started,
        "db_path": str(settings.ssa_alj_db_path),
        "db_exists": Path(settings.ssa_alj_db_path).is_file(),
        "gold": run_suite("gold", cases["gold"]),
        "tool_choice": run_suite("tool_choice", cases.get("tool_choice", [])),
        "errors": run_suite("errors", cases["errors"]),
        "shape": run_suite("shape", cases["shape"]),
        "latency": run_latency(cases["latency"]),
        "multihop": run_multihop(),
    }
    if args.http:
        results["http_smoke"] = run_http_smoke()

    results["elapsed_ms"] = round((time.perf_counter() - t0) * 1000, 2)
    results["ok"] = (
        all(
            results[k].get("ok")
            for k in ("gold", "tool_choice", "errors", "shape", "latency", "multihop")
            if k in results and results[k].get("total", 0) > 0
        )
        and results.get("http_smoke", {"ok": True})["ok"]
    )

    args.json_out.write_text(json.dumps(results, indent=2) + "\n")

    def _line(suite: dict[str, Any]) -> str:
        return f"  {suite['suite']:28} {suite['passed']}/{suite['total']}  ok={suite['ok']}"

    print(f"DB: {results['db_path']} (exists={results['db_exists']})")
    for key in ("gold", "tool_choice", "errors", "shape", "latency", "multihop"):
        if key in results:
            print(_line(results[key]))
    if "http_smoke" in results:
        h = results["http_smoke"]
        print(
            f"  {'http_smoke':28} ok={h['ok']}  p50={h.get('p50_ms')}ms  health={h.get('health')}"
        )
    print(f"Overall ok={results['ok']}  wrote {args.json_out}")
    return 0 if results["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

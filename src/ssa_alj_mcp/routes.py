"""HTTP-only infrastructure routes (active with the streamable-http transport)."""

from __future__ import annotations

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from ssa_alj_mcp import __version__
from ssa_alj_mcp.config import settings
from ssa_alj_mcp.db import DatabaseUnavailable, connect
from ssa_alj_mcp.logging_config import get_logger

log = get_logger(__name__)


def register_routes(mcp: FastMCP) -> None:
    @mcp.custom_route("/health", methods=["GET"])
    async def health_check(request: Request) -> JSONResponse:
        # Fast path for platforms: always returns JSON; db_ok says whether tools can run.
        db_ok = False
        db_error = None
        try:
            with connect() as conn:
                conn.execute("SELECT 1 FROM report_snapshot LIMIT 1").fetchone()
            db_ok = True
        except DatabaseUnavailable as exc:
            db_error = str(exc)
            log.warning("health: database unavailable: %s", exc)
        except Exception as exc:  # pragma: no cover - defensive
            db_error = "database query failed"
            log.warning("health: unexpected database error: %s", exc)

        body = {
            "status": "healthy" if db_ok else "degraded",
            "service": "ssa-alj-mcp",
            "db_ok": db_ok,
            "db_path": str(settings.ssa_alj_db_path),
        }
        if db_error and not db_ok:
            body["db_error"] = db_error
        # 200 even when degraded so platforms that only check HTTP status still see the app up;
        # operators should read db_ok.
        return JSONResponse(body)

    @mcp.custom_route("/version", methods=["GET"])
    async def version(request: Request) -> JSONResponse:
        return JSONResponse({"version": __version__})

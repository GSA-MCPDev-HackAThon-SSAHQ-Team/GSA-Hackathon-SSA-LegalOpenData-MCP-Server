"""Server configuration, loaded from environment variables or a `.env` file.

Every field can be overridden by an environment variable of the same name
(upper- or lower-case). Copy `.env.example` to `.env` for local development.
"""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# src/ssa_alj_mcp/config.py -> repo root is three levels up.
PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # -- Transport -------------------------------------------------------------
    # "stdio"           local subprocess (Goose, Claude Desktop, MCP Inspector)
    # "streamable-http" remote HTTP server. app.py also switches to HTTP automatically when a
    #                   platform injects PORT (Render, Code Engine, Databricks Apps).
    mcp_transport: str = "stdio"
    mcp_host: str = "127.0.0.1"
    mcp_port: int = 8000

    # -- Data ------------------------------------------------------------------
    # SQLite file produced by data/scripts/load_ssa_alj.py. Opened read-only.
    ssa_alj_db_path: Path = PROJECT_ROOT / "data" / "ssa_alj.sqlite"

    # Hard cap for page sizes returned by list-style tools.
    max_page_size: int = 100


settings = Settings()

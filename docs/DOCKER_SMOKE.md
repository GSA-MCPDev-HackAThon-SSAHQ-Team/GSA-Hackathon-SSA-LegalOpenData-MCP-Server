# Docker smoke test

The image serves streamable-HTTP MCP at `/mcp` with `/health` and `/version`. It expects
`data/ssa_alj.sqlite` in the build context (git-ignored; must exist on disk when you build).

## Build and run

```bash
# from repo root, with data/ssa_alj.sqlite present (~39 MB)
docker build -t ssa-alj-mcp:local .
docker run --rm -p 8080:8080 ssa-alj-mcp:local
```

## Checks

```bash
curl -s http://127.0.0.1:8080/health
# expect: "status":"healthy","db_ok":true

curl -s http://127.0.0.1:8080/version
# expect: "version":"0.1.0"

uv run python scripts/mcp_client_demo.py --legacy --url http://127.0.0.1:8080/mcp
# expect: tools/list -> 13 tools, tools/call results
```

## Notes

- `.dockerignore` excludes `data/raw/` (~320 MB), `.venv`, tests, and eval.
- Container hosts (e.g. Render): set health check path to `/health`; public MCP URL is `https://<host>/mcp`.
- Image size is on the order of a few hundred MB (slim Python + deps + 39 MB SQLite) — fine for Render.

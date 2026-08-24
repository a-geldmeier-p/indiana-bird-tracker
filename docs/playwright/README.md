# Playwright MCP adapter contract

The repository does not speak MCP directly. A separately deployed, authenticated adapter receives this JSON request:

```json
{"base_url":"http://127.0.0.1:PORT","workflows":["catalog","record_sighting","my_sightings","dashboard"],"artifact_dir":"docs/playwright/artifacts","commit_sha":"CURRENT_COMMIT"}
```

It must use only synthetic data and temporary DuckDB, upload, and reference-photo folders. On success it writes a `result.json` manifest plus one video and poster per recorded workflow. Each result includes the workflow ID, commit SHA, browser version, and relative artifact paths. If the adapter is unavailable, it must exit nonzero and leave every Markdown video placeholder unchanged.

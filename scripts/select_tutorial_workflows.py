"""Select new, changed, source-affected, or artifact-missing tutorials."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

from tutorial_workflows import fingerprint, load_contract, load_manifest, source_matches


def select_workflows(
    workflows: dict[str, dict], manifest: dict, shared_paths: list[str], changed_paths: set[str]
) -> list[dict]:
    application_paths = {path for path in changed_paths if path.startswith(("R/", "inst/app/"))}
    covered_paths = {
        path for path in application_paths
        if source_matches(path, shared_paths) or any(
            source_matches(path, workflow["source_paths"]) for workflow in workflows.values()
        )
    }
    # A newly added app file cannot silently leave an existing tutorial stale.
    unmapped_paths = application_paths - covered_paths
    recorded = {row["id"]: row for row in manifest.get("workflows", [])}
    selected = []
    for workflow_id, workflow in workflows.items():
        current = fingerprint(workflow_id, workflow)
        previous = recorded.get(workflow_id, {})
        media = [previous.get("video"), previous.get("poster")]
        reasons = []
        if not previous:
            reasons.append("new")
        if previous.get("workflow_fingerprint") != current:
            reasons.append("changed")
        if any(source_matches(path, shared_paths + workflow["source_paths"]) for path in application_paths):
            reasons.append("source-changed")
        elif unmapped_paths:
            reasons.append("unmapped-source-changed")
        if not all(value and Path(value).is_file() and Path(value).stat().st_size for value in media):
            reasons.append("missing-artifact")
        if reasons:
            selected.append({"id": workflow_id, "fingerprint": current, "reasons": reasons})
    return selected


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, default=Path(".github/agents/workflow-contract.yml"))
    parser.add_argument("--manifest", type=Path, default=Path("docs/playwright/manifest.yml"))
    parser.add_argument("--changed-paths", type=Path, help="One PR-changed repository path per line")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    workflows = load_contract(args.contract)
    contract_data = yaml.safe_load(args.contract.read_text(encoding="utf-8")) or {}
    shared_paths = contract_data.get("shared_source_paths", [])
    changed_paths = (
        {line.strip().replace("\\", "/") for line in args.changed_paths.read_text(encoding="utf-8").splitlines() if line.strip()}
        if args.changed_paths else set()
    )
    manifest = load_manifest(args.manifest)
    selected = select_workflows(workflows, manifest, shared_paths, changed_paths)

    args.output.write_text(json.dumps({"workflows": selected}, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"count": len(selected), "ids": [row["id"] for row in selected]}))


if __name__ == "__main__":
    main()

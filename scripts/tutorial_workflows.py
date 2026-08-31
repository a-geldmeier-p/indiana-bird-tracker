"""Shared parsing and fingerprinting for tutorial workflow contracts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import yaml


def load_contract(path: Path) -> dict[str, dict]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    workflows = data.get("workflows")
    if not isinstance(workflows, dict) or not workflows:
        raise ValueError("Workflow contract must contain a non-empty workflows mapping.")
    for workflow_id, workflow in workflows.items():
        if not isinstance(workflow_id, str) or not workflow_id.replace("_", "").isalnum():
            raise ValueError(f"Invalid workflow id: {workflow_id!r}")
        if not isinstance(workflow, dict):
            raise ValueError(f"Workflow {workflow_id} must be a mapping.")
        for field in ("guide_heading", "stable_ids", "script"):
            if not workflow.get(field):
                raise ValueError(f"Workflow {workflow_id} is missing {field}.")
    return workflows


def fingerprint(workflow_id: str, workflow: dict) -> str:
    material = {
        "id": workflow_id,
        "guide_heading": workflow["guide_heading"],
        "stable_ids": workflow["stable_ids"],
        "script": workflow["script"].replace("\r\n", "\n").strip(),
    }
    encoded = json.dumps(material, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def load_manifest(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}

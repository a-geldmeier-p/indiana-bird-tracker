"""Publish verified Playwright recordings into the user guide."""

from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path


WORKFLOWS = (
    (
        "catalog",
        "Catalog browsing and filtering",
        "<!-- VIDEO PLACEHOLDER: Catalog browsing and filtering (Playwright recording) -->",
    ),
    (
        "record_sighting",
        "Recording a sighting",
        "<!-- VIDEO PLACEHOLDER: Recording a sighting with a photo (Playwright recording) -->",
    ),
    (
        "my_sightings",
        "Filtering and reviewing My Sightings",
        "<!-- VIDEO PLACEHOLDER: Filtering and reviewing My Sightings (Playwright recording) -->",
    ),
    (
        "dashboard",
        "Dashboard overview",
        "<!-- VIDEO PLACEHOLDER: Dashboard overview (Playwright recording) -->",
    ),
)


def find_artifact(source_dir: Path, name: str) -> Path:
    matches = list(source_dir.rglob(name))
    if len(matches) != 1:
        raise SystemExit(
            f"Expected exactly one MCP artifact named {name}, found {len(matches)}: {matches}"
        )
    return matches[0]


def video_block(workflow_id: str, title: str) -> str:
    path = f"docs/playwright/artifacts/{workflow_id}.webm"
    poster = f"docs/playwright/artifacts/{workflow_id}.png"
    return (
        f'<figure id="tutorial-{workflow_id}">\n'
        f'  <video controls preload="metadata" poster="{poster}" aria-label="{title} tutorial">\n'
        f'    <source src="{path}" type="video/webm">\n'
        "    Your browser does not support embedded WebM video.\n"
        "  </video>\n"
        f"  <figcaption>{title} tutorial.</figcaption>\n"
        "</figure>"
    )


def add_recording_to_manifest(
    manifest: str, workflow_id: str, video: Path, poster: Path, commit_sha: str
) -> str:
    """Keep contract metadata and add recording metadata to one workflow entry."""
    pattern = re.compile(
        rf"^  - id: {re.escape(workflow_id)}\s*$.*?(?=^  - id:|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(manifest)
    if not match:
        raise SystemExit(f"Manifest is missing workflow: {workflow_id}")

    retained = [
        line
        for line in match.group(0).rstrip().splitlines()
        if not re.match(r"^    (video|poster|commit_sha):", line)
    ]
    retained.extend(
        [
            f"    video: {video.as_posix()}",
            f"    poster: {poster.as_posix()}",
            f"    commit_sha: {commit_sha}",
        ]
    )
    return manifest[: match.start()] + "\n".join(retained) + "\n" + manifest[match.end() :]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--artifact-dir", type=Path, default=Path("docs/playwright/artifacts"))
    parser.add_argument("--guide", type=Path, default=Path("USER_GUIDE.md"))
    parser.add_argument("--manifest", type=Path, default=Path("docs/playwright/manifest.yml"))
    parser.add_argument("--commit-sha", required=True)
    args = parser.parse_args()

    args.artifact_dir.mkdir(parents=True, exist_ok=True)
    keep_file = args.artifact_dir / ".gitkeep"
    if keep_file.exists():
        keep_file.unlink()
    guide = args.guide.read_text(encoding="utf-8")
    results = []
    manifest = args.manifest.read_text(encoding="utf-8")

    for workflow_id, title, placeholder in WORKFLOWS:
        source_video = find_artifact(args.source_dir, f"{workflow_id}.webm")
        source_poster = find_artifact(args.source_dir, f"{workflow_id}.png")
        destination = args.artifact_dir / f"{workflow_id}.webm"
        poster_destination = args.artifact_dir / f"{workflow_id}.png"
        shutil.copy2(source_video, destination)
        shutil.copy2(source_poster, poster_destination)

        block = video_block(workflow_id, title)
        existing_start = f'<figure id="tutorial-{workflow_id}">'
        if placeholder in guide:
            guide = guide.replace(placeholder, block, 1)
        elif existing_start not in guide:
            raise SystemExit(
                f"USER_GUIDE.md contains neither the placeholder nor video block for {workflow_id}."
            )

        relative = destination.as_posix()
        results.append(
            {
                "workflow": workflow_id,
                "commit_sha": args.commit_sha,
                "video": relative,
                "poster": poster_destination.as_posix(),
            }
        )
        manifest = add_recording_to_manifest(
            manifest, workflow_id, destination, poster_destination, args.commit_sha
        )

    args.guide.write_text(guide, encoding="utf-8")
    args.manifest.write_text(manifest.rstrip() + "\n", encoding="utf-8")
    (args.artifact_dir / "result.json").write_text(
        json.dumps({"commit_sha": args.commit_sha, "workflows": results}, indent=2) + "\n",
        encoding="utf-8",
    )

    print("Published four verified Playwright MCP videos and posters into USER_GUIDE.md.")


if __name__ == "__main__":
    main()

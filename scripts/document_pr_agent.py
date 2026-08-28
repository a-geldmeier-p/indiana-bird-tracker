"""Ask the OpenAI API for an allow-listed documentation patch for one PR."""

from __future__ import annotations

import argparse
import difflib
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path


def response_text(payload: dict) -> str:
    """Extract text from a Responses API JSON response."""
    parts = []
    for item in payload.get("output", []):
        for content in item.get("content", []):
            if content.get("type") == "output_text":
                parts.append(content.get("text", ""))
    return "\n".join(parts).strip()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def request_patch(api_key: str, prompt: str) -> str:
    request_body = json.dumps(
        {"model": "gpt-5.6-luna", "input": prompt, "max_output_tokens": 12000}
    ).encode("utf-8")
    request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=request_body,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            patch = response_text(json.load(response))
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise SystemExit(f"OpenAI API request failed ({error.code}): {detail}") from error
    return normalize_patch(patch)


def normalize_patch(patch: str) -> str:
    """Remove model prose/fences while preserving a complete git patch."""
    patch = patch.replace("\\r\\n", "\\n").strip()
    if patch.startswith("*** Begin Patch"):
        patch = patch[len("*** Begin Patch") :].strip()
        if patch.endswith("*** End Patch"):
            patch = patch[: -len("*** End Patch")].rstrip()
    if "```" in patch:
        blocks = patch.split("```")
        fenced = [block for block in blocks if "diff --git " in block]
        if fenced:
            patch = fenced[0]
    marker = patch.find("diff --git ")
    if marker >= 0:
        patch = patch[marker:]
    if patch.endswith("```"):
        patch = patch[:-3].rstrip()
    return patch.strip()


def contents_to_patch(files: dict[str, str]) -> str:
    chunks = []
    for name, new_text in files.items():
        path = Path(name)
        old_text = path.read_text(encoding="utf-8") if path.exists() else ""
        if old_text == new_text:
            continue
        diff = difflib.unified_diff(
            old_text.splitlines(True),
            new_text.splitlines(True),
            fromfile=f"a/{name}" if path.exists() else "/dev/null",
            tofile=f"b/{name}",
            lineterm="\n",
        )
        body = "".join(diff)
        if body:
            chunks.append(f"diff --git a/{name} b/{name}\n{body}")
    return "\n".join(chunks)


def preserves_video_placeholders(patch: str) -> bool:
    """Keep pending placeholders and existing verified video embeds."""
    protected = ("VIDEO PLACEHOLDER:", 'id="tutorial-', "docs/playwright/artifacts/")
    return not any(
        line.startswith("-") and any(marker in line for marker in protected)
        for line in patch.splitlines()
    )


def request_file_contents(api_key: str, repository: str, pr_number: str, context: str, diff: str) -> str:
    prompt = f"""You are documenting {repository}, PR #{pr_number}.
Return ONLY a JSON object with this exact shape: {{\"files\": {{\"README.md\": \"full text\", \"NEWS.md\": \"full text\", \"USER_GUIDE.md\": \"full text\", \"WORKFLOW_INVENTORY.md\": \"full text\"}}}}.
Include only files that need truthful updates. The values must be complete replacement file contents, not diffs.
Also include complete updated Roxygen source files or tests only when required by the PR, using their repository paths as keys.
Do not invent features, links, videos, screenshots, or test results.
Preserve all four existing `VIDEO PLACEHOLDER:` comments in USER_GUIDE.md exactly unless
`docs/playwright/artifacts/result.json` already contains verified real artifact paths.
PR diff:\n{diff}\nCurrent files:\n{context}"""
    raw = request_patch(api_key, prompt)
    start = raw.find("{")
    end = raw.rfind("}")
    if start < 0 or end <= start:
        raise SystemExit("Documentation agent did not return structured file contents.")
    try:
        payload = json.loads(raw[start : end + 1])
        files = payload.get("files", {})
        if not isinstance(files, dict):
            raise ValueError("files must be an object")
        return contents_to_patch({str(k): str(v) for k, v in files.items()})
    except (json.JSONDecodeError, ValueError) as error:
        raise SystemExit(f"Documentation agent returned invalid structured content: {error}") from error


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", required=True)
    parser.add_argument("--pr-number", required=True)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--diff", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    api_key = os.environ.get("OPENAI_API_KEY", "").strip().strip('"').strip("'")
    if not api_key:
        raise SystemExit("OPENAI_API_KEY is required.")

    context_paths = [
        Path("README.md"),
        Path("NEWS.md"),
        Path("USER_GUIDE.md"),
        Path("WORKFLOW_INVENTORY.md"),
        Path("docs/agent-prompts/document-pr.md"),
    ]
    context = "\n\n".join(
        f"--- {path} ---\n{read_text(path)}"
        for path in context_paths
        if path.exists()
    )
    prompt = f"""You are the bounded documentation agent for {args.repository}, PR #{args.pr_number}.

Return ONLY a valid unified git patch. Do not use Markdown fences or explanations.
The patch must modify only paths allowed by this policy:
--- policy ---
{read_text(args.policy)}
--- end policy ---

Rules:
- You MUST return a valid unified git patch, and nothing else.
- You may edit only these paths:
  1. README.md — update setup, usage, or behavior notes affected by this PR.
  2. NEWS.md — add one concise entry under the current development heading.
  3. USER_GUIDE.md — update the relevant user-facing workflow instructions.
  4. WORKFLOW_INVENTORY.md — update workflow IDs/steps only when this PR changes them.
- 5. Roxygen comments in R source files and the generated man/ files.
  6. Focused tests under tests/testthat/ that cover behavior changed by this PR.
- Do not edit application behavior, dependencies, CI workflows, policy files,
  or Playwright files. Do not add unrelated tests or documentation.
- Make only changes supported by the PR diff. Do not invent features, links, videos,
  screenshots, or test results. Preserve existing Markdown structure and headings.
- Treat deleted Roxygen fields, focused tests, README capabilities, NEWS entries,
  user-guide steps, and workflow-inventory steps as stale-documentation gaps when
  the corresponding implementation still exists. Restore or replace that coverage.
- Preserve every existing `VIDEO PLACEHOLDER:` comment and published tutorial
  `<figure>`/`docs/playwright/artifacts/` reference in USER_GUIDE.md exactly.
  The deterministic Playwright publisher, not the model, replaces placeholders.
- If a file does not need a truthful update, leave it unchanged. If none need updates,
  return an empty response.
- Every changed file must have a complete `diff --git` header and valid hunk counts.

--- PR diff ---
{read_text(args.diff)}
--- end PR diff ---

--- current documentation context ---
{context}
--- end context ---
"""
    patch = request_patch(api_key, prompt)
    if patch:
        check = subprocess.run(["git", "apply", "--check"], input=patch, text=True, capture_output=True)
        if check.returncode:
            repair_prompt = f"""Repair this proposed unified git patch so `git apply --check` accepts it.
Return ONLY a standard git unified patch beginning with `diff --git`.
Do not use `*** Begin Patch`, `*** End Patch`, Markdown fences, or prose.
Include complete `---`, `+++`, and valid hunk line counts for every changed file.
Git error:
{check.stderr}
Patch:
{patch}
"""
            patch = request_patch(api_key, repair_prompt)
            repaired = subprocess.run(["git", "apply", "--check"], input=patch, text=True, capture_output=True)
            if repaired.returncode:
                patch = request_file_contents(
                    api_key, args.repository, args.pr_number, context, read_text(args.diff)
                )
                rebuilt = subprocess.run(
                    ["git", "apply", "--check"], input=patch, text=True, capture_output=True
                )
                if rebuilt.returncode:
                    raise SystemExit(
                        "Documentation agent could not produce a valid patch after "
                        f"structured retry:\n{rebuilt.stderr}"
                    )
        if not preserves_video_placeholders(patch):
            patch = request_file_contents(
                api_key, args.repository, args.pr_number, context, read_text(args.diff)
            )
            rebuilt = subprocess.run(
                ["git", "apply", "--check"], input=patch, text=True, capture_output=True
            )
            if rebuilt.returncode or not preserves_video_placeholders(patch):
                raise SystemExit(
                    "Documentation agent attempted to remove protected video "
                    "placeholders or published artifact links."
                )
    args.output.write_text(patch + ("\n" if patch else ""), encoding="utf-8")


if __name__ == "__main__":
    main()

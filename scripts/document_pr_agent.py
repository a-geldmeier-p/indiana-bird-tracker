"""Ask the OpenAI API for an allow-listed documentation patch for one PR."""

from __future__ import annotations

import argparse
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
Return ONLY the corrected patch, with valid diff headers and hunk line counts.
Git error:
{check.stderr}
Patch:
{patch}
"""
            patch = request_patch(api_key, repair_prompt)
            repaired = subprocess.run(["git", "apply", "--check"], input=patch, text=True, capture_output=True)
            if repaired.returncode:
                # Never let an untrusted model response break the PR.  Returning an
                # empty patch lets deterministic checks continue; a later run can
                # retry documentation generation with the same PR diff.
                print(
                    "Documentation agent patch was invalid; skipping this run. "
                    f"git apply error: {repaired.stderr.strip()}",
                    file=sys.stderr,
                )
                patch = ""
    args.output.write_text(patch + ("\n" if patch else ""), encoding="utf-8")


if __name__ == "__main__":
    main()

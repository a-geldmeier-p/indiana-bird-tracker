"""Record only selected new or stale workflows through Playwright MCP."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from tutorial_workflows import load_contract


async def call(session: ClientSession, tool: str, arguments: dict):
    result = await session.call_tool(tool, arguments)
    if result.isError:
        raise RuntimeError(f"Playwright MCP tool {tool} failed: {result.content}")
    return result


def result_text(result) -> str:
    return " ".join(block.text for block in result.content if getattr(block, "text", None))


async def wait_for_artifact(
    output_dir: Path, name: str, stop_response: str = "", timeout: float = 15
) -> Path:
    deadline = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < deadline:
        matches = list(output_dir.rglob(name))
        if len(matches) == 1 and matches[0].stat().st_size > 0:
            return matches[0]
        await asyncio.sleep(0.5)
    files = sorted(
        str(path.relative_to(output_dir))
        for path in output_dir.rglob("*")
        if path.is_file()
    )
    raise RuntimeError(
        f"Expected one non-empty MCP artifact named {name}. "
        f"Files present: {files}. MCP stop response: {stop_response!r}"
    )


def selected_ids(path: Path) -> list[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return [row["id"] for row in data.get("workflows", [])]


async def record(
    mcp_url: str,
    output_dir: Path,
    base_url: str,
    contract_path: Path,
    selection_path: Path,
) -> None:
    if base_url != "http://127.0.0.1:3838":
        raise ValueError("The MCP tutorial recorder is restricted to the temporary local Shiny app.")

    workflows = load_contract(contract_path)
    selection = selected_ids(selection_path)
    unknown = sorted(set(selection) - set(workflows))
    if unknown:
        raise ValueError(f"Selection contains workflows absent from the contract: {unknown}")
    if not selection:
        print("No new or stale tutorial workflows require recording.")
        return

    async with streamablehttp_client(mcp_url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            available = {tool.name for tool in (await session.list_tools()).tools}
            required = {
                "browser_navigate",
                "browser_start_video",
                "browser_stop_video",
                "browser_video_show_actions",
                "browser_run_code_unsafe",
                "browser_take_screenshot",
            }
            missing = required - available
            if missing:
                raise RuntimeError(f"Playwright MCP server lacks required tools: {sorted(missing)}")

            for workflow_id in selection:
                # The page must exist before MCP can enable cursor/action indicators.
                await call(session, "browser_navigate", {"url": base_url})
                await call(
                    session,
                    "browser_start_video",
                    {"filename": f"{workflow_id}.webm", "size": {"width": 1280, "height": 800}},
                )
                try:
                    await call(
                        session,
                        "browser_video_show_actions",
                        {"duration": 650, "position": "top-right", "cursor": "pointer"},
                    )
                    await call(
                        session,
                        "browser_run_code_unsafe",
                        {"code": workflows[workflow_id]["script"]},
                    )
                    await call(
                        session,
                        "browser_take_screenshot",
                        {"filename": f"{workflow_id}.png", "fullPage": False, "scale": "css"},
                    )
                finally:
                    stop_result = await call(session, "browser_stop_video", {})
                stop_response = result_text(stop_result)
                await wait_for_artifact(output_dir, f"{workflow_id}.webm", stop_response)
                await wait_for_artifact(output_dir, f"{workflow_id}.png")

    print(f"Recorded {len(selection)} verified tutorial workflow(s) through Playwright MCP.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mcp-url", required=True)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--contract", type=Path, default=Path(".github/agents/workflow-contract.yml"))
    parser.add_argument("--selection", type=Path, required=True)
    args = parser.parse_args()
    asyncio.run(record(args.mcp_url, args.output_dir, args.base_url, args.contract, args.selection))


if __name__ == "__main__":
    main()

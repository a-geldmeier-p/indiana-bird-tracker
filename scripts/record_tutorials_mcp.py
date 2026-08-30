"""Record the documented Shiny workflows through a Playwright MCP server.

This is deliberately a deterministic MCP client, not an LLM browser agent.  It
uses only synthetic data created by ``seed_playwright_demo.R`` and fails unless
the MCP server writes a real WebM video and PNG poster for every workflow.
"""

from __future__ import annotations

import argparse

import asyncio
from pathlib import Path

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


WORKFLOWS = {
    "catalog": r"""
async (page) => {
  const pause = () => page.waitForTimeout(700);
  await page.goto('http://127.0.0.1:3838/');
  await page.getByRole('link', { name: 'Species catalog' }).click();
  await page.getByLabel('Search common or scientific name').fill('cardinal');
  await page.getByRole('button', { name: 'Filter catalog' }).click();
  await page.getByRole('cell', { name: 'Northern Cardinal' }).waitFor();
  await pause();
  await page.mouse.wheel(0, 700);
  await pause();
  await page.getByRole('button', { name: 'Reset filters' }).click();
  const group = page.locator('#species-bird_group-selectized');
  await group.fill('Ducks, Geese, and Swans');
  await group.press('Enter');
  await page.getByRole('button', { name: 'Filter catalog' }).click();
  await page.mouse.wheel(0, 700);
  await pause();
  await page.getByRole('button', { name: 'Reset filters' }).click();
  const status = page.locator('#species-status_note-selectized');
  await status.fill('Indiana State Endangered');
  await status.press('Enter');
  await page.getByRole('button', { name: 'Filter catalog' }).click();
  await page.mouse.wheel(0, 700);
  await pause();
  await page.getByRole('button', { name: 'Reset filters' }).click();
}
""",
    "record_sighting": r"""
async (page) => {
  const pause = () => page.waitForTimeout(700);
  await page.goto('http://127.0.0.1:3838/');
  await page.getByRole('link', { name: 'Record sighting' }).click();
  const species = page.locator('#record-species_code-selectized');
  await species.click();
  await page.locator('.selectize-dropdown .option').first().waitFor();
  await page.locator('.selectize-dropdown .option').first().click();
  await page.getByLabel('Observation time').fill('12:00');
  await page.locator('#record-observation_date input').fill('2026-08-20');
  await page.getByLabel('Location').fill('Eagle Creek Park');
  await page.getByLabel('Indiana county').fill('Marion');
  await page.getByLabel('Notes (optional)').fill('Playwright MCP tutorial sighting');
  await page.getByLabel('Or photo path or URL (optional)').fill('https://example.com/indiana-bird.jpg');
  await pause();
  await page.getByRole('button', { name: 'Save sighting' }).click();
  await page.getByRole('status').getByText('Saved sighting').waitFor();
  await pause();
}
""",
    "my_sightings": r"""
async (page) => {
  const pause = () => page.waitForTimeout(700);
  await page.goto('http://127.0.0.1:3838/');
  await page.getByRole('link', { name: 'My sightings' }).click();
  await page.getByRole('heading', { name: 'Filter my sightings' }).waitFor();
  await page.getByLabel('Filter by observation date').check();
  const dateRange = page.locator('#sightings-date_range input');
  await dateRange.first().fill('2026-08-01');
  await dateRange.last().fill('2026-08-26');
  await page.getByRole('button', { name: 'Filter sightings' }).click();
  await page.getByRole('cell', { name: /Playwright demo:/ }).first().waitFor();
  await pause();
  await page.mouse.wheel(0, 1200);
  await page.getByRole('heading', { name: 'Sighting photos' }).waitFor();
  await page.locator('img.sighting-photo').first().waitFor();
  await pause();
  await page.getByRole('button', { name: 'Reset filters' }).click();
}
""",
    "dashboard": r"""
async (page) => {
  const pause = () => page.waitForTimeout(700);
  await page.goto('http://127.0.0.1:3838/');
  await page.getByRole('link', { name: 'Dashboard' }).click();
  await page.getByText('Total sightings').waitFor();
  await page.getByText('Distinct species').waitFor();
  await page.locator('#dashboard-total_sightings').filter({ hasNotText: '0' }).waitFor();
  await page.getByRole('cell', { name: /Eagle Creek Park|Fort Harrison State Park|White River State Park|Monon Trail/ }).first().waitFor();
  await page.mouse.wheel(0, 700);
  await pause();
}
""",
}


async def call(session: ClientSession, tool: str, arguments: dict) -> None:
    result = await session.call_tool(tool, arguments)
    if result.isError:
        raise RuntimeError(f"Playwright MCP tool {tool} failed: {result.content}")


def require_artifact(output_dir: Path, name: str) -> None:
    matches = list(output_dir.rglob(name))
    if len(matches) != 1:
        raise RuntimeError(
            f"Expected exactly one MCP artifact named {name}; found {matches}."
        )


async def record(mcp_url: str, output_dir: Path, base_url: str) -> None:
    if base_url != "http://127.0.0.1:3838":
        raise ValueError("The MCP tutorial recorder is restricted to the temporary local Shiny app.")

    async with streamablehttp_client(mcp_url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            available = {tool.name for tool in (await session.list_tools()).tools}
            required = {
                "browser_start_video",
                "browser_stop_video",
                "browser_run_code_unsafe",
                "browser_take_screenshot",
            }
            missing = required - available
            if missing:
                raise RuntimeError(f"Playwright MCP server lacks required tools: {sorted(missing)}")

            for workflow_id, code in WORKFLOWS.items():
                await call(
                    session,
                    "browser_start_video",
                    {"filename": f"{workflow_id}.webm", "size": {"width": 1280, "height": 800}},
                )
                try:
                    await call(session, "browser_run_code_unsafe", {"code": code})
                    await call(
                        session,
                        "browser_take_screenshot",
                        {"filename": f"{workflow_id}.png", "fullPage": False, "scale": "css"},
                    )
                finally:
                    await call(session, "browser_stop_video", {})
                await asyncio.sleep(1)
                require_artifact(output_dir, f"{workflow_id}.webm")
                require_artifact(output_dir, f"{workflow_id}.png")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mcp-url", required=True)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    asyncio.run(record(args.mcp_url, args.output_dir, args.base_url))
    print("Recorded four verified tutorial videos through Playwright MCP.")


if __name__ == "__main__":
    main()

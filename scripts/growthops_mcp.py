"""Official-SDK stdio adapter; no legacy scheduler/publisher imports."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from mcp.server import MCPServer
from src.growthops import GrowthStore, validate_presenter

mcp = MCPServer("contentops-growth")


def store():
    return GrowthStore(os.environ.get("CONTENTOPS_PROJECT_ROOT", str(ROOT)))


@mcp.tool()
def growth_status() -> dict:
    """Inspect queued work, research cost and observed legacy STOP files; never start jobs."""
    return store().status()


@mcp.tool()
def growth_skills() -> list[dict]:
    """List project-installed skills and their actual content hashes."""
    return store().skills()


@mcp.tool()
def queue_growth_task(lane: str, kind: str, idempotency_key: str, payload: dict) -> dict:
    """Prepare a durable bounded campaign/prospecting task; this does not execute or publish it."""
    return store().enqueue(lane, kind, idempotency_key, payload)


@mcp.tool()
def growth_tasks(lane: str = "") -> list[dict]:
    """List saved jobs and actual task status."""
    return store().jobs(lane or None)


@mcp.tool()
def complete_growth_task(job_id: str, result: dict, status: str = "completed") -> dict:
    """Record a task result and its real evidence, or mark it blocked/failed."""
    return store().finish(job_id, result, status)


@mcp.tool()
def save_business_research(lead: dict) -> dict:
    """Save sourced first-party business observations; never certify outreach consent or send."""
    return store().save_prospect(lead)


@mcp.tool()
def list_business_research() -> list[dict]:
    """List saved prospects and their evidence; suppression remains persistent."""
    return store().prospects()


@mcp.tool()
def check_presenter(manifest: dict, approved: dict) -> dict:
    """Compare the series identity/voice manifest and synthetic disclosure."""
    errors = validate_presenter(manifest, approved)
    return {"passed": not errors, "errors": errors}


@mcp.tool()
def prepare_distribution(campaign_id: str, source_hash: str, destinations: list[dict]) -> dict:
    """Prepare distinct verified personal/company destinations, without publishing."""
    return store().distribution_plan(campaign_id, source_hash, destinations)


@mcp.tool()
def reserve_research_cost(job_id: str, quote_usd: float) -> dict:
    """Reserve against an existing verified research budget; this does not call a paid provider."""
    return store().reserve_research(job_id, quote_usd)


@mcp.tool()
def record_research_cost(job_id: str, actual_usd: float, receipt: str) -> dict:
    """Record actual provider cost including overages; never hide an over-quote charge."""
    return store().settle_research(job_id, actual_usd, receipt)


if __name__ == "__main__":
    mcp.run(transport="stdio")

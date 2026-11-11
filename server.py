#!/usr/bin/env python3
"""
meta-ads-sentinel-mcp — Model Context Protocol (MCP) Server for Meta Marketing API.
Enables Claude Desktop & Claude Code to inspect campaigns, monitor adset CPL/frequency,
and autonomously pause fatigued ads or adjust daily budgets.
"""

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional, Tuple

try:
    from mcp.server.mcpserver import MCPServer
    app: Any = MCPServer("meta-ads-sentinel-mcp")
except ImportError:
    class DummyMCPServer:
        """Fallback lightweight mock when mcp package is not installed."""
        def __init__(self, name: str = ""):
            self.name = name

        def tool(self):
            def decorator(fn):
                return fn
            return decorator

        def run(self, **kwargs):
            raise RuntimeError("mcp package is not installed. Install with 'pip install mcp'.")

    app = DummyMCPServer("meta-ads-sentinel-mcp")

VALID_INSIGHT_LEVELS = {"account", "campaign", "adset", "ad"}


def get_meta_config() -> Tuple[str, str, str]:
    access_token = os.environ.get("META_ACCESS_TOKEN", "")
    ad_account_id = os.environ.get("META_AD_ACCOUNT_ID", "")
    api_version = os.environ.get("META_API_VERSION", "v21.0")
    if not access_token or not ad_account_id:
        raise ValueError("Missing META_ACCESS_TOKEN or META_AD_ACCOUNT_ID environment variables.")
    if not ad_account_id.startswith("act_"):
        ad_account_id = f"act_{ad_account_id}"
    return access_token, ad_account_id, api_version


def _parse_http_error(exc: urllib.error.HTTPError) -> str:
    raw = exc.read().decode("utf-8", errors="ignore")
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict) and "error" in parsed:
            err_obj = parsed["error"]
            if isinstance(err_obj, dict):
                msg = err_obj.get("message") or raw
                code = err_obj.get("code")
                return f"HTTP {exc.code} (Meta code {code}): {msg}" if code else f"HTTP {exc.code}: {msg}"
        return f"HTTP {exc.code}: {raw}"
    except Exception:
        return f"HTTP {exc.code}: {raw or exc.reason}"


def meta_api_request(endpoint: str, params: Optional[Dict[str, Any]] = None, method: str = "GET") -> Dict[str, Any]:
    access_token, _, api_version = get_meta_config()
    query_params = dict(params or {})
    query_params["access_token"] = access_token
    query_str = urllib.parse.urlencode(query_params)

    url = f"https://graph.facebook.com/{api_version}/{endpoint}?{query_str}"
    req = urllib.request.Request(url, headers={"User-Agent": "Claude-Meta-Sentinel"}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return {"error": _parse_http_error(e)}
    except Exception as e:
        return {"error": str(e)}


def _validate_adset_id(adset_id: str) -> Optional[str]:
    cleaned = (adset_id or "").strip()
    if not cleaned or not cleaned.isdigit():
        return None
    return cleaned


def _update_adset(adset_id: str, fields: Dict[str, Any], success_msg: str, action_label: str) -> str:
    cleaned_id = _validate_adset_id(adset_id)
    if not cleaned_id:
        return f"Failed to {action_label}: adset_id must be a non-empty numeric ID."

    token, _, api_version = get_meta_config()
    url = f"https://graph.facebook.com/{api_version}/{cleaned_id}"
    payload_dict = dict(fields)
    payload_dict["access_token"] = token
    payload = urllib.parse.urlencode(payload_dict).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"User-Agent": "Claude-Meta-Sentinel"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("success"):
                return success_msg
            return f"Update returned: {data}"
    except urllib.error.HTTPError as e:
        return f"Failed to {action_label}: {_parse_http_error(e)}"
    except Exception as e:
        return f"Failed to {action_label}: {e}"


@app.tool()
def get_campaign_insights(date_preset: str = "last_7d", level: str = "campaign") -> str:
    """
    Fetch aggregate spend, impressions, clicks, leads, and CPA across active campaigns.

    Args:
        date_preset: Time window (e.g. 'today', 'yesterday', 'last_7d', 'last_30d').
        level: Aggregation level ('account', 'campaign', 'adset', 'ad'). Defaults to 'campaign'.
    """
    if level not in VALID_INSIGHT_LEVELS:
        return f"Invalid insight level '{level}'. Must be one of: {sorted(VALID_INSIGHT_LEVELS)}."
    _, ad_account_id, _ = get_meta_config()
    fields = "campaign_name,spend,impressions,clicks,cpc,cpm,actions,cost_per_action_type"
    res = meta_api_request(
        f"{ad_account_id}/insights",
        {"fields": fields, "date_preset": date_preset, "level": level},
    )
    if "error" in res:
        return f"Meta API Error: {res['error']}"
    data = res.get("data", [])
    if not data:
        return f"No ad activity recorded for preset '{date_preset}'."
    return json.dumps(data, indent=2)


@app.tool()
def list_adsets_health() -> str:
    """
    Inspect active adsets for frequency fatigue (>3.5x) or high cost-per-lead (CPL).
    """
    _, ad_account_id, _ = get_meta_config()
    fields = "id,name,status,daily_budget,insights{frequency,spend,actions,cost_per_action_type}"
    res = meta_api_request(f"{ad_account_id}/adsets", {"fields": fields, "effective_status": "['ACTIVE']"})
    if "error" in res:
        return f"Meta API Error: {res['error']}"
    return json.dumps(res.get("data", []), indent=2)


@app.tool()
def pause_adset(adset_id: str) -> str:
    """
    Emergency pause an underperforming or fatigued Meta Adset.

    Args:
        adset_id: The numeric ID of the adset to pause.
    """
    return _update_adset(
        adset_id,
        {"status": "PAUSED"},
        f"Successfully PAUSED adset ID: {(adset_id or '').strip()}.",
        "pause adset",
    )


@app.tool()
def activate_adset(adset_id: str) -> str:
    """
    Activate or resume a paused Meta Adset.

    Args:
        adset_id: The numeric ID of the adset to resume.
    """
    return _update_adset(
        adset_id,
        {"status": "ACTIVE"},
        f"Successfully ACTIVATED adset ID: {(adset_id or '').strip()}.",
        "activate adset",
    )


@app.tool()
def update_adset_budget(adset_id: str, daily_budget_cents: int) -> str:
    """
    Adjust the daily budget for a Meta Adset.

    Args:
        adset_id: The numeric ID of the adset to update.
        daily_budget_cents: New daily budget in account currency subunits (e.g. cents, or IDR).
    """
    if daily_budget_cents <= 0:
        return "Failed to update adset budget: daily_budget_cents must be a positive integer."

    return _update_adset(
        adset_id,
        {"daily_budget": daily_budget_cents},
        f"Successfully updated daily budget for adset ID {(adset_id or '').strip()} to {daily_budget_cents}.",
        "update adset budget",
    )


if __name__ == "__main__":
    app.run(transport="stdio")

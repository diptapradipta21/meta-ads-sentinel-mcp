#!/usr/bin/env python3
"""
meta-ads-sentinel-mcp — Model Context Protocol (MCP) Server for Meta Marketing API.
Enables Claude Desktop & Claude Code to inspect campaigns, monitor adset CPL/frequency,
and autonomously pause fatigued ads or adjust daily budgets.
"""

import os
import sys
import json
import urllib.request
import urllib.error
import urllib.parse
from typing import Optional
try:
    from mcp.server.mcpserver import MCPServer
    app = MCPServer("meta-ads-sentinel-mcp")
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

def get_meta_config():
    access_token = os.environ.get("META_ACCESS_TOKEN", "")
    ad_account_id = os.environ.get("META_AD_ACCOUNT_ID", "")
    api_version = os.environ.get("META_API_VERSION", "v21.0")
    if not access_token or not ad_account_id:
        raise ValueError("Missing META_ACCESS_TOKEN or META_AD_ACCOUNT_ID environment variables.")
    if not ad_account_id.startswith("act_"):
        ad_account_id = f"act_{ad_account_id}"
    return access_token, ad_account_id, api_version

def meta_api_request(endpoint: str, params: dict = None, method: str = "GET") -> dict:
    access_token, ad_account_id, api_version = get_meta_config()
    params = params or {}
    params["access_token"] = access_token
    query_str = urllib.parse.urlencode(params)
    
    url = f"https://graph.facebook.com/{api_version}/{endpoint}?{query_str}"
    req = urllib.request.Request(url, headers={"User-Agent": "Claude-Meta-Sentinel"}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8")
        try:
            return {"error": json.loads(err)}
        except Exception:
            return {"error": err}
    except Exception as e:
        return {"error": str(e)}

@app.tool()
def get_campaign_insights(date_preset: str = "last_7d") -> str:
    """
    Fetch aggregate spend, impressions, clicks, leads, and CPA across active campaigns.
    
    Args:
        date_preset: Time window (e.g. 'today', 'yesterday', 'last_7d', 'last_30d').
    """
    _, ad_account_id, _ = get_meta_config()
    fields = "campaign_name,spend,impressions,clicks,cpc,cpm,actions,cost_per_action_type"
    res = meta_api_request(f"{ad_account_id}/insights", {"fields": fields, "date_preset": date_preset})
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
    token, _, api_version = get_meta_config()
    url = f"https://graph.facebook.com/{api_version}/{adset_id}"
    payload = urllib.parse.urlencode({"status": "PAUSED", "access_token": token}).encode()
    req = urllib.request.Request(url, data=payload, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            if data.get("success"):
                return f"Successfully PAUSED adset ID: {adset_id}."
            return f"Update returned: {data}"
    except Exception as e:
        return f"Failed to pause adset: {e}"

@app.tool()
def activate_adset(adset_id: str) -> str:
    """
    Activate or resume a paused Meta Adset.
    
    Args:
        adset_id: The numeric ID of the adset to resume.
    """
    token, _, api_version = get_meta_config()
    url = f"https://graph.facebook.com/{api_version}/{adset_id}"
    payload = urllib.parse.urlencode({"status": "ACTIVE", "access_token": token}).encode()
    req = urllib.request.Request(url, data=payload, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            if data.get("success"):
                return f"Successfully ACTIVATED adset ID: {adset_id}."
            return f"Update returned: {data}"
    except Exception as e:
        return f"Failed to activate adset: {e}"

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

    token, _, api_version = get_meta_config()
    url = f"https://graph.facebook.com/{api_version}/{adset_id}"
    payload = urllib.parse.urlencode({"daily_budget": daily_budget_cents, "access_token": token}).encode()
    req = urllib.request.Request(url, data=payload, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            if data.get("success"):
                return f"Successfully updated daily budget for adset ID {adset_id} to {daily_budget_cents}."
            return f"Update returned: {data}"
    except Exception as e:
        return f"Failed to update adset budget: {e}"

if __name__ == "__main__":
    app.run(transport="stdio")

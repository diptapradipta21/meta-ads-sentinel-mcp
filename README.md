# 📈 Meta Ads Sentinel MCP Server

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![MCP Standard](https://img.shields.io/badge/MCP-2.0-orange.svg)](https://modelcontextprotocol.io/)
[![Claude Ready](https://img.shields.io/badge/Claude-Desktop%20%26%20Code-purple.svg)](https://claude.ai/)

> **Model Context Protocol (MCP 2.0) server enabling Claude Desktop & Code to audit Meta Ads performance, monitor CPL/frequency fatigue, and autonomously manage budgets or pause burning adsets.**

---

## 🛠️ Available MCP Tools
- `get_campaign_insights(date_preset="last_7d", level="campaign")`: Fetches aggregate ad spend, impressions, clicks, CPC, CPM, and actions at `account`, `campaign`, `adset`, or `ad` level.
- `list_adsets_health()`: Identifies high-frequency fatigue (>3.5x) and high CPL across active adsets.
- `pause_adset(adset_id)`: Emergency pause underperforming adsets directly from Claude.
- `activate_adset(adset_id)`: Resume or activate paused Meta Adsets.
- `update_adset_budget(adset_id, daily_budget_cents)`: Dynamically adjust adset daily budget in account currency subunits.

---

## ⚙️ Configuration

| Environment Variable | Description | Default |
|---|---|---|
| `META_ACCESS_TOKEN` | Meta Marketing API access token | *(Required)* |
| `META_AD_ACCOUNT_ID` | Ad Account ID (with or without `act_` prefix) | *(Required)* |
| `META_API_VERSION` | Graph API version | `v21.0` |

### Claude Desktop Config
```json
{
  "mcpServers": {
    "meta-ads-sentinel": {
      "command": "python3",
      "args": ["/path/to/meta-ads-sentinel-mcp/server.py"],
      "env": {
        "META_ACCESS_TOKEN": "YOUR_TOKEN",
        "META_AD_ACCOUNT_ID": "act_1234567890",
        "META_API_VERSION": "v21.0"
      }
    }
  }
}
```

---

## 🧪 Running Tests
```bash
python3 -m unittest discover -s tests -v
```

---

## 📄 License
MIT License - Copyright (c) 2026 Fajar Indra Pradipta Gajah.

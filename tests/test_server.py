#!/usr/bin/env python3
import json
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import server

class TestMetaAdsSentinelMCP(unittest.TestCase):
    def setUp(self):
        self.env_patcher = patch.dict("os.environ", {
            "META_ACCESS_TOKEN": "EAAXfakeToken123",
            "META_AD_ACCOUNT_ID": "1234567890",
            "META_API_VERSION": "v21.0"
        })
        self.env_patcher.start()

    def tearDown(self):
        self.env_patcher.stop()

    def test_get_meta_config_prefixes_act(self):
        token, account_id, version = server.get_meta_config()
        self.assertEqual(token, "EAAXfakeToken123")
        self.assertEqual(account_id, "act_1234567890")
        self.assertEqual(version, "v21.0")

    def test_get_meta_config_missing_raises_value_error(self):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(ValueError):
                server.get_meta_config()

    @patch("urllib.request.urlopen")
    def test_get_campaign_insights_success(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"data": [{"campaign_name": "TOFU Campaign", "spend": "150.00"}]}).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        res = server.get_campaign_insights("last_7d")
        self.assertIn("TOFU Campaign", res)
        self.assertIn("150.00", res)

    @patch("urllib.request.urlopen")
    def test_pause_and_activate_adset_success(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"success": True}).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        pause_res = server.pause_adset("987654321")
        self.assertIn("Successfully PAUSED adset ID: 987654321", pause_res)

        activate_res = server.activate_adset("987654321")
        self.assertIn("Successfully ACTIVATED adset ID: 987654321", activate_res)

    def test_update_adset_budget_validation(self):
        res = server.update_adset_budget("987654321", -500)
        self.assertIn("daily_budget_cents must be a positive integer", res)

    @patch("urllib.request.urlopen")
    def test_update_adset_budget_success(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"success": True}).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        res = server.update_adset_budget("987654321", 5000000)
        self.assertIn("Successfully updated daily budget for adset ID 987654321", res)

if __name__ == "__main__":
    unittest.main()

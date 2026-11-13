#!/usr/bin/env python3
import io
import json
import sys
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

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
    def test_get_campaign_insights_passes_level_campaign(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"data": [{"campaign_name": "TOFU Campaign", "spend": "150.00"}]}).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        res = server.get_campaign_insights("last_7d")
        self.assertIn("TOFU Campaign", res)
        self.assertIn("150.00", res)
        called_req = mock_urlopen.call_args[0][0]
        self.assertIn("level=campaign", called_req.full_url)

    def test_get_campaign_insights_invalid_level(self):
        res = server.get_campaign_insights("last_7d", level="invalid")
        self.assertIn("Invalid insight level", res)

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

    def test_adset_id_validation(self):
        self.assertIn("non-empty numeric ID", server.pause_adset("../bad"))
        self.assertIn("non-empty numeric ID", server.activate_adset(""))
        self.assertIn("non-empty numeric ID", server.update_adset_budget("abc", 1000))

    @patch("urllib.request.urlopen")
    def test_http_error_parses_meta_json_message(self, mock_urlopen):
        err_body = json.dumps({"error": {"message": "Budget too low", "code": 100}}).encode("utf-8")
        http_err = urllib.error.HTTPError(
            url="https://graph.facebook.com/v21.0/987654321",
            code=400,
            msg="Bad Request",
            hdrs=None,
            fp=io.BytesIO(err_body),
        )
        mock_urlopen.side_effect = http_err
        try:
            res = server.update_adset_budget("987654321", 10)
            self.assertIn("Meta code 100", res)
            self.assertIn("Budget too low", res)
        finally:
            http_err.close()

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


    @patch("urllib.request.urlopen")
    def test_check_ad_account_status_success(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "name": "EELIT Agency",
            "account_status": 1,
            "currency": "SGD",
            "timezone_name": "Asia/Singapore"
        }).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        res = server.check_ad_account_status()
        self.assertIn("act_1234567890", res)
        self.assertIn("EELIT Agency", res)
        self.assertIn("Status=ACTIVE", res)
        self.assertIn("Currency=SGD", res)

    @patch("urllib.request.urlopen")
    def test_check_ad_account_status_error(self, mock_urlopen):
        err_body = json.dumps({"error": {"message": "Invalid OAuth token", "code": 190}}).encode("utf-8")
        http_err = urllib.error.HTTPError(
            url="https://graph.facebook.com/v21.0/act_1234567890",
            code=400,
            msg="Bad Request",
            hdrs=None,
            fp=io.BytesIO(err_body),
        )
        mock_urlopen.side_effect = http_err
        try:
            res = server.check_ad_account_status()
            self.assertIn("Meta API Error", res)
            self.assertIn("Invalid OAuth token", res)
        finally:
            http_err.close()

if __name__ == "__main__":

    unittest.main()

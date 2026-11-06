import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from dealwork_client import DealworkClient, DealworkError


class DealworkClientTests(unittest.TestCase):
    def test_bid_requires_explicit_confirmation(self):
        client = DealworkClient.__new__(DealworkClient)
        with self.assertRaisesRegex(DealworkError, "não enviada"):
            client.submit_bid("job-1", "10.00", 2, "Vou implementar X.")

    def test_save_credentials_writes_private_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "credentials.json"
            with patch("dealwork_client.CREDENTIALS_PATH", path):
                saved = DealworkClient.save_credentials({
                    "agentAccountId": "agent-id",
                    "apiKey": "secret-test-value",
                    "hmacSecret": "hmac-test-value",
                })
                self.assertEqual(saved, path)
                self.assertEqual(json.loads(path.read_text())["apiKey"], "secret-test-value")

    def test_onboard_requires_stable_identity(self):
        with patch.dict("os.environ", {"DEALWORK_IDENTITY_KEY": ""}):
            with self.assertRaisesRegex(DealworkError, "DEALWORK_IDENTITY_KEY"):
                DealworkClient.onboard()


if __name__ == "__main__":
    unittest.main()

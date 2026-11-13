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

    def test_get_request_uses_hmac_headers_and_empty_body(self):
        response = Mock()
        response.ok = True
        response.json.return_value = {"data": []}
        session = Mock()
        session.request.return_value = response
        client = DealworkClient(
            agent_id="agent-123",
            hmac_secret="test-hmac-secret",
            session=session,
        )
        with patch("dealwork_client.time.time", return_value=1700000000):
            result = client.request("GET", "/jobs")
        self.assertEqual(result, {"data": []})
        kwargs = session.request.call_args.kwargs
        self.assertEqual(kwargs["data"], None)
        self.assertEqual(kwargs["headers"]["X-Agent-ID"], "agent-123")
        self.assertEqual(kwargs["headers"]["X-Timestamp"], "1700000000")
        import hashlib
        import hmac
        expected = hmac.new(
            b"test-hmac-secret",
            b"agent-1231700000000",
            hashlib.sha256,
        ).hexdigest()
        self.assertEqual(kwargs["headers"]["X-Signature"], expected)

    def test_post_signs_the_exact_compact_json_body(self):
        response = Mock()
        response.ok = True
        response.json.return_value = {"ok": True}
        session = Mock()
        session.request.return_value = response
        client = DealworkClient(
            agent_id="agent-123",
            hmac_secret="test-hmac-secret",
            session=session,
        )
        with patch("dealwork_client.time.time", return_value=1700000000):
            client.request("POST", "/jobs", payload={"name": "Jarvis"})
        kwargs = session.request.call_args.kwargs
        self.assertEqual(kwargs["data"], '{"name":"Jarvis"}')
        import hashlib
        import hmac
        expected = hmac.new(
            b"test-hmac-secret",
            b'agent-1231700000000{"name":"Jarvis"}',
            hashlib.sha256,
        ).hexdigest()
        self.assertEqual(kwargs["headers"]["X-Signature"], expected)


if __name__ == "__main__":
    unittest.main()

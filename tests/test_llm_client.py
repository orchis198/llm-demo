import json
import unittest
from unittest.mock import MagicMock, patch

from llm.client import LLMClient
from llm.service import ensure_required_keys


class LLMClientTestCase(unittest.TestCase):
    def test_ensure_required_keys_rejects_missing_fields(self) -> None:
        with self.assertRaises(ValueError):
            ensure_required_keys({"business_type": "采购类"}, ["business_type", "voucher_title"])

    @patch("llm.client.settings")
    def test_client_availability_depends_on_key_and_flag(self, mock_settings) -> None:
        mock_settings.LLM_ENABLED = True
        mock_settings.LLM_PROVIDER = "openai-compatible"
        mock_settings.LLM_MODEL = "demo-model"
        mock_settings.LLM_API_BASE = "https://example.com/v1"
        mock_settings.LLM_API_KEY = "test-key"
        mock_settings.LLM_TIMEOUT = 30
        mock_settings.LLM_TEMPERATURE = 0.2
        mock_settings.LLM_MAX_TOKENS = 500

        client = LLMClient()
        self.assertTrue(client.is_available())

    @patch("llm.client.OpenAI")
    @patch("llm.client.settings")
    def test_generate_json_uses_openai_compatible_client(self, mock_settings, mock_openai) -> None:
        mock_settings.LLM_ENABLED = True
        mock_settings.LLM_PROVIDER = "openai-compatible"
        mock_settings.LLM_MODEL = "demo-model"
        mock_settings.LLM_API_BASE = "https://example.com/v1"
        mock_settings.LLM_API_KEY = "test-key"
        mock_settings.LLM_TIMEOUT = 30
        mock_settings.LLM_TEMPERATURE = 0.2
        mock_settings.LLM_MAX_TOKENS = 500

        fake_response = MagicMock()
        fake_response.choices = [MagicMock(message=MagicMock(content=json.dumps({"ok": True})))]
        fake_client = MagicMock()
        fake_client.chat.completions.create.return_value = fake_response
        mock_openai.return_value = fake_client

        client = LLMClient()
        result = client.generate_json(system_prompt="sys", user_prompt="user")

        self.assertEqual(result, {"ok": True})
        fake_client.chat.completions.create.assert_called_once()


if __name__ == "__main__":
    unittest.main()

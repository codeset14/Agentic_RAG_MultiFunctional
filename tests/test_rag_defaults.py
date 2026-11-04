from __future__ import annotations

import unittest
from unittest.mock import patch

from src.config.settings import AppSettings
from src.llm.groq_client import GroqClient


class RagDefaultsTests(unittest.TestCase):
    def test_defaults_use_fast_model_and_single_validation_pass(self) -> None:
        settings = AppSettings(groq_api_key="test-key")

        self.assertEqual(settings.groq_model, "openai/gpt-oss-20b")
        self.assertEqual(settings.max_iterations, 1)

    @patch("src.llm.groq_client.AsyncGroq")
    def test_client_bounds_wait_and_disables_slow_retries(self, groq_client) -> None:
        client = GroqClient("test-key", "openai/gpt-oss-20b")

        groq_client.assert_called_once_with(
            api_key="test-key",
            timeout=30.0,
            max_retries=0,
        )
        self.assertEqual(client.model, "openai/gpt-oss-20b")


if __name__ == "__main__":
    unittest.main()

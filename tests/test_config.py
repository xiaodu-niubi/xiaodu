"""Verify credential isolation without reading or exposing real credentials."""
import os
from pathlib import Path
import runpy
import shutil
import tempfile
import unittest
from unittest.mock import patch

from src.models.llm_client import build_llm, MissingModelCredentialsError
from src.config import settings


class ConfigurationTests(unittest.TestCase):
    def load_settings(self, file_content, inherited):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "src").mkdir()
            config = root / "src" / "config.py"
            shutil.copyfile(Path(__file__).resolve().parents[1] / "src" / "config.py", config)
            (root / ".env").write_text(file_content, encoding="utf-8")
            with patch.dict(os.environ, inherited, clear=True):
                loaded = runpy.run_path(str(config))["settings"]
                self.assertEqual(os.environ.get("LLM_API_KEY"), inherited.get("LLM_API_KEY"))
                return loaded

    def test_file_key_is_ignored_but_other_file_settings_load(self):
        loaded = self.load_settings("LLM_API_KEY=file-only-test-key\nLLM_MODEL=file-model\n", {})
        self.assertEqual(loaded.llm_api_key, "")
        self.assertEqual(loaded.llm_model, "file-model")

    def test_inherited_key_and_other_settings_take_precedence(self):
        loaded = self.load_settings(
            "LLM_API_KEY=obsolete-file-key\nLLM_MODEL=file-model\n",
            {"LLM_API_KEY": "inherited-test-key", "LLM_MODEL": "inherited-model"},
        )
        self.assertEqual(loaded.llm_api_key, "inherited-test-key")
        self.assertEqual(loaded.llm_model, "inherited-model")

    def test_missing_key_fails_before_model_client_is_created(self):
        with patch.object(settings, "llm_api_key", ""), patch("src.models.llm_client.ChatOpenAI") as client:
            with self.assertRaisesRegex(MissingModelCredentialsError, "LLM_API_KEY"):
                build_llm()
            client.assert_not_called()

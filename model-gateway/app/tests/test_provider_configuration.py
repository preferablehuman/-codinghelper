import unittest

from app.config import Settings
from app.providers.langchain import LangChainProvider, provider_configuration


class ProviderConfigurationTests(unittest.TestCase):
    def test_reads_only_the_selected_provider_block(self):
        settings = Settings(
            llm_provider="nvidia",
            nvidia_llm_model="nvidia/model",
            nvidia_llm_json_model="nvidia/json-model",
            nvidia_llm_api_key="nvidia-key",
            nvidia_llm_base_url="https://nvidia.example/v1",
            gemini_llm_model="gemini/model",
            gemini_llm_api_key="gemini-key",
        )

        selected = provider_configuration(settings, "nvidia")

        self.assertEqual(selected.model, "nvidia/model")
        self.assertEqual(selected.json_model, "nvidia/json-model")
        self.assertEqual(selected.api_key, "nvidia-key")
        self.assertEqual(selected.base_url, "https://nvidia.example/v1")

    def test_provider_normalizes_hyphenated_openai_compatible_name(self):
        settings = Settings(
            llm_provider="openai-compatible",
            openai_compatible_llm_model="custom/model",
            openai_compatible_llm_api_key="custom-key",
            openai_compatible_llm_base_url="https://models.example/v1",
        )

        provider = LangChainProvider.from_settings(settings)

        self.assertEqual(provider.provider, "openai_compatible")
        self.assertEqual(provider.model, "custom/model")
        self.assertEqual(provider.api_key, "custom-key")

    def test_json_model_defaults_to_provider_model(self):
        settings = Settings(
            llm_provider="ollama",
            ollama_llm_model="local/model",
            ollama_llm_json_model="",
        )

        provider = LangChainProvider.from_settings(settings)

        self.assertEqual(provider.model, "local/model")
        self.assertEqual(provider.json_model, "local/model")


if __name__ == "__main__":
    unittest.main()

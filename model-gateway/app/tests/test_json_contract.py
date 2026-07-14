import json
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from app.json_contract import StructuredOutputError, normalize_json_text
from app.main import generate
from app.providers.langchain import LangChainProvider, _message_text
from app.schemas import GenerateRequest


class FakeProvider:
    def __init__(self, responses: list[str]) -> None:
        self.responses = responses
        self.prompts: list[str] = []

    def generate(self, prompt: str, max_new_tokens: int, *, json_mode: bool = False, schema_name: str | None = None) -> str:
        self.prompts.append(prompt)
        return self.responses.pop(0)

    def status(self) -> dict[str, object]:
        return {"provider": "fake", "model": "fake-model", "loaded": True}


class JsonContractTests(unittest.TestCase):
    def test_normalizes_fenced_json(self) -> None:
        self.assertEqual(normalize_json_text('```json\n{"ok": true}\n```'), '{"ok":true}')

    def test_rejects_bullet_prose_with_a_nested_array(self) -> None:
        with self.assertRaises(StructuredOutputError):
            normalize_json_text('* Candidate patterns: ["hash_map", "arrays"]')

    def test_controlled_schema_rejects_invalid_equivalence_payload(self) -> None:
        from app.structured_schemas import validate_schema
        with self.assertRaises(Exception):
            validate_schema('{"relation":"MAYBE","confidence":2,"reason":"x"}', "problem_equivalence")

    def test_tests_schema_rejects_untyped_or_extra_fields(self) -> None:
        from app.structured_schemas import validate_schema
        with self.assertRaises(Exception):
            validate_schema('[{"input":1,"expected_output":[],"test_type":"OTHER","extra":true}]', "tests")

    def test_gateway_retries_json_contract_violation(self) -> None:
        provider = FakeProvider(
            [
                '* Summary followed by ["hash_map"]',
                json.dumps({"summary": "Valid Sudoku", "candidate_patterns": ["hash_map"]}),
            ]
        )
        with patch("app.main.get_provider", return_value=provider):
            response = generate(GenerateRequest(prompt="Analyze", max_new_tokens=1024, json_mode=True))

        self.assertEqual(json.loads(response.text)["summary"], "Valid Sudoku")
        self.assertEqual(len(provider.prompts), 2)
        self.assertIn("CRITICAL STRUCTURED-OUTPUT RETRY", provider.prompts[1])
        self.assertIn("Summary followed by", provider.prompts[1])

    def test_langchain_routes_json_mode_to_structured_model(self) -> None:
        provider = LangChainProvider(
            provider="nvidia",
            api_key="key",
            base_url="https://integrate.api.nvidia.com/v1",
            model="nvidia/default-model",
            json_model="nvidia/structured-model",
            temperature=0.2,
            request_timeout_seconds=10,
            max_retries=1,
            ollama_num_ctx=8192,
            ollama_keep_alive="-1",
        )
        provider._status["loaded"] = True
        chat = Mock()
        structured = Mock()
        chat.with_structured_output.return_value = structured
        structured.with_retry.return_value = structured
        structured.invoke.return_value = {"summary": "ok"}
        with patch.object(provider, "_build_chat_model", return_value=chat) as build:
            self.assertEqual(provider.generate("prompt", 1024, json_mode=True, schema_name="problem_analysis"), '{"summary":"ok"}')

        self.assertEqual(build.call_args.args[0], "nvidia/structured-model")
        self.assertTrue(build.call_args.kwargs["json_mode"])
        chat.with_structured_output.assert_called_once()

    def test_message_text_ignores_reasoning_blocks(self) -> None:
        message = SimpleNamespace(
            content=[
                {"type": "reasoning", "text": "private reasoning"},
                {"type": "text", "text": "final answer"},
            ]
        )
        self.assertEqual(_message_text(message), "final answer")

    def test_langchain_falls_back_when_native_structured_output_is_rejected(self) -> None:
        provider = LangChainProvider(
            provider="gemini", api_key="key", base_url="", model="gemini-test", json_model="gemini-test",
            temperature=0.2, request_timeout_seconds=10, max_retries=1, ollama_num_ctx=8192, ollama_keep_alive="-1",
        )
        provider._status["loaded"] = True
        chat = Mock()
        structured = Mock()
        structured.with_retry.return_value = structured
        structured.invoke.side_effect = RuntimeError("schema unsupported")
        chat.with_structured_output.return_value = structured
        chat.with_retry.return_value = chat
        chat.invoke.return_value = SimpleNamespace(content='{"summary":"fallback"}')
        with patch.object(provider, "_build_chat_model", return_value=chat):
            result = provider.generate("prompt", 1024, json_mode=True, schema_name="problem_analysis")
        self.assertEqual(result, '{"summary":"fallback"}')


if __name__ == "__main__":
    unittest.main()

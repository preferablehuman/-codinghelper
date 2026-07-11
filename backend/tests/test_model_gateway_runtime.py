from unittest.mock import patch

import httpx

from app.model_runtime.gateway_runtime import ModelGatewayRuntime


def response(status_code: int, payload: dict[str, object], path: str) -> httpx.Response:
    return httpx.Response(
        status_code,
        json=payload,
        request=httpx.Request("GET", f"http://model-gateway:8300{path}"),
    )


def test_gateway_client_loads_without_knowing_provider_implementation() -> None:
    runtime = ModelGatewayRuntime("http://model-gateway:8300", 60, 5)
    payload = {
        "status": "ok",
        "ready": True,
        "provider": "future-provider",
        "model": {"loaded": True, "provider": "future-provider", "model": "future-model"},
    }
    with patch("app.model_runtime.gateway_runtime.httpx.get", return_value=response(200, payload, "/health")):
        runtime.load()
        assert runtime.status()["provider"] == "future-provider"


def test_gateway_client_uses_stable_generate_contract() -> None:
    runtime = ModelGatewayRuntime("http://model-gateway:8300", 60, 5)
    payload = {"text": "generated", "provider": "any-provider", "model": "any-model"}
    with patch(
        "app.model_runtime.gateway_runtime.httpx.post",
        return_value=response(200, payload, "/generate"),
    ) as request:
        text = runtime.generate("prompt", 2048, json_mode=True)

    assert text == "generated"
    assert request.call_args.kwargs["json"] == {
        "prompt": "prompt",
        "max_new_tokens": 2048,
        "json_mode": True,
    }

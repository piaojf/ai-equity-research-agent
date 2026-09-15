import json

import httpx
import pytest
from pydantic import BaseModel, SecretStr

from app.providers.llm.openai_compatible import OpenAICompatibleProvider


class ExampleOutput(BaseModel):
    answer: str


@pytest.mark.asyncio
async def test_openai_compatible_provider_validates_structured_output() -> None:
    captured: dict[str, object] = {}

    def response(_: httpx.Request) -> httpx.Response:
        captured.update(_json=_.content.decode())
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"content": '{"answer":"grounded"}'}}
                ]
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(response)) as client:
        provider = OpenAICompatibleProvider(SecretStr("test-key"), client=client)
        result = await provider.generate_structured(
            system_prompt="Return JSON.",
            user_prompt="Answer.",
            schema=ExampleOutput,
        )

    assert isinstance(result, ExampleOutput)
    assert result.answer == "grounded"
    request_payload = json.loads(str(captured["_json"]))
    assert request_payload["model"] == "deepseek-flash"
    assert request_payload["response_format"] == {"type": "json_object"}
    assert "Return only valid JSON" in request_payload["messages"][0]["content"]

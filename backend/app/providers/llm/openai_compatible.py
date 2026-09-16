import json
from urllib.parse import urlparse

import httpx
from pydantic import BaseModel, SecretStr


class OpenAICompatibleProvider:
    """Structured-output adapter for OpenAI-compatible chat APIs."""

    name = "openai_compatible"
    _allowed_hosts = {"api.deepseek.com", "api.openai.com"}

    def __init__(
        self,
        api_key: SecretStr | str,
        *,
        model: str = "deepseek-flash",
        base_url: str = "https://api.deepseek.com",
        timeout_seconds: float = 30.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.api_key = (
            api_key.get_secret_value() if isinstance(api_key, SecretStr) else api_key
        )
        self.model = model
        self.base_url = base_url.rstrip("/")
        self._validate_base_url(self.base_url)
        self.timeout_seconds = timeout_seconds
        self._client = client

    @classmethod
    def _validate_base_url(cls, base_url: str) -> None:
        parsed = urlparse(base_url)
        if (
            parsed.scheme != "https"
            or parsed.hostname not in cls._allowed_hosts
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError(
                "LLM base URL must use HTTPS and a configured provider host."
            )

    async def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        schema: type[BaseModel],
    ) -> BaseModel:
        schema_json = json.dumps(schema.model_json_schema(), ensure_ascii=False)
        deepseek_system_prompt = (
            f"{system_prompt}\nReturn only valid JSON. "
            "The JSON must follow this schema:\n"
            f"{schema_json}"
        )
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": deepseek_system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        try:
            if self._client is not None:
                response = await self._client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
            else:
                async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                    response = await client.post(
                        f"{self.base_url}/chat/completions",
                        headers=headers,
                        json=payload,
                    )
            response.raise_for_status()
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            if not isinstance(content, str):
                raise ValueError("LLM response content was not text.")
            return schema.model_validate(json.loads(content))
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
            raise RuntimeError("Structured LLM response was unavailable.") from exc

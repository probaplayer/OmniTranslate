import httpx

from translation_core.providers.base import LLMProvider, ProviderError

_MAX_ERROR_BODY_CHARS = 500
_REDACTED = "***REDACTED***"


class OpenAICompatibleProvider(LLMProvider):
    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        client: httpx.Client | None = None,
        timeout: float = 300.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        # `timeout` only applies when this constructs its own client -- a
        # caller passing an explicit `client` (e.g. tests, with a
        # MockTransport) owns that client's timeout already.
        self._client = client or httpx.Client(timeout=timeout)

    def close(self) -> None:
        """Close the underlying HTTP client.

        Note: this closes whatever ``self._client`` is, including a client the
        caller passed into ``__init__`` — the provider treats it as its own.
        """
        self._client.close()

    def __enter__(self) -> "OpenAICompatibleProvider":
        return self

    def __exit__(self, *args) -> None:
        self.close()

    def _sanitize_error_body(self, body_text: str) -> str:
        # Redact the key out of the FULL body first, so a fragment can't
        # survive by being pushed past the truncation boundary.
        if self.api_key:
            body_text = body_text.replace(self.api_key, _REDACTED)
        if len(body_text) > _MAX_ERROR_BODY_CHARS:
            body_text = body_text[:_MAX_ERROR_BODY_CHARS] + "...(truncated)"
        return body_text

    def complete(self, messages: list[dict], **kwargs) -> str:
        payload = {"model": self.model, "messages": messages, **kwargs}
        headers = {"Authorization": f"Bearer {self.api_key}"}

        try:
            response = self._client.post(
                f"{self.base_url}/chat/completions", json=payload, headers=headers
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise ProviderError(
                f"Provider returned HTTP {exc.response.status_code}: "
                f"{self._sanitize_error_body(exc.response.text)}"
            ) from exc
        except httpx.HTTPError as exc:
            raise ProviderError(f"Provider request failed: {exc}") from exc

        try:
            data = response.json()
            content = data["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise ProviderError(f"Provider returned an unexpected response shape: {exc}") from exc

        if not isinstance(content, str):
            raise ProviderError(
                "Provider returned an unexpected response shape: message content must be a "
                f"str, got {type(content).__name__}"
            )

        return content

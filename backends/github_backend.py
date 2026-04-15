from __future__ import annotations

import os
from typing import AsyncIterator, Iterable
from urllib.parse import urlparse

import ssl

import httpx
import truststore
from openai import AsyncOpenAI, NotFoundError

from .base import AgentBackend, AgentSpec, NormalizedEvent, NormalizedMessage


class GitHubModelsBackend(AgentBackend):
    def __init__(self) -> None:
        self._token = os.getenv("GITHUB_TOKEN")
        self._model = self._normalize_model(os.getenv("GITHUB_MODEL", "gpt-4o-mini"))
        self._endpoint = self._normalize_endpoint(
            os.getenv("GITHUB_ENDPOINT", "https://models.github.ai/inference")
        )
        self._client: AsyncOpenAI | None = None

    async def __aenter__(self) -> "GitHubModelsBackend":
        ssl_context = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        http_client = httpx.AsyncClient(verify=ssl_context)
        self._client = AsyncOpenAI(
            api_key=self._token,
            base_url=self._endpoint,
            http_client=http_client,
        )
        return self

    async def create_agent(self, spec: AgentSpec) -> object:
        return spec

    async def run_workflow(
        self,
        participants: Iterable[object],
        input_text: str,
    ) -> AsyncIterator[NormalizedEvent]:
        if self._client is None:
            raise RuntimeError("GitHub Models backend is not initialized.")

        current_context = input_text.strip()

        all_messages: list[NormalizedMessage] = [
            NormalizedMessage(author_name="user", role="user", text=current_context)
        ]

        for participant in participants:
            if not isinstance(participant, AgentSpec):
                raise TypeError("GitHub Models backend expects AgentSpec participants.")

            response = await self._create_completion(
                system_instructions=participant.instructions,
                user_content=current_context,
            )

            text = (response.choices[0].message.content or "").strip()
            all_messages.append(
                NormalizedMessage(
                    author_name=participant.name,
                    role="assistant",
                    text=text,
                )
            )
            yield NormalizedEvent(
                type="output",
                data=list(all_messages),
            )

            current_context = (
                f"Original input:\n{input_text.strip()}\n\n"
                f"Previous output from {participant.name}:\n{text}\n\n"
                "Continue with your task based on this context."
            )

    async def close(self) -> None:
        if self._client is not None:
            await self._client.close()
            self._client = None

    async def _create_completion(self, system_instructions: str, user_content: str):
        if self._client is None:
            raise RuntimeError("GitHub Models backend is not initialized.")

        candidates = self._candidate_models(self._model)
        last_error: Exception | None = None

        for candidate in candidates:
            try:
                return await self._client.chat.completions.create(
                    model=candidate,
                    messages=[
                        {"role": "system", "content": system_instructions},
                        {"role": "user", "content": user_content},
                    ],
                )
            except NotFoundError as err:
                last_error = err
                message = str(err).lower()
                if "unknown model" not in message:
                    raise

        configured = self._model
        tried = ", ".join(candidates)
        raise ValueError(
            f"Unknown model for GitHub Models. Configured '{configured}', tried: {tried}. "
            "Set GITHUB_MODEL to a valid model such as 'openai/gpt-4o-mini'."
        ) from last_error

    @staticmethod
    def _normalize_model(model: str) -> str:
        cleaned = model.strip()
        if not cleaned:
            raise ValueError(
                "GITHUB_MODEL is empty. Use a model like 'openai/gpt-4o-mini' or 'gpt-4o-mini'."
            )

        if cleaned.count("/") > 1:
            raise ValueError(
                "Invalid GITHUB_MODEL format. Use 'gpt-4o-mini' or 'openai/gpt-4o-mini'."
            )

        if "/" in cleaned:
            provider, model_name = cleaned.split("/", 1)
            if not provider.strip() or not model_name.strip():
                raise ValueError(
                    "Invalid GITHUB_MODEL format. Use 'gpt-4o-mini' or 'openai/gpt-4o-mini'."
                )

        return cleaned

    @staticmethod
    def _candidate_models(configured_model: str) -> list[str]:
        if "/" in configured_model:
            _, bare = configured_model.split("/", 1)
            candidates = [configured_model, bare]
        else:
            candidates = [configured_model, f"openai/{configured_model}"]

        # Keep order but remove accidental duplicates.
        return list(dict.fromkeys(candidate.strip() for candidate in candidates if candidate.strip()))

    @staticmethod
    def _normalize_endpoint(endpoint: str) -> str:
        normalized = endpoint.strip().rstrip("/")
        parsed = urlparse(normalized)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError(
                "Invalid GITHUB_ENDPOINT. Use a full URL like 'https://models.github.ai/inference'."
            )

        is_github_inference = (
            parsed.netloc.lower() == "models.github.ai"
            and parsed.path.rstrip("/").lower().endswith("/inference")
        )
        if is_github_inference:
            return normalized

        if not normalized.endswith("/v1"):
            normalized = f"{normalized}/v1"
        return normalized

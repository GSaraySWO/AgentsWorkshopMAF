from __future__ import annotations

from typing import AsyncIterator, Iterable, cast

from agent_framework import Message
from agent_framework.azure import AzureAIAgentClient
from agent_framework.orchestrations import SequentialBuilder
from azure.identity import AzureCliCredential

from .base import AgentBackend, AgentSpec, NormalizedEvent, NormalizedMessage


class AzureBackend(AgentBackend):
    def __init__(self) -> None:
        self._credential = AzureCliCredential()
        self._client_ctx: AzureAIAgentClient | None = None
        self._chat_client: AzureAIAgentClient | None = None

    async def __aenter__(self) -> "AzureBackend":
        self._client_ctx = AzureAIAgentClient(credential=self._credential)
        self._chat_client = await self._client_ctx.__aenter__()
        return self

    async def create_agent(self, spec: AgentSpec) -> object:
        if self._chat_client is None:
            raise RuntimeError("Azure backend is not initialized.")

        return self._chat_client.as_agent(
            instructions=spec.instructions,
            name=spec.name,
        )

    async def run_workflow(
        self,
        participants: Iterable[object],
        input_text: str,
    ) -> AsyncIterator[NormalizedEvent]:
        workflow = SequentialBuilder(participants=list(participants)).build()

        async for event in workflow.run(input_text, stream=True):
            if event.type != "output":
                continue

            messages = cast(list[Message], event.data)
            normalized_messages = [
                NormalizedMessage(
                    author_name=msg.author_name
                    or ("assistant" if msg.role == "assistant" else "user"),
                    role=msg.role,
                    text=msg.text,
                )
                for msg in messages
            ]
            yield NormalizedEvent(type="output", data=normalized_messages)

    async def close(self) -> None:
        if self._client_ctx is not None:
            await self._client_ctx.__aexit__(None, None, None)
            self._client_ctx = None
            self._chat_client = None

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import AsyncIterator, Iterable


@dataclass
class AgentSpec:
    name: str
    instructions: str


@dataclass
class NormalizedMessage:
    author_name: str
    role: str
    text: str


@dataclass
class NormalizedEvent:
    type: str
    data: list[NormalizedMessage]


class AgentBackend(ABC):
    async def __aenter__(self) -> "AgentBackend":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()

    @abstractmethod
    async def create_agent(self, spec: AgentSpec) -> object:
        raise NotImplementedError

    @abstractmethod
    async def run_workflow(
        self,
        participants: Iterable[object],
        input_text: str,
    ) -> AsyncIterator[NormalizedEvent]:
        raise NotImplementedError

    @abstractmethod
    async def close(self) -> None:
        raise NotImplementedError

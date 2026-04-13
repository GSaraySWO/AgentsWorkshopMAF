from __future__ import annotations

import os
from typing import Literal

from dotenv import load_dotenv

from backends.base import AgentBackend

load_dotenv()

BackendType = Literal["azure", "github"]


class BackendConfig:
    def __init__(self) -> None:
        self.backend_type: BackendType = cast_backend_type(
            os.getenv("AGENT_BACKEND", "github")
        )

    def validate(self) -> None:
        if self.backend_type == "azure":
            self._ensure_required(
                [
                    "AZURE_AI_PROJECT_ENDPOINT",
                    "AZURE_AI_MODEL_DEPLOYMENT_NAME",
                ]
            )
            return

        self._ensure_required(["GITHUB_TOKEN", "GITHUB_MODEL"])

    def create_backend(self) -> AgentBackend:
        self.validate()

        if self.backend_type == "azure":
            from backends.azure_backend import AzureBackend

            return AzureBackend()

        from backends.github_backend import GitHubModelsBackend

        return GitHubModelsBackend()

    @staticmethod
    def _ensure_required(required: list[str]) -> None:
        missing = [name for name in required if not os.getenv(name)]
        if missing:
            missing_list = ", ".join(missing)
            raise ValueError(f"Missing required environment variables: {missing_list}")


def cast_backend_type(value: str) -> BackendType:
    normalized = value.strip().lower()
    if normalized not in {"azure", "github"}:
        raise ValueError("AGENT_BACKEND must be 'azure' or 'github'.")
    return normalized  # type: ignore[return-value]


def get_backend() -> AgentBackend:
    return BackendConfig().create_backend()

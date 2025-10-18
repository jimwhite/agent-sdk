from __future__ import annotations

import json
import logging
from pathlib import Path

from openhands.sdk.llm.llm import LLM
from openhands.sdk.llm.llm_registry import LLMRegistry


logger = logging.getLogger(__name__)


class ProfileManager:
    """Manage LLM profile files on disk.

    Profiles are stored as JSON files using the existing LLM schema, typically
    at ~/.openhands/llm-profiles/<profile_name>.json.
    """

    def __init__(self, base_dir: str | Path | None = None):
        if base_dir is None:
            self.base_dir = Path.home() / ".openhands" / "llm-profiles"
        else:
            self.base_dir = Path(base_dir).expanduser()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def list_profiles(self) -> list[str]:
        return sorted([p.stem for p in self.base_dir.glob("*.json")])

    def get_profile_path(self, name: str) -> Path:
        return self.base_dir / f"{name}.json"

    def load_profile(self, name: str) -> LLM:
        p = self.get_profile_path(name)
        if not p.exists():
            raise FileNotFoundError(f"Profile not found: {name} -> {p}")
        # Use LLM.load_from_json to leverage pydantic validation
        llm = LLM.load_from_json(str(p))
        # Ensure profile_id is present on loaded LLM
        if getattr(llm, "profile_id", None) is None:
            try:
                llm = llm.model_copy(update={"profile_id": name})
            except Exception:
                # Old pydantic versions might not have model_copy; fallback
                llm.profile_id = name  # type: ignore[attr-defined]
        return llm

    def save_profile(self, name: str, llm: LLM, include_secrets: bool = False) -> Path:
        p = self.get_profile_path(name)
        # Dump model to dict and ensure profile_id is set
        data = llm.model_dump(exclude_none=True)
        data["profile_id"] = name
        # Remove secret fields unless explicitly requested
        if not include_secrets:
            for secret_field in (
                "api_key",
                "aws_access_key_id",
                "aws_secret_access_key",
            ):
                if secret_field in data:
                    data.pop(secret_field, None)
        # Write to file
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved profile {name} -> {p}")
        return p

    def register_all(self, registry: LLMRegistry) -> None:
        # Load and attempt to register all profiles. Skip duplicates.
        for name in self.list_profiles():
            try:
                llm = self.load_profile(name)
                try:
                    registry.add(llm)
                except Exception as e:
                    logger.info(f"Skipping profile {name}: registry.add failed: {e}")
            except Exception as e:
                logger.warning(f"Failed to load profile {name}: {e}")

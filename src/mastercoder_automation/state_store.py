from __future__ import annotations

import json
from pathlib import Path

from .models import PipelineState


class StateStore:
    def __init__(self, path: Path):
        self.path = path

    def load(self) -> PipelineState:
        data = json.loads(self.path.read_text(encoding="utf-8"))
        return PipelineState.model_validate(data)

    def save(self, state: PipelineState) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            state.model_dump_json(indent=2),
            encoding="utf-8",
        )

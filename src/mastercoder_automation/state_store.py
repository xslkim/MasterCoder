from __future__ import annotations

import json
from pathlib import Path

from .models import PipelineState


class StateStore:
    def __init__(self, path: Path):
        self.path = path

    def load(self) -> PipelineState:
        try:
            raw = self.path.read_text(encoding="utf-8")
        except FileNotFoundError as e:
            raise FileNotFoundError(
                f"状态文件不存在：{self.path}（可在仓库根目录执行：mc-auto init-state）"
            ) from e
        data = json.loads(raw)
        return PipelineState.model_validate(data)

    def save(self, state: PipelineState) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            state.model_dump_json(indent=2),
            encoding="utf-8",
        )

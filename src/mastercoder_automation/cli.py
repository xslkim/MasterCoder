from __future__ import annotations

import json

import typer
from rich import print

from .config import load_settings
from .gh_client import GhClient
from .orchestrator import Orchestrator
from .state_store import StateStore

app = typer.Typer(help="Deterministic multi-agent pipeline powered by CrewAI.")


@app.command("run-once")
def run_once(req_id: str | None = typer.Option(default=None, help="Target one REQ id")) -> None:
    settings = load_settings()
    store = StateStore(settings.state_file)
    gh = GhClient(repo=settings.github_repo)
    orchestrator = Orchestrator(settings=settings, store=store, gh=gh)
    state = orchestrator.run_once(req_id=req_id)
    print(json.dumps(state.model_dump(), indent=2))


@app.command("init-state")
def init_state() -> None:
    settings = load_settings()
    template = "state/req-status.example.json"
    data = open(template, "r", encoding="utf-8").read()
    settings.state_file.parent.mkdir(parents=True, exist_ok=True)
    settings.state_file.write_text(data, encoding="utf-8")
    print(f"[green]Initialized state file:[/green] {settings.state_file}")


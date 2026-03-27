from __future__ import annotations

import json
import os

import typer
from rich import print

from .config import load_settings
from .gh_client import GhClient
from .models import ReqState
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


@app.command("run-all")
def run_all(
    req_id: str | None = typer.Option(
        None,
        "--req-id",
        help="Only advance this REQ until DONE/BLOCKED/PENDING; omit to drain all READY/FIXING",
    ),
    max_rounds: int = typer.Option(
        200,
        "--max-rounds",
        help="Safety cap (one round = one picked REQ through the pipeline step)",
    ),
) -> None:
    """Repeatedly run run-once until no READY/FIXING remain (full project), or one REQ is finished."""
    settings = load_settings()
    store = StateStore(settings.state_file)
    gh = GhClient(repo=settings.github_repo)
    orchestrator = Orchestrator(settings=settings, store=store, gh=gh)
    cap = int(os.getenv("AUTOMATION_MAX_ROUNDS", str(max_rounds)))

    for round_i in range(cap):
        state = store.load()
        if req_id:
            rec = next((r for r in state.requirements if r.req_id == req_id), None)
            if rec is None:
                print(f"[red]Unknown --req-id {req_id}[/red]")
                raise typer.Exit(1)
            if rec.state in (ReqState.DONE, ReqState.BLOCKED):
                print(f"[green]{req_id} → {rec.state.value}; stopping.[/green]")
                break
            if rec.state == ReqState.PENDING:
                print(
                    f"[yellow]{req_id} is PENDING (dependencies or not READY); cannot advance. Stopping.[/yellow]"
                )
                break
            if rec.state not in (ReqState.READY, ReqState.FIXING):
                print(
                    f"[yellow]{req_id} is {rec.state.value} (resume not implemented); run manually or fix state. Stopping.[/yellow]"
                )
                break
            print(
                f"[cyan]Round {round_i + 1}/{cap}: run-once --req-id {req_id} "
                f"(current={rec.state.value})[/cyan]"
            )
        else:
            work = [r.req_id for r in state.requirements if r.state in (ReqState.READY, ReqState.FIXING)]
            if not work:
                print(f"[green]No READY/FIXING left; done after {round_i} round(s).[/green]")
                break
            print(f"[cyan]Round {round_i + 1}/{cap}: run-once (READY/FIXING: {work})[/cyan]")

        orchestrator.run_once(req_id=req_id)
    else:
        print(f"[yellow]Stopped: reached max rounds cap ({cap})[/yellow]")

    final = store.load()
    print(json.dumps(final.model_dump(), indent=2))


@app.command("init-state")
def init_state() -> None:
    settings = load_settings()
    template = "state/req-status.example.json"
    data = open(template, "r", encoding="utf-8").read()
    settings.state_file.parent.mkdir(parents=True, exist_ok=True)
    settings.state_file.write_text(data, encoding="utf-8")
    print(f"[green]Initialized state file:[/green] {settings.state_file}")


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

app = typer.Typer(help="基于 CrewAI 的确定性多智能体交付流水线。")


@app.command("run-once")
def run_once(
    req_id: str | None = typer.Option(default=None, help="只处理指定的 REQ 编号"),
) -> None:
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
        help="只推进该 REQ 直至完成/阻塞/等待依赖；省略则处理全部 READY/FIXING",
    ),
    max_rounds: int = typer.Option(
        200,
        "--max-rounds",
        help="安全上限（每轮 = 选中一个 REQ 跑完整流水线一步）",
    ),
) -> None:
    """反复执行 run-once，直到没有 READY/FIXING（全项目），或单个 REQ 结束。"""
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
                print(f"[red]未知的 --req-id：{req_id}[/red]")
                raise typer.Exit(1)
            if rec.state in (ReqState.DONE, ReqState.BLOCKED):
                print(f"[green]{req_id} → {rec.state.value}；已结束。[/green]")
                break
            if rec.state == ReqState.PENDING:
                print(
                    f"[yellow]{req_id} 为 PENDING（依赖未满足或未 READY），无法推进。已停止。[/yellow]"
                )
                break
            if rec.state not in (ReqState.READY, ReqState.FIXING):
                print(
                    f"[yellow]{req_id} 当前为 {rec.state.value}（未实现从此状态自动恢复）；请人工处理或修正状态。已停止。[/yellow]"
                )
                break
            print(
                f"[cyan]第 {round_i + 1}/{cap} 轮：run-once --req-id {req_id} "
                f"（当前={rec.state.value}）[/cyan]"
            )
        else:
            work = [
                r.req_id for r in state.requirements if r.state in (ReqState.READY, ReqState.FIXING)
            ]
            if not work:
                print(f"[green]已无 READY/FIXING，共 {round_i} 轮后结束。[/green]")
                break
            print(f"[cyan]第 {round_i + 1}/{cap} 轮：run-once（READY/FIXING：{work}）[/cyan]")

        orchestrator.run_once(req_id=req_id)
    else:
        print(f"[yellow]已停止：达到最大轮数上限（{cap}）[/yellow]")

    final = store.load()
    print(json.dumps(final.model_dump(), indent=2))


@app.command("init-state")
def init_state() -> None:
    settings = load_settings()
    template = "state/req-status.example.json"
    data = open(template, "r", encoding="utf-8").read()
    settings.state_file.parent.mkdir(parents=True, exist_ok=True)
    settings.state_file.write_text(data, encoding="utf-8")
    print(f"[green]已初始化状态文件：[/green] {settings.state_file}")

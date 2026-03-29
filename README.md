# MasterCoder Automation (CrewAI)

Deterministic multi-agent software delivery framework built with CrewAI.

**详细教程（环境变量、冒烟测试、`mc-auto`、评审结论与已知缺口）：** [docs/automation-tutorial.md](docs/automation-tutorial.md)

**`mastercoder_automation` 包结构、设计原因、依赖与全新 Ubuntu 搭建：** [docs/mastercoder-automation.md](docs/mastercoder-automation.md)

## What it provides

- Deterministic REQ state machine (`PENDING -> READY -> DEVELOPING -> REVIEWING -> TESTING -> DONE/FIXING/BLOCKED`)
- Three role agents (Dev, Review, QA) powered by CrewAI
- Objective quality gates (`ruff`, `pytest`, coverage threshold)
- `gh` CLI integration for branch/PR/review/comment/merge operations
- JSON state store for resumable pipeline execution
- GitHub Actions workflow entrypoint

## Quick start（开跑）

前置条件：**已安装 `git` 与 [GitHub CLI `gh`](https://cli.github.com/)**（在 PATH 中可执行）。

```bash
cd /path/to/MasterCoder
python3 -m pip install -e ".[dev]"
source .env.sh
export REPO_ROOT="$(pwd)"
export GITHUB_REPO="your-org/your-repo"

cp state/req-status.example.json state/req-status.json
# 编辑 state/req-status.json：将要做的 REQ 标为 READY

python3 scripts/crewai_glm_smoke.py
python3 scripts/crewai_github_pat_smoke.py

mc-auto run-once --req-id REQ-01
```

本机固定路径：**`./run-automation.sh`** 默认 **`mc-auto run-all`**（无冒烟），按 `state/req-status.json` 反复推进所有 `READY`/`FIXING` 的 REQ，直到做完或达到 `--max-rounds`。指定单个 REQ：`./run-automation.sh REQ-01`。可选：`--once` 只跑一轮，`--smoke` 先跑冒烟。详见脚本注释。

完整清单、严格真人 Review/QA、排错：**[docs/automation-tutorial.md](docs/automation-tutorial.md)** §0。

## Required environment variables

- `OPENAI_API_KEY` (or your OpenAI-compatible key supported by CrewAI)
- `OPENAI_API_BASE_URL` (for OpenAI-compatible providers such as Zhipu)
- `MODEL_NAME` (default: `gpt-4o-mini`)
- `GITHUB_REPO` (for example: `xslkim/MasterCoder`)
- `REPO_ROOT` (Git working copy root for automation; default: current directory)
- `GIT_AGENT_TOKEN_DEV` / `GIT_AGENT_USERNAME_DEV` / `GIT_AGENT_EMAIL_DEV` (push + PR + commit identity)
- `GIT_AGENT_TOKEN_REVIEW` + `GIT_AGENT_USERNAME_REVIEW` (post `gh pr review` as Review account, or human poll)
- `GIT_AGENT_TOKEN_TEST` + `GIT_AGENT_USERNAME_TEST` (post QA comment, or human poll)
- Optional: `GIT_AGENT_TOKEN_MERGE`, `AUTOMATION_STRICT_HUMAN_REVIEW`, `AUTOMATION_STRICT_HUMAN_QA` — see [docs/automation-tutorial.md](docs/automation-tutorial.md)
- `COVERAGE_MIN` (default: `80`)

## Notes

- This framework is deterministic at workflow level. LLM output is advisory and constrained by fixed gates.
- It does not replace CI checks; it orchestrates when and how checks run.
- Before a REQ can enter `TESTING`, the Review step must also approve the newly added or modified `tests/` cases.

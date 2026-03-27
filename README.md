# MasterCoder Automation (CrewAI)

Deterministic multi-agent software delivery framework built with CrewAI.

**详细教程（环境变量、冒烟测试、`mc-auto`、评审结论与已知缺口）：** [docs/automation-tutorial.md](docs/automation-tutorial.md)

## What it provides

- Deterministic REQ state machine (`PENDING -> READY -> DEVELOPING -> REVIEWING -> TESTING -> DONE/FIXING/BLOCKED`)
- Three role agents (Dev, Review, QA) powered by CrewAI
- Objective quality gates (`ruff`, `pytest`, coverage threshold)
- `gh` CLI integration for branch/PR/review/comment/merge operations
- JSON state store for resumable pipeline execution
- GitHub Actions workflow entrypoint

## Quick start

```bash
pip install -e ".[dev]"
source .env.sh
cp state/req-status.example.json state/req-status.json
mc-auto run-once --req-id REQ-01
```

## Required environment variables

- `OPENAI_API_KEY` (or your OpenAI-compatible key supported by CrewAI)
- `OPENAI_API_BASE_URL` (for OpenAI-compatible providers such as Zhipu)
- `MODEL_NAME` (default: `gpt-4o-mini`)
- `GITHUB_REPO` (for example: `xslkim/MasterCoder`)
- `REPO_ROOT` (Git working copy root for automation; default: current directory)
- `GIT_AGENT_TOKEN_DEV` / `GIT_AGENT_USERNAME_DEV` / `GIT_AGENT_EMAIL_DEV` (push + PR + commit identity)
- `COVERAGE_MIN` (default: `80`)

## Notes

- This framework is deterministic at workflow level. LLM output is advisory and constrained by fixed gates.
- It does not replace CI checks; it orchestrates when and how checks run.

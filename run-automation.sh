#!/usr/bin/env bash
# 本机一键开跑完整流水线：加载 .env.sh，设置 REPO_ROOT / GITHUB_REPO，默认不冒烟，反复 mc-auto 直到无 READY/FIXING。
# 用法：
#   ./run-automation.sh                      # run-all（整份 state 里所有可推进的 REQ）
#   ./run-automation.sh REQ-01               # run-all 只盯一个 REQ 直到 DONE/BLOCKED/PENDING
#   ./run-automation.sh --req-id REQ-01      # 同上
#   ./run-automation.sh --once                 # 只跑一轮 run-once（自动挑一个）
#   ./run-automation.sh --once REQ-01          # 只跑一轮 run-once
#   ./run-automation.sh --smoke                # 先跑两个冒烟再 run-all
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

if [[ ! -f .env.sh ]]; then
  echo "error: 未找到 $ROOT/.env.sh，请先创建并填入密钥" >&2
  exit 1
fi

set -a
# shellcheck source=/dev/null
source ".env.sh"
set +a

export REPO_ROOT="$ROOT"
export GITHUB_REPO="${GITHUB_REPO:-xslkim/MasterCoder}"

RUN_SMOKE=0
MC_MODE="all"
REQ_ID=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --smoke)
      RUN_SMOKE=1
      shift
      ;;
    --once)
      MC_MODE="once"
      shift
      ;;
    --req-id)
      [[ $# -ge 2 ]] || { echo "error: --req-id 需要参数" >&2; exit 1; }
      REQ_ID="$2"
      shift 2
      ;;
    -h | --help)
      echo "用法: $0 [--smoke] [--once] [--req-id REQ-XX] [REQ-XX]"
      exit 0
      ;;
    *)
      REQ_ID="$1"
      shift
      ;;
  esac
done

if [[ "$RUN_SMOKE" -eq 1 ]]; then
  echo "=== 冒烟: LLM (CrewAI) ==="
  python3 scripts/crewai_glm_smoke.py
  echo "=== 冒烟: GitHub PAT (三账号) ==="
  python3 scripts/crewai_github_pat_smoke.py
fi

if [[ "$MC_MODE" == "once" ]]; then
  echo "=== mc-auto run-once (REPO_ROOT=$REPO_ROOT GITHUB_REPO=$GITHUB_REPO) ==="
  if [[ -n "$REQ_ID" ]]; then
    exec mc-auto run-once --req-id "$REQ_ID"
  else
    exec mc-auto run-once
  fi
else
  echo "=== mc-auto run-all (REPO_ROOT=$REPO_ROOT GITHUB_REPO=$GITHUB_REPO) ==="
  if [[ -n "$REQ_ID" ]]; then
    exec mc-auto run-all --req-id "$REQ_ID"
  else
    exec mc-auto run-all
  fi
fi

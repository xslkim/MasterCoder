#!/usr/bin/env bash
# 本机一键开跑：加载 .env.sh，设置 REPO_ROOT / GITHUB_REPO，可选冒烟，再执行 mc-auto。
# 用法：
#   ./run-automation.sh                    # 冒烟 + 自动选第一个 READY/FIXING 的 REQ
#   ./run-automation.sh REQ-01             # 冒烟 + 只跑 REQ-01
#   ./run-automation.sh --req-id REQ-01    # 同上
#   ./run-automation.sh --no-smoke REQ-01  # 跳过冒烟
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

RUN_SMOKE=1
REQ_ID=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-smoke)
      RUN_SMOKE=0
      shift
      ;;
    --req-id)
      [[ $# -ge 2 ]] || { echo "error: --req-id 需要参数" >&2; exit 1; }
      REQ_ID="$2"
      shift 2
      ;;
    -h | --help)
      echo "用法: $0 [--no-smoke] [--req-id REQ-XX] [REQ-XX]"
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

echo "=== mc-auto run-once (REPO_ROOT=$REPO_ROOT GITHUB_REPO=$GITHUB_REPO) ==="
if [[ -n "$REQ_ID" ]]; then
  exec mc-auto run-once --req-id "$REQ_ID"
else
  exec mc-auto run-once
fi

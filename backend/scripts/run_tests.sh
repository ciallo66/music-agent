#!/usr/bin/env bash
# 跑后端全盘测试。
#
# 测试需要一个独立的 PostgreSQL 库（tests/conftest.py 禁止连开发库）。本脚本会临时起一个
# pgvector 容器（独立命名、跑完即删），跑完自动清理，不触碰项目的数据卷与运行中的容器。
#
# 用法：
#   bash scripts/run_tests.sh                 # 跑全盘
#   bash scripts/run_tests.sh tests/test_agent.py -v   # 只跑指定文件，参数原样透传给 pytest
#
# 可用环境变量覆盖：TEST_DB_PORT（默认 55432）、TEST_DB_IMAGE、TEST_DB_CONTAINER。
set -euo pipefail

BACKEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$BACKEND_DIR"

IMAGE="${TEST_DB_IMAGE:-pgvector/pgvector:pg16}"
CONTAINER="${TEST_DB_CONTAINER:-music-agent-test-db}"
PORT="${TEST_DB_PORT:-55432}"

if [ -x ".venv/Scripts/python.exe" ]; then
    PY=".venv/Scripts/python.exe"
elif [ -x ".venv/bin/python" ]; then
    PY=".venv/bin/python"
else
    echo "未找到虚拟环境，请先在 backend 目录创建 .venv 并安装依赖" >&2
    exit 1
fi

cleanup() {
    docker stop "$CONTAINER" >/dev/null 2>&1 || true
}
trap cleanup EXIT

docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
PASSWORD="$("$PY" -c 'import secrets; print(secrets.token_urlsafe(16))')"
docker run -d --rm --name "$CONTAINER" \
    -e POSTGRES_PASSWORD="$PASSWORD" \
    -e POSTGRES_USER=postgres \
    -e POSTGRES_DB=music_agent_test \
    -p "127.0.0.1:${PORT}:5432" \
    "$IMAGE" >/dev/null

echo "等待临时测试库就绪（端口 ${PORT}）…"
for _ in $(seq 1 30); do
    if docker exec "$CONTAINER" pg_isready -U postgres -d music_agent_test >/dev/null 2>&1; then
        break
    fi
    sleep 2
done

export TEST_DATABASE_URL="postgresql+psycopg://postgres:${PASSWORD}@127.0.0.1:${PORT}/music_agent_test"
"$PY" -m pytest -o addopts="" -q --tb=short "$@"

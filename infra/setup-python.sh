#!/bin/bash
set -e

# ============================================================
# Python 환경 설정 (SageMaker Code Editor용)
# 사용법: ./infra/setup-python.sh
# ============================================================

echo "🐍 Python 환경 설정..."

cd "$(dirname "$0")/../starter-code"

# venv 생성
python3 -m venv .venv
source .venv/bin/activate

# 패키지 설치
pip install --upgrade pip -q
pip install -r requirements.txt -q

# Playwright (Browser Tool)
playwright install chromium 2>/dev/null || echo "⚠️  Playwright chromium 설치 실패 (Phase 2에서 필요, 지금은 무시 가능)"

echo ""
echo "✅ Python 환경 설정 완료!"
echo ""
echo "활성화: source starter-code/.venv/bin/activate"

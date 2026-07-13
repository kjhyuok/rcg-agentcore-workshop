#!/bin/bash
# ============================================================
# AgentCore Runtime 배포 스크립트
# Usage: ./scripts/deploy-agent.sh <agent_file> <agent_name>
# Example: ./scripts/deploy-agent.sh agents/phase1_recommend.py rcg_recommend_agent
# ============================================================

set -e

# zip 유틸리티 설치 (SageMaker Code Editor에 없을 수 있음)
sudo apt-get install -y zip 2>/dev/null || true

# Deprecated warning 억제
export AGENTCORE_SUPPRESS_RECOMMENDATION=1

AGENT_FILE=${1:-"agents/phase1_recommend.py"}
AGENT_NAME=${2:-"rcg_recommend_agent"}
REGION=${AWS_REGION:-"us-east-1"}

if [ -z "${RUNTIME_ROLE_ARN}" ]; then
  echo "❌ RUNTIME_ROLE_ARN 환경변수가 설정되지 않았습니다."
  echo "   먼저 실행: source ~/workshop/.env.\${PARTICIPANT_ID}"
  echo "   (셋업이 처음이라면: bash infra/onestop.sh 먼저 실행)"
  exit 1
fi

echo "🚀 AgentCore Runtime 배포"
echo "   Agent: ${AGENT_FILE}"
echo "   Name:  ${AGENT_NAME}"
echo "   Region: ${REGION}"
echo "================================"

# 1. Configure
echo "⚙️  agentcore configure..."
agentcore configure \
  --entrypoint "${AGENT_FILE}" \
  --name "${AGENT_NAME}" \
  --runtime PYTHON_3_12 \
  --deployment-type direct_code_deploy \
  --execution-role "${RUNTIME_ROLE_ARN}" \
  --disable-memory \
  --non-interactive

# 2. Deploy
echo "📦 agentcore deploy..."
agentcore deploy \
  --env AGENTCORE_GATEWAY_URL="${AGENTCORE_GATEWAY_URL}" \
  --env AGENTCORE_MEMORY_ID="${AGENTCORE_MEMORY_ID}" \
  --env AWS_REGION="${REGION}" \
  --env AGENT_OBSERVABILITY_ENABLED=true \
  --auto-update-on-conflict

echo ""
echo "✅ 배포 완료!"
echo "================================"
echo "엔드포인트 확인:"
agentcore status --agent "${AGENT_NAME}"

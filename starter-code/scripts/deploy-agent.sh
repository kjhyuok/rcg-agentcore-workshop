#!/bin/bash
# ============================================================
# AgentCore Runtime 배포 스크립트
# Usage: ./scripts/deploy-agent.sh <agent_file> <agent_name>
# Example: ./scripts/deploy-agent.sh agents/phase1_recommend.py recommend-agent
# ============================================================

set -e

AGENT_FILE=${1:-"agents/phase1_recommend.py"}
AGENT_NAME=${2:-"rcg-recommend-agent"}
REGION=${AWS_REGION:-"us-east-1"}

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
  --deployment-type direct_code_deploy

# 2. Deploy
echo "📦 agentcore deploy..."
agentcore deploy \
  --env AGENTCORE_GATEWAY_URL="${AGENTCORE_GATEWAY_URL}" \
  --env AGENTCORE_MEMORY_ID="${AGENTCORE_MEMORY_ID}" \
  --env AWS_REGION="${REGION}" \
  --auto-update-on-conflict

echo ""
echo "✅ 배포 완료!"
echo "================================"
echo "엔드포인트 확인:"
agentcore status --name "${AGENT_NAME}"

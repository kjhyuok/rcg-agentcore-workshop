#!/bin/bash
# ============================================================
# AgentCore Runtime 배포 스크립트 (npm @aws/agentcore CLI)
# Usage: ./scripts/deploy-agent.sh <phase>
# Example: ./scripts/deploy-agent.sh phase1
# ============================================================

set -e

PHASE=${1:-"phase1"}
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BASE_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
AGENT_DIR="${BASE_DIR}/agents/${PHASE}"

if [ ! -d "${AGENT_DIR}" ]; then
  echo "Error: ${AGENT_DIR} does not exist"
  echo "Available phases: phase1, phase2a, phase2b, phase3"
  exit 1
fi

# Resolve AWS account ID and inject into aws-targets.json
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION=${AWS_REGION:-"us-west-2"}
TARGETS_FILE="${AGENT_DIR}/agentcore/aws-targets.json"

cat > "${TARGETS_FILE}" << EOF
[
  {
    "name": "default",
    "account": "${ACCOUNT_ID}",
    "region": "${REGION}"
  }
]
EOF

# Install CDK dependencies if needed
CDK_DIR="${AGENT_DIR}/agentcore/cdk"
if [ -d "${CDK_DIR}" ] && [ ! -d "${CDK_DIR}/node_modules" ]; then
  echo "Installing CDK dependencies..."
  cd "${CDK_DIR}" && npm install --silent
fi

echo "AgentCore Runtime Deploy"
echo "   Phase:   ${PHASE}"
echo "   Account: ${ACCOUNT_ID}"
echo "   Region:  ${REGION}"
echo "================================"

cd "${AGENT_DIR}"
agentcore deploy -y

echo ""
echo "Deploy complete!"
echo "================================"
echo ""
echo "Test:"
echo "  cd agents/${PHASE} && agentcore invoke --prompt \"test message\""
echo ""
echo "Local dev:"
echo "  cd agents/${PHASE} && agentcore dev"

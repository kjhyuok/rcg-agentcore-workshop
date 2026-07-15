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

cat > "${TARGETS_FILE}" << TARGETSEOF
[
  {
    "name": "default",
    "account": "${ACCOUNT_ID}",
    "region": "${REGION}"
  }
]
TARGETSEOF

# Inject runtime env vars (AGENTCORE_GATEWAY_URL, AGENTCORE_MEMORY_ID, MOCK_SITE_URL, AWS_REGION)
# into agentcore.json — the CDK migration dropped the old --env flag, so this is
# the equivalent for the new agentcore.json/CDK-based deploy.
AGENTCORE_JSON="${AGENT_DIR}/agentcore/agentcore.json"
AGENTCORE_GATEWAY_URL="${AGENTCORE_GATEWAY_URL:-}" \
AGENTCORE_MEMORY_ID="${AGENTCORE_MEMORY_ID:-}" \
MOCK_SITE_URL="${MOCK_SITE_URL:-}" \
AWS_REGION="${REGION}" \
python3.12 - "${AGENTCORE_JSON}" << 'PYEOF'
import json
import os
import sys

path = sys.argv[1]
with open(path) as f:
    cfg = json.load(f)

env_map = {
    "AGENTCORE_GATEWAY_URL": os.environ.get("AGENTCORE_GATEWAY_URL", ""),
    "AGENTCORE_MEMORY_ID": os.environ.get("AGENTCORE_MEMORY_ID", ""),
    "MOCK_SITE_URL": os.environ.get("MOCK_SITE_URL", ""),
    "AWS_REGION": os.environ.get("AWS_REGION", ""),
}
env_vars = [{"name": k, "value": v} for k, v in env_map.items() if v]

for rt in cfg.get("runtimes", []):
    rt["envVars"] = env_vars

with open(path, "w") as f:
    json.dump(cfg, f, indent=2)
    f.write("\n")

print(f"Injected env vars into {path}: {[e['name'] for e in env_vars]}")
PYEOF

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

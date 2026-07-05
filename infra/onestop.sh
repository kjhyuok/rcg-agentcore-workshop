#!/bin/bash
set -e

# ============================================================
# RCG AgentCore Workshop — 원스톱 인프라 배포
# 사용법: ./infra/onestop.sh [PARTICIPANT_ID]
# 예시:   ./infra/onestop.sh w001
# ============================================================

PID="${1:-w001}"
REGION="${AWS_REGION:-us-east-1}"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
PREFIX="rcg-workshop"
ROLE_NAME="${PREFIX}-lambda-role"
ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}"
GW_ROLE_NAME="${PREFIX}-gateway-role"
GW_ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${GW_ROLE_NAME}"

echo "╔══════════════════════════════════════════════════════════╗"
echo "║  🚀 RCG AgentCore Workshop — 원스톱 배포                ║"
echo "╠══════════════════════════════════════════════════════════╣"
echo "║  Participant ID : ${PID}"
echo "║  Region         : ${REGION}"
echo "║  Account        : ${ACCOUNT_ID}"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# ============================================================
# 1. IAM Role 생성 (Lambda 실행용)
# ============================================================
echo "[1/4] IAM Role 생성..."

# Lambda Role
aws iam create-role \
  --role-name "${ROLE_NAME}" \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "lambda.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }' 2>/dev/null && echo "  ✅ ${ROLE_NAME} 생성" || echo "  ℹ️  ${ROLE_NAME} 이미 존재"

aws iam attach-role-policy \
  --role-name "${ROLE_NAME}" \
  --policy-arn "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole" 2>/dev/null || true

# Gateway Role (AgentCore가 Lambda를 호출할 수 있도록)
aws iam create-role \
  --role-name "${GW_ROLE_NAME}" \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "bedrock-agentcore.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }' 2>/dev/null && echo "  ✅ ${GW_ROLE_NAME} 생성" || echo "  ℹ️  ${GW_ROLE_NAME} 이미 존재"

aws iam put-role-policy \
  --role-name "${GW_ROLE_NAME}" \
  --policy-name "InvokeLambdaPolicy" \
  --policy-document "{
    \"Version\": \"2012-10-17\",
    \"Statement\": [{
      \"Effect\": \"Allow\",
      \"Action\": \"lambda:InvokeFunction\",
      \"Resource\": \"arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:${PREFIX}-*\"
    }]
  }" 2>/dev/null || true

echo "  ⏳ IAM 전파 대기 (30초)..."
sleep 30

# ============================================================
# 2. Lambda 11개 배포
# ============================================================
echo ""
echo "[2/4] Lambda 11개 배포..."

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LAMBDA_DIR="${SCRIPT_DIR}/../starter-code/lambdas"

LAMBDAS=(
  "customer_profile:customer-profile"
  "product_search:product-search"
  "purchase_history:purchase-history"
  "cs_lookup_order:cs-lookup-order"
  "cs_return_policy:cs-return-policy"
  "cs_process_return:cs-process-return"
  "cs_delivery_status:cs-delivery-status"
  "demand_inventory:demand-inventory"
  "demand_sales_trend:demand-sales-trend"
  "demand_external_factors:demand-external-factors"
  "demand_purchase_order:demand-purchase-order"
)

for entry in "${LAMBDAS[@]}"; do
  DIR_NAME="${entry%%:*}"
  FUNC_NAME="${PREFIX}-${entry##*:}"

  # Zip
  cd "${LAMBDA_DIR}/${DIR_NAME}"
  zip -q /tmp/${FUNC_NAME}.zip index.py
  cd - > /dev/null

  # Create or Update
  if aws lambda get-function --function-name "${FUNC_NAME}" --region "${REGION}" > /dev/null 2>&1; then
    aws lambda update-function-code \
      --function-name "${FUNC_NAME}" \
      --zip-file "fileb:///tmp/${FUNC_NAME}.zip" \
      --region "${REGION}" > /dev/null 2>&1
    echo "  🔄 ${FUNC_NAME} (업데이트)"
  else
    aws lambda create-function \
      --function-name "${FUNC_NAME}" \
      --runtime python3.12 \
      --handler index.handler \
      --role "${ROLE_ARN}" \
      --zip-file "fileb:///tmp/${FUNC_NAME}.zip" \
      --timeout 30 \
      --memory-size 128 \
      --region "${REGION}" > /dev/null 2>&1
    echo "  ✅ ${FUNC_NAME} (생성)"
  fi

  rm -f /tmp/${FUNC_NAME}.zip
done

# ============================================================
# 3. Mock 사이트 S3 배포
# ============================================================
echo ""
echo "[3/4] Mock 사이트 배포..."

MOCK_BUCKET="${PREFIX}-mock-${ACCOUNT_ID}"
MOCK_DIR="${SCRIPT_DIR}/../mock-sites"

aws s3 mb "s3://${MOCK_BUCKET}" --region "${REGION}" 2>/dev/null || true

aws s3 sync "${MOCK_DIR}/" "s3://${MOCK_BUCKET}/" \
  --content-type "text/html" \
  --region "${REGION}" > /dev/null 2>&1

# S3 website 설정
aws s3 website "s3://${MOCK_BUCKET}" --index-document competitor-prices.html --region "${REGION}" 2>/dev/null || true

MOCK_URL="http://${MOCK_BUCKET}.s3-website-${REGION}.amazonaws.com"
echo "  ✅ Mock 사이트: ${MOCK_URL}"

# ============================================================
# 4. 환경변수 출력
# ============================================================
echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  🎉 배포 완료! 아래 환경변수를 설정하세요               ║"
echo "╠══════════════════════════════════════════════════════════╣"
echo ""
echo "  export AWS_REGION=${REGION}"
echo "  export ACCOUNT_ID=${ACCOUNT_ID}"
echo "  export PARTICIPANT_ID=${PID}"
echo "  export MOCK_SITE_URL=${MOCK_URL}"
echo "  export GATEWAY_ROLE_ARN=${GW_ROLE_ARN}"
echo ""
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "다음 단계: Phase 1 → python3 scripts/setup-gateway.py"

# Save env to file for later
cat > "${SCRIPT_DIR}/../.env.${PID}" << EOF
export AWS_REGION=${REGION}
export ACCOUNT_ID=${ACCOUNT_ID}
export PARTICIPANT_ID=${PID}
export MOCK_SITE_URL=${MOCK_URL}
export GATEWAY_ROLE_ARN=${GW_ROLE_ARN}
EOF

echo ""
echo "💡 환경변수 복구: source .env.${PID}"

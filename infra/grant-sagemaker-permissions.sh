#!/bin/bash
set -e

# ============================================================
# SageMaker Code Editor Role에 Bedrock + AgentCore 권한 추가
# CloudShell에서 실행합니다.
# ============================================================

REGION="${AWS_REGION:-us-east-1}"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

echo "🔐 SageMaker Code Editor 권한 설정"
echo "   Account: ${ACCOUNT_ID}"
echo "   Region:  ${REGION}"
echo ""

# ============================================================
# 1. SageMaker Execution Role 찾기
# ============================================================
echo "[1/2] SageMaker Execution Role 탐색..."

# SageMaker Domain의 Execution Role 찾기
SM_ROLE_ARN=$(aws sagemaker list-domains --region ${REGION} \
  --query 'Domains[0].DefaultUserSettings.ExecutionRole // Domains[0].{r: DomainId}' \
  --output text 2>/dev/null || true)

if [ -z "$SM_ROLE_ARN" ] || [ "$SM_ROLE_ARN" = "None" ]; then
    # Domain에서 직접 가져오기
    DOMAIN_ID=$(aws sagemaker list-domains --region ${REGION} \
      --query 'Domains[0].DomainId' --output text 2>/dev/null)

    if [ -n "$DOMAIN_ID" ] && [ "$DOMAIN_ID" != "None" ]; then
        SM_ROLE_ARN=$(aws sagemaker describe-domain --domain-id ${DOMAIN_ID} --region ${REGION} \
          --query 'DefaultUserSettings.ExecutionRole' --output text 2>/dev/null)
    fi
fi

if [ -z "$SM_ROLE_ARN" ] || [ "$SM_ROLE_ARN" = "None" ]; then
    echo "  ⚠️  SageMaker Domain을 찾을 수 없습니다."
    echo "  수동으로 Role ARN을 입력하세요:"
    echo "  (Console → SageMaker → Domains → 상세 → Execution Role 복사)"
    read -p "  Role ARN: " SM_ROLE_ARN
fi

SM_ROLE_NAME=$(echo "$SM_ROLE_ARN" | awk -F'/' '{print $NF}')
echo "  ✅ Role 찾음: ${SM_ROLE_NAME}"

# ============================================================
# 2. Bedrock + AgentCore 정책 추가
# ============================================================
echo ""
echo "[2/2] Bedrock + AgentCore 권한 추가..."

POLICY_NAME="RCGWorkshopBedrockAgentCoreAccess"

POLICY_DOC=$(cat <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "BedrockModelAccess",
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel",
                "bedrock:InvokeModelWithResponseStream",
                "bedrock:Converse",
                "bedrock:ConverseStream",
                "bedrock:ListFoundationModels",
                "bedrock:GetFoundationModel"
            ],
            "Resource": "*"
        },
        {
            "Sid": "MarketplaceModelSubscription",
            "Effect": "Allow",
            "Action": [
                "aws-marketplace:ViewSubscriptions",
                "aws-marketplace:Subscribe",
                "aws-marketplace:Unsubscribe"
            ],
            "Resource": "*"
        },
        {
            "Sid": "AgentCoreFullAccess",
            "Effect": "Allow",
            "Action": [
                "bedrock-agentcore:*"
            ],
            "Resource": "*"
        },
        {
            "Sid": "AgentCoreControlPlane",
            "Effect": "Allow",
            "Action": [
                "bedrock-agentcore-control:*"
            ],
            "Resource": "*"
        },
        {
            "Sid": "LambdaInvoke",
            "Effect": "Allow",
            "Action": [
                "lambda:InvokeFunction",
                "lambda:ListFunctions"
            ],
            "Resource": "arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:rcg-workshop-*"
        },
        {
            "Sid": "IAMPassRole",
            "Effect": "Allow",
            "Action": "iam:PassRole",
            "Resource": "arn:aws:iam::${ACCOUNT_ID}:role/rcg-workshop-*"
        },
        {
            "Sid": "S3MockSiteAccess",
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::rcg-workshop-mock-${ACCOUNT_ID}",
                "arn:aws:s3:::rcg-workshop-mock-${ACCOUNT_ID}/*"
            ]
        },
        {
            "Sid": "CloudWatchObservability",
            "Effect": "Allow",
            "Action": [
                "cloudwatch:GetMetricData",
                "cloudwatch:ListMetrics",
                "logs:GetLogEvents",
                "logs:FilterLogEvents",
                "logs:DescribeLogGroups",
                "xray:GetTraceSummaries",
                "xray:BatchGetTraces"
            ],
            "Resource": "*"
        }
    ]
}
EOF
)

aws iam put-role-policy \
  --role-name "${SM_ROLE_NAME}" \
  --policy-name "${POLICY_NAME}" \
  --policy-document "${POLICY_DOC}" 2>/dev/null \
  && echo "  ✅ 인라인 정책 추가: ${POLICY_NAME}" \
  || echo "  ❌ 정책 추가 실패 — 수동으로 추가 필요"

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  ✅ SageMaker 권한 설정 완료!                           ║"
echo "║                                                        ║"
echo "║  Code Editor에서 Bedrock + AgentCore 호출이             ║"
echo "║  가능합니다.                                            ║"
echo "╚══════════════════════════════════════════════════════════╝"

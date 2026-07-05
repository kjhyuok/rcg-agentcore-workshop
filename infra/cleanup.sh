#!/bin/bash

# ============================================================
# 리소스 정리
# 사용법: ./infra/cleanup.sh
# ============================================================

echo "🧹 RCG Workshop 리소스 정리"
echo "⚠️  이 작업은 되돌릴 수 없습니다. 계속? (y/N)"
read -r confirm
[[ "$confirm" != "y" ]] && echo "취소됨." && exit 0

REGION="${AWS_REGION:-us-east-1}"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
PREFIX="rcg-workshop"

echo ""
echo "[1/3] Lambda 삭제..."
aws lambda list-functions \
  --query "Functions[?starts_with(FunctionName, '${PREFIX}')].FunctionName" \
  --output text --region ${REGION} | tr '\t' '\n' | while read fn; do
  aws lambda delete-function --function-name "$fn" --region ${REGION} 2>/dev/null
  echo "  삭제: $fn"
done

echo ""
echo "[2/3] S3 Mock 사이트 삭제..."
BUCKET="${PREFIX}-mock-${ACCOUNT_ID}"
aws s3 rb "s3://${BUCKET}" --force --region ${REGION} 2>/dev/null && echo "  삭제: ${BUCKET}" || echo "  없음"

echo ""
echo "[3/3] IAM Role 삭제..."
for role in "${PREFIX}-lambda-role" "${PREFIX}-gateway-role"; do
  # Detach policies first
  aws iam list-attached-role-policies --role-name "$role" --query 'AttachedPolicies[].PolicyArn' --output text 2>/dev/null | tr '\t' '\n' | while read arn; do
    aws iam detach-role-policy --role-name "$role" --policy-arn "$arn" 2>/dev/null
  done
  aws iam delete-role-policy --role-name "$role" --policy-name "InvokeLambdaPolicy" 2>/dev/null || true
  aws iam delete-role --role-name "$role" 2>/dev/null && echo "  삭제: $role" || true
done

echo ""
echo "✅ 정리 완료"

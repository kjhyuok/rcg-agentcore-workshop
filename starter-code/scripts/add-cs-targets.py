"""
Phase 2A: CS Tool 4개를 기존 Gateway에 추가 등록
setup-gateway.py 이후에 실행합니다.
"""
import os
import json
import boto3

REGION = os.environ.get("AWS_REGION", "us-east-1")
ACCOUNT_ID = boto3.client("sts").get_caller_identity()["Account"]
GATEWAY_ID = os.environ.get("GATEWAY_ID", "")

if not GATEWAY_ID:
    print("❌ GATEWAY_ID 환경변수가 설정되지 않았습니다.")
    print("   먼저 실행: source ~/workshop/.env.w001")
    exit(1)

client = boto3.client("bedrock-agentcore-control", region_name=REGION)

# ============================================================
# CS Tool 4개 정의
# ============================================================
CS_TARGETS = [
    {
        "name": "cs-lookup-order",
        "lambda_name": "rcg-workshop-cs-lookup-order",
        "description": "주문번호로 주문 상세 조회. 주문 상태, 상품목록, 결제금액, 배송정보를 반환한다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string", "description": "주문번호 (예: ORD-2024-001)"}
            },
            "required": ["order_id"],
        },
    },
    {
        "name": "cs-return-policy",
        "lambda_name": "rcg-workshop-cs-return-policy",
        "description": "상품 카테고리별 반품/교환 정책 조회. 반품 가능 기한, 조건, 환불 방식을 반환한다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {"type": "string", "description": "상품 카테고리 (예: 식품, 화장품, 전자기기)"}
            },
            "required": ["category"],
        },
    },
    {
        "name": "cs-process-return",
        "lambda_name": "rcg-workshop-cs-process-return",
        "description": "반품/환불 처리 요청. 사유와 금액을 기반으로 처리하며, 5만원 초과 시 needs_escalation=true를 반환한다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string", "description": "주문번호"},
                "reason": {"type": "string", "description": "반품 사유 (예: 상품불량, 단순변심, 오배송)"},
                "refund_amount": {"type": "number", "description": "환불 요청 금액 (원)"},
            },
            "required": ["order_id", "reason", "refund_amount"],
        },
    },
    {
        "name": "cs-delivery-status",
        "lambda_name": "rcg-workshop-cs-delivery-status",
        "description": "주문의 배송 추적 정보 조회. 현재 위치, 예상 도착일, 배송 단계를 반환한다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string", "description": "주문번호"}
            },
            "required": ["order_id"],
        },
    },
]

# ============================================================
# Gateway에 CS Target 등록
# ============================================================
print(f"📞 CS Tool Target 추가 등록 (Gateway: {GATEWAY_ID})")
print(f"   Account: {ACCOUNT_ID}")
print(f"   Region:  {REGION}")
print()

for target in CS_TARGETS:
    lambda_arn = f"arn:aws:lambda:{REGION}:{ACCOUNT_ID}:function:{target['lambda_name']}"
    tool_schema = {
        "name": target["name"].replace("-", "_"),
        "description": target["description"],
        "inputSchema": target["input_schema"],
    }

    try:
        client.create_gateway_target(
            gatewayIdentifier=GATEWAY_ID,
            name=target["name"],
            targetConfiguration={
                "mcp": {
                    "lambda": {
                        "lambdaArn": lambda_arn,
                        "toolSchema": {
                            "inlinePayload": [tool_schema]
                        },
                    }
                }
            },
            credentialProviderConfigurations=[{"credentialProviderType": "GATEWAY_IAM_ROLE"}],
        )
        print(f"  ✅ {target['name']} → {target['lambda_name']}")
    except client.exceptions.ConflictException:
        print(f"  ℹ️  {target['name']} 이미 등록됨")
    except Exception as e:
        print(f"  ❌ {target['name']} 실패: {e}")

print(f"\n{'='*50}")
print(f"🎉 CS Tool 4개 등록 완료!")
print(f"   Gateway에 총 7개 Tool 등록됨 (Phase 1: 3개 + Phase 2A: 4개)")
print(f"{'='*50}")

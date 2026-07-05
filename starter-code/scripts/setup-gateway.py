"""
Gateway 생성 + Target 등록 스크립트
참가자가 Phase 1에서 실행합니다.
Lambda는 사전 배포되어 있고, 이 스크립트로 Gateway에 등록합니다.
"""
import os
import json
import boto3

REGION = os.environ.get("AWS_REGION", "us-east-1")
ACCOUNT_ID = boto3.client("sts").get_caller_identity()["Account"]
GATEWAY_NAME = os.environ.get("GATEWAY_NAME", f"rcg-workshop-gw-{ACCOUNT_ID[-4:]}")
ROLE_ARN = os.environ.get("GATEWAY_ROLE_ARN", f"arn:aws:iam::{ACCOUNT_ID}:role/rcg-workshop-gateway-role")

client = boto3.client("bedrock-agentcore-control", region_name=REGION)

# ============================================================
# 1. Gateway 생성
# ============================================================
print(f"🔧 Gateway 생성: {GATEWAY_NAME}")

try:
    gw_resp = client.create_gateway(
        name=GATEWAY_NAME,
        roleArn=ROLE_ARN,
        protocolType="MCP",
        protocolConfiguration={
            "mcp": {"supportedVersions": ["2025-03-26"]}
        },
    )
    gateway_id = gw_resp["gatewayId"]
    print(f"✅ Gateway 생성 완료: {gateway_id}")
except client.exceptions.ConflictException:
    gws = client.list_gateways()
    gateway_id = next(g["gatewayId"] for g in gws["items"] if g["name"] == GATEWAY_NAME)
    print(f"ℹ️  Gateway 이미 존재: {gateway_id}")

# ============================================================
# 2. Phase 1 Tool Targets 등록
# ============================================================
PHASE1_TARGETS = [
    {
        "name": "customer-profile",
        "lambda_name": "rcg-workshop-customer-profile",
        "description": "고객 ID로 프로필(이름, 등급, 선호도, 알러지) 조회",
        "input_schema": {
            "type": "object",
            "properties": {"customer_id": {"type": "string", "description": "고객 ID (예: C001)"}},
            "required": ["customer_id"],
        },
    },
    {
        "name": "product-search",
        "lambda_name": "rcg-workshop-product-search",
        "description": "카테고리와 태그로 상품 검색. 재고 있는 상품만 반환합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {"type": "string", "description": "상품 카테고리 (건강식품, 음료, 뷰티, 간편식, 전자기기)"},
                "tags": {"type": "string", "description": "쉼표로 구분된 태그 (예: 고단백,유기농)"},
            },
        },
    },
    {
        "name": "purchase-history",
        "lambda_name": "rcg-workshop-purchase-history",
        "description": "고객의 최근 구매 이력 조회. 중복 추천 방지용.",
        "input_schema": {
            "type": "object",
            "properties": {"customer_id": {"type": "string", "description": "고객 ID (예: C001)"}},
            "required": ["customer_id"],
        },
    },
]

print(f"\n🔧 Phase 1 Target 등록 ({len(PHASE1_TARGETS)}개)")

for target in PHASE1_TARGETS:
    lambda_arn = f"arn:aws:lambda:{REGION}:{ACCOUNT_ID}:function:{target['lambda_name']}"
    tool_schema = {
        "name": target["name"].replace("-", "_"),
        "description": target["description"],
        "inputSchema": target["input_schema"],
    }

    try:
        client.create_gateway_target(
            gatewayIdentifier=gateway_id,
            name=target["name"],
            targetConfiguration={
                "mcp": {
                    "lambda": {
                        "lambdaArn": lambda_arn,
                        "toolSchema": {"inlinePayload": json.dumps(tool_schema)},
                    }
                }
            },
            credentialProviderConfigurations=[{"credentialProviderType": "GATEWAY_IAM_ROLE"}],
        )
        print(f"  ✅ {target['name']} → {lambda_arn}")
    except client.exceptions.ConflictException:
        print(f"  ℹ️  {target['name']} 이미 등록됨")
    except Exception as e:
        print(f"  ❌ {target['name']} 실패: {e}")

# ============================================================
# 3. Gateway URL 출력
# ============================================================
gw_info = client.get_gateway(gatewayIdentifier=gateway_id)
gateway_url = gw_info.get("gatewayUrl", f"https://{gateway_id}.gateway.agentcore.{REGION}.amazonaws.com")

print(f"\n{'='*50}")
print(f"🎉 Gateway 설정 완료!")
print(f"   Gateway ID:  {gateway_id}")
print(f"   Gateway URL: {gateway_url}")
print(f"\n   이 URL을 환경변수로 설정하세요:")
print(f"   export AGENTCORE_GATEWAY_URL={gateway_url}")
print(f"{'='*50}")

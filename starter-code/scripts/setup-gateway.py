"""
Gateway 생성 + Target 등록 스크립트
참가자가 Phase 1에서 실행합니다.
Lambda는 사전 배포되어 있고, 이 스크립트로 Gateway에 등록합니다.
"""
import os
import json
import time
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

gateway_id = None

# 먼저 기존 Gateway 확인
try:
    gws = client.list_gateways()
    for g in gws.get("items", []):
        if g["name"] == GATEWAY_NAME:
            gateway_id = g["gatewayId"]
            print(f"ℹ️  Gateway 이미 존재: {gateway_id}")
            break
except Exception:
    pass

if not gateway_id:
    # Gateway 생성 시도 (authorizerType 없이 먼저, 실패하면 NONE으로)
    create_params = dict(
        name=GATEWAY_NAME,
        roleArn=ROLE_ARN,
        protocolType="MCP",
        protocolConfiguration={"mcp": {"supportedVersions": ["2025-03-26"]}},
    )
    try:
        gw_resp = client.create_gateway(**create_params)
        gateway_id = gw_resp["gatewayId"]
        print(f"✅ Gateway 생성 완료: {gateway_id}")
    except Exception as e:
        if "authorizer" in str(e).lower() or "Authorizer" in str(e):
            print("  ℹ️  authorizerType 필요 — NONE으로 재시도...")
            create_params["authorizerType"] = "NONE"
            gw_resp = client.create_gateway(**create_params)
            gateway_id = gw_resp["gatewayId"]
            print(f"✅ Gateway 생성 완료: {gateway_id}")
        else:
            raise

# ============================================================
# 2. Gateway READY 대기
# ============================================================
print("  ⏳ Gateway 활성화 대기 중...")
for i in range(24):
    gw_info = client.get_gateway(gatewayIdentifier=gateway_id)
    status = gw_info.get("status", "")
    if status in ("READY", "ACTIVE"):
        print(f"  ✅ Gateway 상태: {status}")
        break
    if "FAIL" in status.upper():
        print(f"  ❌ Gateway 실패: {gw_info.get('statusReasons', '')}")
        break
    time.sleep(5)
else:
    print(f"  ⚠️  Gateway 상태: {status} (시간 초과, 계속 진행)")

# ============================================================
# 3. Phase 1 Tool Targets 등록
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
    # inlinePayload는 리스트 형태여야 함 (공식 가이드 확인)
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

# ============================================================
# 4. Gateway URL 출력
# ============================================================
gw_info = client.get_gateway(gatewayIdentifier=gateway_id)
gateway_url = gw_info.get("gatewayUrl", "")
if not gateway_url:
    gateway_url = f"https://{gateway_id}.gateway.agentcore.{REGION}.amazonaws.com"

print(f"\n{'='*50}")
print(f"🎉 Gateway 설정 완료!")
print(f"   Gateway ID:  {gateway_id}")
print(f"   Gateway URL: {gateway_url}")
print(f"\n   환경변수 설정:")
print(f"   export AGENTCORE_GATEWAY_URL={gateway_url}")
print(f"   export GATEWAY_ID={gateway_id}")
print(f"{'='*50}")

# .env.w001에 자동 추가
env_file = os.path.expanduser("~/workshop/.env.w001")
env_lines = {
    "AGENTCORE_GATEWAY_URL": gateway_url,
    "GATEWAY_ID": gateway_id,
}
try:
    existing = ""
    if os.path.exists(env_file):
        with open(env_file, "r") as f:
            existing = f.read()
    with open(env_file, "a") as f:
        for key, val in env_lines.items():
            if f"export {key}=" not in existing:
                f.write(f"export {key}={val}\n")
    print(f"\n   ✅ ~/workshop/.env.w001 에 자동 저장됨")
    print(f"      세션 재시작 시: source ~/workshop/.env.w001")
except Exception as e:
    print(f"\n   ⚠️  .env.w001 저장 실패 — 위 export 명령어를 수동 실행하세요")

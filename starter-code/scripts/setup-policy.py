"""
Policy Engine 생성 + Cedar 정책 등록 + Gateway 연결 스크립트
참가자가 Phase 2A Step 4에서 실행합니다.

AgentCore Policy는 Gateway를 통한 Tool 호출을 Cedar 정책으로 가로채(intercept)
허용/거부(ALLOW/DENY)합니다. 이 스크립트는 "환불(process_return) 금액이
50,000원을 초과하면 차단"하는 정책을 만들어, LLM이 System Prompt를 무시하고
고액 환불을 처리하려 해도 시스템 레벨에서 강제로 막습니다.

공식 API 참조 (boto3 bedrock-agentcore-control):
- create_policy_engine(name)
- create_policy(name, policyEngineId, definition={"cedar":{"statement": ...}})
- update_gateway(..., policyEngineConfiguration={"arn":..., "mode": "LOG_ONLY"|"ENFORCE"})

Cedar 참고:
- 우리 Gateway는 authorizerType=NONE(OAuth 아님) → principal은 제약 없이 두고
  Tool 입력값(context.input)만으로 판정한다.
- Cedar는 기본 Deny(default-deny). 따라서 "50,000원 이하만 permit"으로 쓰면
  50,000원 초과는 매칭되는 permit이 없어 자동으로 DENY된다.
- Action 이름 형식: "<TargetName>___<tool_name>" (언더스코어 3개).
  우리 target명 cs-process-return, tool명 cs_process_return(하이픈→언더스코어).
"""
import os
import time
import boto3

REGION = os.environ.get("AWS_REGION", "us-west-2")
GATEWAY_ID = os.environ.get("GATEWAY_ID", "")
# 안전을 위해 처음엔 LOG_ONLY(차단 없이 로그만). 검증 후 ENFORCE로 전환.
POLICY_MODE = os.environ.get("POLICY_MODE", "LOG_ONLY")

ACCOUNT_ID = boto3.client("sts").get_caller_identity()["Account"]
ENGINE_NAME = os.environ.get("POLICY_ENGINE_NAME", f"rcg_cs_policy_engine_{ACCOUNT_ID[-4:]}")

client = boto3.client("bedrock-agentcore-control", region_name=REGION)

if not GATEWAY_ID:
    raise SystemExit("❌ GATEWAY_ID 환경변수가 비어 있습니다. source ~/workshop/.env.w001 후 다시 실행하세요.")

# ============================================================
# 0. Gateway 정보 조회 (ARN + update_gateway에 필요한 기존 값)
# ============================================================
gw = client.get_gateway(gatewayIdentifier=GATEWAY_ID)
GATEWAY_ARN = gw["gatewayArn"]
print(f"🔗 Gateway: {gw['name']} ({GATEWAY_ARN})")

# process_return Tool의 Cedar Action 이름
ACTION = "cs-process-return___cs_process_return"

# ============================================================
# 1. Policy Engine 생성 (있으면 재사용)
# ============================================================
print(f"🛡️  Policy Engine 생성: {ENGINE_NAME}")
engine_id = None
engine_arn = None
try:
    for e in client.list_policy_engines().get("items", []):
        if e.get("name") == ENGINE_NAME:
            engine_id = e.get("policyEngineId")
            engine_arn = e.get("policyEngineArn")
            print(f"ℹ️  Policy Engine 이미 존재: {engine_id}")
            break
except Exception:
    pass

if not engine_id:
    resp = client.create_policy_engine(
        name=ENGINE_NAME,
        description="RCG Workshop — CS Agent 환불 가드레일(에스컬레이션) 정책 엔진",
    )
    engine_id = resp["policyEngineId"]
    engine_arn = resp["policyEngineArn"]
    print(f"✅ Policy Engine 생성: {engine_id}")

# ============================================================
# 2. Cedar 정책 등록 — "환불 50,000원 이하만 허용"
#    (초과분은 default-deny로 자동 차단 → Agent가 에스컬레이션 안내)
# ============================================================
CEDAR_STATEMENT = f'''permit(
  principal,
  action == AgentCore::Action::"{ACTION}",
  resource == AgentCore::Gateway::"{GATEWAY_ARN}"
)
when {{
  context.input has refund_amount &&
  context.input.refund_amount <= 50000
}};'''

print("📜 Cedar 정책 등록: 환불 50,000원 이하만 허용 (초과 시 차단)")
try:
    client.create_policy(
        name="RefundUnder50k",
        policyEngineId=engine_id,
        definition={"cedar": {"statement": CEDAR_STATEMENT}},
        description="process_return은 환불 금액 50,000원 이하일 때만 허용",
        validationMode="FAIL_ON_ANY_FINDINGS",
    )
    print("✅ 정책 등록 완료")
except Exception as e:
    if "already" in str(e).lower() or "conflict" in str(e).lower():
        print("ℹ️  정책 이미 존재")
    else:
        raise

# ============================================================
# 3. Gateway에 Policy Engine 연결 (LOG_ONLY로 시작)
# ============================================================
print(f"🔌 Gateway에 Policy Engine 연결 (mode={POLICY_MODE})")
client.update_gateway(
    gatewayIdentifier=GATEWAY_ID,
    name=gw["name"],
    roleArn=gw["roleArn"],
    protocolType=gw["protocolType"],
    authorizerType=gw["authorizerType"],
    policyEngineConfiguration={"arn": engine_arn, "mode": POLICY_MODE},
)
print("✅ 연결 완료")

print("")
print("=" * 60)
print("🎉 Policy 설정 완료!")
print(f"   Policy Engine: {engine_id}")
print(f"   Mode: {POLICY_MODE}")
print(f"   규칙: process_return 환불 > 50,000원 → 차단(default-deny)")
print("")
print("   다음: LOG_ONLY로 로그 확인 후, 아래로 ENFORCE 전환")
print(f"   POLICY_MODE=ENFORCE python3.12 scripts/setup-policy.py")
print("=" * 60)

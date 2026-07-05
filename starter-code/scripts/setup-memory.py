"""
Memory 생성 + Strategy 등록 스크립트
참가자가 Phase 2에서 실행합니다.
"""
import os
import boto3

REGION = os.environ.get("AWS_REGION", "us-east-1")
ACCOUNT_ID = boto3.client("sts").get_caller_identity()["Account"]
MEMORY_NAME = os.environ.get("MEMORY_NAME", f"rcg-workshop-memory-{ACCOUNT_ID[-4:]}")

client = boto3.client("bedrock-agentcore-control", region_name=REGION)

# ============================================================
# 1. Memory 생성
# ============================================================
print(f"🧠 Memory 생성: {MEMORY_NAME}")

try:
    mem_resp = client.create_memory(
        name=MEMORY_NAME,
        description="RCG Workshop — 고객 맥락 및 대화 이력 저장",
    )
    memory_id = mem_resp["memoryId"]
    print(f"✅ Memory 생성 완료: {memory_id}")
except client.exceptions.ConflictException:
    mems = client.list_memories()
    memory_id = next(m["memoryId"] for m in mems["items"] if m["name"] == MEMORY_NAME)
    print(f"ℹ️  Memory 이미 존재: {memory_id}")

# ============================================================
# 2. Strategy 등록 (3가지)
# ============================================================
print("\n🧠 Memory Strategy 등록")

strategies = [
    {
        "userPreferenceMemoryStrategy": {
            "name": "CustomerPreferences",
            "description": "고객의 반복적 선호, 알러지, 스타일을 기억",
            "namespaces": ["/preferences/{actorId}/"],
        }
    },
    {
        "summaryMemoryStrategy": {
            "name": "SessionSummaries",
            "description": "각 세션의 대화 요약을 저장",
            "namespaces": ["/summaries/{actorId}/{sessionId}/"],
        }
    },
    {
        "semanticMemoryStrategy": {
            "name": "DomainFacts",
            "description": "고객이 언급한 도메인 사실 (피부타입, 매장 위치 등)",
            "namespaces": ["/facts/{actorId}/"],
        }
    },
]

for strategy in strategies:
    try:
        client.update_memory_strategies(
            memoryId=memory_id,
            addStrategies=[strategy],
        )
        strategy_name = list(strategy.values())[0]["name"]
        print(f"  ✅ {strategy_name}")
    except Exception as e:
        strategy_name = list(strategy.values())[0]["name"]
        print(f"  ⚠️  {strategy_name}: {e}")

# ============================================================
# 3. 결과 출력
# ============================================================
print(f"\n{'='*50}")
print(f"🎉 Memory 설정 완료!")
print(f"   Memory ID: {memory_id}")
print(f"\n   이 ID를 환경변수로 설정하세요:")
print(f"   export AGENTCORE_MEMORY_ID={memory_id}")
print(f"{'='*50}")

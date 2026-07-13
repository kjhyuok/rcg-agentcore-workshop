"""
Memory 생성 + Strategy 등록 스크립트
참가자가 Phase 2에서 실행합니다.

공식 API 참조:
- Control plane: boto3.client("bedrock-agentcore-control")
- create_memory: name, eventExpiryDuration 필수
- strategies는 create_memory 또는 update_memory에서 설정
"""
import os
import time
import boto3

REGION = os.environ.get("AWS_REGION", "us-west-2")
ACCOUNT_ID = boto3.client("sts").get_caller_identity()["Account"]
MEMORY_NAME = os.environ.get("MEMORY_NAME", f"rcg-workshop-memory-{ACCOUNT_ID[-4:]}")

client = boto3.client("bedrock-agentcore-control", region_name=REGION)

# ============================================================
# 1. Memory 생성
# ============================================================
print(f"🧠 Memory 생성: {MEMORY_NAME}")

memory_id = None

# 기존 Memory 확인
try:
    mems = client.list_memories()
    for m in mems.get("items", mems.get("memories", [])):
        if m.get("name") == MEMORY_NAME:
            memory_id = m["memoryId"]
            print(f"ℹ️  Memory 이미 존재: {memory_id}")
            break
except Exception:
    pass

if not memory_id:
    # strategies를 create_memory에 포함 시도
    strategies = [
        {
            "semanticMemoryStrategy": {
                "name": "CustomerFacts",
                "namespaces": ["users/{actorId}/facts"],
            }
        },
        {
            "summaryMemoryStrategy": {
                "name": "SessionSummaries",
                "namespaces": ["users/{actorId}/summaries/{sessionId}"],
            }
        },
        {
            "userPreferenceMemoryStrategy": {
                "name": "CustomerPreferences",
                "namespaces": ["users/{actorId}/preferences"],
            }
        },
    ]

    try:
        mem_resp = client.create_memory(
            name=MEMORY_NAME,
            description="RCG Workshop — 고객 맥락 및 대화 이력 저장",
            eventExpiryDuration=30,
            strategies=strategies,
        )
        memory_id = mem_resp["memoryId"]
        print(f"✅ Memory 생성 완료: {memory_id}")
    except TypeError as e:
        # strategies 파라미터를 지원하지 않는 boto3 버전
        print(f"  ℹ️  strategies 파라미터 미지원, 기본 생성 후 update...")
        mem_resp = client.create_memory(
            name=MEMORY_NAME,
            description="RCG Workshop — 고객 맥락 및 대화 이력 저장",
            eventExpiryDuration=30,
        )
        memory_id = mem_resp["memoryId"]
        print(f"✅ Memory 생성 완료: {memory_id}")

        # update_memory로 strategies 추가
        try:
            client.update_memory(
                memoryId=memory_id,
                strategies=strategies,
            )
            print("  ✅ Strategies 추가 완료")
        except Exception as e2:
            print(f"  ⚠️  Strategies 추가 실패 (수동 설정 필요): {e2}")
    except Exception as e:
        print(f"  ❌ Memory 생성 실패: {e}")
        raise

# ============================================================
# 2. Memory READY 대기
# ============================================================
print("  ⏳ Memory 활성화 대기 중...")
for i in range(24):
    try:
        mem_info = client.get_memory(memoryId=memory_id)
        status = mem_info.get("status", "")
        if status in ("READY", "ACTIVE"):
            print(f"  ✅ Memory 상태: {status}")
            break
        if "FAIL" in status.upper():
            print(f"  ❌ Memory 실패: {mem_info.get('failureReason', '')}")
            break
    except Exception:
        pass
    time.sleep(5)
else:
    print(f"  ⚠️  Memory 상태: {status} (시간 초과, 계속 진행)")

# ============================================================
# 3. 결과 출력
# ============================================================
print(f"\n{'='*50}")
print(f"🎉 Memory 설정 완료!")
print(f"   Memory ID: {memory_id}")
print(f"\n   환경변수 설정:")
print(f"   export AGENTCORE_MEMORY_ID={memory_id}")
print(f"{'='*50}")

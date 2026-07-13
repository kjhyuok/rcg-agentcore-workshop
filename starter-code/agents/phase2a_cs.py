"""
Phase 2A: CS 자동화 Agent — AgentCore Native + Memory + Browser
참가자가 Phase 1 코드를 확장합니다.
Memory로 고객 문맥 유지, Browser로 경쟁사 가격 조회.
"""
import os
import json
import uuid
import threading
import boto3
from datetime import datetime, timezone
from strands import Agent
from strands.models import BedrockModel
from strands.tools.mcp import MCPClient
from mcp.client.streamable_http import streamablehttp_client
from bedrock_agentcore.runtime import BedrockAgentCoreApp

# ============================================================
# 환경변수
# ============================================================
GATEWAY_URL = os.environ.get("AGENTCORE_GATEWAY_URL", "")
MEMORY_ID = os.environ.get("AGENTCORE_MEMORY_ID", "")
REGION = os.environ.get("AWS_REGION", "us-east-1")

# ============================================================
# Memory Client (boto3 data plane)
# ============================================================
memory_client = boto3.client("bedrock-agentcore", region_name=REGION)

# ============================================================
# MCPClient는 모듈 로드 시 1회만 생성 (요청마다 새로 만들면 매번 핸드셰이크 비용)
#
# Browser Tool은 여전히 "지연" 생성하지만, 요청마다가 아니라 프로세스당 1회만
# 만들도록 싱글톤으로 캐싱합니다. import 시점에 즉시 생성하면 Playwright 초기화가
# Runtime의 30초 콜드스타트 타임아웃에 걸릴 수 있어(과거 실제로 겪은 문제),
# 첫 요청이 들어올 때 최초 1회만 만들고 이후 요청은 캐시된 인스턴스를 재사용합니다.
# ============================================================
mcp_client = MCPClient(lambda: streamablehttp_client(GATEWAY_URL))

_browser_tool = None
_browser_tool_lock = threading.Lock()


def get_browser_tool():
    global _browser_tool
    if _browser_tool is None:
        with _browser_tool_lock:
            if _browser_tool is None:
                from strands_tools.browser import AgentCoreBrowser
                _browser_tool = AgentCoreBrowser(region=REGION)
    return _browser_tool


# ============================================================
# System Prompt
# ============================================================
SYSTEM_PROMPT = """당신은 커머스 고객서비스(CS) 자동화 AI Agent입니다.

## 역할
- 고객의 주문 관련 문의를 처리합니다 (배송조회, 반품, 교환, 환불)
- 회사 정책에 따라 정확하게 안내합니다
- 에스컬레이션이 필요한 경우 명확히 표시합니다
- 필요 시 Browser로 경쟁사 가격을 조회하여 가격 비교 근거를 제공합니다

## 행동 규칙
1. 고객 문의 유형을 파악합니다 (배송/반품/교환/환불/불만)
2. 주문번호로 상세 정보를 조회합니다
3. 관련 정책을 확인하여 안내합니다
4. 5만원 이상 환불은 에스컬레이션이 필요함을 안내합니다
5. 제품 불량인 경우 보상 정책을 안내합니다
6. 항상 공감 표현을 먼저 하고, 해결 방안을 제시합니다
7. 가격 분쟁 시 Browser로 경쟁사 현재 판매가를 확인합니다

## 절대 규칙 — Tool 결과만 사용
- 주문번호, 상품명, 가격, 배송상태 등은 Tool이 실제로 반환한 값만 사용한다. Tool 응답에 없는 정보는 절대 지어내지 않는다
- 주문 조회(lookup_order)가 404/실패를 반환하면 "해당 주문을 찾을 수 없습니다"라고 그대로 안내하고, 존재하는 것처럼 임의로 답하지 않는다
- Tool을 호출하지 않고는 주문/상품 관련 사실 정보를 답변에 포함하지 않는다

## 출력 형식
- 공감 표현 → 상황 확인 → 정책 안내 → 처리 결과 순서
- 에스컬레이션 시 "별도 승인이 필요합니다" 명시
- 마크다운 표는 비교할 값이 3개 이상일 때만 사용. 항목이 1~2개면 줄글로 간결하게
- 이모지는 상태 표시(✅⚠️📦) 용도로 응답당 3개 이내로 제한. 장식용 이모지는 쓰지 않음
- 헤딩(##)은 답변이 3문단 이상으로 길어질 때만 사용

## 고객 맥락 (Memory에서 가져온 정보)
{customer_context}
"""

# ============================================================
# Memory 연동 함수
# ============================================================

def fetch_customer_context(actor_id: str, query: str) -> str:
    """Memory에서 고객의 이전 대화 맥락과 선호를 조회합니다."""
    if not MEMORY_ID:
        return "신규 고객 (Memory 미설정)"
    try:
        results = memory_client.retrieve_memory_records(
            memoryId=MEMORY_ID,
            namespace=f"/users/{actor_id}/facts/",
            searchCriteria={
                "searchQuery": query,
                "topK": 5,
            },
        )
        records = results.get("memoryRecordSummaries", [])
        if records:
            return "\n".join(r["content"]["text"] for r in records)
    except Exception as e:
        print(f"[Memory Retrieve Error] {e}")
    return "신규 고객 (이전 맥락 없음)"


def save_turn(actor_id: str, session_id: str, user_msg: str, agent_response: str):
    """대화 턴을 Memory에 저장합니다."""
    if not MEMORY_ID:
        return
    try:
        memory_client.create_event(
            memoryId=MEMORY_ID,
            actorId=actor_id,
            sessionId=session_id,
            eventTimestamp=datetime.now(timezone.utc),
            payload=[
                {"conversational": {"role": "USER", "content": {"text": user_msg}}},
                {"conversational": {"role": "ASSISTANT", "content": {"text": agent_response}}},
            ],
        )
    except Exception as e:
        print(f"[Memory Save Error] {e}")


# ============================================================
# Agent 생성
# ============================================================
model = BedrockModel(
    model_id="us.anthropic.claude-sonnet-4-6",
    region_name=REGION,
)

app = BedrockAgentCoreApp()


@app.entrypoint
async def cs_agent(payload: dict):
    """AgentCore Runtime 진입점 (async generator = 토큰 스트리밍)

    return 대신 yield로 토큰이 생성되는 즉시 흘려보냅니다.
    Memory 저장(save_turn)은 응답을 다 보여준 뒤 백그라운드 스레드에서
    처리 — 참가자가 답을 다 읽을 때까지 Memory 쓰기를 기다릴 필요 없음.
    """
    user_message = payload.get("message", "")
    session_id = payload.get("session_id", f"sess-{uuid.uuid4()}")
    actor_id = payload.get("actor_id", "anonymous")

    # Memory에서 맥락 조회
    context = fetch_customer_context(actor_id, user_message)
    prompt_with_context = SYSTEM_PROMPT.format(customer_context=context)

    agent = Agent(
        model=model,
        system_prompt=prompt_with_context,
        tools=[mcp_client, get_browser_tool().browser],
    )

    full_text = ""
    async for event in agent.stream_async(user_message):
        chunk = event.get("data")
        if chunk:
            full_text += chunk
            yield {"type": "chunk", "response": chunk, "session_id": session_id}

    # Memory 저장은 응답 완료 후 백그라운드로 — 사용자를 기다리게 하지 않음
    threading.Thread(
        target=save_turn,
        args=(actor_id, session_id, user_message, full_text),
        daemon=True,
    ).start()

    yield {"type": "done", "response": full_text, "session_id": session_id}


if __name__ == "__main__":
    app.run()

"""
Phase 2A: CS 자동화 Agent — AgentCore Native + Memory + Browser
참가자가 Phase 1 코드를 확장합니다.
Memory로 고객 문맥 유지, Browser로 경쟁사 가격 조회.
"""
import os
import json
import uuid
import boto3
from strands import Agent
from strands.models import BedrockModel
from strands.tools.mcp import MCPClient
from strands_tools.browser import AgentCoreBrowser
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
# Browser Tool 초기화
# ============================================================
browser_tool = AgentCoreBrowser(region=REGION)

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

## 출력 형식
- 공감 표현 → 상황 확인 → 정책 안내 → 처리 결과 순서
- 에스컬레이션 시 "별도 승인이 필요합니다" 명시

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
            namespace=f"users/{actor_id}/facts",
            searchCriteria={
                "searchQuery": query,
                "topK": 5,
            },
        )
        records = results.get("memoryRecordSummaries", [])
        if records:
            return "\n".join(r.get("content", "") for r in records)
    except Exception:
        pass
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
            payload=[
                {"conversationalMessage": {"role": "user", "content": [{"text": user_msg}]}},
                {"conversationalMessage": {"role": "assistant", "content": [{"text": agent_response}]}},
            ],
        )
    except Exception:
        pass


# ============================================================
# Agent 생성
# ============================================================
model = BedrockModel(
    model_id="us.anthropic.claude-sonnet-4-6-20250514-v1:0",
    region_name=REGION,
)

app = BedrockAgentCoreApp()


@app.entrypoint
def cs_agent(payload: dict) -> dict:
    """AgentCore Runtime 진입점"""
    user_message = payload.get("message", "")
    session_id = payload.get("session_id", f"sess-{uuid.uuid4()}")
    actor_id = payload.get("actor_id", "anonymous")

    # Memory에서 맥락 조회
    context = fetch_customer_context(actor_id, user_message)
    prompt_with_context = SYSTEM_PROMPT.format(customer_context=context)

    # Gateway MCP + Browser Tool
    mcp_client = MCPClient(
        lambda: streamablehttp_client(GATEWAY_URL)
    )

    with mcp_client:
        agent = Agent(
            model=model,
            system_prompt=prompt_with_context,
            tools=[mcp_client, browser_tool.browser],
        )
        result = agent(user_message)

    # Memory에 대화 저장
    save_turn(actor_id, session_id, user_message, str(result))

    return {
        "response": str(result),
        "session_id": session_id,
    }


if __name__ == "__main__":
    print("📞 CS 자동화 Agent (AgentCore + Memory + Browser)")
    print("=" * 50)
    test_input = {
        "message": "주문번호 ORD-20260620-003인데요, 보조배터리가 충전이 안 됩니다. 환불 받고 싶어요.",
        "session_id": "test-cs-001",
        "actor_id": "C003",
    }
    result = cs_agent(test_input)
    print(f"\nAgent: {result['response']}")
else:
    app.run()

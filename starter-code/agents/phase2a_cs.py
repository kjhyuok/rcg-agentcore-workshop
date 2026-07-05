"""
Phase 2A: CS 자동화 Agent — AgentCore Native + Memory + Browser
참가자가 Phase 1 코드를 확장합니다.
Memory로 고객 문맥 유지, Browser로 경쟁사 가격 조회.
"""
import os
import json
import uuid
from strands import Agent
from strands.models import BedrockModel
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from bedrock_agentcore.memory import MemoryClient
from strands_tools.browser import AgentCoreBrowser
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
import asyncio
import nest_asyncio

nest_asyncio.apply()

# ============================================================
# 환경변수
# ============================================================
GATEWAY_URL = os.environ.get("AGENTCORE_GATEWAY_URL", "")
MEMORY_ID = os.environ.get("AGENTCORE_MEMORY_ID", "")
REGION = os.environ.get("AWS_REGION", "us-east-1")

# ============================================================
# Memory Client & Browser Tool 초기화
# ============================================================
memory_client = MemoryClient(region_name=REGION)
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
"""

# ============================================================
# Memory 연동 함수
# ============================================================

def fetch_customer_context(actor_id: str, session_id: str) -> str:
    """Memory에서 고객의 이전 대화 맥락과 선호를 조회합니다."""
    lines = []
    for ns, query in [
        (f"/preferences/{actor_id}/", "고객 선호 정보"),
        (f"/summaries/{actor_id}/{session_id}/", "이전 대화 요약"),
    ]:
        try:
            results = memory_client.retrieve_memories(
                memory_id=MEMORY_ID,
                namespace=ns,
                query=query,
            )
            for r in results:
                lines.append(r["content"]["text"])
        except Exception:
            pass
    return "\n".join(lines) if lines else "신규 고객 (이전 맥락 없음)"


def save_turn(actor_id: str, session_id: str, user_msg: str, agent_response: str):
    """대화 턴을 Memory에 저장합니다."""
    try:
        memory_client.create_event(
            memory_id=MEMORY_ID,
            actor_id=actor_id,
            session_id=session_id,
            messages=[
                (user_msg, "USER"),
                (agent_response, "ASSISTANT"),
            ],
        )
    except Exception:
        pass


# ============================================================
# Gateway MCP 연결
# ============================================================

async def get_gateway_tools(gateway_url: str, headers: dict) -> list:
    """Gateway에서 MCP Tool 목록을 가져옵니다."""
    async with streamablehttp_client(gateway_url, headers=headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools_result = await session.list_tools()
            return tools_result.tools


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
    context = fetch_customer_context(actor_id, session_id)
    augmented_prompt = f"[고객 맥락]\n{context}\n\n[문의]\n{user_message}"

    # Gateway에서 비즈니스 Tool 가져오기
    access_token = os.environ.get("GATEWAY_ACCESS_TOKEN", "")
    headers = {"Authorization": f"Bearer {access_token}"} if access_token else {}
    gateway_tools = asyncio.run(get_gateway_tools(GATEWAY_URL, headers))

    # Gateway Tool + Browser Tool 결합
    all_tools = list(gateway_tools) + [browser_tool.browser]

    agent = Agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        tools=all_tools,
    )
    result = agent(augmented_prompt)

    # Memory에 대화 저장
    save_turn(actor_id, session_id, user_message, str(result))

    return {
        "response": str(result),
        "session_id": session_id,
    }


if __name__ == "__main__":
    print("CS 자동화 Agent (AgentCore + Memory + Browser)")
    print("=" * 50)
    test_input = {
        "message": "주문번호 ORD-20260620-003인데요, 보조배터리가 충전이 안 됩니다. 환불 받고 싶어요.",
        "session_id": "test-cs-001",
        "actor_id": "C003",
    }
    result = cs_agent(test_input)
    print(f"\nAgent: {result['response']}")

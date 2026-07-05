"""
Phase 2B: 수요 예측 Agent — AgentCore Native + Memory + Browser
분석형 다단계 Agent: 전체 스캔 → 트렌드 분석 → 외부 요인 → 발주 판단
Memory로 이전 발주 이력 참조, Browser로 날씨/뉴스 외부 요인 수집.
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
SYSTEM_PROMPT = """당신은 커머스 수요 예측 및 발주 관리 AI Agent입니다.

## 역할
- 재고 현황을 모니터링하고 품절 위험을 사전 감지합니다
- 판매 트렌드와 외부 요인을 분석하여 최적 발주량을 제안합니다
- 긴급 발주가 필요한 경우 알림을 제공합니다
- Browser로 날씨 예보, 뉴스, 경쟁점 동향 등 외부 요인을 수집합니다

## 행동 규칙
1. 전체 재고 현황을 먼저 확인합니다
2. 품절 위험 상품을 우선 식별합니다 (재고일수 < 리드타임+2)
3. 판매 트렌드(상승/안정/하락)와 계절성을 고려합니다
4. Browser로 외부 요인(날씨, 이벤트, 경쟁점)을 실시간 조회합니다
5. 발주량 = (예상 일판매 x (리드타임+안전일수)) - 현재고로 산출합니다
6. 발주 금액 50만원 초과 시 승인 필요를 명시합니다

## 출력 형식
- 전체 재고 현황 요약 (위험/정상 분류)
- 품절 위험 상품별 분석 (트렌드 + 외부 요인 반영)
- 발주 권고 (상품, 수량, 금액, 긴급도, 승인 필요 여부)
"""

# ============================================================
# Memory 연동
# ============================================================

def fetch_order_history(actor_id: str) -> str:
    """이전 발주 이력을 Memory에서 조회합니다."""
    try:
        results = memory_client.retrieve_memories(
            memory_id=MEMORY_ID,
            namespace=f"/orders/{actor_id}/",
            query="최근 발주 이력",
        )
        return "\n".join([r["content"]["text"] for r in results]) if results else "이전 발주 이력 없음"
    except Exception:
        return "이전 발주 이력 없음"


def save_order_decision(actor_id: str, session_id: str, user_msg: str, agent_response: str):
    """발주 판단 결과를 Memory에 저장합니다."""
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
    model_id="anthropic.claude-sonnet-4-6",
    region_name=REGION,
)

app = BedrockAgentCoreApp()


@app.entrypoint
def demand_agent(payload: dict) -> dict:
    """AgentCore Runtime 진입점"""
    user_message = payload.get("message", "")
    session_id = payload.get("session_id", f"sess-{uuid.uuid4()}")
    actor_id = payload.get("actor_id", "store-manager")

    # Memory에서 이전 발주 이력 조회
    history = fetch_order_history(actor_id)
    augmented_prompt = f"[이전 발주 이력]\n{history}\n\n[요청]\n{user_message}"

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

    # Memory에 발주 판단 저장
    save_order_decision(actor_id, session_id, user_message, str(result))

    return {
        "response": str(result),
        "session_id": session_id,
    }


if __name__ == "__main__":
    print("수요 예측 Agent (AgentCore + Memory + Browser)")
    print("=" * 50)
    test_input = {
        "message": "현재 재고 상황을 분석하고, 긴급 발주가 필요한 상품에 대해 발주를 진행해주세요.",
        "session_id": "test-demand-001",
        "actor_id": "store-manager",
    }
    result = demand_agent(test_input)
    print(f"\nAgent: {result['response']}")

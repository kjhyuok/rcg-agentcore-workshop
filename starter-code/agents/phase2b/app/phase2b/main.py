"""Phase 2B: 수요 예측 Agent — AgentCore Runtime + Memory"""
import os
import boto3
from strands import Agent
from strands.models.bedrock import BedrockModel
from strands.tools.mcp import MCPClient
from mcp.client.streamable_http import streamablehttp_client
from bedrock_agentcore.runtime import BedrockAgentCoreApp

app = BedrockAgentCoreApp()

GATEWAY_URL = os.environ.get("AGENTCORE_GATEWAY_URL", "")
MEMORY_ID = os.environ.get("AGENTCORE_MEMORY_ID", "")
REGION = os.environ.get("AWS_REGION", "us-west-2")

memory_client = boto3.client("bedrock-agentcore", region_name=REGION)

SYSTEM_PROMPT = """당신은 커머스 수요 예측 및 발주 관리 AI Agent입니다.

## 역할
- 재고 현황을 모니터링하고 품절 위험을 사전 감지합니다
- 판매 트렌드와 외부 요인을 분석하여 최적 발주량을 제안합니다
- 긴급 발주가 필요한 경우 알림을 제공합니다

## 행동 규칙
1. 전체 재고 현황을 먼저 확인합니다
2. 품절 위험 상품을 우선 식별합니다 (재고일수 < 리드타임+2)
3. 판매 트렌드(상승/안정/하락)와 계절성을 고려합니다
4. 외부 요인(날씨, 이벤트, 경쟁점)을 반영합니다
5. 발주량 = (예상 일판매 x (리드타임+안전일수)) - 현재고로 산출합니다
6. 발주 금액 50만원 초과 시 승인 필요를 명시합니다

## 출력 형식
- 전체 재고 현황 요약 (위험/정상 분류)
- 품절 위험 상품별 분석 (트렌드 + 외부 요인 반영)
- 발주 권고 (상품, 수량, 금액, 긴급도, 승인 필요 여부)
"""

model = BedrockModel(
    model_id="us.anthropic.claude-sonnet-4-20250514",
    region_name=REGION,
)

mcp_client = MCPClient(lambda: streamablehttp_client(GATEWAY_URL)) if GATEWAY_URL else None


def fetch_order_history(actor_id: str) -> str:
    if not MEMORY_ID:
        return "이전 발주 이력 없음"
    try:
        results = memory_client.retrieve_memory_records(
            memoryId=MEMORY_ID,
            namespace=f"orders/{actor_id}/facts",
            searchCriteria={"searchQuery": "최근 발주 이력", "topK": 5},
        )
        records = results.get("memoryRecordSummaries", [])
        if records:
            return "\n".join(r.get("content", "") for r in records)
    except Exception:
        pass
    return "이전 발주 이력 없음"


def save_order_decision(actor_id: str, session_id: str, user_msg: str, agent_response: str):
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


@app.entrypoint
async def invoke(payload, context):
    actor_id = payload.get("actor_id", "store-manager")
    prompt = payload.get("prompt", payload.get("message", ""))

    history = fetch_order_history(actor_id)
    augmented_prompt = f"[이전 발주 이력]\n{history}\n\n[요청]\n{prompt}"

    tools = [mcp_client] if mcp_client else []
    agent = Agent(model=model, system_prompt=SYSTEM_PROMPT, tools=tools)

    async for event in agent.stream_async(augmented_prompt):
        if not isinstance(event, dict) or "event" not in event:
            continue
        yield event


if __name__ == "__main__":
    app.run()

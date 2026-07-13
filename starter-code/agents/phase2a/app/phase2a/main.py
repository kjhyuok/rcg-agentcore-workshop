"""Phase 2A: CS 자동화 Agent — AgentCore Runtime + Memory"""
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

SYSTEM_PROMPT = """당신은 커머스 고객서비스(CS) 자동화 AI Agent입니다.

## 역할
- 고객의 주문 관련 문의를 처리합니다 (배송조회, 반품, 교환, 환불)
- 회사 정책에 따라 정확하게 안내합니다
- 에스컬레이션이 필요한 경우 명확히 표시합니다

## 행동 규칙
1. 고객 문의 유형을 파악합니다 (배송/반품/교환/환불/불만)
2. 주문번호로 상세 정보를 조회합니다
3. 관련 정책을 확인하여 안내합니다
4. 5만원 이상 환불은 에스컬레이션이 필요함을 안내합니다
5. 제품 불량인 경우 보상 정책을 안내합니다
6. 항상 공감 표현을 먼저 하고, 해결 방안을 제시합니다

## 절대 규칙 — Tool 결과만 사용
- 주문번호, 상품명, 가격, 배송상태 등은 Tool이 반환한 값만 사용한다
- 주문 조회가 실패하면 "해당 주문을 찾을 수 없습니다"라고 안내한다

## 출력 형식
- 공감 표현 → 상황 확인 → 정책 안내 → 처리 결과 순서
- 에스컬레이션 시 "별도 승인이 필요합니다" 명시

## 고객 맥락 (Memory에서 가져온 정보)
{customer_context}
"""

model = BedrockModel(
    model_id="us.anthropic.claude-sonnet-4-6",
    region_name=REGION,
)

mcp_client = MCPClient(lambda: streamablehttp_client(GATEWAY_URL)) if GATEWAY_URL else None


def fetch_customer_context(actor_id: str, query: str) -> str:
    if not MEMORY_ID:
        return "신규 고객 (Memory 미설정)"
    try:
        results = memory_client.retrieve_memory_records(
            memoryId=MEMORY_ID,
            namespace=f"users/{actor_id}/facts",
            searchCriteria={"searchQuery": query, "topK": 5},
        )
        records = results.get("memoryRecordSummaries", [])
        if records:
            return "\n".join(r.get("content", "") for r in records)
    except Exception:
        pass
    return "신규 고객 (이전 맥락 없음)"


def save_turn(actor_id: str, session_id: str, user_msg: str, agent_response: str):
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
    actor_id = payload.get("actor_id", "anonymous")
    prompt = payload.get("prompt", payload.get("message", ""))

    customer_context = fetch_customer_context(actor_id, prompt)
    system_prompt = SYSTEM_PROMPT.format(customer_context=customer_context)

    tools = [mcp_client] if mcp_client else []
    agent = Agent(model=model, system_prompt=system_prompt, tools=tools)

    async for event in agent.stream_async(prompt):
        if not isinstance(event, dict) or "event" not in event:
            continue
        yield event


if __name__ == "__main__":
    app.run()

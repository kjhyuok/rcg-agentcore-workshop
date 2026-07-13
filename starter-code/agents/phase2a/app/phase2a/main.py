"""Phase 2A: CS 자동화 Agent — AgentCore Runtime + Memory"""
import os
from collections import OrderedDict
import boto3
from strands import Agent
from strands.agent.conversation_manager.null_conversation_manager import NullConversationManager
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from model.load import load_model
from mcp_client.client import get_streamable_http_mcp_client

app = BedrockAgentCoreApp()
log = app.logger

MEMORY_ID = os.environ.get("AGENTCORE_MEMORY_ID", "")
REGION = os.environ.get("AWS_REGION", "us-west-2")

memory_client = boto3.client("bedrock-agentcore", region_name=REGION)

mcp_clients = [get_streamable_http_mcp_client()]

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

## 출력 형식
- 공감 표현 → 상황 확인 → 정책 안내 → 처리 결과 순서
- 에스컬레이션 시 "별도 승인이 필요합니다" 명시

## 고객 맥락 (Memory에서 가져온 정보)
{customer_context}
"""


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


tools = []
for mcp_client in mcp_clients:
    if mcp_client:
        tools.append(mcp_client)


def agent_factory():
    cache = OrderedDict()
    def get_or_create_agent(session_id, system_prompt):
        if session_id in cache:
            cache.move_to_end(session_id)
            return cache[session_id]
        if len(cache) >= 128:
            cache.popitem(last=False)
        cache[session_id] = Agent(
            model=load_model(),
            system_prompt=system_prompt,
            tools=tools,
            conversation_manager=NullConversationManager(),
        )
        return cache[session_id]
    return get_or_create_agent

get_or_create_agent = agent_factory()


@app.entrypoint
async def invoke(payload, context):
    log.info("Invoking CS Agent...")

    session_id = getattr(context, 'session_id', 'default-session')
    actor_id = payload.get("actor_id", "anonymous")

    prompt = payload.get("prompt", payload.get("message", ""))
    user_message = prompt if isinstance(prompt, str) else str(prompt)

    customer_context = fetch_customer_context(actor_id, user_message)
    system_prompt = SYSTEM_PROMPT.format(customer_context=customer_context)

    agent = get_or_create_agent(session_id, system_prompt)

    async for event in agent.stream_async(prompt):
        if not isinstance(event, dict) or "event" not in event:
            continue
        cbs = event["event"].get("contentBlockStart")
        if cbs is not None and not cbs.get("start"):
            continue
        yield event


if __name__ == "__main__":
    app.run()

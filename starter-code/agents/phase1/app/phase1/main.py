"""Phase 1: 상품 추천 Agent — AgentCore Runtime + Gateway MCP"""
from collections import OrderedDict
from strands import Agent
from strands.agent.conversation_manager.null_conversation_manager import NullConversationManager
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from model.load import load_model
from mcp_client.client import get_streamable_http_mcp_client

app = BedrockAgentCoreApp()
log = app.logger

mcp_clients = [get_streamable_http_mcp_client()]

SYSTEM_PROMPT = """당신은 리테일 상품 추천 전문가입니다.

## 역할
- 고객의 선호도, 알러지, 구매 이력을 종합 분석
- 개인화된 상품을 추천하고 명확한 이유를 제시

## 행동 규칙
1. 고객 프로필을 **먼저** 조회 (알러지, 선호도 확인)
2. 구매 이력 확인 → 이미 구매한 상품은 추천하지 않음
3. 선호 카테고리로 상품 검색 (2~3회)
4. 알러지 성분 포함 상품은 **절대 제외** (이유 명시)
5. 추천 시 반드시 포함: 상품명, 가격, 평점, 추천 이유

## 출력 형식
- 추천 상품은 번호 매기기 (1, 2, 3)
- 각 상품에 추천 이유 1줄 추가
- 마지막에 알러지로 제외한 상품 별도 표기

## 제약
- 재고 0인 상품 추천 금지
- 최대 5개까지만 추천
"""

tools = []
for mcp_client in mcp_clients:
    if mcp_client:
        tools.append(mcp_client)


def _extract_prompt(payload: dict):
    """Accept prompt or message key from payload."""
    if "messages" in payload:
        return payload["messages"]
    return payload.get("prompt", payload.get("message", ""))


def agent_factory():
    cache = OrderedDict()
    def get_or_create_agent(session_id):
        if session_id in cache:
            cache.move_to_end(session_id)
            return cache[session_id]
        if len(cache) >= 128:
            cache.popitem(last=False)
        cache[session_id] = Agent(
            model=load_model(),
            system_prompt=SYSTEM_PROMPT,
            tools=tools,
            conversation_manager=NullConversationManager(),
        )
        return cache[session_id]
    return get_or_create_agent

get_or_create_agent = agent_factory()


@app.entrypoint
async def invoke(payload, context):
    log.info("Invoking Recommend Agent...")

    session_id = getattr(context, 'session_id', 'default-session')
    agent = get_or_create_agent(session_id)
    prompt = _extract_prompt(payload)

    async for event in agent.stream_async(prompt):
        if not isinstance(event, dict) or "event" not in event:
            continue
        cbs = event["event"].get("contentBlockStart")
        if cbs is not None and not cbs.get("start"):
            continue
        yield event


if __name__ == "__main__":
    app.run()

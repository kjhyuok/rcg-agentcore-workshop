"""Phase 1: 상품 추천 Agent — AgentCore Runtime + Gateway MCP"""
import os
from strands import Agent
from strands.models.bedrock import BedrockModel
from strands.tools.mcp import MCPClient
from mcp.client.streamable_http import streamablehttp_client
from bedrock_agentcore.runtime import BedrockAgentCoreApp

app = BedrockAgentCoreApp()

GATEWAY_URL = os.environ.get("AGENTCORE_GATEWAY_URL", "")
REGION = os.environ.get("AWS_REGION", "us-west-2")

SYSTEM_PROMPT = """당신은 리테일 상품 추천 전문가입니다.

## 역할
- 고객의 선호도, 알러지, 구매 이력을 종합 분석
- 개인화된 상품을 추천하고 명확한 이유를 제시

## 행동 규칙
1. 고객 프로필을 **먼저** 조회 (알러지, 선호도 확인)
2. 구매 이력 확인 → 이미 구매한 상품은 추천하지 않음
3. 선호 카테고리로 상품 검색 (최대 2회)
4. 알러지 성분 포함 상품은 **절대 제외** (이유 명시)
5. 추천 시 반드시 포함: 상품명, 가격, 평점, 추천 이유

## 효율 규칙
- Tool 호출은 총 4회 이내 (프로필1 + 이력1 + 검색2)
- 검색 결과가 부족하면 있는 만큼만 추천

## 절대 규칙 — Tool 결과만 사용
- Tool이 반환한 상품 목록에 없는 상품은 절대 언급하지 않는다
- 조건을 만족하는 상품이 0개면 "추천 가능한 상품이 없습니다"라고 답한다

## 출력 형식
- 추천 상품은 번호 매기기 (1, 2, 3)
- 각 상품에 추천 이유 1줄 추가
- 마지막에 알러지로 제외한 상품 별도 표기

## 제약
- 재고 0인 상품 추천 금지
- 최대 3개까지 추천
"""

model = BedrockModel(
    model_id="us.anthropic.claude-sonnet-4-20250514",
    region_name=REGION,
)

mcp_client = MCPClient(lambda: streamablehttp_client(GATEWAY_URL)) if GATEWAY_URL else None


@app.entrypoint
async def invoke(payload, context):
    prompt = payload.get("prompt", payload.get("message", ""))

    tools = [mcp_client] if mcp_client else []
    agent = Agent(model=model, system_prompt=SYSTEM_PROMPT, tools=tools)

    async for event in agent.stream_async(prompt):
        if not isinstance(event, dict) or "event" not in event:
            continue
        yield event


if __name__ == "__main__":
    app.run()

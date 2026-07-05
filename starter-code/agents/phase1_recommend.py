"""
Phase 1: 상품 추천 Agent — AgentCore Native + Code Interpreter
참가자가 이 파일을 완성합니다.
Runtime에 배포하여 Gateway를 통해 Tool을 호출하고,
Code Interpreter로 추천 결과 차트를 생성합니다.
"""
import os
import json
import uuid
from strands import Agent
from strands.models import BedrockModel
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands_tools.code_interpreter import AgentCoreCodeInterpreter
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
import asyncio
import nest_asyncio

nest_asyncio.apply()

# ============================================================
# 환경변수 (agentcore deploy --env 로 주입)
# ============================================================
GATEWAY_URL = os.environ.get("AGENTCORE_GATEWAY_URL", "")
REGION = os.environ.get("AWS_REGION", "us-east-1")

# ============================================================
# System Prompt
# ============================================================
SYSTEM_PROMPT = """당신은 리테일 상품 추천 전문가입니다.

## 역할
- 고객의 선호도, 알러지, 구매 이력을 종합 분석
- 개인화된 상품을 추천하고 명확한 이유를 제시
- 필요 시 Code Interpreter로 추천 근거 차트를 생성

## 행동 규칙
1. 고객 프로필을 **먼저** 조회 (알러지, 선호도 확인)
2. 구매 이력 확인 → 이미 구매한 상품은 추천하지 않음
3. 선호 카테고리로 상품 검색 (2~3회)
4. 알러지 성분 포함 상품은 **절대 제외** (이유 명시)
5. 추천 시 반드시 포함: 상품명, 가격, 평점, 추천 이유
6. 데이터가 충분하면 Code Interpreter로 비교 차트 생성

## 출력 형식
- 추천 상품은 번호 매기기 (1, 2, 3)
- 각 상품에 추천 이유 1줄 추가
- 마지막에 알러지로 제외한 상품 별도 표기

## 제약
- 재고 0인 상품 추천 금지
- 최대 5개까지만 추천
"""

# ============================================================
# Code Interpreter Tool 초기화
# ============================================================
code_interpreter_tool = AgentCoreCodeInterpreter(region=REGION)

# ============================================================
# Agent 생성 (Gateway MCP + Code Interpreter)
# ============================================================
model = BedrockModel(
    model_id="us.anthropic.claude-sonnet-4-6-20250514-v1:0",
    region_name=REGION,
)


async def get_gateway_tools(gateway_url: str, headers: dict) -> list:
    """Gateway에서 MCP Tool 목록을 가져옵니다."""
    async with streamablehttp_client(gateway_url, headers=headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools_result = await session.list_tools()
            return tools_result.tools


# ============================================================
# Runtime Entrypoint
# ============================================================
app = BedrockAgentCoreApp()


@app.entrypoint
def recommend_agent(payload: dict) -> dict:
    """AgentCore Runtime이 호출하는 진입점"""
    user_message = payload.get("message", "")
    session_id = payload.get("session_id", f"sess-{uuid.uuid4()}")

    # Gateway에서 비즈니스 Tool 가져오기
    # Runtime 내부에서는 IAM 역할 기반 인증 (Authorization 헤더 불필요)
    # 외부에서는 OAuth Bearer 토큰 사용
    access_token = os.environ.get("GATEWAY_ACCESS_TOKEN", "")
    headers = {"Authorization": f"Bearer {access_token}"} if access_token else {}

    gateway_tools = asyncio.run(get_gateway_tools(GATEWAY_URL, headers))

    # Gateway Tool + Code Interpreter를 모두 Agent에 부여
    all_tools = list(gateway_tools) + [code_interpreter_tool.code_interpreter]

    agent = Agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        tools=all_tools,
    )
    result = agent(user_message)

    return {
        "response": str(result),
        "session_id": session_id,
    }


# ============================================================
# 로컬 테스트 (python3 agents/phase1_recommend.py)
# ============================================================
if __name__ == "__main__":
    print("상품 추천 Agent (AgentCore Native + Code Interpreter)")
    print("=" * 50)

    test_input = {
        "message": "고객 C001에게 적합한 상품 3개 추천해주세요. 알러지 고려해서 비교 차트도 만들어주세요.",
        "session_id": "test-001",
    }
    result = recommend_agent(test_input)
    print(f"\nAgent: {result['response']}")

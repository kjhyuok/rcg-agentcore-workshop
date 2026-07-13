"""
Phase 1: 상품 추천 Agent — AgentCore Native
Gateway Tool을 사용하여 고객 맞춤 상품을 추천합니다.
"""
import os
import uuid
from strands import Agent
from strands.models import BedrockModel
from strands.tools.mcp import MCPClient
from mcp.client.streamable_http import streamablehttp_client
from bedrock_agentcore.runtime import BedrockAgentCoreApp

# ============================================================
# 환경변수 (agentcore deploy --env 로 주입)
# ============================================================
GATEWAY_URL = os.environ.get("AGENTCORE_GATEWAY_URL", "")
REGION = os.environ.get("AWS_REGION", "us-east-1")

# ============================================================
# MCPClient는 모듈 로드 시 1회만 생성 — 요청마다 새로 만들면
# 매번 MCP 핸드셰이크 비용(수백ms)이 붙어 응답이 그만큼 늦어짐
# ============================================================
mcp_client = MCPClient(lambda: streamablehttp_client(GATEWAY_URL))

# ============================================================
# System Prompt
# ============================================================
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

## 효율 규칙 (필수)
- Tool 호출은 총 4회 이내 (프로필1 + 이력1 + 검색2)
- 검색 결과가 부족하면 있는 만큼만 추천하고, 부족하다는 사실을 그대로 말한다
- 간결하게 응답

## 절대 규칙 — Tool 결과만 사용
- Tool이 반환한 상품 목록에 없는 상품은 절대 언급하지 않는다 (상품명, 가격, product_id 모두 Tool 응답에서만 가져온다)
- 조건을 만족하는 상품이 3개 미만이면 있는 개수만 추천한다. 개수를 채우려고 다른 상품의 이름을 바꾸거나 존재하지 않는 상품을 만들어내지 않는다
- 조건을 만족하는 상품이 0개면 "추천 가능한 상품이 없습니다"라고 솔직히 답하고, 조건을 완화하면 나올 수 있는 대안(다른 카테고리 등)을 제안한다

## 출력 형식
- 추천 상품은 번호 매기기 (1, 2, 3...) — 실제로 찾은 개수만큼만
- 각 상품에 추천 이유 1줄 추가
- 마지막에 알러지로 제외한 상품 별도 표기
- 이모지는 최소화 (상품당 0~1개), 장식용 헤딩(##)이나 표는 쓰지 않고 목록으로 간결하게

## 제약
- 재고 0인 상품 추천 금지
- 최대 3개까지 추천 (조건을 만족하는 상품이 더 적으면 그만큼만)
"""

# ============================================================
# 모델
# ============================================================
model = BedrockModel(
    model_id="us.anthropic.claude-sonnet-4-6",
    region_name=REGION,
)

# ============================================================
# Runtime Entrypoint
# ============================================================
app = BedrockAgentCoreApp()


@app.entrypoint
async def recommend_agent(payload: dict):
    """AgentCore Runtime이 호출하는 진입점 (async generator = 토큰 스트리밍)

    return 대신 yield를 쓰면 BedrockAgentCoreApp이 자동으로 SSE 스트리밍
    응답으로 변환합니다. 참가자가 agentcore invoke로 호출하면 Agent가
    답을 다 만들 때까지 기다리지 않고, 토큰이 생성되는 즉시 화면에 흘러나옵니다.
    """
    user_message = payload.get("message", payload.get("prompt", ""))
    session_id = payload.get("session_id", f"sess-{uuid.uuid4()}")

    agent = Agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        tools=[mcp_client],
    )

    full_text = ""
    async for event in agent.stream_async(user_message):
        chunk = event.get("data")
        if chunk:
            full_text += chunk
            yield {"type": "chunk", "response": chunk, "session_id": session_id}

    yield {"type": "done", "response": full_text, "session_id": session_id}


# ============================================================
# Runtime 서버 시작 (배포 + 로컬 모두 이 진입점 사용)
# ============================================================
if __name__ == "__main__":
    app.run()

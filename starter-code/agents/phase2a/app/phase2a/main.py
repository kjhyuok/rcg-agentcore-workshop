"""Phase 2A: CS 자동화 Agent — AgentCore Runtime + Memory + Browser"""
import os
import threading
from datetime import datetime, timezone
import boto3
from strands import Agent
from strands.models.bedrock import BedrockModel
from strands.tools.mcp import MCPClient
from mcp.client.streamable_http import streamablehttp_client
from bedrock_agentcore.runtime import BedrockAgentCoreApp

app = BedrockAgentCoreApp()

GATEWAY_URL = os.environ.get("AGENTCORE_GATEWAY_URL", "")
MEMORY_ID = os.environ.get("AGENTCORE_MEMORY_ID", "")
MOCK_SITE_URL = os.environ.get("MOCK_SITE_URL", "")
REGION = os.environ.get("AWS_REGION", "us-west-2")

memory_client = boto3.client("bedrock-agentcore", region_name=REGION)

# Browser Tool은 "지연 생성 + 싱글톤 캐싱" — import 시점에 즉시 만들면
# Playwright 초기화가 Runtime의 30초 콜드스타트 타임아웃에 걸릴 수 있어,
# 첫 요청에서만 최초 1회 생성하고 이후 요청은 캐시된 인스턴스를 재사용합니다.
_browser_tool = None
_browser_tool_lock = threading.Lock()


def _prepare_playwright_driver():
    """CodeZip 배포로 실행권한을 잃은 playwright driver의 node 바이너리를
    쓰기 가능한 /tmp로 복사해 실행권한을 부여하고, PLAYWRIGHT_NODEJS_PATH로
    그 위치를 쓰게 한다.

    Runtime의 코드 영역(/var/task)은 읽기 전용이라 그 자리의
    playwright/driver/node에 chmod를 걸 수 없어
    'PermissionError: [Errno 13] ... playwright/driver/node'가 발생한다.
    playwright는 compute_driver_executable()에서 node 경로를
    os.getenv("PLAYWRIGHT_NODEJS_PATH", <기본경로>)로 결정하므로,
    /tmp에 복사한 실행 가능 node를 이 환경변수로 지정한다. (cli.js는
    /var/task에서 읽기만 하면 되므로 복사 불필요.) 프로세스당 최초 1회만 수행."""
    import os
    import stat
    import shutil
    import playwright

    src_node = os.path.join(os.path.dirname(playwright.__file__), "driver", "node")
    dst_node = "/tmp/pw-driver-node"
    try:
        if not os.path.exists(dst_node):
            shutil.copy2(src_node, dst_node)
        os.chmod(dst_node, os.stat(dst_node).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        os.environ["PLAYWRIGHT_NODEJS_PATH"] = dst_node
    except Exception as e:
        print(f"[playwright driver prep error] {e}")


def get_browser_tool():
    global _browser_tool
    if _browser_tool is None:
        with _browser_tool_lock:
            if _browser_tool is None:
                _prepare_playwright_driver()
                from strands_tools.browser import AgentCoreBrowser
                _browser_tool = AgentCoreBrowser(region=REGION)
    return _browser_tool

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
7. 가격 분쟁("다른 곳이 더 싸다" 등) 시, Browser로 경쟁사 현재 판매가 페이지를 방문해 실제 가격을 확인한 뒤 비교 근거를 제시합니다. 경쟁사 가격 페이지 URL: {mock_site_url}/competitor-prices.html

## 절대 규칙 — Tool 선택 (매우 중요)
- 주문 조회/반품 정책/반품·환불 처리/배송 추적은 **반드시 전용 Gateway Tool**을 사용한다:
  cs_lookup_order(주문조회), cs_return_policy(반품정책), cs_process_return(반품/환불), cs_delivery_status(배송추적)
- **Browser는 오직 "경쟁사 가격 비교"에만** 사용한다. 주문/배송/환불 조회에 Browser로 URL을 여는 것은 절대 금지 — 그런 페이지는 존재하지 않는다.
- 예: "주문 배송 상태 조회" → cs_lookup_order 또는 cs_delivery_status 호출 (Browser 아님)

## 절대 규칙 — Tool 결과만 사용
- 주문번호, 상품명, 가격, 배송상태 등은 Tool이 반환한 값만 사용한다
- 주문 조회가 실패하면 "해당 주문을 찾을 수 없습니다"라고 안내한다

## 절대 규칙 — Tool 연결 실패 시
- Tool 호출이 에러를 반환하거나 Tool 자체를 호출할 수 없는 상황이면, 앞으로 어떤 순서로 Tool을 호출할 계획이었는지, Tool 이름, 파라미터, 진행 단계 표(Step 1/2/3...) 같은 내부 실행 계획을 절대 서술하지 않는다
- 이 경우 딱 한 문장으로만 안내한다: "현재 주문 정보를 조회할 수 없어 문의를 처리하기 어렵습니다. 잠시 후 다시 시도해 주세요."
- 코드블록, JSON 예시, 대체 데이터 요청 등 부가 설명을 덧붙이지 않는다 — 위 한 문장 외에는 아무것도 추가하지 않는다

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
            return "\n".join(r["content"]["text"] for r in records)
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
            eventTimestamp=datetime.now(timezone.utc),
            payload=[
                {"conversational": {"role": "USER", "content": {"text": user_msg}}},
                {"conversational": {"role": "ASSISTANT", "content": {"text": agent_response}}},
            ],
        )
    except Exception:
        pass


@app.entrypoint
async def invoke(payload, context):
    actor_id = payload.get("actor_id", "anonymous")
    session_id = payload.get("session_id", "")
    prompt = payload.get("prompt", payload.get("message", ""))

    customer_context = fetch_customer_context(actor_id, prompt)
    system_prompt = SYSTEM_PROMPT.format(
        customer_context=customer_context,
        mock_site_url=MOCK_SITE_URL,
    )

    # Gateway(MCP) Tool + Browser Tool을 함께 부여
    tools = [mcp_client] if mcp_client else []
    tools.append(get_browser_tool().browser)
    agent = Agent(model=model, system_prompt=system_prompt, tools=tools)

    # 스트리밍하면서 최종 답변 텍스트를 누적 (Memory 저장용)
    full_text = ""
    async for event in agent.stream_async(prompt):
        if not isinstance(event, dict) or "event" not in event:
            continue
        delta = event["event"].get("contentBlockDelta", {}).get("delta", {})
        piece = delta.get("text")
        if isinstance(piece, str):
            full_text += piece
        yield event

    # Memory 저장은 응답 완료 후 백그라운드 스레드로 — 사용자를 기다리게 하지 않음
    if session_id and full_text:
        threading.Thread(
            target=save_turn,
            args=(actor_id, session_id, prompt, full_text),
            daemon=True,
        ).start()


if __name__ == "__main__":
    app.run()

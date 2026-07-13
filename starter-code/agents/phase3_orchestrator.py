"""
Phase 3: 멀티 Agent 오케스트레이터 — A2A (Agent-to-Agent) 통신
운영자가 사전 배포합니다. 참가자는 자신의 Agent ARN을 등록합니다.

역할:
- 사용자 요청의 의도(intent)를 분류
- 적절한 전문 Agent(recommend, cs, demand)로 라우팅
- boto3 invoke_agent_runtime으로 하위 Agent 호출
- 응답을 취합하여 최종 답변 생성
"""
import os
import json
import uuid
import boto3
from strands import Agent
from strands.models import BedrockModel
from bedrock_agentcore.runtime import BedrockAgentCoreApp

# ============================================================
# 환경변수 (운영자가 배포 시 설정)
# ============================================================
REGION = os.environ.get("AWS_REGION", "us-east-1")

# 참가자 Agent ARN 레지스트리 (환경변수 또는 DynamoDB에서 로딩)
AGENT_REGISTRY = {
    "recommend": os.environ.get("AGENT_ARN_RECOMMEND", ""),
    "cs": os.environ.get("AGENT_ARN_CS", ""),
    "demand": os.environ.get("AGENT_ARN_DEMAND", ""),
}

# ============================================================
# System Prompt (의도 분류용)
# ============================================================
CLASSIFIER_PROMPT = """당신은 리테일 커머스 요청을 분류하는 라우터입니다.

## 분류 규칙
사용자 메시지를 분석하여 아래 3개 카테고리 중 하나로 분류하세요:

1. **recommend** — 상품 추천, 추천 요청, 뭐 살까, 상품 검색
2. **cs** — 주문 문의, 환불, 반품, 배송, 교환, 불만, 고객 서비스
3. **demand** — 재고, 발주, 품절, 수요 예측, 트렌드, 매출 분석

## 출력 형식
반드시 JSON만 반환하세요:
{"intent": "recommend|cs|demand", "confidence": 0.0~1.0, "reason": "분류 근거"}
"""

SYNTHESIS_PROMPT = """당신은 최종 응답을 다듬는 편집자입니다.
전문 Agent의 응답을 받아 고객 친화적인 최종 답변으로 다듬으세요.
원본 정보를 빠뜨리지 마세요. 마크다운 형식으로 작성합니다."""

# ============================================================
# Bedrock AgentCore Runtime 클라이언트
# ============================================================
bedrock_client = boto3.client("bedrock-agent-runtime", region_name=REGION)

model = BedrockModel(
    model_id="us.anthropic.claude-sonnet-5",
    region_name=REGION,
)


def classify_intent(message: str) -> dict:
    """사용자 메시지의 의도를 분류합니다."""
    classifier = Agent(
        model=model,
        system_prompt=CLASSIFIER_PROMPT,
    )
    result = classifier(message)
    try:
        return json.loads(str(result))
    except json.JSONDecodeError:
        # JSON 파싱 실패 시 기본값
        return {"intent": "recommend", "confidence": 0.5, "reason": "분류 실패 - 기본 추천으로 라우팅"}


def invoke_specialist_agent(agent_arn: str, payload: dict) -> str:
    """boto3를 통해 배포된 전문 Agent를 호출합니다 (A2A 통신)."""
    if not agent_arn:
        return "[ERROR] Agent ARN이 등록되지 않았습니다. 운영자에게 문의하세요."

    try:
        response = bedrock_client.invoke_agent_runtime(
            agentRuntimeArn=agent_arn,
            inputText=json.dumps(payload),
            sessionId=payload.get("session_id", str(uuid.uuid4())),
        )

        # 스트리밍 응답 수집
        completion = ""
        for event in response.get("completion", []):
            if "chunk" in event:
                chunk_data = event["chunk"].get("bytes", b"")
                completion += chunk_data.decode("utf-8")

        return completion if completion else "[WARNING] Agent로부터 빈 응답 수신"

    except bedrock_client.exceptions.ResourceNotFoundException:
        return f"[ERROR] Agent를 찾을 수 없습니다: {agent_arn}"
    except Exception as e:
        return f"[ERROR] Agent 호출 실패: {str(e)}"


def synthesize_response(original_message: str, specialist_response: str, intent: str) -> str:
    """전문 Agent의 응답을 최종 형태로 다듬습니다."""
    synthesizer = Agent(
        model=model,
        system_prompt=SYNTHESIS_PROMPT,
    )
    prompt = f"""## 원본 요청
{original_message}

## 전문 Agent ({intent}) 응답
{specialist_response}

위 응답을 고객 친화적으로 다듬어주세요."""
    result = synthesizer(prompt)
    return str(result)


# ============================================================
# Runtime Entrypoint
# ============================================================
app = BedrockAgentCoreApp()


@app.entrypoint
def orchestrator_agent(payload: dict) -> dict:
    """
    오케스트레이터 진입점.
    1) 의도 분류
    2) 전문 Agent 호출 (A2A)
    3) 응답 취합 및 다듬기
    """
    user_message = payload.get("message", "")
    session_id = payload.get("session_id", f"sess-{uuid.uuid4()}")
    actor_id = payload.get("actor_id", "anonymous")

    # Step 1: 의도 분류
    classification = classify_intent(user_message)
    intent = classification.get("intent", "recommend")
    confidence = classification.get("confidence", 0.0)

    # Step 2: 전문 Agent 호출
    agent_arn = AGENT_REGISTRY.get(intent, "")
    specialist_payload = {
        "message": user_message,
        "session_id": session_id,
        "actor_id": actor_id,
    }
    specialist_response = invoke_specialist_agent(agent_arn, specialist_payload)

    # Step 3: 응답 다듬기 (신뢰도가 높으면 직접 전달, 낮으면 편집)
    if confidence >= 0.85:
        final_response = specialist_response
    else:
        final_response = synthesize_response(user_message, specialist_response, intent)

    return {
        "response": final_response,
        "session_id": session_id,
        "metadata": {
            "intent": intent,
            "confidence": confidence,
            "reason": classification.get("reason", ""),
            "specialist_agent": intent,
        },
    }


if __name__ == "__main__":
    app.run()

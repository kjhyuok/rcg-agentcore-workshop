"""Phase 3: 멀티 Agent 오케스트레이터 — A2A (Agent-to-Agent) 통신"""
import os
import json
import uuid
import boto3
from strands import Agent
from strands.models.bedrock import BedrockModel
from bedrock_agentcore.runtime import BedrockAgentCoreApp

app = BedrockAgentCoreApp()

REGION = os.environ.get("AWS_REGION", "us-west-2")

AGENT_REGISTRY = {
    "recommend": os.environ.get("AGENT_ARN_RECOMMEND", ""),
    "cs": os.environ.get("AGENT_ARN_CS", ""),
    "demand": os.environ.get("AGENT_ARN_DEMAND", ""),
}

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

model = BedrockModel(
    model_id="us.anthropic.claude-sonnet-4-6",
    region_name=REGION,
)

bedrock_client = boto3.client("bedrock-agent-runtime", region_name=REGION)


def classify_intent(message: str) -> dict:
    classifier = Agent(model=model, system_prompt=CLASSIFIER_PROMPT)
    result = classifier(message)
    try:
        return json.loads(str(result))
    except json.JSONDecodeError:
        return {"intent": "recommend", "confidence": 0.5, "reason": "분류 실패 - 기본 추천으로 라우팅"}


def invoke_specialist_agent(agent_arn: str, payload: dict) -> str:
    if not agent_arn:
        return "[ERROR] Agent ARN이 등록되지 않았습니다."
    try:
        response = bedrock_client.invoke_agent_runtime(
            agentRuntimeArn=agent_arn,
            inputText=json.dumps(payload),
            sessionId=payload.get("session_id", str(uuid.uuid4())),
        )
        completion = ""
        for event in response.get("completion", []):
            if "chunk" in event:
                chunk_data = event["chunk"].get("bytes", b"")
                completion += chunk_data.decode("utf-8")
        return completion if completion else "[WARNING] Agent로부터 빈 응답 수신"
    except Exception as e:
        return f"[ERROR] Agent 호출 실패: {str(e)}"


def synthesize_response(original_message: str, specialist_response: str, intent: str) -> str:
    synthesizer = Agent(model=model, system_prompt=SYNTHESIS_PROMPT)
    prompt = f"""## 원본 요청
{original_message}

## 전문 Agent ({intent}) 응답
{specialist_response}

위 응답을 고객 친화적으로 다듬어주세요."""
    result = synthesizer(prompt)
    return str(result)


@app.entrypoint
async def invoke(payload, context):
    user_message = payload.get("prompt", payload.get("message", ""))
    actor_id = payload.get("actor_id", "anonymous")
    session_id = getattr(context, "session_id", "default-session")

    classification = classify_intent(user_message)
    intent = classification.get("intent", "recommend")
    confidence = classification.get("confidence", 0.0)

    agent_arn = AGENT_REGISTRY.get(intent, "")
    specialist_response = invoke_specialist_agent(agent_arn, {
        "message": user_message,
        "session_id": session_id,
        "actor_id": actor_id,
    })

    if confidence >= 0.85:
        final_response = specialist_response
    else:
        final_response = synthesize_response(user_message, specialist_response, intent)

    result = json.dumps({
        "response": final_response,
        "metadata": {"intent": intent, "confidence": confidence},
    }, ensure_ascii=False)

    yield {"event": {"contentBlockStart": {"start": {"text": ""}}}}
    yield {"event": {"contentBlockDelta": {"delta": {"text": result}}}}
    yield {"event": {"contentBlockStop": {}}}


if __name__ == "__main__":
    app.run()

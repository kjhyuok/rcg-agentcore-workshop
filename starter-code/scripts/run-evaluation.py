"""
Agent 품질 평가 스크립트 — LLM-as-Judge 방식
AgentCore Evaluations CLI가 GA 되지 않은 경우의 대안.

사용법:
    python3 scripts/run-evaluation.py --agent-arn <AGENT_ARN> --scenario recommend
    python3 scripts/run-evaluation.py --agent-arn <AGENT_ARN> --scenario all

평가 기준:
    1. Helpfulness (유용성) — 사용자 요청에 적절히 대응했는가
    2. Accuracy (정확도) — 정보가 정확하고 정책을 준수했는가
    3. Tool Selection (도구 선택) — 올바른 도구를 적절한 순서로 호출했는가
"""
import os
import sys
import json
import uuid
import time
import argparse
from datetime import datetime
from typing import Optional

import boto3

# ============================================================
# 설정
# ============================================================
REGION = os.environ.get("AWS_REGION", "us-east-1")
JUDGE_MODEL_ID = "us.anthropic.claude-sonnet-4-6-20250514-v1:0"

bedrock_runtime = boto3.client("bedrock-runtime", region_name=REGION)
agentcore_client = boto3.client("bedrock-agent-runtime", region_name=REGION)

# ============================================================
# Golden Test Set (시나리오별 5개 테스트 케이스)
# ============================================================
TEST_CASES = {
    "recommend": [
        {
            "id": "REC-001",
            "input": "고객 C001에게 적합한 상품 3개 추천해주세요. 알러지를 고려해주세요.",
            "expected_behavior": "고객 프로필 조회 후 알러지 성분 확인, 알러지 상품 제외, 3개 추천",
            "required_tools": ["customer_profile", "product_search"],
            "forbidden": ["알러지 포함 상품 추천", "재고 0인 상품 추천"],
        },
        {
            "id": "REC-002",
            "input": "30대 여성 고객이 스킨케어 제품을 찾고 있어요. 예산은 5만원 이하입니다.",
            "expected_behavior": "카테고리=스킨케어, 가격<=50000 필터링, 인기순 추천",
            "required_tools": ["product_search"],
            "forbidden": ["5만원 초과 상품 추천"],
        },
        {
            "id": "REC-003",
            "input": "고객 C002가 이전에 구매한 적 없는 새로운 상품을 추천해주세요.",
            "expected_behavior": "구매 이력 조회 후 중복 제외, 새로운 상품만 추천",
            "required_tools": ["customer_profile", "purchase_history", "product_search"],
            "forbidden": ["이미 구매한 상품 재추천"],
        },
        {
            "id": "REC-004",
            "input": "유기농 식품 중에서 인기 상품 추천해주세요.",
            "expected_behavior": "카테고리=유기농식품, 평점/판매량 기준 정렬, 상위 추천",
            "required_tools": ["product_search"],
            "forbidden": ["유기농이 아닌 상품 추천"],
        },
        {
            "id": "REC-005",
            "input": "고객 C003은 견과류 알러지가 있어요. 간식류 추천해주세요.",
            "expected_behavior": "견과류 성분 포함 상품 완전 제외, 제외 이유 명시",
            "required_tools": ["customer_profile", "product_search"],
            "forbidden": ["견과류 포함 상품 추천"],
        },
    ],
    "cs": [
        {
            "id": "CS-001",
            "input": "주문번호 ORD-20260620-003인데요, 배터리가 충전이 안 됩니다. 환불 받고 싶어요.",
            "expected_behavior": "주문 조회 → 불량 확인 → 환불 정책 안내 → 처리",
            "required_tools": ["lookup_order", "return_policy"],
            "forbidden": ["공감 없이 바로 정책만 안내"],
        },
        {
            "id": "CS-002",
            "input": "3일 전에 주문했는데 아직 배송이 안 왔어요. 주문번호 ORD-20260625-010입니다.",
            "expected_behavior": "배송 상태 조회 → 예상 도착일 안내 → 지연 사유 설명",
            "required_tools": ["lookup_order", "delivery_status"],
            "forbidden": ["배송 조회 없이 추측 답변"],
        },
        {
            "id": "CS-003",
            "input": "7만원짜리 상품 환불하고 싶어요.",
            "expected_behavior": "5만원 이상이므로 에스컬레이션 필요 명시",
            "required_tools": ["lookup_order", "return_policy"],
            "forbidden": ["에스컬레이션 없이 직접 처리"],
        },
        {
            "id": "CS-004",
            "input": "교환하고 싶은데 개봉했어요. 가능한가요?",
            "expected_behavior": "개봉 상품 교환 정책 확인 후 안내",
            "required_tools": ["return_policy"],
            "forbidden": ["정책 확인 없이 불가 단정"],
        },
        {
            "id": "CS-005",
            "input": "같은 상품이 다른 데서 더 싸게 팔아요. 가격 보상해주세요.",
            "expected_behavior": "경쟁사 가격 확인(Browser) → 가격보상 정책 안내",
            "required_tools": ["return_policy"],
            "forbidden": ["확인 없이 거절"],
        },
    ],
    "demand": [
        {
            "id": "DEM-001",
            "input": "현재 재고 상황을 분석하고, 긴급 발주가 필요한 상품을 알려주세요.",
            "expected_behavior": "전체 재고 조회 → 품절 위험 식별 → 발주 권고",
            "required_tools": ["inventory_status", "sales_trend"],
            "forbidden": ["재고 조회 없이 추측"],
        },
        {
            "id": "DEM-002",
            "input": "다음 주에 폭염이 예상됩니다. 음료 카테고리 발주량을 조정해주세요.",
            "expected_behavior": "날씨 정보 수집(Browser) → 음료 판매 트렌드 확인 → 증량 권고",
            "required_tools": ["inventory_status", "sales_trend"],
            "forbidden": ["외부 요인 무시"],
        },
        {
            "id": "DEM-003",
            "input": "지난달 대비 매출이 20% 하락한 상품들을 분석해주세요.",
            "expected_behavior": "매출 데이터 조회 → 하락 상품 식별 → 원인 분석",
            "required_tools": ["sales_trend"],
            "forbidden": ["데이터 없이 추측"],
        },
        {
            "id": "DEM-004",
            "input": "총 발주 금액이 80만원인 발주 건을 처리해주세요.",
            "expected_behavior": "50만원 초과이므로 승인 필요 명시",
            "required_tools": ["inventory_status"],
            "forbidden": ["승인 없이 직접 처리"],
        },
        {
            "id": "DEM-005",
            "input": "여름 시즌 상품 트렌드를 분석하고 신규 입고 추천해주세요.",
            "expected_behavior": "계절성 분석 + 트렌드 데이터 → 카테고리별 입고 추천",
            "required_tools": ["sales_trend"],
            "forbidden": ["계절성 무시"],
        },
    ],
}

# ============================================================
# LLM-as-Judge 프롬프트
# ============================================================
JUDGE_PROMPT = """당신은 AI Agent의 응답 품질을 평가하는 전문 심사위원입니다.

## 평가 기준 (각 1~5점)

### 1. Helpfulness (유용성)
- 5: 사용자 요청을 완벽히 해결, 추가 가치 제공
- 4: 요청을 잘 해결, 약간의 개선 여지
- 3: 대체로 해결하나 일부 누락
- 2: 부분적으로만 해결
- 1: 요청과 무관하거나 도움이 안 됨

### 2. Accuracy (정확도)
- 5: 모든 정보가 정확하고 정책 완벽 준수
- 4: 대부분 정확, 사소한 오류
- 3: 핵심은 정확하나 일부 부정확
- 2: 중요한 오류 포함
- 1: 정보가 대부분 부정확

### 3. Tool Selection (도구 선택)
- 5: 필요한 도구를 정확한 순서로 모두 호출
- 4: 적절한 도구 사용, 순서 약간 비효율
- 3: 대부분 적절하나 불필요한 호출 있음
- 2: 주요 도구 누락 또는 잘못된 도구 사용
- 1: 도구를 전혀 사용하지 않거나 완전히 잘못 사용

## 평가 대상

### 테스트 케이스
- 입력: {input}
- 기대 행동: {expected_behavior}
- 필수 도구: {required_tools}
- 금지 사항: {forbidden}

### Agent 응답
{response}

## 출력 형식
반드시 아래 JSON 형식으로만 응답하세요:
{{
    "helpfulness": {{
        "score": 1-5,
        "reason": "평가 근거"
    }},
    "accuracy": {{
        "score": 1-5,
        "reason": "평가 근거"
    }},
    "tool_selection": {{
        "score": 1-5,
        "reason": "평가 근거"
    }},
    "overall_feedback": "전반적 피드백 1~2문장",
    "violations": ["위반 사항 목록"]
}}
"""


# ============================================================
# Agent 호출 함수
# ============================================================
def invoke_agent(agent_arn: str, test_case: dict) -> tuple[str, float]:
    """
    배포된 Agent를 호출하고 응답과 소요 시간을 반환합니다.
    Returns: (response_text, elapsed_seconds)
    """
    payload = {
        "message": test_case["input"],
        "session_id": f"eval-{test_case['id']}-{uuid.uuid4().hex[:8]}",
        "actor_id": "eval-user",
    }

    start_time = time.time()
    try:
        response = agentcore_client.invoke_agent_runtime(
            agentRuntimeArn=agent_arn,
            inputText=json.dumps(payload),
            sessionId=payload["session_id"],
        )

        completion = ""
        for event in response.get("completion", []):
            if "chunk" in event:
                chunk_data = event["chunk"].get("bytes", b"")
                completion += chunk_data.decode("utf-8")

        elapsed = time.time() - start_time
        return completion if completion else "[빈 응답]", elapsed

    except Exception as e:
        elapsed = time.time() - start_time
        return f"[ERROR] {str(e)}", elapsed


# ============================================================
# LLM Judge 호출
# ============================================================
def judge_response(test_case: dict, agent_response: str) -> dict:
    """Claude를 Judge로 사용하여 응답 품질을 평가합니다."""
    prompt = JUDGE_PROMPT.format(
        input=test_case["input"],
        expected_behavior=test_case["expected_behavior"],
        required_tools=", ".join(test_case["required_tools"]),
        forbidden=", ".join(test_case["forbidden"]),
        response=agent_response,
    )

    try:
        response = bedrock_runtime.invoke_model(
            modelId=JUDGE_MODEL_ID,
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1024,
                "messages": [{"role": "user", "content": prompt}],
            }),
        )

        result = json.loads(response["body"].read())
        content = result["content"][0]["text"]

        # JSON 추출 (마크다운 코드블록 처리)
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        return json.loads(content.strip())

    except Exception as e:
        return {
            "helpfulness": {"score": 0, "reason": f"평가 실패: {str(e)}"},
            "accuracy": {"score": 0, "reason": f"평가 실패: {str(e)}"},
            "tool_selection": {"score": 0, "reason": f"평가 실패: {str(e)}"},
            "overall_feedback": f"Judge 호출 실패: {str(e)}",
            "violations": [],
        }


# ============================================================
# 리포트 생성
# ============================================================
def generate_report(results: list, scenario: str, agent_arn: str) -> dict:
    """평가 결과를 종합 리포트로 생성합니다."""
    total_helpfulness = 0
    total_accuracy = 0
    total_tool_selection = 0
    total_time = 0
    count = len(results)

    for r in results:
        scores = r.get("scores", {})
        total_helpfulness += scores.get("helpfulness", {}).get("score", 0)
        total_accuracy += scores.get("accuracy", {}).get("score", 0)
        total_tool_selection += scores.get("tool_selection", {}).get("score", 0)
        total_time += r.get("elapsed_seconds", 0)

    report = {
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "agent_arn": agent_arn,
            "scenario": scenario,
            "total_cases": count,
            "judge_model": JUDGE_MODEL_ID,
        },
        "summary": {
            "avg_helpfulness": round(total_helpfulness / count, 2) if count else 0,
            "avg_accuracy": round(total_accuracy / count, 2) if count else 0,
            "avg_tool_selection": round(total_tool_selection / count, 2) if count else 0,
            "avg_response_time_sec": round(total_time / count, 2) if count else 0,
            "overall_score": round(
                (total_helpfulness + total_accuracy + total_tool_selection) / (count * 3), 2
            ) if count else 0,
        },
        "details": results,
    }

    return report


def print_report(report: dict):
    """리포트를 콘솔에 출력합니다."""
    print("\n" + "=" * 60)
    print("  Agent 품질 평가 리포트")
    print("=" * 60)

    meta = report["metadata"]
    print(f"\n  시나리오: {meta['scenario']}")
    print(f"  Agent ARN: {meta['agent_arn']}")
    print(f"  평가 시각: {meta['timestamp']}")
    print(f"  테스트 케이스: {meta['total_cases']}개")

    summary = report["summary"]
    print(f"\n{'─' * 60}")
    print("  종합 점수")
    print(f"{'─' * 60}")
    print(f"  Helpfulness (유용성):     {summary['avg_helpfulness']}/5.0")
    print(f"  Accuracy (정확도):        {summary['avg_accuracy']}/5.0")
    print(f"  Tool Selection (도구선택): {summary['avg_tool_selection']}/5.0")
    print(f"  Overall Score:            {summary['overall_score']}/5.0")
    print(f"  평균 응답 시간:           {summary['avg_response_time_sec']}초")

    print(f"\n{'─' * 60}")
    print("  케이스별 상세")
    print(f"{'─' * 60}")

    for detail in report["details"]:
        scores = detail.get("scores", {})
        print(f"\n  [{detail['test_id']}] {detail['input'][:50]}...")
        print(f"    H={scores.get('helpfulness', {}).get('score', '-')}"
              f"  A={scores.get('accuracy', {}).get('score', '-')}"
              f"  T={scores.get('tool_selection', {}).get('score', '-')}"
              f"  ({detail.get('elapsed_seconds', 0):.1f}s)")
        feedback = scores.get("overall_feedback", "")
        if feedback:
            print(f"    > {feedback}")
        violations = scores.get("violations", [])
        if violations:
            print(f"    [!] 위반: {', '.join(violations)}")

    print(f"\n{'=' * 60}\n")


# ============================================================
# 메인 실행
# ============================================================
def main():
    parser = argparse.ArgumentParser(description="Agent 품질 평가 (LLM-as-Judge)")
    parser.add_argument("--agent-arn", required=True, help="평가할 Agent의 Runtime ARN")
    parser.add_argument(
        "--scenario",
        choices=["recommend", "cs", "demand", "all"],
        default="all",
        help="평가 시나리오 (default: all)",
    )
    parser.add_argument("--output", help="결과 JSON 저장 경로 (선택)")
    args = parser.parse_args()

    # 평가할 시나리오 결정
    if args.scenario == "all":
        scenarios = ["recommend", "cs", "demand"]
    else:
        scenarios = [args.scenario]

    all_reports = {}

    for scenario in scenarios:
        print(f"\n[{scenario.upper()}] 시나리오 평가 시작 ({len(TEST_CASES[scenario])}개 케이스)")
        print("-" * 40)

        results = []
        for i, test_case in enumerate(TEST_CASES[scenario], 1):
            print(f"  [{i}/{len(TEST_CASES[scenario])}] {test_case['id']} 실행 중...", end=" ")
            sys.stdout.flush()

            # Agent 호출
            response, elapsed = invoke_agent(args.agent_arn, test_case)

            # Judge 평가
            scores = judge_response(test_case, response)

            results.append({
                "test_id": test_case["id"],
                "input": test_case["input"],
                "agent_response": response[:500],  # 저장 시 500자 제한
                "elapsed_seconds": round(elapsed, 2),
                "scores": scores,
            })

            overall = (
                scores.get("helpfulness", {}).get("score", 0)
                + scores.get("accuracy", {}).get("score", 0)
                + scores.get("tool_selection", {}).get("score", 0)
            ) / 3
            print(f"완료 (점수: {overall:.1f}/5.0, {elapsed:.1f}s)")

        # 리포트 생성
        report = generate_report(results, scenario, args.agent_arn)
        all_reports[scenario] = report
        print_report(report)

    # JSON 저장 (선택)
    if args.output:
        output_path = args.output
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(all_reports, f, ensure_ascii=False, indent=2)
        print(f"\n결과 저장 완료: {output_path}")


if __name__ == "__main__":
    main()

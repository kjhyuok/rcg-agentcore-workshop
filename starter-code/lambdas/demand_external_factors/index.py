"""
Lambda: demand_external_factors (external_factors)
수요에 영향을 주는 외부 요인 조회 (날씨, 이벤트, 공휴일, 프로모션)
"""
import json

FACTORS = {
    "store-001": {
        "weather": {
            "today": {"temp": 33, "condition": "맑음", "humidity": 65},
            "forecast": [
                {"date": "2026-07-02", "temp_high": 35, "temp_low": 26, "condition": "폭염", "alert": "폭염주의보"},
                {"date": "2026-07-03", "temp_high": 36, "temp_low": 27, "condition": "폭염", "alert": "폭염경보"},
                {"date": "2026-07-04", "temp_high": 34, "temp_low": 25, "condition": "맑음", "alert": None},
                {"date": "2026-07-05", "temp_high": 30, "temp_low": 23, "condition": "흐림", "alert": None},
                {"date": "2026-07-06", "temp_high": 28, "temp_low": 22, "condition": "비", "alert": "강수확률 80%"},
                {"date": "2026-07-07", "temp_high": 31, "temp_low": 24, "condition": "맑음", "alert": None},
                {"date": "2026-07-08", "temp_high": 33, "temp_low": 25, "condition": "맑음", "alert": None},
            ],
        },
        "events": [
            {"date": "2026-07-05", "name": "여름 세일 시작", "type": "프로모션", "expected_impact": "+30% 방문객"},
            {"date": "2026-07-07", "name": "월드컵 예선전", "type": "스포츠", "expected_impact": "맥주/안주류 +50%"},
        ],
        "holidays": [
            {"date": "2026-07-17", "name": "제헌절 (공휴일 아님)", "impact": "평일과 동일"},
        ],
        "promotions": [
            {"name": "1+1 음료 행사", "start": "2026-07-01", "end": "2026-07-07", "category": "음료"},
            {"name": "여름 간식 할인", "start": "2026-07-05", "end": "2026-07-15", "category": "식품"},
        ],
        "demand_impact_summary": "폭염(7/2~3) + 여름세일(7/5) + 1+1행사 → 음료/아이스크림 수요 2배 이상 예상. 7/6 비 예보로 우산/우비 수요. 7/7 월드컵으로 맥주/안주 급증 예상.",
    }
}


def handler(event, context):
    body = json.loads(event.get("body", "{}")) if isinstance(event.get("body"), str) else event
    store_id = body.get("store_id", "store-001")
    forecast_days = body.get("forecast_days", 7)

    store_factors = FACTORS.get(store_id)
    if not store_factors:
        return {"statusCode": 404, "body": json.dumps({"error": f"매장 {store_id}의 외부 요인 데이터 없음"}, ensure_ascii=False)}

    result = {
        "store_id": store_id,
        "forecast_days": forecast_days,
        **store_factors,
    }
    result["weather"]["forecast"] = result["weather"]["forecast"][:forecast_days]

    return {"statusCode": 200, "body": json.dumps(result, ensure_ascii=False)}

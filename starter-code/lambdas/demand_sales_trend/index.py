"""
Lambda: demand_sales_trend (sales_trend)
최근 판매 데이터를 분석하여 트렌드 반환
"""
import json

TRENDS = {
    "store-001": {
        "7d": {
            "period": "최근 7일",
            "summary": "전주 대비 매출 +12% 상승",
            "top_sellers": [
                {"name": "콜드브루 아메리카노", "sold": 180, "growth": "+45%", "trend": "급상승"},
                {"name": "바나나맛 우유", "sold": 95, "growth": "+8%", "trend": "완만상승"},
                {"name": "제주 삼다수 2L", "sold": 220, "growth": "+30%", "trend": "상승"},
            ],
            "declining": [
                {"name": "핫초코 스틱", "sold": 5, "growth": "-60%", "trend": "급하락"},
                {"name": "어묵탕 컵", "sold": 8, "growth": "-45%", "trend": "하락"},
            ],
            "seasonal_factor": "여름 시즌 진입 — 냉음료/아이스크림 수요 급증",
        },
        "30d": {
            "period": "최근 30일",
            "summary": "전월 대비 매출 +8% 상승, 음료 카테고리 견인",
            "category_performance": [
                {"category": "음료", "revenue": 4200000, "growth": "+22%"},
                {"category": "식품", "revenue": 3800000, "growth": "+5%"},
                {"category": "생활용품", "revenue": 1500000, "growth": "-3%"},
            ],
            "insights": [
                "폭염 예보로 음료 매출 급증",
                "도시락류 점심시간 집중 판매 (11:30~13:00)",
                "에너지드링크 심야 판매량 증가 (22:00~02:00)",
            ],
        },
        "90d": {
            "period": "최근 90일",
            "summary": "분기 매출 전년 동기 대비 +15%",
            "monthly_trend": [
                {"month": "4월", "revenue": 8500000},
                {"month": "5월", "revenue": 9200000},
                {"month": "6월", "revenue": 10800000},
            ],
            "key_events": [
                "5월 가정의달 프로모션 효과",
                "6월 여름 시즌 전환 매출 상승",
                "편의점 도시락 리뉴얼 효과",
            ],
        },
    }
}


def handler(event, context):
    body = json.loads(event.get("body", "{}")) if isinstance(event.get("body"), str) else event
    store_id = body.get("store_id", "store-001")
    period = body.get("period", "7d")
    category = body.get("category", "")

    store_trends = TRENDS.get(store_id, {})
    trend_data = store_trends.get(period)

    if not trend_data:
        return {"statusCode": 404, "body": json.dumps({"error": f"매장 {store_id}의 {period} 트렌드 데이터 없음"}, ensure_ascii=False)}

    result = {"store_id": store_id, **trend_data}

    if category and period == "30d":
        cat_data = next((c for c in trend_data.get("category_performance", []) if c["category"] == category), None)
        if cat_data:
            result["filtered_category"] = cat_data

    return {"statusCode": 200, "body": json.dumps(result, ensure_ascii=False)}

"""
Lambda: purchase_history
고객의 최근 구매 이력 조회. 중복 추천 방지용.
"""
import json

PURCHASE_HISTORY = {
    "C001": [
        {"product_id": "P001", "name": "오트밀 프로틴바", "date": "2026-06-10", "qty": 5},
        {"product_id": "P005", "name": "올인원 로션", "date": "2026-06-05", "qty": 1},
        {"product_id": "P008", "name": "프로틴 쉐이크 초코맛", "date": "2026-05-28", "qty": 3},
    ],
    "C002": [
        {"product_id": "P003", "name": "프리미엄 핸드크림 세트", "date": "2026-06-12", "qty": 1},
        {"product_id": "P011", "name": "선크림 SPF50+", "date": "2026-06-01", "qty": 2},
    ],
    "C003": [
        {"product_id": "P009", "name": "즉석밥 오곡밥 3팩", "date": "2026-06-08", "qty": 4},
        {"product_id": "P012", "name": "무선 충전 보조배터리", "date": "2026-05-20", "qty": 1},
    ],
}


def handler(event, context):
    body = json.loads(event.get("body", "{}")) if isinstance(event.get("body"), str) else event
    customer_id = body.get("customer_id", "")

    history = PURCHASE_HISTORY.get(customer_id, [])
    return {"statusCode": 200, "body": json.dumps(history, ensure_ascii=False)}

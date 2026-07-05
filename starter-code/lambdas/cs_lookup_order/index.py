"""
Lambda: cs_lookup_order
주문번호로 주문 상세 조회 (상태, 상품, 결제금액, 배송정보)
"""
import json

ORDERS = {
    "ORD-20260620-001": {
        "order_id": "ORD-20260620-001",
        "customer_id": "C001",
        "status": "DELIVERED",
        "items": [{"name": "유기농 프로틴바 (12개입)", "price": 32000, "quantity": 1}],
        "total_amount": 32000,
        "ordered_at": "2026-06-20",
        "delivered_at": "2026-06-22",
        "payment_method": "신용카드",
    },
    "ORD-20260620-002": {
        "order_id": "ORD-20260620-002",
        "customer_id": "C002",
        "status": "IN_TRANSIT",
        "items": [{"name": "시카 수분크림 50ml", "price": 28000, "quantity": 1}],
        "total_amount": 28000,
        "ordered_at": "2026-06-25",
        "estimated_delivery": "2026-07-02",
        "tracking_number": "CJ123456789",
        "payment_method": "카카오페이",
    },
    "ORD-20260620-003": {
        "order_id": "ORD-20260620-003",
        "customer_id": "C003",
        "status": "DELIVERED",
        "items": [{"name": "고속 보조배터리 20000mAh", "price": 69000, "quantity": 1}],
        "total_amount": 69000,
        "ordered_at": "2026-06-15",
        "delivered_at": "2026-06-17",
        "payment_method": "네이버페이",
    },
    "ORD-20260625-010": {
        "order_id": "ORD-20260625-010",
        "customer_id": "C002",
        "status": "IN_TRANSIT",
        "items": [
            {"name": "히알루론산 세럼", "price": 35000, "quantity": 1},
            {"name": "클렌징 폼", "price": 15000, "quantity": 2},
        ],
        "total_amount": 65000,
        "ordered_at": "2026-06-25",
        "estimated_delivery": "2026-07-03",
        "tracking_number": "HJ987654321",
        "current_location": "서울 송파 물류센터",
        "payment_method": "신용카드",
    },
    "ORD-2024-101": {
        "order_id": "ORD-2024-101",
        "customer_id": "C001",
        "status": "DELIVERED",
        "items": [{"name": "무선 이어폰 (화이트)", "price": 35000, "quantity": 1}],
        "total_amount": 35000,
        "ordered_at": "2026-06-10",
        "delivered_at": "2026-06-12",
        "payment_method": "신용카드",
    },
    "ORD-2024-999": {
        "order_id": "ORD-2024-999",
        "customer_id": "C003",
        "status": "DELIVERED",
        "items": [{"name": "고속 보조배터리 20000mAh", "price": 69000, "quantity": 1}],
        "total_amount": 69000,
        "ordered_at": "2026-06-18",
        "delivered_at": "2026-06-20",
        "payment_method": "네이버페이",
    },
}


def handler(event, context):
    body = json.loads(event.get("body", "{}")) if isinstance(event.get("body"), str) else event
    order_id = body.get("order_id", "")

    order = ORDERS.get(order_id)
    if not order:
        return {"statusCode": 404, "body": json.dumps({"error": f"주문 {order_id}를 찾을 수 없습니다"}, ensure_ascii=False)}

    return {"statusCode": 200, "body": json.dumps(order, ensure_ascii=False)}

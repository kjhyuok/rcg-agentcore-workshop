"""
Lambda: cs_delivery_status
배송 추적 정보 조회 (현재 위치, 예상 도착일)
"""
import json

DELIVERY_INFO = {
    "ORD-20260620-001": {
        "order_id": "ORD-20260620-001",
        "status": "DELIVERED",
        "carrier": "CJ대한통운",
        "tracking_number": "CJ111222333",
        "delivered_at": "2026-06-22 14:30",
        "signed_by": "본인 수령",
    },
    "ORD-20260620-003": {
        "order_id": "ORD-20260620-003",
        "status": "DELIVERED",
        "carrier": "네이버 도착보장",
        "tracking_number": "NV777888999",
        "delivered_at": "2026-06-17 11:00",
        "signed_by": "본인 수령",
    },
    "ORD-2024-101": {
        "order_id": "ORD-2024-101",
        "status": "DELIVERED",
        "carrier": "CJ대한통운",
        "tracking_number": "CJ444555666",
        "delivered_at": "2026-06-12 16:20",
        "signed_by": "본인 수령",
    },
    "ORD-2024-999": {
        "order_id": "ORD-2024-999",
        "status": "DELIVERED",
        "carrier": "네이버 도착보장",
        "tracking_number": "NV111222333",
        "delivered_at": "2026-06-20 13:00",
        "signed_by": "본인 수령",
    },
    "ORD-20260620-002": {
        "order_id": "ORD-20260620-002",
        "status": "IN_TRANSIT",
        "carrier": "CJ대한통운",
        "tracking_number": "CJ123456789",
        "current_location": "서울 강남 배송센터",
        "estimated_delivery": "2026-07-02",
        "history": [
            {"time": "2026-06-25 10:00", "location": "인천 물류센터", "status": "상품 접수"},
            {"time": "2026-06-26 06:00", "location": "서울 송파 허브", "status": "간선 상차"},
            {"time": "2026-06-27 08:00", "location": "서울 강남 배송센터", "status": "배송 출발 예정"},
        ],
    },
    "ORD-20260625-010": {
        "order_id": "ORD-20260625-010",
        "status": "IN_TRANSIT",
        "carrier": "한진택배",
        "tracking_number": "HJ987654321",
        "current_location": "서울 송파 물류센터",
        "estimated_delivery": "2026-07-03",
        "delay_reason": "물량 집중으로 1일 지연",
        "history": [
            {"time": "2026-06-25 15:00", "location": "경기 이천 물류센터", "status": "상품 접수"},
            {"time": "2026-06-26 22:00", "location": "서울 송파 물류센터", "status": "터미널 도착"},
        ],
    },
    "ORD-2024-555": {
        "order_id": "ORD-2024-555",
        "status": "IN_TRANSIT",
        "carrier": "로젠택배",
        "tracking_number": "LG555666777",
        "current_location": "부산 해운대 배송센터",
        "estimated_delivery": "2026-07-01",
        "history": [
            {"time": "2026-06-28 09:00", "location": "서울 중구 물류센터", "status": "상품 접수"},
            {"time": "2026-06-29 05:00", "location": "부산 해운대 배송센터", "status": "간선 도착"},
        ],
    },
}


def handler(event, context):
    body = json.loads(event.get("body", "{}")) if isinstance(event.get("body"), str) else event
    order_id = body.get("order_id", "")

    delivery = DELIVERY_INFO.get(order_id)
    if not delivery:
        return {"statusCode": 404, "body": json.dumps({"error": f"주문 {order_id}의 배송 정보를 찾을 수 없습니다"}, ensure_ascii=False)}

    return {"statusCode": 200, "body": json.dumps(delivery, ensure_ascii=False)}

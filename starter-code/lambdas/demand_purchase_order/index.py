"""
Lambda: demand_purchase_order (purchase_order)
발주 실행. 금액 500,000원 초과 시 needs_approval=true 반환.
"""
import json
from datetime import datetime

def handler(event, context):
    body = json.loads(event.get("body", "{}")) if isinstance(event.get("body"), str) else event
    store_id = body.get("store_id", "store-001")
    items = body.get("items", [])
    urgency = body.get("urgency", "normal")

    if not items:
        return {"statusCode": 400, "body": json.dumps({"error": "발주 항목(items)이 필요합니다"}, ensure_ascii=False)}

    total_amount = sum(item.get("quantity", 0) * item.get("unit_price", 0) for item in items)

    lead_time = "2영업일" if urgency == "urgent" else "3~5영업일"
    order_id = f"PO-{datetime.now().strftime('%Y%m%d')}-{store_id[-3:]}"

    if total_amount > 500000:
        return {
            "statusCode": 200,
            "body": json.dumps({
                "order_id": order_id,
                "store_id": store_id,
                "status": "PENDING_APPROVAL",
                "needs_approval": True,
                "total_amount": total_amount,
                "items": items,
                "urgency": urgency,
                "lead_time": lead_time,
                "message": f"발주 금액 {total_amount:,}원이 500,000원을 초과합니다. 점장 승인이 필요합니다.",
                "approval_required_from": "store-manager",
                "expected_approval_time": "4시간 이내",
            }, ensure_ascii=False),
        }

    return {
        "statusCode": 200,
        "body": json.dumps({
            "order_id": order_id,
            "store_id": store_id,
            "status": "CONFIRMED",
            "needs_approval": False,
            "total_amount": total_amount,
            "items": items,
            "urgency": urgency,
            "lead_time": lead_time,
            "message": f"발주 확정 (총 {total_amount:,}원). 예상 입고: {lead_time}",
            "supplier": "GS리테일 중앙물류센터",
        }, ensure_ascii=False),
    }

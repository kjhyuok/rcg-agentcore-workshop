"""
Lambda: cs_process_return
반품/환불 처리. 5만원 초과 시 needs_escalation=true 반환.
"""
import json

def handler(event, context):
    body = json.loads(event.get("body", "{}")) if isinstance(event.get("body"), str) else event
    order_id = body.get("order_id", "")
    reason = body.get("reason", "단순변심")
    refund_amount = body.get("refund_amount", 0)

    if not order_id:
        return {"statusCode": 400, "body": json.dumps({"error": "order_id가 필요합니다"}, ensure_ascii=False)}

    if refund_amount > 50000:
        return {
            "statusCode": 200,
            "body": json.dumps({
                "order_id": order_id,
                "status": "PENDING_APPROVAL",
                "needs_escalation": True,
                "reason": reason,
                "refund_amount": refund_amount,
                "message": f"환불 금액 {refund_amount:,}원이 50,000원을 초과하여 CS 팀 리더 승인이 필요합니다.",
                "escalation_to": "cs-team-lead",
                "expected_resolution": "24시간 이내 처리",
            }, ensure_ascii=False),
        }

    return {
        "statusCode": 200,
        "body": json.dumps({
            "order_id": order_id,
            "status": "COMPLETED",
            "needs_escalation": False,
            "reason": reason,
            "refund_amount": refund_amount,
            "message": f"환불 {refund_amount:,}원 처리 완료",
            "refund_method": "원래 결제수단으로 3~5영업일 내 환불",
            "return_label": "CJ대한통운 반품 접수번호: RTN-2026-" + order_id[-3:],
        }, ensure_ascii=False),
    }

"""
Lambda: cs_return_policy
상품 카테고리별 반품/교환 정책 조회
"""
import json

POLICIES = {
    "전자기기": {
        "category": "전자기기",
        "return_period_days": 14,
        "conditions": ["미개봉 시 전액 환불", "개봉 후 불량 시 교환/환불 가능", "단순변심 개봉 후 환불 불가"],
        "refund_method": "원래 결제수단으로 3~5영업일 내 환불",
        "notes": "불량 판정 시 택배비 판매자 부담",
    },
    "건강식품": {
        "category": "건강식품",
        "return_period_days": 7,
        "conditions": ["미개봉 시 전액 환불", "개봉 후 환불 불가 (식품 특성상)", "유통기한 임박 상품은 교환만 가능"],
        "refund_method": "원래 결제수단으로 3~5영업일 내 환불",
        "notes": "식품위생법에 따라 개봉 후 반품 제한",
    },
    "뷰티": {
        "category": "뷰티",
        "return_period_days": 14,
        "conditions": ["미개봉 시 전액 환불", "개봉 후 피부 이상 반응 시 환불 가능 (진단서 필요)", "단순변심 개봉 후 환불 불가"],
        "refund_method": "원래 결제수단으로 3~5영업일 내 환불",
        "notes": "화장품법에 따라 개봉 후 반품 제한",
    },
    "간편식": {
        "category": "간편식",
        "return_period_days": 3,
        "conditions": ["냉장/냉동 상품은 수령 당일만 반품 가능", "포장 훼손 시 반품 불가"],
        "refund_method": "원래 결제수단으로 즉시 환불",
        "notes": "신선식품 특성상 반품 기간 제한",
    },
    "생활용품": {
        "category": "생활용품",
        "return_period_days": 30,
        "conditions": ["미사용 시 전액 환불", "사용 후에도 7일 이내 교환 가능", "대형 가전은 설치 후 반품 불가"],
        "refund_method": "원래 결제수단으로 3~5영업일 내 환불",
        "notes": "반품 택배비 고객 부담 (단순변심 시)",
    },
}


def handler(event, context):
    body = json.loads(event.get("body", "{}")) if isinstance(event.get("body"), str) else event
    category = body.get("category", "")

    policy = POLICIES.get(category)
    if not policy:
        categories = list(POLICIES.keys())
        return {"statusCode": 200, "body": json.dumps({"available_categories": categories, "message": f"'{category}' 카테고리를 찾을 수 없습니다. 가능한 카테고리: {', '.join(categories)}"}, ensure_ascii=False)}

    return {"statusCode": 200, "body": json.dumps(policy, ensure_ascii=False)}

"""
Lambda: customer_profile
고객 ID로 프로필(선호도, 알러지, 등급) 조회.
"""
import json

CUSTOMERS = {
    "C001": {"customer_id": "C001", "name": "김건강", "grade": "VIP", "preferences": ["건강식품", "고단백", "유기농"], "allergies": ["견과류"], "age_group": "30대", "gender": "남성"},
    "C002": {"customer_id": "C002", "name": "이뷰티", "grade": "GOLD", "preferences": ["스킨케어", "자연유래", "저자극"], "allergies": [], "age_group": "20대", "gender": "여성"},
    "C003": {"customer_id": "C003", "name": "박바쁨", "grade": "SILVER", "preferences": ["간편식", "올인원", "가성비"], "allergies": ["유제품"], "age_group": "40대", "gender": "남성"},
}


def handler(event, context):
    body = json.loads(event.get("body", "{}")) if isinstance(event.get("body"), str) else event
    customer_id = body.get("customer_id", "")

    customer = CUSTOMERS.get(customer_id)
    if not customer:
        return {"statusCode": 404, "body": json.dumps({"error": f"고객 {customer_id}를 찾을 수 없습니다"}, ensure_ascii=False)}

    return {"statusCode": 200, "body": json.dumps(customer, ensure_ascii=False)}

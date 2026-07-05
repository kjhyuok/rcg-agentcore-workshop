"""
Lambda: product_search
Gateway Target으로 등록되어 Agent가 MCP를 통해 호출합니다.
카테고리/태그 기반 상품 검색. 재고 있는 상품만 반환.
"""
import json

PRODUCTS = {
    "P001": {"product_id": "P001", "name": "오트밀 프로틴바", "category": "건강식품", "price": 2800, "rating": 4.5, "stock": 150, "tags": ["고단백", "식이섬유", "견과류포함"]},
    "P002": {"product_id": "P002", "name": "제로슈거 콜라 500ml", "category": "음료", "price": 1800, "rating": 4.2, "stock": 300, "tags": ["무설탕", "탄산", "다이어트"]},
    "P003": {"product_id": "P003", "name": "프리미엄 핸드크림 세트", "category": "뷰티", "price": 25000, "rating": 4.8, "stock": 80, "tags": ["보습", "선물용", "자연유래"]},
    "P004": {"product_id": "P004", "name": "비타민C 세럼", "category": "뷰티", "price": 35000, "rating": 4.8, "stock": 45, "tags": ["미백", "안티에이징", "저자극"]},
    "P005": {"product_id": "P005", "name": "올인원 로션", "category": "뷰티", "price": 28000, "rating": 4.6, "stock": 60, "tags": ["남성용", "간편", "보습"]},
    "P006": {"product_id": "P006", "name": "콜드브루 아메리카노 250ml", "category": "음료", "price": 3200, "rating": 4.4, "stock": 200, "tags": ["커피", "저칼로리"]},
    "P007": {"product_id": "P007", "name": "유기농 그래놀라", "category": "건강식품", "price": 8900, "rating": 4.3, "stock": 90, "tags": ["유기농", "식이섬유", "견과류포함"]},
    "P008": {"product_id": "P008", "name": "프로틴 쉐이크 초코맛", "category": "건강식품", "price": 3500, "rating": 4.1, "stock": 180, "tags": ["고단백", "운동후", "초코"]},
    "P009": {"product_id": "P009", "name": "즉석밥 오곡밥 3팩", "category": "간편식", "price": 4200, "rating": 4.5, "stock": 250, "tags": ["간편", "건강", "잡곡"]},
    "P010": {"product_id": "P010", "name": "너트 그래놀라 바", "category": "건강식품", "price": 2200, "rating": 4.0, "stock": 120, "tags": ["간식", "견과류포함", "에너지"]},
    "P011": {"product_id": "P011", "name": "선크림 SPF50+", "category": "뷰티", "price": 22000, "rating": 4.7, "stock": 70, "tags": ["자외선차단", "데일리", "저자극"]},
    "P012": {"product_id": "P012", "name": "무선 충전 보조배터리", "category": "전자기기", "price": 35000, "rating": 4.3, "stock": 40, "tags": ["충전", "휴대", "대용량"]},
}


def handler(event, context):
    body = json.loads(event.get("body", "{}")) if isinstance(event.get("body"), str) else event
    category = body.get("category", "")
    tags = body.get("tags", "")

    results = []
    for pid, product in PRODUCTS.items():
        if category and product["category"] != category:
            continue
        if tags:
            tag_list = [t.strip() for t in tags.split(",")]
            if not any(t in product.get("tags", []) for t in tag_list):
                continue
        if product.get("stock", 0) > 0:
            results.append(product)

    return {
        "statusCode": 200,
        "body": json.dumps(results[:5], ensure_ascii=False),
    }

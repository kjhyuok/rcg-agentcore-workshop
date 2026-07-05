"""
Lambda: demand_inventory (inventory_status)
매장의 현재 재고 현황을 카테고리별로 조회
"""
import json

INVENTORY = {
    "store-001": {
        "식품": [
            {"product_id": "P101", "name": "신라면 멀티팩", "stock": 45, "safety_stock": 30, "unit_price": 5000, "status": "정상"},
            {"product_id": "P102", "name": "콜드브루 아메리카노 (10입)", "stock": 8, "safety_stock": 25, "unit_price": 12000, "status": "긴급"},
            {"product_id": "P103", "name": "바나나맛 우유", "stock": 120, "safety_stock": 50, "unit_price": 1500, "status": "정상"},
            {"product_id": "P104", "name": "도시락 (김치볶음밥)", "stock": 5, "safety_stock": 20, "unit_price": 3500, "status": "긴급"},
        ],
        "음료": [
            {"product_id": "P201", "name": "제주 삼다수 2L", "stock": 200, "safety_stock": 100, "unit_price": 1200, "status": "정상"},
            {"product_id": "P202", "name": "코카콜라 제로 500ml", "stock": 12, "safety_stock": 40, "unit_price": 1800, "status": "긴급"},
            {"product_id": "P203", "name": "아이스티 복숭아 1.5L", "stock": 3, "safety_stock": 30, "unit_price": 2500, "status": "긴급"},
            {"product_id": "P204", "name": "에너지드링크 레드불", "stock": 60, "safety_stock": 25, "unit_price": 2800, "status": "정상"},
        ],
        "생활용품": [
            {"product_id": "P301", "name": "핸드워시 리필 1L", "stock": 35, "safety_stock": 15, "unit_price": 4500, "status": "정상"},
            {"product_id": "P302", "name": "물티슈 100매 3팩", "stock": 22, "safety_stock": 20, "unit_price": 5500, "status": "주의"},
        ],
    }
}


def handler(event, context):
    body = json.loads(event.get("body", "{}")) if isinstance(event.get("body"), str) else event
    store_id = body.get("store_id", "store-001")
    category = body.get("category", "")

    store_data = INVENTORY.get(store_id)
    if not store_data:
        return {"statusCode": 404, "body": json.dumps({"error": f"매장 {store_id}를 찾을 수 없습니다"}, ensure_ascii=False)}

    if category:
        items = store_data.get(category, [])
        result = {"store_id": store_id, "category": category, "items": items, "total_items": len(items)}
    else:
        urgent_items = []
        for cat, items in store_data.items():
            for item in items:
                if item["status"] in ("긴급", "주의"):
                    urgent_items.append({**item, "category": cat})
        result = {
            "store_id": store_id,
            "categories": list(store_data.keys()),
            "urgent_items": urgent_items,
            "urgent_count": len(urgent_items),
            "message": f"긴급/주의 품목 {len(urgent_items)}개 발견" if urgent_items else "재고 상태 양호",
        }

    return {"statusCode": 200, "body": json.dumps(result, ensure_ascii=False)}

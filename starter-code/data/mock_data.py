"""
RCG Workshop — 공통 목업 데이터
참가자 git clone 후 Lambda에 이미 배포되어 있는 데이터와 동일합니다.
로컬 테스트 시 참고용으로 제공됩니다.
"""

# ============================================================
# Phase 1: 상품 추천 시나리오
# ============================================================

CUSTOMERS = {
    "C001": {
        "customer_id": "C001",
        "name": "김건강",
        "grade": "VIP",
        "preferences": ["건강식품", "고단백", "유기농"],
        "allergies": ["견과류"],
        "age_group": "30대",
        "gender": "남성",
    },
    "C002": {
        "customer_id": "C002",
        "name": "이뷰티",
        "grade": "GOLD",
        "preferences": ["스킨케어", "자연유래", "저자극"],
        "allergies": [],
        "age_group": "20대",
        "gender": "여성",
    },
    "C003": {
        "customer_id": "C003",
        "name": "박바쁨",
        "grade": "SILVER",
        "preferences": ["간편식", "올인원", "가성비"],
        "allergies": ["유제품"],
        "age_group": "40대",
        "gender": "남성",
    },
}

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

# ============================================================
# Phase 2A: CS 자동화 시나리오
# ============================================================

ORDERS = [
    {
        "order_id": "ORD-20260615-001",
        "customer_id": "C001",
        "customer_name": "김건강",
        "items": [{"product_id": "P001", "name": "오트밀 프로틴바", "qty": 3, "price": 2800}, {"product_id": "P008", "name": "프로틴 쉐이크 초코맛", "qty": 2, "price": 3500}],
        "total": 15400,
        "status": "DELIVERED",
        "delivery_date": "2026-06-17",
        "payment_method": "카드",
    },
    {
        "order_id": "ORD-20260618-002",
        "customer_id": "C002",
        "customer_name": "이뷰티",
        "items": [{"product_id": "P003", "name": "프리미엄 핸드크림 세트", "qty": 1, "price": 25000}, {"product_id": "P011", "name": "선크림 SPF50+", "qty": 2, "price": 22000}],
        "total": 69000,
        "status": "SHIPPING",
        "expected_delivery": "2026-06-20",
        "tracking_number": "CJ1234567890",
        "payment_method": "네이버페이",
    },
    {
        "order_id": "ORD-20260620-003",
        "customer_id": "C003",
        "customer_name": "박바쁨",
        "items": [{"product_id": "P012", "name": "무선 충전 보조배터리", "qty": 1, "price": 35000}],
        "total": 35000,
        "status": "DELIVERED",
        "delivery_date": "2026-06-22",
        "payment_method": "카카오페이",
        "issue": "제품 불량 (충전 안됨)",
    },
]

CS_POLICIES = {
    "return": {"period_days": 7, "condition": "미개봉/미사용 제품만 가능", "refund_method": "원 결제수단 환불 (3~5영업일)", "exceptions": ["식품/음료 개봉 시 불가", "전자기기 개봉 후 불량만 가능"]},
    "exchange": {"period_days": 14, "condition": "동일 상품 색상/사이즈 변경", "shipping_fee": "판매자 귀책 시 무료, 고객 변심 시 3000원"},
    "refund_escalation": {"threshold": 50000, "approval_required": True, "approver": "CS팀장"},
    "compensation": {"delivery_delay": "쿠폰 3000원", "product_defect": "전액 환불 + 쿠폰 5000원", "wrong_item": "즉시 재발송 + 쿠폰 3000원"},
}

# ============================================================
# Phase 2B: 수요 예측 시나리오
# ============================================================

INVENTORY = [
    {"product_id": "P001", "name": "오트밀 프로틴바", "current_stock": 150, "min_stock": 50, "lead_time_days": 2, "daily_avg_sales": 25, "unit_cost": 1800},
    {"product_id": "P002", "name": "제로슈거 콜라 500ml", "current_stock": 300, "min_stock": 100, "lead_time_days": 1, "daily_avg_sales": 45, "unit_cost": 900},
    {"product_id": "P003", "name": "프리미엄 핸드크림 세트", "current_stock": 80, "min_stock": 20, "lead_time_days": 5, "daily_avg_sales": 5, "unit_cost": 12000},
    {"product_id": "P006", "name": "콜드브루 아메리카노 250ml", "current_stock": 200, "min_stock": 80, "lead_time_days": 1, "daily_avg_sales": 60, "unit_cost": 1600},
    {"product_id": "P009", "name": "즉석밥 오곡밥 3팩", "current_stock": 250, "min_stock": 80, "lead_time_days": 2, "daily_avg_sales": 30, "unit_cost": 2800},
    {"product_id": "P010", "name": "프로틴 쉐이크 초코맛", "current_stock": 180, "min_stock": 60, "lead_time_days": 3, "daily_avg_sales": 20, "unit_cost": 2000},
]

SALES_HISTORY = {
    "P001": {"7d": [22, 28, 25, 30, 18, 27, 24], "trend": "stable", "seasonality": "여름 +20%"},
    "P002": {"7d": [40, 42, 55, 60, 48, 52, 45], "trend": "rising", "seasonality": "여름 +40%"},
    "P003": {"7d": [4, 3, 6, 5, 4, 7, 8], "trend": "rising", "seasonality": "연말 +100%"},
    "P006": {"7d": [55, 62, 70, 58, 65, 72, 68], "trend": "rising", "seasonality": "여름 +30%"},
    "P009": {"7d": [28, 32, 30, 25, 35, 28, 33], "trend": "stable", "seasonality": "겨울 +15%"},
    "P010": {"7d": [18, 22, 20, 25, 19, 21, 23], "trend": "rising", "seasonality": "연중 안정"},
}

EXTERNAL_FACTORS = {
    "weather_forecast": {"next_7d": "폭염 (35°C+)", "impact": "음료/아이스크림 +40%, 라면 -20%"},
    "events": [
        {"date": "2026-06-28", "name": "주말", "impact": "전체 +15%"},
        {"date": "2026-07-01", "name": "여름세일 시작", "impact": "전체 +30%"},
    ],
    "nearby_competition": {"status": "경쟁점 리모델링 휴업 중", "impact": "우리 매장 +10%"},
}

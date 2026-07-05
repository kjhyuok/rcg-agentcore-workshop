# RCG Workshop — Starter Code

## Quick Start

```bash
# 1. Clone
git clone <repo-url> && cd rcg-workshop

# 2. 환경 세팅
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 3. AWS 인증 확인
aws sts get-caller-identity

# 4. AgentCore CLI 설치 확인
agentcore --version
```

## 디렉토리 구조

```
starter-code/
├── agents/                    # 참가자가 완성할 Agent 코드
│   ├── phase1_recommend.py    # Phase 1: 상품 추천
│   ├── phase2a_cs.py          # Phase 2A: CS 자동화
│   └── phase2b_demand.py      # Phase 2B: 수요 예측
│
├── lambdas/                   # 사전 배포된 Lambda (Tool 구현체)
│   ├── customer_profile/      # 고객 프로필 조회
│   ├── product_search/        # 상품 검색
│   ├── purchase_history/      # 구매 이력
│   └── ...                    # CS, 수요예측 Tool들
│
├── scripts/                   # 설정 자동화 스크립트
│   ├── setup-gateway.py       # Gateway 생성 + Target 등록
│   ├── setup-memory.py        # Memory 생성 + Strategy 등록
│   └── deploy-agent.sh        # Runtime 배포
│
├── data/                      # 목업 데이터 (참고용)
│   └── mock_data.py
│
└── requirements.txt
```

## Workshop Flow

| Phase | AgentCore 서비스 | 스크립트 |
|-------|-----------------|---------|
| Phase 1 | Runtime + Gateway + Observability | `setup-gateway.py` → `deploy-agent.sh` |
| Phase 2 | + Memory + Policy | `setup-memory.py` |
| Phase 3 | 풀스택 조합 | 직접 구성 |

## 사전 배포된 리소스 (주최측)

- Lambda 함수 11개 (Tool 구현체)
- IAM Role (Gateway/Runtime/Memory 접근용)
- Bedrock Model Access (Claude Sonnet 4.6)
- Workshop Studio 계정

# RCG AgentCore Workshop

Build! Deploy! Observe! 리테일 Agent 실전 구축하기

## Quick Start

```bash
# 1. 클론
git clone https://github.com/kjhyuok/rcg-agentcore-workshop.git
cd rcg-agentcore-workshop

# 2. Python 환경 설정
chmod +x infra/*.sh
./infra/setup-python.sh
source starter-code/.venv/bin/activate

# 3. 인프라 배포 (Lambda + IAM + Mock 사이트)
./infra/onestop.sh w001

# 4. 환경변수 로드
source .env.w001

# 5. Phase 1 시작
cd starter-code
python3 scripts/setup-gateway.py
```

## 구조

```
├── starter-code/       # 참가자 실습 코드
│   ├── agents/         # Agent Python 코드 (Phase 1~3)
│   ├── scripts/        # 설정 스크립트 (Gateway, Memory, Deploy)
│   ├── lambdas/        # Lambda 함수 (사전 배포)
│   └── requirements.txt
├── mock-sites/         # Browser Tool용 Mock 웹사이트
├── infra/              # 인프라 배포 스크립트
│   ├── onestop.sh      # 원스톱 배포
│   ├── setup-python.sh # Python 환경 설정
│   └── cleanup.sh      # 리소스 정리
└── README.md
```

## 정리

```bash
./infra/cleanup.sh
```

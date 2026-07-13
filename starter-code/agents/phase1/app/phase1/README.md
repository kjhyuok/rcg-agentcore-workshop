# Phase 1: 상품 추천 Agent

AgentCore Runtime + Gateway MCP를 활용한 상품 추천 Agent입니다.

## 환경변수

| Variable | Required | Description |
| --- | --- | --- |
| `AGENTCORE_GATEWAY_URL` | Yes | Gateway MCP endpoint URL |
| `AWS_REGION` | No | AWS region (default: us-west-2) |

## 로컬 개발

```bash
agentcore dev --no-browser
agentcore dev invoke --prompt "C001 고객에게 건강식품 추천해줘"
```

## 배포

```bash
../../scripts/deploy-agent.sh phase1
agentcore invoke --prompt "C001 고객에게 건강식품 추천해줘"
```

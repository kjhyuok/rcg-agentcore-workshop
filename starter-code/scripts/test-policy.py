"""
Policy 시연/검증 스크립트 — Gateway Tool을 LLM 없이 직접 호출한다.

왜 직접 호출인가:
  Agent(LLM)를 거치면 LLM이 Tool을 부를지/Browser로 샐지가 매번 달라져
  Policy 차단을 안정적으로 시연하기 어렵다. 이 스크립트는 Gateway MCP
  엔드포인트에 tools/call을 직접(SigV4 서명) 보내므로 LLM 변수가 없고,
  Policy(ENFORCE)의 ALLOW/DENY를 100% 재현 가능하게 보여준다.

사용:
  source ~/workshop/.env.w001
  python3.12 scripts/test-policy.py

동작:
  1) cs_lookup_order (조회)         → Policy permit → 성공 기대
  2) cs_process_return 35,000원     → 5만원 이하   → 성공 기대
  3) cs_process_return 65,000원     → 5만원 초과   → Policy DENY 기대
"""
import os
import json
import urllib.request
import boto3
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest

REGION = os.environ.get("AWS_REGION", "us-west-2")
GATEWAY_URL = os.environ.get("AGENTCORE_GATEWAY_URL", "")
if not GATEWAY_URL:
    raise SystemExit("❌ AGENTCORE_GATEWAY_URL 없음. source ~/workshop/.env.w001 먼저.")

creds = boto3.Session().get_credentials()


def call_tool(tool_name, arguments):
    """Gateway MCP에 tools/call을 SigV4 서명해서 직접 POST."""
    body = json.dumps({
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": tool_name, "arguments": arguments},
    })
    aws_req = AWSRequest(method="POST", url=GATEWAY_URL, data=body,
                         headers={"Content-Type": "application/json",
                                  "Accept": "application/json, text/event-stream"})
    SigV4Auth(creds, "bedrock-agentcore", REGION).add_auth(aws_req)
    req = urllib.request.Request(GATEWAY_URL, data=body.encode(),
                                 headers=dict(aws_req.headers), method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()
    except Exception as e:
        return None, f"ERROR: {e}"


# Gateway Target 이름 → Cedar/MCP tool 이름은 "<target>___<tool>" (언더스코어 3개)
TESTS = [
    ("cs-lookup-order___cs_lookup_order",
     {"order_id": "ORD-2024-101"},
     "조회 (permit 기대 → 성공)"),
    ("cs-process-return___cs_process_return",
     {"order_id": "ORD-2024-101", "reason": "상품 불량", "refund_amount": 35000},
     "환불 35,000원 (5만원 이하 → 성공 기대)"),
    ("cs-process-return___cs_process_return",
     {"order_id": "ORD-2024-101", "reason": "단순 변심", "refund_amount": 65000},
     "환불 65,000원 (5만원 초과 → Policy DENY 기대)"),
]

print(f"🔗 Gateway: {GATEWAY_URL}\n")
for tool, args, label in TESTS:
    print(f"── {label}")
    print(f"   tool={tool} args={args}")
    status, resp = call_tool(tool, args)
    # 응답에 policy/deny/authoriz 흔적이 있으면 차단으로 판단
    blocked = any(k in resp.lower() for k in ["denied", "not authorized", "forbid", "policy"])
    verdict = "🚫 DENY(차단)" if (blocked or (status and status >= 400)) else "✅ ALLOW(허용)"
    print(f"   → HTTP {status} | {verdict}")
    print(f"   응답: {resp[:300]}\n")

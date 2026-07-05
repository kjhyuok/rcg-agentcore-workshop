"""
RCG Workshop — Streamlit 채팅 클라이언트
Agent는 AgentCore Runtime에서 실행되고, 이 앱은 "프론트엔드"만 담당합니다.

실행: streamlit run client_app.py --server.port 8501
"""
import streamlit as st
import boto3
import json
import uuid
import time
from datetime import datetime

# ============================================================
# 설정
# ============================================================
REGION = "us-east-1"
AGENTS = {
    "🛒 상품 추천 Agent": "rcg-recommend-agent",
    "📞 CS 자동화 Agent": "rcg-cs-agent",
    "📦 수요 예측 Agent": "rcg-demand-agent",
}

# ============================================================
# 페이지 설정
# ============================================================
st.set_page_config(
    page_title="RCG AgentCore Workshop",
    page_icon="🤖",
    layout="wide",
)

# ============================================================
# 스타일
# ============================================================
st.markdown("""
<style>
    .stApp { background-color: #0f1219; }
    .main-header {
        background: linear-gradient(135deg, #1a1025, #0f1219);
        padding: 16px 24px;
        border-radius: 12px;
        border: 1px solid rgba(255,153,0,0.2);
        margin-bottom: 20px;
    }
    .trace-panel {
        background: #161b26;
        border: 1px solid #30363d;
        border-radius: 10px;
        padding: 16px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 12px;
        max-height: 600px;
        overflow-y: auto;
    }
    .trace-entry {
        padding: 4px 0;
        border-bottom: 1px solid rgba(255,255,255,0.04);
    }
    .service-badge {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 10px;
        font-weight: 600;
        margin: 2px;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# 세션 상태 초기화
# ============================================================
if "messages" not in st.session_state:
    st.session_state.messages = []
if "traces" not in st.session_state:
    st.session_state.traces = []
if "session_id" not in st.session_state:
    st.session_state.session_id = f"ws-{uuid.uuid4().hex[:12]}-{int(time.time())}"

# ============================================================
# 사이드바
# ============================================================
with st.sidebar:
    st.markdown("### 🤖 AgentCore Workshop")
    st.markdown("---")

    selected_agent = st.selectbox("시나리오 선택", list(AGENTS.keys()))
    agent_runtime_id = AGENTS[selected_agent]

    st.markdown("---")
    st.markdown("#### AgentCore 서비스")
    st.markdown("""
    - 🟢 **Runtime** — Agent 실행 중
    - 🟢 **Gateway** — Tool 연결됨
    - 🟢 **Observability** — Trace 수집 중
    - 🟡 **Memory** — Phase 2에서 활성화
    - 🟡 **Policy** — Phase 2에서 활성화
    """)

    st.markdown("---")
    st.markdown(f"**Session:** `{st.session_state.session_id[:20]}...`")
    st.markdown(f"**Agent:** `{agent_runtime_id}`")
    st.markdown(f"**Region:** `{REGION}`")

    if st.button("🗑️ 대화 초기화"):
        st.session_state.messages = []
        st.session_state.traces = []
        st.session_state.session_id = f"ws-{uuid.uuid4().hex[:12]}-{int(time.time())}"
        st.rerun()

# ============================================================
# 메인 레이아웃: 좌 채팅 / 우 Trace
# ============================================================
col_chat, col_trace = st.columns([3, 2])

# ============================================================
# 좌측: 채팅 패널
# ============================================================
with col_chat:
    st.markdown(f"""
    <div class="main-header">
        <span style="font-size:18px; font-weight:700; color:#fff;">{selected_agent}</span>
        &nbsp;&nbsp;
        <span style="background:#16c784; color:#fff; padding:2px 8px; border-radius:10px; font-size:11px;">● LIVE</span>
        &nbsp;&nbsp;
        <span style="color:#666; font-size:11px;">AgentCore Runtime | {REGION}</span>
    </div>
    """, unsafe_allow_html=True)

    # 채팅 히스토리 표시
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # 사용자 입력
    if prompt := st.chat_input("메시지를 입력하세요..."):
        # 사용자 메시지 추가
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Agent 호출
        with st.chat_message("assistant"):
            with st.spinner("Agent가 생각 중..."):
                try:
                    start_time = time.time()

                    # Trace 기록 시작
                    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                    st.session_state.traces.append(
                        f"[{timestamp}] <span style='color:#527FFF;'>RUNTIME</span> Invoke received | agent: {agent_runtime_id}"
                    )

                    client = boto3.client("bedrock-agentcore", region_name=REGION)
                    resp = client.invoke_agent_runtime(
                        agentRuntimeId=agent_runtime_id,
                        runtimeSessionId=st.session_state.session_id,
                        payload=json.dumps({
                            "message": prompt,
                            "session_id": st.session_state.session_id,
                            "actor_id": "workshop-user",
                        }),
                    )

                    # 응답 파싱
                    response_body = resp["response"].read().decode()
                    result = json.loads(response_body)
                    agent_response = result.get("response", response_body)

                    elapsed = time.time() - start_time

                    # Trace 기록
                    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                    st.session_state.traces.append(
                        f"[{timestamp}] <span style='color:#FF9900;'>GATEWAY</span> Tool calls completed"
                    )
                    st.session_state.traces.append(
                        f"[{timestamp}] <span style='color:#16c784;'>COMPLETE</span> {elapsed*1000:.0f}ms | status: SUCCESS ✓"
                    )

                    st.markdown(agent_response)
                    st.session_state.messages.append({"role": "assistant", "content": agent_response})

                except Exception as e:
                    error_msg = f"⚠️ Agent 호출 실패: {str(e)}"
                    st.error(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})

                    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                    st.session_state.traces.append(
                        f"[{timestamp}] <span style='color:#DD344C;'>ERROR</span> {str(e)[:80]}"
                    )

        st.rerun()

# ============================================================
# 우측: Trace 패널
# ============================================================
with col_trace:
    st.markdown("""
    <div style="display:flex; align-items:center; gap:8px; margin-bottom:12px;">
        <span style="width:8px; height:8px; border-radius:50%; background:#16c784; display:inline-block;"></span>
        <span style="font-size:14px; font-weight:700; color:#fff;">AgentCore Trace</span>
        <span style="font-size:10px; color:#555; margin-left:auto;">실시간</span>
    </div>
    """, unsafe_allow_html=True)

    # 서비스 뱃지
    st.markdown("""
    <div style="margin-bottom:12px;">
        <span class="service-badge" style="background:rgba(82,127,255,0.15); color:#527FFF; border:1px solid rgba(82,127,255,0.3);">Runtime</span>
        <span class="service-badge" style="background:rgba(255,153,0,0.15); color:#FF9900; border:1px solid rgba(255,153,0,0.3);">Gateway</span>
        <span class="service-badge" style="background:rgba(1,168,141,0.15); color:#01A88D; border:1px solid rgba(1,168,141,0.3);">Memory</span>
        <span class="service-badge" style="background:rgba(237,113,0,0.15); color:#ED7100; border:1px solid rgba(237,113,0,0.3);">Observability</span>
        <span class="service-badge" style="background:rgba(221,52,76,0.15); color:#DD344C; border:1px solid rgba(221,52,76,0.3);">Policy</span>
    </div>
    """, unsafe_allow_html=True)

    # Trace 로그
    if st.session_state.traces:
        trace_html = "<div class='trace-panel'>"
        for entry in st.session_state.traces:
            trace_html += f"<div class='trace-entry'>{entry}</div>"
        trace_html += "</div>"
        st.markdown(trace_html, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class='trace-panel' style="color:#555; text-align:center; padding:40px;">
            채팅을 시작하면 여기에 실시간 Trace가 표시됩니다.
        </div>
        """, unsafe_allow_html=True)

    # Observability 링크
    st.markdown("---")
    st.markdown("""
    **📊 상세 Trace 확인:**
    ```bash
    agentcore obs list --name {agent_id} --limit 5
    ```

    **☁️ GenAI Dashboard:**
    CloudWatch → Application Signals → GenAI
    """)

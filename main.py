import asyncio
import os
import uuid

import dotenv

dotenv.load_dotenv()

import streamlit as st
from agents import (
    InputGuardrailTripwireTriggered,
    OutputGuardrailTripwireTriggered,
    Runner,
    SQLiteSession,
)

# Streamlit Cloud: st.secrets에 등록된 값을 환경변수로 승격.
# OpenAI SDK가 os.environ["OPENAI_API_KEY"]를 읽으므로 이 브리지가 필요하다.
try:
    if "OPENAI_API_KEY" in st.secrets and not os.environ.get("OPENAI_API_KEY"):
        os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]
except (FileNotFoundError, KeyError):
    # 로컬 개발 환경에 secrets.toml이 없을 때 발생. .env로 충분하므로 무시.
    pass

from models import CustomerContext
from my_agents.triage_agent import triage_agent


st.set_page_config(page_title="🍝 Restaurant Bot", page_icon="🍝")
st.title("🍝 Restaurant Bot")
st.caption("Triage → Menu / Order / Reservation 에이전트 핸드오프 데모")


# 데모용 고정 컨텍스트 (실제에서는 로그인 기반)
customer_ctx = CustomerContext(
    customer_id=1,
    name="지호",
    phone="010-1234-5678",
    dietary_restrictions=[],
)


# 세션 초기화 — 사용자별 고유 키로 DB 내 대화 격리
# Streamlit Cloud에서 여러 사용자가 같은 DB를 공유해도 세션 키가 다르면 레코드가 섞이지 않는다.
if "session_key" not in st.session_state:
    st.session_state["session_key"] = f"restaurant-chat-{uuid.uuid4().hex[:12]}"
if "session" not in st.session_state:
    st.session_state["session"] = SQLiteSession(
        st.session_state["session_key"],
        "restaurant-memory.db",
    )
if "agent" not in st.session_state:
    st.session_state["agent"] = triage_agent
if "messages" not in st.session_state:
    st.session_state["messages"] = []

session = st.session_state["session"]


# 이전 대화 렌더링 (assistant 메시지에는 당시 응답한 에이전트 이름 뱃지 표시)
for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"]):
        if msg["role"] == "assistant" and msg.get("agent"):
            st.caption(f"🤖 {msg['agent']}")
        st.markdown(msg["content"])


async def run_agent(user_input: str):
    """현재 활성 에이전트로 사용자 입력을 실행하고 응답을 스트리밍."""
    active_agent_name = st.session_state["agent"].name
    result = Runner.run_streamed(
        st.session_state["agent"],
        user_input,
        session=session,
        context=customer_ctx,
    )

    with st.chat_message("assistant"):
        st.caption(f"🤖 {active_agent_name}")
        placeholder = st.empty()
        buffer = ""
        try:
            async for event in result.stream_events():
                # raw_response_event에는 tool call arguments 델타도 섞여 들어온다.
                # 'response.output_text.delta'만 채팅창 버퍼에 쌓는다.
                if event.type == "raw_response_event":
                    data = getattr(event, "data", None)
                    if getattr(data, "type", "") != "response.output_text.delta":
                        continue
                    delta = getattr(data, "delta", None)
                    if isinstance(delta, str) and delta:
                        buffer += delta
                        placeholder.markdown(buffer + "▌")
            placeholder.markdown(buffer)

        except InputGuardrailTripwireTriggered as e:
            verdict = e.guardrail_result.output.output_info
            if verdict.has_inappropriate_language:
                msg = "⚠️ 부적절한 언어가 감지되었습니다. 정중한 표현으로 다시 말씀해 주세요."
            else:
                msg = "저는 레스토랑 관련 문의(메뉴/주문/예약/불만)만 도와드릴 수 있어요. 🍝"
            placeholder.warning(msg)
            buffer = msg
            with st.sidebar:
                st.error(f"🛑 Input guardrail: {verdict.reason}")

        except OutputGuardrailTripwireTriggered as e:
            msg = "잠시만요, 응답을 다시 정리하고 있어요. (내부 점검에 걸림)"
            placeholder.warning(msg)
            buffer = msg
            with st.sidebar:
                st.error(f"🛑 Output guardrail: {e.guardrail_result.output.output_info.reason}")
            # 역할 침범이 감지됐으니 triage로 복귀
            st.session_state["agent"] = triage_agent
            st.session_state["messages"].append(
                {"role": "assistant", "content": buffer, "agent": active_agent_name}
            )
            return

    # 핸드오프가 있었다면 last_agent가 전문 에이전트로 바뀌어 다음 턴에 이어짐
    st.session_state["agent"] = result.last_agent
    st.session_state["messages"].append(
        {"role": "assistant", "content": buffer, "agent": active_agent_name}
    )


user_input = st.chat_input("무엇을 도와드릴까요? (예: 채식 메뉴 알려줘 / 파스타 주문할게 / 예약하고 싶어)")
if user_input:
    st.session_state["messages"].append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)
    asyncio.run(run_agent(user_input))


# 사이드바: 디버그/리셋
with st.sidebar:
    st.subheader("🔍 세션 정보")
    st.write(f"현재 활성 에이전트: **{st.session_state['agent'].name}**")
    st.write(f"고객: {customer_ctx.name} (ID: {customer_ctx.customer_id})")
    st.divider()
    if st.button("🔄 대화 초기화"):
        asyncio.run(session.clear_session())
        # 새 세션 키 발급 — 동일 DB 안에서도 새 대화 공간 시작
        st.session_state["session_key"] = f"restaurant-chat-{uuid.uuid4().hex[:12]}"
        st.session_state["session"] = SQLiteSession(
            st.session_state["session_key"],
            "restaurant-memory.db",
        )
        st.session_state["agent"] = triage_agent
        st.session_state["messages"] = []
        st.rerun()
    st.divider()
    st.subheader("📜 이벤트 로그")

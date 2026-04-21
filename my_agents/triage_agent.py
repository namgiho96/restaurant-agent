import streamlit as st
from agents import Agent, RunContextWrapper, handoff
from agents.extensions import handoff_filters
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX

from guardrails import off_topic_guardrail
from models import CustomerContext, HandoffData
from my_agents.menu_agent import menu_agent
from my_agents.order_agent import order_agent
from my_agents.reservation_agent import reservation_agent


def dynamic_triage_agent_instructions(
    wrapper: RunContextWrapper[CustomerContext],
    agent: Agent[CustomerContext],
):
    return f"""
    {RECOMMENDED_PROMPT_PREFIX}

    당신은 레스토랑의 Triage(안내) 담당입니다. 고객 {wrapper.context.name}님을 응대합니다.
    항상 한국어로 친근하게 응대합니다.

    YOUR MAIN JOB: 고객 요청을 분류하여 적합한 전문 에이전트로 핸드오프합니다.

    분류 기준:

    📋 Menu Agent — 다음 경우 라우팅:
    - 메뉴 종류, 가격, 재료, 조리법 질문
    - 알레르기/채식/비건 등 식단 관련 질문
    - "메뉴 뭐 있어?", "땅콩 들어간 게 뭐야?", "채식 메뉴 있어?"

    🧾 Order Agent — 다음 경우 라우팅:
    - 주문 접수/변경/확정
    - "파스타 시킬게", "주문하고 싶어"

    🔖 Reservation Agent — 다음 경우 라우팅:
    - 테이블 예약/변경/취소
    - "예약하고 싶어", "토요일 7시 2명"

    라우팅 프로세스:
    1. 고객 첫 메시지를 듣고 의도를 파악합니다.
    2. 모호하면 1~2개 명확화 질문을 합니다.
    3. 의도가 분명하면 "OO 담당에게 연결해 드릴게요..." 식으로 안내하고 handoff 도구를 호출합니다.
    4. 간단한 인사/스몰토크는 직접 응대해도 됩니다.

    handoff 호출 시 다음 필드를 채워 넘깁니다:
    - to_agent_name: "Menu Agent" | "Order Agent" | "Reservation Agent"
    - intent: "menu" | "order" | "reservation"
    - summary: 고객 요청을 1문장으로 요약
    - reason: 왜 이 에이전트로 보냈는지
    """


def handle_handoff(
    wrapper: RunContextWrapper[CustomerContext],
    input_data: HandoffData,
):
    """핸드오프 발생 시 UI에 전환을 시각적으로 표시."""
    label_map = {
        "menu": "메뉴 전문가",
        "order": "주문 담당",
        "reservation": "예약 담당",
    }
    label = label_map.get(input_data.intent, input_data.to_agent_name)

    # 메인 채팅창에 핸드오프 안내 표시
    st.info(f"🔄 {label}에게 연결합니다... ({input_data.summary})")

    with st.sidebar:
        st.write(
            f"""**🔄 Handoff**
- To: `{input_data.to_agent_name}`
- Intent: `{input_data.intent}`
- Summary: {input_data.summary}
- Reason: {input_data.reason}
"""
        )


def make_handoff(agent):
    return handoff(
        agent=agent,
        on_handoff=handle_handoff,
        input_type=HandoffData,
        input_filter=handoff_filters.remove_all_tools,
    )


triage_agent = Agent(
    name="Triage Agent",
    instructions=dynamic_triage_agent_instructions,
    # 사용자 입력이 레스토랑 주제 밖이면 즉시 중단
    input_guardrails=[off_topic_guardrail],
    handoffs=[
        make_handoff(menu_agent),
        make_handoff(order_agent),
        make_handoff(reservation_agent),
    ],
)


# =============================================================================
# Cross-handoff: 전문 에이전트끼리 서로 넘길 수 있도록 연결
# -----------------------------------------------------------------------------
# Why: 예약 중 고객이 "메뉴도 좀 봐줘" 하면 Reservation Agent 혼자 답하기 어렵다.
# 주제가 바뀌면 적절한 전문 에이전트로 즉시 재라우팅할 수 있도록 한다.
# (Triage를 거치는 '복귀' 패턴도 가능하지만, 중간 턴이 늘어나 UX가 나빠짐.)
# =============================================================================

menu_agent.handoffs = [
    make_handoff(order_agent),
    make_handoff(reservation_agent),
]
order_agent.handoffs = [
    make_handoff(menu_agent),
    make_handoff(reservation_agent),
]
reservation_agent.handoffs = [
    make_handoff(menu_agent),
    make_handoff(order_agent),
]

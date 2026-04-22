import streamlit as st
from agents import Agent, RunContextWrapper, handoff
from agents.extensions import handoff_filters
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX

from guardrails import off_topic_guardrail
from models import CustomerContext, HandoffData
from my_agents.complaints_agent import complaints_agent
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

    😤 Complaints Agent — 다음 경우 라우팅:
    - 음식 품질, 서비스, 직원 태도에 대한 불만
    - "별로였어", "불친절했어", "실망했어", "환불하고 싶어"
    - 부정적 경험이 포함된 모든 피드백
    - 반드시 먼저 공감을 표현한 뒤 핸드오프: "정말 죄송합니다. 불만 전담 상담사에게 연결해 드릴게요..."

    라우팅 프로세스:
    1. 고객 첫 메시지를 듣고 의도를 파악합니다.
    2. 모호하면 1~2개 명확화 질문을 합니다.
    3. 의도가 분명하면 "OO 담당에게 연결해 드릴게요..." 식으로 안내하고 handoff 도구를 호출합니다.
    4. 간단한 인사/스몰토크는 직접 응대해도 됩니다.

    handoff 호출 시 다음 필드를 채워 넘깁니다:
    - to_agent_name: "Menu Agent" | "Order Agent" | "Reservation Agent" | "Complaints Agent"
    - intent: "menu" | "order" | "reservation" | "complaint"
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
        "complaint": "불만 전담 상담사",
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
    input_guardrails=[off_topic_guardrail],
    handoffs=[
        make_handoff(menu_agent),
        make_handoff(order_agent),
        make_handoff(reservation_agent),
        make_handoff(complaints_agent),
    ],
)


# Cross-handoff: 전문 에이전트끼리 직접 재라우팅 (Triage 경유 없이 UX 단축)

menu_agent.handoffs = [
    make_handoff(order_agent),
    make_handoff(reservation_agent),
    make_handoff(complaints_agent),
]
order_agent.handoffs = [
    make_handoff(menu_agent),
    make_handoff(reservation_agent),
    make_handoff(complaints_agent),
]
reservation_agent.handoffs = [
    make_handoff(menu_agent),
    make_handoff(order_agent),
    make_handoff(complaints_agent),
]
complaints_agent.handoffs = [
    make_handoff(menu_agent),
    make_handoff(order_agent),
    make_handoff(reservation_agent),
]

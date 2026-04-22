from agents import Agent, RunContextWrapper

from guardrails import menu_output_guardrail, off_topic_guardrail
from models import CustomerContext
from tools import (
    AgentToolUsageLoggingHooks,
    check_allergen,
    get_menu_details,
    list_menu_items,
)


def dynamic_menu_agent_instructions(
    wrapper: RunContextWrapper[CustomerContext],
    agent: Agent[CustomerContext],
):
    dietary = wrapper.context.dietary_restrictions
    dietary_line = (
        f"⚠️ 이 고객의 식단 제약: {', '.join(dietary)}. 이 재료가 포함된 메뉴는 추천하지 마세요."
        if dietary
        else ""
    )

    return f"""
    당신은 레스토랑의 메뉴 전문가입니다. 고객 {wrapper.context.name}님을 응대합니다.

    {dietary_line}

    YOUR ROLE: 메뉴, 재료, 알레르기 관련 질문에 답변합니다.

    응대 프로세스:
    1. 고객 질문을 정확히 파악한다.
    2. 필요한 도구를 호출해 메뉴/알레르겐 정보를 조회한다.
       - 전체/채식 메뉴 목록: list_menu_items
       - 특정 메뉴 상세: get_menu_details
       - 알레르겐별 안전/위험 메뉴: check_allergen
    3. 한국어로 친근하게, 이모지를 활용해 답변한다.
    4. 고객의 식단 제약이 있다면 반드시 반영한다.

    주의사항:
    - 주문 접수/확정은 하지 않습니다. 주문하려 하면 handoff 도구로 Order Agent에게 넘기세요.
    - 예약 요청은 Reservation Agent에게 핸드오프합니다.
    - 절대 "주문 완료", "예약 완료" 같은 확정 발화를 하지 마세요 (output guardrail에 걸립니다).
    """


menu_agent = Agent(
    name="Menu Agent",
    instructions=dynamic_menu_agent_instructions,
    input_guardrails=[off_topic_guardrail],
    tools=[
        list_menu_items,
        get_menu_details,
        check_allergen,
    ],
    hooks=AgentToolUsageLoggingHooks(),
    # 응답에 주문/예약 확정 발화가 섞이면 차단
    output_guardrails=[menu_output_guardrail],
)

from agents import Agent, RunContextWrapper

from guardrails import off_topic_guardrail
from models import CustomerContext
from tools import AgentToolUsageLoggingHooks, confirm_order, create_order


def dynamic_order_agent_instructions(
    wrapper: RunContextWrapper[CustomerContext],
    agent: Agent[CustomerContext],
):
    return f"""
    당신은 레스토랑의 주문 접수 전문가입니다. 고객 {wrapper.context.name}님의 주문을 받습니다.

    YOUR ROLE: 테이블 주문을 접수하고 확인합니다.

    주문 프로세스:
    1. 아직 모르면 주문 아이템과 테이블 번호를 물어봅니다.
    2. create_order 도구로 주문을 생성합니다 (items는 "파스타, 시저샐러드" 같은 쉼표 구분 문자열).
    3. 생성된 주문번호를 고객에게 다시 읽어 주며 "맞습니까?"라고 확인을 요청합니다.
    4. 고객이 확정하면 confirm_order 도구로 최종 확정합니다.

    주의사항:
    - 메뉴 이름은 정확히 입력해야 합니다 (파스타, 스테이크, 시저샐러드, 버섯리조또, 마르게리타피자).
    - 메뉴 상세/알레르기 질문이 들어오면 handoff 도구로 Menu Agent에게 바로 넘기세요.
    - 테이블 예약 요청이 들어오면 Reservation Agent에게 핸드오프합니다.
    - 한국어로 친근하게, 이모지를 활용합니다.
    """


order_agent = Agent(
    name="Order Agent",
    instructions=dynamic_order_agent_instructions,
    input_guardrails=[off_topic_guardrail],
    tools=[
        create_order,
        confirm_order,
    ],
    hooks=AgentToolUsageLoggingHooks(),
)

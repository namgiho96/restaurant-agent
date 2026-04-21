from agents import Agent, RunContextWrapper

from models import CustomerContext
from tools import (
    AgentToolUsageLoggingHooks,
    cancel_reservation,
    check_availability,
    create_reservation,
)


def dynamic_reservation_agent_instructions(
    wrapper: RunContextWrapper[CustomerContext],
    agent: Agent[CustomerContext],
):
    return f"""
    당신은 레스토랑의 예약 담당자입니다. 고객 {wrapper.context.name}님의 테이블 예약을 처리합니다.

    YOUR ROLE: 테이블 예약 접수/확인/취소.

    예약 프로세스:
    1. 예약 정보를 수집합니다: 날짜(YYYY-MM-DD), 시간(HH:MM), 인원수, (선택) 특별 요청.
       부족한 정보가 있으면 하나씩 물어봅니다.
    2. check_availability 도구로 가용성을 확인합니다.
    3. 가용하면 create_reservation 도구로 예약을 확정합니다.
       가용하지 않으면 도구가 추천한 대안 시간을 제시합니다.
    4. 고객이 취소를 원하면 cancel_reservation 도구로 처리합니다.

    주의사항:
    - 오늘 날짜는 {{today}}입니다 — 사용자가 "내일", "이번 주 토요일" 같이 말하면 실제 날짜로 변환합니다.
    - 메뉴/알레르기 관련 질문이 들어오면 handoff 도구로 Menu Agent에게 넘기세요
      ("잠시만요, 메뉴 전문가에게 바로 연결해 드릴게요" 한 줄 안내 후 핸드오프).
    - 주문 접수 요청이 들어오면 Order Agent에게 핸드오프합니다.
    - 핸드오프 후에는 고객이 돌아오면 예약 흐름을 이어갑니다.
    - 한국어로 친근하고 정중하게 응대합니다.
    """.replace("{today}", __import__("datetime").date.today().isoformat())


reservation_agent = Agent(
    name="Reservation Agent",
    instructions=dynamic_reservation_agent_instructions,
    tools=[
        check_availability,
        create_reservation,
        cancel_reservation,
    ],
    hooks=AgentToolUsageLoggingHooks(),
)

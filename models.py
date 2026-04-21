from pydantic import BaseModel
from typing import Optional


class CustomerContext(BaseModel):

    customer_id: int
    name: str
    phone: Optional[str] = None
    # 알레르기 등 식단 제약 (예: "땅콩", "글루텐")
    dietary_restrictions: list[str] = []


class HandoffData(BaseModel):
    """Triage → 전문 에이전트 핸드오프 시 전달되는 구조화 데이터."""

    to_agent_name: str
    intent: str  # "menu" | "order" | "reservation"
    summary: str  # 고객 요청 요약
    reason: str  # 이 에이전트로 라우팅한 이유


class InputGuardRailOutput(BaseModel):
    """Input guardrail 판정 결과. 레스토랑 주제가 아니면 is_off_topic=True."""

    is_off_topic: bool
    reason: str


class MenuOutputGuardRailOutput(BaseModel):
    """Menu Agent 응답이 본인 역할을 벗어났는지 판정."""

    contains_order_confirmation: bool  # 주문을 확정한 것처럼 말하는가
    contains_reservation_confirmation: bool  # 예약을 확정한 것처럼 말하는가
    reason: str

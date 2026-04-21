import random
from datetime import datetime

import streamlit as st
from agents import Agent, AgentHooks, RunContextWrapper, Tool, function_tool

from models import CustomerContext


# =============================================================================
# MENU TOOLS
# =============================================================================

# 간단한 하드코딩 메뉴 DB
MENU_DB = {
    "파스타": {
        "price": 18000,
        "ingredients": ["면", "토마토소스", "마늘", "올리브오일", "파마산치즈"],
        "allergens": ["글루텐", "유제품"],
        "vegetarian": True,
    },
    "스테이크": {
        "price": 42000,
        "ingredients": ["소고기", "버터", "로즈마리", "마늘"],
        "allergens": ["유제품"],
        "vegetarian": False,
    },
    "시저샐러드": {
        "price": 14000,
        "ingredients": ["로메인", "파마산치즈", "크루통", "시저드레싱"],
        "allergens": ["글루텐", "유제품", "계란"],
        "vegetarian": True,
    },
    "버섯리조또": {
        "price": 22000,
        "ingredients": ["쌀", "버섯", "버터", "파마산치즈"],
        "allergens": ["유제품"],
        "vegetarian": True,
    },
    "마르게리타피자": {
        "price": 20000,
        "ingredients": ["도우", "토마토소스", "모짜렐라", "바질"],
        "allergens": ["글루텐", "유제품"],
        "vegetarian": True,
    },
}


@function_tool
def list_menu_items(vegetarian_only: bool = False) -> str:
    """전체 메뉴를 조회합니다.

    Args:
        vegetarian_only: True면 채식 메뉴만 필터링
    """
    items = []
    for name, info in MENU_DB.items():
        if vegetarian_only and not info["vegetarian"]:
            continue
        veg_mark = "🌱" if info["vegetarian"] else "🍖"
        items.append(f"{veg_mark} {name} - {info['price']:,}원")

    if not items:
        return "해당 조건의 메뉴가 없습니다."
    header = "🌱 채식 메뉴 목록:" if vegetarian_only else "📋 전체 메뉴:"
    return header + "\n" + "\n".join(items)


@function_tool
def get_menu_details(item_name: str) -> str:
    """특정 메뉴의 재료/알레르겐 상세 정보를 조회합니다.

    Args:
        item_name: 메뉴 이름 (예: "파스타")
    """
    info = MENU_DB.get(item_name)
    if not info:
        return f"'{item_name}' 메뉴를 찾을 수 없습니다. 메뉴 목록을 확인해 주세요."
    return (
        f"🍽️ {item_name}\n"
        f"💰 가격: {info['price']:,}원\n"
        f"🥬 재료: {', '.join(info['ingredients'])}\n"
        f"⚠️ 알레르겐: {', '.join(info['allergens']) or '없음'}\n"
        f"🌱 채식: {'가능' if info['vegetarian'] else '불가'}"
    )


@function_tool
def check_allergen(allergen: str) -> str:
    """특정 알레르겐이 포함된 메뉴와 포함되지 않은 메뉴를 반환합니다.

    Args:
        allergen: 확인하려는 알레르겐 (예: "글루텐")
    """
    contains, safe = [], []
    for name, info in MENU_DB.items():
        if allergen in info["allergens"]:
            contains.append(name)
        else:
            safe.append(name)
    return (
        f"⚠️ '{allergen}' 포함 메뉴: {', '.join(contains) or '없음'}\n"
        f"✅ '{allergen}' 안전 메뉴: {', '.join(safe) or '없음'}"
    )


# =============================================================================
# ORDER TOOLS
# =============================================================================


@function_tool
def create_order(
    wrapper: RunContextWrapper[CustomerContext],
    items: str,
    table_number: int,
) -> str:
    """주문을 생성합니다.

    Args:
        items: 쉼표로 구분된 주문 아이템 (예: "파스타, 시저샐러드")
        table_number: 테이블 번호
    """
    order_list = [item.strip() for item in items.split(",") if item.strip()]
    total = 0
    lines = []
    unknown = []
    for item in order_list:
        info = MENU_DB.get(item)
        if not info:
            unknown.append(item)
            continue
        total += info["price"]
        lines.append(f"  • {item} - {info['price']:,}원")

    if unknown:
        return f"❌ 메뉴에 없는 항목이 있습니다: {', '.join(unknown)}"

    order_id = f"ORD-{random.randint(10000, 99999)}"
    return (
        f"✅ 주문이 접수되었습니다\n"
        f"🧾 주문번호: {order_id}\n"
        f"🪑 테이블: {table_number}번\n"
        f"👤 고객: {wrapper.context.name}\n"
        f"📝 주문 내역:\n" + "\n".join(lines) + f"\n"
        f"💰 합계: {total:,}원\n"
        f"⏰ 예상 조리 시간: 15~20분"
    )


@function_tool
def confirm_order(order_id: str) -> str:
    """고객에게 주문을 최종 확정합니다.

    Args:
        order_id: 주문번호 (예: "ORD-12345")
    """
    return f"🎉 주문 {order_id} 확정 완료! 잠시만 기다려 주세요."


# =============================================================================
# RESERVATION TOOLS
# =============================================================================


@function_tool
def check_availability(date: str, time: str, party_size: int) -> str:
    """해당 일시 테이블 가용성을 확인합니다.

    Args:
        date: 예약 날짜 (YYYY-MM-DD)
        time: 예약 시간 (HH:MM)
        party_size: 인원수
    """
    # mock: 짝수 시간이면 가능, 홀수면 다음 슬롯 제안
    hour = int(time.split(":")[0]) if ":" in time else 0
    if hour % 2 == 0:
        return f"✅ {date} {time} / {party_size}명 — 예약 가능합니다."
    return (
        f"⚠️ {date} {time}는 만석입니다. "
        f"대신 {hour + 1:02d}:00 슬롯을 추천드립니다."
    )


@function_tool
def create_reservation(
    wrapper: RunContextWrapper[CustomerContext],
    date: str,
    time: str,
    party_size: int,
    special_requests: str = "",
) -> str:
    """테이블 예약을 확정합니다.

    Args:
        date: 예약 날짜 (YYYY-MM-DD)
        time: 예약 시간 (HH:MM)
        party_size: 인원수
        special_requests: 특별 요청사항
    """
    reservation_id = f"RSV-{random.randint(10000, 99999)}"
    return (
        f"✅ 예약이 확정되었습니다\n"
        f"🔖 예약번호: {reservation_id}\n"
        f"👤 예약자: {wrapper.context.name}"
        f"{f' ({wrapper.context.phone})' if wrapper.context.phone else ''}\n"
        f"📅 일시: {date} {time}\n"
        f"👥 인원: {party_size}명\n"
        f"📝 요청사항: {special_requests or '없음'}\n"
        f"📞 변경/취소는 매장으로 연락 부탁드립니다."
    )


@function_tool
def cancel_reservation(reservation_id: str) -> str:
    """예약을 취소합니다.

    Args:
        reservation_id: 예약번호
    """
    return f"✅ 예약 {reservation_id}가 취소되었습니다."


# =============================================================================
# AGENT HOOKS — UI에 도구 사용/핸드오프 로그 표시
# =============================================================================


class AgentToolUsageLoggingHooks(AgentHooks):

    async def on_tool_start(
        self,
        context: RunContextWrapper[CustomerContext],
        agent: Agent[CustomerContext],
        tool: Tool,
    ):
        with st.sidebar:
            st.write(f"🔧 **{agent.name}** 도구 호출: `{tool.name}`")

    async def on_tool_end(
        self,
        context: RunContextWrapper[CustomerContext],
        agent: Agent[CustomerContext],
        tool: Tool,
        result: str,
    ):
        with st.sidebar:
            st.write(f"✅ **{agent.name}** 도구 완료: `{tool.name}`")
            with st.expander("결과 보기"):
                st.code(result)

    async def on_handoff(
        self,
        context: RunContextWrapper[CustomerContext],
        agent: Agent[CustomerContext],
        source: Agent[CustomerContext],
    ):
        with st.sidebar:
            st.write(f"🔄 핸드오프: **{source.name}** → **{agent.name}**")

    async def on_start(
        self,
        context: RunContextWrapper[CustomerContext],
        agent: Agent[CustomerContext],
    ):
        with st.sidebar:
            st.write(f"🚀 **{agent.name}** 시작")

    async def on_end(
        self,
        context: RunContextWrapper[CustomerContext],
        agent: Agent[CustomerContext],
        output,
    ):
        with st.sidebar:
            st.write(f"🏁 **{agent.name}** 종료")

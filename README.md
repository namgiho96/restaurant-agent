# Restaurant Bot

OpenAI Agents SDK의 **handoff** 기능을 사용해 4개 에이전트가 협력하는 레스토랑 상담 봇.

## 에이전트 구성

- **Triage Agent** — 고객 요청을 파악하여 전문 에이전트로 라우팅
- **Menu Agent** — 메뉴, 재료, 알레르기 질문 응대
- **Order Agent** — 주문 접수 및 확인
- **Reservation Agent** — 테이블 예약 처리

## 실행

```bash
uv sync
echo "OPENAI_API_KEY=..." > .env
uv run streamlit run main.py
```

## 흐름

1. 사용자가 채팅 입력
2. Triage Agent가 의도 분류 → `handoff()`로 전문 에이전트 호출
3. 사이드바에 "메뉴 전문가에게 연결합니다..." 형태로 핸드오프 표시
4. 전문 에이전트가 `function_tool`을 호출해 응답

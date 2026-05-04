# Architecture

## 시스템 구성
<img width="1440" height="1040" alt="image" src="https://github.com/user-attachments/assets/7dfce89c-782e-4239-9f34-93cb65ab95e9" />

<br>

| 서비스 | 노출 |
|---|---|
| course-agent | public |
| pgvector | internal |
| facility-mcp | internal |

서비스 간 통신은 Railway internal DNS (`facility-mcp.railway.internal:8001`).


## 멀티에이전트 그래프
<img width="1440" height="1440" alt="image" src="https://github.com/user-attachments/assets/5ee3dbc9-10d8-4b8b-bf37-7e73299da626" />

<br>

| 노드 | 역할 |
|---|---|
| Supervisor | LLM 의도 분류 → `routing_mode`, `agent_plan` 결정 |
| Dispatcher | passthrough, 조건부 엣지로 다음 에이전트 라우팅 |
| Sub-agent | 도메인 도구 실행, `agent_outputs[name]` 기록 |
| Aggregator | 결과 검증(`is_valid`), `current_agent_index++` |
| Reroute Supervisor | 휴리스틱 매핑으로 새 에이전트 추가 |
| Response | 최종 자연어 응답 (SSE 토큰 스트리밍) |

<br>

## Self-Correction 재라우팅

**트리거**: `single_agent` AND `is_valid=False` AND `rerouting_count==0`

**휴리스틱 매핑** (LLM 미사용):
lesson     → faq
faq        → lesson
enrollment → lesson
facility   → lesson

1회만 발동. 재라우팅 후 실패하면 그대로 Response.

**예시**: "야구 입문반 있어?"
Supervisor → single_agent: [lesson]
lesson → 결과 0건, is_valid=False
Reroute → faq 추가, plan=[lesson, faq]
faq → RAG 검색 성공
Response → "야구 입문반은 없지만..."
tool_used: "lesson,faq"

<br>

## MCP 양방향

### 서버 (`mcp_servers/facility_server/`)
FastMCP로 `search_facilities` 도구 노출. 내부 흐름: KSPO API 호출 → 응답 정규화 → (좌표 시) haversine 거리 정렬 → TTL 캐시.

### 클라이언트 (`server/app/services/ai/mcp_client.py`)
`fastmcp.Client`로 facility-mcp의 `search_facilities` 호출. URL은 환경별로:

| 환경 | FACILITY_MCP_URL |
|---|---|
| 로컬 개별 실행 | `http://localhost:8001/mcp` |
| 로컬 docker-compose | `http://facility-mcp:8001/mcp` |
| Railway 프로덕션 | `http://facility-mcp.railway.internal:8001/mcp` |

MCP 호출 실패 시 예외 → `make_subagent` 표준 실패 경로 → 재라우팅 발동.

<br>

## SSE 스트리밍

`POST /api/chat/stream`은 LangGraph 표준 streaming이 아닌 수동 오케스트레이션(`_run_multi_agent_stream`).

**이벤트 시퀀스**:
```text
status  step=supervisor
status  step=supervisor_done, mode=single_agent, agents=[lesson]
status  step=agent_start, agent=lesson
status  step=agent_done, agent=lesson, success=true

(재라우팅 발동 시)
status  step=reroute, from=lesson
status  step=agent_start, agent=faq, rerouted=true
status  step=agent_done, agent=faq, rerouted=true

status  step=response
token   content=안
token   content=녕
...
done    tools_used=["lesson"], total_tokens=1234
```

## 파일별 실행 흐름
<img width="1440" height="1960" alt="image" src="https://github.com/user-attachments/assets/1c1149ca-a514-460d-b534-9c1485787bee" />



## 핵심 파일

| 파일 | 책임 |
|---|---|
| `server/app/services/ai/agent_graph.py` | 그래프 빌더, 조건부 분기 |
| `server/app/services/ai/agent_state.py` | TypedDict 스키마 |
| `server/app/services/ai/supervisor_node.py` | Supervisor + Aggregator + Reroute |
| `server/app/services/ai/agents/base.py` | `make_subagent` 팩토리 |
| `server/app/services/ai/agents/{lesson,enrollment,faq,facility}_agent.py` | 4개 서브에이전트 |
| `server/app/services/ai/mcp_client.py` | facility-mcp 호출 |
| `server/app/services/chat_service.py` | `_run_multi_agent_stream` |
| `mcp_servers/facility_server/app/main.py` | FastMCP 진입점 |
| `mcp_servers/facility_server/app/tools/facility.py` | `search_facilities` 도구 |
| `mcp_servers/facility_server/app/kspo_client.py` | KSPO API + 정규화 |
| `mcp_servers/facility_server/app/cache.py` | TTL 캐시 |

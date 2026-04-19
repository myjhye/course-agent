# Facility MCP Server

공공데이터포털의 전국 체육시설 API(KSPO)를 MCP(Model Context Protocol) 도구로 래핑한 서버.

Course Agent의 facility 서브에이전트가 이 서버를 HTTP MCP 클라이언트로 호출해
지역·종목 기반 체육시설 검색을 수행한다. Claude Desktop 등 다른 MCP 클라이언트에도 연결 가능한 독립 서버다.

## 상태 (Step 8)

- FastMCP 기반 서버 스켈레톤
- 헬스 체크 도구 `ping` 노출
- 실제 시설 검색 도구는 다음 스텝에서 추가

## 기술 스택

- Python 3.11+
- FastMCP
- httpx (KSPO API 호출 예정)

## 개발 실행

```bash
pip install -r requirements.txt
cp .env.example .env   # 키 입력 (Step 9)
python -m app.main
```

HTTP 기본 주소: `http://127.0.0.1:8001/mcp` (포트는 `MCP_PORT`로 변경 가능)

## 아키텍처

```text
Claude Desktop / Course Agent (MCP Client)
              │  HTTP MCP
              ▼
   Facility MCP Server (this project)
              │  HTTPS
              ▼
       KSPO Public API
```

## 후속 스텝

- Step 9: KSPO API 클라이언트 + TTL 캐시
- Step 10: `search_facilities`, `find_nearby_facilities` 도구 + Dockerfile
- Step 11: Course Agent MCP 클라이언트 + facility_agent

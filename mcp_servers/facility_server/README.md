# Facility MCP Server

공공데이터포털의 [전국 체육시설 API(KSPO)](https://www.data.go.kr/data/15052633/openapi.do)를 MCP(Model Context Protocol) 도구로 래핑한 **독립 실행 서버**.

Course Agent의 `facility_agent`가 HTTP MCP 클라이언트로 이 서버를 호출해 지역·종목 기반 체육시설 검색을 수행한다. Claude Desktop 등 다른 MCP 클라이언트에도 그대로 연결 가능.

## 위치
course-agent/
├── server/                       # Course Agent 본체 (MCP 클라이언트)
└── mcp_servers/
    └── facility_server/          # ← 이 프로젝트 (MCP 서버)

## 기능

| 도구 | 설명 |
|---|---|
| `ping` | 헬스 체크 |
| `search_facilities` | 시도·시군구·시설유형·업종·시설명으로 체육시설 검색. `user_lat`/`user_lng` 주어지면 haversine 거리순 정렬 |

응답 시:
- 폐업 시설은 자동 제외 (`include_closed=False` 기본값)
- 위경도는 `float`로 변환 (KSPO 원본은 문자열)
- 26개 원본 필드 중 12개로 정규화하여 반환

## 아키텍처
┌─────────────────────────────────────────┐
│  Claude Desktop / Course Agent          │
│  (any MCP client over HTTP)             │
└──────────────────┬──────────────────────┘
                   │ HTTP MCP (FastMCP)
                   ▼
┌─────────────────────────────────────────┐
│  Facility MCP Server  (this project)    │
│                                         │
│  app/main.py        FastMCP 진입점       │
│  app/tools/         @mcp.tool 데코레이터  │
│  app/kspo_client.py 외부 API 호출         │  
│  app/cache.py       TTL + per-key lock  │
│  app/config.py      pydantic-settings   │
└──────────────────┬──────────────────────┘
                   │ HTTPS
                   ▼
┌─────────────────────────────────────────┐
│  KSPO Public API (data.go.kr)           │
│  전국 체육시설 약 15만 건                  │
└─────────────────────────────────────────┘

## 기술 스택

- Python 3.11+
- [FastMCP 3.x](https://gofastmcp.com/) — MCP 프로토콜 서버
- httpx (async HTTP)
- cachetools — TTL 메모리 캐시
- pydantic-settings

## 캐시 전략

- **In-memory TTL** (`cachetools.TTLCache`)
  - 기본 TTL 10분, 최대 256 entries
  - 동일 쿼리 파라미터에 대해 외부 API 중복 호출 방지
- **per-key `asyncio.Lock`**으로 동시 요청 race condition 방지
- 캐시 키에서 `serviceKey`는 제외 (키 변경 시 캐시 통째로 무효화 회피)

KSPO API의 시도·시군구·시설유형 필터를 그대로 사용하므로 SQLite 시드 같은 사전 동기화 없이 실시간 호출만으로 충분. 일일 트래픽 쿼터 10,000회 안에서 운용.

## 로컬 실행

```bash
# 1. 가상환경
python -m venv venv
.\venv\Scripts\Activate.ps1   # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt

# 2. 환경변수
cp .env.example .env
# .env 편집 — KSPO_API_KEY 입력

# 3. 기동
python -m app.main
```

기본 주소: `http://127.0.0.1:8001/mcp`

기동 로그 예시:
FastMCP 3.2.4
🖥  Server: facility-mcp-server, 3.2.4
INFO  Starting MCP server 'facility-mcp-server' with transport 'http' on http://127.0.0.1:8001/mcp
INFO  Uvicorn running on http://127.0.0.1:8001

## 환경변수

| Key | Default | 설명 |
|---|---|---|
| `KSPO_API_KEY` | (필수) | 공공데이터포털 인증키 |
| `KSPO_BASE_URL` | `https://apis.data.go.kr/B551014/SRVC_API_SFMS_FACI` | API 엔드포인트 |
| `KSPO_TIMEOUT_SECONDS` | `10.0` | HTTP 타임아웃 |
| `CACHE_TTL_SECONDS` | `600` | 캐시 유효 시간 (10분) |
| `CACHE_MAXSIZE` | `256` | 캐시 최대 항목 수 |
| `MCP_HOST` | `127.0.0.1` | 바인딩 주소. Docker는 `0.0.0.0` |
| `MCP_PORT` | `8001` | 포트 |

## Docker

```bash
docker build -t facility-mcp:dev .
docker run -p 8001:8001 --env-file .env facility-mcp:dev
```

상위 디렉터리의 `docker-compose.yml`에서 course-agent와 함께 통합 기동 가능:

```bash
cd ..   # course-agent 루트
docker compose up -d --build
```

이 경우 facility-mcp는 외부 노출 없이 internal network로만 접근됨.

## Claude Desktop에서 사용

Claude Desktop의 MCP 설정에 추가:

```json
{
  "mcpServers": {
    "facility": {
      "url": "http://localhost:8001/mcp"
    }
  }
}
```

Claude Desktop을 재시작하면 `search_facilities` 도구가 도구 목록에 노출됨.

## 테스트

```bash
pytest tests/ -v
```

총 12 cases:
- KSPO 응답 파싱 / 정규화 / 에러 코드 처리
- 폐업 시설 필터링
- 캐시 hit/miss 동작
- haversine 거리 계산 (서울↔부산 ≈ 325km 검증)
- 거리순 정렬 및 좌표 누락 시 뒤로 밀기

실제 API 호출 없이 `monkeypatch`로 외부 의존성 차단.

## 배포

GitHub `main` 브랜치 push 시 Railway가 Dockerfile로 자동 빌드·재배포. Railway 서비스명 `facility-mcp`로 등록되며 internal DNS `facility-mcp.railway.internal:8001`로만 접근(외부 비노출). 같은 Railway 프로젝트의 `course-agent` 서비스가 환경변수 `FACILITY_MCP_URL=http://facility-mcp.railway.internal:8001/mcp`로 호출.

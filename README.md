# Course Agent

LangGraph 기반 멀티에이전트 + MCP 클라이언트/서버를 갖춘 AI 스포츠 강습 플랫폼

## 🚀 라이브 데모

| 항목 | 링크 |
|---|---|
| **사용자 화면** | [course-agent.vercel.app](https://course-agent.vercel.app) |
| **관리자 대시보드** | [course-agent.vercel.app/admin/dashboard](https://course-agent.vercel.app/admin/dashboard) |
| **API 문서 (Swagger)** | [course-agent-production.up.railway.app/docs](https://course-agent-production.up.railway.app/docs) |

배포 환경: Vercel(프론트) + Railway(백엔드 + MCP 서버 + Postgres)

---

## 한눈에 보기

**AI 에이전트 운영에 필요한 핵심 패턴들을 실제로 구현·통합한 풀스택 서비스**입니다.

### 핵심 특징

- **LangGraph Supervisor 패턴 기반 멀티에이전트** — lesson / enrollment / faq / facility 4개 도메인 서브에이전트 분리, 복합 질문 multi-agent 순차 실행
- **Self-Correction 재라우팅** — 에이전트 결과 부실 시 다른 도메인으로 자동 재분배 (예: lesson 검색 실패 → faq로 자동 폴백)
- **MCP 클라이언트/서버 양방향 구현** — 공공 체육시설 API(KSPO)를 MCP 도구로 노출하는 독립 서버 + Course Agent의 MCP 클라이언트 통합
- **SSE 토큰 스트리밍** — LangGraph 노드별 실시간 상태 + GPT 토큰 스트림
- **RAG (pgvector)** — 125개 지식 청크 임베딩 + 코사인 유사도 검색, ILIKE 폴백 지원
- **Langfuse 관측성** — 모든 에이전트 노드·LLM 호출 end-to-end trace
- **마이크로서비스 인프라** — docker-compose로 로컬 통합, Railway internal DNS로 프로덕션 서비스 간 통신

---

## 데모 시나리오

| 사용자 입력 | 동작 |
|---|---|
| `"수영 강습 알려줘"` | Supervisor → `lesson` 단일 호출 → DB 검색 결과 반환 |
| `"강습 목록 보여주고 환불 규정도 알려줘"` | Supervisor → `multi_agent: [lesson, faq]` 순차 실행 → 통합 응답 |
| `"서울에서 수영장 알려줘"` | Supervisor → `facility` → MCP 호출 → KSPO 공공 API 결과 |
| `"파쿠르 강습 있어?"` | Supervisor → `lesson` 실패 → **재라우팅** → `faq` → 대안 안내 |
| `"강남에서 수영 배우고 싶은데 근처 수영장도 알려줘"` | Supervisor → `multi_agent: [lesson, facility]` |

---

## 주요 화면

라이브 데모에서 직접 확인 가능:

| 경로 | 설명 |
|---|---|
| [`/`](https://course-agent.vercel.app/) | 홈 |
| [`/chat`](https://course-agent.vercel.app/chat) | AI 채팅 (SSE 스트리밍) |
| [`/lessons`](https://course-agent.vercel.app/lessons) | 강습 목록 |
| [`/admin/dashboard`](https://course-agent.vercel.app/admin/dashboard) | 관리자 대시보드 |

---

## 아키텍처

### 시스템 구성
┌─────────────────────┐
│  Vercel             │
│  course-agent       │  ← 비밀번호 게이트(VITE_GATE_PASSWORD)
│  (React + Vite)     │
└──────────┬──────────┘
           │ HTTPS
           ▼
┌──────────────────────────────────────────────────────┐
│  Railway: tranquil-nourishment / production          │
│                                                      │
│  ┌─────────────────────┐                             │
│  │ course-agent        │  ← public  (8000)           │
│  │ (FastAPI+LangGraph) │                             │
│  └─┬───────────────┬───┘                             │
│    │ asyncpg       │ MCP HTTP (railway.internal)     │
│    ▼               ▼                                 │
│  ┌──────────┐   ┌────────────────────┐               │
│  │ pgvector │   │ facility-mcp       │  ← internal   │
│  │ Postgres │   │ (FastMCP HTTP)     │     only      │
│  └──────────┘   └─────────┬──────────┘               │
│                           │                          │
└───────────────────────────┼──────────────────────────┘
                            │ HTTPS
                            ▼
┌──────────────────┐
│ KSPO Public API  │
│ (체육시설 정보)    │
└──────────────────┘

### 멀티에이전트 흐름
사용자 메시지
   │
   ▼
┌─────────────┐
│ Supervisor  │  ← LLM이 의도 분류
│             │     · direct_response: 인사 등 도구 불필요
└─────┬───────┘     · single_agent: 한 도메인
      │             · multi_agent: 여러 도메인 순차
      ▼
┌─────────────┐
│ Dispatcher  │  ← 조건부 엣지로 분기
└─┬─┬─┬─┬─────┘
  │ │ │ │
  ▼ ▼ ▼ ▼
lesson / enrollment / faq / facility
  │ │ │ │
  ▼ ▼ ▼ ▼
┌──────────────┐
│  Aggregator  │  ← 결과 검증 (is_valid)
└──┬───────────┘
   │
   │  is_valid=False & single_agent
   │  & rerouting_count==0 ?
   │
   ├─ Yes ──▶ Reroute Supervisor (휴리스틱: lesson↔faq, etc.)
   │           └─▶ Dispatcher 재진입
   │
   └─ No  ──▶ Response (SSE 토큰 스트리밍)

---

## 기술 스택

### Backend (`server/`)

| 분류 | 기술 |
|---|---|
| 언어/프레임워크 | Python 3.11+, FastAPI, SQLAlchemy(async) |
| 에이전트 | LangGraph (Supervisor 패턴) |
| LLM | OpenAI GPT-4o-mini |
| RAG | pgvector(HNSW), text-embedding-3-small |
| 관측 | Langfuse |
| 스트리밍 | sse-starlette |
| MCP | fastmcp.Client |

### Frontend (`client/`)

React 18, TypeScript, Vite, TailwindCSS, React Router v6, Axios

### MCP Server (`mcp_servers/facility_server/`)

Python 3.11+, FastMCP 3.x, httpx, cachetools

### 인프라

PostgreSQL + pgvector(pg17), docker-compose, Railway, Vercel

---

## 디렉터리 구조
course-agent/
├── server/                              # Course Agent 본체 (FastAPI)
│   ├── app/
│   │   ├── models/                      # SQLAlchemy 모델 (lesson, enrollment, chat, knowledge ...)
│   │   ├── routers/                     # API 라우터 (admin/, my/, lessons, chat)
│   │   ├── services/
│   │   │   ├── chat_service.py          # 비스트리밍/스트리밍 채팅 오케스트레이션
│   │   │   ├── recommendation_service.py
│   │   │   ├── feedback_service.py
│   │   │   ├── dashboard_service.py
│   │   │   └── ai/
│   │   │       ├── agent_state.py       # AgentState (TypedDict)
│   │   │       ├── agent_graph.py       # build_multi_agent_graph + 조건부 분기
│   │   │       ├── agent_nodes.py       # response_node + 공용 헬퍼
│   │   │       ├── supervisor_node.py   # Supervisor + Aggregator + reroute_supervisor
│   │   │       ├── mcp_client.py        # facility MCP 서버 호출 클라이언트
│   │   │       ├── tool_executor.py     # lesson/enrollment/faq 도구 실행
│   │   │       ├── embedding_service.py # 임베딩 생성 + pgvector 검색
│   │   │       ├── langfuse_client.py   # Langfuse 싱글톤
│   │   │       ├── llm_client.py        # OpenAI 클라이언트
│   │   │       ├── content_generator.py # 강습 콘텐츠 자동 생성
│   │   │       └── agents/
│   │   │           ├── base.py          # make_subagent 팩토리
│   │   │           ├── lesson_agent.py
│   │   │           ├── enrollment_agent.py
│   │   │           ├── faq_agent.py
│   │   │           └── facility_agent.py  # MCP 호출 서브에이전트
│   │   └── main.py
│   ├── knowledge_base/                  # RAG 지식 (md 19개, 청크 125개)
│   ├── scripts/                         # load_knowledge.py, seed_data.py
│   ├── alembic/                         # DB 마이그레이션
│   ├── Dockerfile
│   └── requirements.txt
│
├── mcp_servers/
│   └── facility_server/                 # 독립 MCP 서버 (KSPO 공공 API 래핑)
│       ├── app/
│       │   ├── main.py                  # FastMCP 진입점
│       │   ├── config.py                # pydantic-settings
│       │   ├── kspo_client.py           # 공공 API 클라이언트
│       │   ├── cache.py                 # TTL 캐시 + per-key lock
│       │   └── tools/
│       │       ├── health.py            # ping
│       │       └── facility.py          # search_facilities (거리 정렬 옵션)
│       ├── tests/                       # pytest (12 cases)
│       ├── Dockerfile
│       └── README.md
│
├── client/                              # React 프론트엔드
│   ├── src/
│   │   ├── components/
│   │   │   ├── PasswordGate.tsx         # 외부 접근 차단 게이트
│   │   │   ├── layout/
│   │   │   └── common/
│   │   ├── pages/                       # HomePage, ChatPage, admin/, my/ ...
│   │   ├── services/api.ts              # SSE 스트리밍 파싱 포함
│   │   └── App.tsx
│   └── index.html
│
└── docker-compose.yml                   # course-agent + facility-mcp 통합 기동

---

### 사전 준비

- Docker Desktop (DB + 컴포즈용)
- Python 3.11+, Node.js 18+
- OpenAI API Key
- 공공데이터포털 KSPO API Key ([data.go.kr](https://data.go.kr) 신청)
- (선택) Langfuse 클라우드 키

### 옵션 1: docker-compose로 백엔드 통합 기동 (권장)

```bash
# 환경변수 준비
cp server/.env.example server/.env
cp mcp_servers/facility_server/.env.example mcp_servers/facility_server/.env
# 각 .env 파일에 키·DB URL 채워넣기

# 빌드 및 기동
docker compose up -d --build

# 로그 확인
docker compose logs -f course-agent
docker compose logs -f facility-mcp
```

course-agent → http://localhost:8000  
facility-mcp → 컨테이너 내부 통신만 (외부 비노출)

### 옵션 2: 개별 실행 (개발용)

```bash
# 1. DB
docker compose up -d postgres   # 또는 본인 환경의 pgvector 컨테이너

# 2. Server
cd server
python -m venv venv
.\venv\Scripts\Activate.ps1   # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
python -m alembic upgrade head
python scripts/load_knowledge.py    # RAG 지식 로딩 (최초 1회)
python scripts/seed_data.py          # 시드 데이터 (선택)
python -m uvicorn app.main:app --reload

# 3. Facility MCP (별도 터미널)
cd mcp_servers/facility_server
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m app.main

# 4. Client (별도 터미널)
cd client
npm install
cp .env.example .env   # VITE_API_URL=http://localhost:8000
npm run dev
```

접속:
- 사용자: http://localhost:5173
- 관리자: http://localhost:5173/admin/dashboard
- API 문서: http://localhost:8000/docs

---

## 주요 환경변수

### `server/.env`

```bash
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/course_agent
OPENAI_API_KEY=sk-...

# Optional - Langfuse (없으면 관측 자동 비활성화)
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com

# Facility MCP
FACILITY_MCP_URL=http://localhost:8001/mcp           # 로컬
# 프로덕션은 Railway internal DNS:
# FACILITY_MCP_URL=http://facility-mcp.railway.internal:8001/mcp
```

### `mcp_servers/facility_server/.env`

```bash
KSPO_API_KEY=...
MCP_HOST=127.0.0.1   # 로컬, Docker는 0.0.0.0
MCP_PORT=8001
```

### `client/.env`

```bash
VITE_API_URL=http://localhost:8000
VITE_GATE_PASSWORD=1111   # 외부 접근 차단용 게이트
```

---

## AI 기능 상세

### 1. 멀티에이전트 채팅

| 구성 요소 | 책임 |
|---|---|
| Supervisor | 사용자 의도를 분석해 에이전트 계획 수립 (direct/single/multi) |
| lesson_agent | 강습 검색·상세 조회 (DB) |
| enrollment_agent | 수강 현황·맞춤 추천 (DB) |
| faq_agent | FAQ RAG 검색 (pgvector + ILIKE 폴백) |
| facility_agent | 공공 체육시설 검색 (MCP → KSPO API) |
| Aggregator | 에이전트 결과 통합·검증 (`is_valid`) |
| Reroute Supervisor | 휴리스틱 매핑(lesson↔faq, enrollment→lesson, facility→lesson)으로 재라우팅 |
| Response (stream) | OpenAI `stream=True`로 토큰 단위 SSE 출력 |

### 2. AI 콘텐츠 자동 생성

강습 등록 시 GPT-4o-mini로 소개문구·커리큘럼 자동 생성. 항목별 개별 재생성 가능.

### 3. 맞춤 추천

| 카테고리 | 조건 |
|---|---|
| 🎯 다음 단계 | 완료 또는 출석률 70%+ |
| 🌟 새로운 도전 | 미경험 종목 입문 |
| 💡 관심 기반 | 찜 또는 자주 조회한 종목 |

추천 이유는 GPT-4o-mini가 개인화하여 생성.

### 4. AI 피드백 생성

수강생 출석률·진도 기반 피드백 자동 생성 (관리자 기능).

---

## 데이터 모델
Instructor (강사)
└── Lesson (강습) ── LessonContent (AI 콘텐츠, 버전 관리)
    ├── Enrollment ── Feedback
    ├── LessonView (조회)
    └── LessonLike (찜)
ChatSession ── ChatMessage
KnowledgeChunk (RAG 청크 + pgvector 임베딩)
FAQ
AILog

체육시설 데이터는 외부 KSPO API 호출이라 로컬 모델 없음.

---

## 주요 API

### 채팅
POST   /api/chat/                메시지 전송 (비스트리밍)
POST   /api/chat/stream          SSE 스트리밍 채팅
GET    /api/chat/sessions        세션 목록
GET    /api/chat/sessions/:id    세션 상세
DELETE /api/chat/sessions/:id    세션 삭제

### 강습 / 수강 / 추천
GET  /api/lessons/                    발행된 강습 목록
GET  /api/lessons/:id                 강습 상세
POST /api/lessons/:id/view            조회 기록
POST /api/lessons/:id/like            찜 토글
GET  /api/my/enrollments/             내 수강 현황
POST /api/my/enrollments/             수강 신청
GET  /api/my/recommendations/         맞춤 추천

### 관리자
GET  /api/admin/dashboard/                                대시보드 통계
GET  /api/admin/dashboard/ai-logs                         AI 사용 로그
POST /api/admin/lessons/                                  강습 등록
POST /api/admin/lessons/:id/generate-content              AI 콘텐츠 생성
POST /api/admin/lessons/:id/contents/:cid/regenerate-introduction
POST /api/admin/lessons/:id/contents/:cid/regenerate-curriculum
POST /api/admin/lessons/:id/publish                       강습 발행
GET  /api/admin/enrollments/                              수강 목록
PUT  /api/admin/enrollments/:id                           수강 상태 변경
POST /api/admin/enrollments/:id/generate-feedback         AI 피드백 생성

전체 스펙: http://localhost:8000/docs (FastAPI Swagger UI)

---

## 배포

### Railway (백엔드)

| 서비스 | 역할 | 노출 |
|---|---|---|
| `pgvector` | Postgres + pgvector 확장 | internal only |
| `course-agent` | FastAPI 본체 | public (도메인 자동 부여) |
| `facility-mcp` | MCP 서버 | internal only (`facility-mcp.railway.internal:8001`) |

GitHub `main` 브랜치 push 시 Railway가 Dockerfile 기반으로 자동 빌드·재배포.

facility-mcp는 외부 비노출이라 KSPO 공공 API 키가 안전.

### Vercel (프론트엔드)

`main` 브랜치 push 시 자동 배포. `VITE_*` 환경변수는 Vercel 대시보드에 등록 (`VITE_API_URL`, `VITE_GATE_PASSWORD`).

---

## 개발 진행 단계

| Phase | 내용 |
|---|---|
| 1 | 멀티에이전트 리팩토링 (단일 Router → Supervisor + 도메인 서브에이전트) |
| 2 | Self-Correction 재라우팅 (도메인 간 자동 폴백) |
| 3 | 외부 MCP 서버 (facility) — 클라이언트/서버 양방향 |
| 4 | 배포 (Railway 멀티서비스 + Vercel) |
| 5 | 문서 마감 |

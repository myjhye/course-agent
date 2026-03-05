# Course Agent

LangGraph 기반 AI 에이전트 + RAG + 실시간 스트리밍을 갖춘 스포츠 강습 플랫폼

## 프로젝트 소개

Course Agent는 스포츠 강습 플랫폼에 프로덕션 수준의 AI 파이프라인을 구현한 풀스택 프로젝트입니다.
단순한 LLM API 호출이 아닌, **LangGraph 상태 머신 기반 멀티스텝 에이전트**, **pgvector RAG 파이프라인**, **Langfuse 관측성**, **SSE 실시간 스트리밍**까지 AI 엔지니어링의 핵심 기술을 실제로 구현했습니다.

### 핵심 AI 아키텍처

```
사용자 질문
  │
  ▼
┌─────────────────────────────────────────────────────┐
│ LangGraph State Machine                             │
│                                                     │
│  [Router] ─── GPT-4o-mini 의도 분류 (5가지)         │
│     │                                               │
│     ├── general_inquiry → [Response] 바로 응답       │
│     └── 그 외 ──────────→ [ToolExecutor]            │
│                               │                     │
│                          도구 실행 (DB 쿼리/RAG)     │
│                               │                     │
│                          [Validator]                 │
│                           ├── 성공 → [Response]      │
│                           └── 실패 → 필터 완화 재시도 │
│                                                     │
│  [Response] ─── GPT-4o-mini 스트리밍 응답 생성       │
│                                                     │
│  ※ 전 노드 Langfuse 트레이싱                        │
│  ※ Response 노드 SSE 토큰 스트리밍                   │
└─────────────────────────────────────────────────────┘
```

### 주요 특징

- **LangGraph 상태 머신**: Router → ToolExecutor → Validator → Response 4단계 파이프라인. 의도 분류로 일반 대화 시 Tool 호출 0회 (토큰 40% 절감)
- **Self-Correction**: 검색 결과 없을 시 Validator가 필터를 완화하여 자동 재검색 (최대 2회)
- **RAG (pgvector)**: 125개 지식 청크에서 코사인 유사도 벡터 검색. ILIKE 폴백으로 가용성 보장
- **Langfuse Observability**: 모든 LLM 호출/RAG 검색/에이전트 흐름을 Trace 단위로 추적
- **SSE 스트리밍**: ChatGPT처럼 토큰 단위 실시간 응답 + 단계별 상태 표시
- **맞춤형 추천**: 수강 이력/출석률/찜 기록 기반 3가지 카테고리 추천
- **AI 콘텐츠 생성**: 강습 소개문구/커리큘럼 자동 생성, 종목별 Unsplash 썸네일

## 기술 스택

### Backend

| 기술 | 용도 |
|------|------|
| Python 3.11+ | 서버 언어 |
| FastAPI | 웹 프레임워크 |
| LangGraph | AI 에이전트 오케스트레이션 (상태 머신) |
| OpenAI GPT-4o-mini | 의도 분류, 인자 추출, 응답 생성 |
| OpenAI text-embedding-3-small | 벡터 임베딩 (1536차원) |
| pgvector | PostgreSQL 벡터 검색 확장 (HNSW 인덱스) |
| Langfuse | LLM 관측성 (트레이싱, 비용 추적) |
| SSE (sse-starlette) | 실시간 토큰 스트리밍 |
| SQLAlchemy (async) | ORM |
| PostgreSQL | 데이터베이스 |
| Alembic | DB 마이그레이션 |

### Frontend

| 기술 | 용도 |
|------|------|
| React 18 | UI 라이브러리 |
| TypeScript | 타입 안정성 |
| Vite | 빌드 도구 |
| TailwindCSS | 스타일링 |
| React Router v6 | 라우팅 |
| fetch + ReadableStream | SSE 스트리밍 수신 |

### Infra

| 기술 | 용도 |
|------|------|
| Railway | 백엔드 + PostgreSQL (pgvector Docker) 배포 |
| Vercel | 프론트엔드 배포 |
| Langfuse Cloud | LLM 관측성 대시보드 |

## AI 파이프라인 상세

### Phase 1: LangGraph 에이전트

기존 OpenAI Function Calling while 루프를 LangGraph 상태 머신으로 전환했습니다.

**Before (while 루프):**
```
사용자 → LLM(5개 Tool 정의 포함) → Tool 호출 → LLM → ... → 응답
- "안녕하세요"에도 5개 Tool 정의를 매번 전송 (토큰 낭비)
- 조건부 분기 불가, Self-Correction 없음
```

**After (LangGraph):**
```
사용자 → Router(의도 분류) → 의도별 분기
- general_inquiry → Tool 없이 바로 응답 (토큰 40% 절감)
- search_lessons → ToolExecutor → Validator → (실패 시 재시도) → Response
```

**AgentState (TypedDict):**

| 필드 | 타입 | 설명 |
|------|------|------|
| intent | str | Router가 분류한 의도 (5가지) |
| tool_name / tool_args / tool_result | Optional | 실행할/실행된 Tool 정보 |
| is_valid / retry_count / retry_strategy | bool/int/str | Validator의 Self-Correction 상태 |
| trace_id | Optional[str] | Langfuse Trace 연결용 |
| tools_used / all_tool_results / total_tokens | list/dict/int | 실행 이력 추적 |

**의도 분류 (Router):**

| 의도 | 설명 | Tool |
|------|------|------|
| search_lessons | 강습 검색 | search_lessons |
| get_recommendations | 맞춤 추천 | get_recommendations |
| manage_enrollment | 수강 현황 | get_my_enrollments |
| faq_inquiry | 정보/FAQ 질문 | search_faq (RAG) |
| general_inquiry | 인사/잡담 | 없음 |

### Phase 2: RAG + pgvector

FAQ ILIKE 키워드 검색을 벡터 유사도 검색으로 업그레이드했습니다.

**Knowledge Base 구성:**

| 폴더 | 파일 수 | 청크 수 | 내용 |
|------|---------|---------|------|
| sports/ | 11개 | 67 | 종목별 가이드 (효과, 준비물, 단계별 학습, 주의사항) |
| platform/ | 4개 | 26 | 수강 가이드, 결제/환불, FAQ, 초보자 가이드 |
| instructors/ | 1개 | 15 | 강사 15명 프로필 |
| tips/ | 3개 | 17 | 운동 시작 팁, 부상 예방, 영양 기초 |

**파이프라인:**
```
md 파일 → ## 헤더 기준 청킹 (200~500자) → text-embedding-3-small → pgvector 저장
                                                                       ↓
사용자 질문 → 임베딩 → 코사인 유사도 검색 (HNSW, threshold 0.3, top_k=5)
                                                                       ↓
                                                              LLM 컨텍스트에 주입
```

**검색 예시:**
```
"물이 무서운데 수영 배울 수 있어?"
→ 벡터 검색 → swimming.md "물 공포증이 있는 경우" 청크 (similarity 0.52)
→ LLM이 이해수 코치의 물 적응 전문 경험을 포함한 구체적 답변 생성
```

### Phase 3: Langfuse Observability

모든 AI 호출을 Langfuse로 추적합니다.

| 추적 대상 | Langfuse 타입 | 기록 내용 |
|-----------|--------------|----------|
| Router | generation | 의도 분류 프롬프트, 결과, 토큰 |
| 인자 추출 | generation | 검색 조건/FAQ 키워드 추출 |
| ToolExecutor | span | tool_name, args, 성공/실패, 결과 수 |
| RAG Search | span | 검색 쿼리, 결과 수, similarity Top 3 |
| Embedding | generation | 입력 텍스트, 차원, 토큰 |
| Response | generation | 프롬프트 전문, 응답, 토큰 |
| Trace (루트) | trace | 총 레이턴시, 총 토큰, 에러 여부 |

**Graceful Degradation:** Langfuse API 키가 없으면 모든 트레이싱 코드가 자동으로 비활성화되며, 앱은 정상 동작합니다.

### Phase 3.5: SSE 스트리밍

Server-Sent Events 기반 실시간 토큰 스트리밍으로 ChatGPT급 UX를 구현했습니다.

**SSE 이벤트 흐름:**
```
[프론트] POST /api/chat/stream → SSE 연결

  event: status   → "🔍 의도 분석 중..."
  event: status   → "📡 정보 검색 중..."
  event: status   → "✍️ 답변 생성 중..."
  event: token    → "홍" "길" "동" "님" "," " " ...
  event: done     → {tools_used, total_tokens}
```

**설계 결정:**
- Router/ToolExecutor/Validator는 비스트리밍 (빠르게 완료)
- Response 노드만 OpenAI stream=True로 토큰 스트리밍
- EventSource API 대신 fetch + ReadableStream (POST 요청 지원)
- 기존 /api/chat/ 비스트리밍 엔드포인트 유지 (폴백)

## 그 외 AI 기능

### AI 콘텐츠 자동 생성

강습 등록 후 "AI 콘텐츠 생성" 버튼 클릭 시:

| 항목 | 모델 | 설명 |
|------|------|------|
| 소개 문구 | GPT-4o-mini | 대상/난이도에 맞는 3~4문장 |
| 커리큘럼 | GPT-4o-mini | 난이도별 4~8주차 체계적 구성 |
| 썸네일 | Unsplash | 종목별 기본 이미지 자동 적용 |

### 맞춤형 추천 시스템

| 카테고리 | 조건 | 데이터 소스 |
|----------|------|-------------|
| 🎯 다음 단계 | 완료 또는 출석률 70%+ | 수강 이력 |
| 🌟 새로운 도전 | 미경험 종목 입문 | 수강 이력 |
| 💡 관심 기반 | 찜 또는 자주 조회한 종목 | 조회/찜 기록 |

## 프로젝트 구조

```
course-agent/
├── server/
│   ├── app/
│   │   ├── models/                     # SQLAlchemy 모델
│   │   │   ├── knowledge.py            # ★ RAG 지식 청크 + pgvector 임베딩
│   │   │   ├── chat.py                 # 채팅 세션/메시지
│   │   │   ├── lesson.py / enrollment.py / ...
│   │   │   └── ai_log.py
│   │   ├── routers/
│   │   │   ├── chat.py                 # ★ /api/chat/stream SSE 엔드포인트
│   │   │   ├── admin/ / my/ / lessons.py
│   │   │   └── ...
│   │   ├── services/
│   │   │   ├── ai/
│   │   │   │   ├── agent_state.py      # ★ AgentState TypedDict
│   │   │   │   ├── agent_nodes.py      # ★ Router/ToolExecutor/Validator/Response 노드
│   │   │   │   ├── agent_graph.py      # ★ LangGraph 그래프 조건 분기
│   │   │   │   ├── embedding_service.py # ★ 임베딩 생성 + 벡터 검색
│   │   │   │   ├── langfuse_client.py  # ★ Langfuse 싱글톤
│   │   │   │   ├── tool_executor.py    # 도구 실행기 (RAG 벡터 검색 통합)
│   │   │   │   ├── llm_client.py       # OpenAI 클라이언트
│   │   │   │   ├── tools.py            # Function Calling 도구 정의
│   │   │   │   └── content_generator.py
│   │   │   ├── chat_service.py         # ★ chat() + chat_stream() + LangGraph 실행
│   │   │   ├── recommendation_service.py
│   │   │   └── ...
│   │   ├── schemas/
│   │   ├── config.py                   # ★ Langfuse 환경변수 포함
│   │   └── main.py
│   ├── knowledge_base/                 # ★ RAG용 지식 문서
│   │   ├── sports/                     # 종목별 가이드 (11개)
│   │   ├── platform/                   # 플랫폼 안내 (4개)
│   │   ├── instructors/                # 강사 프로필 (1개)
│   │   └── tips/                       # 운동 팁 (3개)
│   ├── scripts/
│   │   ├── seed_data.py                # 시드 데이터
│   │   └── load_knowledge.py           # ★ 지식 청킹 → 임베딩 → DB 로딩
│   └── alembic/
│
├── client/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── ChatPage.tsx            # ★ SSE 스트리밍 + 단계별 상태 표시
│   │   │   └── ...
│   │   └── services/
│   │       └── api.ts                  # ★ sendMessageStream (fetch + ReadableStream)
│   └── ...
│
└── ★ = Phase 1~3.5에서 추가/수정된 파일
```

## 실행 방법

### 1. PostgreSQL (pgvector 포함)

```bash
# Docker로 pgvector 포함 PostgreSQL 실행
docker run -d \
  --name course-agent-db \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=course_agent \
  -p 5432:5432 \
  pgvector/pgvector:pg17
```

### 2. 서버 실행

```bash
cd server
python -m venv venv
source venv/bin/activate  # Windows: .\venv\Scripts\activate
pip install -r requirements.txt

# .env 설정
# DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/course_agent
# OPENAI_API_KEY=sk-...
# LANGFUSE_PUBLIC_KEY=pk-lf-...     (선택, 없어도 동작)
# LANGFUSE_SECRET_KEY=sk-lf-...     (선택, 없어도 동작)
# LANGFUSE_HOST=https://cloud.langfuse.com

# DB 마이그레이션 + 시드 데이터 + 지식 로딩
python -m alembic upgrade head
python scripts/seed_data.py
python scripts/load_knowledge.py   # 125개 청크 임베딩 → pgvector

# 서버 실행
python -m uvicorn app.main:app --reload
```

### 3. 클라이언트 실행

```bash
cd client
npm install
# VITE_API_URL=http://localhost:8000
npm run dev
```

### 4. 접속

- 사용자 화면: http://localhost:5173
- AI 채팅: http://localhost:5173/chat
- 관리자 대시보드: http://localhost:5173/admin/dashboard
- API 문서: http://localhost:8000/docs
- Langfuse 대시보드: https://cloud.langfuse.com

## 기술 선택 근거

### 왜 LangGraph인가?

기존 while 루프 방식은 선형적이라 조건부 분기가 불가능했습니다. LangGraph는 상태 머신 기반으로 Router의 의도 분류 결과에 따라 다른 경로를 탈 수 있고, Validator의 Self-Correction도 "validator → tool_executor" 순환 엣지로 자연스럽게 구현됩니다. 또한 AgentState에 전체 흐름이 기록되어 Langfuse 연동 시 각 노드의 입출력을 투명하게 추적할 수 있습니다.

### 왜 pgvector인가?

이미 PostgreSQL을 사용하고 있어서 별도 Vector DB(Pinecone, Weaviate)를 추가하면 인프라 복잡도와 비용이 증가합니다. pgvector는 PostgreSQL 확장이라 기존 DB에서 바로 벡터 검색이 가능하고, HNSW 인덱스로 125개 청크 규모에서 충분히 빠릅니다. ILIKE 폴백을 두어 pgvector 장애 시에도 기본 검색이 동작하도록 했습니다.

### 왜 SSE인가? (WebSocket이 아니라)

LLM 토큰 스트리밍은 서버→클라이언트 단방향 통신입니다. SSE는 HTTP 위에서 동작하여 CORS, 인증, 로드밸런싱 등 기존 HTTP 인프라를 그대로 활용할 수 있습니다. OpenAI, Anthropic 등 주요 AI API도 SSE를 사용합니다. 브라우저 EventSource API는 GET만 지원하므로 fetch + ReadableStream으로 POST SSE를 구현했습니다.

### 왜 Langfuse인가?

LangSmith는 LangChain 에코시스템에 종속적이고 유료 플랜이 비쌉니다. Langfuse는 오픈소스이면서 클라우드 무료 플랜이 있고, 셀프호스팅도 가능합니다. API 키가 없으면 자동으로 비활성화되는 graceful degradation 패턴으로 구현하여 Langfuse 없이도 앱이 완전히 정상 동작합니다.

## 트러블슈팅 기록

### 1. pip 의존성 충돌 (Phase 1)

**문제:** `langgraph`, `langchain-openai` 추가 시 기존 `pydantic==2.5.0` 핀 고정과 충돌하여 Railway Docker 빌드 실패. pip이 수백 개 버전을 순회하다 `ResolutionImpossible` 에러 발생.

**원인:** 핀 고정(`==`)된 구버전 패키지들이 langgraph/langchain이 요구하는 최신 버전과 호환 불가.

**해결:** 모든 핀 고정을 범위 지정(`>=x.y.z,<x+1.0.0`)으로 변경. pip이 호환 조합을 자동으로 찾도록 함.

### 2. Railway PostgreSQL pgvector 미지원 (Phase 2)

**문제:** `CREATE EXTENSION IF NOT EXISTS vector` 실행 시 `extension "vector" is not available` 에러. Railway 기본 PostgreSQL 이미지에 pgvector가 포함되어 있지 않음.

**해결:** Railway에서 기본 PostgreSQL 서비스를 삭제하고, Docker 이미지 `pgvector/pgvector:pg17`로 새 서비스를 생성하여 pgvector 지원 DB로 교체.

### 3. asyncpg `::vector` 캐스팅 구문 에러 (Phase 2)

**문제:** `embedding <=> :embedding::vector` 쿼리에서 `syntax error at or near ":"` 발생. asyncpg가 `$1` 스타일 파라미터를 사용하는데, SQLAlchemy `text()`의 `:param`이 `::vector`의 `::`과 충돌.

**해결:** `::vector`를 `cast(:embedding AS vector)`로 변경하여 파라미터 바인딩 충돌 회피.

### 4. Alembic Multiple Heads (Phase 2)

**문제:** `alembic upgrade head` 실행 시 `Multiple head revisions are present` 에러. Cursor가 생성한 새 마이그레이션이 기존 체인에 연결되지 않아 head가 2개로 분기.

**해결:** `alembic merge heads -m "merge heads"`로 두 head를 하나로 합친 후 `upgrade head` 실행.

### 5. FastAPI/Starlette 버전 호환 문제 (Phase 3.5)

**문제:** `sse-starlette` 설치 시 Starlette 0.52.1이 끌려들어왔으나, 기존 FastAPI 0.104.1은 Starlette 0.27.x를 요구. 미들웨어 스택 빌드 시 `ValueError: too many values to unpack` 에러 발생.

**해결:** FastAPI를 `>=0.115.0`으로 업그레이드하여 최신 Starlette과 호환되도록 함.

### 6. 벡터 검색 실패 시 트랜잭션 꼬임 (Phase 2 + 배포)

**문제:** `search_similar`에서 에러 발생 → SQLAlchemy 트랜잭션이 "failed" 상태로 전환 → 이후 `save_message`의 INSERT가 `InFailedSQLTransactionError`로 연쇄 실패.

**해결:** `_search_faq`의 except 블록에서 `await self.db.rollback()`을 추가하여 실패한 트랜잭션을 정리. ILIKE 폴백 실패 시에도 동일하게 rollback 처리.

### 7. Router 오분류로 인한 무한 루프 (Phase 1)

**문제:** "물이 무서운데 수영 배울 수 있어?"를 Router가 `search_lessons`로 분류 → 수영 강습 검색 → 결과 있지만 답변 부적절 → 반복 호출되는 무한 루프 발생.

**해결:** Router 프롬프트에 "~할 수 있을까?", "~해도 괜찮을까?" 같은 정보성 질문은 종목이 언급되더라도 `faq_inquiry`로 분류하도록 명시적 가이드 추가.

## 데이터 모델

```
Instructor (강사)
  └── Lesson (강습) ─── LessonContent (AI 콘텐츠, 버전 관리)
        │
        ├── Enrollment (수강) ─── Feedback (피드백)
        ├── LessonView (조회 기록)
        └── LessonLike (찜)

ChatSession (채팅 세션)
  └── ChatMessage (채팅 메시지)

KnowledgeChunk (RAG 지식 청크 + pgvector 임베딩)    ← NEW
FAQ (자주 묻는 질문)
AILog (AI 사용 로그)
```

## API 엔드포인트

### 채팅 (AI)

```
POST   /api/chat/                     # 메시지 전송 (비스트리밍)
POST   /api/chat/stream               # SSE 스트리밍 채팅       ← NEW
GET    /api/chat/sessions              # 세션 목록
GET    /api/chat/sessions/:id          # 세션 상세
DELETE /api/chat/sessions/:id          # 세션 삭제
```

### 강습

```
GET    /api/lessons/                   # 발행된 강습 목록
GET    /api/lessons/:id                # 강습 상세
POST   /api/lessons/:id/view           # 조회 기록
POST   /api/lessons/:id/like           # 찜 토글
```

### 수강

```
GET    /api/my/enrollments/            # 내 수강 현황
POST   /api/my/enrollments/            # 수강 신청
GET    /api/my/recommendations/        # 맞춤 추천
```

### 관리자

```
GET    /api/admin/dashboard/           # 대시보드 통계
GET    /api/admin/dashboard/ai-logs    # AI 로그
POST   /api/admin/lessons/             # 강습 등록
POST   /api/admin/lessons/:id/generate-content   # AI 콘텐츠 생성
POST   /api/admin/lessons/:id/publish  # 강습 발행
GET    /api/admin/enrollments/         # 수강 목록
PUT    /api/admin/enrollments/:id      # 수강 상태 변경
POST   /api/admin/enrollments/:id/generate-feedback  # AI 피드백 생성
```

## 배포

| 서비스 | 플랫폼 | URL |
|--------|--------|-----|
| Backend API | Railway | https://course-agent-production.up.railway.app |
| Frontend | Vercel | https://course-agent.vercel.app |
| Database | Railway (pgvector/pgvector:pg17) | - |
| Observability | Langfuse Cloud | https://cloud.langfuse.com |

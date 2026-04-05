# Course Agent

AI 기반 스포츠 강습 플랫폼 - LLM을 활용한 콘텐츠 자동 생성, 맞춤형 추천, **LangGraph 에이전트 + RAG + Langfuse 관측성 + SSE 스트리밍** 상담 기능을 갖춘 풀스택 프로젝트

## 프로젝트 소개

Course Agent는 스포츠 강습 플랫폼에 AI를 접목한 프로젝트입니다.
단순한 CRUD를 넘어 실제 서비스에서 활용 가능한 AI 기능들을 구현했습니다.

### 주요 특징

- **AI 콘텐츠 자동 생성**: 강습 등록 시 GPT-4o-mini로 소개문구/커리큘럼 생성, 종목별 기본 썸네일 URL 자동 적용
- **맞춤형 추천 시스템**: 수강 이력, 출석률, 조회/찜 기록을 기반으로 3가지 카테고리(다음 단계/새로운 도전/관심 기반) 추천
- **LangGraph 에이전트 + RAG + Langfuse 관측성 + SSE 스트리밍**: **LangGraph 상태 머신 기반 4단계 파이프라인 (Router → ToolExecutor → Validator → Response)** 으로 의도 분류, 도구 실행, 검증·Self-Correction, 실시간 토큰 스트리밍 응답
- **운영 대시보드**: 강습/수강 통계, AI 사용량 모니터링

## 스크린샷

| 홈 화면 | 강습 목록 |
|---------|-----------|
| 히어로 배너 + 카테고리 + 맞춤 추천 | 필터링 + 찜 기능 |

| 강습 상세 | AI 채팅 |
|-----------|---------|
| 썸네일 + 커리큘럼 + 수강신청 | LangGraph 에이전트 + SSE 스트리밍 |

| 내 수강 현황 | 관리자 대시보드 |
|--------------|-----------------|
| 카테고리별 맞춤 추천 | 통계 + AI 로그 |

## 기술 스택

### Backend

| 기술 | 용도 |
|------|------|
| Python 3.11+ | 서버 언어 |
| FastAPI | 웹 프레임워크 |
| SQLAlchemy (async) | ORM |
| PostgreSQL | 데이터베이스 |
| Alembic | DB 마이그레이션 |
| **LangGraph** | AI 에이전트 오케스트레이션 |
| **pgvector** | PostgreSQL 벡터 검색 (HNSW 인덱스) |
| **OpenAI text-embedding-3-small** | 벡터 임베딩 (1536차원) |
| **Langfuse** | LLM 관측성 |
| **sse-starlette** | SSE 실시간 스트리밍 |
| OpenAI GPT-4o-mini | 텍스트 생성 (소개문구, 커리큘럼, 추천 이유, 피드백, 에이전트 노드) |

### Frontend

| 기술 | 용도 |
|------|------|
| React 18 | UI 라이브러리 |
| TypeScript | 타입 안정성 |
| Vite | 빌드 도구 |
| TailwindCSS | 스타일링 |
| React Router v6 | 라우팅 |
| Axios | API 통신 |

## 프로젝트 구조

```
course-agent/
├── server/                          # FastAPI 백엔드
│   ├── app/
│   │   ├── models/                  # SQLAlchemy 모델
│   │   │   ├── lesson.py            # 강습
│   │   │   ├── enrollment.py        # 수강
│   │   │   ├── instructor.py        # 강사
│   │   │   ├── lesson_content.py    # AI 생성 콘텐츠
│   │   │   ├── lesson_interest.py   # 조회/찜 기록
│   │   │   ├── feedback.py          # 피드백
│   │   │   ├── faq.py               # FAQ
│   │   │   ├── chat.py              # 채팅 세션/메시지
│   │   │   ├── knowledge.py         # KnowledgeChunk (RAG 지식 청크 + pgvector)
│   │   │   └── ai_log.py            # AI 사용 로그
│   │   ├── routers/
│   │   │   ├── admin/               # 관리자 API
│   │   │   │   ├── dashboard.py     # 대시보드 통계
│   │   │   │   ├── lessons.py       # 강습 관리
│   │   │   │   └── enrollments.py   # 수강 관리
│   │   │   ├── my/                  # 수강생 API
│   │   │   │   ├── enrollments.py   # 내 수강 현황
│   │   │   │   └── recommendations.py # 맞춤 추천
│   │   │   ├── lessons.py           # 강습 조회/찜
│   │   │   └── chat.py              # AI 채팅 (비스트리밍 + SSE)
│   │   ├── services/
│   │   │   ├── ai/
│   │   │   │   ├── agent_state.py      # AgentState TypedDict
│   │   │   │   ├── agent_nodes.py      # Router / ToolExecutor / Validator / Response 노드
│   │   │   │   ├── agent_graph.py      # LangGraph 그래프·조건 분기
│   │   │   │   ├── embedding_service.py # 임베딩 생성 + 벡터 검색
│   │   │   │   ├── langfuse_client.py  # Langfuse 싱글톤
│   │   │   │   ├── llm_client.py       # OpenAI 클라이언트
│   │   │   │   ├── content_generator.py # 강습 콘텐츠 생성
│   │   │   │   └── tool_executor.py    # 도구 실행기
│   │   │   ├── chat_service.py      # LangGraph 스트리밍·세션 저장
│   │   │   ├── recommendation_service.py # 추천 로직
│   │   │   ├── feedback_service.py  # AI 피드백 생성
│   │   │   └── dashboard_service.py # 통계 집계
│   │   ├── schemas/                 # Pydantic 스키마
│   │   └── main.py                  # FastAPI 앱
│   ├── knowledge_base/              # RAG용 지식 문서 (19개 md, 125개 청크)
│   │   ├── sports/                  # 종목별 가이드 (11개)
│   │   ├── platform/                # 플랫폼 안내 (4개)
│   │   ├── instructors/             # 강사 프로필
│   │   └── tips/                    # 운동 팁 (3개)
│   ├── scripts/
│   │   ├── load_knowledge.py        # 지식 청킹 → 임베딩 → DB 로딩
│   │   └── seed_data.py             # 시드 데이터
│   ├── alembic/                     # 마이그레이션
│   └── static/thumbnails/           # (레거시 폴더, 현재는 기본 URL 위주)
│
├── client/                          # React 프론트엔드
│   ├── src/
│   │   ├── components/
│   │   │   ├── layout/              # Header, Footer, Layout
│   │   │   └── common/              # Pagination 등
│   │   ├── pages/
│   │   │   ├── HomePage.tsx         # 메인 (히어로 + 추천)
│   │   │   ├── LessonsPage.tsx      # 강습 목록
│   │   │   ├── LessonDetailPage.tsx # 강습 상세
│   │   │   ├── ChatPage.tsx         # AI 채팅 (SSE)
│   │   │   ├── my/
│   │   │   │   └── MyEnrollmentsPage.tsx # 내 수강 현황
│   │   │   └── admin/
│   │   │       ├── DashboardPage.tsx    # 대시보드
│   │   │       ├── LessonsPage.tsx      # 강습 관리
│   │   │       ├── LessonDetailPage.tsx # 강습 상세/콘텐츠 생성
│   │   │       └── EnrollmentsPage.tsx  # 수강 관리
│   │   ├── services/api.ts          # API 클라이언트 (POST SSE 파싱)
│   │   ├── constants/labels.ts      # 라벨 상수
│   │   └── App.tsx                  # 라우팅
│   └── index.html
│
└── docker-compose.yml               # PostgreSQL + pgvector (pg17)
```

## AI 기능 상세

### 1. AI 콘텐츠 자동 생성

강습 등록 후 "AI 콘텐츠 생성" 버튼 클릭 시:

| 항목 | 모델 | 설명 |
|------|------|------|
| 소개 문구 | GPT-4o-mini | 대상/난이도에 맞는 3~4문장 |
| 커리큘럼 | GPT-4o-mini | 난이도별 4~8주차 체계적 구성 |
| 썸네일 | (모델 사용 안 함) | 종목별 기본 썸네일 URL 자동 적용 |

소개/커리큘럼은 항목별 개별 재생성 가능

### 2. 맞춤형 추천 시스템

3가지 고정 카테고리:

| 카테고리 | 조건 | 데이터 소스 |
|----------|------|-------------|
| 🎯 다음 단계 | 완료 또는 출석률 70%+ | 수강 이력 |
| 🌟 새로운 도전 | 미경험 종목 입문 | 수강 이력 |
| 💡 관심 기반 | 찜 또는 자주 조회한 종목 | 조회/찜 기록 |

추천 이유는 GPT-4o-mini가 개인화하여 생성

### 3. AI 에이전트 파이프라인

LangGraph 상태 머신 기반 4단계 파이프라인:

```
사용자 질문 → [Router] 의도 분류 (5가지)
  ├── general_inquiry → Tool 없이 응답 (토큰·레이턴시 절감)
  └── 그 외 → [ToolExecutor] → [Validator] → Self-Correction 재시도
                                                → [Response] SSE 토큰 스트리밍
전 노드 Langfuse 트레이싱 (키 없으면 비활성화)
```

**Phase 1 — LangGraph 에이전트:**  
Router(GPT-4o-mini)가 의도를 분류하고, 의도별로 다른 Tool을 실행합니다.  
Validator가 결과를 검증하여 실패 시 필터를 완화하고 자동 재시도(Self-Correction)합니다.

**Phase 2 — RAG (pgvector):**  
125개 지식 청크를 OpenAI 임베딩 후 pgvector 코사인 유사도 검색합니다.  
벡터 검색이 비어도 ILIKE 폴백으로 FAQ 검색이 동작하도록 보장합니다.

**Phase 3 — Langfuse 관측성:**  
LLM 호출·RAG 검색 등을 Trace 단위로 추적합니다.  
API 키가 없으면 자동 비활성화(graceful degradation)됩니다.

**Phase 3.5 — SSE 스트리밍:**  
Response 노드에서 OpenAI `stream=True`로 토큰 단위 실시간 출력합니다.  
단계별 상태 표시(예: "의도 분석 중…" → "정보 검색 중…" → "답변 생성 중…")를 프론트에 전달합니다.

사용 가능한 도구(예시):

- `search_lessons`: 강습 검색
- `get_lesson_detail`: 강습 상세 조회
- `get_my_enrollments`: 내 수강 현황
- `get_recommendations`: 맞춤 추천
- `search_faq`: RAG + ILIKE 폴백 FAQ 검색

### 4. AI 피드백 생성

수강생 출석률, 진도 기반 자동 피드백 생성 (관리자 기능)

## 실행 방법

### 1. 데이터베이스 실행 (pgvector)

RAG·벡터 검색을 쓰려면 **pgvector가 포함된 PostgreSQL**이 필요합니다.  
루트 `docker-compose.yml`은 `pgvector/pgvector:pg17` 이미지를 사용합니다.

```bash
docker-compose up -d
```

직접 띄울 때 예시:

```bash
docker run -d --name course-agent-pg -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=course_agent -p 5432:5432 pgvector/pgvector:pg17
```

### 2. 서버 실행

```bash
cd server
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 환경 변수 설정
cp .env.example .env
# .env 파일 수정:
# - DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/course_agent
# - OPENAI_API_KEY=your_openai_api_key
# - (선택) Langfuse — 없으면 관측 비활성화
#   LANGFUSE_PUBLIC_KEY=...
#   LANGFUSE_SECRET_KEY=...
#   LANGFUSE_HOST=https://cloud.langfuse.com

# DB 마이그레이션
python -m alembic upgrade head

# RAG 지식 로딩 (knowledge_base → 임베딩 → knowledge_chunks)
python scripts/load_knowledge.py

# 시드 데이터 (선택)
python scripts/seed_data.py

# 서버 실행
python -m uvicorn app.main:app --reload
```

### 3. 클라이언트 실행

```bash
cd client
npm install

# 환경 변수 설정
cp .env.example .env
# VITE_API_URL=http://localhost:8000

npm run dev
```

### 4. 접속

- 사용자 화면: http://localhost:5173
- 관리자 화면: http://localhost:5173/admin/dashboard
- API 문서: http://localhost:8000/docs

## 주요 화면

### 사용자

| 경로 | 설명 |
|------|------|
| `/` | 홈 (히어로 배너, 카테고리, 맞춤 추천, 인기 강습) |
| `/lessons` | 강습 목록 (필터, 찜 기능) |
| `/lessons/:id` | 강습 상세 (썸네일, 커리큘럼, 수강신청) |
| `/my/enrollments` | 내 수강 현황 + 맞춤 추천 |
| `/chat` | AI 상담 (SSE 스트리밍) |

### 관리자

| 경로 | 설명 |
|------|------|
| `/admin/dashboard` | 대시보드 (통계, AI 사용 현황) |
| `/admin/lessons` | 강습 관리 (등록, AI 콘텐츠 생성, 발행) |
| `/admin/lessons/:id` | 강습 상세 (콘텐츠 재생성) |
| `/admin/enrollments` | 수강 관리 (상태 변경, 피드백 생성) |

## API 엔드포인트

### 강습

```
GET    /api/lessons/                  # 발행된 강습 목록
GET    /api/lessons/:id               # 강습 상세
POST   /api/lessons/:id/view          # 조회 기록
POST   /api/lessons/:id/like          # 찜 토글
```

### 수강

```
GET    /api/my/enrollments/           # 내 수강 현황
POST   /api/my/enrollments/           # 수강 신청
GET    /api/my/recommendations/       # 맞춤 추천
```

### 채팅

```
POST   /api/chat/                     # 메시지 전송 (비스트리밍)
POST   /api/chat/stream               # SSE 스트리밍 채팅
GET    /api/chat/sessions             # 세션 목록
GET    /api/chat/sessions/:id         # 세션 상세
DELETE /api/chat/sessions/:id         # 세션 삭제
```

### 관리자

```
GET    /api/admin/dashboard/          # 대시보드 통계
GET    /api/admin/dashboard/ai-logs   # AI 로그

POST   /api/admin/lessons/            # 강습 등록
POST   /api/admin/lessons/:id/generate-content  # AI 콘텐츠 생성
POST   /api/admin/lessons/:id/contents/:cid/regenerate-introduction  # 소개 재생성
POST   /api/admin/lessons/:id/contents/:cid/regenerate-curriculum    # 커리큘럼 재생성
POST   /api/admin/lessons/:id/publish # 강습 발행

GET    /api/admin/enrollments/        # 수강 목록
PUT    /api/admin/enrollments/:id     # 수강 상태 변경
POST   /api/admin/enrollments/:id/generate-feedback  # AI 피드백 생성
```

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

KnowledgeChunk (RAG 지식 청크 + pgvector 임베딩)

FAQ (자주 묻는 질문)
AILog (AI 사용 로그)
```

## 향후 개선 사항

- [ ] 사용자 인증 (JWT)
- [ ] 수강생 프로필 관리 (연령, 선호 종목)
- [ ] 출석 자동 기록 (QR 체크인)
- [x] RAG 기반 FAQ 검색
- [ ] 결제 연동
- [ ] 강사 전용 화면
- [ ] 알림 기능 (수업 리마인더)
- [ ] Multi-Agent (Supervisor / Network)
- [ ] MCP 연동
- [ ] GraphRAG (Neo4j 등)

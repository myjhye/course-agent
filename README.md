# Course Agent

LLM 기반 강의 플랫폼

## 기술 스택

### Server
- Python 3.11+
- FastAPI
- SQLAlchemy (async)
- PostgreSQL
- Pydantic v2
- Alembic

### Client
- React 18
- TypeScript
- Vite
- TailwindCSS

## 프로젝트 구조

```
course-agent/
├── server/          # FastAPI 백엔드
├── client/          # React 프론트엔드
└── docker-compose.yml
```

## 실행 방법

### 1. 데이터베이스 실행

```bash
docker-compose up -d
```

### 2. Server 실행

```bash
cd server
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# .env 파일 수정 (DATABASE_URL, OPENAI_API_KEY)
uvicorn app.main:app --reload
```

### 3. Client 실행

```bash
cd client
npm install
cp .env.example .env
# .env 파일 수정 (VITE_API_URL)
npm run dev
```

## API 문서

Server 실행 후 http://localhost:8000/docs 에서 Swagger UI 확인 가능


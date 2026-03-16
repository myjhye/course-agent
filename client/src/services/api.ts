import axios from 'axios';
import type {
  Instructor,
  Lesson,
  LessonDetail,
  LessonContent,
  LessonCreateRequest,
  EnrollmentDetail,
  EnrollmentCreateRequest,
  Feedback,
} from '../types';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/** 백엔드 REST API 클라이언트 인스턴스. 공통 baseURL과 JSON 헤더를 설정한다. */
const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 페이징 응답 타입
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// ===== 강사 (운영자) =====
/** 운영자용 강사 관리 API 래퍼. 강사 생성/조회/삭제 엔드포인트를 감싼다. */
export const instructorApi = {
  getAll: () => api.get<Instructor[]>('/api/admin/instructors/'),
  getById: (id: number) => api.get<Instructor>(`/api/admin/instructors/${id}`),
  create: (data: { name: string; specialty?: string; bio?: string }) =>
    api.post<Instructor>('/api/admin/instructors/', data),
  delete: (id: number) => api.delete(`/api/admin/instructors/${id}`),
};

// ===== 강습 (운영자) =====
/** 운영자용 강습 관리 API. 강습 CRUD와 AI 콘텐츠 생성/발행을 호출한다. */
export const adminLessonApi = {
  getAll: (params?: { page?: number; page_size?: number; status?: string }) =>
    api.get<PaginatedResponse<Lesson>>('/api/admin/lessons/', { params }),
  getById: (id: number) => api.get<LessonDetail>(`/api/admin/lessons/${id}`),
  create: (data: LessonCreateRequest) =>
    api.post<Lesson>('/api/admin/lessons/', data),
  update: (id: number, data: Partial<LessonCreateRequest>) =>
    api.put<Lesson>(`/api/admin/lessons/${id}`, data),
  delete: (id: number) => api.delete(`/api/admin/lessons/${id}`),
  
  // AI 콘텐츠
  generateContent: (id: number) =>
    api.post<LessonContent>(`/api/admin/lessons/${id}/generate-content`),
  getContents: (id: number) =>
    api.get<LessonContent[]>(`/api/admin/lessons/${id}/contents`),
  updateContent: (lessonId: number, contentId: number, data: { introduction?: string; curriculum?: object }) =>
    api.put<LessonContent>(`/api/admin/lessons/${lessonId}/contents/${contentId}`, data),
  activateContent: (lessonId: number, contentId: number) =>
    api.post(`/api/admin/lessons/${lessonId}/contents/${contentId}/activate`),
  
  // 개별 재생성 API
  regenerateIntroduction: (lessonId: number, contentId: number) =>
    api.post(`/api/admin/lessons/${lessonId}/contents/${contentId}/regenerate-introduction`),
  regenerateCurriculum: (lessonId: number, contentId: number) =>
    api.post(`/api/admin/lessons/${lessonId}/contents/${contentId}/regenerate-curriculum`),
  
  // 발행
  publish: (id: number) => api.post<Lesson>(`/api/admin/lessons/${id}/publish`),
};

// ===== 강습 (공개) =====
/** 수강생이 보는 공개 강습 목록/상세 API. 조회/찜 관련 엔드포인트를 포함한다. */
export const lessonApi = {
  getPublished: (params?: { page?: number; page_size?: number; sport_type?: string; target_audience?: string; difficulty?: string }) =>
    api.get<PaginatedResponse<Lesson>>('/api/lessons/', { params }),
  getById: (id: number) => api.get<LessonDetail>(`/api/lessons/${id}`),

  // 조회 기록
  recordView: (lessonId: number, studentName: string) =>
    api.post(`/api/lessons/${lessonId}/view?student_name=${studentName}`),

  // 찜 토글
  toggleLike: (lessonId: number, studentName: string) =>
    api.post(`/api/lessons/${lessonId}/like?student_name=${studentName}`),

  // 찜 상태
  getLikeStatus: (lessonId: number, studentName: string) =>
    api.get<{ liked: boolean }>(`/api/lessons/${lessonId}/like-status?student_name=${studentName}`),

  // 내가 찜한 강습 목록
  getLikedLessons: (studentName: string) =>
    api.get<{
      id: number;
      title: string;
      sport_type: string;
      difficulty: string;
      target_audience: string;
      instructor_name: string | null;
      thumbnail_url: string | null;
    }[]>(`/api/lessons/my/liked?student_name=${studentName}`),
};

// ===== 수강 (운영자) =====
/** 운영자용 수강 관리 API. 수강 목록과 상태/출결 업데이트, 피드백 생성을 처리한다. */
export const adminEnrollmentApi = {
  getAll: (params?: { page?: number; page_size?: number; status?: string; lesson_id?: number }) =>
    api.get<PaginatedResponse<EnrollmentDetail>>('/api/admin/enrollments/', { params }),
  update: (id: number, data: { status?: string; attendance_rate?: number }) =>
    api.put<EnrollmentDetail>(`/api/admin/enrollments/${id}`, data),
  generateFeedback: (id: number) =>
    api.post<Feedback>(`/api/admin/enrollments/${id}/generate-feedback`),
  getFeedback: (id: number) =>
    api.get<Feedback>(`/api/admin/enrollments/${id}/feedback`),
};

// ===== 수강 (수강생) =====
/** 수강생용 내 수강 API. 내 수강 목록 조회와 신청/취소를 담당한다. */
export const myEnrollmentApi = {
  getAll: (studentName: string) =>
    api.get<EnrollmentDetail[]>('/api/my/enrollments/', { params: { student_name: studentName } }),
  create: (data: EnrollmentCreateRequest) =>
    api.post<EnrollmentDetail>('/api/my/enrollments/', data),
  cancel: (id: number) => api.delete(`/api/my/enrollments/${id}`),
};

// ===== 추천 (수강생) =====
// 타입 추가
export interface CategorizedRecommendations {
  next_level: RecommendationItem | null;
  new_sport: RecommendationItem | null;
  interest_based: RecommendationItem | null;
}

export interface RecommendationItem {
  lesson: {
    id: number;
    title: string;
    sport_type: string;
    difficulty: string;
    instructor_name: string | null;
    thumbnail_url: string | null;
  };
  reason: string;
  reason_type: string;
}

/** 수강생용 개인화 추천 API. 카테고리별 추천 강습을 조회한다. */
export const myRecommendationApi = {
  getCategorized: (studentName: string) =>
    api.get<CategorizedRecommendations>(`/api/my/recommendations/?student_name=${studentName}`),
};

// ===== 대시보드 (운영자) =====
export interface DashboardStats {
  period: {
    start_date: string;
    end_date: string;
  };
  lessons: {
    total: number;
    published: number;
    draft: number;
    archived: number;
    by_sport: Record<string, number>;
  };
  enrollments: {
    total: number;
    new_in_period: number;
    completed_in_period: number;
    enrolled: number;
    in_progress: number;
    completed: number;
    cancelled: number;
    avg_attendance_rate: number;
  };
  instructors: {
    total: number;
  };
  ai_usage: {
    total_calls: number;
    by_feature: Record<string, number>;
    total_tokens: number;
    avg_latency_ms: number;
    edit_rate: number;
  };
}

export interface AILog {
  id: number;
  feature_type: string;
  lesson_id: number | null;
  enrollment_id: number | null;
  input_data: Record<string, any> | null;
  output_data: Record<string, any> | null;
  tokens_used: number | null;
  latency_ms: number | null;
  was_edited: boolean;
  created_at: string;
}

/** 운영자용 대시보드 API. 통계와 AI 로그 목록을 조회한다. */
export const adminDashboardApi = {
  getStats: (startDate?: string, endDate?: string) =>
    api.get<DashboardStats>('/api/admin/dashboard/', {
      params: { start_date: startDate, end_date: endDate }
    }),
  getAILogs: (featureType?: string, skip: number = 0, limit: number = 20) =>
    api.get<AILog[]>('/api/admin/dashboard/ai-logs', {
      params: { feature_type: featureType, skip, limit }
    }),
};

// ===== 채팅 =====
export interface ChatMessage {
  id: number;
  session_id: string;
  role: 'user' | 'assistant';
  content: string;
  tool_used: string | null;
  tool_result: Record<string, any> | null;
  created_at: string;
}

export interface ChatSession {
  id: number;
  session_id: string;
  student_name: string | null;
  title: string | null;
  created_at: string;
  updated_at: string;
}

export interface ChatResponse {
  session_id: string;
  user_message: ChatMessage;
  assistant_message: ChatMessage;
}

/** 채팅 기능 API. 동기/스트리밍 채팅 호출과 세션 관리를 제공한다. */
export const chatApi = {
  /** 단일 요청/응답 패턴으로 채팅 메시지를 전송한다. 스트리밍을 지원하지 않는 클라이언트용이다. */
  sendMessage: (sessionId: string, message: string, studentName?: string) =>
    api.post<ChatResponse>('/api/chat/', {
      session_id: sessionId,
      message,
      student_name: studentName
    }),
  /** SSE 스트리밍으로 채팅 메시지를 전송한다. fetch + ReadableStream을 사용해 POST SSE를 구현한다. */
  sendMessageStream: (
    sessionId: string,
    message: string,
    studentName: string,
    callbacks: {
      onStatus?: (data: { step: string; message?: string; intent?: string }) => void;
      onToken?: (data: { content: string }) => void;
      onDone?: (data: { tools_used: string[]; total_tokens: number; message_id: number }) => void;
      onError?: (error: string) => void;
    },
  ) => {
    const abortController = new AbortController();

    const baseUrl = api.defaults.baseURL || '';

    // POST 요청으로 SSE 스트리밍 엔드포인트를 호출한다
    fetch(`${baseUrl}/api/chat/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        message,
        student_name: studentName,
      }),
      signal: abortController.signal,
    })
      .then(async (response) => {
        if (!response.ok) {
          callbacks.onError?.(`HTTP ${response.status}`);
          return;
        }

        // ReadableStream으로 SSE 청크를 순차적으로 읽는다
        const reader = response.body?.getReader();
        if (!reader) {
          callbacks.onError?.('ReadableStream not supported');
          return;
        }

        // 바이너리 스트림을 UTF-8 문자열로 복원할 디코더와 버퍼를 준비한다
        const decoder = new TextDecoder();
        let buffer = '';

        // 스트림이 끝날 때까지 청크를 읽고 SSE 이벤트로 파싱한다
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });

          // 줄바꿈 기준으로 분할하고 마지막 불완전한 줄은 버퍼에 남긴다
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          let currentEvent = '';

          // SSE 프로토콜을 파싱해 event / data 필드를 분리한다
          for (const line of lines) {
            if (line.startsWith('event:')) {
              currentEvent = line.slice(6).trim();
            } else if (line.startsWith('data:')) {
              const dataStr = line.slice(5).trim();
              if (!dataStr) continue;

              // data 라인의 JSON 페이로드를 파싱하고 콜백을 호출한다
              try {
                const data = JSON.parse(dataStr);

                switch (currentEvent) {
                  case 'status':
                    callbacks.onStatus?.(data);
                    break;
                  case 'token':
                    callbacks.onToken?.(data);
                    break;
                  case 'done':
                    callbacks.onDone?.(data);
                    break;
                  case 'error':
                    callbacks.onError?.(data.message);
                    break;
                }
              } catch {
                // ignore JSON parse errors
              }

              currentEvent = '';
            }
          }
        }
      })
      .catch((err) => {
        if (err.name !== 'AbortError') {
          callbacks.onError?.(err.message);
        }
      });

    return () => abortController.abort();
  },
  getSessions: () =>
    api.get<ChatSession[]>('/api/chat/sessions'),
  getSessionDetail: (sessionId: string) =>
    api.get<{ session: ChatSession; messages: ChatMessage[] }>(`/api/chat/sessions/${sessionId}`),
  deleteSession: (sessionId: string) =>
    api.delete(`/api/chat/sessions/${sessionId}`),
};

export default api;

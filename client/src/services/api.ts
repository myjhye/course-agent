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
export const instructorApi = {
  getAll: () => api.get<Instructor[]>('/api/admin/instructors/'),
  getById: (id: number) => api.get<Instructor>(`/api/admin/instructors/${id}`),
  create: (data: { name: string; specialty?: string; bio?: string }) =>
    api.post<Instructor>('/api/admin/instructors/', data),
  delete: (id: number) => api.delete(`/api/admin/instructors/${id}`),
};

// ===== 강습 (운영자) =====
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

export const chatApi = {
  sendMessage: (sessionId: string, message: string, studentName?: string) =>
    api.post<ChatResponse>('/api/chat/', {
      session_id: sessionId,
      message,
      student_name: studentName
    }),
  getSessions: () =>
    api.get<ChatSession[]>('/api/chat/sessions'),
  getSessionDetail: (sessionId: string) =>
    api.get<{ session: ChatSession; messages: ChatMessage[] }>(`/api/chat/sessions/${sessionId}`),
  deleteSession: (sessionId: string) =>
    api.delete(`/api/chat/sessions/${sessionId}`),
};

export default api;

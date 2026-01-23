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
  Recommendation,
} from '../types';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

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
  getAll: (params?: { status?: string; skip?: number; limit?: number }) =>
    api.get<Lesson[]>('/api/admin/lessons/', { params }),
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
  
  // 발행
  publish: (id: number) => api.post<Lesson>(`/api/admin/lessons/${id}/publish`),
};

// ===== 강습 (공개) =====
export const lessonApi = {
  getPublished: (params?: { sport_type?: string; difficulty?: string }) =>
    api.get<Lesson[]>('/api/lessons/', { params }),
  getById: (id: number) => api.get<LessonDetail>(`/api/lessons/${id}`),
};

// ===== 수강 (운영자) =====
export const adminEnrollmentApi = {
  getAll: (params?: { status?: string; lesson_id?: number }) =>
    api.get<EnrollmentDetail[]>('/api/admin/enrollments/', { params }),
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
export const myRecommendationApi = {
  getRecommendations: (studentName: string, limit: number = 3) =>
    api.get<Recommendation[]>('/api/my/recommendations/', {
      params: { student_name: studentName, limit }
    }),
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

export default api;

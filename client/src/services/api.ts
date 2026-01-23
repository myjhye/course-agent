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

export default api;

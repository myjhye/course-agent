import axios from 'axios';
import type { Course, CourseCreate, CourseUpdate } from '../types';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const courseApi = {
  getCourses: async (): Promise<Course[]> => {
    const response = await apiClient.get<Course[]>('/api/courses');
    return response.data;
  },

  getCourse: async (id: number): Promise<Course> => {
    const response = await apiClient.get<Course>(`/api/courses/${id}`);
    return response.data;
  },

  createCourse: async (data: CourseCreate): Promise<Course> => {
    const response = await apiClient.post<Course>('/api/courses', data);
    return response.data;
  },

  updateCourse: async (id: number, data: CourseUpdate): Promise<Course> => {
    const response = await apiClient.put<Course>(`/api/courses/${id}`, data);
    return response.data;
  },

  deleteCourse: async (id: number): Promise<void> => {
    await apiClient.delete(`/api/courses/${id}`);
  },

  generateCourseContent: async (id: number): Promise<Course> => {
    const response = await apiClient.post<Course>(`/api/courses/${id}/generate`);
    return response.data;
  },
};

export const api = apiClient;


// Enums
export type SportType = 'swimming' | 'tennis' | 'golf' | 'fitness' | 'yoga' | 'pilates' | 'other';
export type TargetAudience = 'adult' | 'child' | 'senior' | 'all';
export type Difficulty = 'beginner' | 'elementary' | 'intermediate' | 'advanced';
export type LessonStatus = 'draft' | 'published' | 'archived';
export type EnrollmentStatus = 'enrolled' | 'in_progress' | 'completed' | 'cancelled';

// 강사
export interface Instructor {
  id: number;
  name: string;
  specialty: string | null;
  bio: string | null;
  created_at: string;
}

// 강습
export interface Lesson {
  id: number;
  title: string;
  sport_type: SportType;
  target_audience: TargetAudience;
  difficulty: Difficulty;
  instructor_id: number | null;
  status: LessonStatus;
  created_at: string;
  updated_at: string;
  active_content?: LessonContent | null; // 목록용 썸네일 포함
}

export interface LessonDetail extends Lesson {
  instructor_name: string | null;
  active_content: LessonContent | null;
}

// 강습 콘텐츠
export interface CurriculumWeek {
  week: number;
  title: string;
  topics: string[];
}

export interface Curriculum {
  weeks: CurriculumWeek[];
}

export interface LessonContent {
  id: number;
  lesson_id: number;
  introduction: string | null;
  curriculum: Curriculum | null;
  thumbnail_url: string | null;
  version: number;
  is_active: boolean;
  created_at: string;
}

// 수강
export interface Enrollment {
  id: number;
  student_name: string;
  lesson_id: number;
  status: EnrollmentStatus;
  attendance_rate: number | null;
  completion_date: string | null;
  created_at: string;
  updated_at: string;
}

export interface EnrollmentDetail extends Enrollment {
  lesson_title: string;
  lesson_sport_type: string;
  lesson_difficulty: string;
}

// 피드백
export interface Feedback {
  id: number;
  enrollment_id: number;
  student_feedback: string | null;
  instructor_feedback: string | null;
  created_at: string;
}

// Request 타입
export interface LessonCreateRequest {
  title: string;
  sport_type: SportType;
  target_audience: TargetAudience;
  difficulty: Difficulty;
  instructor_id?: number;
}

export interface EnrollmentCreateRequest {
  lesson_id: number;
  student_name: string;
}

// 추천
export interface RecommendedLesson {
  id: number;
  title: string;
  sport_type: string;
  target_audience: string;
  difficulty: string;
  instructor_name: string | null;
  thumbnail_url: string | null;
}

export interface Recommendation {
  lesson: RecommendedLesson;
  reason: string;
  reason_type: string;
}

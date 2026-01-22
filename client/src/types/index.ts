export interface Course {
  id: number;
  title: string;
  category: string;
  description: string | null;
  curriculum: string | null;
  created_at: string;
  updated_at: string;
}

export interface CourseCreate {
  title: string;
  category: string;
  description?: string | null;
  curriculum?: string | null;
}

export interface CourseUpdate {
  title?: string;
  category?: string;
  description?: string | null;
  curriculum?: string | null;
}


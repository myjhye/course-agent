import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { courseApi } from '../services/api';
import type { Course } from '../types';

function CourseDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [course, setCourse] = useState<Course | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    const fetchCourse = async () => {
      if (!id) return;

      try {
        setLoading(true);
        const data = await courseApi.getCourse(Number(id));
        setCourse(data);
      } catch (err) {
        setError(err instanceof Error ? err : new Error('Failed to fetch course'));
      } finally {
        setLoading(false);
      }
    };

    fetchCourse();
  }, [id]);

  if (loading) {
    return <div className="p-8">Loading...</div>;
  }

  if (error || !course) {
    return (
      <div className="p-8">
        <div className="text-red-600 mb-4">Error: {error?.message || 'Course not found'}</div>
        <Link to="/courses" className="text-blue-600 hover:text-blue-800">
          강의 목록으로 돌아가기
        </Link>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-4xl mx-auto">
        <div className="mb-6">
          <Link
            to="/courses"
            className="text-blue-600 hover:text-blue-800"
          >
            ← 강의 목록으로
          </Link>
        </div>

        <div className="bg-white p-8 rounded-lg shadow">
          <h1 className="text-4xl font-bold mb-4">{course.title}</h1>
          <p className="text-sm text-gray-500 mb-6">{course.category}</p>

          {course.description && (
            <div className="mb-6">
              <h2 className="text-2xl font-semibold mb-2">설명</h2>
              <p className="text-gray-700 whitespace-pre-wrap">{course.description}</p>
            </div>
          )}

          {course.curriculum && (
            <div className="mb-6">
              <h2 className="text-2xl font-semibold mb-2">커리큘럼</h2>
              <p className="text-gray-700 whitespace-pre-wrap">{course.curriculum}</p>
            </div>
          )}

          <div className="text-sm text-gray-500 mt-8">
            <p>생성일: {new Date(course.created_at).toLocaleString('ko-KR')}</p>
            <p>수정일: {new Date(course.updated_at).toLocaleString('ko-KR')}</p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default CourseDetailPage;


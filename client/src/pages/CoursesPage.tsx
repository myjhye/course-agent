import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { courseApi } from '../services/api';
import type { Course } from '../types';

const DEFAULT_THUMBNAIL = '/default-thumbnail.jpeg';

export default function CoursesPage() {
  const [courses, setCourses] = useState<Course[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchCourses = async () => {
      try {
        const data = await courseApi.getCourses();
        setCourses(data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchCourses();
  }, []);

  const getThumbnailUrl = (url: string | null) => {
    if (!url) return DEFAULT_THUMBNAIL;
    // 서버 URL 붙이기
    if (url.startsWith('/')) {
      return `http://localhost:8000${url}`;
    }
    return url;
  };

  if (loading) return <div className="p-8">로딩 중...</div>;

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold">강의 목록</h1>
        <Link 
          to="/courses/new" 
          className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600"
        >
          + 새 강의
        </Link>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {courses.map(course => (
          <Link 
            key={course.id} 
            to={`/courses/${course.id}`}
            className="border rounded-lg overflow-hidden hover:shadow-lg transition-shadow"
          >
            <img 
              src={getThumbnailUrl(course.thumbnail_url)} 
              alt={course.title}
              className="w-full h-48 object-cover bg-gray-200"
              onError={(e) => {
                (e.target as HTMLImageElement).src = DEFAULT_THUMBNAIL;
              }}
            />
            <div className="p-4">
              <span className="text-sm text-blue-500">{course.category}</span>
              <h2 className="text-lg font-semibold mt-1">{course.title}</h2>
              {course.description && (
                <p className="text-gray-600 text-sm mt-2 line-clamp-2">
                  {course.description}
                </p>
              )}
            </div>
          </Link>
        ))}
      </div>

      {courses.length === 0 && (
        <p className="text-center text-gray-500 mt-8">등록된 강의가 없습니다.</p>
      )}
    </div>
  );
}

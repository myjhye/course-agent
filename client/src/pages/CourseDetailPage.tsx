import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import { courseApi } from '../services/api';
import type { Course } from '../types';

const DEFAULT_THUMBNAIL = '/default-thumbnail.jpeg';

export default function CourseDetailPage() {
  const { id } = useParams();
  const [course, setCourse] = useState<Course | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchCourse = async () => {
    if (!id) return;
    
    try {
      const data = await courseApi.getCourse(Number(id));
      setCourse(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCourse();
  }, [id]);

  const getThumbnailUrl = (url: string | null) => {
    if (!url) return DEFAULT_THUMBNAIL;
    if (url.startsWith('/')) {
      return `http://localhost:8000${url}`;
    }
    return url;
  };

  if (loading) return <div className="p-8">로딩 중...</div>;
  if (!course) return <div className="p-8">강의를 찾을 수 없습니다.</div>;

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <Link to="/courses" className="text-blue-500 hover:underline mb-4 inline-block">
        ← 강의 목록으로
      </Link>

      {/* 썸네일 이미지 */}
      <img 
        src={getThumbnailUrl(course.thumbnail_url)} 
        alt={course.title}
        className="w-full h-64 object-cover rounded-lg mb-6 bg-gray-200"
        onError={(e) => {
          (e.target as HTMLImageElement).src = DEFAULT_THUMBNAIL;
        }}
      />

      <h1 className="text-3xl font-bold mb-2">{course.title}</h1>
      <p className="text-gray-500 mb-6">{course.category}</p>

      {/* 설명 */}
      <section className="mb-8">
        <h2 className="text-xl font-semibold mb-3">설명</h2>
        {course.description ? (
          <div className="prose prose-slate max-w-none">
            <ReactMarkdown>{course.description}</ReactMarkdown>
          </div>
        ) : (
          <p className="text-gray-500">설명이 없습니다.</p>
        )}
      </section>

      {/* 커리큘럼 */}
      <section>
        <h2 className="text-xl font-semibold mb-3">커리큘럼</h2>
        {course.curriculum ? (
          <div className="prose prose-slate max-w-none">
            <ReactMarkdown>{course.curriculum}</ReactMarkdown>
          </div>
        ) : (
          <p className="text-gray-500">커리큘럼이 없습니다.</p>
        )}
      </section>
    </div>
  );
}

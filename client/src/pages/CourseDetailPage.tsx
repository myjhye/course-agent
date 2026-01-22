import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { courseApi } from '../services/api';
import type { Course } from '../types';

const DEFAULT_THUMBNAIL = '/default-thumbnail.jpeg';

export default function CourseDetailPage() {
  const { id } = useParams();
  const [course, setCourse] = useState<Course | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);

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

  const handleGenerate = async () => {
    if (!id) return;
    
    setGenerating(true);
    try {
      const data = await courseApi.generateCourseContent(Number(id));
      setCourse(data);
      alert('AI 콘텐츠가 생성되었습니다!');
    } catch (err) {
      console.error(err);
      alert('생성 실패');
    } finally {
      setGenerating(false);
    }
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

      {/* AI 생성 버튼 */}
      {(!course.description || !course.curriculum || !course.thumbnail_url) && (
        <button
          onClick={handleGenerate}
          disabled={generating}
          className="mb-6 bg-green-500 text-white px-4 py-2 rounded hover:bg-green-600 disabled:bg-gray-400"
        >
          {generating ? 'AI 생성 중...' : '🤖 AI로 콘텐츠 생성'}
        </button>
      )}

      {/* 설명 */}
      <section className="mb-8">
        <h2 className="text-xl font-semibold mb-3">설명</h2>
        <p className="text-gray-700 whitespace-pre-wrap">
          {course.description || '설명이 없습니다. AI 생성 버튼을 눌러주세요.'}
        </p>
      </section>

      {/* 커리큘럼 */}
      <section>
        <h2 className="text-xl font-semibold mb-3">커리큘럼</h2>
        <div className="text-gray-700 whitespace-pre-wrap">
          {course.curriculum || '커리큘럼이 없습니다. AI 생성 버튼을 눌러주세요.'}
        </div>
      </section>
    </div>
  );
}

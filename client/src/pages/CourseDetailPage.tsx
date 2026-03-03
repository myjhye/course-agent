import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import { lessonApi } from '../services/api';
import type { LessonDetail } from '../types';
import { getImageUrl, handleImageError } from '../utils/image';

export default function CourseDetailPage() {
  const { id } = useParams();
  // Course -> LessonDetail 타입으로 변경
  const [course, setCourse] = useState<LessonDetail | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchCourse = async () => {
    if (!id) return;
    
    try {
      // courseApi.getCourse -> lessonApi.getById로 변경
      const res = await lessonApi.getById(Number(id));
      setCourse(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCourse();
  }, [id]);

  if (loading) return <div className="p-8">로딩 중...</div>;
  if (!course) return <div className="p-8">강의를 찾을 수 없습니다.</div>;

  // 데이터 구조 변경에 따른 필드 매핑 (category -> sport_type 등)
  const thumbnail = course.active_content?.thumbnail_url || null;
  const description = course.active_content?.introduction || null;
  // 커리큘럼이 객체(JSON)일 경우 문자열로 변환하여 출력
  const curriculum = typeof course.active_content?.curriculum === 'object' 
    ? JSON.stringify(course.active_content.curriculum, null, 2) 
    : null;

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <Link to="/lessons" className="text-blue-500 hover:underline mb-4 inline-block">
        ← 강습 목록으로
      </Link>

      {/* 썸네일 이미지 */}
      <img 
        src={getImageUrl(thumbnail)} 
        alt={course.title}
        className="w-full h-64 object-cover rounded-lg mb-6 bg-gray-200"
        onError={handleImageError}
      />

      <h1 className="text-3xl font-bold mb-2">{course.title}</h1>
      <p className="text-gray-500 mb-6">
        {course.sport_type} · {course.difficulty} · {course.instructor_name || '강사 미지정'}
      </p>

      {/* 설명 */}
      <section className="mb-8">
        <h2 className="text-xl font-semibold mb-3">설명</h2>
        {description ? (
          <div className="prose prose-slate max-w-none">
            <ReactMarkdown>{description}</ReactMarkdown>
          </div>
        ) : (
          <p className="text-gray-500">설명이 없습니다.</p>
        )}
      </section>

      {/* 커리큘럼 */}
      <section>
        <h2 className="text-xl font-semibold mb-3">커리큘럼</h2>
        {curriculum ? (
          <div className="prose prose-slate max-w-none">
             <pre className="bg-gray-50 p-4 rounded-lg overflow-auto text-sm">
                {curriculum}
             </pre>
          </div>
        ) : (
          <p className="text-gray-500">커리큘럼이 없습니다.</p>
        )}
      </section>
    </div>
  );
}

import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { lessonApi } from '../services/api';
import type { Lesson } from '../types';
import { SPORT_LABELS } from '../constants/labels';
import { getImageUrl, handleImageError } from '../utils/image';

export default function CoursesPage() {
  const [courses, setCourses] = useState<Lesson[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchCourses = async () => {
      try {
        const res = await lessonApi.getPublished();
        setCourses(res.data.items);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchCourses();
  }, []);


  if (loading) return <div className="p-8 text-center">로딩 중...</div>;

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold text-slate-900">강습 목록</h1>
        <Link 
          to="/lessons/new" 
          className="bg-blue-600 text-white px-5 py-2.5 rounded-xl font-semibold hover:bg-blue-700 transition-colors shadow-lg shadow-blue-500/20"
        >
          + 새 강습 만들기
        </Link>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
        {courses.map(course => {
          const thumbnail = course.active_content?.thumbnail_url;
          const introduction = course.active_content?.introduction;

          return (
            <Link 
              key={course.id} 
              to={`/lessons/${course.id}`}
              className="group bg-white border border-slate-200 rounded-2xl overflow-hidden hover:shadow-xl hover:border-blue-400 transition-all duration-300"
            >
              <div className="relative aspect-video bg-slate-100 overflow-hidden">
                <img 
                  src={getImageUrl(thumbnail)} 
                  alt={course.title}
                  className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                  onError={handleImageError}
                />
                <div className="absolute top-3 left-3">
                  <span className="bg-white/90 backdrop-blur px-2.5 py-1 rounded-lg text-xs font-bold text-blue-600 shadow-sm">
                    {SPORT_LABELS[course.sport_type] || course.sport_type}
                  </span>
                </div>
              </div>
              
              <div className="p-5">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-[10px] font-black uppercase tracking-widest text-slate-400">
                    {course.difficulty} · {course.target_audience}
                  </span>
                </div>
                <h2 className="text-xl font-bold text-slate-900 mb-2 group-hover:text-blue-600 transition-colors">
                  {course.title}
                </h2>
                {introduction && (
                  <p className="text-slate-500 text-sm line-clamp-2 leading-relaxed">
                    {introduction}
                  </p>
                )}
              </div>
            </Link>
          );
        })}
      </div>

      {courses.length === 0 && (
        <div className="text-center py-20 bg-slate-50 rounded-3xl border-2 border-dashed border-slate-200 mt-8">
          <p className="text-slate-400 font-medium">등록된 강습이 없습니다.</p>
        </div>
      )}
    </div>
  );
}

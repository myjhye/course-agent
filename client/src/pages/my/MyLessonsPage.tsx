import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { lessonApi } from '../../services/api';
import type { Lesson } from '../../types';
import Pagination from '../../components/common/Pagination';
import { SPORT_LABELS, TARGET_LABELS, DIFFICULTY_LABELS } from '../../constants/labels';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function MyLessonsPage() {
  const [lessons, setLessons] = useState<Lesson[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);

  useEffect(() => {
    loadLessons();
  }, [page]);

  const loadLessons = async () => {
    setLoading(true);
    try {
      const res = await lessonApi.getPublished({ page, page_size: 12 });
      setLessons(res.data.items);
      setTotalPages(res.data.total_pages);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-gray-500">로딩 중...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* 헤더 */}
      <header className="bg-white shadow-sm">
        <div className="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between">
          <Link to="/" className="text-xl font-bold text-blue-600">
            Course Agent
          </Link>
          <Link
            to="/my/enrollments"
            className="text-sm text-gray-600 hover:text-blue-600"
          >
            내 수강 현황
          </Link>
        </div>
      </header>

      {/* 메인 */}
      <main className="max-w-6xl mx-auto px-4 py-8">
        <h1 className="text-2xl font-bold mb-6">강습 목록</h1>

        {loading ? (
          <div className="text-center py-16 text-gray-500">로딩 중...</div>
        ) : lessons.length === 0 ? (
          <div className="text-center py-16 text-gray-500">
            현재 등록된 강습이 없습니다.
          </div>
        ) : (
          <>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {lessons.map((lesson) => (
                <LessonCard key={lesson.id} lesson={lesson} />
              ))}
            </div>

            <Pagination
              page={page}
              totalPages={totalPages}
              onPageChange={setPage}
            />
          </>
        )}
      </main>
    </div>
  );
}

function LessonCard({ lesson }: { lesson: Lesson & { active_content?: { thumbnail_url?: string | null } } }) {
  const thumbnailUrl = lesson.active_content?.thumbnail_url
    ? `${API_BASE}${lesson.active_content.thumbnail_url}`
    : null;

  return (
    <Link
      to={`/lessons/${lesson.id}`}
      className="bg-white rounded-xl shadow-md overflow-hidden hover:shadow-lg transition-shadow"
    >
      {/* 썸네일 */}
      <div className="aspect-video bg-gradient-to-br from-blue-100 to-blue-200 relative">
        {thumbnailUrl ? (
          <img
            src={thumbnailUrl}
            alt={lesson.title}
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <span className="text-4xl">
              {lesson.sport_type === 'swimming' && '🏊'}
              {lesson.sport_type === 'tennis' && '🎾'}
              {lesson.sport_type === 'golf' && '⛳'}
              {lesson.sport_type === 'fitness' && '💪'}
              {lesson.sport_type === 'yoga' && '🧘'}
              {lesson.sport_type === 'pilates' && '🤸'}
              {lesson.sport_type === 'other' && '🏃'}
            </span>
          </div>
        )}
        {/* 종목 뱃지 */}
        <span className="absolute top-3 left-3 bg-blue-600 text-white text-xs px-2 py-1 rounded-full">
          {SPORT_LABELS[lesson.sport_type] || lesson.sport_type}
        </span>
        {/* 난이도 뱃지 */}
        <span className="absolute top-3 right-3 bg-white/90 text-gray-700 text-xs px-2 py-1 rounded-full">
          {DIFFICULTY_LABELS[lesson.difficulty] || lesson.difficulty}
        </span>
      </div>

      {/* 정보 */}
      <div className="p-4">
        <h3 className="font-bold text-lg text-gray-900 mb-2 line-clamp-2">
          {lesson.title}
        </h3>
        <div className="flex items-center gap-2 text-sm text-gray-500">
          <span className="bg-gray-100 px-2 py-0.5 rounded">
            {TARGET_LABELS[lesson.target_audience] || lesson.target_audience}
          </span>
        </div>
      </div>
    </Link>
  );
}

import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { lessonApi } from '../../services/api';
import type { Lesson, SportType, TargetAudience, Difficulty } from '../../types';
import Pagination from '../../components/common/Pagination';
import { SPORT_LABELS, TARGET_LABELS, DIFFICULTY_LABELS } from '../../constants/labels';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const STUDENT_NAME = '홍길동'; // 하드코딩

const SPORT_OPTIONS: { value: SportType | ''; label: string }[] = [
  { value: '', label: '전체' },
  ...Object.entries(SPORT_LABELS).map(([value, label]) => ({
    value: value as SportType,
    label,
  })),
];

const TARGET_OPTIONS: { value: TargetAudience | ''; label: string }[] = [
  { value: '', label: '전체' },
  ...Object.entries(TARGET_LABELS).map(([value, label]) => ({
    value: value as TargetAudience,
    label,
  })),
];

const DIFFICULTY_OPTIONS: { value: Difficulty | ''; label: string }[] = [
  { value: '', label: '전체' },
  ...Object.entries(DIFFICULTY_LABELS).map(([value, label]) => ({
    value: value as Difficulty,
    label,
  })),
];

export default function MyLessonsPage() {
  const [lessons, setLessons] = useState<Lesson[]>([]);
  const [likedLessons, setLikedLessons] = useState<Set<number>>(new Set());
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [filters, setFilters] = useState<{
    sport_type?: string;
    target_audience?: string;
    difficulty?: string;
  }>({});

  useEffect(() => {
    loadLessons();
  }, [page, filters]);

  const loadLessons = async () => {
    setLoading(true);
    try {
      const params: {
        page: number;
        page_size: number;
        sport_type?: string;
        target_audience?: string;
        difficulty?: string;
      } = {
        page,
        page_size: 6,
      };

      if (filters.sport_type) {
        params.sport_type = filters.sport_type;
      }
      if (filters.target_audience) {
        params.target_audience = filters.target_audience;
      }
      if (filters.difficulty) {
        params.difficulty = filters.difficulty;
      }

      const res = await lessonApi.getPublished(params);
      setLessons(res.data.items);
      setTotalPages(res.data.total_pages);

      // 각 강습의 찜 상태 확인
      const likedSet = new Set<number>();
      await Promise.all(
        res.data.items.map(async (lesson: Lesson) => {
          try {
            const likeRes = await lessonApi.getLikeStatus(lesson.id, STUDENT_NAME);
            if (likeRes.data.liked) {
              likedSet.add(lesson.id);
            }
          } catch {
            // 무시
          }
        })
      );
      setLikedLessons(likedSet);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleFilterChange = (key: 'sport_type' | 'target_audience' | 'difficulty', value: string) => {
    setFilters((prev) => {
      const newFilters = { ...prev };
      if (value === '') {
        delete newFilters[key];
      } else {
        newFilters[key] = value;
      }
      return newFilters;
    });
    setPage(1); // 필터 변경 시 첫 페이지로
  };

  const handleToggleLike = async (lessonId: number, e: React.MouseEvent) => {
    e.preventDefault(); // Link 클릭 방지
    e.stopPropagation();

    try {
      const res = await lessonApi.toggleLike(lessonId, STUDENT_NAME);
      setLikedLessons(prev => {
        const newSet = new Set(prev);
        if (res.data.liked) {
          newSet.add(lessonId);
        } else {
          newSet.delete(lessonId);
        }
        return newSet;
      });
    } catch (err) {
      console.error(err);
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

        {/* 필터 */}
        <div className="bg-white rounded-lg shadow p-4 mb-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* 종목 필터 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                종목
              </label>
              <select
                value={filters.sport_type || ''}
                onChange={(e) => handleFilterChange('sport_type', e.target.value)}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                {SPORT_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>

            {/* 대상 필터 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                대상
              </label>
              <select
                value={filters.target_audience || ''}
                onChange={(e) => handleFilterChange('target_audience', e.target.value)}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                {TARGET_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>

            {/* 난이도 필터 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                난이도
              </label>
              <select
                value={filters.difficulty || ''}
                onChange={(e) => handleFilterChange('difficulty', e.target.value)}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                {DIFFICULTY_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>

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
                <LessonCard
                  key={lesson.id}
                  lesson={lesson}
                  liked={likedLessons.has(lesson.id)}
                  onToggleLike={handleToggleLike}
                />
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

function LessonCard({
  lesson,
  liked,
  onToggleLike
}: {
  lesson: Lesson;
  liked: boolean;
  onToggleLike: (lessonId: number, e: React.MouseEvent) => void;
}) {
  // active_content가 null일 수 있으므로 옵셔널 체이닝 사용
  const thumbnailUrl = lesson.active_content?.thumbnail_url
    ? `${API_BASE}${lesson.active_content.thumbnail_url}`
    : null;

  return (
    <Link
      to={`/lessons/${lesson.id}`}
      className="bg-white rounded-xl shadow-md overflow-hidden hover:shadow-lg transition-shadow relative group"
    >
      {/* 찜 버튼 */}
      <button
        onClick={(e) => onToggleLike(lesson.id, e)}
        className="absolute bottom-4 right-4 z-10 w-12 h-12 flex items-center justify-center rounded-full bg-white/90 hover:bg-white shadow-md transition-all duration-200"
      >
        {liked ? (
          <span className="text-red-500 text-xl">❤️</span>
        ) : (
          <span className="text-gray-400 text-xl group-hover:text-gray-600">🤍</span>
        )}
      </button>

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

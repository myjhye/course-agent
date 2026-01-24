import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { Difficulty, Lesson, SportType, TargetAudience } from '../types';
import { lessonApi } from '../services/api';
import Pagination from '../components/common/Pagination';
import { DIFFICULTY_LABELS, SPORT_LABELS, TARGET_LABELS } from '../constants/labels';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// 종목별 아이콘 & 색상
const SPORT_CONFIG: Record<string, { icon: string; color: string }> = {
  swimming: { icon: '🏊', color: 'from-blue-400 to-cyan-400' },
  tennis: { icon: '🎾', color: 'from-green-400 to-emerald-400' },
  golf: { icon: '⛳', color: 'from-emerald-400 to-teal-400' },
  yoga: { icon: '🧘', color: 'from-purple-400 to-pink-400' },
  pilates: { icon: '🤸', color: 'from-pink-400 to-rose-400' },
  fitness: { icon: '💪', color: 'from-orange-400 to-red-400' },
  other: { icon: '🏃', color: 'from-gray-400 to-gray-500' },
};

// 난이도별 색상
const DIFFICULTY_COLORS: Record<string, string> = {
  beginner: 'bg-green-100 text-green-700',
  elementary: 'bg-blue-100 text-blue-700',
  intermediate: 'bg-yellow-100 text-yellow-700',
  advanced: 'bg-red-100 text-red-700',
};

export default function LessonsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [lessons, setLessons] = useState<Lesson[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [showMobileFilter, setShowMobileFilter] = useState(false);
  
  // URL 쿼리 파라미터로부터 초기 필터 설정
  const [filters, setFilters] = useState<{
    sport_type?: string;
    target_audience?: string;
    difficulty?: string;
  }>(() => {
    const initialFilters: {
      sport_type?: string;
      target_audience?: string;
      difficulty?: string;
    } = {};
    const sport = searchParams.get('sport');
    const target = searchParams.get('target');
    const difficulty = searchParams.get('difficulty');
    if (sport) initialFilters.sport_type = sport;
    if (target) initialFilters.target_audience = target;
    if (difficulty) initialFilters.difficulty = difficulty;
    return initialFilters;
  });

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
        page_size: 9,
      };

      if (filters.sport_type) params.sport_type = filters.sport_type;
      if (filters.target_audience) params.target_audience = filters.target_audience;
      if (filters.difficulty) params.difficulty = filters.difficulty;

      const res = await lessonApi.getPublished(params);
      setLessons(res.data.items);
      setTotalPages(res.data.total_pages);
      setTotal(res.data.total);
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
    setPage(1);

    const urlKey = key === 'sport_type' ? 'sport' : key === 'target_audience' ? 'target' : 'difficulty';
    if (value === '') {
      searchParams.delete(urlKey);
    } else {
      searchParams.set(urlKey, value);
    }
    setSearchParams(searchParams);
  };

  const clearFilters = () => {
    setFilters({});
    setPage(1);
    setSearchParams({});
  };

  const hasFilters = Object.keys(filters).length > 0;
  const filterCount = Object.keys(filters).length;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* 페이지 헤더 */}
      <div className="bg-white border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <h1 className="text-2xl font-bold text-gray-900">강습 둘러보기</h1>
          <p className="text-gray-500 mt-1">
            {total > 0 ? `총 ${total}개의 강습` : '강습을 찾아보세요'}
          </p>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="flex gap-8">
          {/* 왼쪽 사이드바 필터 (데스크탑) */}
          <aside className="hidden lg:block w-64 flex-shrink-0">
            <div className="sticky top-24">
              <FilterSidebar
                filters={filters}
                onFilterChange={handleFilterChange}
                onClearFilters={clearFilters}
                hasFilters={hasFilters}
              />
            </div>
          </aside>

          {/* 메인 콘텐츠 */}
          <main className="flex-1 min-w-0">
            {/* 모바일 필터 버튼 */}
            <div className="lg:hidden mb-4">
              <button
                onClick={() => setShowMobileFilter(true)}
                className="w-full flex items-center justify-center gap-2 bg-white border border-gray-200 rounded-xl px-4 py-3 text-gray-700 hover:bg-gray-50 transition"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
                </svg>
                <span>필터</span>
                {filterCount > 0 && (
                  <span className="bg-blue-600 text-white text-xs px-2 py-0.5 rounded-full">
                    {filterCount}
                  </span>
                )}
              </button>
            </div>

            {/* 활성 필터 태그 */}
            {hasFilters && (
              <div className="flex flex-wrap items-center gap-2 mb-4">
                <span className="text-sm text-gray-500">적용된 필터:</span>
                {filters.sport_type && (
                  <FilterTag
                    label={`${SPORT_CONFIG[filters.sport_type]?.icon || ''} ${SPORT_LABELS[filters.sport_type]}`}
                    onRemove={() => handleFilterChange('sport_type', '')}
                  />
                )}
                {filters.target_audience && (
                  <FilterTag
                    label={TARGET_LABELS[filters.target_audience]}
                    onRemove={() => handleFilterChange('target_audience', '')}
                  />
                )}
                {filters.difficulty && (
                  <FilterTag
                    label={DIFFICULTY_LABELS[filters.difficulty]}
                    onRemove={() => handleFilterChange('difficulty', '')}
                  />
                )}
                <button
                  onClick={clearFilters}
                  className="text-sm text-gray-500 hover:text-red-500 ml-2"
                >
                  전체 해제
                </button>
              </div>
            )}

            {/* 결과 */}
            {loading ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-5">
                {[...Array(6)].map((_, i) => (
                  <SkeletonCard key={i} />
                ))}
              </div>
            ) : lessons.length === 0 ? (
              <EmptyState hasFilters={hasFilters} onClearFilters={clearFilters} />
            ) : (
              <>
                <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-5">
                  {lessons.map((lesson) => (
                    <LessonCard key={lesson.id} lesson={lesson} />
                  ))}
                </div>

                {totalPages > 1 && (
                  <div className="mt-10">
                    <Pagination
                      page={page}
                      totalPages={totalPages}
                      onPageChange={setPage}
                    />
                  </div>
                )}
              </>
            )}
          </main>
        </div>
      </div>

      {/* 모바일 필터 모달 */}
      {showMobileFilter && (
        <div className="fixed inset-0 bg-black/50 z-50 lg:hidden">
          <div className="absolute right-0 top-0 bottom-0 w-80 max-w-full bg-white shadow-xl overflow-y-auto">
            <div className="flex items-center justify-between p-4 border-b sticky top-0 bg-white">
              <h2 className="font-bold text-lg">필터</h2>
              <button
                onClick={() => setShowMobileFilter(false)}
                className="p-2 hover:bg-gray-100 rounded-lg"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="p-4">
              <FilterSidebar
                filters={filters}
                onFilterChange={(key, value) => {
                  handleFilterChange(key, value);
                }}
                onClearFilters={clearFilters}
                hasFilters={hasFilters}
              />
            </div>
            <div className="p-4 border-t sticky bottom-0 bg-white">
              <button
                onClick={() => setShowMobileFilter(false)}
                className="w-full bg-blue-600 text-white py-3 rounded-xl font-medium hover:bg-blue-700 transition"
              >
                {total}개 강습 보기
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// 필터 사이드바
function FilterSidebar({
  filters,
  onFilterChange,
  onClearFilters,
  hasFilters,
}: {
  filters: { sport_type?: string; target_audience?: string; difficulty?: string };
  onFilterChange: (key: 'sport_type' | 'target_audience' | 'difficulty', value: string) => void;
  onClearFilters: () => void;
  hasFilters: boolean;
}) {
  return (
    <div className="space-y-6">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <h3 className="font-bold text-gray-900">필터</h3>
        {hasFilters && (
          <button
            onClick={onClearFilters}
            className="text-sm text-blue-600 hover:text-blue-700"
          >
            초기화
          </button>
        )}
      </div>

      {/* 종목 필터 */}
      <div>
        <h4 className="font-medium text-gray-900 mb-3">종목</h4>
        <div className="space-y-2">
          <FilterOption
            selected={!filters.sport_type}
            onClick={() => onFilterChange('sport_type', '')}
            label="전체"
          />
          {Object.entries(SPORT_LABELS).map(([value, label]) => (
            <FilterOption
              key={value}
              selected={filters.sport_type === value}
              onClick={() => onFilterChange('sport_type', value)}
              label={`${SPORT_CONFIG[value]?.icon || ''} ${label}`}
            />
          ))}
        </div>
      </div>

      {/* 대상 필터 */}
      <div>
        <h4 className="font-medium text-gray-900 mb-3">대상</h4>
        <div className="space-y-2">
          <FilterOption
            selected={!filters.target_audience}
            onClick={() => onFilterChange('target_audience', '')}
            label="전체"
          />
          {Object.entries(TARGET_LABELS).map(([value, label]) => (
            <FilterOption
              key={value}
              selected={filters.target_audience === value}
              onClick={() => onFilterChange('target_audience', value)}
              label={label}
            />
          ))}
        </div>
      </div>

      {/* 난이도 필터 */}
      <div>
        <h4 className="font-medium text-gray-900 mb-3">난이도</h4>
        <div className="space-y-2">
          <FilterOption
            selected={!filters.difficulty}
            onClick={() => onFilterChange('difficulty', '')}
            label="전체"
          />
          {Object.entries(DIFFICULTY_LABELS).map(([value, label]) => (
            <FilterOption
              key={value}
              selected={filters.difficulty === value}
              onClick={() => onFilterChange('difficulty', value)}
              label={label}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

// 필터 옵션
function FilterOption({
  selected,
  onClick,
  label,
}: {
  selected: boolean;
  onClick: () => void;
  label: string;
}) {
  return (
    <button
      onClick={onClick}
      className={`w-full text-left px-3 py-2 rounded-lg text-sm transition ${
        selected
          ? 'bg-blue-50 text-blue-700 font-medium'
          : 'text-gray-600 hover:bg-gray-100'
      }`}
    >
      {label}
    </button>
  );
}

// 필터 태그
function FilterTag({ label, onRemove }: { label: string; onRemove: () => void }) {
  return (
    <span className="inline-flex items-center gap-1 bg-blue-100 text-blue-700 px-3 py-1 rounded-full text-sm">
      {label}
      <button onClick={onRemove} className="hover:text-blue-900">
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </span>
  );
}

// 스켈레톤 카드
function SkeletonCard() {
  return (
    <div className="bg-white rounded-xl shadow-sm overflow-hidden animate-pulse">
      <div className="aspect-video bg-gray-200" />
      <div className="p-4">
        <div className="h-5 bg-gray-200 rounded mb-2 w-3/4" />
        <div className="h-4 bg-gray-200 rounded w-1/2" />
      </div>
    </div>
  );
}

// 빈 상태
function EmptyState({ hasFilters, onClearFilters }: { hasFilters: boolean; onClearFilters: () => void }) {
  return (
    <div className="text-center py-16">
      <div className="text-5xl mb-4">🔍</div>
      <h3 className="text-lg font-bold text-gray-900 mb-2">
        {hasFilters ? '조건에 맞는 강습이 없습니다' : '등록된 강습이 없습니다'}
      </h3>
      <p className="text-gray-500 mb-6">
        {hasFilters ? '다른 필터 조건으로 검색해보세요' : '곧 새로운 강습이 등록됩니다'}
      </p>
      {hasFilters && (
        <button
          onClick={onClearFilters}
          className="inline-flex items-center px-5 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
        >
          필터 초기화
        </button>
      )}
    </div>
  );
}

// 강습 카드
function LessonCard({ lesson }: { lesson: any }) {
  const thumbnailUrl = lesson.active_content?.thumbnail_url
    ? `${API_BASE}${lesson.active_content.thumbnail_url}`
    : null;

  const sportConfig = SPORT_CONFIG[lesson.sport_type] || SPORT_CONFIG.other;
  const difficultyColor = DIFFICULTY_COLORS[lesson.difficulty] || 'bg-gray-100 text-gray-700';

  return (
    <Link
      to={`/lessons/${lesson.id}`}
      className="group bg-white rounded-xl shadow-sm overflow-hidden hover:shadow-md transition-shadow"
    >
      {/* 썸네일 */}
      <div className="aspect-video relative overflow-hidden bg-gray-100">
        {thumbnailUrl ? (
          <img
            src={thumbnailUrl}
            alt={lesson.title}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
          />
        ) : (
          <div className={`w-full h-full flex items-center justify-center bg-gradient-to-br ${sportConfig.color}`}>
            <span className="text-5xl opacity-80">{sportConfig.icon}</span>
          </div>
        )}
        
        {/* 종목 뱃지 */}
        <span className="absolute top-2.5 left-2.5 bg-white/95 text-gray-800 text-xs px-2.5 py-1 rounded-full font-medium">
          {sportConfig.icon} {SPORT_LABELS[lesson.sport_type]}
        </span>
      </div>

      {/* 정보 */}
      <div className="p-4">
        <h3 className="font-bold text-gray-900 mb-2 line-clamp-2 group-hover:text-blue-600 transition-colors">
          {lesson.title}
        </h3>
        <div className="flex items-center gap-2 text-sm">
          <span className={`px-2 py-0.5 rounded text-xs font-medium ${difficultyColor}`}>
            {DIFFICULTY_LABELS[lesson.difficulty]}
          </span>
          <span className="text-gray-400">·</span>
          <span className="text-gray-500">
            {TARGET_LABELS[lesson.target_audience]}
          </span>
        </div>
      </div>
    </Link>
  );
}

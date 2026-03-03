import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { Lesson } from '../types';
import { lessonApi } from '../services/api';
import Pagination from '../components/common/Pagination';
import { DIFFICULTY_LABELS, SPORT_LABELS, TARGET_LABELS } from '../constants/labels';
import { getImageUrl } from '../utils/image';

// Material Symbols 아이콘 매핑
const SPORT_ICONS: Record<string, string> = {
  swimming: 'pool',
  tennis: 'sports_tennis',
  golf: 'sports_golf',
  yoga: 'self_improvement',
  pilates: 'accessibility_new',
  fitness: 'fitness_center',
  other: 'sports',
};

// 난이도별 스타일
const DIFFICULTY_STYLES: Record<string, { bg: string; text: string; border: string }> = {
  beginner: { bg: 'bg-green-500/20', text: 'text-green-400', border: 'border-green-500/30' },
  elementary: { bg: 'bg-blue-500/20', text: 'text-blue-400', border: 'border-blue-500/30' },
  intermediate: { bg: 'bg-yellow-500/20', text: 'text-yellow-400', border: 'border-yellow-500/30' },
  advanced: { bg: 'bg-orange-500/20', text: 'text-orange-400', border: 'border-orange-500/30' },
};

export default function LessonsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [lessons, setLessons] = useState<Lesson[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [showMobileFilter, setShowMobileFilter] = useState(false);
  
  const [filters, setFilters] = useState<{
    sport_type?: string;
    target_audience?: string;
    difficulty?: string;
    search?: string;
  }>(() => {
    const initialFilters: {
      sport_type?: string;
      target_audience?: string;
      difficulty?: string;
      search?: string;
    } = {};
    const sport = searchParams.get('sport');
    const target = searchParams.get('target');
    const difficulty = searchParams.get('difficulty');
    const search = searchParams.get('search');
    if (sport) initialFilters.sport_type = sport;
    if (target) initialFilters.target_audience = target;
    if (difficulty) initialFilters.difficulty = difficulty;
    if (search) initialFilters.search = search;
    return initialFilters;
  });
  
  const [searchInput, setSearchInput] = useState(searchParams.get('search') || '');

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
        search?: string;
      } = {
        page,
        page_size: 9,
      };

      if (filters.sport_type) params.sport_type = filters.sport_type;
      if (filters.target_audience) params.target_audience = filters.target_audience;
      if (filters.difficulty) params.difficulty = filters.difficulty;
      if (filters.search) params.search = filters.search;

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

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchInput.trim()) {
      setFilters((prev) => ({ ...prev, search: searchInput.trim() }));
      searchParams.set('search', searchInput.trim());
    } else {
      setFilters((prev) => {
        const newFilters = { ...prev };
        delete newFilters.search;
        return newFilters;
      });
      searchParams.delete('search');
    }
    setSearchParams(searchParams);
    setPage(1);
  };

  const clearSearch = () => {
    setSearchInput('');
    setFilters((prev) => {
      const newFilters = { ...prev };
      delete newFilters.search;
      return newFilters;
    });
    searchParams.delete('search');
    setSearchParams(searchParams);
    setPage(1);
  };

  const clearFilters = () => {
    setFilters({});
    setSearchInput('');
    setPage(1);
    setSearchParams({});
  };

  const hasFilters = Object.keys(filters).length > 0;
  const filterCount = Object.keys(filters).length;

  return (
    <div className="min-h-screen bg-background-light">
      {/* Page Header */}
      <div className="bg-navy border-b border-slate-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {/* Breadcrumbs */}
          <nav className="flex items-center gap-2 mb-4 text-sm">
            <Link to="/" className="text-slate-400 hover:text-primary transition-colors font-medium">홈</Link>
            <span className="material-symbols-outlined text-slate-600 text-base">chevron_right</span>
            <span className="text-white font-medium">강습 둘러보기</span>
          </nav>
          
          <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
            <div>
              <h1 className="text-3xl lg:text-4xl font-bold text-white tracking-tight mb-2">강습 둘러보기</h1>
              <p className="text-slate-400">다양한 종목의 스포츠 강습을 둘러보세요.</p>
            </div>
            {total > 0 && (
              <div className="text-primary font-semibold bg-primary/10 px-4 py-2 rounded-lg border border-primary/20">
                {total}개 강습
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex flex-col lg:flex-row gap-8">
          {/* Sidebar Filters (Desktop) */}
          <aside className="hidden lg:block w-72 flex-shrink-0 space-y-8">
            <FilterSidebar
              filters={filters}
              onFilterChange={handleFilterChange}
              onClearFilters={clearFilters}
              hasFilters={hasFilters}
              searchInput={searchInput}
              setSearchInput={setSearchInput}
              onSearch={handleSearch}
            />
          </aside>

          {/* Main Content */}
          <main className="flex-1 min-w-0">
            {/* Mobile Filter Button */}
            <div className="lg:hidden mb-4">
              <button
                onClick={() => setShowMobileFilter(true)}
                className="w-full flex items-center justify-center gap-2 bg-white border border-slate-200 rounded-xl px-4 py-3 text-slate-700 hover:bg-slate-50 transition"
              >
                <span className="material-symbols-outlined">tune</span>
                <span>필터</span>
                {filterCount > 0 && (
                  <span className="bg-primary text-white text-xs px-2 py-0.5 rounded-full">
                    {filterCount}
                  </span>
                )}
              </button>
            </div>

            {/* Active Filters & Sort */}
            {hasFilters && (
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
                <div className="flex flex-wrap items-center gap-2">
                  {filters.search && (
                    <FilterTag
                      label={`"${filters.search}"`}
                      isPrimary
                      onRemove={clearSearch}
                    />
                  )}
                  {filters.sport_type && (
                    <FilterTag
                      label={SPORT_LABELS[filters.sport_type]}
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
                    className="text-sm text-slate-500 hover:text-primary underline ml-2"
                  >
                    전체 해제
                  </button>
                </div>
              </div>
            )}

            {/* Results */}
            {loading ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {[...Array(6)].map((_, i) => (
                  <SkeletonCard key={i} />
                ))}
              </div>
            ) : lessons.length === 0 ? (
              <EmptyState hasFilters={hasFilters} onClearFilters={clearFilters} />
            ) : (
              <>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {lessons.map((lesson) => (
                    <LessonCard key={lesson.id} lesson={lesson} />
                  ))}
                </div>

                {totalPages > 1 && (
                  <div className="mt-12">
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

      {/* Mobile Filter Modal */}
      {showMobileFilter && (
        <div className="fixed inset-0 bg-black/50 z-50 lg:hidden">
          <div className="absolute right-0 top-0 bottom-0 w-80 max-w-full bg-navy shadow-xl overflow-y-auto">
            <div className="flex items-center justify-between p-4 border-b border-slate-800 sticky top-0 bg-navy">
              <h2 className="font-bold text-lg text-white">필터</h2>
              <button
                onClick={() => setShowMobileFilter(false)}
                className="p-2 hover:bg-slate-800 rounded-lg text-slate-400"
              >
                <span className="material-symbols-outlined">close</span>
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
                searchInput={searchInput}
                setSearchInput={setSearchInput}
                onSearch={handleSearch}
              />
            </div>
            <div className="p-4 border-t border-slate-800 sticky bottom-0 bg-navy">
              <button
                onClick={() => setShowMobileFilter(false)}
                className="w-full bg-primary text-white py-3 rounded-xl font-medium hover:bg-blue-600 transition"
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

// Filter Sidebar
function FilterSidebar({
  filters,
  onFilterChange,
  onClearFilters,
  hasFilters,
  searchInput,
  setSearchInput,
  onSearch,
}: {
  filters: { sport_type?: string; target_audience?: string; difficulty?: string; search?: string };
  onFilterChange: (key: 'sport_type' | 'target_audience' | 'difficulty', value: string) => void;
  onClearFilters: () => void;
  hasFilters: boolean;
  searchInput?: string;
  setSearchInput?: (value: string) => void;
  onSearch?: (e: React.FormEvent) => void;
}) {
  return (
    <div className="space-y-8">
      {/* Search */}
      {onSearch && setSearchInput && (
        <form onSubmit={onSearch}>
          <div className="bg-white border border-slate-200 p-1 rounded-xl">
            <div className="relative flex items-center h-12">
              <span className="material-symbols-outlined absolute left-4 text-slate-400">search</span>
              <input
                type="text"
                placeholder="강습 검색..."
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                className="w-full h-full bg-transparent border-none focus:ring-0 text-slate-900 pl-12 pr-4 placeholder-slate-400 rounded-lg"
              />
            </div>
          </div>
        </form>
      )}

      {/* Sport Type Filter */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-slate-900 font-bold text-lg">종목</h3>
        </div>
        <div className="space-y-2">
          <FilterCheckbox
            checked={!filters.sport_type}
            onChange={() => onFilterChange('sport_type', '')}
            label="전체"
          />
          {Object.entries(SPORT_LABELS).map(([value, label]) => (
            <FilterCheckbox
              key={value}
              checked={filters.sport_type === value}
              onChange={() => onFilterChange('sport_type', filters.sport_type === value ? '' : value)}
              label={label}
              icon={SPORT_ICONS[value]}
            />
          ))}
        </div>
      </div>

      <div className="h-px w-full bg-slate-200"></div>

      {/* Target Audience Filter */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-slate-900 font-bold text-lg">대상</h3>
        </div>
        <div className="space-y-2">
          <FilterCheckbox
            checked={!filters.target_audience}
            onChange={() => onFilterChange('target_audience', '')}
            label="전체"
          />
          {Object.entries(TARGET_LABELS).map(([value, label]) => (
            <FilterCheckbox
              key={value}
              checked={filters.target_audience === value}
              onChange={() => onFilterChange('target_audience', filters.target_audience === value ? '' : value)}
              label={label}
            />
          ))}
        </div>
      </div>

      <div className="h-px w-full bg-slate-200"></div>

      {/* Difficulty Filter */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-slate-900 font-bold text-lg">난이도</h3>
        </div>
        <div className="space-y-2">
          <FilterCheckbox
            checked={!filters.difficulty}
            onChange={() => onFilterChange('difficulty', '')}
            label="전체"
          />
          {Object.entries(DIFFICULTY_LABELS).map(([value, label]) => (
            <FilterCheckbox
              key={value}
              checked={filters.difficulty === value}
              onChange={() => onFilterChange('difficulty', filters.difficulty === value ? '' : value)}
              label={label}
            />
          ))}
        </div>
      </div>

      {hasFilters && (
        <button
          onClick={onClearFilters}
          className="w-full py-3 text-sm font-bold text-slate-500 hover:text-slate-700 border border-slate-200 hover:border-slate-300 rounded-xl transition-all"
        >
          필터 초기화
        </button>
      )}
    </div>
  );
}

// Filter Checkbox
function FilterCheckbox({
  checked,
  onChange,
  label,
  icon,
}: {
  checked: boolean;
  onChange: () => void;
  label: string;
  icon?: string;
}) {
  return (
    <label className="flex items-center gap-3 cursor-pointer group">
      <input
        type="checkbox"
        checked={checked}
        onChange={onChange}
        className="w-5 h-5 rounded border-slate-300 text-primary focus:ring-offset-0 focus:ring-0 focus:border-primary transition-colors"
      />
      {icon && <span className="material-symbols-outlined text-slate-400 group-hover:text-primary text-[20px]">{icon}</span>}
      <span className="text-slate-600 group-hover:text-slate-900 transition-colors">{label}</span>
    </label>
  );
}

// Filter Tag
function FilterTag({ label, onRemove, isPrimary }: { label: string; onRemove: () => void; isPrimary?: boolean }) {
  return (
    <span className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium ${
      isPrimary 
        ? 'bg-primary/20 border border-primary/30 text-primary' 
        : 'bg-slate-100 border border-slate-200 text-slate-700'
    }`}>
      {label}
      <button onClick={onRemove} className="hover:opacity-70 transition-opacity flex items-center">
        <span className="material-symbols-outlined text-base">close</span>
      </button>
    </span>
  );
}

// Skeleton Card
function SkeletonCard() {
  return (
    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden animate-pulse">
      <div className="aspect-video bg-slate-200" />
      <div className="p-5">
        <div className="h-4 bg-slate-200 rounded mb-3 w-1/3" />
        <div className="h-5 bg-slate-200 rounded mb-2 w-3/4" />
        <div className="h-4 bg-slate-200 rounded w-1/2" />
      </div>
    </div>
  );
}

// Empty State
function EmptyState({ hasFilters, onClearFilters }: { hasFilters: boolean; onClearFilters: () => void }) {
  return (
    <div className="text-center py-16 bg-white rounded-2xl border border-slate-200">
      <span className="material-symbols-outlined text-6xl text-slate-300 mb-4">search_off</span>
      <h3 className="text-lg font-bold text-slate-900 mb-2">
        {hasFilters ? '조건에 맞는 강습이 없습니다' : '등록된 강습이 없습니다'}
      </h3>
      <p className="text-slate-500 mb-6">
        {hasFilters ? '다른 필터 조건으로 검색해보세요' : '곧 새로운 강습이 등록됩니다'}
      </p>
      {hasFilters && (
        <button
          onClick={onClearFilters}
          className="inline-flex items-center px-5 py-2.5 bg-primary text-white rounded-lg hover:bg-blue-600 transition"
        >
          필터 초기화
        </button>
      )}
    </div>
  );
}

// Lesson Card
function LessonCard({ lesson }: { lesson: any }) {
  const thumbnailUrl = getImageUrl(lesson.active_content?.thumbnail_url);

  const sportIcon = SPORT_ICONS[lesson.sport_type] || 'sports';
  const difficultyStyle = DIFFICULTY_STYLES[lesson.difficulty] || { bg: 'bg-slate-500/20', text: 'text-slate-400', border: 'border-slate-500/30' };

  return (
    <Link
      to={`/lessons/${lesson.id}`}
      className="group bg-white rounded-xl overflow-hidden border border-slate-200 hover:border-primary hover:shadow-xl hover:-translate-y-1 transition-all duration-300"
    >
      {/* Thumbnail */}
      <div className="relative aspect-video overflow-hidden">
        {thumbnailUrl ? (
          <img
            src={thumbnailUrl}
            alt={lesson.title}
            className="object-cover w-full h-full group-hover:scale-105 transition-transform duration-500"
          />
        ) : (
          <div className="w-full h-full bg-gradient-to-br from-slate-100 to-slate-200 flex items-center justify-center">
            <span className="material-symbols-outlined text-5xl text-slate-400">{sportIcon}</span>
          </div>
        )}
        <div className="absolute inset-0 bg-gradient-to-t from-black/40 to-transparent opacity-60"></div>
        
        {/* Sport Badge */}
        <div className="absolute top-3 left-3 bg-black/50 backdrop-blur-md text-white text-xs font-bold px-3 py-1 rounded-full border border-white/10 flex items-center gap-1">
          <span className="material-symbols-outlined text-sm">{sportIcon}</span>
          {SPORT_LABELS[lesson.sport_type]}
        </div>
      </div>

      {/* Info */}
      <div className="p-5">
        <div className="flex items-center gap-2 mb-3">
          <span className={`${difficultyStyle.bg} ${difficultyStyle.text} text-xs px-2 py-1 rounded-md font-medium border ${difficultyStyle.border}`}>
            {DIFFICULTY_LABELS[lesson.difficulty]}
          </span>
          <span className="text-slate-400 text-xs">•</span>
          <span className="text-slate-500 text-xs font-medium">{TARGET_LABELS[lesson.target_audience]}</span>
        </div>
        
        <h3 className="text-slate-900 text-lg font-bold leading-tight mb-2 group-hover:text-primary transition-colors line-clamp-2">
          {lesson.title}
        </h3>
        
        {lesson.active_content?.introduction && (
          <p className="text-slate-500 text-sm line-clamp-2 mb-4">
            {lesson.active_content.introduction}
          </p>
        )}

        <div className="flex items-center justify-between pt-4 border-t border-slate-100">
          <div className="flex items-center gap-2 text-slate-400 text-sm">
            <span className="material-symbols-outlined text-lg">person</span>
            {lesson.instructor_name || '강사 미정'}
          </div>
        </div>
      </div>
    </Link>
  );
}

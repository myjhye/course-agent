import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { adminLessonApi } from '../../services/api';
import type { Lesson } from '../../types';
import Pagination from '../../components/common/Pagination';
import { SPORT_LABELS, DIFFICULTY_LABELS, STATUS_LABELS } from '../../constants/labels';
import { getImageUrl } from '../../utils/image';

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

export default function LessonsPage() {
  const [lessons, setLessons] = useState<Lesson[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);

  useEffect(() => {
    loadLessons();
  }, [page]);

  const loadLessons = async () => {
    setLoading(true);
    try {
      const res = await adminLessonApi.getAll({ page, page_size: 10 });
      setLessons(res.data.items);
      setTotalPages(res.data.total_pages);
      setTotal(res.data.total);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'published':
        return 'bg-emerald-100 text-emerald-700 ring-1 ring-inset ring-emerald-600/20';
      case 'draft':
        return 'bg-amber-100 text-amber-700 ring-1 ring-inset ring-amber-600/20';
      default:
        return 'bg-slate-100 text-slate-600 ring-1 ring-inset ring-slate-500/20';
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-bold text-slate-900 tracking-tight">강습 관리</h1>
            <span className="rounded-full bg-slate-200 px-2.5 py-0.5 text-xs font-semibold text-slate-600">
              총 {total}개
            </span>
          </div>
          <p className="text-sm text-slate-500">등록된 스포츠 강습 콘텐츠를 관리하고 상태를 변경합니다.</p>
        </div>
        <Link
          to="/admin/lessons/new"
          className="flex items-center gap-2 rounded-xl bg-primary px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-primary/30 hover:bg-blue-600 hover:-translate-y-0.5 transition-all duration-200"
        >
          <span className="material-symbols-outlined text-[18px]">add</span>
          새 강습 등록
        </Link>
      </div>

      {/* Content */}
      {loading ? (
        <div className="flex flex-col items-center justify-center py-16 bg-white rounded-xl border border-slate-200">
          <div className="w-10 h-10 border-4 border-primary border-t-transparent rounded-full animate-spin mb-4" />
          <p className="text-slate-500">강습 목록을 불러오는 중...</p>
        </div>
      ) : lessons.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 bg-white rounded-xl border border-slate-200">
          <span className="material-symbols-outlined text-5xl text-slate-300 mb-4">school</span>
          <p className="text-slate-500 mb-4">등록된 강습이 없습니다.</p>
          <Link
            to="/admin/lessons/new"
            className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-blue-600 transition-colors"
          >
            <span className="material-symbols-outlined text-[18px]">add</span>
            첫 강습 등록하기
          </Link>
        </div>
      ) : (
        <>
          {/* Table Container */}
          <div className="flex flex-col overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
            {/* Table */}
            <div className="overflow-x-auto">
              <table className="w-full min-w-[800px] text-left border-collapse">
                <thead>
                  <tr className="bg-slate-50/80 border-b border-slate-200">
                    <th className="px-6 py-4 text-xs font-semibold uppercase tracking-wider text-slate-500 w-[120px]">
                      썸네일
                    </th>
                    <th className="px-6 py-4 text-xs font-semibold uppercase tracking-wider text-slate-500 min-w-[200px]">
                      강습명
                    </th>
                    <th className="px-6 py-4 text-xs font-semibold uppercase tracking-wider text-slate-500 w-[100px]">
                      종목
                    </th>
                    <th className="px-6 py-4 text-xs font-semibold uppercase tracking-wider text-slate-500 w-[100px]">
                      난이도
                    </th>
                    <th className="px-6 py-4 text-xs font-semibold uppercase tracking-wider text-slate-500 w-[120px]">
                      상태
                    </th>
                    <th className="px-6 py-4 text-xs font-semibold uppercase tracking-wider text-slate-500 w-[140px] text-right">
                      등록일
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {lessons.map((lesson) => {
                    const thumbnailUrl = getImageUrl(lesson.active_content?.thumbnail_url);
                    const sportIcon = SPORT_ICONS[lesson.sport_type] || 'sports';

                    return (
                      <tr key={lesson.id} className="group hover:bg-slate-50 transition-colors">
                        {/* Thumbnail */}
                        <td className="px-6 py-4">
                          <div className="h-12 w-20 overflow-hidden rounded-lg bg-slate-100 relative shadow-sm border border-slate-100">
                            {thumbnailUrl ? (
                              <img
                                src={thumbnailUrl}
                                alt={lesson.title}
                                className="h-full w-full object-cover"
                              />
                            ) : (
                              <div className="h-full w-full flex items-center justify-center">
                                <span className="material-symbols-outlined text-2xl text-slate-400">
                                  {sportIcon}
                                </span>
                              </div>
                            )}
                          </div>
                        </td>

                        {/* Title */}
                        <td className="px-6 py-4">
                          <Link
                            to={`/admin/lessons/${lesson.id}`}
                            className="text-sm font-semibold text-primary hover:underline hover:text-blue-700 decoration-2 underline-offset-2"
                          >
                            {lesson.title}
                          </Link>
                          <p className="mt-0.5 text-xs text-slate-400">ID: {lesson.id}</p>
                        </td>

                        {/* Sport Type */}
                        <td className="px-6 py-4">
                          <span className="inline-flex items-center text-sm font-medium text-slate-700">
                            {SPORT_LABELS[lesson.sport_type] || lesson.sport_type}
                          </span>
                        </td>

                        {/* Difficulty */}
                        <td className="px-6 py-4">
                          <span className="text-sm text-slate-600">
                            {DIFFICULTY_LABELS[lesson.difficulty] || lesson.difficulty}
                          </span>
                        </td>

                        {/* Status */}
                        <td className="px-6 py-4">
                          <span className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold ${getStatusBadge(lesson.status)}`}>
                            {STATUS_LABELS[lesson.status]}
                          </span>
                        </td>

                        {/* Created Date */}
                        <td className="px-6 py-4 text-right whitespace-nowrap">
                          <span className="text-sm text-slate-500 font-mono">
                            {new Date(lesson.created_at).toLocaleDateString('ko-KR')}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* Pagination Footer */}
            <div className="flex items-center justify-center border-t border-slate-200 bg-white px-6 py-4">
              <Pagination
                page={page}
                totalPages={totalPages}
                onPageChange={setPage}
              />
            </div>
          </div>
        </>
      )}
    </div>
  );
}

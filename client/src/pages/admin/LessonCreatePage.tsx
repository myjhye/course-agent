import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { adminLessonApi, instructorApi } from '../../services/api';
import type { Instructor, LessonCreateRequest, SportType, TargetAudience, Difficulty } from '../../types';
import { SPORT_LABELS, TARGET_LABELS, DIFFICULTY_LABELS } from '../../constants/labels';

const SPORT_OPTIONS: { value: SportType; label: string }[] = Object.entries(SPORT_LABELS).map(([value, label]) => ({
  value: value as SportType,
  label,
}));

const TARGET_OPTIONS: { value: TargetAudience; label: string }[] = Object.entries(TARGET_LABELS).map(([value, label]) => ({
  value: value as TargetAudience,
  label,
}));

const DIFFICULTY_OPTIONS: { value: Difficulty; label: string }[] = Object.entries(DIFFICULTY_LABELS).map(([value, label]) => ({
  value: value as Difficulty,
  label,
}));

export default function LessonCreatePage() {
  const navigate = useNavigate();
  const [instructors, setInstructors] = useState<Instructor[]>([]);
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState<LessonCreateRequest>({
    title: '',
    sport_type: 'swimming',
    target_audience: 'adult',
    difficulty: 'beginner',
    instructor_id: undefined,
  });

  useEffect(() => {
    instructorApi.getAll().then((res) => setInstructors(res.data));
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.title.trim()) {
      alert('강습명을 입력해주세요.');
      return;
    }

    setLoading(true);
    try {
      const res = await adminLessonApi.create(form);
      navigate(`/admin/lessons/${res.data.id}`);
    } catch (err) {
      console.error(err);
      alert('강습 등록에 실패했습니다.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link
          to="/admin/lessons"
          className="p-2 -ml-2 rounded-full hover:bg-slate-200 transition-colors text-slate-600"
        >
          <span className="material-symbols-outlined">arrow_back</span>
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-slate-900">새 강습 등록</h1>
          <p className="text-sm text-slate-500">새로운 강습 정보를 입력하고 등록해주세요.</p>
        </div>
      </div>

      {/* Form Card */}
      <div className="max-w-2xl">
        <form
          onSubmit={handleSubmit}
          className="bg-white rounded-xl shadow-sm border border-slate-100 p-8 flex flex-col gap-8"
        >
          {/* Section: Basic Info */}
          <div className="flex flex-col gap-6">
            {/* Title */}
            <label className="flex flex-col gap-2">
              <span className="text-slate-700 text-sm font-semibold">
                강습명 <span className="text-red-500">*</span>
              </span>
              <input
                type="text"
                value={form.title}
                onChange={(e) => setForm({ ...form, title: e.target.value })}
                placeholder="예: 성인 수영 입문반"
                className="w-full h-12 px-4 rounded-lg border border-slate-300 bg-white text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all"
              />
            </label>

            {/* Sport & Target */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <label className="flex flex-col gap-2">
                <span className="text-slate-700 text-sm font-semibold">
                  종목 <span className="text-red-500">*</span>
                </span>
                <div className="relative">
                  <select
                    value={form.sport_type}
                    onChange={(e) => setForm({ ...form, sport_type: e.target.value as SportType })}
                    className="w-full h-12 px-4 pr-10 rounded-lg border border-slate-300 bg-white text-slate-900 appearance-none focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all"
                  >
                    {SPORT_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                  <div className="absolute inset-y-0 right-0 flex items-center px-3 pointer-events-none text-slate-500">
                    <span className="material-symbols-outlined">expand_more</span>
                  </div>
                </div>
              </label>

              <label className="flex flex-col gap-2">
                <span className="text-slate-700 text-sm font-semibold">
                  대상 <span className="text-red-500">*</span>
                </span>
                <div className="relative">
                  <select
                    value={form.target_audience}
                    onChange={(e) => setForm({ ...form, target_audience: e.target.value as TargetAudience })}
                    className="w-full h-12 px-4 pr-10 rounded-lg border border-slate-300 bg-white text-slate-900 appearance-none focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all"
                  >
                    {TARGET_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                  <div className="absolute inset-y-0 right-0 flex items-center px-3 pointer-events-none text-slate-500">
                    <span className="material-symbols-outlined">expand_more</span>
                  </div>
                </div>
              </label>
            </div>

            {/* Difficulty & Instructor */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <label className="flex flex-col gap-2">
                <span className="text-slate-700 text-sm font-semibold">난이도</span>
                <div className="relative">
                  <select
                    value={form.difficulty}
                    onChange={(e) => setForm({ ...form, difficulty: e.target.value as Difficulty })}
                    className="w-full h-12 px-4 pr-10 rounded-lg border border-slate-300 bg-white text-slate-900 appearance-none focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all"
                  >
                    {DIFFICULTY_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                  <div className="absolute inset-y-0 right-0 flex items-center px-3 pointer-events-none text-slate-500">
                    <span className="material-symbols-outlined">expand_more</span>
                  </div>
                </div>
              </label>

              <label className="flex flex-col gap-2">
                <span className="text-slate-700 text-sm font-semibold">강사 배정</span>
                <div className="relative">
                  <select
                    value={form.instructor_id || ''}
                    onChange={(e) =>
                      setForm({ ...form, instructor_id: e.target.value ? Number(e.target.value) : undefined })
                    }
                    className="w-full h-12 px-4 pr-10 rounded-lg border border-slate-300 bg-white text-slate-900 appearance-none focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all"
                  >
                    <option value="">강사를 선택하세요</option>
                    {instructors.map((inst) => (
                      <option key={inst.id} value={inst.id}>
                        {inst.name} ({inst.specialty})
                      </option>
                    ))}
                  </select>
                  <div className="absolute inset-y-0 right-0 flex items-center px-3 pointer-events-none text-slate-500">
                    <span className="material-symbols-outlined">person</span>
                  </div>
                </div>
              </label>
            </div>
          </div>

          {/* Divider */}
          <div className="h-px bg-slate-100 w-full" />

          {/* Action Buttons */}
          <div className="flex flex-col-reverse sm:flex-row gap-3 pt-2">
            <button
              type="button"
              onClick={() => navigate('/admin/lessons')}
              className="flex-1 h-12 px-6 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50 font-medium transition-all"
            >
              취소
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex-[2] h-12 px-6 rounded-lg bg-primary hover:bg-blue-600 text-white shadow-lg shadow-blue-500/30 font-semibold transition-all flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <>
                  <span className="material-symbols-outlined text-[20px] animate-spin">autorenew</span>
                  등록 중...
                </>
              ) : (
                <>
                  <span className="material-symbols-outlined text-[20px]">check</span>
                  강습 등록
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

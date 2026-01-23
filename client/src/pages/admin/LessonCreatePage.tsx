import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { adminLessonApi, instructorApi } from '../../services/api';
import type { Instructor, LessonCreateRequest, SportType, TargetAudience, Difficulty } from '../../types';

const SPORT_OPTIONS: { value: SportType; label: string }[] = [
  { value: 'swimming', label: '수영' },
  { value: 'tennis', label: '테니스' },
  { value: 'golf', label: '골프' },
  { value: 'fitness', label: '피트니스' },
  { value: 'yoga', label: '요가' },
  { value: 'pilates', label: '필라테스' },
  { value: 'other', label: '기타' },
];

const TARGET_OPTIONS: { value: TargetAudience; label: string }[] = [
  { value: 'adult', label: '성인' },
  { value: 'child', label: '어린이' },
  { value: 'senior', label: '시니어' },
  { value: 'all', label: '전체' },
];

const DIFFICULTY_OPTIONS: { value: Difficulty; label: string }[] = [
  { value: 'beginner', label: '입문' },
  { value: 'elementary', label: '초급' },
  { value: 'intermediate', label: '중급' },
  { value: 'advanced', label: '고급' },
];

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
    <div className="max-w-2xl">
      <h1 className="text-2xl font-bold mb-6">새 강습 등록</h1>

      <form onSubmit={handleSubmit} className="bg-white rounded-lg shadow p-6 space-y-6">
        {/* 강습명 */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            강습명 *
          </label>
          <input
            type="text"
            value={form.title}
            onChange={(e) => setForm({ ...form, title: e.target.value })}
            className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            placeholder="예: 성인 수영 입문반"
          />
        </div>

        {/* 종목 */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            종목 *
          </label>
          <select
            value={form.sport_type}
            onChange={(e) => setForm({ ...form, sport_type: e.target.value as SportType })}
            className="w-full border border-gray-300 rounded-lg px-4 py-2"
          >
            {SPORT_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        {/* 대상 */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            대상 *
          </label>
          <select
            value={form.target_audience}
            onChange={(e) => setForm({ ...form, target_audience: e.target.value as TargetAudience })}
            className="w-full border border-gray-300 rounded-lg px-4 py-2"
          >
            {TARGET_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        {/* 난이도 */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            난이도 *
          </label>
          <select
            value={form.difficulty}
            onChange={(e) => setForm({ ...form, difficulty: e.target.value as Difficulty })}
            className="w-full border border-gray-300 rounded-lg px-4 py-2"
          >
            {DIFFICULTY_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        {/* 강사 */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            강사
          </label>
          <select
            value={form.instructor_id || ''}
            onChange={(e) =>
              setForm({ ...form, instructor_id: e.target.value ? Number(e.target.value) : undefined })
            }
            className="w-full border border-gray-300 rounded-lg px-4 py-2"
          >
            <option value="">선택 안 함</option>
            {instructors.map((inst) => (
              <option key={inst.id} value={inst.id}>
                {inst.name} ({inst.specialty})
              </option>
            ))}
          </select>
        </div>

        {/* 버튼 */}
        <div className="flex gap-4">
          <button
            type="submit"
            disabled={loading}
            className="flex-1 bg-blue-600 text-white py-2 rounded-lg hover:bg-blue-700 disabled:bg-gray-400"
          >
            {loading ? '등록 중...' : '강습 등록'}
          </button>
          <button
            type="button"
            onClick={() => navigate('/admin/lessons')}
            className="px-6 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            취소
          </button>
        </div>
      </form>
    </div>
  );
}


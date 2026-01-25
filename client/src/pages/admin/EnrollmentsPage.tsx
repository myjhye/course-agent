import { useEffect, useState } from 'react';
import { adminEnrollmentApi } from '../../services/api';
import type { EnrollmentDetail, Feedback } from '../../types';
import Pagination from '../../components/common/Pagination';
import {
  ENROLLMENT_STATUS_LABELS,
  SPORT_LABELS,
  DIFFICULTY_LABELS,
} from '../../constants/labels';

// 상태별 스타일 설정
const STATUS_STYLES: Record<string, { bg: string; text: string; border: string }> = {
  enrolled: { bg: 'bg-slate-50', text: 'text-slate-700', border: 'border-slate-200' },
  in_progress: { bg: 'bg-blue-50', text: 'text-blue-700', border: 'border-blue-200' },
  completed: { bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-200' },
  cancelled: { bg: 'bg-red-50', text: 'text-red-700', border: 'border-red-200' },
};

// 필터 버튼 아이콘
const FILTER_ICONS: Record<string, string> = {
  '': 'check_circle',
  enrolled: 'how_to_reg',
  in_progress: 'play_circle',
  completed: 'verified',
  cancelled: 'cancel',
};

export default function EnrollmentsPage() {
  const [enrollments, setEnrollments] = useState<EnrollmentDetail[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  
  // 피드백 모달 상태
  const [selectedEnrollment, setSelectedEnrollment] = useState<EnrollmentDetail | null>(null);
  const [feedback, setFeedback] = useState<Feedback | null>(null);
  const [feedbackLoading, setFeedbackLoading] = useState(false);
  const [generating, setGenerating] = useState(false);

  useEffect(() => {
    setPage(1);
  }, [statusFilter]);

  useEffect(() => {
    loadEnrollments();
  }, [page, statusFilter]);

  const loadEnrollments = async () => {
    setLoading(true);
    try {
      const params: any = { page, page_size: 10 };
      if (statusFilter) params.status = statusFilter;
      const res = await adminEnrollmentApi.getAll(params);
      setEnrollments(res.data.items);
      setTotalPages(res.data.total_pages);
      setTotal(res.data.total);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleStatusChange = async (id: number, newStatus: string) => {
    try {
      await adminEnrollmentApi.update(id, { status: newStatus });
      await loadEnrollments();
    } catch (err) {
      console.error(err);
      alert('상태 변경에 실패했습니다.');
    }
  };

  const handleAttendanceChange = async (id: number, rate: number) => {
    try {
      await adminEnrollmentApi.update(id, { attendance_rate: rate });
    } catch (err) {
      console.error(err);
      alert('출석률 저장에 실패했습니다.');
    }
  };

  const openFeedbackModal = async (enrollment: EnrollmentDetail) => {
    setSelectedEnrollment(enrollment);
    setFeedback(null);
    setFeedbackLoading(true);
    
    try {
      const res = await adminEnrollmentApi.getFeedback(enrollment.id);
      setFeedback(res.data);
    } catch (err: any) {
      if (err.response?.status !== 404) {
        console.error(err);
      }
    } finally {
      setFeedbackLoading(false);
    }
  };

  const handleGenerateFeedback = async () => {
    if (!selectedEnrollment) return;
    
    setGenerating(true);
    try {
      const res = await adminEnrollmentApi.generateFeedback(selectedEnrollment.id);
      setFeedback(res.data);
    } catch (err: any) {
      console.error(err);
      alert(err.response?.data?.detail || '피드백 생성에 실패했습니다.');
    } finally {
      setGenerating(false);
    }
  };

  const closeFeedbackModal = () => {
    setSelectedEnrollment(null);
    setFeedback(null);
  };

  const getStatusStyle = (status: string) => {
    return STATUS_STYLES[status] || STATUS_STYLES.enrolled;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap justify-between items-end gap-4">
        <div className="flex flex-col gap-2">
          <h1 className="text-3xl font-black text-slate-900 tracking-tight">수강 관리</h1>
          <p className="text-slate-500 text-sm font-normal flex items-center gap-2">
            <span className="material-symbols-outlined text-base">analytics</span>
            총 수강 내역: {total}건
          </p>
        </div>
        <div className="flex gap-2">
          <button className="flex items-center justify-center gap-2 rounded-full border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors">
            <span className="material-symbols-outlined text-[20px]">download</span>
            Export
          </button>
        </div>
      </div>

      {/* Filter Chips */}
      <div className="flex gap-2 overflow-x-auto pb-2">
        <button
          onClick={() => setStatusFilter('')}
          className={`group flex h-9 items-center justify-center gap-x-2 rounded-full pl-3 pr-4 shadow-sm ring-1 ring-inset transition-all whitespace-nowrap ${
            statusFilter === ''
              ? 'bg-primary text-white ring-primary'
              : 'bg-white text-slate-500 ring-slate-200 hover:bg-slate-50 hover:text-slate-900'
          }`}
        >
          <span className="material-symbols-outlined text-[18px]">{FILTER_ICONS['']}</span>
          <span className="text-sm font-medium">전체</span>
        </button>
        {Object.entries(ENROLLMENT_STATUS_LABELS).map(([value, label]) => (
          <button
            key={value}
            onClick={() => setStatusFilter(value)}
            className={`group flex h-9 items-center justify-center gap-x-2 rounded-full pl-3 pr-4 shadow-sm ring-1 ring-inset transition-all whitespace-nowrap ${
              statusFilter === value
                ? 'bg-primary text-white ring-primary'
                : 'bg-white text-slate-500 ring-slate-200 hover:bg-slate-50 hover:text-slate-900'
            }`}
          >
            <span className="material-symbols-outlined text-[18px]">{FILTER_ICONS[value]}</span>
            <span className="text-sm font-medium">{label}</span>
          </button>
        ))}
      </div>

      {/* Content */}
      {loading ? (
        <div className="flex flex-col items-center justify-center py-16 bg-white rounded-2xl border border-slate-200">
          <div className="w-10 h-10 border-4 border-primary border-t-transparent rounded-full animate-spin mb-4" />
          <p className="text-slate-500">수강 목록을 불러오는 중...</p>
        </div>
      ) : enrollments.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 bg-white rounded-2xl border border-slate-200">
          <span className="material-symbols-outlined text-5xl text-slate-300 mb-4">assignment_ind</span>
          <p className="text-slate-500">수강 내역이 없습니다.</p>
        </div>
      ) : (
        <>
          {/* Table */}
          <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead className="bg-slate-50 sticky top-0 z-10 border-b border-slate-200">
                  <tr>
                    <th className="px-6 py-4 text-xs font-semibold uppercase tracking-wider text-slate-500">
                      수강생
                    </th>
                    <th className="px-6 py-4 text-xs font-semibold uppercase tracking-wider text-slate-500">
                      강습 정보
                    </th>
                    <th className="px-6 py-4 text-xs font-semibold uppercase tracking-wider text-slate-500 w-[180px]">
                      상태
                    </th>
                    <th className="px-6 py-4 text-xs font-semibold uppercase tracking-wider text-slate-500 w-[140px]">
                      출석률
                    </th>
                    <th className="px-6 py-4 text-xs font-semibold uppercase tracking-wider text-slate-500 whitespace-nowrap">
                      등록일
                    </th>
                    <th className="px-6 py-4 text-xs font-semibold uppercase tracking-wider text-slate-500 text-right">
                      액션
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {enrollments.map((enrollment) => {
                    const statusStyle = getStatusStyle(enrollment.status);
                    const isCompleted = enrollment.status === 'completed';
                    const isCancelled = enrollment.status === 'cancelled';

                    return (
                      <tr key={enrollment.id} className="hover:bg-slate-50 transition-colors group">
                        {/* Student Name */}
                        <td className="px-6 py-4">
                          <div className="flex items-center gap-3">
                            <div className="size-9 rounded-full bg-gradient-to-br from-primary to-purple-600 flex items-center justify-center text-white font-bold text-sm">
                              {enrollment.student_name.charAt(0)}
                            </div>
                            <span className="font-bold text-slate-900">{enrollment.student_name}</span>
                          </div>
                        </td>

                        {/* Lesson Info */}
                        <td className="px-6 py-4">
                          <div className="flex flex-col">
                            <span className="font-medium text-slate-900 text-sm">{enrollment.lesson_title}</span>
                            <span className="text-xs text-slate-500 mt-0.5">
                              {SPORT_LABELS[enrollment.lesson_sport_type] || enrollment.lesson_sport_type} • {DIFFICULTY_LABELS[enrollment.lesson_difficulty] || enrollment.lesson_difficulty}
                            </span>
                          </div>
                        </td>

                        {/* Status Dropdown */}
                        <td className="px-6 py-4">
                          <div className="relative">
                            <select
                              value={enrollment.status}
                              onChange={(e) => handleStatusChange(enrollment.id, e.target.value)}
                              className={`appearance-none w-full text-sm font-medium px-3 py-1.5 rounded-lg border cursor-pointer focus:outline-none focus:ring-2 focus:ring-primary/20 ${statusStyle.bg} ${statusStyle.text} ${statusStyle.border}`}
                            >
                              {Object.entries(ENROLLMENT_STATUS_LABELS).map(([value, label]) => (
                                <option key={value} value={value}>
                                  {label}
                                </option>
                              ))}
                            </select>
                            <div className={`pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 ${statusStyle.text}`}>
                              <span className="material-symbols-outlined text-[18px]">expand_more</span>
                            </div>
                          </div>
                        </td>

                        {/* Attendance Rate */}
                        <td className="px-6 py-4">
                          {isCancelled ? (
                            <span className="text-slate-400 text-sm">-</span>
                          ) : (
                            <div className="flex items-center">
                              <input
                                type="number"
                                min="0"
                                max="100"
                                defaultValue={enrollment.attendance_rate || 0}
                                onBlur={(e) => handleAttendanceChange(enrollment.id, Number(e.target.value))}
                                className="w-12 text-right p-1 rounded border border-transparent hover:border-slate-200 focus:border-primary focus:ring-0 text-sm font-medium bg-transparent transition-colors"
                              />
                              <span className="text-slate-500 text-sm ml-1">%</span>
                            </div>
                          )}
                        </td>

                        {/* Registration Date */}
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className="text-slate-500 text-sm tabular-nums">
                            {new Date(enrollment.created_at).toLocaleDateString('ko-KR')}
                          </span>
                        </td>

                        {/* Action */}
                        <td className="px-6 py-4 text-right">
                          {isCompleted ? (
                            <button
                              onClick={() => openFeedbackModal(enrollment)}
                              className="inline-flex items-center justify-center gap-1.5 px-4 py-1.5 rounded-full bg-purple-50 text-purple-700 text-sm font-semibold hover:bg-purple-100 transition-colors"
                            >
                              <span className="material-symbols-outlined text-[18px]">auto_awesome</span>
                              피드백
                            </button>
                          ) : (
                            <button
                              disabled
                              className="inline-flex items-center justify-center gap-1.5 px-4 py-1.5 rounded-full bg-slate-100 text-slate-400 text-sm font-medium cursor-not-allowed"
                            >
                              피드백
                            </button>
                          )}
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

      {/* Feedback Modal */}
      {selectedEnrollment && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          {/* Backdrop */}
          <div 
            className="absolute inset-0 bg-slate-900/60 backdrop-blur-sm"
            onClick={closeFeedbackModal}
          />
          
          {/* Modal Card */}
          <div className="relative w-full max-w-2xl bg-white rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
            {/* Modal Header */}
            <div className="px-6 py-5 border-b border-slate-100 flex items-center justify-between bg-white sticky top-0 z-10">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-purple-50 rounded-full text-purple-600">
                  <span className="material-symbols-outlined text-2xl">auto_awesome</span>
                </div>
                <div>
                  <h3 className="text-xl font-bold text-slate-900">AI 피드백 분석</h3>
                  <p className="text-sm text-slate-500">
                    {selectedEnrollment.student_name} • {selectedEnrollment.lesson_title}
                  </p>
                </div>
              </div>
              <button 
                onClick={closeFeedbackModal}
                className="text-slate-400 hover:text-slate-600 transition-colors p-1 rounded-full hover:bg-slate-100"
              >
                <span className="material-symbols-outlined">close</span>
              </button>
            </div>

            {/* Modal Content */}
            <div className="p-6 overflow-y-auto flex flex-col gap-6">
              {feedbackLoading ? (
                <div className="flex flex-col items-center justify-center py-12">
                  <div className="w-10 h-10 border-4 border-purple-500 border-t-transparent rounded-full animate-spin mb-4" />
                  <p className="text-slate-500">피드백을 불러오는 중...</p>
                </div>
              ) : feedback ? (
                <>
                  {/* Student Feedback Section */}
                  <div className="flex flex-col gap-3">
                    <h4 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                      <span className="material-symbols-outlined text-blue-500 text-lg">person</span>
                      수강생용 피드백
                    </h4>
                    <div className="bg-blue-50/50 border border-blue-100 rounded-xl p-5">
                      <p className="text-slate-700 text-sm leading-relaxed whitespace-pre-line">
                        {feedback.student_feedback}
                      </p>
                    </div>
                  </div>

                  {/* Instructor Feedback Section */}
                  <div className="flex flex-col gap-3">
                    <h4 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                      <span className="material-symbols-outlined text-purple-500 text-lg">school</span>
                      강사용 피드백
                    </h4>
                    <div className="bg-purple-50/50 border border-purple-100 rounded-xl p-5">
                      <p className="text-slate-700 text-sm leading-relaxed whitespace-pre-line">
                        {feedback.instructor_feedback}
                      </p>
                    </div>
                  </div>
                </>
              ) : (
                <div className="flex flex-col items-center justify-center py-12">
                  <div className="p-4 bg-purple-50 rounded-full mb-4">
                    <span className="material-symbols-outlined text-4xl text-purple-400">edit_note</span>
                  </div>
                  <p className="text-slate-500 mb-6">아직 생성된 피드백이 없습니다.</p>
                  <button
                    onClick={handleGenerateFeedback}
                    disabled={generating}
                    className="flex items-center gap-2 px-6 py-3 rounded-full bg-purple-600 text-white font-semibold hover:bg-purple-700 disabled:opacity-50 transition-colors shadow-lg shadow-purple-500/20"
                  >
                    {generating ? (
                      <>
                        <span className="material-symbols-outlined text-[18px] animate-spin">autorenew</span>
                        생성 중...
                      </>
                    ) : (
                      <>
                        <span className="material-symbols-outlined text-[18px]">auto_awesome</span>
                        AI 피드백 생성
                      </>
                    )}
                  </button>
                </div>
              )}
            </div>

            {/* Modal Footer */}
            {feedback && (
              <div className="px-6 py-4 bg-slate-50 border-t border-slate-100 flex justify-end gap-3 sticky bottom-0">
                <button 
                  onClick={() => navigator.clipboard.writeText(`[수강생용]\n${feedback.student_feedback}\n\n[강사용]\n${feedback.instructor_feedback}`)}
                  className="px-4 py-2.5 rounded-full border border-slate-300 text-slate-700 text-sm font-medium hover:bg-white hover:border-slate-400 transition-all"
                >
                  클립보드에 복사
                </button>
                <button
                  onClick={handleGenerateFeedback}
                  disabled={generating}
                  className="px-5 py-2.5 rounded-full bg-primary text-white text-sm font-medium hover:bg-blue-600 transition-all shadow-lg shadow-blue-500/20 flex items-center gap-2 disabled:opacity-50"
                >
                  {generating ? (
                    <>
                      <span className="material-symbols-outlined text-[18px] animate-spin">autorenew</span>
                      재생성 중...
                    </>
                  ) : (
                    <>
                      <span className="material-symbols-outlined text-[18px]">autorenew</span>
                      피드백 재생성
                    </>
                  )}
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

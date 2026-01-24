import { useEffect, useState } from 'react';
import { adminEnrollmentApi } from '../../services/api';
import type { EnrollmentDetail, Feedback } from '../../types';
import Pagination from '../../components/common/Pagination';
import {
  ENROLLMENT_STATUS_LABELS,
  SPORT_LABELS,
  DIFFICULTY_LABELS,
} from '../../constants/labels';

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
    setPage(1); // 필터 변경 시 첫 페이지로
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

  // 상태 변경
  const handleStatusChange = async (id: number, newStatus: string) => {
    try {
      await adminEnrollmentApi.update(id, { status: newStatus });
      await loadEnrollments();
    } catch (err) {
      console.error(err);
      alert('상태 변경에 실패했습니다.');
    }
  };

  // 출석률 변경 (blur 시 저장)
  const handleAttendanceChange = async (id: number, rate: number) => {
    try {
      await adminEnrollmentApi.update(id, { attendance_rate: rate });
    } catch (err) {
      console.error(err);
      alert('출석률 저장에 실패했습니다.');
    }
  };

  // 피드백 모달 열기
  const openFeedbackModal = async (enrollment: EnrollmentDetail) => {
    setSelectedEnrollment(enrollment);
    setFeedback(null);
    setFeedbackLoading(true);
    
    try {
      const res = await adminEnrollmentApi.getFeedback(enrollment.id);
      setFeedback(res.data);
    } catch (err: any) {
      // 404면 아직 피드백 없음
      if (err.response?.status !== 404) {
        console.error(err);
      }
    } finally {
      setFeedbackLoading(false);
    }
  };

  // 피드백 생성
  const handleGenerateFeedback = async () => {
    if (!selectedEnrollment) return;
    
    setGenerating(true);
    try {
      const res = await adminEnrollmentApi.generateFeedback(selectedEnrollment.id);
      setFeedback(res.data);
      alert('피드백이 생성되었습니다!');
    } catch (err: any) {
      console.error(err);
      alert(err.response?.data?.detail || '피드백 생성에 실패했습니다.');
    } finally {
      setGenerating(false);
    }
  };

  // 모달 닫기
  const closeFeedbackModal = () => {
    setSelectedEnrollment(null);
    setFeedback(null);
  };

  if (loading) return <div className="p-4">로딩 중...</div>;

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold">수강 관리</h1>
        <p className="text-sm text-gray-500 mt-1">총 {total}개</p>
      </div>

      {/* 상태 필터 */}
      <div className="mb-4 flex gap-2 flex-wrap">
        <button
          onClick={() => setStatusFilter('')}
          className={`px-4 py-2 rounded-lg text-sm transition ${
            statusFilter === '' 
              ? 'bg-blue-600 text-white' 
              : 'bg-gray-100 hover:bg-gray-200 text-gray-700'
          }`}
        >
          전체
        </button>
        {Object.entries(ENROLLMENT_STATUS_LABELS).map(([value, label]) => (
          <button
            key={value}
            onClick={() => setStatusFilter(value)}
            className={`px-4 py-2 rounded-lg text-sm transition ${
              statusFilter === value 
                ? 'bg-blue-600 text-white' 
                : 'bg-gray-100 hover:bg-gray-200 text-gray-700'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* 테이블 */}
      {enrollments.length === 0 ? (
        <div className="text-center py-12 text-gray-500 bg-white rounded-lg">
          수강 내역이 없습니다.
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  수강생
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  강습명
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  상태
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  출석률
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  등록일
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  피드백
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {enrollments.map((enrollment) => (
                <tr key={enrollment.id} className="hover:bg-gray-50">
                  {/* 수강생 */}
                  <td className="px-4 py-4 font-medium text-gray-900">
                    {enrollment.student_name}
                  </td>
                  
                  {/* 강습명 */}
                  <td className="px-4 py-4">
                    <div className="text-sm text-gray-900">{enrollment.lesson_title}</div>
                    <div className="text-xs text-gray-500">
                      {SPORT_LABELS[enrollment.lesson_sport_type] || enrollment.lesson_sport_type} ・{' '}
                      {DIFFICULTY_LABELS[enrollment.lesson_difficulty] || enrollment.lesson_difficulty}
                    </div>
                  </td>
                  
                  {/* 상태 (드롭다운) */}
                  <td className="px-4 py-4">
                    <select
                      value={enrollment.status}
                      onChange={(e) => handleStatusChange(enrollment.id, e.target.value)}
                      className={`text-sm px-3 py-1.5 rounded-lg border cursor-pointer ${
                        enrollment.status === 'completed'
                          ? 'bg-green-50 border-green-300 text-green-800'
                          : enrollment.status === 'in_progress'
                          ? 'bg-blue-50 border-blue-300 text-blue-800'
                          : enrollment.status === 'cancelled'
                          ? 'bg-red-50 border-red-300 text-red-800'
                          : 'bg-gray-50 border-gray-300 text-gray-800'
                      }`}
                    >
                      {Object.entries(ENROLLMENT_STATUS_LABELS).map(([value, label]) => (
                        <option key={value} value={value}>
                          {label}
                        </option>
                      ))}
                    </select>
                  </td>
                  
                  {/* 출석률 (입력) */}
                  <td className="px-4 py-4">
                    <div className="flex items-center gap-1">
                      <input
                        type="number"
                        min="0"
                        max="100"
                        defaultValue={enrollment.attendance_rate || 0}
                        onBlur={(e) => handleAttendanceChange(enrollment.id, Number(e.target.value))}
                        className="w-16 text-sm px-2 py-1.5 border border-gray-300 rounded-lg text-center"
                      />
                      <span className="text-sm text-gray-500">%</span>
                    </div>
                  </td>
                  
                  {/* 등록일 */}
                  <td className="px-4 py-4 text-sm text-gray-500">
                    {new Date(enrollment.created_at).toLocaleDateString('ko-KR')}
                  </td>
                  
                  {/* 피드백 버튼 */}
                  <td className="px-4 py-4">
                    {enrollment.status === 'completed' ? (
                      <button
                        onClick={() => openFeedbackModal(enrollment)}
                        className="text-sm bg-purple-100 text-purple-700 px-3 py-1.5 rounded-lg hover:bg-purple-200 transition"
                      >
                        피드백
                      </button>
                    ) : (
                      <span className="text-sm text-gray-400">-</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* 페이징 */}
      {enrollments.length > 0 && (
        <Pagination
          page={page}
          totalPages={totalPages}
          onPageChange={setPage}
        />
      )}

      {/* 피드백 모달 */}
      {selectedEnrollment && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-2xl w-full max-h-[80vh] overflow-y-auto">
            {/* 모달 헤더 */}
            <div className="p-6 border-b sticky top-0 bg-white">
              <div className="flex justify-between items-start">
                <div>
                  <h2 className="text-xl font-bold text-gray-900">AI 피드백</h2>
                  <p className="text-sm text-gray-500 mt-1">
                    {selectedEnrollment.student_name} ・ {selectedEnrollment.lesson_title}
                  </p>
                  <p className="text-xs text-gray-400 mt-1">
                    출석률: {selectedEnrollment.attendance_rate || 0}%
                  </p>
                </div>
                <button
                  onClick={closeFeedbackModal}
                  className="text-gray-400 hover:text-gray-600 text-2xl leading-none"
                >
                  ×
                </button>
              </div>
            </div>

            {/* 모달 콘텐츠 */}
            <div className="p-6">
              {feedbackLoading ? (
                <div className="text-center py-12 text-gray-500">로딩 중...</div>
              ) : feedback ? (
                <div className="space-y-6">
                  {/* 수강생용 피드백 */}
                  <div>
                    <h3 className="text-sm font-semibold text-blue-600 mb-2 flex items-center gap-2">
                      👤 수강생용 피드백
                    </h3>
                    <div className="bg-blue-50 rounded-lg p-4 text-gray-700 whitespace-pre-line leading-relaxed">
                      {feedback.student_feedback}
                    </div>
                  </div>

                  {/* 강사용 피드백 */}
                  <div>
                    <h3 className="text-sm font-semibold text-purple-600 mb-2 flex items-center gap-2">
                      👨‍🏫 강사용 피드백
                    </h3>
                    <div className="bg-purple-50 rounded-lg p-4 text-gray-700 whitespace-pre-line leading-relaxed">
                      {feedback.instructor_feedback}
                    </div>
                  </div>

                  {/* 재생성 버튼 */}
                  <button
                    onClick={handleGenerateFeedback}
                    disabled={generating}
                    className="w-full py-2.5 border border-purple-300 text-purple-600 rounded-lg hover:bg-purple-50 disabled:opacity-50 transition"
                  >
                    {generating ? '재생성 중...' : '🔄 피드백 재생성'}
                  </button>
                </div>
              ) : (
                <div className="text-center py-12">
                  <div className="text-4xl mb-4">📝</div>
                  <p className="text-gray-500 mb-6">아직 생성된 피드백이 없습니다.</p>
                  <button
                    onClick={handleGenerateFeedback}
                    disabled={generating}
                    className="bg-purple-600 text-white px-8 py-3 rounded-lg hover:bg-purple-700 disabled:opacity-50 transition"
                  >
                    {generating ? '생성 중...' : '✨ AI 피드백 생성'}
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

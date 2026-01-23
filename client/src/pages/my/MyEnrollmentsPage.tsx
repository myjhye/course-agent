import { useEffect, useState } from 'react';
import { myEnrollmentApi } from '../../services/api';
import type { EnrollmentDetail } from '../../types';
import { ENROLLMENT_STATUS_LABELS } from '../../constants/labels';

export default function MyEnrollmentsPage() {
  const [studentName] = useState('홍길동'); // 임시: 나중에 인증으로 교체
  const [enrollments, setEnrollments] = useState<EnrollmentDetail[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadEnrollments();
  }, []);

  const loadEnrollments = async () => {
    try {
      const res = await myEnrollmentApi.getAll(studentName);
      setEnrollments(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = async (id: number) => {
    if (!confirm('정말 취소하시겠습니까?')) return;

    try {
      await myEnrollmentApi.cancel(id);
      await loadEnrollments();
      alert('수강이 취소되었습니다.');
    } catch (err) {
      console.error(err);
      alert('취소에 실패했습니다.');
    }
  };

  if (loading) return <div className="p-8">로딩 중...</div>;

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <h1 className="text-3xl font-bold mb-8">내 수강 현황</h1>

      {enrollments.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          수강 중인 강습이 없습니다.
        </div>
      ) : (
        <div className="space-y-4">
          {enrollments.map((enrollment) => (
            <div
              key={enrollment.id}
              className="bg-white border rounded-lg p-6 hover:shadow-lg transition-shadow"
            >
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <h2 className="text-xl font-semibold mb-2">
                    {enrollment.lesson_title}
                  </h2>
                  <div className="flex items-center gap-4 text-sm text-gray-500 mb-2">
                    <span>종목: {enrollment.lesson_sport_type}</span>
                    <span>난이도: {enrollment.lesson_difficulty}</span>
                  </div>
                  <div className="flex items-center gap-4 mt-4">
                    <span
                      className={`px-3 py-1 text-sm rounded-full ${
                        enrollment.status === 'completed'
                          ? 'bg-green-100 text-green-800'
                          : enrollment.status === 'in_progress'
                          ? 'bg-blue-100 text-blue-800'
                          : 'bg-gray-100 text-gray-800'
                      }`}
                    >
                      {ENROLLMENT_STATUS_LABELS[enrollment.status]}
                    </span>
                    {enrollment.attendance_rate !== null && (
                      <span className="text-sm text-gray-600">
                        출석률: {enrollment.attendance_rate}%
                      </span>
                    )}
                  </div>
                </div>
                {enrollment.status !== 'completed' && enrollment.status !== 'cancelled' && (
                  <button
                    onClick={() => handleCancel(enrollment.id)}
                    className="px-4 py-2 text-sm text-red-600 border border-red-300 rounded-lg hover:bg-red-50"
                  >
                    취소
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}


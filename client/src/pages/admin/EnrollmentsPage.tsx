import { useEffect, useState } from 'react';
import { adminEnrollmentApi } from '../../services/api';
import type { EnrollmentDetail } from '../../types';
import { ENROLLMENT_STATUS_LABELS } from '../../constants/labels';

export default function EnrollmentsPage() {
  const [enrollments, setEnrollments] = useState<EnrollmentDetail[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadEnrollments();
  }, []);

  const loadEnrollments = async () => {
    try {
      const res = await adminEnrollmentApi.getAll();
      setEnrollments(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div>로딩 중...</div>;

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">수강 관리</h1>

      {enrollments.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          등록된 수강이 없습니다.
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  수강생
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  강습명
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  상태
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  출석률
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  등록일
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {enrollments.map((enrollment) => (
                <tr key={enrollment.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 font-medium">{enrollment.student_name}</td>
                  <td className="px-6 py-4 text-sm text-gray-500">
                    {enrollment.lesson_title}
                  </td>
                  <td className="px-6 py-4">
                    <span
                      className={`px-2 py-1 text-xs rounded-full ${
                        enrollment.status === 'completed'
                          ? 'bg-green-100 text-green-800'
                          : enrollment.status === 'in_progress'
                          ? 'bg-blue-100 text-blue-800'
                          : 'bg-gray-100 text-gray-800'
                      }`}
                    >
                      {ENROLLMENT_STATUS_LABELS[enrollment.status]}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-500">
                    {enrollment.attendance_rate !== null ? `${enrollment.attendance_rate}%` : '-'}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-500">
                    {new Date(enrollment.created_at).toLocaleDateString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}


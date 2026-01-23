import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { adminLessonApi } from '../../services/api';
import type { Lesson } from '../../types';
import { SPORT_LABELS, DIFFICULTY_LABELS, STATUS_LABELS } from '../../constants/labels';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function LessonsPage() {
  const [lessons, setLessons] = useState<Lesson[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadLessons();
  }, []);

  const loadLessons = async () => {
    try {
      const res = await adminLessonApi.getAll();
      setLessons(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div>로딩 중...</div>;

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">강습 관리</h1>
        <Link
          to="/admin/lessons/new"
          className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
        >
          + 새 강습 등록
        </Link>
      </div>

      {lessons.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          등록된 강습이 없습니다.
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  썸네일
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  강습명
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  종목
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  난이도
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  상태
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  등록일
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {lessons.map((lesson) => {
                const thumbnailUrl = lesson.active_content?.thumbnail_url
                  ? `${API_BASE}${lesson.active_content.thumbnail_url}`
                  : null;
                
                return (
                  <tr key={lesson.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4">
                      {thumbnailUrl ? (
                        <img
                          src={thumbnailUrl}
                          alt={lesson.title}
                          className="w-32 h-20 object-cover rounded border"
                        />
                      ) : (
                        <div className="w-32 h-20 bg-gray-200 rounded flex items-center justify-center text-4xl">
                          {lesson.sport_type === 'swimming' && '🏊'}
                          {lesson.sport_type === 'tennis' && '🎾'}
                          {lesson.sport_type === 'golf' && '⛳'}
                          {lesson.sport_type === 'fitness' && '💪'}
                          {lesson.sport_type === 'yoga' && '🧘'}
                          {lesson.sport_type === 'pilates' && '🤸'}
                          {lesson.sport_type === 'other' && '🏃'}
                        </div>
                      )}
                    </td>
                    <td className="px-6 py-4">
                      <Link
                        to={`/admin/lessons/${lesson.id}`}
                        className="text-blue-600 hover:underline font-medium"
                      >
                        {lesson.title}
                      </Link>
                    </td>
                  <td className="px-6 py-4 text-sm text-gray-500">
                    {SPORT_LABELS[lesson.sport_type] || lesson.sport_type}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-500">
                    {DIFFICULTY_LABELS[lesson.difficulty] || lesson.difficulty}
                  </td>
                  <td className="px-6 py-4">
                    <span
                      className={`px-2 py-1 text-xs rounded-full ${
                        lesson.status === 'published'
                          ? 'bg-green-100 text-green-800'
                          : lesson.status === 'draft'
                          ? 'bg-yellow-100 text-yellow-800'
                          : 'bg-gray-100 text-gray-800'
                      }`}
                    >
                      {STATUS_LABELS[lesson.status]}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-500">
                    {new Date(lesson.created_at).toLocaleDateString()}
                  </td>
                </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}


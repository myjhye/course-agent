import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { myEnrollmentApi, myRecommendationApi } from '../../services/api';
import type { EnrollmentDetail, Recommendation } from '../../types';
import {
  SPORT_LABELS,
  DIFFICULTY_LABELS,
  ENROLLMENT_STATUS_LABELS,
} from '../../constants/labels';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// 임시 수강생 이름 (실제로는 로그인 또는 입력받음)
const STUDENT_NAME = '홍길동';

export default function MyEnrollmentsPage() {
  const [enrollments, setEnrollments] = useState<EnrollmentDetail[]>([]);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [loading, setLoading] = useState(true);
  const [recLoading, setRecLoading] = useState(true);

  useEffect(() => {
    loadEnrollments();
    loadRecommendations();
  }, []);

  const loadEnrollments = async () => {
    try {
      const res = await myEnrollmentApi.getAll(STUDENT_NAME);
      setEnrollments(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const loadRecommendations = async () => {
    try {
      const res = await myRecommendationApi.getRecommendations(STUDENT_NAME, 3);
      setRecommendations(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setRecLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* 헤더 */}
      <header className="bg-white shadow-sm">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center justify-between">
          <Link to="/" className="text-xl font-bold text-blue-600">
            Course Agent
          </Link>
          <Link to="/lessons" className="text-sm text-gray-600 hover:text-blue-600">
            강습 둘러보기
          </Link>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-8 space-y-8">
        {/* 내 수강 현황 */}
        <section>
          <h1 className="text-2xl font-bold mb-4">내 수강 현황</h1>
          <p className="text-gray-500 mb-6">수강생: {STUDENT_NAME}</p>

          {loading ? (
            <div className="text-center py-8 text-gray-500">로딩 중...</div>
          ) : enrollments.length === 0 ? (
            <div className="text-center py-12 bg-white rounded-xl text-gray-500">
              <p className="mb-4">아직 수강 중인 강습이 없습니다.</p>
              <Link
                to="/lessons"
                className="text-blue-600 hover:underline"
              >
                강습 둘러보기 →
              </Link>
            </div>
          ) : (
            <div className="space-y-4">
              {enrollments.map((enrollment) => (
                <div
                  key={enrollment.id}
                  className="bg-white rounded-xl shadow-sm p-4 flex items-center justify-between"
                >
                  <div>
                    <h3 className="font-bold text-gray-900">
                      {enrollment.lesson_title}
                    </h3>
                    <p className="text-sm text-gray-500 mt-1">
                      {SPORT_LABELS[enrollment.lesson_sport_type] || enrollment.lesson_sport_type} ・{' '}
                      {DIFFICULTY_LABELS[enrollment.lesson_difficulty] || enrollment.lesson_difficulty}
                    </p>
                  </div>
                  <div className="text-right">
                    <span
                      className={`inline-block px-3 py-1 rounded-full text-sm ${
                        enrollment.status === 'completed'
                          ? 'bg-green-100 text-green-700'
                          : enrollment.status === 'in_progress'
                          ? 'bg-blue-100 text-blue-700'
                          : 'bg-gray-100 text-gray-700'
                      }`}
                    >
                      {ENROLLMENT_STATUS_LABELS[enrollment.status] || enrollment.status}
                    </span>
                    <p className="text-xs text-gray-400 mt-1">
                      출석률: {enrollment.attendance_rate || 0}%
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* 추천 강습 */}
        <section>
          <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
            ✨ 추천 강습
          </h2>

          {recLoading ? (
            <div className="text-center py-8 text-gray-500">추천 강습 불러오는 중...</div>
          ) : recommendations.length === 0 ? (
            <div className="text-center py-8 bg-white rounded-xl text-gray-500">
              추천할 강습이 없습니다.
            </div>
          ) : (
            <div className="space-y-4">
              {recommendations.map((rec, idx) => (
                <Link
                  key={rec.lesson.id}
                  to={`/lessons/${rec.lesson.id}`}
                  className="block bg-white rounded-xl shadow-sm overflow-hidden hover:shadow-md transition"
                >
                  <div className="flex">
                    {/* 썸네일 */}
                    <div className="w-32 h-24 bg-gradient-to-br from-purple-100 to-purple-200 flex-shrink-0">
                      {rec.lesson.thumbnail_url ? (
                        <img
                          src={`${API_BASE}${rec.lesson.thumbnail_url}`}
                          alt={rec.lesson.title}
                          className="w-full h-full object-cover"
                        />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center text-2xl">
                          {rec.reason_type === 'next_level' ? '📈' : rec.reason_type === 'new_sport' ? '🆕' : '⭐'}
                        </div>
                      )}
                    </div>

                    {/* 정보 */}
                    <div className="p-4 flex-1">
                      <div className="flex items-start justify-between">
                        <div>
                          <div className="flex items-center gap-2 mb-1">
                            <span className="text-xs bg-purple-100 text-purple-700 px-2 py-0.5 rounded-full">
                              {rec.reason_type === 'next_level' ? '다음 단계' : 
                               rec.reason_type === 'new_sport' ? '새로운 도전' : '추천'}
                            </span>
                          </div>
                          <h3 className="font-bold text-gray-900">{rec.lesson.title}</h3>
                          <p className="text-xs text-gray-500 mt-1">
                            {SPORT_LABELS[rec.lesson.sport_type] || rec.lesson.sport_type} ・{' '}
                            {DIFFICULTY_LABELS[rec.lesson.difficulty] || rec.lesson.difficulty}
                          </p>
                        </div>
                      </div>
                      <p className="text-sm text-gray-600 mt-2 line-clamp-2">
                        💬 {rec.reason}
                      </p>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}

import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { myEnrollmentApi, myRecommendationApi } from '../../services/api';
import type { CategorizedRecommendations } from '../../services/api';
import {
  SPORT_LABELS,
  DIFFICULTY_LABELS,
  ENROLLMENT_STATUS_LABELS,
} from '../../constants/labels';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const STUDENT_NAME = '홍길동'; // 하드코딩

export default function MyEnrollmentsPage() {
  const [enrollments, setEnrollments] = useState<any[]>([]);
  const [recommendations, setRecommendations] = useState<CategorizedRecommendations | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [enrollRes, recRes] = await Promise.all([
        myEnrollmentApi.getAll(STUDENT_NAME),
        myRecommendationApi.getCategorized(STUDENT_NAME)
      ]);
      setEnrollments(enrollRes.data);
      setRecommendations(recRes.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="min-h-screen bg-gray-50 flex items-center justify-center">로딩 중...</div>;
  }

  const hasAnyRecommendation = recommendations && (
    recommendations.next_level || recommendations.new_sport || recommendations.interest_based
  );

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center justify-between">
          <Link to="/" className="text-xl font-bold text-blue-600">Course Agent</Link>
          <Link to="/lessons" className="text-sm text-gray-600 hover:text-blue-600">강습 둘러보기</Link>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-8 space-y-8">
        {/* 내 수강 현황 */}
        <section>
          <h1 className="text-2xl font-bold mb-2">내 수강 현황</h1>
          <p className="text-sm text-gray-500 mb-6">수강생: {STUDENT_NAME}</p>

          {enrollments.length === 0 ? (
            <div className="bg-white rounded-xl p-8 text-center text-gray-500">
              수강 중인 강습이 없습니다.
              <Link to="/lessons" className="block mt-2 text-blue-600 hover:underline">
                강습 둘러보기 →
              </Link>
            </div>
          ) : (
            <div className="space-y-3">
              {enrollments.map((enrollment) => (
                <EnrollmentCard key={enrollment.id} enrollment={enrollment} />
              ))}
            </div>
          )}
        </section>

        {/* 추천 강습 */}
        {hasAnyRecommendation && (
          <section>
            <h2 className="text-xl font-bold mb-6">✨ 맞춤 추천</h2>
            <div className="space-y-6">

              {/* 다음 단계 */}
              <RecommendationSection
                title="🎯 다음 단계"
                subtitle="지금 듣고 있는 강습의 다음 레벨"
                item={recommendations?.next_level}
                emptyMessage={null}
              />

              {/* 새로운 도전 */}
              <RecommendationSection
                title="🌟 새로운 도전"
                subtitle="아직 경험하지 않은 종목"
                item={recommendations?.new_sport}
                emptyMessage={null}
              />

              {/* 관심 기반 */}
              <RecommendationSection
                title="💡 관심 기반"
                subtitle="조회하거나 찜한 강습 기반"
                item={recommendations?.interest_based}
                emptyMessage={null}
              />

            </div>
          </section>
        )}
      </main>
    </div>
  );
}

function EnrollmentCard({ enrollment }: { enrollment: any }) {
  const statusColors: Record<string, string> = {
    enrolled: 'bg-gray-100 text-gray-700',
    in_progress: 'bg-blue-100 text-blue-700',
    completed: 'bg-green-100 text-green-700',
    cancelled: 'bg-red-100 text-red-700',
  };

  return (
    <div className="bg-white rounded-xl p-4 flex items-center justify-between">
      <div>
        <h3 className="font-medium">{enrollment.lesson?.title || '알 수 없는 강습'}</h3>
        <p className="text-sm text-gray-500">
          {SPORT_LABELS[enrollment.lesson?.sport_type] || enrollment.lesson?.sport_type} ・{' '}
          {DIFFICULTY_LABELS[enrollment.lesson?.difficulty] || enrollment.lesson?.difficulty}
        </p>
      </div>
      <div className="text-right">
        <span className={`px-3 py-1 rounded-full text-sm ${statusColors[enrollment.status] || ''}`}>
          {ENROLLMENT_STATUS_LABELS[enrollment.status] || enrollment.status}
        </span>
        <p className="text-xs text-gray-400 mt-1">출석률: {enrollment.attendance_rate || 0}%</p>
      </div>
    </div>
  );
}

function RecommendationSection({
  title,
  subtitle,
  item,
  emptyMessage
}: {
  title: string;
  subtitle: string;
  item: any;
  emptyMessage: string | null;
}) {
  if (!item && !emptyMessage) return null;

  return (
    <div className="bg-white rounded-xl p-5">
      <div className="mb-4">
        <h3 className="font-bold text-lg">{title}</h3>
        <p className="text-sm text-gray-500">{subtitle}</p>
      </div>

      {item ? (
        <Link
          to={`/lessons/${item.lesson.id}`}
          className="flex gap-4 hover:bg-gray-50 rounded-lg p-2 -m-2 transition"
        >
          {/* 썸네일 */}
          <div className="w-24 h-16 bg-gray-100 rounded-lg overflow-hidden flex-shrink-0">
            {item.lesson.thumbnail_url ? (
              <img
                src={`${API_BASE}${item.lesson.thumbnail_url}`}
                alt=""
                className="w-full h-full object-cover"
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center text-2xl">
                {item.lesson.sport_type === 'swimming' && '🏊'}
                {item.lesson.sport_type === 'tennis' && '🎾'}
                {item.lesson.sport_type === 'golf' && '⛳'}
                {item.lesson.sport_type === 'fitness' && '💪'}
                {item.lesson.sport_type === 'yoga' && '🧘'}
                {item.lesson.sport_type === 'pilates' && '🤸'}
              </div>
            )}
          </div>

          {/* 정보 */}
          <div className="flex-1 min-w-0">
            <h4 className="font-medium truncate">{item.lesson.title}</h4>
            <p className="text-sm text-gray-500">
              {SPORT_LABELS[item.lesson.sport_type]} ・{' '}
              {DIFFICULTY_LABELS[item.lesson.difficulty]}
            </p>
            <p className="text-sm text-blue-600 mt-1">💬 {item.reason}</p>
          </div>
        </Link>
      ) : (
        <p className="text-sm text-gray-400">{emptyMessage}</p>
      )}
    </div>
  );
}

import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { myEnrollmentApi, myRecommendationApi, lessonApi } from '../../services/api';
import type { CategorizedRecommendations } from '../../services/api';
import {
  SPORT_LABELS,
  DIFFICULTY_LABELS,
  ENROLLMENT_STATUS_LABELS,
  TARGET_LABELS,
} from '../../constants/labels';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const STUDENT_NAME = '홍길동'; // 하드코딩

// 종목별 아이콘
const SPORT_ICONS: Record<string, string> = {
  swimming: '🏊',
  tennis: '🎾',
  golf: '⛳',
  yoga: '🧘',
  pilates: '🤸',
  fitness: '💪',
  other: '🏃',
};

// 상태별 색상
const STATUS_COLORS: Record<string, { bg: string; text: string; icon: string }> = {
  enrolled: { bg: 'bg-gray-100', text: 'text-gray-700', icon: '📝' },
  in_progress: { bg: 'bg-blue-100', text: 'text-blue-700', icon: '📚' },
  completed: { bg: 'bg-green-100', text: 'text-green-700', icon: '🎉' },
  cancelled: { bg: 'bg-red-100', text: 'text-red-700', icon: '❌' },
};

type TabType = 'enrollments' | 'liked' | 'recommendations';

export default function MyEnrollmentsPage() {
  const [activeTab, setActiveTab] = useState<TabType>('enrollments');
  const [enrollments, setEnrollments] = useState<any[]>([]);
  const [likedLessons, setLikedLessons] = useState<any[]>([]);
  const [recommendations, setRecommendations] = useState<CategorizedRecommendations | null>(null);
  
  // 분리된 로딩 상태
  const [loading, setLoading] = useState(true); // 일반 데이터 (수강, 찜)
  const [recommendationsLoading, setRecommendationsLoading] = useState(true); // AI 추천

  useEffect(() => {
    loadBasicData();
    loadRecommendations(); // 별도로 로드
  }, []);

  // 일반 데이터 로드 (빠름)
  const loadBasicData = async () => {
    setLoading(true);
    try {
      const [enrollRes, likedRes] = await Promise.all([
        myEnrollmentApi.getAll(STUDENT_NAME),
        lessonApi.getLikedLessons(STUDENT_NAME).catch(() => ({ data: [] })),
      ]);
      setEnrollments(enrollRes.data);
      setLikedLessons(likedRes.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  // AI 추천 로드 (느림 - 별도 로딩)
  const loadRecommendations = async () => {
    setRecommendationsLoading(true);
    try {
      const recRes = await myRecommendationApi.getCategorized(STUDENT_NAME);
      setRecommendations(recRes.data);
    } catch (err) {
      console.error(err);
    } finally {
      setRecommendationsLoading(false);
    }
  };

  const handleUnlike = async (lessonId: number) => {
    try {
      await lessonApi.toggleLike(lessonId, STUDENT_NAME);
      setLikedLessons((prev) => prev.filter((l) => l.id !== lessonId));
    } catch (err) {
      console.error(err);
    }
  };

  // 통계
  const stats = {
    total: enrollments.length,
    inProgress: enrollments.filter((e) => e.status === 'in_progress').length,
    completed: enrollments.filter((e) => e.status === 'completed').length,
    liked: likedLessons.length,
  };

  const hasAnyRecommendation = recommendations && (
    recommendations.next_level || recommendations.new_sport || recommendations.interest_based
  );

  if (loading) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
          <p className="text-gray-500">데이터를 불러오는 중...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* 헤더 */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">내 강습</h1>
        <p className="text-gray-500">안녕하세요, {STUDENT_NAME}님! 오늘도 건강한 하루 보내세요 💪</p>
      </div>

      {/* 통계 카드 */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <StatCard icon="📚" label="전체 수강" value={stats.total} color="blue" />
        <StatCard icon="📖" label="수강 중" value={stats.inProgress} color="yellow" />
        <StatCard icon="🎉" label="수강 완료" value={stats.completed} color="green" />
        <StatCard icon="❤️" label="찜한 강습" value={stats.liked} color="red" />
      </div>

      {/* 탭 네비게이션 */}
      <div className="bg-white rounded-2xl shadow-sm mb-6 overflow-hidden">
        <div className="flex border-b">
          <TabButton
            active={activeTab === 'enrollments'}
            onClick={() => setActiveTab('enrollments')}
            icon="📚"
            label="수강 현황"
            count={enrollments.length}
          />
          <TabButton
            active={activeTab === 'liked'}
            onClick={() => setActiveTab('liked')}
            icon="❤️"
            label="찜한 강습"
            count={likedLessons.length}
          />
          <TabButton
            active={activeTab === 'recommendations'}
            onClick={() => setActiveTab('recommendations')}
            icon="✨"
            label="맞춤 추천"
            loading={recommendationsLoading}
          />
        </div>

        {/* 탭 콘텐츠 */}
        <div className="p-6">
          {/* 수강 현황 */}
          {activeTab === 'enrollments' && (
            <div>
              {enrollments.length === 0 ? (
                <EmptyState
                  icon="📚"
                  title="수강 중인 강습이 없습니다"
                  description="새로운 강습을 둘러보고 시작해보세요!"
                  actionLabel="강습 둘러보기"
                  actionLink="/lessons"
                />
              ) : (
                <div className="space-y-4">
                  {enrollments.map((enrollment) => (
                    <EnrollmentCard key={enrollment.id} enrollment={enrollment} />
                  ))}
                </div>
              )}
            </div>
          )}

          {/* 찜한 강습 */}
          {activeTab === 'liked' && (
            <div>
              {likedLessons.length === 0 ? (
                <EmptyState
                  icon="❤️"
                  title="찜한 강습이 없습니다"
                  description="마음에 드는 강습을 찜해보세요!"
                  actionLabel="강습 둘러보기"
                  actionLink="/lessons"
                />
              ) : (
                <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
                  {likedLessons.map((lesson) => (
                    <LikedLessonCard
                      key={lesson.id}
                      lesson={lesson}
                      onUnlike={() => handleUnlike(lesson.id)}
                    />
                  ))}
                </div>
              )}
            </div>
          )}

          {/* 맞춤 추천 */}
          {activeTab === 'recommendations' && (
            <div>
              {recommendationsLoading ? (
                <RecommendationsLoading />
              ) : !hasAnyRecommendation ? (
                <EmptyState
                  icon="✨"
                  title="추천할 강습이 없습니다"
                  description="강습을 더 둘러보시면 AI가 맞춤 추천을 해드려요!"
                  actionLabel="강습 둘러보기"
                  actionLink="/lessons"
                />
              ) : (
                <div className="space-y-6">
                  {recommendations?.next_level && (
                    <RecommendationCard
                      category="🎯 다음 단계"
                      subtitle="지금 듣고 있는 강습의 다음 레벨"
                      item={recommendations.next_level}
                    />
                  )}
                  {recommendations?.new_sport && (
                    <RecommendationCard
                      category="🌟 새로운 도전"
                      subtitle="아직 경험하지 않은 종목"
                      item={recommendations.new_sport}
                    />
                  )}
                  {recommendations?.interest_based && (
                    <RecommendationCard
                      category="💡 관심 기반"
                      subtitle="조회하거나 찜한 강습 기반"
                      item={recommendations.interest_based}
                    />
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// 통계 카드
function StatCard({
  icon,
  label,
  value,
  color,
}: {
  icon: string;
  label: string;
  value: number;
  color: 'blue' | 'yellow' | 'green' | 'red';
}) {
  const colorClasses = {
    blue: 'bg-blue-50 text-blue-600',
    yellow: 'bg-yellow-50 text-yellow-600',
    green: 'bg-green-50 text-green-600',
    red: 'bg-red-50 text-red-600',
  };

  return (
    <div className="bg-white rounded-2xl p-5 shadow-sm">
      <div className={`w-12 h-12 ${colorClasses[color]} rounded-xl flex items-center justify-center text-2xl mb-3`}>
        {icon}
      </div>
      <div className="text-2xl font-bold text-gray-900">{value}</div>
      <div className="text-sm text-gray-500">{label}</div>
    </div>
  );
}

// 탭 버튼
function TabButton({
  active,
  onClick,
  icon,
  label,
  count,
  loading,
}: {
  active: boolean;
  onClick: () => void;
  icon: string;
  label: string;
  count?: number;
  loading?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      className={`flex-1 py-4 text-center font-medium transition flex items-center justify-center gap-2 ${
        active
          ? 'text-blue-600 border-b-2 border-blue-600 bg-blue-50/50'
          : 'text-gray-500 hover:text-gray-700 hover:bg-gray-50'
      }`}
    >
      <span>{icon}</span>
      <span>{label}</span>
      {loading && (
        <span className="w-4 h-4 border-2 border-purple-400 border-t-transparent rounded-full animate-spin" />
      )}
      {count !== undefined && !loading && (
        <span className={`text-xs px-2 py-0.5 rounded-full ${active ? 'bg-blue-100' : 'bg-gray-100'}`}>
          {count}
        </span>
      )}
    </button>
  );
}

// AI 추천 로딩 상태
function RecommendationsLoading() {
  return (
    <div className="space-y-6">
      {/* 헤더 */}
      <div className="text-center py-4">
        <div className="inline-flex items-center gap-3 px-5 py-3 bg-gradient-to-r from-purple-100 to-blue-100 rounded-2xl">
          <div className="w-8 h-8 border-3 border-purple-500 border-t-transparent rounded-full animate-spin" />
          <span className="text-purple-700 font-medium">AI가 맞춤 추천을 분석 중입니다...</span>
        </div>
      </div>
      
      {/* 스켈레톤 카드 */}
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
        {[1, 2, 3].map((i) => (
          <div key={i} className="bg-gray-50 rounded-2xl overflow-hidden animate-pulse">
            {/* 썸네일 스켈레톤 */}
            <div className="h-40 bg-gradient-to-br from-gray-200 to-gray-300" />
            <div className="p-5 space-y-4">
              {/* 카테고리 */}
              <div className="h-5 w-24 bg-gray-200 rounded-full" />
              {/* 제목 */}
              <div className="space-y-2">
                <div className="h-5 bg-gray-200 rounded w-full" />
                <div className="h-5 bg-gray-200 rounded w-3/4" />
              </div>
              {/* 설명 */}
              <div className="space-y-2">
                <div className="h-3 bg-gray-100 rounded w-full" />
                <div className="h-3 bg-gray-100 rounded w-5/6" />
              </div>
              {/* AI 이유 */}
              <div className="pt-3 border-t border-gray-100">
                <div className="flex items-start gap-2">
                  <div className="w-5 h-5 bg-purple-100 rounded" />
                  <div className="flex-1 space-y-1.5">
                    <div className="h-3 bg-purple-50 rounded w-full" />
                    <div className="h-3 bg-purple-50 rounded w-4/5" />
                  </div>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
      
      {/* 로딩 힌트 */}
      <p className="text-center text-sm text-gray-400">
        수강 이력과 관심사를 분석하여 개인화된 추천을 준비하고 있어요
      </p>
    </div>
  );
}

// 빈 상태
function EmptyState({
  icon,
  title,
  description,
  actionLabel,
  actionLink,
}: {
  icon: string;
  title: string;
  description: string;
  actionLabel: string;
  actionLink: string;
}) {
  return (
    <div className="text-center py-12">
      <div className="text-5xl mb-4">{icon}</div>
      <h3 className="text-lg font-medium text-gray-900 mb-2">{title}</h3>
      <p className="text-gray-500 mb-6">{description}</p>
      <Link
        to={actionLink}
        className="inline-flex items-center px-6 py-3 bg-blue-600 text-white font-medium rounded-xl hover:bg-blue-700 transition"
      >
        {actionLabel} →
      </Link>
    </div>
  );
}

// 수강 카드
function EnrollmentCard({ enrollment }: { enrollment: any }) {
  const title = enrollment.lesson?.title || enrollment.lesson_title || '알 수 없는 강습';
  const sportType = enrollment.lesson?.sport_type || enrollment.lesson_sport_type;
  const difficulty = enrollment.lesson?.difficulty || enrollment.lesson_difficulty;
  const lessonId = enrollment.lesson?.id || enrollment.lesson_id;
  const statusConfig = STATUS_COLORS[enrollment.status] || STATUS_COLORS.enrolled;
  const sportIcon = SPORT_ICONS[sportType] || '🏃';

  return (
    <Link
      to={`/lessons/${lessonId}`}
      className="block bg-gray-50 rounded-xl p-5 hover:bg-gray-100 transition group"
    >
      <div className="flex items-center gap-4">
        {/* 아이콘 */}
        <div className="w-14 h-14 bg-white rounded-xl flex items-center justify-center text-3xl shadow-sm group-hover:scale-105 transition">
          {sportIcon}
        </div>

        {/* 정보 */}
        <div className="flex-1 min-w-0">
          <h3 className="font-bold text-gray-900 truncate">{title}</h3>
          <p className="text-sm text-gray-500">
            {SPORT_LABELS[sportType]} · {DIFFICULTY_LABELS[difficulty]}
          </p>
        </div>

        {/* 상태 & 출석률 */}
        <div className="text-right">
          <span className={`inline-flex items-center gap-1 px-3 py-1.5 rounded-full text-sm font-medium ${statusConfig.bg} ${statusConfig.text}`}>
            {statusConfig.icon} {ENROLLMENT_STATUS_LABELS[enrollment.status]}
          </span>
          <p className="text-xs text-gray-400 mt-2">
            출석률 <span className="font-medium text-gray-600">{enrollment.attendance_rate || 0}%</span>
          </p>
        </div>
      </div>

      {/* 진행률 바 */}
      {enrollment.status === 'in_progress' && (
        <div className="mt-4">
          <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-blue-500 to-purple-500 rounded-full transition-all"
              style={{ width: `${enrollment.attendance_rate || 0}%` }}
            />
          </div>
        </div>
      )}
    </Link>
  );
}

// 찜한 강습 카드
function LikedLessonCard({
  lesson,
  onUnlike,
}: {
  lesson: any;
  onUnlike: () => void;
}) {
  const thumbnailUrl = lesson.thumbnail_url ? `${API_BASE}${lesson.thumbnail_url}` : null;
  const sportIcon = SPORT_ICONS[lesson.sport_type] || '🏃';

  return (
    <div className="bg-gray-50 rounded-xl overflow-hidden group hover:shadow-md transition">
      <Link to={`/lessons/${lesson.id}`}>
        <div className="aspect-video bg-gray-200 relative overflow-hidden">
          {thumbnailUrl ? (
            <img src={thumbnailUrl} alt="" className="w-full h-full object-cover group-hover:scale-105 transition duration-300" />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-4xl bg-gradient-to-br from-gray-100 to-gray-200">
              {sportIcon}
            </div>
          )}
          <span className="absolute top-2 left-2 bg-blue-600 text-white text-xs px-2 py-1 rounded-lg">
            {SPORT_LABELS[lesson.sport_type]}
          </span>
        </div>
        <div className="p-4">
          <h3 className="font-bold text-gray-900 truncate">{lesson.title}</h3>
          <p className="text-sm text-gray-500 mt-1">
            {DIFFICULTY_LABELS[lesson.difficulty]} · {TARGET_LABELS[lesson.target_audience]}
          </p>
        </div>
      </Link>
      <div className="px-4 pb-4">
        <button
          onClick={(e) => {
            e.preventDefault();
            onUnlike();
          }}
          className="w-full py-2 text-sm text-red-500 hover:bg-red-50 rounded-lg transition"
        >
          ❤️ 찜 해제
        </button>
      </div>
    </div>
  );
}

// 추천 카드
function RecommendationCard({
  category,
  subtitle,
  item,
}: {
  category: string;
  subtitle: string;
  item: any;
}) {
  const thumbnailUrl = item.lesson.thumbnail_url ? `${API_BASE}${item.lesson.thumbnail_url}` : null;
  const sportIcon = SPORT_ICONS[item.lesson.sport_type] || '🏃';

  return (
    <div className="bg-gradient-to-r from-blue-50 to-purple-50 rounded-xl p-5">
      <div className="mb-4">
        <h3 className="font-bold text-lg text-gray-900">{category}</h3>
        <p className="text-sm text-gray-500">{subtitle}</p>
      </div>

      <Link
        to={`/lessons/${item.lesson.id}`}
        className="flex gap-4 bg-white rounded-xl p-4 hover:shadow-md transition"
      >
        {/* 썸네일 */}
        <div className="w-24 h-24 bg-gray-100 rounded-xl overflow-hidden flex-shrink-0">
          {thumbnailUrl ? (
            <img src={thumbnailUrl} alt="" className="w-full h-full object-cover" />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-3xl">
              {sportIcon}
            </div>
          )}
        </div>

        {/* 정보 */}
        <div className="flex-1 min-w-0">
          <h4 className="font-bold text-gray-900 mb-1">{item.lesson.title}</h4>
          <p className="text-sm text-gray-500 mb-2">
            {SPORT_LABELS[item.lesson.sport_type]} · {DIFFICULTY_LABELS[item.lesson.difficulty]}
          </p>
          <p className="text-sm text-blue-600 bg-blue-50 px-3 py-1.5 rounded-lg inline-block">
            💬 {item.reason}
          </p>
        </div>
      </Link>
    </div>
  );
}

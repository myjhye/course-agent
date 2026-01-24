import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { lessonApi, myRecommendationApi } from '../services/api';
import { SPORT_LABELS, DIFFICULTY_LABELS } from '../constants/labels';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const STUDENT_NAME = '홍길동';

const CATEGORIES = [
  { id: 'swimming', name: '수영', icon: '🏊', color: 'from-blue-400 to-cyan-400' },
  { id: 'tennis', name: '테니스', icon: '🎾', color: 'from-green-400 to-emerald-400' },
  { id: 'golf', name: '골프', icon: '⛳', color: 'from-emerald-400 to-teal-400' },
  { id: 'yoga', name: '요가', icon: '🧘', color: 'from-purple-400 to-pink-400' },
  { id: 'pilates', name: '필라테스', icon: '🤸', color: 'from-pink-400 to-rose-400' },
  { id: 'fitness', name: '피트니스', icon: '💪', color: 'from-orange-400 to-red-400' },
];

export default function HomePage() {
  const [popularLessons, setPopularLessons] = useState<any[]>([]);
  const [recommendations, setRecommendations] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [lessonsRes, recRes] = await Promise.all([
        lessonApi.getPublished({ page: 1, page_size: 8 }),
        myRecommendationApi.getCategorized(STUDENT_NAME).catch(() => ({ data: null }))
      ]);
      setPopularLessons(lessonsRes.data.items);
      setRecommendations(recRes.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      {/* 히어로 섹션 */}
      <section className="relative bg-gradient-to-br from-blue-600 via-purple-600 to-pink-500 text-white overflow-hidden">
        <div className="absolute inset-0 bg-black/20" />
        <div className="absolute inset-0">
          <div className="absolute top-20 left-10 w-72 h-72 bg-white/10 rounded-full blur-3xl" />
          <div className="absolute bottom-10 right-10 w-96 h-96 bg-purple-500/20 rounded-full blur-3xl" />
        </div>

        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24 md:py-32">
          <div className="max-w-2xl">
            <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold leading-tight mb-6">
              AI가 추천하는<br />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-yellow-200 to-pink-200">
                나만의 스포츠 강습
              </span>
            </h1>
            <p className="text-lg md:text-xl text-white/80 mb-8">
              수영, 테니스, 골프, 요가까지<br />
              당신의 건강한 라이프스타일을 위한 맞춤형 강습을 만나보세요.
            </p>
            <div className="flex flex-wrap gap-4">
              <Link
                to="/lessons"
                className="inline-flex items-center px-6 py-3 bg-white text-gray-900 font-semibold rounded-full hover:bg-gray-100 transition shadow-lg"
              >
                강습 둘러보기
                <svg className="ml-2 w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </Link>
              <Link
                to="/chat"
                className="inline-flex items-center px-6 py-3 bg-white/20 text-white font-semibold rounded-full hover:bg-white/30 transition backdrop-blur"
              >
                🤖 AI 상담받기
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* 카테고리 */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <h2 className="text-2xl font-bold text-gray-900 mb-8">종목별 강습</h2>
        <div className="grid grid-cols-3 md:grid-cols-6 gap-4">
          {CATEGORIES.map((cat) => (
            <Link
              key={cat.id}
              to={`/lessons?sport=${cat.id}`}
              className="group flex flex-col items-center p-4 bg-white rounded-2xl shadow-sm hover:shadow-md transition"
            >
              <div className={`w-16 h-16 bg-gradient-to-br ${cat.color} rounded-2xl flex items-center justify-center text-3xl mb-3 group-hover:scale-110 transition`}>
                {cat.icon}
              </div>
              <span className="text-sm font-medium text-gray-700">{cat.name}</span>
            </Link>
          ))}
        </div>
      </section>

      {/* 맞춤 추천 */}
      {recommendations && (recommendations.next_level || recommendations.new_sport || recommendations.interest_based) && (
        <section className="bg-gradient-to-r from-blue-50 to-purple-50 py-16">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex items-center justify-between mb-8">
              <div>
                <h2 className="text-2xl font-bold text-gray-900">✨ {STUDENT_NAME}님을 위한 추천</h2>
                <p className="text-gray-600 mt-1">AI가 분석한 맞춤형 강습 추천</p>
              </div>
              <Link to="/my/enrollments" className="text-blue-600 hover:text-blue-700 font-medium text-sm">
                전체 보기 →
              </Link>
            </div>

            <div className="grid md:grid-cols-3 gap-6">
              {recommendations.next_level && (
                <RecommendationCard
                  category="🎯 다음 단계"
                  item={recommendations.next_level}
                />
              )}
              {recommendations.new_sport && (
                <RecommendationCard
                  category="🌟 새로운 도전"
                  item={recommendations.new_sport}
                />
              )}
              {recommendations.interest_based && (
                <RecommendationCard
                  category="💡 관심 기반"
                  item={recommendations.interest_based}
                />
              )}
            </div>
          </div>
        </section>
      )}

      {/* 인기 강습 */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="flex items-center justify-between mb-8">
          <h2 className="text-2xl font-bold text-gray-900">🔥 인기 강습</h2>
          <Link to="/lessons" className="text-blue-600 hover:text-blue-700 font-medium text-sm">
            전체 보기 →
          </Link>
        </div>

        {loading ? (
          <div className="grid md:grid-cols-4 gap-6">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="bg-gray-200 rounded-2xl h-64 animate-pulse" />
            ))}
          </div>
        ) : (
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {popularLessons.slice(0, 4).map((lesson) => (
              <LessonCard key={lesson.id} lesson={lesson} />
            ))}
          </div>
        )}
      </section>

      {/* CTA */}
      <section className="bg-gray-900 text-white py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-3xl font-bold mb-4">지금 바로 시작하세요</h2>
          <p className="text-gray-400 mb-8 max-w-2xl mx-auto">
            AI가 당신에게 딱 맞는 강습을 추천해드립니다.<br />
            건강한 라이프스타일의 시작, Course Agent와 함께하세요.
          </p>
          <Link
            to="/chat"
            className="inline-flex items-center px-8 py-4 bg-gradient-to-r from-blue-500 to-purple-600 text-white font-semibold rounded-full hover:opacity-90 transition shadow-lg"
          >
            🤖 AI 상담 시작하기
          </Link>
        </div>
      </section>
    </div>
  );
}

function RecommendationCard({ category, item }: { category: string; item: any }) {
  const thumbnailUrl = item.lesson.thumbnail_url
    ? `${API_BASE}${item.lesson.thumbnail_url}`
    : null;

  return (
    <Link
      to={`/lessons/${item.lesson.id}`}
      className="bg-white rounded-2xl shadow-sm hover:shadow-lg transition overflow-hidden group"
    >
      <div className="aspect-video bg-gray-100 relative overflow-hidden">
        {thumbnailUrl ? (
          <img src={thumbnailUrl} alt="" className="w-full h-full object-cover group-hover:scale-105 transition duration-300" />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-4xl bg-gradient-to-br from-gray-100 to-gray-200">
            {item.lesson.sport_type === 'swimming' && '🏊'}
            {item.lesson.sport_type === 'tennis' && '🎾'}
            {item.lesson.sport_type === 'golf' && '⛳'}
            {item.lesson.sport_type === 'yoga' && '🧘'}
            {item.lesson.sport_type === 'pilates' && '🤸'}
            {item.lesson.sport_type === 'fitness' && '💪'}
          </div>
        )}
        <div className="absolute top-3 left-3 bg-white/90 backdrop-blur px-3 py-1 rounded-full text-sm font-medium">
          {category}
        </div>
      </div>
      <div className="p-4">
        <h3 className="font-bold text-gray-900 mb-1">{item.lesson.title}</h3>
        <p className="text-sm text-gray-500 mb-2">
          {SPORT_LABELS[item.lesson.sport_type]} · {DIFFICULTY_LABELS[item.lesson.difficulty]}
        </p>
        <p className="text-sm text-blue-600">{item.reason}</p>
      </div>
    </Link>
  );
}

function LessonCard({ lesson }: { lesson: any }) {
  const thumbnailUrl = lesson.active_content?.thumbnail_url
    ? `${API_BASE}${lesson.active_content.thumbnail_url}`
    : null;

  return (
    <Link
      to={`/lessons/${lesson.id}`}
      className="bg-white rounded-2xl shadow-sm hover:shadow-lg transition overflow-hidden group"
    >
      <div className="aspect-video bg-gray-100 relative overflow-hidden">
        {thumbnailUrl ? (
          <img src={thumbnailUrl} alt="" className="w-full h-full object-cover group-hover:scale-105 transition duration-300" />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-4xl bg-gradient-to-br from-gray-100 to-gray-200">
            {lesson.sport_type === 'swimming' && '🏊'}
            {lesson.sport_type === 'tennis' && '🎾'}
            {lesson.sport_type === 'golf' && '⛳'}
            {lesson.sport_type === 'yoga' && '🧘'}
            {lesson.sport_type === 'pilates' && '🤸'}
            {lesson.sport_type === 'fitness' && '💪'}
          </div>
        )}
        <div className="absolute top-3 left-3 bg-blue-600 text-white px-2 py-1 rounded-lg text-xs font-medium">
          {SPORT_LABELS[lesson.sport_type]}
        </div>
      </div>
      <div className="p-4">
        <h3 className="font-bold text-gray-900 mb-1 truncate">{lesson.title}</h3>
        <p className="text-sm text-gray-500">
          {DIFFICULTY_LABELS[lesson.difficulty]} · {lesson.instructor_name || '강사 미정'}
        </p>
      </div>
    </Link>
  );
}


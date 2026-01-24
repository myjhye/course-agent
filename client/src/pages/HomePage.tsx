import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { lessonApi, myRecommendationApi } from '../services/api';
import { SPORT_LABELS, DIFFICULTY_LABELS } from '../constants/labels';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const STUDENT_NAME = '홍길동';

const CATEGORIES = [
  { id: 'swimming', name: '수영', icon: '🏊', bg: 'bg-sky-100', iconBg: 'bg-sky-500' },
  { id: 'tennis', name: '테니스', icon: '🎾', bg: 'bg-lime-100', iconBg: 'bg-lime-500' },
  { id: 'golf', name: '골프', icon: '⛳', bg: 'bg-emerald-100', iconBg: 'bg-emerald-500' },
  { id: 'yoga', name: '요가', icon: '🧘', bg: 'bg-violet-100', iconBg: 'bg-violet-500' },
  { id: 'pilates', name: '필라테스', icon: '🤸', bg: 'bg-rose-100', iconBg: 'bg-rose-500' },
  { id: 'fitness', name: '피트니스', icon: '💪', bg: 'bg-amber-100', iconBg: 'bg-amber-500' },
];

// 종목별 색상 (밝은 배경 + 배지용 진한색)
const SPORT_COLORS: Record<string, { bg: string; badge: string }> = {
  swimming: { bg: 'bg-sky-50', badge: 'bg-sky-500' },
  tennis: { bg: 'bg-lime-50', badge: 'bg-lime-500' },
  golf: { bg: 'bg-emerald-50', badge: 'bg-emerald-500' },
  yoga: { bg: 'bg-violet-50', badge: 'bg-violet-500' },
  pilates: { bg: 'bg-rose-50', badge: 'bg-rose-500' },
  fitness: { bg: 'bg-amber-50', badge: 'bg-amber-500' },
};

export default function HomePage() {
  const [popularLessons, setPopularLessons] = useState<any[]>([]);
  const [recommendations, setRecommendations] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [recLoading, setRecLoading] = useState(true);

  useEffect(() => {
    loadLessons();
    loadRecommendations();
  }, []);

  const loadLessons = async () => {
    try {
      const res = await lessonApi.getPublished({ page: 1, page_size: 8 });
      setPopularLessons(res.data.items);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const loadRecommendations = async () => {
    try {
      const res = await myRecommendationApi.getCategorized(STUDENT_NAME);
      setRecommendations(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setRecLoading(false);
    }
  };

  const hasRecommendations = recommendations && 
    (recommendations.next_level || recommendations.new_sport || recommendations.interest_based);

  return (
    <div className="bg-gray-50">
      {/* 히어로 섹션 - 다크 모던 스타일 */}
      <section className="relative bg-gray-900 text-white overflow-hidden">
        {/* 배경 패턴 */}
        <div className="absolute inset-0 opacity-30">
          <div className="absolute top-0 left-1/4 w-[500px] h-[500px] bg-blue-600 rounded-full blur-[120px]" />
          <div className="absolute bottom-0 right-1/4 w-[400px] h-[400px] bg-indigo-600 rounded-full blur-[100px]" />
        </div>
        
        {/* 그리드 패턴 */}
        <div 
          className="absolute inset-0 opacity-[0.03]"
          style={{
            backgroundImage: `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='1'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")`
          }}
        />

        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20 md:py-28">
          <div className="max-w-3xl">
            <div className="inline-flex items-center gap-2 px-4 py-2 bg-white/10 backdrop-blur rounded-full text-sm mb-6">
              <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
              <span className="text-gray-300">AI 맞춤 추천 시스템</span>
            </div>
            
            <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold leading-[1.1] mb-6 tracking-tight">
              스포츠 강습,<br />
              <span className="text-blue-400">더 스마트하게</span> 시작하세요
            </h1>
            
            <p className="text-lg text-gray-400 mb-10 max-w-xl leading-relaxed">
              수영부터 요가까지, AI가 분석한 개인 맞춤형 강습 추천으로
              당신의 운동 목표를 더 빠르게 달성하세요.
            </p>
            
            <div className="flex flex-wrap gap-4">
              <Link
                to="/lessons"
                className="inline-flex items-center px-7 py-3.5 bg-white text-gray-900 font-semibold rounded-lg hover:bg-gray-100 transition-all shadow-lg shadow-white/10"
              >
                강습 둘러보기
                <svg className="ml-2 w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </Link>
              <Link
                to="/chat"
                className="inline-flex items-center px-7 py-3.5 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-500 transition-all"
              >
                <span className="mr-2">💬</span>
                AI 상담받기
              </Link>
            </div>
          </div>

          {/* 우측 플로팅 카드 (데스크탑) */}
          <div className="hidden lg:block absolute right-8 top-1/2 -translate-y-1/2 w-72">
            <div className="bg-white/10 backdrop-blur-xl rounded-2xl p-6 border border-white/20">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 bg-blue-500 rounded-xl flex items-center justify-center text-xl">🎯</div>
                <div>
                  <div className="text-sm text-gray-400">이번 주 추천</div>
                  <div className="font-semibold">맞춤 강습 3개</div>
                </div>
              </div>
              <div className="space-y-2">
                {['수영 중급반', '요가 입문', '테니스 기초'].map((item, i) => (
                  <div key={i} className="flex items-center gap-2 text-sm text-gray-300">
                    <span className="w-1.5 h-1.5 bg-blue-400 rounded-full" />
                    {item}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 카테고리 */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="flex items-center justify-between mb-8">
          <h2 className="text-2xl font-bold text-gray-900">종목별 강습</h2>
          <Link to="/lessons" className="text-sm text-gray-500 hover:text-gray-900 transition">
            전체 보기 →
          </Link>
        </div>
        <div className="grid grid-cols-3 md:grid-cols-6 gap-3 md:gap-4">
          {CATEGORIES.map((cat) => (
            <Link
              key={cat.id}
              to={`/lessons?sport=${cat.id}`}
              className={`group flex flex-col items-center p-5 ${cat.bg} rounded-xl border border-gray-100 hover:shadow-lg transition-all`}
            >
              <div className={`w-14 h-14 ${cat.iconBg} rounded-xl flex items-center justify-center text-2xl mb-3 group-hover:scale-110 transition-transform shadow-md`}>
                {cat.icon}
              </div>
              <span className="text-sm font-medium text-gray-700">{cat.name}</span>
            </Link>
          ))}
        </div>
      </section>

      {/* AI 맞춤 추천 */}
      <section className="border-y border-gray-200 bg-white py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between mb-8">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-indigo-100 rounded-xl flex items-center justify-center text-lg">✨</div>
              <div>
                <h2 className="text-2xl font-bold text-gray-900">{STUDENT_NAME}님 맞춤 추천</h2>
                <p className="text-sm text-gray-500">AI가 분석한 당신만을 위한 강습</p>
              </div>
            </div>
            <Link to="/my/enrollments" className="text-sm text-gray-500 hover:text-gray-900 transition">
              전체 보기 →
            </Link>
          </div>

          {recLoading ? (
            <div className="grid md:grid-cols-3 gap-6">
              {[1, 2, 3].map((i) => (
                <div key={i} className="bg-gray-100 rounded-xl h-72 animate-pulse" />
              ))}
            </div>
          ) : hasRecommendations ? (
            <div className="grid md:grid-cols-3 gap-6">
              {recommendations.next_level && (
                <RecommendationCard
                  category="다음 단계"
                  categoryIcon="🎯"
                  categoryColor="bg-blue-600"
                  item={recommendations.next_level}
                />
              )}
              {recommendations.new_sport && (
                <RecommendationCard
                  category="새로운 도전"
                  categoryIcon="🌟"
                  categoryColor="bg-amber-500"
                  item={recommendations.new_sport}
                />
              )}
              {recommendations.interest_based && (
                <RecommendationCard
                  category="관심 기반"
                  categoryIcon="💡"
                  categoryColor="bg-emerald-600"
                  item={recommendations.interest_based}
                />
              )}
            </div>
          ) : (
            <div className="text-center py-12 bg-gray-50 rounded-xl">
              <div className="text-4xl mb-3">🤖</div>
              <p className="text-gray-500">강습을 더 둘러보시면 맞춤 추천을 받을 수 있어요!</p>
              <Link to="/lessons" className="inline-block mt-4 text-blue-600 font-medium hover:underline">
                강습 보러가기 →
              </Link>
            </div>
          )}
        </div>
      </section>

      {/* 인기 강습 */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-orange-100 rounded-xl flex items-center justify-center text-lg">🔥</div>
            <h2 className="text-2xl font-bold text-gray-900">인기 강습</h2>
          </div>
          <Link to="/lessons" className="text-sm text-gray-500 hover:text-gray-900 transition">
            전체 보기 →
          </Link>
        </div>

        {loading ? (
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="bg-gray-200 rounded-xl h-64 animate-pulse" />
            ))}
          </div>
        ) : (
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5">
            {popularLessons.slice(0, 4).map((lesson, index) => (
              <LessonCard key={lesson.id} lesson={lesson} rank={index + 1} />
            ))}
          </div>
        )}
      </section>

      {/* CTA */}
      <section className="bg-gray-900 text-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
          <div className="flex flex-col md:flex-row items-center justify-between gap-8">
            <div>
              <h2 className="text-3xl font-bold mb-3">어떤 강습이 좋을지 고민되시나요?</h2>
              <p className="text-gray-400">
                AI 상담으로 나에게 딱 맞는 강습을 추천받아 보세요.
              </p>
            </div>
            <Link
              to="/chat"
              className="shrink-0 inline-flex items-center px-8 py-4 bg-white text-gray-900 font-semibold rounded-lg hover:bg-gray-100 transition-all"
            >
              <span className="mr-2">💬</span>
              AI 상담 시작하기
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}

function RecommendationCard({ 
  category, 
  categoryIcon, 
  categoryColor,
  item 
}: { 
  category: string; 
  categoryIcon: string;
  categoryColor: string;
  item: any;
}) {
  const thumbnailUrl = item.lesson.thumbnail_url
    ? `${API_BASE}${item.lesson.thumbnail_url}`
    : null;

  return (
    <Link
      to={`/lessons/${item.lesson.id}`}
      className="group bg-white rounded-xl border border-gray-200 hover:border-gray-300 hover:shadow-xl transition-all overflow-hidden"
    >
      <div className="aspect-[16/10] bg-gray-100 relative overflow-hidden">
        {thumbnailUrl ? (
          <img src={thumbnailUrl} alt="" className="w-full h-full object-cover group-hover:scale-105 transition duration-500" />
        ) : (
          <div className={`w-full h-full flex items-center justify-center text-5xl ${SPORT_COLORS[item.lesson.sport_type]?.bg || 'bg-gray-100'}`}>
            {item.lesson.sport_type === 'swimming' && '🏊'}
            {item.lesson.sport_type === 'tennis' && '🎾'}
            {item.lesson.sport_type === 'golf' && '⛳'}
            {item.lesson.sport_type === 'yoga' && '🧘'}
            {item.lesson.sport_type === 'pilates' && '🤸'}
            {item.lesson.sport_type === 'fitness' && '💪'}
          </div>
        )}
        <div className={`absolute top-3 left-3 ${categoryColor} text-white px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 shadow-md`}>
          <span>{categoryIcon}</span>
          {category}
        </div>
      </div>
      <div className="p-5">
        <h3 className="font-bold text-gray-900 mb-1 group-hover:text-blue-600 transition">{item.lesson.title}</h3>
        <p className="text-sm text-gray-500 mb-3">
          {SPORT_LABELS[item.lesson.sport_type]} · {DIFFICULTY_LABELS[item.lesson.difficulty]}
        </p>
        <div className="flex items-start gap-2 p-3 bg-gray-50 rounded-lg">
          <span className="text-blue-500 mt-0.5">💡</span>
          <p className="text-sm text-gray-600 leading-relaxed">{item.reason}</p>
        </div>
      </div>
    </Link>
  );
}

function LessonCard({ lesson, rank }: { lesson: any; rank: number }) {
  const thumbnailUrl = lesson.active_content?.thumbnail_url
    ? `${API_BASE}${lesson.active_content.thumbnail_url}`
    : null;

  return (
    <Link
      to={`/lessons/${lesson.id}`}
      className="group bg-white rounded-xl border border-gray-200 hover:border-gray-300 hover:shadow-xl transition-all overflow-hidden"
    >
      <div className="aspect-[16/10] bg-gray-100 relative overflow-hidden">
        {thumbnailUrl ? (
          <img src={thumbnailUrl} alt="" className="w-full h-full object-cover group-hover:scale-105 transition duration-500" />
        ) : (
          <div className={`w-full h-full flex items-center justify-center text-4xl ${SPORT_COLORS[lesson.sport_type]?.bg || 'bg-gray-100'}`}>
            {lesson.sport_type === 'swimming' && '🏊'}
            {lesson.sport_type === 'tennis' && '🎾'}
            {lesson.sport_type === 'golf' && '⛳'}
            {lesson.sport_type === 'yoga' && '🧘'}
            {lesson.sport_type === 'pilates' && '🤸'}
            {lesson.sport_type === 'fitness' && '💪'}
          </div>
        )}
        {/* 순위 배지 */}
        <div className="absolute top-3 left-3 w-8 h-8 bg-white/90 backdrop-blur text-gray-800 rounded-lg flex items-center justify-center text-sm font-bold shadow-md">
          {rank}
        </div>
        {/* 종목 배지 */}
        <div className={`absolute top-3 right-3 ${SPORT_COLORS[lesson.sport_type]?.badge || 'bg-gray-500'} text-white px-2.5 py-1 rounded-lg text-xs font-medium shadow-md`}>
          {SPORT_LABELS[lesson.sport_type]}
        </div>
      </div>
      <div className="p-4">
        <h3 className="font-bold text-gray-900 mb-1 truncate group-hover:text-blue-600 transition">{lesson.title}</h3>
        <p className="text-sm text-gray-500">
          {DIFFICULTY_LABELS[lesson.difficulty]} · {lesson.instructor_name || '강사 미정'}
        </p>
      </div>
    </Link>
  );
}

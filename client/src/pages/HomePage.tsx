import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { lessonApi, myRecommendationApi } from '../services/api';
import { SPORT_LABELS, DIFFICULTY_LABELS } from '../constants/labels';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const STUDENT_NAME = '홍길동';

const CATEGORIES = [
  { id: 'swimming', name: '수영', icon: 'pool', hoverBorder: 'hover:border-blue-200', hoverBg: 'hover:bg-blue-50/50', hoverText: 'group-hover:text-blue-600', hoverTextDark: 'group-hover:text-blue-800' },
  { id: 'yoga', name: '요가', icon: 'self_improvement', hoverBorder: 'hover:border-purple-200', hoverBg: 'hover:bg-purple-50/50', hoverText: 'group-hover:text-purple-600', hoverTextDark: 'group-hover:text-purple-800' },
  { id: 'tennis', name: '테니스', icon: 'sports_tennis', hoverBorder: 'hover:border-green-200', hoverBg: 'hover:bg-green-50/50', hoverText: 'group-hover:text-green-600', hoverTextDark: 'group-hover:text-green-800' },
  { id: 'pilates', name: '필라테스', icon: 'accessibility_new', hoverBorder: 'hover:border-rose-200', hoverBg: 'hover:bg-rose-50/50', hoverText: 'group-hover:text-rose-600', hoverTextDark: 'group-hover:text-rose-800' },
  { id: 'golf', name: '골프', icon: 'sports_golf', hoverBorder: 'hover:border-emerald-200', hoverBg: 'hover:bg-emerald-50/50', hoverText: 'group-hover:text-emerald-600', hoverTextDark: 'group-hover:text-emerald-800' },
  { id: 'fitness', name: '피트니스', icon: 'fitness_center', hoverBorder: 'hover:border-orange-200', hoverBg: 'hover:bg-orange-50/50', hoverText: 'group-hover:text-orange-600', hoverTextDark: 'group-hover:text-orange-800' },
];

// Sport type to Material Symbol icon mapping
const SPORT_ICONS: Record<string, string> = {
  swimming: 'pool',
  tennis: 'sports_tennis',
  golf: 'sports_golf',
  yoga: 'self_improvement',
  pilates: 'accessibility_new',
  fitness: 'fitness_center',
};

// Recommendation category styling
const REC_STYLES = {
  next_level: {
    label: '다음 단계',
    badge: 'bg-indigo-600',
    bubble: 'bg-blue-50 text-blue-800 border-blue-100',
    bubbleArrow: 'bg-blue-50 border-blue-100',
    icon: 'psychology',
  },
  new_sport: {
    label: '새로운 도전',
    badge: 'bg-emerald-600',
    bubble: 'bg-emerald-50 text-emerald-800 border-emerald-100',
    bubbleArrow: 'bg-emerald-50 border-emerald-100',
    icon: 'bolt',
  },
  interest_based: {
    label: '관심 기반',
    badge: 'bg-purple-600',
    bubble: 'bg-purple-50 text-purple-800 border-purple-100',
    bubbleArrow: 'bg-purple-50 border-purple-100',
    icon: 'favorite',
  },
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

  const recList = recommendations ? [
    { key: 'next_level', data: recommendations.next_level },
    { key: 'new_sport', data: recommendations.new_sport },
    { key: 'interest_based', data: recommendations.interest_based },
  ].filter(r => r.data) : [];

  return (
    <div className="bg-background-light text-[#111318] overflow-x-hidden">
      {/* Hero Section */}
      <section className="relative bg-navy w-full overflow-hidden">
        {/* Background Elements */}
        <div className="absolute inset-0 bg-grid-pattern opacity-20"></div>
        <div className="absolute -top-[20%] -right-[10%] w-[600px] h-[600px] bg-primary/30 rounded-full blur-[100px] pointer-events-none"></div>
        <div className="absolute bottom-[10%] -left-[10%] w-[400px] h-[400px] bg-purple-600/20 rounded-full blur-[80px] pointer-events-none"></div>

        <div className="max-w-[1280px] mx-auto px-4 sm:px-6 lg:px-8 py-20 lg:py-28 relative z-10">
          <div className="flex flex-col lg:flex-row items-center gap-12 lg:gap-20">
            {/* Text Content */}
            <div className="flex-1 text-center lg:text-left">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/10 border border-white/10 backdrop-blur-sm mb-6">
                <span className="material-symbols-outlined text-primary text-[18px]">temp_preferences_custom</span>
                <span className="text-xs font-medium text-white tracking-wide">AI 맞춤 추천 시스템</span>
              </div>

              <h1 className="text-4xl sm:text-5xl lg:text-6xl font-black text-white leading-[1.15] mb-6">
                스포츠 강습,<br />
                <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-indigo-400">더 스마트하게</span> 시작하세요
              </h1>

              <p className="text-slate-400 text-lg mb-8 max-w-lg mx-auto lg:mx-0 leading-relaxed">
                수영부터 요가까지, AI가 분석한 개인 맞춤형 강습 추천으로
                당신의 운동 목표를 더 빠르게 달성하세요.
              </p>

              <div className="flex flex-wrap items-center justify-center lg:justify-start gap-4">
                <Link
                  to="/chat"
                  className="h-12 px-8 rounded-xl bg-primary text-white font-bold hover:bg-blue-600 hover:shadow-glow transition-all duration-300 flex items-center gap-2"
                >
                  <span className="material-symbols-outlined text-[20px]">chat_bubble</span>
                  AI 상담
                </Link>
                <Link
                  to="/lessons"
                  className="h-12 px-8 rounded-xl bg-white/10 text-white font-bold border border-white/20 hover:bg-white/20 transition-all backdrop-blur-sm flex items-center"
                >
                  강습 둘러보기
                </Link>
              </div>
            </div>

            {/* Floating Visual - Shows first recommendation */}
            {recList.length > 0 && (
              <div className="w-full max-w-[380px] shrink-0 hidden lg:block">
                <Link
                  to={`/lessons/${recList[0].data.lesson.id}`}
                  className="relative block bg-slate-800/50 backdrop-blur-xl border border-slate-700 rounded-2xl p-5 shadow-2xl hover:border-slate-600 transition-colors"
                >
                  {/* Card Header */}
                  <div className="flex items-center justify-between mb-3 border-b border-slate-700/50 pb-3">
                    <div>
                      <h3 className="text-white font-bold text-base">이번 주 추천</h3>
                      <p className="text-slate-400 text-xs">{STUDENT_NAME}님의 최근 활동 기반</p>
                    </div>
                    <div className="size-9 rounded-full bg-primary/20 flex items-center justify-center text-primary animate-pulse">
                      <span className="material-symbols-outlined text-[20px]">recommend</span>
                    </div>
                  </div>

                  {/* Main Image */}
                  <div className="relative w-full aspect-[4/3] rounded-lg overflow-hidden mb-3 group">
                    <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent z-10"></div>
                    <div className="absolute bottom-3 left-3 z-20 flex items-center gap-2">
                      <span className={`px-2 py-1 ${REC_STYLES[recList[0].key as keyof typeof REC_STYLES].badge} text-white text-xs font-bold rounded-md`}>
                        {REC_STYLES[recList[0].key as keyof typeof REC_STYLES].label}
                      </span>
                      {recList[0].data.match_score && (
                        <span className="px-2 py-1 bg-white/90 text-slate-800 text-xs font-bold rounded-md">
                          {recList[0].data.match_score}% Match
                        </span>
                      )}
                    </div>
                    {recList[0].data.lesson.thumbnail_url ? (
                      <img
                        src={`${API_BASE}${recList[0].data.lesson.thumbnail_url}`}
                        alt=""
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <div className="w-full h-full bg-gradient-to-br from-blue-500/20 to-purple-500/20 flex items-center justify-center">
                        <span className="material-symbols-outlined text-6xl text-white/30">
                          {SPORT_ICONS[recList[0].data.lesson.sport_type] || 'sports'}
                        </span>
                      </div>
                    )}
                  </div>

                  {/* Card Details */}
                  <div className="space-y-2">
                    <div>
                      <h4 className="text-white font-bold text-sm">{recList[0].data.lesson.title}</h4>
                      <p className="text-slate-400 text-xs">{recList[0].data.lesson.instructor_name || '강사 미정'}</p>
                    </div>

                    {/* AI Insight Bubble */}
                    <div className="bg-primary/10 border border-primary/20 rounded-lg p-2.5 flex gap-2">
                      <span className="material-symbols-outlined text-primary shrink-0 text-[18px]">auto_awesome</span>
                      <p className="text-blue-200 text-[11px] leading-relaxed line-clamp-2">
                        "{recList[0].data.reason}"
                      </p>
                    </div>
                  </div>

                  {/* Decorative floating elements */}
                  <div className="absolute -z-10 -top-4 -right-4 w-20 h-20 bg-purple-500 rounded-2xl opacity-20 rotate-12"></div>
                  <div className="absolute -z-10 -bottom-6 -left-6 w-24 h-24 bg-blue-500 rounded-full opacity-20 blur-xl"></div>
                </Link>
              </div>
            )}
          </div>
        </div>
      </section>

      {/* Category Section */}
      <section className="py-16 bg-white">
        <div className="max-w-[960px] mx-auto px-4 sm:px-6">
          <div className="flex items-center justify-between mb-8">
            <h2 className="text-2xl font-bold text-[#111318]">종목별 강습</h2>
            <Link to="/lessons" className="text-sm font-medium text-primary hover:underline">
              전체 보기
            </Link>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-4">
            {CATEGORIES.map((cat) => (
              <Link
                key={cat.id}
                to={`/lessons?sport=${cat.id}`}
                className={`group flex flex-col items-center justify-center p-6 rounded-xl bg-slate-50 border border-slate-100 ${cat.hoverBorder} ${cat.hoverBg} hover:-translate-y-1 transition-all duration-300`}
              >
                <div className={`size-12 rounded-full bg-white shadow-sm flex items-center justify-center text-slate-700 ${cat.hoverText} group-hover:scale-110 transition-all mb-3`}>
                  <span className="material-symbols-outlined">{cat.icon}</span>
                </div>
                <span className={`text-sm font-bold text-slate-700 ${cat.hoverTextDark}`}>{cat.name}</span>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* AI Recommendations Section */}
      <section className="py-16 bg-background-light">
        <div className="max-w-[960px] mx-auto px-4 sm:px-6">
          <div className="flex items-center gap-2 mb-8">
            <span className="material-symbols-outlined text-primary text-2xl">auto_awesome</span>
            <h2 className="text-2xl font-bold text-[#111318]">{STUDENT_NAME}님 맞춤 추천</h2>
          </div>

          {recLoading ? (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {[1, 2, 3].map((i) => (
                <div key={i} className="bg-white rounded-xl h-80 animate-pulse shadow-sm border border-slate-200" />
              ))}
            </div>
          ) : hasRecommendations ? (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {recList.map(({ key, data }) => (
                <RecommendationCard
                  key={key}
                  type={key as keyof typeof REC_STYLES}
                  item={data}
                />
              ))}
            </div>
          ) : (
            <div className="text-center py-16 bg-white rounded-xl border border-slate-200">
              <span className="material-symbols-outlined text-6xl text-slate-300 mb-4">smart_toy</span>
              <p className="text-slate-500 mb-4">강습을 더 둘러보시면 맞춤 추천을 받을 수 있어요!</p>
              <Link
                to="/lessons"
                className="inline-flex items-center gap-2 text-primary font-medium hover:underline"
              >
                강습 보러가기
                <span className="material-symbols-outlined text-[18px]">arrow_forward</span>
              </Link>
            </div>
          )}
        </div>
      </section>

      {/* Popular Lessons Section */}
      <section className="py-16 bg-white">
        <div className="max-w-[960px] mx-auto px-4 sm:px-6">
          <h2 className="text-2xl font-bold text-[#111318] mb-8">인기 강습</h2>

          {loading ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="bg-slate-100 rounded-xl h-64 animate-pulse" />
              ))}
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
              {popularLessons.slice(0, 4).map((lesson, index) => (
                <PopularCard key={lesson.id} lesson={lesson} rank={index + 1} />
              ))}
            </div>
          )}
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 bg-[#111621] relative overflow-hidden">
        {/* Abstract Glows */}
        <div className="absolute top-0 left-1/4 w-[500px] h-[500px] bg-primary/20 rounded-full blur-[120px] pointer-events-none"></div>
        <div className="absolute bottom-0 right-1/4 w-[300px] h-[300px] bg-purple-600/20 rounded-full blur-[100px] pointer-events-none"></div>

        <div className="max-w-4xl mx-auto px-4 text-center relative z-10">
          <h2 className="text-3xl md:text-4xl font-black text-white mb-6">
            어떤 강습이 좋을지 고민되시나요?
          </h2>
          <p className="text-slate-400 text-lg mb-10 max-w-2xl mx-auto">
            AI 상담으로 나에게 딱 맞는 강습을 추천받아 보세요.
            라이프스타일, 체력 조건, 목표를 분석해 최적의 스포츠 활동을 제안해드립니다.
          </p>
          <Link
            to="/chat"
            className="group relative inline-flex items-center gap-3 px-8 py-4 bg-primary text-white text-lg font-bold rounded-xl overflow-hidden transition-all hover:bg-blue-600 hover:scale-105 shadow-glow"
          >
            <span className="relative z-10">AI 상담 시작하기</span>
            <span className="material-symbols-outlined relative z-10 transition-transform group-hover:translate-x-1">arrow_forward</span>
            {/* Button Shine Effect */}
            <div className="absolute inset-0 -translate-x-full group-hover:animate-shimmer bg-gradient-to-r from-transparent via-white/20 to-transparent z-0"></div>
          </Link>
        </div>
      </section>
    </div>
  );
}

function RecommendationCard({ type, item }: { type: keyof typeof REC_STYLES; item: any }) {
  const style = REC_STYLES[type];
  const thumbnailUrl = item.lesson.thumbnail_url
    ? `${API_BASE}${item.lesson.thumbnail_url}`
    : null;

  return (
    <Link
      to={`/lessons/${item.lesson.id}`}
      className="flex flex-col bg-white rounded-xl overflow-hidden shadow-sm border border-slate-200 hover:shadow-lg transition-shadow group"
    >
      <div className="relative h-40 bg-gray-200 overflow-hidden">
        <div className={`absolute top-3 left-3 ${style.badge} text-white text-[10px] uppercase font-bold px-2 py-1 rounded z-10`}>
          {style.label}
        </div>
        {thumbnailUrl ? (
          <img
            src={thumbnailUrl}
            alt=""
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
          />
        ) : (
          <div className="w-full h-full bg-gradient-to-br from-slate-100 to-slate-200 flex items-center justify-center group-hover:scale-105 transition-transform duration-500">
            <span className="material-symbols-outlined text-4xl text-slate-400">
              {SPORT_ICONS[item.lesson.sport_type] || 'sports'}
            </span>
          </div>
        )}
      </div>

      <div className="p-5 flex flex-col grow">
        {/* AI Reason Bubble */}
        <div className={`relative ${style.bubble} text-xs p-3 rounded-lg rounded-tl-none mb-3 border`}>
          <span className={`absolute -top-[6px] left-0 w-2 h-2 ${style.bubbleArrow} border-t border-l rotate-45`}></span>
          <div className="flex gap-2 items-start">
            <span className="material-symbols-outlined text-[14px] mt-0.5">{style.icon}</span>
            <span>{item.reason}</span>
          </div>
        </div>

        <h3 className="font-bold text-lg mb-1 group-hover:text-primary transition-colors">
          {item.lesson.title}
        </h3>
        <p className="text-slate-500 text-sm mb-4">
          {SPORT_LABELS[item.lesson.sport_type]} · {DIFFICULTY_LABELS[item.lesson.difficulty]}
        </p>

        <div className="mt-auto pt-4 border-t border-slate-100 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="size-6 rounded-full bg-gradient-to-br from-blue-400 to-purple-500 flex items-center justify-center">
              <span className="text-white text-[10px] font-medium">
                {item.lesson.instructor_name?.charAt(0) || '강'}
              </span>
            </div>
            <span className="text-xs font-medium text-slate-600">
              {item.lesson.instructor_name || '강사 미정'}
            </span>
          </div>
          {item.match_score && (
            <span className={`font-bold text-sm ${
              item.match_score >= 90 ? 'text-green-600' :
              item.match_score >= 80 ? 'text-blue-600' :
              item.match_score >= 70 ? 'text-indigo-600' :
              'text-slate-600'
            }`}>
              {item.match_score}% Match
            </span>
          )}
        </div>
      </div>
    </Link>
  );
}

function PopularCard({ lesson, rank }: { lesson: any; rank: number }) {
  const thumbnailUrl = lesson.active_content?.thumbnail_url
    ? `${API_BASE}${lesson.active_content.thumbnail_url}`
    : null;

  return (
    <Link to={`/lessons/${lesson.id}`} className="group block">
      <div className="relative rounded-xl overflow-hidden aspect-[4/3] mb-3 shadow-sm group-hover:shadow-md transition-shadow">
        {/* Ranking Badge */}
        <div className={`absolute top-2 left-2 z-10 size-8 ${rank === 1 ? 'bg-primary' : 'bg-slate-800'} text-white font-black text-lg flex items-center justify-center rounded-lg shadow-lg`}>
          {rank}
        </div>
        <div className="absolute inset-0 bg-black/10 group-hover:bg-transparent transition-colors z-0"></div>
        {thumbnailUrl ? (
          <img
            src={thumbnailUrl}
            alt=""
            className="w-full h-full object-cover transform group-hover:scale-110 transition-transform duration-700"
          />
        ) : (
          <div className="w-full h-full bg-gradient-to-br from-slate-100 to-slate-200 flex items-center justify-center transform group-hover:scale-110 transition-transform duration-700">
            <span className="material-symbols-outlined text-4xl text-slate-400">
              {SPORT_ICONS[lesson.sport_type] || 'sports'}
            </span>
          </div>
        )}
        <div className="absolute bottom-2 right-2 bg-black/60 backdrop-blur-sm px-2 py-0.5 rounded text-white text-xs">
          {DIFFICULTY_LABELS[lesson.difficulty]}
        </div>
      </div>
      <div>
        <div className="flex items-center gap-2 mb-1">
          <span className="text-xs font-bold text-primary uppercase tracking-wide">
            {SPORT_LABELS[lesson.sport_type]}
          </span>
        </div>
        <h3 className="font-bold text-[#111318] leading-tight mb-1 group-hover:text-primary transition-colors">
          {lesson.title}
        </h3>
        <p className="text-sm text-slate-500">
          {lesson.instructor_name || '강사 미정'}
        </p>
      </div>
    </Link>
  );
}

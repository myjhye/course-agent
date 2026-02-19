import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';

import { LessonDetail } from '../types';
import { lessonApi, myEnrollmentApi } from '../services/api';
import { DIFFICULTY_LABELS, SPORT_LABELS, TARGET_LABELS } from '../constants/labels';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const STUDENT_NAME = '홍길동';

// Material Symbols 아이콘 매핑
const SPORT_ICONS: Record<string, string> = {
  swimming: 'pool',
  tennis: 'sports_tennis',
  golf: 'sports_golf',
  yoga: 'self_improvement',
  pilates: 'accessibility_new',
  fitness: 'fitness_center',
  other: 'sports',
};

// 난이도별 스타일
const DIFFICULTY_STYLES: Record<string, { bg: string; text: string; border: string }> = {
  beginner: { bg: 'bg-green-500/10', text: 'text-green-400', border: 'border-green-500/20' },
  elementary: { bg: 'bg-blue-500/10', text: 'text-blue-400', border: 'border-blue-500/20' },
  intermediate: { bg: 'bg-yellow-500/10', text: 'text-yellow-400', border: 'border-yellow-500/20' },
  advanced: { bg: 'bg-orange-500/10', text: 'text-orange-400', border: 'border-orange-500/20' },
};

export default function LessonDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [lesson, setLesson] = useState<LessonDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [enrolling, setEnrolling] = useState(false);
  const [studentName, setStudentName] = useState('');
  const [showEnrollForm, setShowEnrollForm] = useState(false);
  const [liked, setLiked] = useState(false);
  const [activeTab, setActiveTab] = useState<'intro' | 'curriculum'>('intro');

  useEffect(() => {
    if (id) {
      loadLesson();
      recordView();
      checkLikeStatus();
    }
  }, [id]);

  const loadLesson = async () => {
    if (!id) return;
    try {
      const res = await lessonApi.getById(Number(id));
      setLesson(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const recordView = async () => {
    try {
      await lessonApi.recordView(Number(id), STUDENT_NAME);
    } catch (err) {
      // 무시
    }
  };

  const checkLikeStatus = async () => {
    try {
      const res = await lessonApi.getLikeStatus(Number(id), STUDENT_NAME);
      setLiked(res.data.liked);
    } catch (err) {
      // 무시
    }
  };

  const handleToggleLike = async () => {
    try {
      const res = await lessonApi.toggleLike(Number(id), STUDENT_NAME);
      setLiked(res.data.liked);
    } catch (err) {
      console.error(err);
    }
  };

  const handleEnroll = async () => {
    if (!id || !studentName.trim()) {
      alert('이름을 입력해주세요.');
      return;
    }

    setEnrolling(true);
    try {
      await myEnrollmentApi.create({
        lesson_id: Number(id),
        student_name: studentName.trim(),
      });
      alert('수강 신청이 완료되었습니다!');
      setShowEnrollForm(false);
      setStudentName('');
    } catch (err: any) {
      console.error(err);
      const errorDetail = err.response?.data?.detail || '';
      
      if (errorDetail.includes('DUPLICATE_ENROLLMENT')) {
        alert(`😊 ${studentName.trim()}님은 이미 이 강습을 수강 중이에요!\n\n내 수강 현황에서 확인해보세요.`);
      } else {
        alert(errorDetail || '수강 신청에 실패했습니다. 잠시 후 다시 시도해주세요.');
      }
    } finally {
      setEnrolling(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center bg-background-light">
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 border-4 border-primary border-t-transparent rounded-full animate-spin" />
          <p className="text-slate-500">강습 정보를 불러오는 중...</p>
        </div>
      </div>
    );
  }

  if (!lesson) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center bg-background-light">
        <div className="text-center">
          <span className="material-symbols-outlined text-6xl text-slate-300 mb-4">sentiment_dissatisfied</span>
          <p className="text-slate-500 mb-4">강습을 찾을 수 없습니다.</p>
          <Link
            to="/lessons"
            className="inline-flex items-center gap-2 text-primary hover:underline font-medium"
          >
            <span className="material-symbols-outlined text-[18px]">arrow_back</span>
            강습 목록으로 돌아가기
          </Link>
        </div>
      </div>
    );
  }

  const content = lesson.active_content;
  const thumbnailUrl = content?.thumbnail_url
    ? content.thumbnail_url.startsWith('http')
      ? content.thumbnail_url
      : `${API_BASE}${content.thumbnail_url}`
    : null;
  const sportIcon = SPORT_ICONS[lesson.sport_type] || 'sports';
  const difficultyStyle = DIFFICULTY_STYLES[lesson.difficulty] || { bg: 'bg-slate-500/10', text: 'text-slate-400', border: 'border-slate-500/20' };

  return (
    <div className="bg-background-light min-h-screen">
      {/* Hero Section */}
      <div className="relative bg-navy border-b border-slate-800 pt-8 pb-12">
        {/* Background Gradient */}
        <div className="absolute inset-0 bg-gradient-to-b from-slate-900 to-navy opacity-90 pointer-events-none"></div>
        {/* Abstract Glow */}
        <div className="absolute -top-24 right-0 w-[500px] h-[500px] bg-primary/10 rounded-full blur-[100px] pointer-events-none"></div>

        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          {/* Breadcrumbs */}
          <nav className="flex mb-6 text-sm font-medium text-slate-400">
            <ol className="flex items-center space-x-2">
              <li><Link to="/" className="hover:text-primary transition-colors">홈</Link></li>
              <li><span className="text-slate-600">/</span></li>
              <li><Link to="/lessons" className="hover:text-primary transition-colors">강습</Link></li>
              <li><span className="text-slate-600">/</span></li>
              <li className="text-white">{SPORT_LABELS[lesson.sport_type]}</li>
            </ol>
          </nav>

          <div className="grid lg:grid-cols-12 gap-8 items-start">
            {/* Left: Thumbnail (7 cols) */}
            <div className="lg:col-span-7 w-full">
              <div className="relative aspect-video w-full rounded-xl overflow-hidden shadow-2xl ring-1 ring-white/10 bg-slate-900">
                {thumbnailUrl ? (
                  <img
                    src={thumbnailUrl}
                    alt={lesson.title}
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <div className="absolute inset-0 bg-gradient-to-br from-slate-800 to-slate-900 flex items-center justify-center">
                    <span className="material-symbols-outlined text-[120px] text-slate-600">{sportIcon}</span>
                  </div>
                )}
              </div>
            </div>

            {/* Right: Info (5 cols) */}
            <div className="lg:col-span-5 flex flex-col justify-center h-full space-y-6">
              {/* Badges */}
              <div className="flex flex-wrap gap-2">
                <span className="px-3 py-1 rounded-full bg-primary/20 text-primary text-xs font-bold border border-primary/20 flex items-center gap-1">
                  <span className="material-symbols-outlined text-sm">{sportIcon}</span>
                  {SPORT_LABELS[lesson.sport_type]}
                </span>
                <span className={`px-3 py-1 rounded-full ${difficultyStyle.bg} ${difficultyStyle.text} text-xs font-bold border ${difficultyStyle.border}`}>
                  {DIFFICULTY_LABELS[lesson.difficulty]}
                </span>
                <span className="px-3 py-1 rounded-full bg-purple-500/10 text-purple-400 text-xs font-bold border border-purple-500/20">
                  {TARGET_LABELS[lesson.target_audience]}
                </span>
              </div>

              {/* Title */}
              <h1 className="text-3xl md:text-4xl lg:text-5xl font-bold text-white leading-tight">
                {lesson.title}
              </h1>

              {/* Instructor */}
              {lesson.instructor_name && (
                <div className="flex items-center gap-4 pt-2">
                  <div className="relative">
                    <div className="h-12 w-12 rounded-full p-[2px] bg-gradient-to-tr from-primary via-purple-500 to-orange-400">
                      <div className="rounded-full h-full w-full bg-navy flex items-center justify-center text-white font-bold">
                        {lesson.instructor_name.charAt(0)}
                      </div>
                    </div>
                    <div className="absolute -bottom-1 -right-1 bg-primary text-white text-[10px] font-bold px-1.5 py-0.5 rounded border border-navy">
                      PRO
                    </div>
                  </div>
                  <div>
                    <p className="text-white font-semibold">{lesson.instructor_name}</p>
                    <p className="text-slate-400 text-sm">전문 강사</p>
                  </div>
                </div>
              )}

              {/* Mobile Action Buttons */}
              <div className="lg:hidden flex gap-3 pt-4 border-t border-slate-800">
                <button
                  onClick={handleToggleLike}
                  className={`flex items-center gap-2 px-4 py-3 rounded-xl font-medium transition ${
                    liked
                      ? 'bg-red-500 text-white'
                      : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                  }`}
                >
                  {liked ? '❤️ 찜했어요!' : '🤍 찜하기'}
                </button>
                <button
                  onClick={() => setShowEnrollForm(true)}
                  className="flex-1 bg-gradient-to-r from-blue-500 to-purple-600 text-white px-6 py-3 rounded-xl font-bold hover:opacity-90 transition shadow-lg"
                >
                  수강 신청하기
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Content Area */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid lg:grid-cols-12 gap-10">
          {/* Left Column: Tabs & Content (8 Cols) */}
          <div className="lg:col-span-8 space-y-10">
            {/* Tabs */}
            <div className="border-b border-slate-200">
              <nav className="-mb-px flex space-x-8">
                <button
                  onClick={() => setActiveTab('intro')}
                  className={`whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm flex items-center gap-2 transition-colors ${
                    activeTab === 'intro'
                      ? 'border-primary text-primary'
                      : 'border-transparent text-slate-500 hover:text-slate-700'
                  }`}
                >
                  <span className="material-symbols-outlined text-lg">description</span>
                  강습 소개
                </button>
                <button
                  onClick={() => setActiveTab('curriculum')}
                  className={`whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm flex items-center gap-2 transition-colors ${
                    activeTab === 'curriculum'
                      ? 'border-primary text-primary'
                      : 'border-transparent text-slate-500 hover:text-slate-700'
                  }`}
                >
                  <span className="material-symbols-outlined text-lg">school</span>
                  커리큘럼
                </button>
              </nav>
            </div>

            {/* Tab Content */}
            {activeTab === 'intro' && (
              <div className="prose prose-lg max-w-none text-slate-600">
                {content?.introduction ? (
                  <>
                    <h3 className="text-2xl font-bold text-slate-900 mb-4">강습 소개</h3>
                    <p className="leading-relaxed whitespace-pre-line">{content.introduction}</p>
                  </>
                ) : (
                  <div className="text-center py-12 text-slate-400">
                    <span className="material-symbols-outlined text-5xl mb-3">edit_note</span>
                    <p>아직 소개가 작성되지 않았습니다.</p>
                  </div>
                )}
              </div>
            )}

            {activeTab === 'curriculum' && (
              <div>
                <h3 className="text-2xl font-bold text-slate-900 mb-6">커리큘럼</h3>
                {content?.curriculum?.weeks && content.curriculum.weeks.length > 0 ? (
                  <div className="space-y-4">
                    {content.curriculum.weeks.map((week) => (
                      <div
                        key={week.week}
                        className="bg-white border border-slate-200 rounded-xl overflow-hidden"
                      >
                        <div className="p-5 flex items-center justify-between cursor-pointer hover:bg-slate-50 transition-colors">
                          <div className="flex items-center gap-4">
                            <div className="flex items-center justify-center h-10 w-10 rounded-full bg-primary/10 text-primary font-bold">
                              {week.week}
                            </div>
                            <div>
                              <h4 className="font-bold text-slate-900">{week.title}</h4>
                              <p className="text-sm text-slate-500">{week.topics?.length || 0}개 주제</p>
                            </div>
                          </div>
                          <span className="material-symbols-outlined text-slate-400">expand_more</span>
                        </div>
                        {week.topics && week.topics.length > 0 && (
                          <div className="px-5 pb-5 pl-[4.5rem]">
                            <div className="space-y-3">
                              {week.topics.map((topic, i) => (
                                <div key={i} className="flex items-center gap-3 text-sm text-slate-600">
                                  <span className="material-symbols-outlined text-primary text-base">check_circle</span>
                                  <span>{topic}</span>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-12 text-slate-400">
                    <span className="material-symbols-outlined text-5xl mb-3">menu_book</span>
                    <p>아직 커리큘럼이 작성되지 않았습니다.</p>
                  </div>
                )}
              </div>
            )}

            {/* Lesson Summary Card */}
            <div className="bg-white border border-slate-200 rounded-2xl p-6">
              <h3 className="text-lg font-bold text-slate-900 mb-6">강습 정보</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
                <div className="flex flex-col items-center text-center gap-2">
                  <div className="text-primary bg-primary/10 w-10 h-10 rounded-full flex items-center justify-center">
                    <span className="material-symbols-outlined">{sportIcon}</span>
                  </div>
                  <p className="text-xs text-slate-500 uppercase font-semibold">종목</p>
                  <p className="font-medium text-slate-900">{SPORT_LABELS[lesson.sport_type]}</p>
                </div>
                <div className="flex flex-col items-center text-center gap-2">
                  <div className="text-orange-500 bg-orange-500/10 w-10 h-10 rounded-full flex items-center justify-center">
                    <span className="material-symbols-outlined">signal_cellular_alt</span>
                  </div>
                  <p className="text-xs text-slate-500 uppercase font-semibold">난이도</p>
                  <p className="font-medium text-slate-900">{DIFFICULTY_LABELS[lesson.difficulty]}</p>
                </div>
                <div className="flex flex-col items-center text-center gap-2">
                  <div className="text-purple-500 bg-purple-500/10 w-10 h-10 rounded-full flex items-center justify-center">
                    <span className="material-symbols-outlined">groups</span>
                  </div>
                  <p className="text-xs text-slate-500 uppercase font-semibold">대상</p>
                  <p className="font-medium text-slate-900">{TARGET_LABELS[lesson.target_audience]}</p>
                </div>
                <div className="flex flex-col items-center text-center gap-2">
                  <div className="text-blue-500 bg-blue-500/10 w-10 h-10 rounded-full flex items-center justify-center">
                    <span className="material-symbols-outlined">calendar_today</span>
                  </div>
                  <p className="text-xs text-slate-500 uppercase font-semibold">기간</p>
                  <p className="font-medium text-slate-900">{content?.curriculum?.weeks?.length || 0}주</p>
                </div>
              </div>
            </div>
          </div>

          {/* Right Column: Sticky Enrollment (4 Cols) */}
          <div className="lg:col-span-4 relative hidden lg:block">
            <div className="sticky top-28 space-y-6">
              {/* Enrollment Card */}
              <div className="bg-white border border-slate-200 rounded-2xl overflow-hidden shadow-xl">
                {/* Gradient Header */}
                <div className="bg-gradient-to-r from-primary to-purple-600 p-6 text-white relative overflow-hidden">
                  <div className="absolute inset-0 opacity-10" style={{ backgroundImage: "url('data:image/svg+xml,%3Csvg width=\"20\" height=\"20\" viewBox=\"0 0 20 20\" xmlns=\"http://www.w3.org/2000/svg\"%3E%3Cg fill=\"%23ffffff\" fill-opacity=\"0.4\" fill-rule=\"evenodd\"%3E%3Ccircle cx=\"3\" cy=\"3\" r=\"1\"/%3E%3C/g%3E%3C/svg%3E')" }}></div>
                  <h3 className="text-lg font-bold relative z-10">강습 신청</h3>
                  <p className="text-sm text-blue-100 relative z-10">{lesson.title}</p>
                </div>

                <div className="p-6">
                  {/* Action Buttons */}
                  {!showEnrollForm ? (
                    <div className="space-y-3">
                      {/* 찜하기 버튼 */}
                      <button
                        onClick={handleToggleLike}
                        className={`w-full flex items-center justify-center gap-2 py-3 rounded-xl font-medium transition ${
                          liked
                            ? 'bg-red-50 text-red-600 border-2 border-red-200'
                            : 'bg-slate-50 text-slate-600 border-2 border-slate-200 hover:border-slate-300'
                        }`}
                      >
                        {liked ? '❤️ 찜했어요!' : '🤍 찜하기'}
                      </button>
                      {/* 수강 신청 버튼 */}
                      <button
                        onClick={() => setShowEnrollForm(true)}
                        className="w-full bg-gradient-to-r from-blue-500 to-purple-600 text-white py-4 rounded-xl font-bold text-lg hover:opacity-90 transition shadow-lg"
                      >
                        수강 신청하기
                      </button>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      <div>
                        <label className="block text-sm font-medium text-slate-700 mb-1">수강생 이름</label>
                        <input
                          type="text"
                          value={studentName}
                          onChange={(e) => setStudentName(e.target.value)}
                          placeholder="이름을 입력하세요"
                          className="w-full rounded-lg border-slate-300 bg-slate-50 focus:ring-primary focus:border-primary"
                        />
                      </div>
                      <button
                        onClick={handleEnroll}
                        disabled={enrolling}
                        className="w-full bg-primary hover:bg-blue-600 text-white font-bold py-3 rounded-xl transition disabled:opacity-50"
                      >
                        {enrolling ? '신청 중...' : '신청 완료하기'}
                      </button>
                      <button
                        onClick={() => {
                          setShowEnrollForm(false);
                          setStudentName('');
                        }}
                        className="w-full text-slate-500 hover:text-slate-700 text-sm"
                      >
                        취소
                      </button>
                    </div>
                  )}

                  <div className="my-6 h-px bg-slate-200"></div>

                  {/* Benefits */}
                  <ul className="space-y-3">
                    <li className="flex items-start gap-3 text-sm text-slate-600">
                      <span className="material-symbols-outlined text-green-500 text-lg shrink-0">check</span>
                      <span>수강 신청 후 바로 시작 가능</span>
                    </li>
                    <li className="flex items-start gap-3 text-sm text-slate-600">
                      <span className="material-symbols-outlined text-green-500 text-lg shrink-0">check</span>
                      <span><strong>전문 강사</strong>의 1:1 피드백</span>
                    </li>
                    <li className="flex items-start gap-3 text-sm text-slate-600">
                      <span className="material-symbols-outlined text-green-500 text-lg shrink-0">check</span>
                      <span>AI 기반 맞춤형 학습 추천</span>
                    </li>
                    <li className="flex items-start gap-3 text-sm text-slate-600">
                      <span className="material-symbols-outlined text-green-500 text-lg shrink-0">check</span>
                      <span>수료증 발급</span>
                    </li>
                  </ul>
                </div>

                <div className="bg-slate-50 px-6 py-4 border-t border-slate-200 flex items-center justify-between text-xs text-slate-500">
                  <div className="flex items-center gap-1">
                    <span className="material-symbols-outlined text-sm">verified_user</span>
                    안심 수강 보장
                  </div>
                  <div>안전한 결제</div>
                </div>
              </div>

              {/* AI Help Card */}
              <Link
                to="/chat"
                className="bg-gradient-to-br from-navy to-slate-800 border border-slate-700 rounded-2xl p-5 flex items-center gap-4 hover:border-slate-600 transition-colors"
              >
                <div className="h-10 w-10 rounded-full bg-blue-500/20 text-blue-400 flex items-center justify-center shrink-0">
                  <span className="material-symbols-outlined">smart_toy</span>
                </div>
                <div>
                  <p className="text-sm font-bold text-white">도움이 필요하신가요?</p>
                  <p className="text-xs text-slate-400">AI 상담으로 맞춤 추천을 받아보세요.</p>
                </div>
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* Mobile Enrollment Modal */}
      {showEnrollForm && (
        <div className="lg:hidden fixed inset-0 bg-black/50 z-50 flex items-end">
          <div className="bg-white w-full rounded-t-3xl p-6 animate-slide-up">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-bold">수강 신청</h3>
              <button
                onClick={() => {
                  setShowEnrollForm(false);
                  setStudentName('');
                }}
                className="text-slate-400 hover:text-slate-600"
              >
                <span className="material-symbols-outlined text-2xl">close</span>
              </button>
            </div>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  수강생 이름
                </label>
                <input
                  type="text"
                  value={studentName}
                  onChange={(e) => setStudentName(e.target.value)}
                  placeholder="이름을 입력하세요"
                  className="w-full border-2 border-slate-200 rounded-xl px-4 py-3 focus:ring-2 focus:ring-primary focus:border-transparent"
                />
              </div>
              <button
                onClick={handleEnroll}
                disabled={enrolling}
                className="w-full bg-gradient-to-r from-primary to-purple-600 text-white py-4 rounded-xl font-bold hover:opacity-90 disabled:opacity-50"
              >
                {enrolling ? '신청 중...' : '신청 완료하기'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

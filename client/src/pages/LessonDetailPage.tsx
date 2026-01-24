import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';

import { LessonDetail } from '../types';
import { lessonApi, myEnrollmentApi } from '../services/api';
import { DIFFICULTY_LABELS, SPORT_LABELS, TARGET_LABELS } from '../constants/labels';

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

// 난이도별 색상
const DIFFICULTY_COLORS: Record<string, string> = {
  beginner: 'bg-green-100 text-green-700',
  elementary: 'bg-blue-100 text-blue-700',
  intermediate: 'bg-yellow-100 text-yellow-700',
  advanced: 'bg-red-100 text-red-700',
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
      alert(err.response?.data?.detail || '수강 신청에 실패했습니다.');
    } finally {
      setEnrolling(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
          <p className="text-gray-500">강습 정보를 불러오는 중...</p>
        </div>
      </div>
    );
  }

  if (!lesson) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <div className="text-center">
          <div className="text-6xl mb-4">😢</div>
          <p className="text-gray-500 mb-4">강습을 찾을 수 없습니다.</p>
          <Link
            to="/lessons"
            className="inline-flex items-center text-blue-600 hover:text-blue-700 font-medium"
          >
            ← 강습 목록으로 돌아가기
          </Link>
        </div>
      </div>
    );
  }

  const content = lesson.active_content;
  const thumbnailUrl = content?.thumbnail_url
    ? `${API_BASE}${content.thumbnail_url}`
    : null;
  const sportIcon = SPORT_ICONS[lesson.sport_type] || '🏃';
  const difficultyColor = DIFFICULTY_COLORS[lesson.difficulty] || 'bg-gray-100 text-gray-700';

  return (
    <div className="bg-gray-50 min-h-screen">
      {/* 히어로 섹션 */}
      <div className="bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 text-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {/* 브레드크럼 */}
          <nav className="flex items-center gap-2 text-sm text-gray-400 mb-6">
            <Link to="/" className="hover:text-white transition">홈</Link>
            <span>›</span>
            <Link to="/lessons" className="hover:text-white transition">강습</Link>
            <span>›</span>
            <span className="text-gray-300">{SPORT_LABELS[lesson.sport_type]}</span>
          </nav>

          <div className="grid lg:grid-cols-2 gap-8 items-center">
            {/* 썸네일 */}
            <div className="aspect-video rounded-2xl overflow-hidden bg-gray-700 shadow-2xl">
              {thumbnailUrl ? (
                <img
                  src={thumbnailUrl}
                  alt={lesson.title}
                  className="w-full h-full object-cover"
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center text-8xl bg-gradient-to-br from-gray-700 to-gray-800">
                  {sportIcon}
                </div>
              )}
            </div>

            {/* 기본 정보 */}
            <div>
              {/* 뱃지 */}
              <div className="flex flex-wrap gap-2 mb-4">
                <span className="bg-blue-600 text-white text-sm px-3 py-1 rounded-full font-medium">
                  {sportIcon} {SPORT_LABELS[lesson.sport_type]}
                </span>
                <span className={`text-sm px-3 py-1 rounded-full font-medium ${difficultyColor}`}>
                  {DIFFICULTY_LABELS[lesson.difficulty]}
                </span>
                <span className="bg-gray-700 text-gray-300 text-sm px-3 py-1 rounded-full">
                  {TARGET_LABELS[lesson.target_audience]}
                </span>
              </div>

              {/* 제목 */}
              <h1 className="text-3xl lg:text-4xl font-bold mb-4 leading-tight">
                {lesson.title}
              </h1>

              {/* 강사 정보 */}
              {lesson.instructor_name && (
                <div className="flex items-center gap-3 mb-6">
                  <div className="w-12 h-12 bg-gradient-to-br from-blue-400 to-purple-500 rounded-full flex items-center justify-center text-white font-bold text-lg">
                    {lesson.instructor_name.charAt(0)}
                  </div>
                  <div>
                    <p className="font-medium">{lesson.instructor_name}</p>
                    <p className="text-sm text-gray-400">전문 강사</p>
                  </div>
                </div>
              )}

              {/* 액션 버튼 (모바일) */}
              <div className="lg:hidden flex gap-3">
                <button
                  onClick={handleToggleLike}
                  className={`flex items-center gap-2 px-4 py-3 rounded-xl font-medium transition ${
                    liked
                      ? 'bg-red-500 text-white'
                      : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                  }`}
                >
                  {liked ? '❤️' : '🤍'} 찜하기
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

      {/* 메인 콘텐츠 */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid lg:grid-cols-3 gap-8">
          {/* 왼쪽: 콘텐츠 영역 */}
          <div className="lg:col-span-2 space-y-6">
            {/* 탭 네비게이션 */}
            <div className="bg-white rounded-2xl shadow-sm overflow-hidden">
              <div className="flex border-b">
                <button
                  onClick={() => setActiveTab('intro')}
                  className={`flex-1 py-4 text-center font-medium transition ${
                    activeTab === 'intro'
                      ? 'text-blue-600 border-b-2 border-blue-600 bg-blue-50/50'
                      : 'text-gray-500 hover:text-gray-700 hover:bg-gray-50'
                  }`}
                >
                  📖 강습 소개
                </button>
                <button
                  onClick={() => setActiveTab('curriculum')}
                  className={`flex-1 py-4 text-center font-medium transition ${
                    activeTab === 'curriculum'
                      ? 'text-blue-600 border-b-2 border-blue-600 bg-blue-50/50'
                      : 'text-gray-500 hover:text-gray-700 hover:bg-gray-50'
                  }`}
                >
                  📋 커리큘럼
                </button>
              </div>

              {/* 탭 콘텐츠 */}
              <div className="p-6">
                {activeTab === 'intro' && (
                  <div>
                    {content?.introduction ? (
                      <div className="prose prose-gray max-w-none">
                        <p className="text-gray-700 leading-relaxed whitespace-pre-line text-lg">
                          {content.introduction}
                        </p>
                      </div>
                    ) : (
                      <div className="text-center py-12 text-gray-400">
                        <div className="text-4xl mb-3">📝</div>
                        <p>아직 소개가 작성되지 않았습니다.</p>
                      </div>
                    )}
                  </div>
                )}

                {activeTab === 'curriculum' && (
                  <div>
                    {content?.curriculum?.weeks && content.curriculum.weeks.length > 0 ? (
                      <div className="space-y-4">
                        {content.curriculum.weeks.map((week, index) => (
                          <div
                            key={week.week}
                            className="bg-gray-50 rounded-xl p-5 hover:bg-gray-100 transition"
                          >
                            <div className="flex items-start gap-4">
                              <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl flex items-center justify-center text-white font-bold shrink-0">
                                {week.week}
                              </div>
                              <div className="flex-1">
                                <h3 className="font-bold text-gray-900 text-lg mb-2">
                                  {week.title}
                                </h3>
                                {week.topics && week.topics.length > 0 && (
                                  <ul className="space-y-2">
                                    {week.topics.map((topic, i) => (
                                      <li key={i} className="flex items-start gap-2 text-gray-600">
                                        <span className="text-blue-500 mt-1">✓</span>
                                        <span>{topic}</span>
                                      </li>
                                    ))}
                                  </ul>
                                )}
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="text-center py-12 text-gray-400">
                        <div className="text-4xl mb-3">📚</div>
                        <p>아직 커리큘럼이 작성되지 않았습니다.</p>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>

            {/* 강습 정보 요약 */}
            <div className="bg-white rounded-2xl shadow-sm p-6">
              <h2 className="font-bold text-gray-900 mb-4">강습 정보</h2>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="text-center p-4 bg-gray-50 rounded-xl">
                  <div className="text-2xl mb-1">{sportIcon}</div>
                  <div className="text-sm text-gray-500">종목</div>
                  <div className="font-medium">{SPORT_LABELS[lesson.sport_type]}</div>
                </div>
                <div className="text-center p-4 bg-gray-50 rounded-xl">
                  <div className="text-2xl mb-1">📊</div>
                  <div className="text-sm text-gray-500">난이도</div>
                  <div className="font-medium">{DIFFICULTY_LABELS[lesson.difficulty]}</div>
                </div>
                <div className="text-center p-4 bg-gray-50 rounded-xl">
                  <div className="text-2xl mb-1">👥</div>
                  <div className="text-sm text-gray-500">대상</div>
                  <div className="font-medium">{TARGET_LABELS[lesson.target_audience]}</div>
                </div>
                <div className="text-center p-4 bg-gray-50 rounded-xl">
                  <div className="text-2xl mb-1">📅</div>
                  <div className="text-sm text-gray-500">기간</div>
                  <div className="font-medium">
                    {content?.curriculum?.weeks?.length || 0}주
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* 오른쪽: 수강 신청 카드 (Sticky) */}
          <div className="hidden lg:block">
            <div className="sticky top-24">
              <div className="bg-white rounded-2xl shadow-lg overflow-hidden">
                {/* 카드 헤더 */}
                <div className="bg-gradient-to-r from-blue-600 to-purple-600 p-6 text-white">
                  <div className="text-sm opacity-80 mb-1">강습 신청</div>
                  <div className="text-2xl font-bold">{lesson.title}</div>
                </div>

                {/* 카드 바디 */}
                <div className="p-6">
                  {/* 찜하기 */}
                  <button
                    onClick={handleToggleLike}
                    className={`w-full flex items-center justify-center gap-2 py-3 rounded-xl font-medium mb-4 transition ${
                      liked
                        ? 'bg-red-50 text-red-600 border-2 border-red-200'
                        : 'bg-gray-50 text-gray-600 border-2 border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    {liked ? '❤️ 찜했어요!' : '🤍 찜하기'}
                  </button>

                  {/* 수강 신청 */}
                  {!showEnrollForm ? (
                    <button
                      onClick={() => setShowEnrollForm(true)}
                      className="w-full bg-gradient-to-r from-blue-500 to-purple-600 text-white py-4 rounded-xl font-bold text-lg hover:opacity-90 transition shadow-lg"
                    >
                      수강 신청하기
                    </button>
                  ) : (
                    <div className="space-y-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          수강생 이름
                        </label>
                        <input
                          type="text"
                          value={studentName}
                          onChange={(e) => setStudentName(e.target.value)}
                          placeholder="이름을 입력하세요"
                          className="w-full border-2 border-gray-200 rounded-xl px-4 py-3 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition"
                        />
                      </div>
                      <button
                        onClick={handleEnroll}
                        disabled={enrolling}
                        className="w-full bg-gradient-to-r from-blue-500 to-purple-600 text-white py-4 rounded-xl font-bold hover:opacity-90 disabled:opacity-50 transition"
                      >
                        {enrolling ? '신청 중...' : '신청 완료하기'}
                      </button>
                      <button
                        onClick={() => {
                          setShowEnrollForm(false);
                          setStudentName('');
                        }}
                        className="w-full text-gray-500 hover:text-gray-700 text-sm"
                      >
                        취소
                      </button>
                    </div>
                  )}

                  {/* 안내 */}
                  <div className="mt-6 pt-6 border-t space-y-3 text-sm text-gray-500">
                    <div className="flex items-center gap-2">
                      <span className="text-green-500">✓</span>
                      <span>수강 신청 후 바로 시작 가능</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-green-500">✓</span>
                      <span>전문 강사의 1:1 피드백</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-green-500">✓</span>
                      <span>AI 기반 맞춤형 학습 추천</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 모바일 하단 고정 바 */}
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
                className="text-gray-400 hover:text-gray-600 text-2xl"
              >
                ×
              </button>
            </div>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  수강생 이름
                </label>
                <input
                  type="text"
                  value={studentName}
                  onChange={(e) => setStudentName(e.target.value)}
                  placeholder="이름을 입력하세요"
                  className="w-full border-2 border-gray-200 rounded-xl px-4 py-3 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>
              <button
                onClick={handleEnroll}
                disabled={enrolling}
                className="w-full bg-gradient-to-r from-blue-500 to-purple-600 text-white py-4 rounded-xl font-bold hover:opacity-90 disabled:opacity-50"
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

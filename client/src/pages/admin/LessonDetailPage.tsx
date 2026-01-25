import { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { adminLessonApi } from '../../services/api';
import type { LessonDetail } from '../../types';
import { SPORT_LABELS, TARGET_LABELS, DIFFICULTY_LABELS, STATUS_LABELS } from '../../constants/labels';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function LessonDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [lesson, setLesson] = useState<LessonDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [regeneratingIntro, setRegeneratingIntro] = useState(false);
  const [regeneratingCurriculum, setRegeneratingCurriculum] = useState(false);
  const [regeneratingThumbnail, setRegeneratingThumbnail] = useState(false);

  useEffect(() => {
    loadLesson();
  }, [id]);

  const loadLesson = async () => {
    if (!id) return;
    try {
      const res = await adminLessonApi.getById(Number(id));
      setLesson(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateContent = async () => {
    if (!id) return;
    setGenerating(true);
    try {
      await adminLessonApi.generateContent(Number(id));
      await loadLesson();
    } catch (err) {
      console.error(err);
      alert('콘텐츠 생성에 실패했습니다.');
    } finally {
      setGenerating(false);
    }
  };

  const handlePublish = async () => {
    if (!id) return;
    if (!lesson?.active_content) {
      alert('먼저 AI 콘텐츠를 생성해주세요.');
      return;
    }
    if (!confirm('강습을 발행하시겠습니까?')) return;

    setPublishing(true);
    try {
      await adminLessonApi.publish(Number(id));
      navigate('/admin/lessons');
    } catch (err) {
      console.error(err);
      alert('발행에 실패했습니다.');
    } finally {
      setPublishing(false);
    }
  };

  const handleDelete = async () => {
    if (!id) return;
    if (!confirm('정말 삭제하시겠습니까?')) return;

    try {
      await adminLessonApi.delete(Number(id));
      navigate('/admin/lessons');
    } catch (err) {
      console.error(err);
      alert('삭제에 실패했습니다.');
    }
  };

  const handleRegenerateIntroduction = async () => {
    if (!id || !content) return;
    setRegeneratingIntro(true);
    try {
      await adminLessonApi.regenerateIntroduction(Number(id), content.id);
      await loadLesson();
    } catch (err) {
      console.error(err);
      alert('소개 문구 재생성에 실패했습니다.');
    } finally {
      setRegeneratingIntro(false);
    }
  };

  const handleRegenerateCurriculum = async () => {
    if (!id || !content) return;
    setRegeneratingCurriculum(true);
    try {
      await adminLessonApi.regenerateCurriculum(Number(id), content.id);
      await loadLesson();
    } catch (err) {
      console.error(err);
      alert('커리큘럼 재생성에 실패했습니다.');
    } finally {
      setRegeneratingCurriculum(false);
    }
  };

  const handleRegenerateThumbnail = async () => {
    if (!id || !content) return;
    setRegeneratingThumbnail(true);
    try {
      await adminLessonApi.regenerateThumbnail(Number(id), content.id);
      await loadLesson();
    } catch (err) {
      console.error(err);
      alert('썸네일 재생성에 실패했습니다.');
    } finally {
      setRegeneratingThumbnail(false);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-24">
        <div className="w-10 h-10 border-4 border-primary border-t-transparent rounded-full animate-spin mb-4" />
        <p className="text-slate-500">강습 정보를 불러오는 중...</p>
      </div>
    );
  }

  if (!lesson) {
    return (
      <div className="flex flex-col items-center justify-center py-24">
        <span className="material-symbols-outlined text-5xl text-slate-300 mb-4">error</span>
        <p className="text-slate-500 mb-4">강습을 찾을 수 없습니다.</p>
        <Link to="/admin/lessons" className="text-primary hover:underline">
          목록으로 돌아가기
        </Link>
      </div>
    );
  }

  const content = lesson.active_content;
  const statusBadgeStyle = lesson.status === 'published'
    ? 'bg-emerald-100 text-emerald-700 ring-emerald-600/20'
    : 'bg-amber-100 text-amber-700 ring-amber-600/20';

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <header className="flex flex-wrap justify-between items-start gap-4">
        <div className="flex flex-col gap-2">
          <div className="flex items-center gap-3">
            <Link
              to="/admin/lessons"
              className="p-1.5 -ml-1.5 rounded-full hover:bg-slate-200 transition-colors text-slate-500"
            >
              <span className="material-symbols-outlined">arrow_back</span>
            </Link>
            <h1 className="text-3xl font-black text-slate-900 tracking-tight">{lesson.title}</h1>
            <span className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-bold ring-1 ring-inset ${statusBadgeStyle}`}>
              {STATUS_LABELS[lesson.status]}
            </span>
          </div>
          <p className="text-slate-500">강사: {lesson.instructor_name || '미지정'}</p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={handleDelete}
            className="flex items-center justify-center rounded-full h-10 px-6 bg-red-50 hover:bg-red-100 text-red-600 text-sm font-bold transition-colors"
          >
            삭제
          </button>
          {lesson.status === 'draft' && (
            <button
              onClick={handlePublish}
              disabled={publishing || !content}
              className="flex items-center justify-center rounded-full h-10 px-6 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-bold shadow-lg shadow-emerald-600/20 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {publishing ? '발행 중...' : '발행하기'}
            </button>
          )}
        </div>
      </header>

      {/* Info Grid Card */}
      <section className="bg-white rounded-2xl p-6 shadow-sm border border-slate-100">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
          <div className="flex flex-col gap-1">
            <p className="text-slate-500 text-xs font-semibold uppercase tracking-wider">종목</p>
            <p className="text-slate-900 text-base font-medium">{SPORT_LABELS[lesson.sport_type] || lesson.sport_type}</p>
          </div>
          <div className="flex flex-col gap-1">
            <p className="text-slate-500 text-xs font-semibold uppercase tracking-wider">대상</p>
            <p className="text-slate-900 text-base font-medium">{TARGET_LABELS[lesson.target_audience] || lesson.target_audience}</p>
          </div>
          <div className="flex flex-col gap-1">
            <p className="text-slate-500 text-xs font-semibold uppercase tracking-wider">난이도</p>
            <p className="text-slate-900 text-base font-medium">{DIFFICULTY_LABELS[lesson.difficulty] || lesson.difficulty}</p>
          </div>
          <div className="flex flex-col gap-1">
            <p className="text-slate-500 text-xs font-semibold uppercase tracking-wider">등록일</p>
            <p className="text-slate-900 text-base font-medium">{new Date(lesson.created_at).toLocaleDateString('ko-KR')}</p>
          </div>
        </div>
      </section>

      {/* AI Content Generator Section */}
      <section className="bg-white rounded-2xl shadow-sm border border-purple-100 overflow-hidden">
        {/* AI Header Toolbar */}
        <div className="flex flex-wrap items-center justify-between gap-4 p-6 bg-purple-50/50 border-b border-purple-100">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-purple-100 rounded-full text-purple-600">
              <span className="material-symbols-outlined">auto_awesome</span>
            </div>
            <h3 className="text-lg font-bold text-slate-900">AI 콘텐츠 생성기</h3>
          </div>
          <button
            onClick={handleGenerateContent}
            disabled={generating}
            className="flex items-center gap-2 bg-purple-600 hover:bg-purple-700 text-white px-5 py-2.5 rounded-full text-sm font-bold shadow-lg shadow-purple-500/20 transition-all transform hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
          >
            {generating ? (
              <>
                <span className="material-symbols-outlined text-[18px] animate-spin">autorenew</span>
                생성 중...
              </>
            ) : (
              <>
                <span className="material-symbols-outlined text-[18px]">bolt</span>
                {content ? '전체 재생성' : '전체 콘텐츠 생성'}
              </>
            )}
          </button>
        </div>

        <div className="p-6 md:p-8 flex flex-col gap-8">
          {content ? (
            <>
              {/* Top Row: Thumbnail & Description */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Thumbnail */}
                <div className="lg:col-span-1 flex flex-col gap-3">
                  <div className="flex justify-between items-center">
                    <label className="text-sm font-bold text-slate-700">썸네일</label>
                    <button
                      onClick={handleRegenerateThumbnail}
                      disabled={regeneratingThumbnail}
                      className="text-purple-600 hover:text-purple-700 text-xs font-bold flex items-center gap-1 disabled:opacity-50"
                    >
                      <span className="material-symbols-outlined text-[16px]">refresh</span>
                      {regeneratingThumbnail ? '재생성 중...' : '재생성'}
                    </button>
                  </div>
                  <div className="relative group aspect-video w-full overflow-hidden rounded-2xl bg-slate-200 shadow-inner">
                    {content.thumbnail_url ? (
                      <>
                        <img
                          src={`${API_BASE}${content.thumbnail_url}`}
                          alt="썸네일"
                          className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-105"
                        />
                        <div className="absolute inset-0 bg-black/0 group-hover:bg-black/10 transition-colors" />
                      </>
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-slate-400">
                        <span className="material-symbols-outlined text-4xl">image</span>
                      </div>
                    )}
                  </div>
                </div>

                {/* Description */}
                <div className="lg:col-span-2 flex flex-col gap-3">
                  <div className="flex justify-between items-center">
                    <label className="text-sm font-bold text-slate-700">소개 문구</label>
                    <button
                      onClick={handleRegenerateIntroduction}
                      disabled={regeneratingIntro}
                      className="text-purple-600 hover:text-purple-700 text-xs font-bold flex items-center gap-1 disabled:opacity-50"
                    >
                      <span className="material-symbols-outlined text-[16px]">refresh</span>
                      {regeneratingIntro ? '재생성 중...' : '재생성'}
                    </button>
                  </div>
                  <div className="flex-1 bg-slate-50 rounded-2xl p-5 border border-slate-100 text-sm leading-relaxed text-slate-600">
                    {content.introduction || '(소개 문구 없음)'}
                  </div>
                </div>
              </div>

              {/* Curriculum */}
              <div className="flex flex-col gap-4">
                <div className="flex justify-between items-end border-b border-slate-100 pb-2">
                  <h4 className="text-lg font-bold text-slate-900">커리큘럼</h4>
                  <button
                    onClick={handleRegenerateCurriculum}
                    disabled={regeneratingCurriculum}
                    className="text-purple-600 hover:text-purple-700 text-xs font-bold flex items-center gap-1 px-3 py-1 rounded-full hover:bg-purple-50 transition-colors disabled:opacity-50"
                  >
                    <span className="material-symbols-outlined text-[16px]">refresh</span>
                    {regeneratingCurriculum ? '재생성 중...' : '커리큘럼 재생성'}
                  </button>
                </div>

                {content.curriculum?.weeks && content.curriculum.weeks.length > 0 ? (
                  <div className="space-y-4">
                    {content.curriculum.weeks.map((week: any) => (
                      <div
                        key={week.week}
                        className="group bg-white rounded-xl border border-slate-100 hover:border-purple-200 transition-all shadow-sm"
                      >
                        <div className="p-4 flex flex-col md:flex-row gap-4 md:items-start">
                          <div className="flex-shrink-0 flex items-center justify-center w-12 h-12 rounded-full bg-purple-100 text-purple-600 font-bold">
                            W{week.week}
                          </div>
                          <div className="flex-1">
                            <h5 className="text-base font-bold text-slate-900 mb-2">{week.title}</h5>
                            {week.topics && week.topics.length > 0 && (
                              <ul className="space-y-2">
                                {week.topics.map((topic: string, i: number) => (
                                  <li key={i} className="flex items-start gap-2 text-sm text-slate-600">
                                    <span className="material-symbols-outlined text-[16px] text-emerald-500 mt-0.5">check_circle</span>
                                    {topic}
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
                  <div className="text-center py-8 text-slate-400 bg-slate-50 rounded-xl">
                    <span className="material-symbols-outlined text-4xl mb-2">list_alt</span>
                    <p>커리큘럼이 아직 생성되지 않았습니다.</p>
                  </div>
                )}
              </div>

              {/* Version Info */}
              <div className="text-xs text-slate-400 pt-4 border-t border-slate-100 flex items-center gap-4">
                <span>버전 {content.version}</span>
                <span>•</span>
                <span>생성일: {new Date(content.created_at).toLocaleString('ko-KR')}</span>
              </div>
            </>
          ) : (
            <div className="text-center py-16">
              <div className="p-4 bg-purple-50 rounded-full inline-block mb-4">
                <span className="material-symbols-outlined text-4xl text-purple-400">auto_awesome</span>
              </div>
              <p className="text-slate-500 mb-2">아직 생성된 콘텐츠가 없습니다.</p>
              <p className="text-slate-400 text-sm">위의 "전체 콘텐츠 생성" 버튼을 클릭해주세요.</p>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}

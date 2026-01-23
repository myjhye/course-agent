import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { adminLessonApi } from '../../services/api';
import type { LessonDetail } from '../../types';
import { SPORT_LABELS, TARGET_LABELS, DIFFICULTY_LABELS, STATUS_LABELS } from '../../constants/labels';

export default function LessonDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [lesson, setLesson] = useState<LessonDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [publishing, setPublishing] = useState(false);

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
      alert('AI 콘텐츠가 생성되었습니다!');
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
      await loadLesson();
      alert('강습이 발행되었습니다!');
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

  if (loading) return <div>로딩 중...</div>;
  if (!lesson) return <div>강습을 찾을 수 없습니다.</div>;

  const content = lesson.active_content;

  return (
    <div className="space-y-6">
      {/* 헤더 */}
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-2xl font-bold">{lesson.title}</h1>
          <p className="text-gray-500 mt-1">
            {lesson.instructor_name || '강사 미지정'} ・{' '}
            <span
              className={`px-2 py-0.5 text-xs rounded-full ${
                lesson.status === 'published'
                  ? 'bg-green-100 text-green-800'
                  : 'bg-yellow-100 text-yellow-800'
              }`}
            >
              {STATUS_LABELS[lesson.status]}
            </span>
          </p>
        </div>
        <div className="flex gap-2">
          {lesson.status === 'draft' && (
            <button
              onClick={handlePublish}
              disabled={publishing || !content}
              className="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 disabled:bg-gray-400"
            >
              {publishing ? '발행 중...' : '발행하기'}
            </button>
          )}
          <button
            onClick={handleDelete}
            className="bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700"
          >
            삭제
          </button>
        </div>
      </div>

      {/* 기본 정보 */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold mb-4">기본 정보</h2>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-gray-500">종목:</span>{' '}
            <span className="font-medium">{SPORT_LABELS[lesson.sport_type] || lesson.sport_type}</span>
          </div>
          <div>
            <span className="text-gray-500">대상:</span>{' '}
            <span className="font-medium">{TARGET_LABELS[lesson.target_audience] || lesson.target_audience}</span>
          </div>
          <div>
            <span className="text-gray-500">난이도:</span>{' '}
            <span className="font-medium">{DIFFICULTY_LABELS[lesson.difficulty] || lesson.difficulty}</span>
          </div>
          <div>
            <span className="text-gray-500">등록일:</span>{' '}
            <span className="font-medium">
              {new Date(lesson.created_at).toLocaleDateString('ko-KR')}
            </span>
          </div>
        </div>
      </div>

      {/* AI 콘텐츠 */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-semibold">AI 콘텐츠</h2>
          <button
            onClick={handleGenerateContent}
            disabled={generating}
            className="bg-purple-600 text-white px-4 py-2 rounded-lg hover:bg-purple-700 disabled:bg-gray-400"
          >
            {generating ? '생성 중...' : content ? '재생성' : 'AI 콘텐츠 생성'}
          </button>
        </div>

        {content ? (
          <div className="space-y-6">
            {/* 썸네일 */}
            {content.thumbnail_url && (
              <div>
                <h3 className="text-sm font-medium text-gray-700 mb-2">썸네일</h3>
                <img
                  src={`http://localhost:8000${content.thumbnail_url}`}
                  alt="썸네일"
                  className="w-64 h-36 object-cover rounded-lg border"
                />
              </div>
            )}

            {/* 소개 문구 */}
            <div>
              <h3 className="text-sm font-medium text-gray-700 mb-2">소개 문구</h3>
              <p className="text-gray-600 bg-gray-50 p-4 rounded-lg">
                {content.introduction || '(없음)'}
              </p>
            </div>

            {/* 커리큘럼 */}
            <div>
              <h3 className="text-sm font-medium text-gray-700 mb-2">커리큘럼</h3>
              {content.curriculum?.weeks ? (
                <div className="space-y-3">
                  {content.curriculum.weeks.map((week) => (
                    <div
                      key={week.week}
                      className="bg-gray-50 p-4 rounded-lg"
                    >
                      <div className="font-medium">
                        {week.week}주차: {week.title}
                      </div>
                      {week.topics && (
                        <ul className="mt-2 text-sm text-gray-600 list-disc list-inside">
                          {week.topics.map((topic, i) => (
                            <li key={i}>{topic}</li>
                          ))}
                        </ul>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-gray-500">(없음)</p>
              )}
            </div>

            <div className="text-xs text-gray-400">
              버전 {content.version} ・ 생성일:{' '}
              {new Date(content.created_at).toLocaleString()}
            </div>
          </div>
        ) : (
          <div className="text-center py-12 text-gray-500">
            아직 생성된 콘텐츠가 없습니다.
            <br />
            "AI 콘텐츠 생성" 버튼을 클릭해주세요.
          </div>
        )}
      </div>
    </div>
  );
}


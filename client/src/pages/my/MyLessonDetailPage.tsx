import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { lessonApi, myEnrollmentApi } from '../../services/api';
import type { LessonDetail } from '../../types';
import { SPORT_LABELS, TARGET_LABELS, DIFFICULTY_LABELS } from '../../constants/labels';
import { getImageUrl } from '../../utils/image';

const STUDENT_NAME = '홍길동'; // 하드코딩

export default function MyLessonDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [lesson, setLesson] = useState<LessonDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [enrolling, setEnrolling] = useState(false);
  const [studentName, setStudentName] = useState('');
  const [showEnrollForm, setShowEnrollForm] = useState(false);
  const [liked, setLiked] = useState(false);

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
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-gray-500">로딩 중...</div>
      </div>
    );
  }

  if (!lesson) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-gray-500 mb-4">강습을 찾을 수 없습니다.</p>
          <Link to="/lessons" className="text-blue-600 hover:underline">
            목록으로 돌아가기
          </Link>
        </div>
      </div>
    );
  }

  const content = lesson.active_content;
  const thumbnailUrl = getImageUrl(content?.thumbnail_url);

  return (
    <div className="min-h-screen bg-gray-50">
      {/* 헤더 */}
      <header className="bg-white shadow-sm">
        <div className="max-w-4xl mx-auto px-4 py-4">
          <Link to="/lessons" className="text-blue-600 hover:underline text-sm">
            ← 목록으로
          </Link>
        </div>
      </header>

      {/* 메인 */}
      <main className="max-w-4xl mx-auto px-4 py-8">
        {/* 썸네일 */}
        {thumbnailUrl && (
          <div className="aspect-video rounded-xl overflow-hidden mb-6">
            <img
              src={thumbnailUrl}
              alt={lesson.title}
              className="w-full h-full object-cover"
            />
          </div>
        )}

        {/* 제목 + 수강 신청 */}
        <div className="bg-white rounded-xl shadow-md p-6 mb-6">
          <div className="flex flex-wrap gap-2 mb-3">
            <span className="bg-blue-100 text-blue-700 text-sm px-3 py-1 rounded-full">
              {SPORT_LABELS[lesson.sport_type] || lesson.sport_type}
            </span>
            <span className="bg-gray-100 text-gray-700 text-sm px-3 py-1 rounded-full">
              {DIFFICULTY_LABELS[lesson.difficulty] || lesson.difficulty}
            </span>
            <span className="bg-gray-100 text-gray-700 text-sm px-3 py-1 rounded-full">
              {TARGET_LABELS[lesson.target_audience] || lesson.target_audience}
            </span>
          </div>

          <div className="flex items-center gap-3 mb-2">
            <h1 className="text-2xl font-bold text-gray-900">
              {lesson.title}
            </h1>
            <button
              onClick={handleToggleLike}
              className="text-2xl hover:scale-110 transition"
            >
              {liked ? '❤️' : '🤍'}
            </button>
          </div>

          {lesson.instructor_name && (
            <p className="text-gray-600 mb-4">
              강사: {lesson.instructor_name}
            </p>
          )}

          {/* 수강 신청 버튼/폼 */}
          {!showEnrollForm ? (
            <button
              onClick={() => setShowEnrollForm(true)}
              className="w-full bg-blue-600 text-white py-3 rounded-lg font-medium hover:bg-blue-700 transition-colors"
            >
              수강 신청하기
            </button>
          ) : (
            <div className="border-t pt-4 mt-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                수강생 이름
              </label>
              <input
                type="text"
                value={studentName}
                onChange={(e) => setStudentName(e.target.value)}
                placeholder="홍길동"
                className="w-full border border-gray-300 rounded-lg px-4 py-2 mb-3 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
              <div className="flex gap-2">
                <button
                  onClick={handleEnroll}
                  disabled={enrolling}
                  className="flex-1 bg-blue-600 text-white py-2 rounded-lg font-medium hover:bg-blue-700 disabled:bg-gray-400"
                >
                  {enrolling ? '신청 중...' : '신청 완료'}
                </button>
                <button
                  onClick={() => {
                    setShowEnrollForm(false);
                    setStudentName('');
                  }}
                  className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
                >
                  취소
                </button>
              </div>
            </div>
          )}
        </div>

        {/* 소개 */}
        {content?.introduction && (
          <div className="bg-white rounded-xl shadow-md p-6 mb-6">
            <h2 className="text-lg font-bold text-gray-900 mb-3">강습 소개</h2>
            <p className="text-gray-700 leading-relaxed whitespace-pre-line">
              {content.introduction}
            </p>
          </div>
        )}

        {/* 커리큘럼 */}
        {content?.curriculum?.weeks && content.curriculum.weeks.length > 0 && (
          <div className="bg-white rounded-xl shadow-md p-6">
            <h2 className="text-lg font-bold text-gray-900 mb-4">커리큘럼</h2>
            <div className="space-y-4">
              {content.curriculum.weeks.map((week) => (
                <div
                  key={week.week}
                  className="border-l-4 border-blue-500 pl-4 py-2"
                >
                  <div className="font-medium text-gray-900">
                    {week.week}주차: {week.title}
                  </div>
                  {week.topics && week.topics.length > 0 && (
                    <ul className="mt-2 text-sm text-gray-600 space-y-1">
                      {week.topics.map((topic, i) => (
                        <li key={i} className="flex items-start gap-2">
                          <span className="text-blue-500">•</span>
                          {topic}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}


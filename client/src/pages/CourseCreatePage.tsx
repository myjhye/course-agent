import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { courseApi } from '../services/api';

const DEFAULT_THUMBNAIL = '/default-thumbnail.jpeg';

export default function CourseCreatePage() {
  const navigate = useNavigate();
  const [step, setStep] = useState<'input' | 'editor'>('input');
  const [topic, setTopic] = useState('');
  const [generating, setGenerating] = useState(false);
  const [formData, setFormData] = useState({
    title: '',
    category: '',
    description: '',
    curriculum: '',
    thumbnail_url: null as string | null,
  });
  const [saving, setSaving] = useState(false);

  const getThumbnailUrl = (url: string | null) => {
    if (!url) return DEFAULT_THUMBNAIL;
    if (url.startsWith('/')) {
      return `http://localhost:8000${url}`;
    }
    return url;
  };

  const handleGenerateDraft = async () => {
    if (!topic.trim()) {
      alert('강의 주제를 입력해주세요.');
      return;
    }

    setGenerating(true);
    try {
      const draft = await courseApi.generateCourseDraft(topic);
      setFormData({
        title: draft.title,
        category: draft.category,
        description: draft.description,
        curriculum: draft.curriculum,
        thumbnail_url: draft.thumbnail_url,
      });
      setStep('editor');
    } catch (err) {
      console.error(err);
      alert('AI 초안 생성에 실패했습니다.');
    } finally {
      setGenerating(false);
    }
  };

  const handleSave = async () => {
    if (!formData.title.trim() || !formData.category.trim()) {
      alert('제목과 카테고리는 필수입니다.');
      return;
    }

    setSaving(true);
    try {
      await courseApi.createCourse({
        title: formData.title,
        category: formData.category,
        description: formData.description || null,
        curriculum: formData.curriculum || null,
        thumbnail_url: formData.thumbnail_url,
      });
      alert('강의가 성공적으로 생성되었습니다!');
      navigate('/courses');
    } catch (err) {
      console.error(err);
      alert('강의 생성에 실패했습니다.');
    } finally {
      setSaving(false);
    }
  };

  if (step === 'input') {
    return (
      <div className="p-8 max-w-2xl mx-auto">
        <h1 className="text-3xl font-bold mb-8">새 강의 만들기</h1>

        <div className="bg-white p-6 rounded-lg shadow">
          <label className="block mb-4">
            <span className="block text-sm font-medium text-gray-700 mb-2">
              강의 주제를 입력하세요
            </span>
            <input
              type="text"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="예: 직장인을 위한 엑셀 자동화"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              onKeyPress={(e) => {
                if (e.key === 'Enter' && !generating) {
                  handleGenerateDraft();
                }
              }}
            />
          </label>

          <button
            onClick={handleGenerateDraft}
            disabled={generating || !topic.trim()}
            className="w-full bg-blue-500 text-white px-6 py-3 rounded-lg hover:bg-blue-600 disabled:bg-gray-400 disabled:cursor-not-allowed flex items-center justify-center"
          >
            {generating ? (
              <>
                <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                AI가 커리큘럼을 짜고 있습니다...
              </>
            ) : (
              '✨ AI로 초안 만들기'
            )}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <h1 className="text-3xl font-bold mb-8">강의 초안 편집</h1>

      <div className="bg-white p-6 rounded-lg shadow space-y-6">
        {/* 썸네일 미리보기 */}
        {formData.thumbnail_url && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              썸네일 이미지
            </label>
            <img
              src={getThumbnailUrl(formData.thumbnail_url)}
              alt="썸네일 미리보기"
              className="w-full h-64 object-cover rounded-lg bg-gray-200"
              onError={(e) => {
                (e.target as HTMLImageElement).src = DEFAULT_THUMBNAIL;
              }}
            />
          </div>
        )}

        {/* 강의 제목 */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            강의 제목 *
          </label>
          <input
            type="text"
            value={formData.title}
            onChange={(e) => setFormData({ ...formData, title: e.target.value })}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            placeholder="강의 제목을 입력하세요"
          />
        </div>

        {/* 카테고리 */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            카테고리 *
          </label>
          <input
            type="text"
            value={formData.category}
            onChange={(e) => setFormData({ ...formData, category: e.target.value })}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            placeholder="카테고리를 입력하세요"
          />
        </div>

        {/* 상세 설명 */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            상세 설명
          </label>
          <textarea
            value={formData.description}
            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
            rows={6}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            placeholder="강의에 대한 상세 설명을 입력하세요"
          />
        </div>

        {/* 커리큘럼 */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            커리큘럼
          </label>
          <textarea
            value={formData.curriculum}
            onChange={(e) => setFormData({ ...formData, curriculum: e.target.value })}
            rows={10}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono text-sm"
            placeholder="커리큘럼을 입력하세요"
          />
        </div>

        {/* 버튼들 */}
        <div className="flex gap-4 pt-4">
          <button
            onClick={() => setStep('input')}
            className="px-6 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            ← 주제 다시 입력
          </button>
          <button
            onClick={handleSave}
            disabled={saving || !formData.title.trim() || !formData.category.trim()}
            className="flex-1 bg-green-500 text-white px-6 py-3 rounded-lg hover:bg-green-600 disabled:bg-gray-400 disabled:cursor-not-allowed"
          >
            {saving ? '저장 중...' : '강의 개설하기'}
          </button>
        </div>
      </div>
    </div>
  );
}


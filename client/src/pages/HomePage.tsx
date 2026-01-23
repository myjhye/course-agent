import { Link } from 'react-router-dom';

function HomePage() {
  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-4xl font-bold mb-8">Course Agent</h1>
        <p className="text-lg text-gray-600 mb-8">
          LLM 기반 강의 플랫폼에 오신 것을 환영합니다.
        </p>
        <div className="space-x-4">
          <Link
            to="/lessons"
            className="inline-block bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700"
          >
            강습 목록 보기
          </Link>
          <Link
            to="/admin"
            className="inline-block bg-purple-600 text-white px-6 py-3 rounded-lg hover:bg-purple-700"
          >
            관리자 화면
          </Link>
          <Link
            to="/chat"
            className="inline-block bg-gray-600 text-white px-6 py-3 rounded-lg hover:bg-gray-700"
          >
            채팅
          </Link>
        </div>
      </div>
    </div>
  );
}

export default HomePage;


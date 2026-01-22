import { Link } from 'react-router-dom';

function ChatPage() {
  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-4xl mx-auto">
        <div className="mb-6">
          <Link
            to="/"
            className="text-blue-600 hover:text-blue-800"
          >
            ← 홈으로
          </Link>
        </div>
        <h1 className="text-4xl font-bold mb-8">채팅</h1>
        <p className="text-gray-600">채팅 기능은 추후 구현 예정입니다.</p>
      </div>
    </div>
  );
}

export default ChatPage;


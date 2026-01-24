import { useEffect, useState, useRef } from 'react';
import { Link } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import { chatApi } from '../services/api';
import type { ChatMessage } from '../services/api';
import { v4 as uuidv4 } from 'uuid';

export default function ChatPage() {
  const [sessionId, setSessionId] = useState<string>('');
  const [studentName, setStudentName] = useState<string>('');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [showNameInput, setShowNameInput] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // 새 세션 ID 생성
    setSessionId(uuidv4());
  }, []);

  useEffect(() => {
    // 메시지 추가 시 스크롤
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleStartChat = () => {
    if (!studentName.trim()) {
      alert('이름을 입력해주세요.');
      return;
    }
    setShowNameInput(false);
  };

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userMessage = input.trim();
    setInput('');
    setLoading(true);

    // 사용자 메시지 임시 추가
    const tempUserMsg: ChatMessage = {
      id: Date.now(),
      session_id: sessionId,
      role: 'user',
      content: userMessage,
      tool_used: null,
      tool_result: null,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, tempUserMsg]);

    try {
      const res = await chatApi.sendMessage(sessionId, userMessage, studentName);
      
      // 실제 응답으로 교체
      setMessages((prev) => [
        ...prev.slice(0, -1),
        res.data.user_message,
        res.data.assistant_message,
      ]);
    } catch (err) {
      console.error(err);
      // 에러 메시지 추가
      const errorMsg: ChatMessage = {
        id: Date.now() + 1,
        session_id: sessionId,
        role: 'assistant',
        content: '죄송합니다. 오류가 발생했습니다. 다시 시도해주세요.',
        tool_used: null,
        tool_result: null,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // 이름 입력 화면
  if (showNameInput) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-xl shadow-lg p-8 max-w-md w-full">
          <h1 className="text-2xl font-bold text-center mb-2">💬 AI 상담</h1>
          <p className="text-gray-500 text-center mb-6">
            강습 추천, 수강 현황, 이용 방법 등을 물어보세요!
          </p>
          
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              이름을 알려주세요
            </label>
            <input
              type="text"
              value={studentName}
              onChange={(e) => setStudentName(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleStartChat()}
              placeholder="홍길동"
              className="w-full border border-gray-300 rounded-lg px-4 py-3 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
          
          <button
            onClick={handleStartChat}
            className="w-full bg-blue-600 text-white py-3 rounded-lg font-medium hover:bg-blue-700 transition"
          >
            대화 시작하기
          </button>
          
          <Link
            to="/lessons"
            className="block text-center text-sm text-gray-500 mt-4 hover:text-blue-600"
          >
            강습 둘러보기 →
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* 헤더 */}
      <header className="bg-white shadow-sm">
        <div className="max-w-3xl mx-auto px-4 py-4 flex items-center justify-between">
          <div>
            <h1 className="font-bold text-lg">💬 AI 상담</h1>
            <p className="text-xs text-gray-500">{studentName}님</p>
          </div>
          <Link to="/lessons" className="text-sm text-blue-600 hover:underline">
            강습 보기
          </Link>
        </div>
      </header>

      {/* 메시지 영역 */}
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-3xl mx-auto px-4 py-6 space-y-4">
          {/* 초기 안내 */}
          {messages.length === 0 && (
            <div className="text-center py-12">
              <div className="text-4xl mb-4">🤖</div>
              <p className="text-gray-600 mb-2">안녕하세요, {studentName}님!</p>
              <p className="text-gray-500 text-sm">
                강습 추천, 수강 현황, 환불/결제 등 궁금한 것을 물어보세요.
              </p>
              <div className="flex flex-wrap justify-center gap-2 mt-6">
                {['수영 강습 있어요?', '내 수강 현황 알려줘', '환불 어떻게 해요?'].map((q) => (
                  <button
                    key={q}
                    onClick={() => {
                      setInput(q);
                    }}
                    className="text-sm bg-white border border-gray-200 rounded-full px-4 py-2 hover:bg-gray-50"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* 메시지 목록 */}
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[80%] rounded-2xl px-4 py-3 ${
                  msg.role === 'user'
                    ? 'bg-blue-600 text-white'
                    : 'bg-white shadow-sm border border-gray-100'
                }`}
              >
                {msg.role === 'assistant' ? (
                  <div className="prose prose-sm max-w-none">
                    <ReactMarkdown>{msg.content}</ReactMarkdown>
                  </div>
                ) : (
                  <p className="whitespace-pre-line">{msg.content}</p>
                )}
                {msg.tool_used && (
                  <p className="text-xs mt-2 opacity-60">
                    🔧 {msg.tool_used}
                  </p>
                )}
              </div>
            </div>
          ))}

          {/* 로딩 */}
          {loading && (
            <div className="flex justify-start">
              <div className="bg-white shadow-sm border border-gray-100 rounded-2xl px-4 py-3">
                <div className="flex items-center gap-1">
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-100" />
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-200" />
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </main>

      {/* 입력 영역 */}
      <footer className="bg-white border-t">
        <div className="max-w-3xl mx-auto px-4 py-4">
          <div className="flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="메시지를 입력하세요..."
              disabled={loading}
              className="flex-1 border border-gray-300 rounded-full px-4 py-3 focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100"
            />
            <button
              onClick={handleSend}
              disabled={loading || !input.trim()}
              className="bg-blue-600 text-white px-6 py-3 rounded-full font-medium hover:bg-blue-700 disabled:bg-gray-400 transition"
            >
              전송
            </button>
          </div>
        </div>
      </footer>
    </div>
  );
}

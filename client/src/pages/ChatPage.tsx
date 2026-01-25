import { useEffect, useState, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import { chatApi } from '../services/api';
import type { ChatMessage } from '../services/api';
import { v4 as uuidv4 } from 'uuid';

// 하드코딩된 사용자 이름
const STUDENT_NAME = '홍길동';

export default function ChatPage() {
  const [sessionId, setSessionId] = useState<string>('');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setSessionId(uuidv4());
  }, []);

  useEffect(() => {
    if (messagesContainerRef.current) {
      messagesContainerRef.current.scrollTop = messagesContainerRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userMessage = input.trim();
    setInput('');
    setLoading(true);

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
      const res = await chatApi.sendMessage(sessionId, userMessage, STUDENT_NAME);
      setMessages((prev) => [
        ...prev.slice(0, -1),
        res.data.user_message,
        res.data.assistant_message,
      ]);
    } catch (err) {
      console.error(err);
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

  const quickActions = [
    { icon: 'pool', label: '수영 추천', query: '수영 강습 추천해줘' },
    { icon: 'assignment_ind', label: '수강 현황', query: '내 수강 현황 알려줘' },
    { icon: 'receipt_long', label: '환불 정책', query: '환불 어떻게 해요?' },
  ];

  return (
    <div className="flex flex-col bg-slate-100" style={{ height: 'calc(100vh - 180px)' }}>
      {/* Chat Header */}
      <header className="flex flex-none items-center justify-between border-b border-slate-100 bg-white/80 backdrop-blur-md px-6 py-4 z-10">
        <div className="flex items-center gap-4">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-primary to-purple-600 text-white shadow-md">
            <span className="material-symbols-outlined">smart_toy</span>
          </div>
          <div>
            <h2 className="text-slate-900 text-lg font-bold leading-tight">💬 AI 상담</h2>
            <div className="flex items-center gap-1.5 pt-0.5">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
              </span>
              <span className="text-xs font-medium text-slate-500">Course Agent 온라인</span>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-3 bg-slate-50 px-3 py-1.5 rounded-full border border-slate-100">
            <div className="bg-slate-200 rounded-full h-8 w-8 flex items-center justify-center">
              <span className="material-symbols-outlined text-slate-500 text-[18px]">person</span>
            </div>
            <span className="text-sm font-semibold text-slate-700 pr-1">{STUDENT_NAME}</span>
          </div>
        </div>
      </header>

      {/* Chat Area */}
      <main ref={messagesContainerRef} className="flex-1 overflow-y-auto bg-background-light p-6 sm:p-8 flex flex-col gap-6 chat-scroll">
        {/* Initial Welcome State */}
        {messages.length === 0 && (
          <>
            {/* Date Divider */}
            <div className="flex justify-center">
              <span className="text-xs font-medium text-slate-400 bg-slate-200/50 px-3 py-1 rounded-full">
                오늘
              </span>
            </div>
            
            {/* AI Welcome Message */}
            <div className="flex items-start gap-4 max-w-3xl">
              <div className="flex-none h-10 w-10 rounded-full bg-white flex items-center justify-center shadow-sm border border-slate-100">
                <span className="material-symbols-outlined text-primary text-[20px]">smart_toy</span>
              </div>
              <div className="flex flex-col gap-2">
                <div className="flex flex-col gap-1">
                  <span className="text-xs font-semibold text-slate-500 ml-1">Course Agent</span>
                  <div className="bg-white p-5 rounded-2xl rounded-tl-none shadow-sm text-slate-800 text-sm sm:text-base leading-relaxed border border-slate-100">
                    <p>안녕하세요 <strong>{STUDENT_NAME}</strong>님! 👋</p>
                    <p className="mt-2">저는 AI 코스 에이전트입니다. 스포츠 강습 추천, 수강 현황 확인, 시설 이용 안내 등을 도와드릴 수 있어요.</p>
                    <p className="mt-2">오늘 어떤 도움이 필요하신가요?</p>
                  </div>
                </div>
                
                {/* Quick Actions */}
                <div className="flex flex-wrap gap-2 pt-1">
                  {quickActions.map((action) => (
                    <button
                      key={action.label}
                      onClick={() => setInput(action.query)}
                      className="flex items-center gap-1.5 px-4 py-2 bg-white border border-primary/20 rounded-full text-xs sm:text-sm font-medium text-primary hover:bg-primary/5 transition-colors shadow-sm"
                    >
                      <span className="material-symbols-outlined text-[18px]">{action.icon}</span>
                      {action.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </>
        )}

        {/* Messages */}
        {messages.map((msg) => (
          <div key={msg.id}>
            {msg.role === 'user' ? (
              // User Message
              <div className="flex items-end justify-end gap-3 w-full pl-12">
                <div className="flex flex-col gap-1 items-end max-w-[80%]">
                  <div className="bg-primary text-white p-4 rounded-2xl rounded-tr-none shadow-md text-sm sm:text-base leading-relaxed">
                    <p className="whitespace-pre-line">{msg.content}</p>
                  </div>
                  <span className="text-xs text-slate-400 mr-1">
                    {new Date(msg.created_at).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })}
                  </span>
                </div>
              </div>
            ) : (
              // AI Message
              <div className="flex items-start gap-4 max-w-3xl">
                <div className="flex-none h-10 w-10 rounded-full bg-white flex items-center justify-center shadow-sm border border-slate-100">
                  <span className="material-symbols-outlined text-primary text-[20px]">smart_toy</span>
                </div>
                <div className="flex flex-col gap-2 w-full">
                  <span className="text-xs font-semibold text-slate-500 ml-1">Course Agent</span>
                  <div className="bg-white p-5 rounded-2xl rounded-tl-none shadow-sm text-slate-800 text-sm sm:text-base leading-relaxed border border-slate-100">
                    <div className="prose prose-sm max-w-none prose-slate">
                      <ReactMarkdown>{msg.content}</ReactMarkdown>
                    </div>
                    
                    {/* Tool Badge */}
                    {msg.tool_used && (
                      <div className="mt-4 pt-3 border-t border-slate-100 flex flex-wrap items-center gap-2">
                        {msg.tool_used.split(',').map((tool, idx) => (
                          <div
                            key={idx}
                            className="flex items-center gap-1.5 px-2 py-1 bg-purple-50 rounded text-[10px] font-mono font-medium text-purple-600 border border-purple-100"
                          >
                            <span className="material-symbols-outlined text-[12px]">build</span>
                            {tool.trim()}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        ))}

        {/* Typing Indicator */}
        {loading && (
          <div className="flex items-start gap-4">
            <div className="flex-none h-10 w-10 rounded-full bg-white flex items-center justify-center shadow-sm border border-slate-100">
              <span className="material-symbols-outlined text-primary text-[20px] opacity-50">smart_toy</span>
            </div>
            <div className="bg-white px-4 py-3 rounded-2xl rounded-tl-none shadow-sm border border-slate-100 flex items-center gap-1 h-[46px]">
              <div className="typing-dot h-2 w-2 bg-primary rounded-full"></div>
              <div className="typing-dot h-2 w-2 bg-primary rounded-full"></div>
              <div className="typing-dot h-2 w-2 bg-primary rounded-full"></div>
            </div>
          </div>
        )}
      </main>

      {/* Input Area */}
      <div className="flex-none bg-white p-4 sm:p-6 border-t border-slate-100 z-10">
        <div className="relative flex items-end gap-3 max-w-4xl mx-auto">
          <div className="flex-1 relative">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="메시지를 입력하세요..."
              disabled={loading}
              rows={1}
              className="w-full bg-background-light border-0 rounded-xl px-5 py-3.5 text-slate-800 placeholder:text-slate-400 focus:ring-2 focus:ring-primary/50 resize-none overflow-hidden min-h-[50px] max-h-[150px] disabled:bg-slate-100"
            />
          </div>
          <button
            onClick={handleSend}
            disabled={loading || !input.trim()}
            className="flex-none h-12 w-12 rounded-xl bg-primary text-white flex items-center justify-center hover:bg-blue-600 hover:shadow-lg hover:shadow-primary/30 transition-all active:scale-95 shadow-md disabled:bg-slate-300 disabled:shadow-none"
          >
            <span className="material-symbols-outlined">send</span>
          </button>
        </div>
        <div className="text-center mt-3">
          <p className="text-[10px] text-slate-400">AI는 실수할 수 있습니다. 중요한 정보는 확인해 주세요.</p>
        </div>
      </div>

      {/* CSS for typing animation */}
      <style>{`
        .typing-dot {
          animation: bounce 1.4s infinite ease-in-out both;
        }
        .typing-dot:nth-child(1) { animation-delay: -0.32s; }
        .typing-dot:nth-child(2) { animation-delay: -0.16s; }
        
        @keyframes bounce {
          0%, 80%, 100% { transform: scale(0); }
          40% { transform: scale(1); }
        }
        
        .chat-scroll::-webkit-scrollbar {
          width: 6px;
        }
        .chat-scroll::-webkit-scrollbar-track {
          background: transparent;
        }
        .chat-scroll::-webkit-scrollbar-thumb {
          background-color: #cbd5e1;
          border-radius: 20px;
        }
      `}</style>
    </div>
  );
}

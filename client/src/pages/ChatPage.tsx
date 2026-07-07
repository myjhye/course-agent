import { useEffect, useState, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import { chatApi } from '../services/api';
import type { ChatMessage, ChatSession } from '../services/api';
import { v4 as uuidv4 } from 'uuid';

// 하드코딩된 사용자 이름
const STUDENT_NAME = '홍길동';

/** AI 상담 채팅 화면. SSE 스트리밍으로 단계 상태와 토큰을 실시간 표시한다. */
export default function ChatPage() {
  const [sessionId, setSessionId] = useState<string>('');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [statusText, setStatusText] = useState('');
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  // 전송 중 페이지를 떠나거나 재전송 시 이전 스트림을 중단하기 위해 abort 함수를 보관한다.
  const abortRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    // 페이지를 새로 열 때마다 세션 ID를 바꿔, 이전 대화와 현재 대화를 명확히 구분한다
    setSessionId(uuidv4());
  }, []);

  useEffect(() => {
    // 페이지 진입 시 최근 세션 목록(최대 5개)을 가져온다.
    chatApi.getSessions().then(setSessions).catch(console.error);
  }, []);

  useEffect(() => {
    // 긴 대화에서도 항상 최신 메시지가 보이도록, 메시지가 추가될 때마다 맨 아래로 스크롤한다
    if (messagesContainerRef.current) {
      messagesContainerRef.current.scrollTop = messagesContainerRef.current.scrollHeight;
    }
  }, [messages]);

  /** 입력된 문장을 현재 세션으로 전송하고 SSE 스트림을 시작한다. */
  const handleSend = async () => {
    if (!input.trim() || loading) return;

    // 공백만 전송되는 케이스를 막기 위해 입력을 trim한 후 사용한다
    const userMessage = input.trim();
    setInput('');
    setLoading(true);
    setStatusText('');

    // 백엔드 응답을 기다리지 않고도 사용자가 보낸 내용을 바로 보여주기 위해 낙관적으로 추가한다
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

    // 스트리밍 응답을 한 메시지에 계속 이어 붙이기 위해, 비어 있는 assistant 버블을 미리 만들어 둔다
    const tempAssistantMsg: ChatMessage = {
      id: Date.now() + 1,
      session_id: sessionId,
      role: 'assistant',
      content: '',
      tool_used: null,
      tool_result: null,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, tempAssistantMsg]);

    const abort = chatApi.sendMessageStream(sessionId, userMessage, STUDENT_NAME, {
      onStatus: (data) => {
        const statusMap: Record<string, string> = {
          router: '🔍 의도 분석 중...',
          tool_executor: '📡 정보 검색 중...',
          retry: '🔄 조건 완화 재검색 중...',
          response: '✍️ 답변 생성 중...',
        };
        setStatusText(statusMap[data.step] || data.message || '');
      },
      onToken: (data) => {
        // ChatGPT 스타일 타이핑 효과를 위해, 서버가 보내는 토큰을 마지막 assistant 메시지에 순차적으로 붙인다
        setMessages((prev) => {
          const updated = [...prev];
          const lastMsg = updated[updated.length - 1];
          if (lastMsg && lastMsg.role === 'assistant') {
            updated[updated.length - 1] = {
              ...lastMsg,
              content: lastMsg.content + data.content,
            };
          }
          return updated;
        });
      },
      onDone: (data) => {
        // 대화가 완료되면 최근 세션 목록을 갱신해서 좌측 탭이 최신 상태가 되게 한다.
        chatApi.getSessions().then(setSessions).catch(console.error);

        // 어떤 툴을 거쳐 생성된 답변인지 추적할 수 있도록, 완료 시 tool_used 정보를 최종 메시지에 기록한다
        setMessages((prev) => {
          const updated = [...prev];
          const lastMsg = updated[updated.length - 1];
          if (lastMsg && lastMsg.role === 'assistant') {
            updated[updated.length - 1] = {
              ...lastMsg,
              tool_used: data.tools_used?.join(',') || null,
            };
          }
          return updated;
        });
        setLoading(false);
        setStatusText('');
      },
      onError: (error) => {
        console.error('Stream error:', error);
        // 빈 assistant 버블만 남는 UX를 피하기 위해, 에러가 나면 사용자에게 명시적으로 실패 메시지를 보여준다
        setMessages((prev) => {
          const updated = [...prev];
          const lastMsg = updated[updated.length - 1];
          if (lastMsg && lastMsg.role === 'assistant' && !lastMsg.content) {
            updated[updated.length - 1] = {
              ...lastMsg,
              content: '죄송합니다. 오류가 발생했습니다. 다시 시도해주세요.',
            };
          }
          return updated;
        });
        setLoading(false);
        setStatusText('');
      },
    });

    abortRef.current = abort;
  };

  /** 엔터 키 입력을 가로채 단일 줄 전송 UX를 구현한다. */
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

  /** 새 대화 버튼 클릭 시: 스트림을 중단하고 세션/메시지를 초기화한다. */
  const handleNewChat = () => {
    abortRef.current?.();
    abortRef.current = null;

    setLoading(false);
    setStatusText('');
    setInput('');

    setSessionId(uuidv4());
    setMessages([]);
  };

  /** 세션 목록 클릭 시: 해당 세션의 메시지를 불러와 화면을 교체한다. */
  const handleSelectSession = async (sid: string) => {
    abortRef.current?.();
    abortRef.current = null;

    setLoading(false);
    setStatusText('');
    setInput('');

    setSessionId(sid);

    try {
      const detail = await chatApi.getSessionDetail(sid);
      setMessages(detail.data.messages);
    } catch (e) {
      console.error('Failed to load session detail:', e);
      setMessages([]);
    }
  };

  /** 대화 세션 삭제 처리 */
  const handleDeleteSession = async (e: React.MouseEvent, sid: string) => {
    e.stopPropagation(); // 세션 선택 핸들러 호출 방지
    if (!window.confirm('대화를 삭제하시겠습니까?')) return;

    try {
      await chatApi.deleteSession(sid);
      const updated = await chatApi.getSessions();
      setSessions(updated);

      if (sid === sessionId) {
        handleNewChat();
      }
    } catch (err) {
      console.error('Failed to delete session:', err);
      alert('대화 삭제에 실패했습니다.');
    }
  };

  return (
    <div className="flex flex-row bg-slate-100" style={{ height: 'calc(100vh - 180px)' }}>
      {/* 좌측 세션 탭 (모바일에서는 숨김) */}
      <aside className="hidden md:flex w-64 flex-none bg-white border-r border-slate-100 flex-col p-4 gap-2">
        {/* 새 대화 버튼 */}
        <button
          onClick={handleNewChat}
          className="w-full flex items-center gap-2 px-4 py-2.5 rounded-xl bg-primary text-white text-sm font-medium"
        >
          <span className="material-symbols-outlined text-[18px]">add</span>
          새 대화
        </button>

        {/* 세션 목록 */}
        <div className="flex flex-col gap-1 mt-2 overflow-y-auto max-h-[calc(100vh-270px)] pr-1">
          {sessions.map((s) => (
            <div
              key={s.session_id}
              onClick={() => handleSelectSession(s.session_id)}
              className={`group flex items-center justify-between px-3 py-2 rounded-xl text-sm cursor-pointer transition-colors ${
                s.session_id === sessionId
                  ? 'bg-primary/10 text-primary font-medium'
                  : 'text-slate-600 hover:bg-slate-50'
              }`}
            >
              <span className="truncate flex-1 pr-2">
                {s.title || '새 대화'}
              </span>
              <button
                onClick={(e) => handleDeleteSession(e, s.session_id)}
                className="hidden group-hover:flex items-center justify-center p-1 rounded-md text-slate-400 hover:text-red-500 hover:bg-slate-100 transition-colors"
                title="대화 삭제"
              >
                <span className="material-symbols-outlined text-[18px]">delete</span>
              </button>
            </div>
          ))}
        </div>
      </aside>

      <div className="flex-1 flex flex-col">
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
            ) : msg.content ? (
              // AI Message: content가 있을 때만 말풍선을 그린다. 스트리밍 중 빈 assistant 메시지는 아래 Typing Indicator로 표시된다.
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
            ) : null}
          </div>
        ))}

        {/* Typing Indicator / Status: loading 중엔 status 이벤트(의도 분석/검색/답변 생성) 또는 점 애니메이션을 표시한다. */}
        {loading && (
          <div className="flex items-start gap-4">
            <div className="flex-none h-10 w-10 rounded-full bg-white flex items-center justify-center shadow-sm border border-slate-100">
              <span className="material-symbols-outlined text-primary text-[20px] opacity-50">smart_toy</span>
            </div>
            <div className="bg-white px-4 py-3 rounded-2xl rounded-tl-none shadow-sm border border-slate-100 flex items-center gap-2 h-[46px]">
              {statusText ? (
                <span className="text-sm text-slate-500 animate-pulse">{statusText}</span>
              ) : (
                <>
                  <div className="typing-dot h-2 w-2 bg-primary rounded-full"></div>
                  <div className="typing-dot h-2 w-2 bg-primary rounded-full"></div>
                  <div className="typing-dot h-2 w-2 bg-primary rounded-full"></div>
                </>
              )}
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

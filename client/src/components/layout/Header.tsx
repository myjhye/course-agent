import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useState } from 'react';

const STUDENT_NAME = '홍길동';

export default function Header() {
  const location = useLocation();
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState('');
  const [showMobileMenu, setShowMobileMenu] = useState(false);

  const isActive = (path: string) => location.pathname === path;

  const handleSearch = (e?: React.FormEvent) => {
    e?.preventDefault();
    if (searchQuery.trim()) {
      navigate(`/lessons?search=${encodeURIComponent(searchQuery.trim())}`);
      setSearchQuery('');
      setShowMobileMenu(false);
    }
  };

  return (
    <header className="sticky top-0 z-50 bg-white border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* 로고 */}
          <Link to="/" className="flex items-center gap-2">
            <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-sm">CA</span>
            </div>
            <span className="text-xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
              Course Agent
            </span>
          </Link>

          {/* 검색바 (데스크탑) */}
          <form onSubmit={handleSearch} className="hidden md:flex flex-1 max-w-md mx-8">
            <div className="relative w-full">
              <input
                type="text"
                placeholder="배우고 싶은 강습을 검색해보세요"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-full focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
              />
              <button
                type="submit"
                className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                  />
                </svg>
              </button>
            </div>
          </form>

          {/* 네비게이션 (데스크탑) */}
          <nav className="hidden md:flex items-center gap-6">
            <Link
              to="/lessons"
              className={`text-sm font-medium transition ${
                isActive('/lessons') ? 'text-blue-600' : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              강습 둘러보기
            </Link>
            <Link
              to="/my/enrollments"
              className={`text-sm font-medium transition ${
                isActive('/my/enrollments') ? 'text-blue-600' : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              내 강습
            </Link>
            <Link
              to="/chat"
              className={`text-sm font-medium transition ${
                isActive('/chat') ? 'text-blue-600' : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              AI 상담
            </Link>
            <div className="h-6 w-px bg-gray-200" />
            <Link
              to="/admin/dashboard"
              className="text-sm text-gray-500 hover:text-gray-700"
            >
              관리자
            </Link>
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 bg-gradient-to-br from-blue-400 to-purple-500 rounded-full flex items-center justify-center">
                <span className="text-white text-sm font-medium">
                  {STUDENT_NAME.charAt(0)}
                </span>
              </div>
              <span className="text-sm font-medium text-gray-700">{STUDENT_NAME}</span>
            </div>
          </nav>

          {/* 모바일 메뉴 버튼 */}
          <button
            onClick={() => setShowMobileMenu(!showMobileMenu)}
            className="md:hidden p-2 rounded-lg hover:bg-gray-100"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
        </div>
      </div>

      {/* 모바일 메뉴 */}
      {showMobileMenu && (
        <div className="md:hidden border-t border-gray-200 bg-white">
          <div className="px-4 py-3 space-y-3">
            <form onSubmit={handleSearch}>
              <input
                type="text"
                placeholder="강습 검색..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full px-4 py-2 border rounded-lg text-sm"
              />
            </form>
            <Link to="/lessons" onClick={() => setShowMobileMenu(false)} className="block py-2 text-gray-700">강습 둘러보기</Link>
            <Link to="/my/enrollments" onClick={() => setShowMobileMenu(false)} className="block py-2 text-gray-700">내 강습</Link>
            <Link to="/chat" onClick={() => setShowMobileMenu(false)} className="block py-2 text-gray-700">AI 상담</Link>
            <Link to="/admin/dashboard" onClick={() => setShowMobileMenu(false)} className="block py-2 text-gray-500">관리자</Link>
          </div>
        </div>
      )}
    </header>
  );
}

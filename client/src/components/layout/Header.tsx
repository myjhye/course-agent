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
    <header className="sticky top-0 z-50 w-full bg-white/90 backdrop-blur-md border-b border-[#f0f1f4]">
      <div className="max-w-[1280px] mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex h-16 items-center justify-between gap-4">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-3 shrink-0">
            <div className="size-8 flex items-center justify-center bg-primary/10 rounded-lg text-primary">
              <span className="material-symbols-outlined">sports_handball</span>
            </div>
            <h2 className="text-xl font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-blue-600 to-purple-600">
              Course Agent
            </h2>
          </Link>

          {/* Search Bar (Hidden on mobile, visible on tablet+) */}
          <form onSubmit={handleSearch} className="hidden md:flex flex-1 max-w-md mx-4">
            <label className="relative w-full">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                <span className="material-symbols-outlined text-[20px]">search</span>
              </div>
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="block w-full pl-10 pr-3 py-2 border-none rounded-full bg-slate-100 text-sm focus:ring-2 focus:ring-primary/50 focus:bg-white transition-colors placeholder:text-slate-400"
                placeholder="배우고 싶은 강습을 검색해보세요..."
              />
            </label>
          </form>

          {/* Nav Links & Profile */}
          <div className="flex items-center gap-6">
            <nav className="hidden lg:flex items-center gap-6">
              <Link
                to="/lessons"
                className={`text-sm font-medium transition-colors ${
                  isActive('/lessons') ? 'text-primary' : 'text-slate-600 hover:text-primary'
                }`}
              >
                강습 둘러보기
              </Link>
              <Link
                to="/my/enrollments"
                className={`text-sm font-medium transition-colors ${
                  isActive('/my/enrollments') ? 'text-primary' : 'text-slate-600 hover:text-primary'
                }`}
              >
                내 강습
              </Link>
              <Link
                to="/chat"
                className={`text-sm font-medium transition-colors flex items-center gap-1 ${
                  isActive('/chat') ? 'text-primary' : 'text-slate-600 hover:text-primary'
                }`}
              >
                <span className="material-symbols-outlined text-[18px] text-primary">auto_awesome</span>
                AI 상담
              </Link>
            </nav>

            <div className="h-6 w-px bg-slate-200 hidden lg:block"></div>

            <Link
              to="/admin/dashboard"
              className="hidden lg:block text-sm text-slate-500 hover:text-slate-700 transition-colors"
            >
              관리자
            </Link>

            <button className="flex items-center gap-2 hover:opacity-80 transition-opacity">
              <div className="bg-gradient-to-br from-blue-400 to-purple-500 rounded-full size-9 border border-slate-200 flex items-center justify-center">
                <span className="text-white text-sm font-medium">
                  {STUDENT_NAME.charAt(0)}
                </span>
              </div>
              <span className="hidden lg:block text-sm font-medium text-slate-700">{STUDENT_NAME}</span>
            </button>

            {/* Mobile Menu Button */}
            <button
              onClick={() => setShowMobileMenu(!showMobileMenu)}
              className="lg:hidden text-slate-600"
            >
              <span className="material-symbols-outlined">menu</span>
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Menu */}
      {showMobileMenu && (
        <div className="lg:hidden border-t border-slate-200 bg-white">
          <div className="px-4 py-3 space-y-3">
            <form onSubmit={handleSearch}>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                  <span className="material-symbols-outlined text-[20px]">search</span>
                </div>
                <input
                  type="text"
                  placeholder="강습 검색..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 border border-slate-200 rounded-full text-sm"
                />
              </div>
            </form>
            <Link
              to="/lessons"
              onClick={() => setShowMobileMenu(false)}
              className="flex items-center gap-2 py-2 text-slate-700 hover:text-primary transition-colors"
            >
              <span className="material-symbols-outlined text-[20px]">school</span>
              강습 둘러보기
            </Link>
            <Link
              to="/my/enrollments"
              onClick={() => setShowMobileMenu(false)}
              className="flex items-center gap-2 py-2 text-slate-700 hover:text-primary transition-colors"
            >
              <span className="material-symbols-outlined text-[20px]">bookmark</span>
              내 강습
            </Link>
            <Link
              to="/chat"
              onClick={() => setShowMobileMenu(false)}
              className="flex items-center gap-2 py-2 text-slate-700 hover:text-primary transition-colors"
            >
              <span className="material-symbols-outlined text-[20px] text-primary">auto_awesome</span>
              AI 상담
            </Link>
            <div className="border-t border-slate-200 pt-2">
              <Link
                to="/admin/dashboard"
                onClick={() => setShowMobileMenu(false)}
                className="flex items-center gap-2 py-2 text-slate-500 hover:text-slate-700 transition-colors"
              >
                <span className="material-symbols-outlined text-[20px]">admin_panel_settings</span>
                관리자
              </Link>
            </div>
          </div>
        </div>
      )}
    </header>
  );
}

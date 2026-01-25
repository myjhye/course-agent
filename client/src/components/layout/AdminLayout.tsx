import { Link, Outlet, useLocation } from 'react-router-dom';

const NAV_ITEMS = [
  { path: '/admin/dashboard', label: '대시보드', icon: 'dashboard' },
  { path: '/admin/lessons', label: '강습 관리', icon: 'school' },
  { path: '/admin/enrollments', label: '수강 관리', icon: 'group' },
];

export default function AdminLayout() {
  const location = useLocation();

  return (
    <div className="bg-background-light text-slate-900 h-screen flex overflow-hidden">
      {/* Sidebar */}
      <aside className="w-64 bg-gray-900 text-white flex flex-col flex-shrink-0 transition-all duration-300 z-50">
        {/* Logo */}
        <div className="h-16 flex items-center px-6 border-b border-gray-800 gap-3">
          <Link to="/admin/dashboard" className="flex items-center gap-3">
            <div className="size-8 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center shadow-lg">
              <span className="font-bold text-white text-sm">CA</span>
            </div>
            <div className="flex flex-col justify-center">
              <span className="font-bold text-sm leading-tight tracking-wide">Course Agent</span>
              <span className="text-[10px] text-gray-500 font-medium uppercase tracking-wider">Admin</span>
            </div>
          </Link>
        </div>

        {/* Navigation */}
        <nav className="flex-1 py-6 px-3 flex flex-col gap-1 overflow-y-auto">
          {NAV_ITEMS.map((item) => {
            const isActive = location.pathname === item.path;
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium group transition-all ${
                  isActive
                    ? 'bg-blue-600 text-white shadow-md font-semibold'
                    : 'text-gray-400 hover:text-white hover:bg-gray-800'
                }`}
              >
                <span className="material-symbols-outlined text-[20px]">{item.icon}</span>
                {item.label}
              </Link>
            );
          })}
        </nav>

        {/* Footer */}
        <div className="p-4 border-t border-gray-800">
          <Link
            to="/"
            className="flex items-center gap-2 text-gray-400 hover:text-white text-sm font-medium transition-colors"
          >
            <span className="material-symbols-outlined text-[18px]">arrow_back</span>
            사용자 화면으로
          </Link>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col h-full overflow-hidden relative">
        {/* Header */}
        <header className="bg-white border-b border-slate-100 sticky top-0 z-40 flex-shrink-0">
          <div className="px-6 lg:px-10 py-3 flex items-center justify-between">
            <div className="flex items-center gap-4">
              {/* Mobile Menu Button */}
              <button className="text-slate-400 hover:text-slate-600 lg:hidden">
                <span className="material-symbols-outlined">menu</span>
              </button>
              
              {/* Search */}
              <div className="hidden md:flex items-center gap-2 text-slate-400 bg-slate-50 px-3 py-1.5 rounded-lg border border-transparent focus-within:border-primary/50 transition-colors w-64">
                <span className="material-symbols-outlined text-[20px]">search</span>
                <input
                  type="text"
                  placeholder="검색..."
                  className="bg-transparent border-none text-sm w-full focus:ring-0 p-0 text-slate-900 placeholder-slate-400"
                />
              </div>
            </div>

            <div className="flex flex-1 justify-end gap-8 items-center">
              <div className="flex items-center gap-4">
                {/* Notifications */}
                <button className="text-slate-500 hover:text-primary relative">
                  <span className="material-symbols-outlined">notifications</span>
                  <span className="absolute top-0 right-0 size-2 bg-red-500 rounded-full border-2 border-white"></span>
                </button>
                
                {/* User Avatar */}
                <div className="bg-gradient-to-br from-primary to-purple-600 rounded-full size-10 flex items-center justify-center text-white font-bold text-sm border-2 border-white shadow-sm cursor-pointer">
                  A
                </div>
              </div>
            </div>
          </div>
        </header>

        {/* Main Content */}
        <main className="flex-1 overflow-y-auto p-6 lg:p-10 w-full">
          <div className="max-w-[1440px] mx-auto">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}

import { Link, Outlet, useLocation } from 'react-router-dom';

const NAV_ITEMS = [
  { path: '/admin/dashboard', label: '대시보드', icon: '📊' },
  { path: '/admin/lessons', label: '강습 관리', icon: '📚' },
  { path: '/admin/enrollments', label: '수강 관리', icon: '👥' },
];

export default function AdminLayout() {
  const location = useLocation();

  return (
    <div className="min-h-screen bg-gray-100 flex">
      {/* 사이드바 */}
      <aside className="w-64 bg-gray-900 text-white">
        <div className="p-6">
          <Link to="/admin/dashboard" className="flex items-center gap-2">
            <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-sm">CA</span>
            </div>
            <span className="font-bold">Course Agent</span>
          </Link>
          <span className="text-xs text-gray-500 mt-1 block">Admin</span>
        </div>

        <nav className="px-4 space-y-1">
          {NAV_ITEMS.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={`flex items-center gap-3 px-4 py-3 rounded-lg transition ${
                location.pathname === item.path
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-400 hover:bg-gray-800 hover:text-white'
              }`}
            >
              <span>{item.icon}</span>
              <span className="font-medium">{item.label}</span>
            </Link>
          ))}
        </nav>

        <div className="absolute bottom-0 left-0 w-64 p-4 border-t border-gray-800">
          <Link
            to="/"
            className="flex items-center gap-2 text-gray-400 hover:text-white transition text-sm"
          >
            ← 사용자 화면으로
          </Link>
        </div>
      </aside>

      {/* 메인 */}
      <main className="flex-1 overflow-auto p-8">
        <Outlet />
      </main>
    </div>
  );
}

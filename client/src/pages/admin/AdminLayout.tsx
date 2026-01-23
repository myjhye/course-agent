import { Outlet, Link, useLocation } from 'react-router-dom';

const navItems = [
  { path: '/admin/dashboard', label: '대시보드' },
  { path: '/admin/lessons', label: '강습 관리' },
  { path: '/admin/instructors', label: '강사 관리' },
  { path: '/admin/enrollments', label: '수강 관리' },
];

export default function AdminLayout() {
  const location = useLocation();

  return (
    <div className="min-h-screen bg-gray-50">
      {/* 헤더 */}
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <Link to="/admin" className="text-xl font-bold text-blue-600">
            Course Agent 관리자
          </Link>
          <Link to="/" className="text-sm text-gray-500 hover:text-gray-700">
            수강생 화면으로
          </Link>
        </div>
      </header>

      {/* 네비게이션 */}
      <nav className="bg-white border-b">
        <div className="max-w-7xl mx-auto px-4">
          <div className="flex space-x-8">
            {navItems.map((item) => (
              <Link
                key={item.path}
                to={item.path}
                className={`py-4 px-1 border-b-2 font-medium text-sm ${
                  location.pathname.startsWith(item.path)
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                {item.label}
              </Link>
            ))}
          </div>
        </div>
      </nav>

      {/* 콘텐츠 */}
      <main className="max-w-7xl mx-auto px-4 py-8">
        <Outlet />
      </main>
    </div>
  );
}


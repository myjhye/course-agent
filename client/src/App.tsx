import { BrowserRouter, Routes, Route } from 'react-router-dom';
import ScrollToTop from './components/ScrollToTop';
import Layout from './components/layout/Layout';
import HomePage from './pages/HomePage';
import LessonsPage from './pages/LessonsPage';
import LessonDetailPage from './pages/LessonDetailPage';
import MyEnrollmentsPage from './pages/my/MyEnrollmentsPage';
import ChatPage from './pages/ChatPage';
// Admin pages
import AdminLayout from './components/layout/AdminLayout';
import DashboardPage from './pages/admin/DashboardPage';
import AdminLessonsPage from './pages/admin/LessonsPage';
import AdminLessonCreatePage from './pages/admin/LessonCreatePage';
import AdminLessonDetailPage from './pages/admin/LessonDetailPage';
import AdminEnrollmentsPage from './pages/admin/EnrollmentsPage';

export default function App() {
  return (
    <BrowserRouter>
      <ScrollToTop />
      <Routes>
        {/* 일반 사용자 */}
        <Route element={<Layout />}>
          <Route path="/" element={<HomePage />} />
          <Route path="/lessons" element={<LessonsPage />} />
          <Route path="/lessons/:id" element={<LessonDetailPage />} />
          <Route path="/my/enrollments" element={<MyEnrollmentsPage />} />
          <Route path="/chat" element={<ChatPage />} />
        </Route>

        {/* 관리자 */}
        <Route path="/admin" element={<AdminLayout />}>
          <Route path="dashboard" element={<DashboardPage />} />
          <Route path="lessons" element={<AdminLessonsPage />} />
          <Route path="lessons/new" element={<AdminLessonCreatePage />} />
          <Route path="lessons/:id" element={<AdminLessonDetailPage />} />
          <Route path="enrollments" element={<AdminEnrollmentsPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}


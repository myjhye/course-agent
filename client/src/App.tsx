import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';

// Admin pages
import AdminLayout from './pages/admin/AdminLayout';
import DashboardPage from './pages/admin/DashboardPage';
import LessonsPage from './pages/admin/LessonsPage';
import LessonCreatePage from './pages/admin/LessonCreatePage';
import LessonDetailPage from './pages/admin/LessonDetailPage';
import InstructorsPage from './pages/admin/InstructorsPage';
import EnrollmentsPage from './pages/admin/EnrollmentsPage';

// Public/Student pages
import HomePage from './pages/HomePage';
import MyLessonsPage from './pages/my/MyLessonsPage';
import MyLessonDetailPage from './pages/my/MyLessonDetailPage';
import MyEnrollmentsPage from './pages/my/MyEnrollmentsPage';
import ChatPage from './pages/ChatPage';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* 홈 */}
        <Route path="/" element={<HomePage />} />

        {/* 운영자 */}
        <Route path="/admin" element={<AdminLayout />}>
          <Route index element={<Navigate to="/admin/dashboard" replace />} />
          <Route path="dashboard" element={<DashboardPage />} />
          <Route path="lessons" element={<LessonsPage />} />
          <Route path="lessons/new" element={<LessonCreatePage />} />
          <Route path="lessons/:id" element={<LessonDetailPage />} />
          <Route path="instructors" element={<InstructorsPage />} />
          <Route path="enrollments" element={<EnrollmentsPage />} />
        </Route>

        {/* 수강생 */}
        <Route path="/lessons" element={<MyLessonsPage />} />
        <Route path="/lessons/:id" element={<MyLessonDetailPage />} />
        <Route path="/my/enrollments" element={<MyEnrollmentsPage />} />
        <Route path="/chat" element={<ChatPage />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;


import { Route, Routes } from 'react-router-dom';
import { AdminUsersPage } from '@/pages/admin-users';
import { AnswerWindowPage } from '@/pages/answer-window';
import { DashboardPage } from '@/pages/dashboard';
import { DdTypesPage } from '@/pages/dd-types';
import { LoginPage } from '@/pages/login';
import { NotFoundPage } from '@/pages/not-found';
import { ProfilePage } from '@/pages/profile';
import { QuestionsPage } from '@/pages/questions';
import { ResetPasswordPage } from '@/pages/reset-password';
import { SessionAnswersPage } from '@/pages/session-answers';
import { SessionCreatePage } from '@/pages/session-create';
import { SessionDetailPage } from '@/pages/session-detail';
import { VectorStoresPage } from '@/pages/vector-stores';
import { AppLayout } from '@/widgets/app-layout';
import { GuestOnly, RequireAuth } from './RequireAuth';

export const AppRouter = () => (
  <Routes>
    <Route element={<GuestOnly />}>
      <Route path="/login" element={<LoginPage />} />
    </Route>

    {/* The link of a reset e-mail: open whether or not someone is signed in. */}
    <Route path="/reset-password" element={<ResetPasswordPage />} />

    <Route element={<RequireAuth />}>
      {/* An answer in a window of its own: no application bar, the window has its own. */}
      <Route path="/session/:sessionId/answer/:answerId" element={<AnswerWindowPage />} />
      <Route element={<AppLayout />}>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/session/create" element={<SessionCreatePage />} />
        <Route path="/session/:sessionId" element={<SessionDetailPage />} />
        <Route path="/session/:sessionId/answers" element={<SessionAnswersPage />} />
        <Route path="/profile" element={<ProfilePage />} />
        <Route path="/questions" element={<QuestionsPage />} />
        <Route path="/dd-types" element={<DdTypesPage />} />
        <Route path="/vector-stores" element={<VectorStoresPage />} />
        <Route element={<RequireAuth adminOnly />}>
          <Route path="/admin/users" element={<AdminUsersPage />} />
        </Route>
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Route>
  </Routes>
);

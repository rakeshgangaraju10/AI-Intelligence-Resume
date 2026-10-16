import { Route, Routes } from "react-router";

import { AppLayout } from "./components/layout/AppLayout";
import { PublicLayout } from "./components/layout/PublicLayout";
import { ProtectedRoute, PublicOnlyRoute } from "./features/auth/RouteGuards";
import { AnalysesPage } from "./pages/AnalysesPage";
import { AnalysisComparePage } from "./pages/AnalysisComparePage";
import { AnalysisDetailPage } from "./pages/AnalysisDetailPage";
import { DashboardPage } from "./pages/DashboardPage";
import { ForgotPasswordPage } from "./pages/ForgotPasswordPage";
import { JobDetailPage } from "./pages/JobDetailPage";
import { JobNewPage } from "./pages/JobNewPage";
import { JobsPage } from "./pages/JobsPage";
import { LandingPage } from "./pages/LandingPage";
import { LoginPage } from "./pages/LoginPage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { RegisterPage } from "./pages/RegisterPage";
import { ResetPasswordPage } from "./pages/ResetPasswordPage";
import { ResumeReviewPage } from "./pages/ResumeReviewPage";
import { ResumesPage } from "./pages/ResumesPage";
import { ResumeUploadPage } from "./pages/ResumeUploadPage";
import { SettingsPage } from "./pages/SettingsPage";

export function App() {
  return (
    <Routes>
      <Route element={<PublicLayout />}>
        <Route index element={<LandingPage />} />
        <Route element={<PublicOnlyRoute />}>
          <Route path="login" element={<LoginPage />} />
          <Route path="register" element={<RegisterPage />} />
          <Route path="forgot-password" element={<ForgotPasswordPage />} />
        </Route>
        {/* Reachable while logged in too: the emailed link must always work. */}
        <Route path="reset-password/:uid/:token" element={<ResetPasswordPage />} />
      </Route>

      <Route element={<ProtectedRoute />}>
        <Route element={<AppLayout />}>
          <Route path="dashboard" element={<DashboardPage />} />
          <Route path="resumes" element={<ResumesPage />} />
          <Route path="resumes/upload" element={<ResumeUploadPage />} />
          <Route path="resumes/:resumeId" element={<ResumeReviewPage />} />
          <Route path="jobs" element={<JobsPage />} />
          <Route path="jobs/new" element={<JobNewPage />} />
          <Route path="jobs/:jobId" element={<JobDetailPage />} />
          <Route path="analyses" element={<AnalysesPage />} />
          <Route path="analyses/compare" element={<AnalysisComparePage />} />
          <Route path="analyses/:analysisId" element={<AnalysisDetailPage />} />
          <Route path="settings" element={<SettingsPage />} />
        </Route>
      </Route>

      <Route element={<PublicLayout />}>
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}

import { Navigate, Route, Routes } from "react-router-dom";

import { AppShell } from "./components/AppShell";
import { BenchmarksPage } from "./pages/Benchmarks";
import { DashboardPage } from "./pages/Dashboard";
import { DemoPage } from "./pages/Demo";
import { LandingPage } from "./pages/Landing";
import { ReviewQueuePage } from "./pages/ReviewQueue";

export function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route element={<AppShell />}>
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/dashboard/actions/:actionId" element={<DashboardPage />} />
        <Route path="/review" element={<ReviewQueuePage />} />
        <Route path="/review/actions/:actionId" element={<ReviewQueuePage />} />
        <Route path="/demo" element={<DemoPage />} />
        <Route path="/demo/actions/:actionId" element={<DemoPage />} />
        <Route path="/benchmarks" element={<BenchmarksPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

import { NavLink, Route, Routes } from "react-router-dom";
import { BookOpen, Clock3, PlusCircle } from "lucide-react";

import JobHistoryPage from "./pages/JobHistoryPage";
import JobResultPage from "./pages/JobResultPage";
import ProblemInputPage from "./pages/ProblemInputPage";

const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  `inline-flex items-center gap-2 border-b-2 px-1 py-4 text-sm font-medium ${
    isActive
      ? "border-teal-600 text-teal-700"
      : "border-transparent text-slate-600 hover:border-slate-300 hover:text-slate-900"
  }`;

export default function App() {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-950">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-md bg-teal-600 text-white">
              <BookOpen size={19} aria-hidden="true" />
            </div>
            <div>
              <p className="text-base font-semibold leading-tight">Study Buddy</p>
              <p className="text-xs text-slate-500">Local programming explainer</p>
            </div>
          </div>
          <nav className="flex gap-6">
            <NavLink to="/" className={navLinkClass}>
              <PlusCircle size={16} aria-hidden="true" />
              New problem
            </NavLink>
            <NavLink to="/history" className={navLinkClass}>
              <Clock3 size={16} aria-hidden="true" />
              History
            </NavLink>
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
        <Routes>
          <Route path="/" element={<ProblemInputPage />} />
          <Route path="/history" element={<JobHistoryPage />} />
          <Route path="/jobs/:jobId" element={<JobResultPage />} />
        </Routes>
      </main>
    </div>
  );
}


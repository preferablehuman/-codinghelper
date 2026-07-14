import { NavLink, Route, Routes } from "react-router-dom";
import { Clock3, Code2, Moon, PlusCircle, Sun } from "lucide-react";
import { useEffect, useState } from "react";

import JobHistoryPage from "./pages/JobHistoryPage";
import JobResultPage from "./pages/JobResultPage";
import ProblemInputPage from "./pages/ProblemInputPage";

const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  `focus-ring inline-flex h-10 items-center gap-2 rounded-md px-3 text-sm font-medium transition duration-200 ${
    isActive
      ? "bg-zinc-950 text-white shadow-sm shadow-zinc-950/10 dark:bg-white dark:text-zinc-950"
      : "text-zinc-600 hover:bg-zinc-100 hover:text-zinc-950 dark:text-zinc-300 dark:hover:bg-zinc-800 dark:hover:text-white"
  }`;

type Theme = "light" | "dark";
const THEME_STORAGE_KEY = "coding-helper-theme";
const LEGACY_THEME_STORAGE_KEY = "study-buddy-theme";

function initialTheme(): Theme {
  if (typeof window === "undefined") {
    return "dark";
  }
  const stored = window.localStorage.getItem(THEME_STORAGE_KEY) ?? window.localStorage.getItem(LEGACY_THEME_STORAGE_KEY);
  if (stored === "light" || stored === "dark") {
    return stored;
  }
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export default function App() {
  const [theme, setTheme] = useState<Theme>(initialTheme);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
    window.localStorage.setItem(THEME_STORAGE_KEY, theme);
    window.localStorage.removeItem(LEGACY_THEME_STORAGE_KEY);
  }, [theme]);

  return (
    <div className="min-h-screen text-zinc-950 transition-colors duration-300 dark:text-zinc-50">
      <header className="sticky top-0 z-30 border-b border-zinc-200/80 bg-white/85 backdrop-blur-xl transition-colors duration-300 dark:border-zinc-800/80 dark:bg-zinc-950/85">
        <div className="mx-auto flex h-16 w-full max-w-[1760px] items-center justify-between px-4 sm:px-6 lg:px-8">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-md border border-emerald-400/50 bg-zinc-950 text-emerald-300 shadow-sm shadow-emerald-950/20 dark:bg-zinc-900">
              <Code2 size={19} aria-hidden="true" />
            </div>
            <div>
              <p className="text-base font-semibold leading-tight text-zinc-950 dark:text-white">CodingHelper</p>
              <p className="font-mono text-xs text-zinc-500 dark:text-zinc-400">local coding explainer</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <nav className="flex gap-2">
              <NavLink to="/" className={navLinkClass}>
                <PlusCircle size={16} aria-hidden="true" />
                New problem
              </NavLink>
              <NavLink to="/history" className={navLinkClass}>
                <Clock3 size={16} aria-hidden="true" />
                History
              </NavLink>
            </nav>
            <button
              type="button"
              onClick={() => setTheme((current) => (current === "dark" ? "light" : "dark"))}
              className="focus-ring inline-flex h-10 w-10 items-center justify-center rounded-md border border-zinc-200 bg-white text-zinc-700 shadow-sm transition duration-200 hover:bg-zinc-100 dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-200 dark:hover:bg-zinc-800"
              aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
              title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
            >
              {theme === "dark" ? <Sun size={17} aria-hidden="true" /> : <Moon size={17} aria-hidden="true" />}
            </button>
          </div>
        </div>
      </header>
      <main className="page-shell min-h-[calc(100vh-4rem)] animate-fade-in">
        <Routes>
          <Route path="/" element={<ProblemInputPage />} />
          <Route path="/history" element={<JobHistoryPage />} />
          <Route path="/jobs/:jobId" element={<JobResultPage />} />
        </Routes>
      </main>
    </div>
  );
}

"use client";

import { useEffect, useState } from "react";

export default function ThemeToggle() {
  const [dark, setDark] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    const stored = localStorage.getItem("theme");
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    const isDark = stored === "dark" || (!stored && prefersDark);
    setDark(isDark);
    document.documentElement.classList.toggle("dark", isDark);
  }, []);

  function toggle() {
    const next = !dark;
    setDark(next);
    document.documentElement.classList.toggle("dark", next);
    localStorage.setItem("theme", next ? "dark" : "light");
  }

  if (!mounted) return <div className="w-12 h-6 rounded-full bg-slate-200 dark:bg-slate-700" />;

  return (
    <button onClick={toggle} aria-label="Témaváltás"
      className={`relative w-12 h-6 rounded-full transition-colors duration-300 focus:outline-none focus-visible:ring-2 focus-visible:ring-crimson-500
                  ${dark ? "bg-navy-600" : "bg-slate-200"}`}>
      <span className={`absolute top-0.5 w-5 h-5 rounded-full bg-white shadow-md
                        transition-all duration-300 flex items-center justify-center text-[10px]
                        ${dark ? "left-[26px]" : "left-0.5"}`}>
        {dark ? "🌙" : "☀️"}
      </span>
    </button>
  );
}

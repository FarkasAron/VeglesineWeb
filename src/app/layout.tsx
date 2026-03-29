import type { Metadata } from "next";
import "./globals.css";
import ThemeToggle from "@/components/ThemeToggle";
import Link from "next/link";
import Image from "next/image";

export const metadata: Metadata = {
  title: "Matematika Feladatbank",
  description: "Magyar érettségi matematika feladatok témakör és nehézség szerint szűrve.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="hu" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: `
          try {
            const t = localStorage.getItem('theme');
            const d = window.matchMedia('(prefers-color-scheme: dark)').matches;
            if (t === 'dark' || (!t && d)) document.documentElement.classList.add('dark');
          } catch(e) {}
        `}} />
      </head>
      <body className="min-h-screen bg-slate-50 dark:bg-[#060d1a] transition-colors duration-300">

        {/* Top accent bar */}
        <div className="h-1 w-full bg-gradient-to-r from-navy-600 via-crimson-600 to-navy-600" />

        {/* Header */}
        <header className="sticky top-0 z-50 glass border-b border-slate-200/50 dark:border-white/5">
          <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between gap-6">

            {/* Logo */}
            <Link href="/" className="flex items-center gap-3 group">
              <Image
                src="/boronkay-logo.png"
                alt="Boronkay"
                width={36} height={36}
                className="rounded-lg group-hover:scale-110 transition-transform duration-300 drop-shadow-sm"
              />
              <div className="hidden sm:block">
                <div className="text-sm font-bold text-slate-900 dark:text-white leading-none">Matematika</div>
                <div className="text-xs text-slate-400 dark:text-slate-500 leading-none mt-0.5">Feladatbank</div>
              </div>
            </Link>

            {/* Nav */}
            <nav className="flex items-center gap-1">
              {[
                { href: "/feladatok",      label: "Feladatok" },
                { href: "/feladatsor",     label: "Feladatsorok" },
                { href: "/temakoren-kint", label: "Témakörök" },
                { href: "/statisztika",    label: "Statisztika" },
              ].map(({ href, label }) => (
                <Link key={href} href={href}
                  className="nav-link px-4 py-2 rounded-lg text-slate-600 dark:text-slate-300
                             hover:text-navy-600 hover:bg-navy-50 dark:hover:bg-white/5 dark:hover:text-white">
                  {label}
                </Link>
              ))}
            </nav>

            <ThemeToggle />
          </div>
        </header>

        <main className="max-w-6xl mx-auto px-4 py-10">
          {children}
        </main>

        <footer className="mt-20 border-t border-slate-200 dark:border-white/5 py-10">
          <div className="max-w-6xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-4 text-sm text-slate-400 dark:text-slate-600">
            <span>Matematika Feladatbank — Boronkay György Technikum</span>
            <span>Forrás: Oktatási Hivatal érettségi feladatsorok</span>
          </div>
        </footer>
      </body>
    </html>
  );
}

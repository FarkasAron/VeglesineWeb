import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Érettségi Matematika Feladatbank",
  description: "Magyar érettségi matematika feladatok témakör és nehézség szerint szűrve.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="hu">
      <body className="min-h-screen bg-gray-50 text-gray-900">
        <header className="bg-white border-b border-gray-200 px-4 py-3">
          <div className="max-w-6xl mx-auto flex items-center justify-between">
            <a href="/" className="text-lg font-semibold text-blue-700 hover:text-blue-800">
              Matematika Feladatbank
            </a>
            <nav className="flex gap-6 text-sm text-gray-600">
              <a href="/feladatok" className="hover:text-blue-700">Feladatok</a>
              <a href="/temakoren-kint" className="hover:text-blue-700">Témakörök</a>
            </nav>
          </div>
        </header>
        <main className="max-w-6xl mx-auto px-4 py-8">
          {children}
        </main>
        <footer className="border-t border-gray-200 mt-16 py-6 text-center text-sm text-gray-500">
          Forrás: Oktatási Hivatal érettségi feladatsorok
        </footer>
      </body>
    </html>
  );
}
